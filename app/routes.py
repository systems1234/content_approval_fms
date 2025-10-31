from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_from_directory, current_app as app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Task, TaskLog
from app.forms import (LoginForm, CreateTaskForm, TaskActionForm, AuditForm, CreateUserForm,
                        UpdateTaskForm, UpdatePasswordForm)
from datetime import datetime
from sqlalchemy import or_, and_
import os
import re
import traceback

main_bp = Blueprint('main', __name__)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_google_doc_url(url):
    """Validate Google Docs URL format"""
    pattern = r'https://docs\.google\.com/document/d/[a-zA-Z0-9-_]+'
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


def calculate_dashboard_summary_metrics(user_id=None, team_view=False):
    """
    Calculate enhanced summary metrics for dashboard
    Returns: dict with on-time completion rate, pending count, delayed count, last audit passed
    """
    from datetime import datetime as dt

    # Build base query based on view mode
    if team_view:
        # Team-wide metrics
        base_query = Task.query
        completed_query = Task.query.filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
        )
    elif user_id:
        # Personal metrics for specific user
        base_query = Task.query.filter_by(assigned_to_id=user_id)
        completed_query = Task.query.filter_by(assigned_to_id=user_id).filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
        )
    else:
        # Fallback to all tasks
        base_query = Task.query
        completed_query = Task.query.filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
        )

    # Calculate On-Time Completion Rate
    completed_tasks = completed_query.all()
    total_completed = len(completed_tasks)
    on_time_completed = 0

    for task in completed_tasks:
        if task.completed_date and task.plan_date:
            plan_datetime = dt.combine(task.plan_date, dt.min.time())
            if task.completed_date <= plan_datetime:
                on_time_completed += 1

    on_time_rate = round((on_time_completed / total_completed * 100), 1) if total_completed > 0 else 0

    # Calculate Total Pending (assigned/in_progress, not delayed)
    now = dt.utcnow().date()
    pending_query = base_query.filter(
        Task.status.in_(['assigned', 'in_progress'])
    ).filter(
        or_(
            Task.plan_date >= now,
            Task.plan_date.is_(None)
        )
    )
    total_pending = pending_query.count()

    # Calculate Total Delayed (plan_date < today, not completed)
    delayed_query = base_query.filter(
        Task.plan_date < now,
        Task.status.in_(['assigned', 'in_progress', 'under_audit'])
    )
    total_delayed = delayed_query.count()

    # Get Last Audit Passed task
    last_audit_query = base_query.filter_by(status='audit_passed').order_by(Task.audit_date.desc())
    last_audit_passed = last_audit_query.first()

    # Get total under audit
    under_audit_count = base_query.filter_by(status='under_audit').count()

    # Get total completed
    total_completed_count = completed_query.count()

    return {
        'on_time_rate': on_time_rate,
        'on_time_completed': on_time_completed,
        'total_completed': total_completed,
        'total_pending': total_pending,
        'total_delayed': total_delayed,
        'under_audit': under_audit_count,
        'completed_count': total_completed_count,
        'last_audit_passed': last_audit_passed
    }


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with actionable tabs, summary metrics, and date range filtering"""
    try:
        # Get and validate query parameters with safe defaults
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        search_query = request.args.get('search', '').strip() if request.args.get('search') else ''
        tab = request.args.get('tab', 'all') or 'all'
        view_mode = request.args.get('view', 'personal') or 'personal'

        # Date range filters
        start_date_str = request.args.get('start_date', None)
        end_date_str = request.args.get('end_date', None)

        # Validate per_page
        if per_page not in [10, 15, 25, 50, 100]:
            per_page = 15

        # Determine if team view is available and active
        is_manager = current_user.role in ['admin', 'manager']
        show_team_view = is_manager and view_mode == 'team'

        # Build base query based on role and view mode
        if show_team_view:
            # Team-wide view for managers/admins
            query = Task.query
            user_id_filter = None
        elif current_user.role == 'auditor':
            # Auditors see tasks assigned to them for audit
            query = Task.query.filter_by(auditor_id=current_user.id)
            user_id_filter = current_user.id
        else:
            # Assignees see their own tasks (personal view)
            query = Task.query.filter_by(assigned_to_id=current_user.id)
            user_id_filter = current_user.id

        # Parse date range filter (only apply if user provides dates)
        from datetime import datetime as dt, timedelta

        start_date = None
        end_date = None

        # Only parse and apply date filter if user explicitly provides dates
        if start_date_str:
            try:
                start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass  # Ignore invalid dates

        if end_date_str:
            try:
                end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass  # Ignore invalid dates

        # Apply date range filter to query ONLY if dates are provided
        if start_date and end_date:
            query = query.filter(
                or_(
                    and_(Task.plan_date >= start_date, Task.plan_date <= end_date),
                    Task.plan_date.is_(None)  # Include tasks without plan_date
                )
            )
        elif start_date:  # Only start date provided
            query = query.filter(
                or_(
                    Task.plan_date >= start_date,
                    Task.plan_date.is_(None)
                )
            )
        elif end_date:  # Only end date provided
            query = query.filter(
                or_(
                    Task.plan_date <= end_date,
                    Task.plan_date.is_(None)
                )
            )

        # Apply search filter
        if search_query:
            query = query.filter(
                or_(
                    Task.ticket_id.ilike(f'%{search_query}%'),
                    Task.title.ilike(f'%{search_query}%'),
                    Task.description.ilike(f'%{search_query}%')
                )
            )

        # Apply tab-based filtering
        now = datetime.utcnow().date()

        if tab == 'delayed':
            query = query.filter(
                Task.plan_date < now,
                Task.status.in_(['assigned', 'in_progress', 'under_audit'])
            ).order_by(Task.plan_date)

        elif tab == 'pending':
            query = query.filter(
                Task.status.in_(['assigned', 'in_progress'])
            ).filter(
                or_(
                    Task.plan_date >= now,
                    Task.plan_date.is_(None)
                )
            ).order_by(Task.plan_date)

        elif tab == 'completed':
            query = query.filter(
                Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
            ).order_by(Task.completed_date.desc())

        else:  # tab == 'all'
            query = query.order_by(Task.updated_at.desc())

        # Paginate with error handling
        tasks = query.paginate(page=page, per_page=per_page, error_out=False)

        # Calculate enhanced summary metrics with error handling
        try:
            summary_metrics = calculate_dashboard_summary_metrics(user_id_filter, show_team_view)
        except Exception as e:
            app.logger.error(f"Error calculating summary metrics: {str(e)}")
            # Provide fallback metrics
            summary_metrics = {
                'on_time_rate': 0,
                'on_time_completed': 0,
                'total_completed': 0,
                'total_pending': 0,
                'total_delayed': 0,
                'under_audit': 0,
                'completed_count': 0,
                'last_audit_passed': None
            }

        # Pass current date for template calculations
        current_date = dt.utcnow().date()

        return render_template('dashboard.html',
                             tasks=tasks,
                             summary_metrics=summary_metrics,
                             search_query=search_query,
                             per_page=per_page,
                             tab=tab,
                             view_mode=view_mode,
                             is_manager=is_manager,
                             start_date=start_date,
                             end_date=end_date,
                             current_date=current_date)

    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash(f'An error occurred loading the dashboard. Please try again.', 'danger')
        return redirect(url_for('main.index'))


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
        # Collect Content Metrics (dynamic table 1)
        types = request.form.getlist('type[]')
        keywords = request.form.getlist('keyword[]')
        search_volumes = request.form.getlist('search_volume[]')

        content_metrics = []
        for i in range(len(types)):
            if i < len(keywords) and i < len(search_volumes):
                content_metrics.append({
                    'type': types[i],
                    'keyword': keywords[i],
                    'search_volume': search_volumes[i]
                })

        # Collect Linking Data (dynamic table 2)
        linking_keywords = request.form.getlist('internal_linking_keywords[]')
        linking_urls = request.form.getlist('internal_link_urls[]')
        linking_svs = request.form.getlist('internal_linking_keywords_sv[]')

        linking_data = []
        for i in range(len(linking_keywords)):
            if i < len(linking_urls) and i < len(linking_svs):
                linking_data.append({
                    'internal_linking_keywords': linking_keywords[i],
                    'internal_link_urls': linking_urls[i],
                    'internal_linking_keywords_sv': linking_svs[i]
                })

        # Collect content-specific data
        content_data = {
            'category_type': form.category_type.data,
            'content_metrics': content_metrics,
            'linking_data': linking_data,
            'title': form.title_field.data,
            'meta_description': form.meta_description.data,
            'faqs': form.faqs.data,
        }

        # Add category-specific fields if Category type
        if form.category_type.data == 'Category':
            content_data.update({
                'page_type': form.page_type.data,
                'category_name': form.category_name.data,
                'url': form.url.data,
                'page_sv': form.page_sv.data,
                'gemstone_category': form.gemstone_category.data,
                'recommended_density': form.recommended_density.data,
                'word_count': form.word_count.data,
                'astro_non_astro': form.astro_non_astro.data,
            })

        # Add blog-specific fields if Blog type
        elif form.category_type.data == 'Blog':
            content_data.update({
                'blog_url': form.blog_url.data,
                'keyword_sv': form.keyword_sv.data,
                'h1': form.h1.data,
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

        # Log task creation
        assignee_user = User.query.get(form.assigned_to.data)
        log = TaskLog(
            task_id=task.id,
            user_id=current_user.id,
            action='Task created',
            field_name='assigned_to',
            previous_value=None,
            new_value=assignee_user.username if assignee_user else None,
            new_status='assigned',
            notes=f'Task assigned to {task.assignee.username if task.assignee else "unassigned"}'
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
                        # Handle Google Doc URL
                        sheet_url = request.form.get('sheet_url', '').strip()

                        if not sheet_url:
                            flash('Please provide a Google Doc URL.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        if not validate_google_doc_url(sheet_url):
                            flash('Invalid Google Docs URL format.', 'danger')
                            return redirect(url_for('main.task_detail', task_id=task_id))

                        # Update task
                        task.submission_type = 'sheet_link'
                        task.sheet_url = sheet_url

                        # Log Google Doc URL submission
                        sheet_log = TaskLog(
                            task_id=task.id,
                            user_id=current_user.id,
                            action='Google Doc link submitted',
                            field_name='sheet_url',
                            previous_value=None,
                            new_value=sheet_url,
                            notes='Task completion Google Doc link provided'
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


@main_bp.route('/user/<int:user_id>/update-password', methods=['GET', 'POST'])
@login_required
def update_user_password(user_id):
    """Update user password (Admin only)"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    form = UpdatePasswordForm()

    if form.validate_on_submit():
        # Update the user's password
        user.set_password(form.new_password.data)
        db.session.commit()

        flash(f'Password for user {user.username} has been updated successfully!', 'success')
        return redirect(url_for('main.users'))

    return render_template('update_password.html', form=form, user=user)


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


# ============================================================================
# REPORTING FUNCTIONS - FMS
# ============================================================================

def calculate_task_performance(task):
    """
    Calculate if a task was completed on-time or delayed
    Returns: dict with 'completion_status' and 'audit_status'
    """
    from datetime import timedelta

    performance = {
        'completion_status': None,  # 'on-time', 'delayed', or None
        'audit_status': None,       # 'on-time', 'delayed', or None
        'completion_delay_days': 0,
        'audit_delay_days': 0
    }

    # Check task completion against plan_date
    if task.completed_date and task.plan_date:
        # Convert plan_date (date) to datetime for comparison
        from datetime import datetime
        plan_datetime = datetime.combine(task.plan_date, datetime.min.time())

        if task.completed_date <= plan_datetime:
            performance['completion_status'] = 'on-time'
        else:
            performance['completion_status'] = 'delayed'
            delay = task.completed_date - plan_datetime
            performance['completion_delay_days'] = delay.days

    # Check audit performance (1 day TAT from completion)
    if task.audit_date and task.completed_date:
        audit_deadline = task.completed_date + timedelta(days=1)

        if task.audit_date <= audit_deadline:
            performance['audit_status'] = 'on-time'
        else:
            performance['audit_status'] = 'delayed'
            delay = task.audit_date - audit_deadline
            performance['audit_delay_days'] = delay.days

    return performance


def get_assignee_report_data(start_date=None, end_date=None):
    """
    Generate assignee-wise performance report
    Args:
        start_date: Filter tasks from this date (inclusive)
        end_date: Filter tasks to this date (inclusive)
    Returns: list of dicts with assignee stats
    """
    from sqlalchemy import func

    # Get all users who have been assigned tasks
    assignees = User.query.join(Task, Task.assigned_to_id == User.id).distinct().all()

    report_data = []

    for assignee in assignees:
        # Build query for completed tasks with date filters
        completed_query = Task.query.filter_by(
            assigned_to_id=assignee.id
        ).filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed', 'under_audit'])
        )

        # Apply date filters
        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            completed_query = completed_query.filter(Task.completed_date >= start_datetime)

        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            completed_query = completed_query.filter(Task.completed_date <= end_datetime)

        completed_tasks = completed_query.all()

        # Build query for total assigned tasks with date filters
        total_assigned_query = Task.query.filter_by(assigned_to_id=assignee.id)
        if start_date or end_date:
            # For total assigned, we'll use the same date filter as completed tasks
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                total_assigned_query = total_assigned_query.filter(
                    or_(Task.completed_date >= start_datetime, Task.completed_date.is_(None))
                )
            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                total_assigned_query = total_assigned_query.filter(
                    or_(Task.completed_date <= end_datetime, Task.completed_date.is_(None))
                )

        stats = {
            'assignee_name': assignee.username,
            'assignee_id': assignee.id,
            'total_assigned': total_assigned_query.count(),
            'total_completed': len(completed_tasks),
            'completion_on_time': 0,
            'completion_delayed': 0,
            'average_delay_days': 0,
            'completion_rate': 0
        }

        # Calculate performance for each completed task
        total_delay_days = 0
        delayed_count = 0

        for task in completed_tasks:
            perf = calculate_task_performance(task)

            if perf['completion_status'] == 'on-time':
                stats['completion_on_time'] += 1
            elif perf['completion_status'] == 'delayed':
                stats['completion_delayed'] += 1
                total_delay_days += perf['completion_delay_days']
                delayed_count += 1

        # Calculate averages
        if delayed_count > 0:
            stats['average_delay_days'] = round(total_delay_days / delayed_count, 1)

        if stats['total_completed'] > 0:
            stats['completion_rate'] = round(
                (stats['completion_on_time'] / stats['total_completed']) * 100, 1
            )

        report_data.append(stats)

    # Sort by completion rate (best performers first)
    report_data.sort(key=lambda x: x['completion_rate'], reverse=True)

    return report_data


def get_overall_report_stats(start_date=None, end_date=None):
    """
    Generate overall system statistics
    Args:
        start_date: Filter tasks from this date (inclusive)
        end_date: Filter tasks to this date (inclusive)
    Returns: dict with overall stats
    """
    # Build base queries with date filters
    all_tasks_query = Task.query
    completed_tasks_query = Task.query.filter(
        Task.status.in_(['audit_passed', 'audit_failed', 'completed', 'under_audit'])
    )

    # Apply date filters based on completed_date
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        all_tasks_query = all_tasks_query.filter(
            or_(Task.completed_date >= start_datetime, Task.completed_date.is_(None))
        )
        completed_tasks_query = completed_tasks_query.filter(Task.completed_date >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        all_tasks_query = all_tasks_query.filter(
            or_(Task.completed_date <= end_datetime, Task.completed_date.is_(None))
        )
        completed_tasks_query = completed_tasks_query.filter(Task.completed_date <= end_datetime)

    all_tasks = all_tasks_query.all()
    completed_tasks = completed_tasks_query.all()

    stats = {
        'total_tasks': len(all_tasks),
        'total_completed': len(completed_tasks),
        'completion_on_time': 0,
        'completion_delayed': 0,
        'audit_on_time': 0,
        'audit_delayed': 0,
        'average_completion_delay': 0,
        'average_audit_delay': 0,
        'overall_on_time_rate': 0
    }

    total_completion_delay = 0
    completion_delayed_count = 0
    total_audit_delay = 0
    audit_delayed_count = 0

    for task in completed_tasks:
        perf = calculate_task_performance(task)

        # Count completion performance
        if perf['completion_status'] == 'on-time':
            stats['completion_on_time'] += 1
        elif perf['completion_status'] == 'delayed':
            stats['completion_delayed'] += 1
            total_completion_delay += perf['completion_delay_days']
            completion_delayed_count += 1

        # Count audit performance
        if perf['audit_status'] == 'on-time':
            stats['audit_on_time'] += 1
        elif perf['audit_status'] == 'delayed':
            stats['audit_delayed'] += 1
            total_audit_delay += perf['audit_delay_days']
            audit_delayed_count += 1

    # Calculate averages
    if completion_delayed_count > 0:
        stats['average_completion_delay'] = round(
            total_completion_delay / completion_delayed_count, 1
        )

    if audit_delayed_count > 0:
        stats['average_audit_delay'] = round(
            total_audit_delay / audit_delayed_count, 1
        )

    if stats['total_completed'] > 0:
        stats['overall_on_time_rate'] = round(
            (stats['completion_on_time'] / stats['total_completed']) * 100, 1
        )

    return stats


def get_personal_performance_data(user_id, start_date=None, end_date=None):
    """
    Generate personal performance report for a specific assignee
    Args:
        user_id: The assignee's user ID
        start_date: Filter tasks from this date (inclusive)
        end_date: Filter tasks to this date (inclusive)
    Returns: dict with personal performance stats
    """
    # Build query for assignee's completed tasks
    completed_query = Task.query.filter_by(
        assigned_to_id=user_id
    ).filter(
        Task.status.in_(['audit_passed', 'audit_failed', 'completed', 'under_audit'])
    )

    # Apply date filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        completed_query = completed_query.filter(Task.completed_date >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        completed_query = completed_query.filter(Task.completed_date <= end_datetime)

    completed_tasks = completed_query.all()

    # Get total assigned tasks with date filter
    total_assigned_query = Task.query.filter_by(assigned_to_id=user_id)
    if start_date or end_date:
        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            total_assigned_query = total_assigned_query.filter(
                or_(Task.completed_date >= start_datetime, Task.completed_date.is_(None))
            )
        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            total_assigned_query = total_assigned_query.filter(
                or_(Task.completed_date <= end_datetime, Task.completed_date.is_(None))
            )

    stats = {
        'total_assigned': total_assigned_query.count(),
        'total_completed': len(completed_tasks),
        'completion_on_time': 0,
        'completion_delayed': 0,
        'audit_on_time': 0,
        'audit_delayed': 0,
        'average_completion_delay': 0,
        'average_audit_delay': 0,
        'completion_rate': 0,
        'audit_rate': 0,
        'overall_score': 0,
        'performance_grade': 'Not Rated'
    }

    # Calculate performance for each completed task
    total_completion_delay = 0
    completion_delayed_count = 0
    total_audit_delay = 0
    audit_delayed_count = 0

    for task in completed_tasks:
        perf = calculate_task_performance(task)

        if perf['completion_status'] == 'on-time':
            stats['completion_on_time'] += 1
        elif perf['completion_status'] == 'delayed':
            stats['completion_delayed'] += 1
            total_completion_delay += perf['completion_delay_days']
            completion_delayed_count += 1

        if perf['audit_status'] == 'on-time':
            stats['audit_on_time'] += 1
        elif perf['audit_status'] == 'delayed':
            stats['audit_delayed'] += 1
            total_audit_delay += perf['audit_delay_days']
            audit_delayed_count += 1

    # Calculate averages and rates
    if completion_delayed_count > 0:
        stats['average_completion_delay'] = round(total_completion_delay / completion_delayed_count, 1)

    if audit_delayed_count > 0:
        stats['average_audit_delay'] = round(total_audit_delay / audit_delayed_count, 1)

    if stats['total_completed'] > 0:
        stats['completion_rate'] = round(
            (stats['completion_on_time'] / stats['total_completed']) * 100, 1
        )

    # Calculate audit rate
    total_audited = stats['audit_on_time'] + stats['audit_delayed']
    if total_audited > 0:
        stats['audit_rate'] = round(
            (stats['audit_on_time'] / total_audited) * 100, 1
        )

    # Calculate overall score (weighted average: 70% completion rate, 30% audit rate)
    if stats['total_completed'] > 0:
        if total_audited > 0:
            stats['overall_score'] = round((stats['completion_rate'] * 0.7) + (stats['audit_rate'] * 0.3), 1)
        else:
            stats['overall_score'] = stats['completion_rate']

        # Assign performance grade
        if stats['overall_score'] >= 90:
            stats['performance_grade'] = 'Excellent'
        elif stats['overall_score'] >= 80:
            stats['performance_grade'] = 'Very Good'
        elif stats['overall_score'] >= 70:
            stats['performance_grade'] = 'Good'
        elif stats['overall_score'] >= 60:
            stats['performance_grade'] = 'Satisfactory'
        else:
            stats['performance_grade'] = 'Needs Improvement'

    return stats


@main_bp.route('/reports')
@login_required
def reports():
    """Performance reports page - Personal view for assignees, global for managers/admins"""

    # Get date range from query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Parse dates
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format.', 'danger')
            start_date_str = None

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid end date format.', 'danger')
            end_date_str = None

    # Determine if this is a personal view (assignee) or global view (manager/admin)
    is_personal_view = not current_user.is_manager()
    personal_stats = None

    if is_personal_view:
        # Personal view for assignees - show only their data
        personal_stats = get_personal_performance_data(current_user.id, start_date, end_date)

        # For personal view, we use personal stats as overall stats
        overall_stats = {
            'total_tasks': personal_stats['total_assigned'],
            'total_completed': personal_stats['total_completed'],
            'completion_on_time': personal_stats['completion_on_time'],
            'completion_delayed': personal_stats['completion_delayed'],
            'audit_on_time': personal_stats['audit_on_time'],
            'audit_delayed': personal_stats['audit_delayed'],
            'average_completion_delay': personal_stats['average_completion_delay'],
            'average_audit_delay': personal_stats['average_audit_delay'],
            'overall_on_time_rate': personal_stats['completion_rate']
        }

        # No assignee report in personal view
        assignee_report = []

        # Filter tasks to only show current user's tasks
        filtered_query = Task.query.filter_by(assigned_to_id=current_user.id).filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
        )
    else:
        # Global view for managers/admins - show all data
        overall_stats = get_overall_report_stats(start_date, end_date)
        assignee_report = get_assignee_report_data(start_date, end_date)

        # Show all tasks
        filtered_query = Task.query.filter(
            Task.status.in_(['audit_passed', 'audit_failed', 'completed'])
        )

    # Apply date filters
    if start_date:
        filtered_query = filtered_query.filter(Task.completed_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filtered_query = filtered_query.filter(Task.completed_date <= datetime.combine(end_date, datetime.max.time()))

    # Get all filtered tasks (ordered by most recent first)
    filtered_tasks = filtered_query.order_by(Task.completed_date.desc()).all()

    # Count total filtered tasks
    total_filtered_tasks = len(filtered_tasks)

    # Add performance data to each filtered task
    tasks_with_performance = []
    for task in filtered_tasks:
        task_data = {
            'task': task,
            'performance': calculate_task_performance(task)
        }
        tasks_with_performance.append(task_data)

    return render_template('reports.html',
                         overall_stats=overall_stats,
                         assignee_report=assignee_report,
                         filtered_tasks=tasks_with_performance,
                         total_filtered_tasks=total_filtered_tasks,
                         start_date=start_date_str,
                         end_date=end_date_str,
                         has_filter=bool(start_date_str or end_date_str),
                         is_personal_view=is_personal_view,
                         personal_stats=personal_stats)
