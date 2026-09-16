from functools import wraps

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from app import csrf, oauth
from app.store import ROLES, STAGE_LABELS, WorkflowError

main_bp = Blueprint('main', __name__)


def store():
    return current_app.extensions['store']


def approver_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.can_approve():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def admin_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def api_key_only(view):
    """Shared secret for the AI side. Nothing to do with the human session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get('WORKFLOW_API_KEY')
        if not expected:
            return jsonify(error='WORKFLOW_API_KEY is not set on the server'), 503
        if request.headers.get('X-API-Key', '') != expected:
            return jsonify(error='Missing or wrong X-API-Key header'), 401
        return view(*args, **kwargs)
    return wrapped


def back_to(unique_key):
    return redirect(url_for('main.content', unique_key=unique_key))


@main_bp.app_context_processor
def _header_context():
    if current_app.config['REQUIRE_SIGNIN'] or not current_user.is_authenticated:
        return {'switchable': []}
    try:
        return {'switchable': store().users(active_only=True)}
    except Exception:
        return {'switchable': []}


# ---------------------------------------------------------------------------
# Sign in
# ---------------------------------------------------------------------------

@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))


@main_bp.route('/acting-as', methods=['POST'])
def acting_as():
    """Switch identity while the sign-in gate is off. Does nothing once it is on."""
    if current_app.config['REQUIRE_SIGNIN']:
        abort(404)
    email = (request.form.get('email') or '').strip().lower()
    user = store().user_by_email(email)
    if not user:
        flash('No active person with that email.', 'danger')
    else:
        session['acting_as'] = user.email
        logout_user()
        login_user(user)
    return redirect(request.referrer or url_for('main.dashboard'))


@main_bp.route('/signin')
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    gated = current_app.config['REQUIRE_SIGNIN']
    return render_template('signin.html',
                           gated=gated,
                           sso_ready=current_app.config['SSO_READY'],
                           domain=current_app.config['GOOGLE_WORKSPACE_DOMAIN'])


@main_bp.route('/signin/google')
def signin_google():
    if not current_app.config['SSO_READY']:
        abort(404)
    return oauth.google.authorize_redirect(
        url_for('main.signin_google_callback', _external=True))


@main_bp.route('/signin/google/callback')
def signin_google_callback():
    if not current_app.config['SSO_READY']:
        abort(404)
    domain = current_app.config['GOOGLE_WORKSPACE_DOMAIN']
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Google did not complete the sign-in. Try again.', 'danger')
        return redirect(url_for('main.signin'))

    claims = token.get('userinfo') or {}
    email = (claims.get('email') or '').lower()
    if not email or not claims.get('email_verified', True) or not email.endswith(f'@{domain}'):
        flash(f'Sign in with your @{domain} account.', 'danger')
        return redirect(url_for('main.signin'))

    user = store().user_by_email(email)
    if not user:
        flash(f'{email} has no access yet. An admin needs to add you first.', 'danger')
        return redirect(url_for('main.signin'))

    login_user(user)
    return redirect(url_for('main.dashboard'))


@main_bp.route('/signout')
@login_required
def signout():
    logout_user()
    return redirect(url_for('main.signin'))


# ---------------------------------------------------------------------------
# Dashboard and queue
# ---------------------------------------------------------------------------

SCOPES = (
    ('needs-you', 'Needs you'),
    ('approvals', 'Waiting on approval'),
    ('writing', 'With writers'),
    ('open', 'All open'),
    ('completed', 'Completed'),
    ('closed', 'Closed'),
    ('all', 'Everything'),
)


def in_scope(item, scope, user):
    if scope == 'needs-you':
        return item.needs(user)
    if scope == 'approvals':
        return item.awaiting_approver()
    if scope == 'writing':
        return item.stage in ('ALLOCATED', 'REWRITE_REQUESTED')
    if scope == 'open':
        return not item.is_terminal
    if scope == 'completed':
        return item.stage == 'COMPLETED'
    if scope == 'closed':
        return item.stage in ('REJECTED', 'DELETED')
    return True


@main_bp.route('/dashboard')
@login_required
def dashboard():
    items, counts = store().counts(current_user)
    return render_template(
        'dashboard.html',
        counts=counts,
        mine=[i for i in items if i.needs(current_user)][:8],
        recent=items[:8],
        waiting=store().pending_seeds()[:6],
        ai_ready=current_app.config['AI_READY'])


@main_bp.route('/queue')
@login_required
def queue():
    scope = request.args.get('scope', 'needs-you')
    if scope not in dict(SCOPES):
        scope = 'needs-you'
    search = request.args.get('q', '').strip().lower()

    items, counts = store().counts(current_user)
    scope_counts = {key: sum(in_scope(i, key, current_user) for i in items)
                    for key, _ in SCOPES}

    rows = [i for i in items if in_scope(i, scope, current_user)]
    if search:
        def haystack(item):
            return ' '.join(str(v or '') for v in (
                item.unique_key, item.category, item.assignee_email,
                item.search_keywords, item.stage_label)).lower()
        rows = [i for i in rows if search in haystack(i)]

    return render_template('queue.html', items=rows, scope=scope, scopes=SCOPES,
                           scope_counts=scope_counts, counts=counts, search=search)


# ---------------------------------------------------------------------------
# One piece of content
# ---------------------------------------------------------------------------

@main_bp.route('/content/<path:unique_key>')
@login_required
def content(unique_key):
    item = store().item(unique_key)
    if not item:
        abort(404)
    writers = store().writers() if (current_user.can_approve()
                                    and item.stage == 'DRAFT_RECEIVED') else []
    return render_template('content.html', item=item, writers=writers,
                           stage_labels=STAGE_LABELS)


@main_bp.route('/content/<path:unique_key>/approve', methods=['POST'])
@login_required
@approver_only
def approve(unique_key):
    assignee_id = request.form.get('assignee_user_id', type=int)
    assignee = store().user(assignee_id) if assignee_id else None
    try:
        if not assignee:
            raise WorkflowError('Pick who should rewrite this.')
        store().approve(unique_key, current_user, assignee,
                        comment=request.form.get('comment', '').strip())
        flash(f'Approved and sent to {assignee.username}.', 'good')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


@main_bp.route('/content/<path:unique_key>/reject', methods=['POST'])
@login_required
@approver_only
def reject(unique_key):
    try:
        store().reject(unique_key, current_user,
                       comment=request.form.get('comment', '').strip())
        flash('Rejected. This request is closed.', 'warn')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


@main_bp.route('/content/<path:unique_key>/submit', methods=['POST'])
@login_required
def submit(unique_key):
    try:
        store().submit(unique_key, current_user,
                       content_text=request.form.get('content_text', ''),
                       content_url=request.form.get('content_url', ''),
                       comment=request.form.get('comment', '').strip())
        flash('Submitted for review.', 'good')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


@main_bp.route('/content/<path:unique_key>/rewrite', methods=['POST'])
@login_required
@approver_only
def rewrite(unique_key):
    try:
        store().request_rewrite(unique_key, current_user, request.form.get('comment', ''))
        flash('Sent back to the writer.', 'warn')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


@main_bp.route('/content/<path:unique_key>/complete', methods=['POST'])
@login_required
@approver_only
def complete(unique_key):
    try:
        store().complete(unique_key, current_user,
                         comment=request.form.get('comment', '').strip())
        flash('Completed.', 'good')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


@main_bp.route('/content/<path:unique_key>/cancel', methods=['POST'])
@login_required
@admin_only
def cancel(unique_key):
    try:
        store().cancel(unique_key, current_user,
                       comment=request.form.get('comment', '').strip())
        flash('Cancelled.', 'warn')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return back_to(unique_key)


# ---------------------------------------------------------------------------
# Pulling in what the AI wrote
# ---------------------------------------------------------------------------

@main_bp.route('/sync', methods=['POST'])
@login_required
@approver_only
def sync():
    try:
        result = store().sync_ai_drafts()
    except WorkflowError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as exc:
        flash(f'Could not read the AI table: {exc}', 'danger')
        return redirect(url_for('main.dashboard'))

    if result['added']:
        flash(f'Brought in {result["added"]} new draft(s).', 'good')
    else:
        flash('No new drafts waiting.', 'warn')
    if result['skipped']:
        flash(f'{len(result["skipped"])} row(s) had no content and were left alone.', 'warn')
    return redirect(url_for('main.queue', scope='approvals'))


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

@main_bp.route('/people')
@login_required
@admin_only
def people():
    return render_template('people.html', people=store().users(), roles=ROLES)


@main_bp.route('/people/save', methods=['POST'])
@login_required
@admin_only
def save_person():
    email = request.form.get('email', '').strip().lower()
    domain = current_app.config['GOOGLE_WORKSPACE_DOMAIN']
    try:
        if not email.endswith(f'@{domain}'):
            raise WorkflowError(f'Only @{domain} addresses can be given access.')
        # Same email means same person: keep their id so this is a role change,
        # not a second account that shadows the first.
        existing = store().user_by_email(email, active_only=False)
        store().save_user(
            username=request.form.get('username', '').strip(),
            email=email,
            role=request.form.get('role', 'viewer'),
            is_active=True,
            user_id=existing.id if existing else None,
            created_at=existing.created_at if existing else None)
        flash(f'Saved. {email} is now a {request.form.get("role", "viewer")}.', 'good')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.people'))


@main_bp.route('/people/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_only
def toggle_person(user_id):
    if user_id == current_user.id:
        flash('You cannot switch off your own access.', 'danger')
        return redirect(url_for('main.people'))
    try:
        active = request.form.get('active') == '1'
        store().set_user_active(user_id, active)
        flash('Access updated.', 'good')
    except WorkflowError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('main.people'))


# ---------------------------------------------------------------------------
# Machine endpoints for the AI side
#
#   POST /api/keywords   {"unique_key": "...", "search_keywords": "...", ...}
#   POST /api/drafts     {"unique_key": "...", "content_text": "..."|"content_url": "..."}
#   POST /api/sync       {}   -- pulls everything new out of AI_SOURCE_TABLE
#   Header on all three: X-API-Key: <WORKFLOW_API_KEY>
# ---------------------------------------------------------------------------

@main_bp.route('/api/keywords', methods=['POST'])
@csrf.exempt
@api_key_only
def api_keywords():
    payload = request.get_json(silent=True) or {}
    unique_key = str(payload.get('unique_key') or '').strip()
    if not unique_key:
        return jsonify(error='unique_key is required'), 400
    try:
        store().record_keywords(
            unique_key,
            category=payload.get('category'),
            search_keywords=payload.get('search_keywords'),
            search_volume=payload.get('search_volume'),
            source_row_id=payload.get('source_row_id'))
    except WorkflowError as exc:
        return jsonify(error=str(exc)), 409
    return jsonify(status='ok', unique_key=unique_key, stage='KEYWORDS_READY'), 201


@main_bp.route('/api/drafts', methods=['POST'])
@csrf.exempt
@api_key_only
def api_drafts():
    import json as _json
    payload = request.get_json(silent=True) or {}
    unique_key = str(payload.get('unique_key') or '').strip()
    if not unique_key:
        return jsonify(error='unique_key is required'), 400
    try:
        store().record_draft(
            unique_key,
            category=payload.get('category'),
            content_text=payload.get('content_text'),
            content_url=payload.get('content_url'),
            word_count=payload.get('word_count'),
            search_keywords=payload.get('search_keywords'),
            search_volume=payload.get('search_volume'),
            source_row_id=payload.get('source_row_id'),
            source_payload=_json.dumps(payload, default=str, ensure_ascii=False))
    except WorkflowError as exc:
        return jsonify(error=str(exc)), 409
    return jsonify(status='ok', unique_key=unique_key, stage='DRAFT_RECEIVED'), 201


@main_bp.route('/api/sync', methods=['POST'])
@csrf.exempt
@api_key_only
def api_sync():
    try:
        return jsonify(status='ok', **store().sync_ai_drafts()), 200
    except WorkflowError as exc:
        return jsonify(error=str(exc)), 400
