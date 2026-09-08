import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    BIGQUERY_PROJECT = os.environ.get('BIGQUERY_PROJECT', 'mis-gempundit')
    BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', 'Content_FMS')
    BIGQUERY_USERS_TABLE = os.environ.get('BIGQUERY_USERS_TABLE', 'Users')
    GCS_BUCKET = os.environ.get('GCS_BUCKET')

    # Google Workspace SSO (Sign in with Google, restricted to one domain)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', 'gempundit.com')
    GOOGLE_SSO_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

    # Shared-secret auth for the external keyword-search / content-writer API webhooks
    WORKFLOW_API_KEY = os.environ.get('WORKFLOW_API_KEY')

    # Flask-WTF configuration
    WTF_CSRF_ENABLED = True

    # Session configuration
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Application settings
    TASKS_PER_PAGE = 10

    # Static files cache busting
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files with versioning

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
