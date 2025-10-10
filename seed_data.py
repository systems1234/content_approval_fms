"""
Seed script to populate the database with initial demo data
Run this script to create demo users and sample tasks
"""

from app import create_app, db
from app.models import User, Task, TaskLog
from datetime import datetime, timedelta
import random

def seed_users():
    """Create demo users with different roles"""
    print("Creating demo users...")

    users_data = [
        {
            'username': 'admin',
            'email': 'admin@crm.com',
            'password': 'admin123',
            'role': 'admin'
        },
        {
            'username': 'manager',
            'email': 'manager@crm.com',
            'password': 'manager123',
            'role': 'manager'
        },
        {
            'username': 'manager2',
            'email': 'manager2@crm.com',
            'password': 'manager123',
            'role': 'manager'
        },
        {
            'username': 'user',
            'email': 'user@crm.com',
            'password': 'user123',
            'role': 'assignee'
        },
        {
            'username': 'john_doe',
            'email': 'john@crm.com',
            'password': 'user123',
            'role': 'assignee'
        },
        {
            'username': 'jane_smith',
            'email': 'jane@crm.com',
            'password': 'user123',
            'role': 'assignee'
        }
    ]

    created_users = []
    for user_data in users_data:
        # Check if user already exists
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if existing_user:
            print(f"  User '{user_data['username']}' already exists, skipping...")
            created_users.append(existing_user)
            continue

        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            is_active=True
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
        print(f"  Created user: {user_data['username']} ({user_data['role']})")

    db.session.commit()
    print(f"[OK] {len(created_users)} users ready\n")
    return created_users


def seed_tasks(users):
    """Create sample tasks with various statuses"""
    print("Creating sample tasks...")

    # Get users by role
    admin = next((u for u in users if u.role == 'admin'), None)
    manager = next((u for u in users if u.role == 'manager'), None)
    assignees = [u for u in users if u.role == 'assignee']

    if not manager or not assignees:
        print("  ⚠ Not enough users to create tasks")
        return

    tasks_data = [
        {
            'title': 'Design new landing page layout',
            'description': 'Create a modern, responsive landing page design following our brand guidelines. Include hero section, features, testimonials, and CTA.',
            'status': 'assigned',
            'plan_date': datetime.now().date() + timedelta(days=7)
        },
        {
            'title': 'Implement user authentication system',
            'description': 'Build a secure authentication system with login, logout, password reset, and session management.',
            'status': 'in_progress',
            'plan_date': datetime.now().date() + timedelta(days=5)
        },
        {
            'title': 'Write API documentation',
            'description': 'Document all REST API endpoints with request/response examples, authentication requirements, and error codes.',
            'status': 'completed',
            'plan_date': datetime.now().date() + timedelta(days=3),
            'completed_date': datetime.now() - timedelta(hours=2)
        },
        {
            'title': 'Fix mobile responsive issues',
            'description': 'Address layout issues on mobile devices, particularly on iPhone and Android tablets.',
            'status': 'under_audit',
            'plan_date': datetime.now().date() + timedelta(days=2),
            'completed_date': datetime.now() - timedelta(hours=5)
        },
        {
            'title': 'Optimize database queries',
            'description': 'Identify and optimize slow database queries. Add proper indexes and review N+1 query issues.',
            'status': 'audit_passed',
            'plan_date': datetime.now().date(),
            'completed_date': datetime.now() - timedelta(days=2),
            'audit_date': datetime.now() - timedelta(days=1)
        },
        {
            'title': 'Update email templates',
            'description': 'Redesign transactional email templates to match new brand identity.',
            'status': 'audit_failed',
            'plan_date': datetime.now().date() - timedelta(days=1),
            'completed_date': datetime.now() - timedelta(days=3),
            'audit_date': datetime.now() - timedelta(days=2),
            'revision_count': 1,
            'audit_notes': 'Templates do not match brand guidelines. Color scheme needs adjustment.'
        },
        {
            'title': 'Create dashboard analytics widget',
            'description': 'Build an interactive analytics widget showing key metrics with charts and graphs.',
            'status': 'assigned',
            'plan_date': datetime.now().date() + timedelta(days=10)
        },
        {
            'title': 'Implement file upload feature',
            'description': 'Add support for uploading images and documents with validation and size limits.',
            'status': 'in_progress',
            'plan_date': datetime.now().date() + timedelta(days=4)
        }
    ]

    created_tasks = []
    for i, task_data in enumerate(tasks_data):
        assignee = random.choice(assignees)

        task = Task(
            ticket_id=Task.generate_ticket_id(),
            title=task_data['title'],
            description=task_data['description'],
            created_by_id=manager.id,
            assigned_to_id=assignee.id,
            status=task_data['status'],
            plan_date=task_data['plan_date'],
            completed_date=task_data.get('completed_date'),
            audit_date=task_data.get('audit_date'),
            revision_count=task_data.get('revision_count', 0),
            audit_notes=task_data.get('audit_notes'),
            created_at=datetime.now() - timedelta(days=len(tasks_data) - i)
        )

        # Manually set auditor for tasks that are already in audit status (for seeding purposes)
        # In real app, this is auto-assigned when task transitions to under_audit
        if task.status in ['under_audit', 'audit_passed', 'audit_failed']:
            task.auditor_id = manager.id  # Task creator is the auditor

        db.session.add(task)
        created_tasks.append(task)

        # Create initial log entry
        log = TaskLog(
            task=task,
            user_id=manager.id,
            action='Task created',
            new_status='assigned',
            notes=f'Task assigned to {assignee.username}',
            timestamp=task.created_at
        )
        db.session.add(log)

        # Add additional logs for progressed tasks
        if task.status != 'assigned':
            log = TaskLog(
                task=task,
                user_id=assignee.id,
                action='Changed status from assigned to in_progress',
                previous_status='assigned',
                new_status='in_progress',
                timestamp=task.created_at + timedelta(hours=1)
            )
            db.session.add(log)

        if task.status in ['completed', 'under_audit', 'audit_passed', 'audit_failed']:
            log = TaskLog(
                task=task,
                user_id=assignee.id,
                action='Changed status from in_progress to completed',
                previous_status='in_progress',
                new_status='completed',
                timestamp=task.completed_date
            )
            db.session.add(log)

            log = TaskLog(
                task=task,
                user_id=assignee.id,
                action='Changed status from completed to under_audit',
                previous_status='completed',
                new_status='under_audit',
                notes='Auto-assigned for audit',
                timestamp=task.completed_date + timedelta(minutes=1)
            )
            db.session.add(log)

        if task.status in ['audit_passed', 'audit_failed']:
            status = task.status
            log = TaskLog(
                task=task,
                user_id=task.auditor_id,
                action=f'Changed status from under_audit to {status}',
                previous_status='under_audit',
                new_status=status,
                notes=task.audit_notes if status == 'audit_failed' else 'Task approved',
                timestamp=task.audit_date
            )
            db.session.add(log)

        print(f"  Created task: {task_data['title']} ({task_data['status']})")

    db.session.commit()
    print(f"[OK] {len(created_tasks)} tasks created\n")


def main():
    """Main seeding function"""
    app = create_app('development')

    with app.app_context():
        print("\n" + "="*60)
        print("DATABASE SEEDING")
        print("="*60 + "\n")

        # Check if database already has data
        user_count = User.query.count()
        task_count = Task.query.count()

        if user_count > 0 or task_count > 0:
            print(f"[WARNING] Database already contains data:")
            print(f"  Users: {user_count}")
            print(f"  Tasks: {task_count}")
            response = input("\nDo you want to continue? This will add more data. (y/N): ")
            if response.lower() != 'y':
                print("\n[CANCELLED] Seeding cancelled\n")
                return

        # Seed data
        users = seed_users()
        seed_tasks(users)

        print("="*60)
        print("[SUCCESS] SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nDemo Credentials:")
        print("-" * 60)
        print("Admin     : admin / admin123")
        print("Manager 1 : manager / manager123")
        print("Manager 2 : manager2 / manager123")
        print("Assignee  : user / user123")
        print("-" * 60)
        print("\nYou can now login at: http://localhost:5000/login\n")


if __name__ == '__main__':
    main()
