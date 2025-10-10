from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Task, TaskLog
from app.forms import LoginForm, CreateTaskForm, TaskActionForm, AuditForm, CreateUserForm, UpdateTaskForm
from datetime import datetime
from sqlalchemy import or_, and_
import os
import re

main_bp = Blueprint('main', __name__)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_google_sheet_url(url):
    """Validate Google Sheets URL format"""
    pattern = r'https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9-_]+'
    return bool(re.match(pattern, url))


@main_bp.route('/')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact admin.', 'danger')
                return redirect(url_for('main.login'))

            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')

            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html', form=form)


@main_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - shows tasks based on user role"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', None)
    search_query = request.args.get('search', '').strip()

    # Validate per_page to prevent abuse
    if per_page not in [10, 25, 50, 100]:
        per_page = 10

    # Build query based on role
    if current_user.role == 'admin' or current_user.role == 'manager':
        # Managers and admins see all tasks
        query = Task.query
    elif current_user.role == 'auditor':
        # Auditors see tasks assigned to them for audit
        query = Task.query.filter_by(auditor_id=current_user.id)
    else:
        # Assignees see their own tasks
        query = Task.query.filter_by(assigned_to_id=current_user.id)

    # Apply search filter
    if search_query:
        query = query.filter(
            or_(
                Task.ticket_id.ilike(f'%{search_query}%'),
                Task.title.ilike(f'%{search_query}%'),
                Task.description.ilike(f'%{search_query}%')
            )
        )

    # Apply status filter
    if status_filter:
        query = query.filter_by(status=status_filter)

    # Order by most recent first
    query = query.order_by(Task.updated_at.desc())

    # Paginate
    tasks = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get statistics
    stats = get_dashboard_stats()

    return render_template('dashboard.html', tasks=tasks, stats=stats, status_filter=status_filter, search_query=search_query)


@main_bp.route('/create-task', methods=['GET', 'POST'])
@login_required
def create_task():
    """Create a new task"""
    if current_user.role not in ['manager', 'admin']:
        flash('Only managers and admins can create tasks.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = CreateTaskForm()

    # Populate assignee choices
    assignees = User.query.filter_by(is_active=True).all()
    form.assigned_to.choices = [(u.id, f"{u.username} ({u.role})") for u in assignees]

    if form.validate_on_submit():
        # Collect content-specific data
        content_data = {
            'category_type': form.category_type.data,
            'keyword': form.keyword.data,
            'search_volume': form.search_volume.data,
            'meta_description': form.meta_description.data,
            'faqs': form.faqs.data,
            'internal_linking_keywords': form.internal_linking_keywords.data,
            'internal_link_urls': form.internal_link_urls.data,
        }

        # Add category-specific fields if Category type
        if form.category_type.data == 'Category':
            content_data.update({
                'page_type': form.page_type.data,
                'category_name': form.category_name.data,
                'url': form.url.data,
                'page_sv': form.page_sv.data,
                'gemstone_category': form.gemstone_category.data,
                'type': form.type_field.data,
                'recommended_density': form.recommended_density.data,
                'word_count': form.word_count.data,
                'title': form.title_field.data,
                'astro_non_astro': form.astro_non_astro.data,
                'internal_linking_keywords_sv': form.internal_linking_keywords_sv.data,
            })

        # Add blog-specific fields if Blog type
        elif form.category_type.data == 'Blog':
            content_data.update({
                'blog_url': form.blog_url.data,
                'keyword_sv': form.keyword_sv.data,
                'h1': form.h1.data,
                'meta_title': form.meta_title.data,
                'content_structure_recommended': form.content_structure_recommended.data,
            })

        task = Task(
            ticket_id=Task.generate_ticket_id(),
            title=form.title.data,
            description=form.description.data,
            created_by_id=current_user.id,
            assigned_to_id=form.assigned_to.data,
            plan_date=form.plan_date.data,
            status='assigned',
            content_data=content_data
        )

        db.session.add(task)
        db.session.commit()

        # Log task creation with detailed field tracking
        assignee_user = User.query.get(form.assigned_to.data)
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='Task created',
            field_name='assigned_to',
            previous_value=None,
            new_value=assignee_user.username,
            new_status='assigned',
            notes=f'Task assigned to {task.assignee.username}'
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Task "{task.title}" created successfully!', 'success')
        return redirect(url_for('main.task_detail', task_id=task.id))

    return render_template('create_task.html', form=form)


@main_bp.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    """Task detail view with action handling"""
    task = Task.query.get_or_404(task_id)

    # Check permissions
    can_view = (
        current_user.is_manager() or
        task.assigned_to_id == current_user.id or
        task.auditor_id == current_user.id or
        task.created_by_id == current_user.id
    )

    if not can_view:
        flash('You do not have permission to view this task.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Handle POST actions
    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes', '')

        try:
            if action == 'start':
                if task.assigned_to_id != current_user.id:
                    flash('Only the assignee can start this task.', 'danger')
                elif task.can_transition_to('in_progress'):
                    task.transition_to('in_progress', current_user, notes)
                    db.session.commit()
                    flash('Task started!', 'success')

            elif action == 'complete':
                if task.assigned_to_id != current_user.id:
                    flash('Only the assignee can complete this task.', 'danger')
                elif task.can_transition_to('completed'):
                    # Handle document submission
                    submission_type = request.form.get('submission_type')

                    if not submission_type:
                        flash('Please submit your completed work (document or sheet link).', 'danger')
                        return redirect(url_for('main.task_detail', task_id=task_id))

                    if submission_type == 'document':
                        # Handle file upload
                        if 'document_file' not in request.files:
                            flash('No file uploaded.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        file = request.files['document_file']
                        if file.filename == '':
                            flash('No file selected.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        if file and allowed_file(file.filename):
                            # Check file size
                            file.seek(0, os.SEEK_END)
                            file_length = file.tell()
                            file.seek(0, 0)

                            if file_length > MAX_FILE_SIZE:
                                flash('File size exceeds 10MB limit.', 'danger')
                                return redirect(url_for('main.task_detail', task_id=task_id))

                            # Create uploads directory if it doesn't exist
                            if not os.path.exists(UPLOAD_FOLDER):
                                os.makedirs(UPLOAD_FOLDER)

                            # Save file
                            filename = secure_filename(file.filename)
                            unique_filename = f"{task.ticket_id}_{filename}"
                            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                            file.save(filepath)

                            # Update task
                            task.submission_type = 'document'
                            task.document_file_path = filepath
                            task.document_file_name = filename

                            # Log document upload
                            doc_log = TaskLog(
                                task_id=task.id,
                                user_id=current_user.id,
                                action='Document uploaded',
                                field_name='document_file',
                                previous_value=None,
                                new_value=filename,
                                notes='Task completion document uploaded'
                            )
                            db.session.add(doc_log)
                        else:
                            flash('Invalid file type. Only PDF, DOC, DOCX allowed.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                    elif submission_type == 'sheet_link':
                        # Handle Google Sheet URL
                        sheet_url = request.form.get('sheet_url', '').strip()

                        if not sheet_url:
                            flash('Please provide a Google Sheet URL.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        if not validate_google_sheet_url(sheet_url):
                            flash('Invalid Google Sheets URL format.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        # Update task
                        task.submission_type = 'sheet_link'
                        task.sheet_url = sheet_url

                        # Log sheet URL submission
                        sheet_log = TaskLog(
                            task_id=task.id,
                            user_id=current_user.id,
                            action='Google Sheet link submitted',
                            field_name='sheet_url',
                            previous_value=None,
                            new_value=sheet_url,
                            notes='Task completion sheet link provided'
                        )
                        db.session.add(sheet_log)

                    # Proceed with task completion
                    task.transition_to('completed', current_user, notes)
                    # Auto-transition to under_audit
                    if task.can_transition_to('under_audit'):
                        task.transition_to('under_audit', current_user, 'Auto-assigned for audit')
                    db.session.commit()
                    flash('Task completed and sent for audit!', 'success')

            elif action == 'cancel':
                if not current_user.is_manager():
                    flash('Only managers can cancel tasks.', 'danger')
                elif task.can_transition_to('cancelled'):
                    task.transition_to('cancelled', current_user, notes)
                    db.session.commit()
                    flash('Task cancelled.', 'info')

            elif action == 'audit_pass':
                if task.auditor_id != current_user.id and not current_user.is_manager():
                    flash('Only the assigned auditor can audit this task.', 'danger')
                elif task.can_transition_to('audit_passed'):
                    task.transition_to('audit_passed', current_user, notes)
                    db.session.commit()
                    flash('Audit passed!', 'success')

            elif action == 'audit_fail':
                if task.auditor_id != current_user.id and not current_user.is_manager():
                    flash('Only the assigned auditor can audit this task.', 'danger')
                elif task.can_transition_to('audit_failed'):
                    # Get new completion date if provided
                    new_date_str = request.form.get('new_completion_date')
                    if new_date_str:
                        from datetime import datetime
                        old_plan_date = task.plan_date
                        task.plan_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()

                        # Log plan date change
                        date_log = TaskLog(
                            task_id=task.id,
                            user_id=current_user.id,
                            action='Plan date updated',
                            field_name='plan_date',
                            previous_value=old_plan_date.strftime('%Y-%m-%d') if old_plan_date else None,
                            new_value=task.plan_date.strftime('%Y-%m-%d'),
                            notes='New deadline set by auditor after audit failure'
                        )
                        db.session.add(date_log)

                    task.transition_to('audit_failed', current_user, notes)
                    # Auto-transition back to in_progress
                    if task.can_transition_to('in_progress'):
                        task.transition_to('in_progress', current_user, 'Returned for revision')
                    db.session.commit()
                    flash('Audit failed. Task returned for revision.', 'warning')

        except ValueError as e:
            flash(str(e), 'danger')

        return redirect(url_for('main.task_detail', task_id=task_id))

    # Get task logs
    logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.desc()).all()

    # Determine available actions
    actions = get_available_actions(task)

    return render_template('task_detail.html', task=task, logs=logs, actions=actions)


@main_bp.route('/audit-dashboard')
@login_required
def audit_dashboard():
    """Dashboard for auditors"""
    if not current_user.is_auditor():
        flash('Access denied. Auditors only.', 'danger')
        return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get tasks pending audit
    tasks = Task.query.filter_by(
        auditor_id=current_user.id,
        status='under_audit'
    ).order_by(Task.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Get audit statistics
    total_audits = Task.query.filter_by(auditor_id=current_user.id).count()
    pending_audits = Task.query.filter_by(auditor_id=current_user.id, status='under_audit').count()
    passed_audits = Task.query.filter_by(auditor_id=current_user.id, status='audit_passed').count()
    failed_audits = Task.query.filter_by(auditor_id=current_user.id, status='audit_failed').count()

    stats = {
        'total': total_audits,
        'pending': pending_audits,
        'passed': passed_audits,
        'failed': failed_audits
    }

    return render_template('audit_dashboard.html', tasks=tasks, stats=stats)


@main_bp.route('/users')
@login_required
def users():
    """User management page (Admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('main.dashboard'))

    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=all_users)


@main_bp.route('/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create new user (Admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('main.dashboard'))

    form = CreateUserForm()

    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'danger')
            return render_template('create_user.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return render_template('create_user.html', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=True
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('main.users'))

    return render_template('create_user.html', form=form)


@main_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (Admin only)"""
    if not current_user.is_admin():
        abort(403)

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
        return redirect(url_for('main.users'))

    user.is_active = not user.is_active
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')

    return redirect(url_for('main.users'))


@main_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (Admin only)"""
    if not current_user.is_admin():
        abort(403)

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('main.users'))

    # Check if user has any tasks
    created_tasks_count = Task.query.filter_by(created_by_id=user.id).count()
    assigned_tasks_count = Task.query.filter_by(assigned_to_id=user.id).count()

    if created_tasks_count > 0 or assigned_tasks_count > 0:
        flash(f'Cannot delete user {user.username}. User has {created_tasks_count} created tasks and {assigned_tasks_count} assigned tasks.', 'danger')
        return redirect(url_for('main.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'User {username} has been deleted successfully.', 'success')
    return redirect(url_for('main.users'))


@main_bp.route('/task/<int:task_id>/download')
@login_required
def download_document(task_id):
    """Download task document"""
    task = Task.query.get_or_404(task_id)

    # Check permissions
    can_download = (
        current_user.is_manager() or
        task.assigned_to_id == current_user.id or
        task.auditor_id == current_user.id or
        task.created_by_id == current_user.id
    )

    if not can_download:
        abort(403)

    if not task.document_file_path:
        abort(404)

    directory = os.path.dirname(task.document_file_path)
    filename = os.path.basename(task.document_file_path)

    return send_from_directory(directory, filename, as_attachment=True, download_name=task.document_file_name)


def get_dashboard_stats():
    """Get dashboard statistics based on user role"""
    if current_user.role in ['admin', 'manager']:
        # All tasks statistics
        total = Task.query.count()
        assigned = Task.query.filter_by(status='assigned').count()
        in_progress = Task.query.filter_by(status='in_progress').count()
        under_audit = Task.query.filter_by(status='under_audit').count()
        completed = Task.query.filter_by(status='audit_passed').count()
    else:
        # User's tasks statistics
        total = Task.query.filter_by(assigned_to_id=current_user.id).count()
        assigned = Task.query.filter_by(assigned_to_id=current_user.id, status='assigned').count()
        in_progress = Task.query.filter_by(assigned_to_id=current_user.id, status='in_progress').count()
        under_audit = Task.query.filter_by(assigned_to_id=current_user.id, status='under_audit').count()
        completed = Task.query.filter_by(assigned_to_id=current_user.id, status='audit_passed').count()

    return {
        'total': total,
        'assigned': assigned,
        'in_progress': in_progress,
        'under_audit': under_audit,
        'completed': completed
    }


def get_available_actions(task):
    """Determine which actions are available for the current user and task"""
    actions = []

    # Start task
    if (task.status == 'assigned' and task.assigned_to_id == current_user.id):
        actions.append({'action': 'start', 'label': 'Start Task', 'class': 'btn-primary'})

    # Complete task
    if (task.status == 'in_progress' and task.assigned_to_id == current_user.id):
        actions.append({'action': 'complete', 'label': 'Complete Task', 'class': 'btn-success'})

    # Audit actions
    if (task.status == 'under_audit' and
        (task.auditor_id == current_user.id or current_user.is_manager())):
        actions.append({'action': 'audit_pass', 'label': 'Pass Audit', 'class': 'btn-success'})
        actions.append({'action': 'audit_fail', 'label': 'Fail Audit', 'class': 'btn-danger'})

    # Cancel task (managers only)
    if (current_user.is_manager() and task.status not in ['audit_passed', 'cancelled']):
        actions.append({'action': 'cancel', 'label': 'Cancel Task', 'class': 'btn-secondary'})

    return actions
