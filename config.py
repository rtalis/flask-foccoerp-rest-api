import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'

    SECRET_KEY = os.getenv('SECRET_KEY')
    SESSION_COOKIE_NAME = 'session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Defina como True em produção
    SESSION_COOKIE_SAMESITE = 'Lax'  # Pode ser 'Strict', 'Lax' ou 'None'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)  # Tempo de vida da sessão
    SESSION_COOKIE_DOMAIN = None
    JWT_EXPIRATION_MINUTES = int(os.getenv('JWT_EXPIRATION_MINUTES', 90))  # Tempo de expiração do JWT em minutos
    SIEG_API_KEY = os.getenv('SIEG_API_KEY')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    
    