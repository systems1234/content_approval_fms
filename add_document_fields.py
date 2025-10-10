"""
Migration script to add document submission fields to Task model
Run this script once to update the database schema
"""

from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app('development')

    with app.app_context():
        print("Adding document submission fields to tasks table...")

        try:
            # Add new columns
            db.session.execute(text("""
                ALTER TABLE tasks
                ADD COLUMN submission_type VARCHAR(20)
            """))
            print("  - Added submission_type column")
        except Exception as e:
            print(f"  - submission_type column may already exist: {e}")

        try:
            db.session.execute(text("""
                ALTER TABLE tasks
                ADD COLUMN document_file_path VARCHAR(500)
            """))
            print("  - Added document_file_path column")
        except Exception as e:
            print(f"  - document_file_path column may already exist: {e}")

        try:
            db.session.execute(text("""
                ALTER TABLE tasks
                ADD COLUMN document_file_name VARCHAR(255)
            """))
            print("  - Added document_file_name column")
        except Exception as e:
            print(f"  - document_file_name column may already exist: {e}")

        try:
            db.session.execute(text("""
                ALTER TABLE tasks
                ADD COLUMN sheet_url VARCHAR(500)
            """))
            print("  - Added sheet_url column")
        except Exception as e:
            print(f"  - sheet_url column may already exist: {e}")

        db.session.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        print("The tasks table now has document submission fields.")

if __name__ == '__main__':
    migrate()
