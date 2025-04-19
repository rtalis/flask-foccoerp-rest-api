from flask import Blueprint, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import app
from app.models import User
from app import db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
from app.models import LoginHistory
from app.utils import send_login_notification_email
from config import Config

auth_bp = Blueprint('auth', __name__)
limiter = Limiter(key_func=get_remote_address)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 5 seconds")
def login():
    data = request.get_json()
    email = data.get('email').lower()
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password, password):
        login_user(user)
        
        # Registrar o login no histórico
        login_history = LoginHistory(
            user_id=user.id,
            login_time=datetime.now()
        )
        db.session.add(login_history)
        db.session.commit()
        
        # Enviar notificação para o administrador
        notify_admin_login(user, request.remote_addr)
        
        response = make_response(jsonify({'message': 'Logged in successfully'}), 200)
        session_cookie = request.cookies.get('session')
        if session_cookie:
            response.set_cookie('session', session_cookie, httponly=True, samesite='Lax')
        return response
    return jsonify({'error': 'Invalid credentials'}), 401


@auth_bp.route('/logout', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def logout():
    logout_user()
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    response.delete_cookie('session')
    return response

@auth_bp.route('/register', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def register():
    data = request.get_json()
    username = data.get('username').lower()
    email = data.get('email').lower()
    password = data.get('password')
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/protected', methods=['GET'])
@limiter.limit("5 per 5 seconds")
@login_required
def protected():
    return jsonify({'message': 'This is a protected route'}), 200



def notify_admin_login(user, ip_address):

    try:
        if Config.ADMIN_EMAIL:
            send_login_notification_email(user, ip_address)

            
    except Exception as e:
        print(f"Erro ao enviar notificação: {str(e)}")