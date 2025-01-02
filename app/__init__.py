from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    with app.app_context():
        from .routes import routes
        from .routes import auth
        app.register_blueprint(routes.bp, url_prefix='/api')
        app.register_blueprint(auth.auth_bp, url_prefix='/auth')
        db.create_all()
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))