from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})  # Adicione esta linha para habilitar CORS para uma origem específica


    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp , url_prefix='/api')
        db.create_all()

    return app