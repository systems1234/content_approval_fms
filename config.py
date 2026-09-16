import json
import os

from dotenv import load_dotenv

load_dotenv()


def _column_map():
    raw = os.environ.get('AI_COLUMN_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in parsed.items() if v}


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    BIGQUERY_PROJECT = os.environ.get('BIGQUERY_PROJECT', 'mis-gempundit')
    BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', 'Content_FMS')
    USERS_TABLE = 'Users'
    WORKFLOW_TABLE = 'Content_Approval_Workflow'

    # Google Workspace SSO. There is no password login, so without these the
    # app cannot let anyone in and says so on the sign-in screen.
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', 'gempundit.com').lower()
    SSO_READY = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

    # Where the AI writes its finished drafts.
    AI_SOURCE_TABLE = os.environ.get('AI_SOURCE_TABLE', '').strip()
    AI_KEY_COLUMN = os.environ.get('AI_KEY_COLUMN', 'unique_key').strip()
    AI_COLUMN_MAP = _column_map()
    AI_READY = bool(AI_SOURCE_TABLE and AI_KEY_COLUMN)

    WORKFLOW_API_KEY = os.environ.get('WORKFLOW_API_KEY')

    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SEND_FILE_MAX_AGE_DEFAULT = 31536000
    PAGE_SIZE = 50
