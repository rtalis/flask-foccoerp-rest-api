from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
import os
import jwt
import time
from flask_mail import Mail
from datetime import date, datetime
from flask.json.provider import DefaultJSONProvider

mail = Mail()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider that handles date objects properly to avoid timezone issues."""
    
    def default(self, obj):
        if isinstance(obj, date) and not isinstance(obj, datetime):
            # Convert date to datetime at noon to avoid timezone conversion issues
            return datetime.combine(obj, datetime.min.time().replace(hour=12)).isoformat()
        return super().default(obj)

def create_app():
    app = Flask(__name__)
    app.json = CustomJSONProvider(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["2000 per day", "500 per hour"]
    )
    app.config.from_object(Config)
    mail.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    with app.app_context():
        from .routes import routes
        from .routes import auth
        app.register_blueprint(routes.bp, url_prefix='/api')
        app.register_blueprint(auth.auth_bp, url_prefix='/auth')

        db.create_all()

    @app.before_request
    def log_request_start():
        request._start_time = time.time()

    @app.after_request
    def log_request(response):
        if current_user.is_authenticated and hasattr(request, '_start_time'):
            # Skip logging for static files
            if request.path.startswith('/static'):
                return response
            try:
                from app.models import RequestLog
                duration = (time.time() - request._start_time) * 1000
                log = RequestLog(
                    user_id=current_user.id,
                    endpoint=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=round(duration, 2),
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                db.session.rollback()
        return response

    @app.before_request
    def validate_session_token():
        if request.endpoint in ('auth.login', 'auth.logout', 'auth.register', 'static'):
            return None
        if request.path.startswith('/auth/login') or request.path.startswith('/auth/logout'):
            return None

        auth_header = request.headers.get('Authorization', '')
        if auth_header.lower().startswith('bearer '):
            return None
            
        if current_user.is_authenticated:
            session_token = request.cookies.get('session_token')
            if current_user.session_token and session_token != current_user.session_token:
                from flask_login import logout_user
                logout_user()
                return jsonify({
                    'error': 'Session invalidated',
                    'code': 'SESSION_INVALIDATED',
                    'message': 'Você foi desconectado porque fez login em outro dispositivo.'
                }), 403

            # Logic for 60m overall / 15m idle session timeout
            from flask import session
            from datetime import timedelta
            from flask_login import logout_user
            
            now_time = time.time()
            # Try to get the login time from current_user or session
            login_time_dt = current_user.session_token_created_at
            login_time = login_time_dt.timestamp() if login_time_dt else now_time
            if not login_time_dt and 'login_time' in session:
                login_time = session['login_time']
                
            last_action_time = session.get('last_action_time', login_time)

            absolute_limit = login_time + (60 * 60) # 60 minutes from login
            idle_limit = last_action_time + (15 * 60) # 15 minutes from last action
            
            expiration_time = max(absolute_limit, idle_limit)

            if now_time > expiration_time:
                logout_user()
                return jsonify({
                    'error': 'Session expired',
                    'code': 'SESSION_EXPIRED',
                    'message': 'Sua sessão expirou por inatividade ou tempo limite.'
                }), 401
            
            # Update last action time roughly every minute to avoid too many DB writes or cookie rewrites
            if now_time - last_action_time > 60:
                session['last_action_time'] = now_time
                session.modified = True
                
                # Also update in the database so it's not empty
                from datetime import datetime
                from app import db
                current_user.last_action_time = datetime.fromtimestamp(now_time)
                db.session.commit()
                
        return None

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
