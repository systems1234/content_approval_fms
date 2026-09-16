from datetime import datetime

from authlib.integrations.flask_client import OAuth
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import Config

login_manager = LoginManager()
csrf = CSRFProtect()
oauth = OAuth()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    login_manager.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = 'main.signin'
    login_manager.login_message = 'Sign in to continue.'
    login_manager.login_message_category = 'warn'

    if app.config['SSO_READY']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    from app.store import Store
    app.extensions['store'] = Store(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    _register_filters(app)
    _register_errors(app)
    return app


def _register_filters(app):
    @app.template_filter('dt')
    def _dt(value, fmt='%d %b %Y, %H:%M'):
        return value.strftime(fmt) if isinstance(value, datetime) else '—'

    @app.template_filter('ago')
    def _ago(value):
        from app.store import now_ist
        if not isinstance(value, datetime):
            return '\u2014'
        seconds = max(0.0, (now_ist() - value).total_seconds())
        if seconds < 90:
            return 'just now'
        minutes = seconds / 60
        if minutes < 60:
            return f'{int(minutes)}m ago'
        hours = minutes / 60
        if hours < 24:
            return f'{int(hours)}h ago'
        days = hours / 24
        if days < 14:
            return f'{int(days)}d ago'
        return f'{int(days // 7)}w ago'

    @app.template_filter('words')
    def _words(value):
        return len((value or '').split())


def _register_errors(app):
    def page(code, heading, body):
        return render_template('error.html', code=code, heading=heading, body=body), code

    @app.errorhandler(403)
    def _403(_):
        return page(403, 'Not your call',
                    'Your role does not cover this screen. Ask an admin if that looks wrong.')

    @app.errorhandler(404)
    def _404(_):
        return page(404, 'Nothing here',
                    'That content does not exist, or it was never registered in the workflow.')

    @app.errorhandler(CSRFError)
    def _csrf(_):
        return page(400, 'The page went stale',
                    'Your session expired while this page was open. Reload and try again.')

    @app.errorhandler(500)
    def _500(_):
        return page(500, 'Something broke on our side',
                    'The request did not complete. Try again; if it keeps happening, check the BigQuery credentials.')


@login_manager.user_loader
def load_user(user_id):
    from flask import current_app
    try:
        return current_app.extensions['store'].user(int(user_id))
    except (TypeError, ValueError):
        return None
