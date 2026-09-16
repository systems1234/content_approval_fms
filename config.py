import json
import os

from dotenv import load_dotenv

load_dotenv()

_PROJECT = os.environ.get('BIGQUERY_PROJECT', 'mis-gempundit')
_DATASET = os.environ.get('BIGQUERY_DATASET', 'Content_FMS')

# Our fields <- the AI_Content_Queue columns. Override with AI_COLUMN_MAP only
# if the automation ends up naming things differently.
_DEFAULT_MAP = {
    'category': 'category',
    'content_text': 'ai_draft',
    'content_url': 'ai_draft_url',
    'word_count': 'word_count',
    'search_keywords': 'search_term',
    'search_volume': 'search_volume',
}


def _flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _column_map():
    raw = os.environ.get('AI_COLUMN_MAP', '').strip()
    if not raw:
        return dict(_DEFAULT_MAP)
    try:
        parsed = json.loads(raw)
    except ValueError:
        return dict(_DEFAULT_MAP)
    merged = dict(_DEFAULT_MAP)
    merged.update({str(k): str(v) for k, v in parsed.items() if v})
    return merged


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    BIGQUERY_PROJECT = _PROJECT
    BIGQUERY_DATASET = _DATASET
    USERS_TABLE = 'Users'
    WORKFLOW_TABLE = 'Content_Approval_Workflow'
    SEED_TABLE = 'AI_Content_Queue'

    # Where stage 1 drops its finished rows. Same dataset by default.
    AI_SOURCE_TABLE = os.environ.get(
        'AI_SOURCE_TABLE', f'{_PROJECT}.{_DATASET}.AI_Content_Queue').strip()
    AI_KEY_COLUMN = os.environ.get('AI_KEY_COLUMN', 'unique_key').strip()
    AI_STATUS_COLUMN = os.environ.get('AI_STATUS_COLUMN', 'status').strip()
    AI_COLUMN_MAP = _column_map()
    AI_READY = bool(AI_SOURCE_TABLE and AI_KEY_COLUMN)

    # Sign-in is off while the flow is being reviewed: the app opens straight
    # on the dashboard and you pick who you are acting as from the header.
    # Flip REQUIRE_SIGNIN=1 (with the Google keys set) to turn the gate on.
    REQUIRE_SIGNIN = _flag('REQUIRE_SIGNIN', False)
    DEFAULT_ACTOR_EMAIL = os.environ.get('DEFAULT_ACTOR_EMAIL', 'vivek@gempundit.com').lower()

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', 'gempundit.com').lower()
    SSO_READY = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

    WORKFLOW_API_KEY = os.environ.get('WORKFLOW_API_KEY')

    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SEND_FILE_MAX_AGE_DEFAULT = 31536000
