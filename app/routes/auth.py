from flask import Blueprint, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app.models import User, LoginHistory
from app import db, login_manager

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import datetime as dt
from app.utils import send_login_notification_email
from config import Config

auth_bp = Blueprint('auth', __name__)
limiter = Limiter(key_func=get_remote_address)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("2 per 5 seconds")
def login():
    data = request.get_json()
    email = data.get('email', '').lower()
    password = data.get('password')
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        login_history = LoginHistory(user_id=user.id, login_time=datetime.now())
        db.session.add(login_history)
        db.session.commit()
        send_login_notification_email(user, request.remote_addr)

        resp = make_response(jsonify({
            'message': 'Logged in successfully',
            'user': {
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'purchaser_name': user.purchaser_name,
                'initial_screen': user.initial_screen,
                'allowed_screens': user.allowed_screens or []
            }
        }), 200)
        session_cookie = request.cookies.get('session')
        if session_cookie:
            resp.set_cookie('session', session_cookie, httponly=True, samesite='Lax')
        return resp
    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/me', methods=['GET'])
@login_required
@limiter.limit("10 per minute")
def me():
    u = current_user
    return jsonify({
        'username': u.username,
        'email': u.email,
        'role': u.role,
        'purchaser_name': u.purchaser_name,
        'initial_screen': u.initial_screen,
        'allowed_screens': u.allowed_screens or []
    }), 200

@auth_bp.route('/register', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def register():
    # Only admins can register users
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json() or {}
    username = (data.get('username') or '').lower()
    email = (data.get('email') or '').lower()
    password = data.get('password')
    purchaser_name = data.get('purchaser_name')  # optional, from PurchaseOrder.func_nome
    role = data.get('role', 'viewer')
    initial_screen = data.get('initial_screen', '/dashboard')
    allowed_screens = data.get('allowed_screens', ['/dashboard'])

    if not username or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password=hashed_password,
        role=role,
        purchaser_name=purchaser_name,
        initial_screen=initial_screen,
        allowed_screens=allowed_screens
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/logout', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def logout():
    logout_user()
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    response.delete_cookie('session')
    return response




def notify_admin_login(user, ip_address):

    try:
        if Config.ADMIN_EMAIL:
            send_login_notification_email(user, ip_address)

            
    except Exception as e:
        print(f"Erro ao enviar notificação: {str(e)}")

@login_manager.request_loader
@limiter.limit("2 per 5 seconds")
@auth_bp.route('/login_by_token', methods=['POST'])
def login_by_token():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_headers = auth_header.split()
        if len(auth_headers) == 2 and auth_headers[0].lower() == 'bearer':
            token = auth_headers[1]
            try:
                data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
                user = User.query.filter_by(email=data['sub']).first()
                if user:
                    login_user(user)
                    return jsonify({'message': 'Logged in successfully'}), 200
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception) as e:
                return jsonify({'error': 'Invalid or expired token'}), 401
            except (jwt.InvalidTokenError, Exception) as e:
                return jsonify({'error': 'Invalid token'}), 401
        return jsonify({'error': 'Authorization header missing or invalid'}), 401

@auth_bp.route('/generate_jwt_token', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def generate_jwt_token():
    from flask_login import current_user
    
    token = jwt.encode({
        'sub': current_user.email,
        'iat': dt.datetime.now(dt.timezone.utc),
        'exp': dt.datetime.now(tz=dt.timezone.utc) + timedelta(minutes=Config.JWT_EXPIRATION_MINUTES)
    }, Config.SECRET_KEY, algorithm='HS256')
    
    return jsonify({'token': token}), 200

@auth_bp.route('/protected', methods=['GET'])
@login_required
def protected():
    return jsonify({'message': 'This is a protected route'}), 200