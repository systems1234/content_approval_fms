#!/usr/bin/env python3
"""
Admin User Creation Script for Flask CRM
=========================================
This script creates an admin user in Cloud Run Jobs.
It handles:
- Admin user creation with secure password
- Email validation
- Duplicate user checking
- Logging and error handling
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask
from app import db
from app.models import User
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    """Create Flask application instance"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Override config for production
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    return app


def check_database_connection(app):
    """Test database connectivity"""
    logger.info("Testing database connection...")
    try:
        with app.app_context():
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False


def admin_user_exists(app, username):
    """Check if admin user already exists"""
    try:
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            return user is not None
    except Exception as e:
        logger.error(f"Error checking for existing user: {str(e)}")
        return False


def create_admin_user(app, username, email, password):
    """Create admin user with provided credentials"""
    logger.info(f"Creating admin user: {username}")

    try:
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                logger.warning(f"⚠ User '{username}' already exists - RESETTING PASSWORD")
                logger.info(f"User details: ID={existing_user.id}, Role={existing_user.role}, Active={existing_user.is_active}")

                # Update password, role, and ensure active
                existing_user.set_password(password)
                existing_user.role = 'admin'
                existing_user.is_active = True
                existing_user.email = email
                db.session.commit()

                logger.info(f"✓ User '{username}' password has been reset")
                logger.info(f"✓ User '{username}' is now an active admin")

                return True

            # Create new admin user
            admin = User(
                username=username,
                email=email,
                role='admin',
                is_active=True
            )
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()

            logger.info(f"✓ Admin user '{username}' created successfully")
            logger.info(f"  - User ID: {admin.id}")
            logger.info(f"  - Email: {admin.email}")
            logger.info(f"  - Role: {admin.role}")
            logger.info(f"  - Active: {admin.is_active}")

            return True

    except Exception as e:
        logger.error(f"✗ Failed to create admin user: {str(e)}")
        logger.exception("Full traceback:")
        db.session.rollback()
        return False


def create_default_users(app):
    """Create default users for development/testing"""
    logger.info("Creating default users...")

    default_users = [
        {
            'username': 'manager',
            'email': 'manager@example.com',
            'password': os.getenv('MANAGER_PASSWORD', 'manager123'),
            'role': 'manager'
        },
        {
            'username': 'auditor',
            'email': 'auditor@example.com',
            'password': os.getenv('AUDITOR_PASSWORD', 'auditor123'),
            'role': 'auditor'
        },
        {
            'username': 'user',
            'email': 'user@example.com',
            'password': os.getenv('USER_PASSWORD', 'user123'),
            'role': 'assignee'
        }
    ]

    try:
        with app.app_context():
            for user_data in default_users:
                existing_user = User.query.filter_by(username=user_data['username']).first()

                if existing_user:
                    logger.info(f"⚠ User '{user_data['username']}' already exists, skipping...")
                    continue

                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    is_active=True
                )
                user.set_password(user_data['password'])
                db.session.add(user)

                logger.info(f"✓ Created {user_data['role']}: {user_data['username']}")

            db.session.commit()
            logger.info("✓ Default users created successfully")
            return True

    except Exception as e:
        logger.error(f"✗ Failed to create default users: {str(e)}")
        db.session.rollback()
        return False


def verify_admin_user(app, username):
    """Verify admin user was created correctly"""
    logger.info(f"Verifying admin user: {username}")

    try:
        with app.app_context():
            user = User.query.filter_by(username=username).first()

            if not user:
                logger.error(f"✗ User '{username}' not found in database")
                return False

            # Check properties
            checks = {
                'User exists': user is not None,
                'Role is admin': user.role == 'admin',
                'User is active': user.is_active == True,
                'Password hash exists': user.password_hash is not None,
                'Email is set': user.email is not None
            }

            all_passed = True
            for check_name, result in checks.items():
                status = "✓" if result else "✗"
                logger.info(f"  {status} {check_name}")
                if not result:
                    all_passed = False

            return all_passed

    except Exception as e:
        logger.error(f"✗ Verification failed: {str(e)}")
        return False


def list_all_users(app):
    """List all users in the database"""
    logger.info("Listing all users in database...")

    try:
        with app.app_context():
            users = User.query.all()

            if not users:
                logger.info("  No users found in database")
                return

            logger.info(f"  Found {len(users)} user(s):")
            for user in users:
                logger.info(f"    - {user.username} ({user.role}) - Active: {user.is_active} - Email: {user.email}")

    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")


def main():
    """Main execution"""
    start_time = datetime.now()
    logger.info("="*70)
    logger.info("Flask CRM Admin User Creation")
    logger.info("="*70)
    logger.info(f"Started at: {start_time.isoformat()}")
    logger.info("")

    # Get admin credentials from environment
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('ADMIN_PASSWORD')

    if not admin_password:
        logger.error("✗ ADMIN_PASSWORD environment variable not set")
        logger.error("Please set ADMIN_PASSWORD in Secret Manager")
        sys.exit(1)

    # Validate password strength
    if len(admin_password) < 8:
        logger.error("✗ Admin password must be at least 8 characters long")
        sys.exit(1)

    logger.info(f"Admin username: {admin_username}")
    logger.info(f"Admin email: {admin_email}")
    logger.info(f"Password length: {len(admin_password)} characters")
    logger.info("")

    # Create Flask app
    logger.info("[1/5] Creating Flask application...")
    try:
        app = create_app()
        logger.info("✓ Flask application created")
    except Exception as e:
        logger.error(f"✗ Failed to create Flask app: {str(e)}")
        sys.exit(1)

    # Test database connection
    logger.info("\n[2/5] Testing database connection...")
    if not check_database_connection(app):
        logger.error("Cannot proceed without database connection")
        sys.exit(1)

    # Create admin user
    logger.info("\n[3/5] Creating admin user...")
    if not create_admin_user(app, admin_username, admin_email, admin_password):
        logger.error("Failed to create admin user")
        sys.exit(1)

    # Create default users (optional - only if CREATE_DEFAULT_USERS=true)
    if os.getenv('CREATE_DEFAULT_USERS', 'false').lower() == 'true':
        logger.info("\n[4/5] Creating default users...")
        create_default_users(app)
    else:
        logger.info("\n[4/5] Skipping default users creation (set CREATE_DEFAULT_USERS=true to enable)")

    # Verify admin user
    logger.info("\n[5/5] Verifying admin user...")
    if not verify_admin_user(app, admin_username):
        logger.error("Admin user verification failed")
        sys.exit(1)

    # List all users
    logger.info("\n")
    list_all_users(app)

    # Success
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("")
    logger.info("="*70)
    logger.info("✓ Admin user creation completed successfully!")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Completed at: {end_time.isoformat()}")
    logger.info("")
    logger.info(f"You can now login with:")
    logger.info(f"  Username: {admin_username}")
    logger.info(f"  Password: <the password you set in ADMIN_PASSWORD>")
    logger.info("="*70)

    sys.exit(0)


if __name__ == '__main__':
    main()
