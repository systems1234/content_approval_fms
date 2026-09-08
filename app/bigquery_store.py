from datetime import datetime
import os
import uuid
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from google.cloud import bigquery


STAGE_TABLES = (
    'Seed_File',
    'Content_Planning',
    'Content_Creation',
    'Content_Review_and_Approval',
    'Content_Audit',
    'Content_Publishing',
    'Content_Distribution',
)

WORKFLOW_TABLE = 'Content_Approval_Workflow'

# State machine for the post-authoring approval loop.
#   KEYWORDS_READY     -- external API finished keyword research (informational)
#   DRAFT_RECEIVED     -- external API delivered the auto-written draft; awaiting Vivek
#   APPROVED           -- Vivek approved the draft; about to be allocated
#   ALLOCATED          -- content handed to a doer to write/update
#   SUBMITTED          -- doer submitted a version; awaiting Vivek's call
#   REWRITE_REQUESTED  -- Vivek sent it back for changes (loops to the same doer)
#   COMPLETED          -- Vivek gave final confirmation (terminal)
#   DELETED            -- request was cancelled (terminal)
WORKFLOW_ACTIONS = (
    'KEYWORDS_READY', 'DRAFT_RECEIVED', 'APPROVED', 'ALLOCATED',
    'SUBMITTED', 'REWRITE_REQUESTED', 'COMPLETED', 'DELETED',
)
WORKFLOW_TERMINAL_ACTIONS = ('COMPLETED', 'DELETED')
# Stages a doer may act on (submit a version for).
WORKFLOW_DOER_ACTIONABLE = ('ALLOCATED', 'REWRITE_REQUESTED')
# Stages Vivek (approver) may act on.
WORKFLOW_APPROVER_ACTIONABLE = ('DRAFT_RECEIVED', 'SUBMITTED')

WORKFLOW_COLUMNS = {
    'event_id', 'timestamp', 'unique_key', 'category', 'action',
    'actor_user_id', 'actor_email', 'assignee_user_id', 'assignee_email',
    'content_text', 'content_url', 'word_count', 'search_keywords',
    'search_volume', 'comment', 'revision_number',
}

STAGE_COLUMNS = {
    'Seed_File': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'upload_file', 'step_code', 'planned_date'},
    'Content_Planning': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'search_volume', 'url', 'gemstone_type', 'tab_content', 'seed_file_upload_date'},
    'Content_Creation': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'upload_file', 'step_code', 'planned_date', 'words_count'},
    'Content_Review_and_Approval': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'approval', 'suggestion', 'step_code', 'planned_date', 'content_quality_rating', 'seo_quality_rating'},
    'Content_Audit': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'approval', 'step_code', 'planned_date', 'suggestion'},
    'Content_Publishing': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'content_published', 'step_code', 'planned_date'},
    'Content_Distribution': {'timestamp', 'email', 'user_id', 'primary_key', 'unique_key', 'category', 'content_posted', 'step_code', 'planned_date'},
}


class BigQueryUser(UserMixin):
    def __init__(self, row):
        self.id = int(row['user_id'])
        self.username = row.get('username') or row.get('email')
        self.email = row.get('email') or ''
        self.password_hash = row.get('password_hash') or ''
        self.role = row.get('role') or 'assignee'
        self.active = row.get('is_active', True)
        self.created_at = row.get('created_at')

    @property
    def is_active(self):
        return self.active

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role in ('admin', 'manager')

    def is_auditor(self):
        return self.role in ('admin', 'manager', 'auditor')

    def is_approver(self):
        """Can approve/allocate/complete/reject content in the workflow (i.e. 'Vivek')."""
        return self.role in ('admin', 'approver')

    def is_doer(self):
        """Everyone can be assigned content to write/update except pure approvers/admins-only view."""
        return self.role in ('assignee', 'manager', 'auditor', 'approver', 'admin')


class ContentRecord:
    def __init__(self, row):
        self.id = row['unique_key']
        self.ticket_id = row['unique_key']
        self.title = row.get('category') or row['unique_key']
        self.description = row.get('tab_content') or row.get('suggestion') or ''
        self.unique_key = row['unique_key']
        self.category = row.get('category') or ''
        self.source_table = row.get('source_table', '')
        approval = str(row.get('approval') or row.get('Approval') or '').lower()
        self.status = {
            'approved': 'audit_passed',
            'rejected': 'audit_failed',
            'pending': 'under_audit',
        }.get(approval, self._status_from_stage())
        self.plan_date = row.get('planned_date')
        self.updated_at = row.get('timestamp')
        self.created_at = row.get('timestamp')
        self.content_data = row
        self.revision_count = 0
        self.audit_date = None
        self.completed_date = None

    @property
    def is_delayed(self):
        return bool(self.plan_date and self.plan_date.date() < datetime.utcnow().date() and self.status not in ('audit_passed', 'cancelled'))

    def get_status_badge_class(self):
        return 'bg-blue-100 text-blue-800'

    def _status_from_stage(self):
        return {
            'Seed_File': 'assigned',
            'Content_Planning': 'in_progress',
            'Content_Creation': 'in_progress',
            'Content_Review_and_Approval': 'under_audit',
            'Content_Audit': 'under_audit',
            'Content_Publishing': 'audit_passed',
            'Content_Distribution': 'audit_passed',
        }.get(self.source_table, 'assigned')


class WorkflowItem:
    """Current state of one content item in the approval workflow, folded from
    its full append-only event history (oldest first)."""

    STAGE_LABELS = {
        'KEYWORDS_READY': 'Keyword Search Done',
        'DRAFT_RECEIVED': 'Pending Approval',
        'APPROVED': 'Approved (Allocating)',
        'ALLOCATED': 'Assigned',
        'SUBMITTED': 'Pending Review',
        'REWRITE_REQUESTED': 'Rewrite Requested',
        'COMPLETED': 'Completed',
        'DELETED': 'Deleted',
    }

    def __init__(self, events):
        events = sorted(events, key=lambda row: row.get('timestamp') or datetime.min)
        self.history = events
        first, last = events[0], events[-1]
        self.unique_key = last['unique_key']
        self.category = last.get('category') or first.get('category') or ''
        self.stage = last['action']
        self.created_at = first.get('timestamp')
        self.updated_at = last.get('timestamp')
        self.revision_number = max((row.get('revision_number') or 0) for row in events)

        # Fold forward the last known value of each carry-forward field so that,
        # e.g., the assignee and content text are still known during SUBMITTED
        # or REWRITE_REQUESTED even though only the ALLOCATED row set them.
        carried = {}
        for row in events:
            for field in ('assignee_user_id', 'assignee_email', 'content_text',
                          'content_url', 'word_count', 'search_keywords', 'search_volume'):
                if row.get(field) not in (None, ''):
                    carried[field] = row[field]
        self.assignee_user_id = carried.get('assignee_user_id')
        self.assignee_email = carried.get('assignee_email')
        self.content_text = carried.get('content_text')
        self.content_url = carried.get('content_url')
        self.word_count = carried.get('word_count')
        self.search_keywords = carried.get('search_keywords')
        self.search_volume = carried.get('search_volume')
        self.last_comment = last.get('comment') or ''
        self.last_actor_email = last.get('actor_email') or ''

    @property
    def stage_label(self):
        return self.STAGE_LABELS.get(self.stage, self.stage)

    @property
    def is_terminal(self):
        return self.stage in WORKFLOW_TERMINAL_ACTIONS

    def awaiting_approver(self):
        return self.stage in WORKFLOW_APPROVER_ACTIONABLE

    def awaiting_doer(self, user=None):
        if self.stage not in WORKFLOW_DOER_ACTIONABLE:
            return False
        if user is None:
            return True
        return self.assignee_user_id == user.id


class BigQueryStore:
    def __init__(self, app):
        self.project = app.config['BIGQUERY_PROJECT']
        self.dataset = app.config['BIGQUERY_DATASET']
        self.users_table = app.config['BIGQUERY_USERS_TABLE']
        self.client = None

    def _client(self):
        if self.client is None:
            credentials = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if credentials:
                from google.oauth2 import service_account
                self.client = bigquery.Client.from_service_account_info(__import__('json').loads(credentials), project=self.project)
            else:
                self.client = bigquery.Client(project=self.project)
        return self.client

    def table(self, name):
        return f'`{self.project}.{self.dataset}.{name}`'

    def query(self, sql, params=()):
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter(f'p{i}', 'STRING', value)
            for i, value in enumerate(params)
        ])
        return [{str(key).lower(): value for key, value in row.items()} for row in self._client().query(sql, job_config=job_config).result()]

    def user(self, user_id=None, username=None):
        where = 'user_id = @p0' if user_id is not None else 'username = @p0'
        rows = self.query(f'SELECT * FROM {self.table(self.users_table)} WHERE {where} ORDER BY updated_at DESC LIMIT 1', (str(user_id) if user_id is not None else username,))
        rows = [row for row in rows if row.get('is_active', True)]
        return BigQueryUser(rows[0]) if rows else None

    def user_by_email(self, email):
        rows = self.query(f'SELECT * FROM {self.table(self.users_table)} WHERE LOWER(email) = LOWER(@p0) ORDER BY updated_at DESC LIMIT 1', (email,))
        rows = [row for row in rows if row.get('is_active', True)]
        return BigQueryUser(rows[0]) if rows else None

    def users(self):
        rows = self.query(f'SELECT * FROM {self.table(self.users_table)} ORDER BY created_at DESC')
        return [BigQueryUser(row) for row in rows]

    def records(self, user=None):
        rows = []
        for table in STAGE_TABLES:
            table_rows = self.query(f'SELECT * FROM {self.table(table)} WHERE Unique_Key IS NOT NULL ORDER BY Timestamp DESC')
            for row in table_rows:
                row['source_table'] = table
            rows.extend(table_rows)
        rows.sort(key=lambda row: row.get('timestamp') or datetime.min, reverse=True)
        latest = {}
        for row in rows:
            key = row['unique_key']
            if key not in latest:
                latest[key] = row
        return [ContentRecord(row) for row in latest.values()]

    def record(self, unique_key):
        return next((item for item in self.records() if item.unique_key == unique_key), None)

    def append(self, table, row):
        errors = self._client().insert_rows_json(f'{self.project}.{self.dataset}.{table}', [row])
        if errors:
            raise RuntimeError(str(errors))

    def create_user(self, username, email, password, role):
        # A blank password means "Google SSO only": store an unusable hash
        # (werkzeug's check_password_hash never matches it) rather than no
        # password_hash at all, since BigQueryUser.check_password treats a
        # falsy hash as "no password set" and callers may not distinguish.
        password_hash = generate_password_hash(password, method='pbkdf2:sha256') if password \
            else generate_password_hash(uuid.uuid4().hex, method='pbkdf2:sha256')
        self.append(self.users_table, {
            'user_id': int(datetime.utcnow().timestamp() * 1000),
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        })

    def append_event(self, table, record, user, approval=None, suggestion=None, values=None):
        row = {
            'timestamp': datetime.utcnow().isoformat(),
            'email': user.email,
            'user_id': user.id,
            'primary_key': record.content_data.get('primary_key'),
            'unique_key': record.unique_key,
            'category': record.category,
            'step_code': record.content_data.get('step_code'),
            'planned_date': record.plan_date.isoformat() if record.plan_date else None,
        }
        if approval is not None:
            row['approval'] = approval
        if suggestion is not None:
            row['suggestion'] = suggestion
        row.update(values or {})
        self.append(table, {key: value for key, value in row.items() if key in STAGE_COLUMNS[table]})

    def set_user_active(self, user_id, active):
        rows = self.query(f'SELECT * FROM {self.table(self.users_table)} WHERE user_id = @p0 ORDER BY updated_at DESC LIMIT 1', (str(user_id),))
        user = BigQueryUser(rows[0]) if rows else None
        if not user:
            raise ValueError('User not found')
        self.append(self.users_table, {
            'user_id': user.id, 'username': user.username, 'email': user.email,
            'password_hash': user.password_hash, 'role': user.role,
            'is_active': active, 'created_at': user.created_at or datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        })

    def upload_file(self, file_storage):
        from google.cloud import storage
        bucket_name = os.environ.get('GCS_BUCKET')
        if not bucket_name:
            raise RuntimeError('GCS_BUCKET is not configured')
        client = storage.Client(project=self.project)
        blob = client.bucket(bucket_name).blob(f'content/{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}_{file_storage.filename}')
        blob.upload_from_file(file_storage, content_type=file_storage.content_type)
        return blob.public_url

    # ------------------------------------------------------------------
    # Approval workflow (event-sourced state machine over WORKFLOW_TABLE)
    # ------------------------------------------------------------------

    def _workflow_rows(self, unique_key=None):
        where = 'WHERE unique_key = @p0' if unique_key else ''
        params = (unique_key,) if unique_key else ()
        return self.query(
            f'SELECT * FROM {self.table(WORKFLOW_TABLE)} {where} ORDER BY timestamp ASC', params)

    def append_workflow_event(self, unique_key, action, actor=None, category=None,
                               assignee=None, comment=None, revision_number=None, **fields):
        if action not in WORKFLOW_ACTIONS:
            raise ValueError(f'Unknown workflow action: {action}')
        row = {
            'event_id': uuid.uuid4().hex,
            'timestamp': datetime.utcnow().isoformat(),
            'unique_key': unique_key,
            'category': category,
            'action': action,
            'comment': comment,
            'revision_number': revision_number,
        }
        if actor is not None:
            row['actor_user_id'] = actor.id
            row['actor_email'] = actor.email
        if assignee is not None:
            row['assignee_user_id'] = assignee.id
            row['assignee_email'] = assignee.email
        row.update(fields)
        self.append(WORKFLOW_TABLE, {key: value for key, value in row.items()
                                      if key in WORKFLOW_COLUMNS and value is not None})

    def workflow_items(self):
        """All content items currently in (or that ever entered) the approval workflow,
        newest activity first."""
        rows = self._workflow_rows()
        grouped = {}
        for row in rows:
            grouped.setdefault(row['unique_key'], []).append(row)
        items = [WorkflowItem(events) for events in grouped.values()]
        items.sort(key=lambda item: item.updated_at or datetime.min, reverse=True)
        return items

    def workflow_item(self, unique_key):
        rows = self._workflow_rows(unique_key)
        return WorkflowItem(rows) if rows else None

    # -- external API stub (stage 1 & 2 automation) -----------------------

    def ingest_keyword_search(self, unique_key, category, search_keywords, search_volume=None):
        """Called by the (future) external keyword-research API once it has
        finished stage 1 for this content item."""
        self.append_workflow_event(unique_key, 'KEYWORDS_READY', category=category,
                                    search_keywords=search_keywords, search_volume=search_volume)

    def ingest_content_draft(self, unique_key, category, content_text=None, content_url=None, word_count=None):
        """Called by the (future) external content-writer API once it has
        finished stage 2 (initial content written) for this content item.
        This is what puts the item in front of Vivek for approval."""
        self.append_workflow_event(unique_key, 'DRAFT_RECEIVED', category=category,
                                    content_text=content_text, content_url=content_url, word_count=word_count)

    # -- approver (Vivek) actions -------------------------------------------

    def approve_and_allocate(self, unique_key, approver, assignee, comment=None):
        item = self.workflow_item(unique_key)
        if not item or item.stage != 'DRAFT_RECEIVED':
            raise ValueError('Content must be in "Pending Approval" to be approved.')
        self.append_workflow_event(unique_key, 'APPROVED', actor=approver,
                                    category=item.category, comment=comment)
        self.append_workflow_event(unique_key, 'ALLOCATED', actor=approver,
                                    category=item.category, assignee=assignee)

    def request_rewrite(self, unique_key, approver, comment):
        item = self.workflow_item(unique_key)
        if not item or item.stage != 'SUBMITTED':
            raise ValueError('Only a submitted version can be sent back for a re-write.')
        if not comment or not comment.strip():
            raise ValueError('A comment is required when requesting a re-write.')
        self.append_workflow_event(unique_key, 'REWRITE_REQUESTED', actor=approver,
                                    category=item.category, comment=comment.strip(),
                                    assignee_user_id=item.assignee_user_id, assignee_email=item.assignee_email)

    def complete_workflow(self, unique_key, approver, comment=None):
        item = self.workflow_item(unique_key)
        if not item or item.stage != 'SUBMITTED':
            raise ValueError('Only a submitted version can be given final confirmation.')
        self.append_workflow_event(unique_key, 'COMPLETED', actor=approver,
                                    category=item.category, comment=comment)

    def delete_workflow_item(self, unique_key, actor, comment=None):
        item = self.workflow_item(unique_key)
        if not item:
            raise ValueError('No such content item.')
        if item.is_terminal:
            raise ValueError('This request is already closed.')
        self.append_workflow_event(unique_key, 'DELETED', actor=actor,
                                    category=item.category, comment=comment)

    # -- doer actions -------------------------------------------------------

    def submit_update(self, unique_key, doer, content_text=None, content_url=None, comment=None):
        item = self.workflow_item(unique_key)
        if not item or item.stage not in WORKFLOW_DOER_ACTIONABLE:
            raise ValueError('This item is not currently assigned to you for writing.')
        if item.assignee_user_id != doer.id:
            raise ValueError('This item is assigned to someone else.')
        if not (content_text or '').strip() and not (content_url or '').strip():
            raise ValueError('Provide the updated content (text or a link) before submitting.')
        self.append_workflow_event(unique_key, 'SUBMITTED', actor=doer, category=item.category,
                                    content_text=content_text, content_url=content_url, comment=comment,
                                    revision_number=item.revision_number + 1,
                                    assignee_user_id=item.assignee_user_id, assignee_email=item.assignee_email)