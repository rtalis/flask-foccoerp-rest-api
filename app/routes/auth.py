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


def _extract_client_ip(req):
    forwarded_for = req.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return req.remote_addr


def _extract_user_agent(req):
    return req.headers.get('User-Agent', '')


def _record_login_event(user, req, method='password'):
    ip_address = _extract_client_ip(req)
    user_agent = _extract_user_agent(req)
    login_history = LoginHistory(
        user_id=user.id,
        login_time=datetime.now(),
        login_ip=ip_address,
        login_user_agent=user_agent,
        login_method=method
    )
    db.session.add(login_history)
    db.session.commit()
    return login_history


def _record_logout_event(user, req):
    ip_address = _extract_client_ip(req)
    user_agent = _extract_user_agent(req)
    last_login = (
        LoginHistory.query
        .filter_by(user_id=user.id)
        .order_by(LoginHistory.login_time.desc())
        .first()
    )
    if last_login and last_login.logout_time is None:
        last_login.logout_time = datetime.now()
        last_login.logout_ip = ip_address
        last_login.logout_user_agent = user_agent
        db.session.commit()
        return last_login
    return None

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("2 per 5 seconds")
def login():
    data = request.get_json()
    email = data.get('email', '').lower()
    password = data.get('password')
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        login_history = _record_login_event(user, request, method='password')
        send_login_notification_email(user, login_history.login_ip)

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
    system_name = data.get('system_name', '')

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
        allowed_screens=allowed_screens,
        system_name=system_name
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/logout', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def logout():
    _record_logout_event(current_user, request)
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

def _user_from_authorization(req):
    auth_header = req.headers.get('Authorization') if req else None
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    token = parts[1]
    try:
        data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None

    return User.query.filter_by(email=data.get('sub')).first()


@login_manager.request_loader
def load_user_from_request(req):
    user = _user_from_authorization(req)
    if user:
        return user
    return None


@auth_bp.route('/login_by_token', methods=['POST'])
@limiter.limit("2 per 5 seconds")
def login_by_token():
    user = _user_from_authorization(request)
    if not user:
        return jsonify({'error': 'Invalid or expired token'}), 401

    login_user(user)
    _record_login_event(user, request, method='jwt_token')
    return jsonify({'message': 'Logged in successfully'}), 200

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


@auth_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    # Only admins can view users
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
        
    users = User.query.all()
    result = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'purchaser_name': user.purchaser_name,
        'system_name': user.system_name,
        'initial_screen': user.initial_screen,
        'allowed_screens': user.allowed_screens
    } for user in users]
    
    return jsonify(result), 200

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    # Only admins can update users
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json() or {}
    
    # Update fields if provided
    if 'username' in data and data['username']:
        username = data['username'].lower()
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = username
        
    if 'email' in data and data['email']:
        email = data['email'].lower()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = email
        
    if 'password' in data and data['password']:
        user.password = generate_password_hash(data['password'])
        
    if 'role' in data:
        user.role = data['role']
        
    if 'purchaser_name' in data:
        user.purchaser_name = data['purchaser_name']
        
    if 'system_name' in data:
        user.system_name = data['system_name']
        
    if 'initial_screen' in data:
        user.initial_screen = data['initial_screen']
        
    if 'allowed_screens' in data:
        user.allowed_screens = data['allowed_screens']

    if 'system_name' in data:
        user.system_name = data['system_name']

    db.session.commit()
    return jsonify({'message': 'User updated successfully'}), 200

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    # Only admins can delete users
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
        
    # Prevent deleting the main admin user
    if user_id == 1000:
        return jsonify({'error': 'Cannot delete the main administrator account'}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200