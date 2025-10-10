from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db
import random
import string

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

    @staticmethod
    def generate_ticket_id():
        """Generate a unique ticket ID in format: TKT-YYYYMMDD-XXXX"""
        from datetime import datetime
        date_part = datetime.now().strftime('%Y%m%d')

        # Generate random 4-character alphanumeric code
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

        ticket_id = f'TKT-{date_part}-{random_part}'

        # Ensure uniqueness
        while Task.query.filter_by(ticket_id=ticket_id).first():
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            ticket_id = f'TKT-{date_part}-{random_part}'

        return ticket_id

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
