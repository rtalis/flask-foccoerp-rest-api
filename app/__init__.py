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

    # Session token validation - checks if user logged in from another device
    @app.before_request
    def validate_session_token():
        # Skip validation for login, logout, and static files
        if request.endpoint in ('auth.login', 'auth.logout', 'auth.register', 'static'):
            return None
        if request.path.startswith('/auth/login') or request.path.startswith('/auth/logout'):
            return None
            
        # Only check for authenticated users
        if current_user.is_authenticated:
            session_token = request.cookies.get('session_token')
            # If user has a session_token set and it doesn't match the cookie, they were logged out
            if current_user.session_token and session_token != current_user.session_token:
                return jsonify({
                    'error': 'Session invalidated',
                    'code': 'SESSION_INVALIDATED',
                    'message': 'Você foi desconectado porque fez login em outro dispositivo.'
                }), 403
        
        return None

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
