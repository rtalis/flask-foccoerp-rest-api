import os
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:8098@localhost:5432/system')
    SECRET_KEY = 'default_secret_key'
    SESSION_COOKIE_NAME = 'session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Defina como True em produção
    SESSION_COOKIE_SAMESITE = 'Lax'  # Pode ser 'Strict', 'Lax' ou 'None'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)  # Tempo de vida da sessão
    SESSION_COOKIE_DOMAIN = None