"""
Clear all data from database while keeping the structure intact
This will delete all records but preserve all tables
"""
from app import create_app, db
from app.models import Task, TaskLog, WorkflowStep, User, Holiday, BusinessHours, StepTemplate

def clear_all_data():
    """Delete all data from all tables"""
    app = create_app()

    with app.app_context():
        print("\n" + "=" * 60)
        print("CLEARING ALL DATA FROM DATABASE")
        print("=" * 60)
        print("\nWARNING: This will delete ALL data from the database!")
        print("The database structure will remain intact.")
        print()

        response = input("Are you sure you want to continue? Type 'yes' to confirm: ").strip().lower()

        if response != 'yes':
            print("\n✗ Operation cancelled.\n")
            return

        print("\nDeleting all data...")
        print()

        try:
            # 1. Delete all task logs
            log_count = TaskLog.query.count()
            if log_count > 0:
                TaskLog.query.delete()
                print(f"  ✓ Deleted {log_count} task logs")

            # 2. Delete all workflow steps
            workflow_count = WorkflowStep.query.count()
            if workflow_count > 0:
                WorkflowStep.query.delete()
                print(f"  ✓ Deleted {workflow_count} workflow steps")

            # 3. Delete all tasks
            task_count = Task.query.count()
            if task_count > 0:
                Task.query.delete()
                print(f"  ✓ Deleted {task_count} tasks")

            # 4. Delete all holidays
            holiday_count = Holiday.query.count()
            if holiday_count > 0:
                Holiday.query.delete()
                print(f"  ✓ Deleted {holiday_count} holidays")

            # 5. Delete all step templates
            template_count = StepTemplate.query.count()
            if template_count > 0:
                StepTemplate.query.delete()
                print(f"  ✓ Deleted {template_count} step templates")

            # 6. Delete all business hours
            business_hours_count = BusinessHours.query.count()
            if business_hours_count > 0:
                BusinessHours.query.delete()
                print(f"  ✓ Deleted {business_hours_count} business hours entries")

            # 7. Delete all users
            user_count = User.query.count()
            if user_count > 0:
                User.query.delete()
                print(f"  ✓ Deleted {user_count} users")

            # Commit all deletions
            db.session.commit()

            print("\n" + "=" * 60)
            print("✓ ALL DATA CLEARED SUCCESSFULLY")
            print("=" * 60)
            print()
            print("Summary:")
            print(f"  - {log_count} task logs deleted")
            print(f"  - {workflow_count} workflow steps deleted")
            print(f"  - {task_count} tasks deleted")
            print(f"  - {holiday_count} holidays deleted")
            print(f"  - {template_count} step templates deleted")
            print(f"  - {business_hours_count} business hours deleted")
            print(f"  - {user_count} users deleted")
            print()

            # Create admin user
            print("Creating admin user...")
            admin = User(
                username='admin',
                email='admin@crm.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("  ✓ Admin user created successfully")
            print()
            print("Login Credentials:")
            print("  Username: admin")
            print("  Password: admin123")
            print()
            print("The database is now empty but structure is intact.")
            print("You can now add data manually through the application forms.")
            print()

        except Exception as e:
            db.session.rollback()
            print("\n" + "=" * 60)
            print("✗ ERROR OCCURRED")
            print("=" * 60)
            print(f"Error: {str(e)}")
            print("All changes have been rolled back.")
            print()
            raise


if __name__ == '__main__':
    clear_all_data()
