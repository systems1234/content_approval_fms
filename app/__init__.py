from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth
from config import config

login_manager = LoginManager()
csrf = CSRFProtect()
oauth = OAuth()

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Add built-in functions to Jinja2 environment
    app.jinja_env.globals.update(min=min, max=max)

    # Initialize extensions
    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    if app.config['GOOGLE_SSO_ENABLED']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    from app.bigquery_store import BigQueryStore
    app.extensions['bigquery_store'] = BigQueryStore(app)

    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Import and register blueprints
    from app.routes_bigquery import main_bp
    app.register_blueprint(main_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    from flask import current_app
    return current_app.extensions['bigquery_store'].user(user_id=int(user_id))
