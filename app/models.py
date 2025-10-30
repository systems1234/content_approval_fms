from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db
import random
import string
from sqlalchemy import Index

class User(UserMixin, db.Model):
    """User model with role-based access"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='assignee')  # assignee, auditor, manager, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_tasks = db.relationship('Task', foreign_keys='Task.created_by_id', backref='creator', lazy='dynamic')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assigned_to_id', backref='assignee', lazy='dynamic')
    audited_tasks = db.relationship('Task', foreign_keys='Task.auditor_id', backref='auditor', lazy='dynamic')
    task_logs = db.relationship('TaskLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Hash password using PBKDF2"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role in ['manager', 'admin']

    def is_auditor(self):
        return self.role in ['auditor', 'manager', 'admin']

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Task(db.Model):
    """Task model with FSM workflow states"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Content-specific fields stored as JSON
    content_data = db.Column(db.JSON, nullable=True)

    # Foreign keys
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Dates
    plan_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    audit_date = db.Column(db.DateTime, nullable=True)

    # Audit tracking
    revision_count = db.Column(db.Integer, default=0)
    audit_notes = db.Column(db.Text, nullable=True)

    # Document submission (for task completion)
    submission_type = db.Column(db.String(20), nullable=True)  # 'document' or 'sheet_link'
    document_file_path = db.Column(db.String(500), nullable=True)  # Path to uploaded file
    document_file_name = db.Column(db.String(255), nullable=True)  # Original filename
    sheet_url = db.Column(db.String(500), nullable=True)  # Google Sheet URL

    # FSM status: assigned, in_progress, completed, under_audit, audit_passed, audit_failed, cancelled
    status = db.Column(db.String(20), nullable=False, default='assigned')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    logs = db.relationship('TaskLog', backref='task', lazy='dynamic', cascade='all, delete-orphan')

    # FSM State Definitions
    STATES = [
        'assigned',
        'in_progress',
        'completed',
        'under_audit',
        'audit_passed',
        'audit_failed',
        'cancelled'
    ]

    # Valid state transitions
    TRANSITIONS = {
        'assigned': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'cancelled'],
        'completed': ['under_audit', 'cancelled'],
        'under_audit': ['audit_passed', 'audit_failed', 'cancelled'],
        'audit_failed': ['in_progress', 'cancelled'],
        'audit_passed': [],  # Terminal state
        'cancelled': []  # Terminal state
    }

    def can_transition_to(self, new_status):
        """Check if transition is valid"""
        return new_status in self.TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status, user, notes=None):
        """Perform state transition with logging"""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        # Auto-assign auditor on completion
        if new_status == 'under_audit' and not self.auditor_id:
            self.auto_assign_auditor()

        # Update dates
        if new_status == 'completed':
            self.completed_date = datetime.utcnow()
        elif new_status == 'under_audit':
            # Transition automatically triggered
            pass
        elif new_status == 'audit_passed':
            self.audit_date = datetime.utcnow()
        elif new_status == 'audit_failed':
            self.audit_date = datetime.utcnow()
            self.revision_count += 1
            self.audit_notes = notes

        # Log the transition with detailed field tracking
        log = TaskLog(
            task_id=self.id,
            user_id=user.id,
            action=f'Changed status from {old_status} to {new_status}',
            field_name='status',
            previous_value=old_status.replace('_', ' ').title(),
            new_value=new_status.replace('_', ' ').title(),
            previous_status=old_status,
            new_status=new_status,
            notes=notes
        )
        db.session.add(log)

        return True

    def auto_assign_auditor(self):
        """Assign the task creator (manager) as auditor"""
        # The person who created the task will be the auditor
        if self.created_by_id:
            self.auditor_id = self.created_by_id

    def get_status_badge_class(self):
        """Return Tailwind CSS classes for status badge"""
        status_classes = {
            'assigned': 'bg-gray-100 text-gray-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'completed': 'bg-green-100 text-green-800',
            'under_audit': 'bg-yellow-100 text-yellow-800',
            'audit_passed': 'bg-emerald-100 text-emerald-800',
            'audit_failed': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-600'
        }
        return status_classes.get(self.status, 'bg-gray-100 text-gray-800')

    @property
    def is_delayed(self):
        """Check if task is delayed (past plan date and not completed)"""
        if self.status in ['audit_passed', 'cancelled']:
            return False
        if self.plan_date:
            from datetime import datetime
            now = datetime.utcnow().date()
            return self.plan_date < now
        return False

    @staticmethod
    def generate_ticket_id():
        """Generate a unique ticket ID in format: TKT-YYYYMMDD-NNN (sequential)"""
        from datetime import datetime
        date_part = datetime.now().strftime('%Y%m%d')

        # Find the last ticket created today
        prefix = f'TKT-{date_part}-'
        last_ticket = Task.query.filter(
            Task.ticket_id.like(f'{prefix}%')
        ).order_by(Task.ticket_id.desc()).first()

        # Extract sequence number and increment
        if last_ticket:
            try:
                # Extract the numeric part (last 3 digits)
                last_sequence = int(last_ticket.ticket_id.split('-')[-1])
                next_sequence = last_sequence + 1
            except (ValueError, IndexError):
                # If parsing fails, start from 1
                next_sequence = 1
        else:
            # No tickets today, start from 1
            next_sequence = 1

        # Format with leading zeros (3 digits)
        sequence_str = str(next_sequence).zfill(3)
        ticket_id = f'{prefix}{sequence_str}'

        # Extra safety check for uniqueness
        while Task.query.filter_by(ticket_id=ticket_id).first():
            next_sequence += 1
            sequence_str = str(next_sequence).zfill(3)
            ticket_id = f'{prefix}{sequence_str}'

        return ticket_id

    def generate_workflow_steps(self, step_assignments=None):
        """
        Generate workflow steps from active step templates

        Args:
            step_assignments: Dict mapping step_order to {assigned_to_id, auditor_id}
                             e.g., {1: {'assigned_to_id': 5, 'auditor_id': 3}}
        """
        from app.utils import calculate_planned_ptp

        # Get active step templates ordered by step_order
        templates = StepTemplate.query.filter_by(is_active=True).order_by(StepTemplate.step_order).all()

        if not templates:
            return []

        step_assignments = step_assignments or {}
        created_steps = []
        previous_step_planned = None

        for template in templates:
            # Get assignment for this step
            assignment = step_assignments.get(template.step_order, {})
            assigned_to_id = assignment.get('assigned_to_id')
            auditor_id = assignment.get('auditor_id')

            # Calculate planned_ptp
            planned_ptp = calculate_planned_ptp(
                task_start_date=self.created_at,
                step_order=template.step_order,
                previous_step_planned=previous_step_planned,
                tat_hours=template.tat_hours
            )

            # Create workflow step
            step = WorkflowStep(
                task_id=self.id,
                step_template_id=template.id,
                step_name=template.name,
                step_order=template.step_order,
                tat_hours=template.tat_hours,
                assigned_to_id=assigned_to_id,
                auditor_id=auditor_id,
                planned_ptp=planned_ptp,
                status='pending'
            )

            db.session.add(step)
            created_steps.append(step)

            # Set previous step's planned for next iteration
            previous_step_planned = planned_ptp

        return created_steps

    def get_current_step(self):
        """Get the current active workflow step (first non-completed step)"""
        return WorkflowStep.query.filter_by(
            task_id=self.id
        ).filter(
            WorkflowStep.status.in_(['pending', 'in_progress', 'completed', 'under_audit', 'audit_failed'])
        ).order_by(WorkflowStep.step_order).first()

    def get_all_steps(self):
        """Get all workflow steps ordered by step_order"""
        return WorkflowStep.query.filter_by(task_id=self.id).order_by(WorkflowStep.step_order).all()

    def is_workflow_complete(self):
        """Check if all workflow steps have passed audit"""
        steps = self.get_all_steps()
        if not steps:
            return False

        return all(step.status == 'audit_passed' for step in steps)

    def update_task_status_from_workflow(self):
        """Update task status based on workflow step statuses"""
        if self.is_workflow_complete():
            self.status = 'audit_passed'
            self.completed_date = datetime.utcnow()
            self.audit_date = datetime.utcnow()
        else:
            current_step = self.get_current_step()
            if current_step:
                # Map workflow step status to task status
                step_to_task_status = {
                    'pending': 'assigned',
                    'in_progress': 'in_progress',
                    'completed': 'completed',
                    'under_audit': 'under_audit',
                    'audit_failed': 'audit_failed',
                    'audit_passed': 'in_progress'  # Move to next step
                }
                mapped_status = step_to_task_status.get(current_step.status, 'assigned')
                if self.status != mapped_status:
                    self.status = mapped_status

    def __repr__(self):
        return f'<Task {self.ticket_id}: {self.title} ({self.status})>'


class TaskLog(db.Model):
    """Audit log for task status changes"""
    __tablename__ = 'task_logs'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    action = db.Column(db.String(200), nullable=False)
    field_name = db.Column(db.String(100), nullable=True)  # Which field changed
    previous_value = db.Column(db.Text, nullable=True)  # Old value
    new_value = db.Column(db.Text, nullable=True)  # New value
    previous_status = db.Column(db.String(20), nullable=True)  # Kept for backward compatibility
    new_status = db.Column(db.String(20), nullable=True)  # Kept for backward compatibility
    notes = db.Column(db.Text, nullable=True)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Field name to human-readable label mapping
    FIELD_LABELS = {
        'status': 'Status',
        'plan_date': 'Plan Date',
        'assigned_to': 'Assignee',
        'auditor': 'Auditor',
        'title': 'Title',
        'description': 'Description',
        'submission_type': 'Submission Type',
        'document_file': 'Document File',
        'sheet_url': 'Sheet URL',
        'audit_notes': 'Audit Notes',
        'revision_count': 'Revision Count',
        'notes': 'Notes'
    }

    def get_field_label(self):
        """Get human-readable field label"""
        return self.FIELD_LABELS.get(self.field_name, self.field_name.replace('_', ' ').title() if self.field_name else '')

    def __repr__(self):
        return f'<TaskLog {self.id}: Task {self.task_id} - {self.action}>'


class Holiday(db.Model):
    """Holiday calendar for business date calculations"""
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)  # If true, applies every year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    creator = db.relationship('User', backref='created_holidays')

    def __repr__(self):
        return f'<Holiday {self.date}: {self.name}>'


class BusinessHours(db.Model):
    """Business hours configuration for working time calculations"""
    __tablename__ = 'business_hours'

    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)  # e.g., 09:00
    end_time = db.Column(db.Time, nullable=False)  # e.g., 18:00
    is_working_day = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_day_of_week', 'day_of_week'),
    )

    def __repr__(self):
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f'<BusinessHours {day_names[self.day_of_week]}: {self.start_time}-{self.end_time}>'


class StepTemplate(db.Model):
    """Template for workflow steps with TAT configuration"""
    __tablename__ = 'step_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    step_order = db.Column(db.Integer, nullable=False)  # Order in workflow (1, 2, 3...)
    tat_hours = db.Column(db.Float, nullable=False, default=24.0)  # Turnaround time in hours
    requires_audit = db.Column(db.Boolean, default=True)  # If step requires audit approval
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    creator = db.relationship('User', backref='created_step_templates')

    __table_args__ = (
        Index('idx_step_order', 'step_order'),
    )

    def __repr__(self):
        return f'<StepTemplate {self.step_order}: {self.name} (TAT: {self.tat_hours}h)>'


class WorkflowStep(db.Model):
    """Individual workflow step instance for a task"""
    __tablename__ = 'workflow_steps'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    step_template_id = db.Column(db.Integer, db.ForeignKey('step_templates.id'), nullable=True)

    # Step details
    step_name = db.Column(db.String(200), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    tat_hours = db.Column(db.Float, nullable=False)

    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Planned dates - two calculation methods
    planned_ptp = db.Column(db.DateTime, nullable=True)  # Plan-to-Plan: based on previous step's planned
    planned_atp = db.Column(db.DateTime, nullable=True)  # Actual-to-Plan: based on previous step's actual

    # Actual dates
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)  # When assignee completes
    audit_completed_at = db.Column(db.DateTime, nullable=True)  # When audit passes

    # Status: pending, in_progress, completed, under_audit, audit_passed, audit_failed
    status = db.Column(db.String(20), nullable=False, default='pending')

    # Audit tracking
    revision_count = db.Column(db.Integer, default=0)
    audit_notes = db.Column(db.Text, nullable=True)

    # Document submission
    submission_type = db.Column(db.String(20), nullable=True)  # 'document' or 'sheet_link'
    document_file_path = db.Column(db.String(500), nullable=True)
    document_file_name = db.Column(db.String(255), nullable=True)
    sheet_url = db.Column(db.String(500), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = db.relationship('Task', backref=db.backref('workflow_steps', lazy='dynamic', order_by='WorkflowStep.step_order'))
    step_template = db.relationship('StepTemplate', backref='step_instances')
    assignee = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_steps')
    auditor = db.relationship('User', foreign_keys=[auditor_id], backref='audit_steps')

    __table_args__ = (
        Index('idx_task_step_order', 'task_id', 'step_order'),
        Index('idx_assigned_to', 'assigned_to_id'),
        Index('idx_status', 'status'),
    )

    def is_delayed(self):
        """Check if step is delayed based on planned_atp or planned_ptp"""
        if self.status in ['audit_passed', 'cancelled']:
            return False

        now = datetime.utcnow()
        # Use planned_atp if previous step is completed, otherwise use planned_ptp
        planned = self.planned_atp if self.planned_atp else self.planned_ptp

        if planned and now > planned:
            return True
        return False

    def is_on_time(self):
        """Check if step was completed on time"""
        if not self.audit_completed_at:
            return None  # Not yet completed

        # Use planned_atp if available, otherwise planned_ptp
        planned = self.planned_atp if self.planned_atp else self.planned_ptp

        if planned:
            return self.audit_completed_at <= planned
        return None

    def get_status_badge_class(self):
        """Return Tailwind CSS classes for status badge"""
        status_classes = {
            'pending': 'bg-gray-100 text-gray-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'completed': 'bg-green-100 text-green-800',
            'under_audit': 'bg-yellow-100 text-yellow-800',
            'audit_passed': 'bg-emerald-100 text-emerald-800',
            'audit_failed': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-600'
        }
        return status_classes.get(self.status, 'bg-gray-100 text-gray-800')

    def __repr__(self):
        return f'<WorkflowStep {self.id}: Task {self.task_id} Step {self.step_order} - {self.step_name} ({self.status})>'
