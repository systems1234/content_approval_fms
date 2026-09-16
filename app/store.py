"""BigQuery access layer for the Content FMS.

Everything is append-only. Reads fold an item's event history forward; writes
are parameterised DML `INSERT`s rather than the streaming API, so a row is
queryable the instant the statement returns instead of sitting in a buffer.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from flask_login import UserMixin
from google.cloud import bigquery

IST = ZoneInfo('Asia/Kolkata')


def now_ist() -> datetime:
    """Naive IST. Everything in this app is stored and shown in IST."""
    return datetime.now(IST).replace(tzinfo=None, microsecond=0)


# --------------------------------------------------------------------------
# Column types. Needed so a NULL lands in the right slot: BigQuery cannot infer
# a parameter's type from a None, and will not compare an INT64 to a STRING.
# --------------------------------------------------------------------------

USER_COLUMNS = {
    'user_id': 'INT64',
    'username': 'STRING',
    'email': 'STRING',
    'password_hash': 'STRING',
    'role': 'STRING',
    'is_active': 'BOOL',
    'created_at': 'DATETIME',
    'updated_at': 'DATETIME',
}

EVENT_COLUMNS = {
    'event_id': 'STRING',
    'timestamp': 'DATETIME',
    'unique_key': 'STRING',
    'category': 'STRING',
    'action': 'STRING',
    'actor_user_id': 'INT64',
    'actor_email': 'STRING',
    'assignee_user_id': 'INT64',
    'assignee_email': 'STRING',
    'content_text': 'STRING',
    'content_url': 'STRING',
    'word_count': 'INT64',
    'search_keywords': 'STRING',
    'search_volume': 'INT64',
    'comment': 'STRING',
    'revision_number': 'INT64',
    'source_row_id': 'STRING',
    'source_payload': 'STRING',
}

# Every event field except the two heavy ones. List screens fold from these;
# the item screen refetches everything. One fold, one code path, no divergence.
LIGHT_EVENT_FIELDS = [c for c in EVENT_COLUMNS if c not in ('content_text', 'source_payload')]


# --------------------------------------------------------------------------
# Roles and the state machine
# --------------------------------------------------------------------------

ROLES = ('admin', 'approver', 'writer', 'viewer')

ROLE_LABELS = {
    'admin': 'Admin',
    'approver': 'Approver',
    'writer': 'Writer',
    'viewer': 'Viewer',
}

STAGE_LABELS = {
    'KEYWORDS_READY': 'Keywords ready',
    'DRAFT_RECEIVED': 'Waiting on approval',
    'APPROVED': 'Approved',
    'ALLOCATED': 'With the writer',
    'SUBMITTED': 'Waiting on review',
    'REWRITE_REQUESTED': 'Rewrite requested',
    'COMPLETED': 'Completed',
    'REJECTED': 'Rejected',
    'DELETED': 'Cancelled',
}

# Colour family each stage uses in the UI.
STAGE_TONES = {
    'KEYWORDS_READY': 'neutral',
    'DRAFT_RECEIVED': 'warn',
    'APPROVED': 'accent',
    'ALLOCATED': 'accent',
    'SUBMITTED': 'warn',
    'REWRITE_REQUESTED': 'danger',
    'COMPLETED': 'good',
    'REJECTED': 'danger',
    'DELETED': 'neutral',
}

TERMINAL_STAGES = ('COMPLETED', 'REJECTED', 'DELETED')
APPROVER_STAGES = ('DRAFT_RECEIVED', 'SUBMITTED')
WRITER_STAGES = ('ALLOCATED', 'REWRITE_REQUESTED')

ALLOWED_NEXT = {
    None: {'KEYWORDS_READY', 'DRAFT_RECEIVED'},
    'KEYWORDS_READY': {'DRAFT_RECEIVED', 'DELETED'},
    'DRAFT_RECEIVED': {'APPROVED', 'REJECTED', 'DELETED'},
    'APPROVED': {'ALLOCATED', 'DELETED'},
    'ALLOCATED': {'SUBMITTED', 'DELETED'},
    'SUBMITTED': {'COMPLETED', 'REWRITE_REQUESTED', 'DELETED'},
    'REWRITE_REQUESTED': {'SUBMITTED', 'DELETED'},
    'COMPLETED': set(),
    'REJECTED': set(),
    'DELETED': set(),
}


class WorkflowError(Exception):
    """A refused transition. Carries a message meant for the person."""


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, row):
        self.id = int(row['user_id'])
        self.username = row.get('username') or row.get('email') or ''
        self.email = (row.get('email') or '').lower()
        self.role = row.get('role') or 'viewer'
        self.active = bool(row.get('is_active', True))
        self.created_at = row.get('created_at')

    @property
    def is_active(self):
        return self.active

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role.title())

    @property
    def initials(self):
        parts = [p for p in self.username.replace('.', ' ').split() if p]
        return ''.join(p[0] for p in parts[:2]).upper() or self.email[:2].upper()

    def is_admin(self):
        return self.role == 'admin'

    def can_approve(self):
        """Decides on drafts and submissions. This is Vivek."""
        return self.role in ('admin', 'approver')

    def can_write(self):
        """Can be allocated content to rewrite. This is Kirti."""
        return self.role in ('admin', 'approver', 'writer')


class Item:
    """One piece of content, folded from its event history (oldest first)."""

    CARRY_FORWARD = (
        'category', 'assignee_user_id', 'assignee_email', 'content_text',
        'content_url', 'word_count', 'search_keywords', 'search_volume',
        'source_row_id', 'source_payload',
    )

    def __init__(self, events):
        events = sorted(events, key=lambda e: (e.get('timestamp') or datetime.min, e.get('event_id') or ''))
        self.history = events
        first, last = events[0], events[-1]

        self.unique_key = last['unique_key']
        self.stage = last['action']
        self.created_at = first.get('timestamp')
        self.updated_at = last.get('timestamp')
        self.revision_number = max((e.get('revision_number') or 0) for e in events)
        self.last_comment = last.get('comment') or ''
        self.last_actor_email = last.get('actor_email') or ''
        # Filled in by the store from AI_Content_Queue. The brief lives there,
        # not in the workflow table, so it stays true if the automation edits it.
        self.seed = {}

        carried = {}
        for event in events:
            for field in self.CARRY_FORWARD:
                value = event.get(field)
                if value not in (None, ''):
                    carried[field] = value
        for field in self.CARRY_FORWARD:
            setattr(self, field, carried.get(field))

    @property
    def stage_label(self):
        return STAGE_LABELS.get(self.stage, self.stage)

    @property
    def tone(self):
        return STAGE_TONES.get(self.stage, 'neutral')

    @property
    def is_terminal(self):
        return self.stage in TERMINAL_STAGES

    @property
    def ai_fields(self):
        """Whatever extra columns the AI table carried, ready to render."""
        if not self.source_payload:
            return []
        try:
            payload = json.loads(self.source_payload)
        except ValueError:
            return []
        return [(str(k), v) for k, v in payload.items() if v not in (None, '')]

    def awaiting_approver(self):
        return self.stage in APPROVER_STAGES

    def awaiting_writer(self, user=None):
        if self.stage not in WRITER_STAGES:
            return False
        return user is None or self.assignee_user_id == user.id

    def needs(self, user):
        """Is this item sitting on this person's desk right now?"""
        if user.can_approve() and self.awaiting_approver():
            return True
        return self.awaiting_writer(user)


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------

class Store:
    def __init__(self, app):
        self.project = app.config['BIGQUERY_PROJECT']
        self.dataset = app.config['BIGQUERY_DATASET']
        self.users_table = app.config['USERS_TABLE']
        self.workflow_table = app.config['WORKFLOW_TABLE']
        self.seed_table = app.config['SEED_TABLE']
        self.ai_source_table = app.config['AI_SOURCE_TABLE']
        self.ai_status_column = app.config['AI_STATUS_COLUMN']
        self.ai_key_column = app.config['AI_KEY_COLUMN']
        self.ai_column_map = app.config['AI_COLUMN_MAP']
        self._client = None

    # -- plumbing ----------------------------------------------------------

    def client(self):
        if self._client is None:
            raw = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if raw:
                self._client = bigquery.Client.from_service_account_info(
                    json.loads(raw), project=self.project)
            else:
                self._client = bigquery.Client(project=self.project)
        return self._client

    def ref(self, table):
        return f'`{self.project}.{self.dataset}.{table}`'

    @staticmethod
    def _scalar(name, value, bq_type=None):
        if bq_type is None:
            if isinstance(value, bool):
                bq_type = 'BOOL'
            elif isinstance(value, int):
                bq_type = 'INT64'
            elif isinstance(value, float):
                bq_type = 'FLOAT64'
            elif isinstance(value, datetime):
                bq_type = 'DATETIME'
            else:
                bq_type = 'STRING'
        return bigquery.ScalarQueryParameter(name, bq_type, value)

    def run(self, sql, params=None):
        job_config = bigquery.QueryJobConfig(query_parameters=params or [])
        result = self.client().query(sql, job_config=job_config).result()
        return [{str(k).lower(): v for k, v in row.items()} for row in result]

    def query(self, sql, **params):
        return self.run(sql, [self._scalar(k, v) for k, v in params.items()])

    def insert(self, table, rows, columns):
        """One INSERT statement for all rows, so a multi-row write is atomic."""
        rows = [r for r in rows if r]
        if not rows:
            return
        used = [c for c in columns if any(c in row for row in rows)]
        tuples, params = [], []
        for i, row in enumerate(rows):
            names = []
            for column in used:
                name = f'v{i}_{column}'
                names.append(f'@{name}')
                params.append(self._scalar(name, row.get(column), columns[column]))
            tuples.append('(' + ', '.join(names) + ')')
        sql = (f'INSERT INTO {self.ref(table)} ({", ".join(used)}) '
               f'VALUES {", ".join(tuples)}')
        self.run(sql, params)

    # -- users -------------------------------------------------------------

    def _latest_users(self, where='', **params):
        sql = f'''
            SELECT * EXCEPT(row_rank) FROM (
              SELECT *, ROW_NUMBER() OVER (
                PARTITION BY user_id ORDER BY updated_at DESC
              ) AS row_rank
              FROM {self.ref(self.users_table)}
              {where}
            )
            WHERE row_rank = 1
            ORDER BY username
        '''
        return self.query(sql, **params)

    def user(self, user_id):
        rows = self._latest_users('WHERE user_id = @user_id', user_id=int(user_id))
        rows = [r for r in rows if r.get('is_active', True)]
        return User(rows[0]) if rows else None

    def user_by_email(self, email, active_only=True):
        rows = self._latest_users('WHERE LOWER(email) = @email', email=(email or '').lower())
        if active_only:
            rows = [r for r in rows if r.get('is_active', True)]
        # An email could have been added twice under different user_ids; the
        # most recently touched row is the one that counts.
        rows.sort(key=lambda r: r.get('updated_at') or datetime.min, reverse=True)
        return User(rows[0]) if rows else None

    def users(self, active_only=False):
        rows = self._latest_users()
        if active_only:
            rows = [r for r in rows if r.get('is_active', True)]
        return [User(r) for r in rows]

    def writers(self):
        return [u for u in self.users(active_only=True) if u.can_write()]

    def save_user(self, username, email, role, is_active=True, user_id=None, created_at=None):
        if role not in ROLES:
            raise WorkflowError(f'Unknown role: {role}')
        email = (email or '').strip().lower()
        if not email:
            raise WorkflowError('An email address is required.')
        now = now_ist()
        self.insert(self.users_table, [{
            'user_id': int(user_id) if user_id else int(datetime.now(IST).timestamp() * 1000),
            'username': (username or email.split('@')[0]).strip(),
            'email': email,
            'password_hash': '',
            'role': role,
            'is_active': bool(is_active),
            'created_at': created_at or now,
            'updated_at': now,
        }], USER_COLUMNS)

    def set_user_active(self, user_id, active):
        rows = self._latest_users('WHERE user_id = @user_id', user_id=int(user_id))
        if not rows:
            raise WorkflowError('No such user.')
        row = rows[0]
        self.save_user(row.get('username'), row.get('email'), row.get('role'),
                       is_active=active, user_id=row['user_id'],
                       created_at=row.get('created_at'))

    # -- reading the workflow ----------------------------------------------

    def _events(self, unique_key=None, light=False):
        fields = ', '.join(LIGHT_EVENT_FIELDS) if light else '*'
        where = 'WHERE unique_key = @unique_key' if unique_key else ''
        sql = (f'SELECT {fields} FROM {self.ref(self.workflow_table)} {where} '
               f'ORDER BY timestamp ASC, event_id ASC')
        return self.query(sql, **({'unique_key': unique_key} if unique_key else {}))

    def items(self):
        """Every item, newest activity first. Folded without the heavy fields."""
        grouped = {}
        for event in self._events(light=True):
            grouped.setdefault(event['unique_key'], []).append(event)
        items = [Item(events) for events in grouped.values()]
        items.sort(key=lambda i: i.updated_at or datetime.min, reverse=True)
        return self.attach_seeds(items)

    def item(self, unique_key):
        events = self._events(unique_key)
        if not events:
            return None
        return self.attach_seeds([Item(events)])[0]

    def counts(self, user):
        items = self.items()
        return items, {
            'needs_you': sum(i.needs(user) for i in items),
            'approvals': sum(i.awaiting_approver() for i in items),
            'writing': sum(i.stage in WRITER_STAGES for i in items),
            'open': sum(not i.is_terminal for i in items),
            'completed': sum(i.stage == 'COMPLETED' for i in items),
            'closed': sum(i.stage in ('REJECTED', 'DELETED') for i in items),
            'waiting_intake': len(self.pending_seeds()),
        }

    # -- the brief the AI wrote ---------------------------------------------

    def seeds(self, keys=None):
        """Rows from AI_Content_Queue, keyed by unique_key."""
        if not self.ai_source_table:
            return {}
        key = self.ai_key_column
        where, params = '', []
        if keys is not None:
            keys = sorted({k for k in keys if k})
            if not keys:
                return {}
            where = f'WHERE CAST({key} AS STRING) IN UNNEST(@keys)'
            params = [bigquery.ArrayQueryParameter('keys', 'STRING', keys)]
        try:
            rows = self.run(f'SELECT * FROM `{self.ai_source_table}` {where}', params)
        except Exception:
            # No seed table yet is not a reason to break a page.
            return {}
        return {str(row.get(key.lower()) or ''): row for row in rows}

    def attach_seeds(self, items):
        lookup = self.seeds([i.unique_key for i in items])
        for item in items:
            item.seed = lookup.get(item.unique_key, {})
        return items

    def pending_seeds(self):
        """Ready rows the workflow has not picked up yet."""
        if not self.ai_source_table:
            return []
        key, status = self.ai_key_column, self.ai_status_column
        sql = f'''
            SELECT * FROM `{self.ai_source_table}`
            WHERE COALESCE({status}, 'READY') = 'READY'
              AND CAST({key} AS STRING) NOT IN (
                SELECT DISTINCT unique_key FROM {self.ref(self.workflow_table)})
            ORDER BY generated_at DESC
        '''
        try:
            return self.run(sql)
        except Exception:
            return []

    # -- writing to the workflow -------------------------------------------

    def _event(self, unique_key, action, actor=None, assignee=None, **fields):
        row = {
            'event_id': uuid.uuid4().hex,
            'timestamp': now_ist(),
            'unique_key': unique_key,
            'action': action,
        }
        if actor is not None:
            row['actor_user_id'] = actor.id
            row['actor_email'] = actor.email
        if assignee is not None:
            row['assignee_user_id'] = assignee.id
            row['assignee_email'] = assignee.email
        row.update({k: v for k, v in fields.items() if v not in (None, '')})
        return row

    def _guard(self, item, action):
        current = item.stage if item else None
        if action not in ALLOWED_NEXT.get(current, set()):
            if item and item.is_terminal:
                raise WorkflowError('This request is closed. Nothing more can happen to it.')
            raise WorkflowError(
                f'Cannot go from "{STAGE_LABELS.get(current, "nothing")}" to '
                f'"{STAGE_LABELS.get(action, action)}".')

    def append(self, rows):
        self.insert(self.workflow_table, rows, EVENT_COLUMNS)

    # -- intake (the AI's side) --------------------------------------------

    def record_keywords(self, unique_key, category=None, search_keywords=None,
                        search_volume=None, source_row_id=None, source_payload=None):
        item = self.item(unique_key)
        self._guard(item, 'KEYWORDS_READY')
        self.append([self._event(
            unique_key, 'KEYWORDS_READY', category=category,
            search_keywords=search_keywords, search_volume=search_volume,
            source_row_id=source_row_id, source_payload=source_payload)])

    def record_draft(self, unique_key, category=None, content_text=None, content_url=None,
                     word_count=None, search_keywords=None, search_volume=None,
                     source_row_id=None, source_payload=None):
        item = self.item(unique_key)
        self._guard(item, 'DRAFT_RECEIVED')
        if not (content_text or content_url):
            raise WorkflowError('A draft needs either its text or a link to it.')
        self.append([self._event(
            unique_key, 'DRAFT_RECEIVED', category=category, content_text=content_text,
            content_url=content_url, word_count=word_count, search_keywords=search_keywords,
            search_volume=search_volume, source_row_id=source_row_id,
            source_payload=source_payload)])

    def sync_ai_drafts(self, limit=500):
        """Pull rows the AI has written that this app has not seen yet.

        The AI table's shape is not known in advance, so only the key column is
        assumed. Mapped columns fill the workflow fields; every other column is
        kept verbatim in source_payload and shown on the item page.
        """
        if not self.ai_source_table:
            raise WorkflowError('No AI source table is configured yet. Set AI_SOURCE_TABLE.')
        rows = self.pending_seeds()[:int(limit)]
        key = self.ai_key_column
        mapping = {k: v.lower() for k, v in self.ai_column_map.items()}
        events, skipped = [], []
        for row in rows:
            unique_key = str(row.get(key.lower()) or '').strip()
            if not unique_key:
                continue
            picked = {field: row.get(column) for field, column in mapping.items()}
            text = picked.get('content_text')
            url = picked.get('content_url')
            if not text and not url:
                skipped.append(unique_key)
                continue
            events.append(self._event(
                unique_key, 'DRAFT_RECEIVED',
                category=picked.get('category'),
                content_text=text,
                content_url=url,
                word_count=_as_int(picked.get('word_count')),
                search_keywords=picked.get('search_keywords'),
                search_volume=_as_int(picked.get('search_volume')),
                source_row_id=unique_key,
                source_payload=json.dumps(row, default=str, ensure_ascii=False)))
        # Two rows for the same key in one batch would both pass the NOT IN
        # check, so keep the first and let the next sync pick up the rest.
        deduped, seen = [], set()
        for event in events:
            if event['unique_key'] in seen:
                continue
            seen.add(event['unique_key'])
            deduped.append(event)
        self.append(deduped)
        return {'added': len(deduped), 'skipped': skipped}

    # -- approver actions ---------------------------------------------------

    def approve(self, unique_key, approver, assignee, comment=None):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'APPROVED')
        if not assignee or not assignee.can_write():
            raise WorkflowError('Pick who should rewrite this.')
        # Both rows in one statement: an approval never lands without its
        # allocation, so an item cannot get stranded between the two.
        self.append([
            self._event(unique_key, 'APPROVED', actor=approver,
                        category=item.category, comment=comment),
            self._event(unique_key, 'ALLOCATED', actor=approver,
                        category=item.category, assignee=assignee),
        ])

    def reject(self, unique_key, approver, comment=None):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'REJECTED')
        self.append([self._event(unique_key, 'REJECTED', actor=approver,
                                 category=item.category, comment=comment)])

    def request_rewrite(self, unique_key, approver, comment):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'REWRITE_REQUESTED')
        if not (comment or '').strip():
            raise WorkflowError('Say what needs changing before sending it back.')
        self.append([self._event(
            unique_key, 'REWRITE_REQUESTED', actor=approver, category=item.category,
            comment=comment.strip(), assignee_user_id=item.assignee_user_id,
            assignee_email=item.assignee_email)])

    def complete(self, unique_key, approver, comment=None):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'COMPLETED')
        self.append([self._event(unique_key, 'COMPLETED', actor=approver,
                                 category=item.category, comment=comment)])

    def cancel(self, unique_key, actor, comment=None):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'DELETED')
        self.append([self._event(unique_key, 'DELETED', actor=actor,
                                 category=item.category, comment=comment)])

    # -- writer action ------------------------------------------------------

    def submit(self, unique_key, writer, content_text=None, content_url=None, comment=None):
        item = self.item(unique_key)
        if not item:
            raise WorkflowError('No such content.')
        self._guard(item, 'SUBMITTED')
        if item.assignee_user_id != writer.id and not writer.is_admin():
            raise WorkflowError('This one is allocated to someone else.')
        text = (content_text or '').strip()
        url = (content_url or '').strip()
        if not text and not url:
            raise WorkflowError('Add the rewritten content, or a link to it, before submitting.')
        self.append([self._event(
            unique_key, 'SUBMITTED', actor=writer, category=item.category,
            content_text=text, content_url=url, comment=comment,
            revision_number=item.revision_number + 1,
            word_count=len(text.split()) if text else item.word_count,
            assignee_user_id=item.assignee_user_id,
            assignee_email=item.assignee_email)])


def _as_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
