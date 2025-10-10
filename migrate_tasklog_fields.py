"""
Migration script to add field tracking columns to TaskLog model
Run this script once to update the database schema
"""

from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app('development')

    with app.app_context():
        print("Adding field tracking columns to task_logs table...")

        try:
            # Add field_name column
            db.session.execute(text("""
                ALTER TABLE task_logs
                ADD COLUMN field_name VARCHAR(100)
            """))
            print("  - Added field_name column")
        except Exception as e:
            print(f"  - field_name column may already exist: {e}")

        try:
            # Add previous_value column
            db.session.execute(text("""
                ALTER TABLE task_logs
                ADD COLUMN previous_value TEXT
            """))
            print("  - Added previous_value column")
        except Exception as e:
            print(f"  - previous_value column may already exist: {e}")

        try:
            # Add new_value column
            db.session.execute(text("""
                ALTER TABLE task_logs
                ADD COLUMN new_value TEXT
            """))
            print("  - Added new_value column")
        except Exception as e:
            print(f"  - new_value column may already exist: {e}")

        db.session.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        print("The task_logs table now has field tracking columns.")

if __name__ == '__main__':
    migrate()
