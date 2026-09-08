import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from app.forms import LoginForm, CreateUserForm
from app import csrf, oauth


main_bp = Blueprint('main', __name__)


def store():
    return current_app.extensions['bigquery_store']


def approver_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_approver():
            return 'Forbidden', 403
        return view(*args, **kwargs)
    return wrapped


def require_api_key(view):
    """Shared-secret auth for machine-to-machine webhooks (the external
    keyword-search / content-writer API), independent of the human login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = os.environ.get('WORKFLOW_API_KEY')
        if not expected:
            return jsonify(error='WORKFLOW_API_KEY is not configured on the server'), 503
        provided = request.headers.get('X-API-Key', '')
        if provided != expected:
            return jsonify(error='invalid or missing X-API-Key header'), 401
        return view(*args, **kwargs)
    return wrapped


@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard' if current_user.is_authenticated else 'main.login'))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = store().user(username=form.username.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form, google_sso_enabled=current_app.config['GOOGLE_SSO_ENABLED'])


@main_bp.route('/login/google')
def login_google():
    if not current_app.config['GOOGLE_SSO_ENABLED']:
        return 'Google SSO is not configured', 404
    redirect_uri = url_for('main.login_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@main_bp.route('/login/google/callback')
def login_google_callback():
    if not current_app.config['GOOGLE_SSO_ENABLED']:
        return 'Google SSO is not configured', 404
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Google sign-in failed. Please try again.', 'danger')
        return redirect(url_for('main.login'))
    claims = token.get('userinfo') or {}
    email = (claims.get('email') or '').lower()
    email_verified = claims.get('email_verified', True)
    domain = current_app.config['GOOGLE_WORKSPACE_DOMAIN'].lower()
    if not email or not email_verified or not email.endswith(f'@{domain}'):
        flash(f'Only @{domain} Google accounts can sign in here.', 'danger')
        return redirect(url_for('main.login'))
    user = store().user_by_email(email)
    if not user:
        flash(f'No account for {email}. Ask an admin to create one first.', 'danger')
        return redirect(url_for('main.login'))
    login_user(user)
    return redirect(url_for('main.dashboard'))


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    records = store().records(current_user)
    search = request.args.get('search', '').strip().lower()
    if search:
        records = [record for record in records if search in record.unique_key.lower() or search in record.title.lower()]
    # Every metric here is a straight count over `records` (no placeholder/fake values) --
    # a metric with no real computation is worse than not showing it at all.
    metrics = {
        'total_pending': sum(record.status in ('assigned', 'in_progress') for record in records),
        'under_audit': sum(record.status == 'under_audit' for record in records),
        'completed_count': sum(record.status == 'audit_passed' for record in records),
    }
    workflow_items = store().workflow_items()
    workflow_summary = {
        'pending_approval': sum(item.awaiting_approver() for item in workflow_items),
        'my_tasks': sum(item.awaiting_doer(current_user) for item in workflow_items),
        'in_progress': sum(not item.is_terminal for item in workflow_items),
        'completed': sum(item.stage == 'COMPLETED' for item in workflow_items),
    }
    return render_template('dashboard_bigquery.html', records=records, summary_metrics=metrics, search_query=search,
                           tab='all', view_mode='team', is_manager=current_user.is_manager(), current_date=datetime.utcnow().date(),
                           workflow_summary=workflow_summary)


@main_bp.route('/content/<path:unique_key>')
@login_required
def content_detail(unique_key):
    record = store().record(unique_key)
    if not record:
        return 'Content not found', 404
    return render_template('content_detail_bigquery.html', record=record)


@main_bp.route('/content/<path:unique_key>/update', methods=['POST'])
@login_required
def update_content(unique_key):
    record = store().record(unique_key)
    if not record:
        return 'Content not found', 404
    action = request.form.get('action', '').lower()
    approval = {'approve': 'Approved', 'reject': 'Rejected'}.get(action)
    if not approval:
        flash('Unsupported workflow action.', 'danger')
        return redirect(url_for('main.content_detail', unique_key=unique_key))
    target = 'Content_Audit' if record.source_table != 'Content_Audit' else 'Content_Review_and_Approval'
    store().append_event(target, record, current_user, approval=approval, suggestion=request.form.get('suggestion', '').strip())
    flash(f'{approval} event appended to BigQuery.', 'success')
    return redirect(url_for('main.content_detail', unique_key=unique_key))


@main_bp.route('/create-content', methods=['GET', 'POST'])
@login_required
def create_content():
    if not current_user.is_manager():
        return 'Forbidden', 403
    if request.method == 'POST':
        unique_key = request.form.get('unique_key', '').strip()
        if not unique_key:
            flash('Unique_Key is required.', 'danger')
            return render_template('create_content_bigquery.html')
        values = {key: value for key, value in request.form.items() if key in {
            'primary_key', 'category', 'step_code', 'planned_date', 'search_volume', 'url',
            'gemstone_type', 'tab_content', 'words_count', 'upload_file'
        } and value}
        target = request.form.get('stage', 'Seed_File')
        if target not in ('Seed_File', 'Content_Planning', 'Content_Creation'):
            target = 'Seed_File'
        file = request.files.get('upload')
        if file and file.filename:
            values['upload_file'] = store().upload_file(file)
        record = type('NewRecord', (), {'unique_key': unique_key, 'category': values.get('category', ''), 'plan_date': None,
                                        'content_data': values})()
        store().append_event(target, record, current_user, values=values)
        flash('Content event appended to BigQuery.', 'success')
        return redirect(url_for('main.content_detail', unique_key=unique_key))
    return render_template('create_content_bigquery.html')


@main_bp.route('/users')
@login_required
def users():
    if not current_user.is_admin():
        return 'Forbidden', 403
    return render_template('users_bigquery.html', users=store().users())


@main_bp.route('/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin():
        return 'Forbidden', 403
    form = CreateUserForm()
    if form.validate_on_submit():
        store().create_user(form.username.data, form.email.data, form.password.data, form.role.data)
        flash('User created in BigQuery.', 'success')
        return redirect(url_for('main.users'))
    return render_template('create_user.html', form=form)


@main_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not current_user.is_admin():
        return 'Forbidden', 403
    user = store().user(user_id=user_id)
    if not user:
        return 'User not found', 404
    store().set_user_active(user_id, not user.is_active)
    return redirect(url_for('main.users'))


# ==========================================================================
# Approval workflow: keyword-search + drafting are done by an external API,
# Vivek (approver) approves/allocates/completes/rejects, a doer writes/
# updates content and resubmits until Vivek confirms or the request is
# deleted.
# ==========================================================================

@main_bp.route('/approvals')
@login_required
@approver_required
def approvals():
    items = [item for item in store().workflow_items() if item.awaiting_approver()]
    return render_template('workflow_list.html', items=items, title='Pending Approvals', empty_message='Nothing waiting on your review.')


@main_bp.route('/my-tasks')
@login_required
def my_tasks():
    items = [item for item in store().workflow_items() if item.awaiting_doer(current_user)]
    return render_template('workflow_list.html', items=items, title='My Tasks', empty_message='Nothing currently assigned to you.')


@main_bp.route('/workflow')
@login_required
def workflow_all():
    items = store().workflow_items()
    return render_template('workflow_list.html', items=items, title='All Content Requests', empty_message='No content has entered the approval workflow yet.', show_all=True)


@main_bp.route('/workflow/<path:unique_key>')
@login_required
def workflow_detail(unique_key):
    item = store().workflow_item(unique_key)
    if not item:
        return 'Not found', 404
    assignable_users = store().users() if current_user.is_approver() and item.stage == 'DRAFT_RECEIVED' else []
    return render_template('workflow_detail.html', item=item, assignable_users=assignable_users)


@main_bp.route('/workflow/<path:unique_key>/approve', methods=['POST'])
@login_required
@approver_required
def workflow_approve(unique_key):
    assignee_id = request.form.get('assignee_user_id', type=int)
    assignee = store().user(user_id=assignee_id) if assignee_id else None
    if not assignee:
        flash('Choose who this content should be allocated to.', 'danger')
        return redirect(url_for('main.workflow_detail', unique_key=unique_key))
    try:
        store().approve_and_allocate(unique_key, current_user, assignee, comment=request.form.get('comment', '').strip())
        flash(f'Approved and allocated to {assignee.username}.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.workflow_detail', unique_key=unique_key))


@main_bp.route('/workflow/<path:unique_key>/request-rewrite', methods=['POST'])
@login_required
@approver_required
def workflow_request_rewrite(unique_key):
    try:
        store().request_rewrite(unique_key, current_user, request.form.get('comment', ''))
        flash('Sent back to the doer for a re-write.', 'warning')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.workflow_detail', unique_key=unique_key))


@main_bp.route('/workflow/<path:unique_key>/complete', methods=['POST'])
@login_required
@approver_required
def workflow_complete(unique_key):
    try:
        store().complete_workflow(unique_key, current_user, comment=request.form.get('comment', '').strip())
        flash('Marked as completed.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.workflow_detail', unique_key=unique_key))


@main_bp.route('/workflow/<path:unique_key>/delete', methods=['POST'])
@login_required
@approver_required
def workflow_delete(unique_key):
    try:
        store().delete_workflow_item(unique_key, current_user, comment=request.form.get('comment', '').strip())
        flash('Request deleted; the loop is closed.', 'warning')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.workflow_detail', unique_key=unique_key))


@main_bp.route('/workflow/<path:unique_key>/submit', methods=['POST'])
@login_required
def workflow_submit(unique_key):
    try:
        store().submit_update(unique_key, current_user,
                               content_text=request.form.get('content_text', '').strip(),
                               content_url=request.form.get('content_url', '').strip(),
                               comment=request.form.get('comment', '').strip())
        flash('Submitted for Vivek\'s review.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.workflow_detail', unique_key=unique_key))


# -- webhooks for the external keyword-search / content-writer API --------
#
# Contract (stub -- update if the real API differs):
#   POST /api/workflow/keyword-search
#   POST /api/workflow/content-draft
#   Header: X-API-Key: <WORKFLOW_API_KEY>
#   Body (JSON):
#     unique_key       string, required
#     category         string, optional
#     search_keywords  string, optional (keyword-search endpoint)
#     search_volume    integer, optional (keyword-search endpoint)
#     content_text     string, optional (content-draft endpoint)
#     content_url      string, optional (content-draft endpoint)
#     word_count       integer, optional (content-draft endpoint)

@main_bp.route('/api/workflow/keyword-search', methods=['POST'])
@csrf.exempt
@require_api_key
def api_keyword_search():
    payload = request.get_json(silent=True) or {}
    unique_key = (payload.get('unique_key') or '').strip()
    if not unique_key:
        return jsonify(error='unique_key is required'), 400
    store().ingest_keyword_search(unique_key, payload.get('category'),
                                   payload.get('search_keywords'), payload.get('search_volume'))
    return jsonify(status='ok', unique_key=unique_key, stage='KEYWORDS_READY'), 201


@main_bp.route('/api/workflow/content-draft', methods=['POST'])
@csrf.exempt
@require_api_key
def api_content_draft():
    payload = request.get_json(silent=True) or {}
    unique_key = (payload.get('unique_key') or '').strip()
    if not unique_key:
        return jsonify(error='unique_key is required'), 400
    if not payload.get('content_text') and not payload.get('content_url'):
        return jsonify(error='content_text or content_url is required'), 400
    store().ingest_content_draft(unique_key, payload.get('category'), payload.get('content_text'),
                                  payload.get('content_url'), payload.get('word_count'))
    return jsonify(status='ok', unique_key=unique_key, stage='DRAFT_RECEIVED'), 201