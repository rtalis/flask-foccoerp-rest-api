from flask import Blueprint, request, jsonify, make_response, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import secrets
from app.models import User, LoginHistory, UserToken
from app import db, login_manager

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta, timezone
import datetime as dt
from app.utils import send_login_notification_email
from config import Config
from functools import wraps


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
    force = data.get('force', False)  
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        has_existing_session = False
        if user.session_token and user.session_token_created_at:
            session_age = datetime.now() - user.session_token_created_at
            if session_age < current_app.config['PERMANENT_SESSION_LIFETIME']:
                has_existing_session = True
        
        if has_existing_session and not force:
            return jsonify({
                'warning': 'active_session',
                'message': 'Há uma sessão ativa em outro dispositivo. Se você continuar, a outra sessão será encerrada.',
                'requires_confirmation': True
            }), 200
        
        new_session_token = secrets.token_hex(32)
        user.session_token = new_session_token
        user.session_token_created_at = datetime.now()
        db.session.commit()
        
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
        session_lifetime = int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
        resp.set_cookie('session_token', new_session_token, httponly=True, samesite='Lax', max_age=session_lifetime)
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
    # Clear session token to invalidate the session
    current_user.session_token = None
    current_user.session_token_created_at = None
    db.session.commit()
    
    _record_logout_event(current_user, request)
    logout_user()
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    response.delete_cookie('session')
    response.delete_cookie('session_token')
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

    token_record = UserToken.query.filter_by(token=token).first()
    if token_record:
        if token_record.disabled_at is not None:
            return None
        if token_record.expires_at and token_record.expires_at <= datetime.utcnow():
            return None

    return User.query.filter_by(email=data.get('sub')).first()


def _build_jwt_for_user(user, expires_minutes=None):
    if not user:
        return None

    minutes = expires_minutes or Config.JWT_EXPIRATION_MINUTES
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        minutes = Config.JWT_EXPIRATION_MINUTES

    minutes = max(1, minutes)

    now = datetime.now(timezone.utc)
    payload = {
        'sub': user.email,
        'iat': now,
        'exp': now + timedelta(minutes=minutes)
    }

    token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    return token, minutes


def _issue_token_for_user(user, expires_minutes=None, created_by=None):
    token, actual_minutes = _build_jwt_for_user(user, expires_minutes)
    if not token:
        return None, None, None

    now = datetime.utcnow()
    record = UserToken(
        user_id=user.id,
        token=token,
        created_by_id=(created_by.id if created_by else user.id),
        created_at=now,
        expires_at=now + timedelta(minutes=actual_minutes)
    )
    db.session.add(record)
    db.session.commit()
    return token, actual_minutes, record


def _serialize_token_record(record):
    if not record:
        return None

    duration_minutes = None
    if record.created_at and record.expires_at:
        duration_minutes = int((record.expires_at - record.created_at).total_seconds() // 60)

    def _user_payload(u):
        if not u:
            return None
        return {
            'id': u.id,
            'username': u.username,
            'email': u.email,
        }

    return {
        'id': record.id,
        'token': record.token,
        'user': _user_payload(record.user),
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'expires_at': record.expires_at.isoformat() if record.expires_at else None,
        'duration_minutes': duration_minutes,
        'created_by': _user_payload(record.created_by),
        'disabled_at': record.disabled_at.isoformat() if record.disabled_at else None,
        'disabled_by': _user_payload(record.disabled_by),
    }


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _user_from_authorization(request)
        if not user:
            return jsonify({'message': 'Token inválido ou ausente'}), 401
        return f(user, *args, **kwargs)
    return decorated


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
    minutes = (request.get_json() or {}).get('expires_in')
    token, actual_minutes, record = _issue_token_for_user(current_user, minutes, current_user)

    return jsonify({
        'token': token,
        'token_id': record.id,
        'expires_in_minutes': actual_minutes,
        'expires_at': record.expires_at.isoformat()
    }), 200


@auth_bp.route('/users/<int:user_id>/token', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def generate_token_for_user(user_id):
    """Generate a token for a specific user (admin only)"""
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    minutes = (request.get_json() or {}).get('expires_in')
    token, actual_minutes, record = _issue_token_for_user(target_user, minutes, current_user)

    return jsonify({
        'token': token,
        'token_id': record.id,
        'expires_in_minutes': actual_minutes,
        'expires_at': record.expires_at.isoformat()
    }), 200


@auth_bp.route('/tokens', methods=['GET'])
@login_required
@limiter.limit("10 per minute")
def list_tokens():
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    tokens = (
        UserToken.query
        .order_by(UserToken.created_at.desc())
        .all()
    )

    return jsonify([_serialize_token_record(t) for t in tokens]), 200

@auth_bp.route('/tokens/<int:token_id>/disable', methods=['POST'])
@login_required
@limiter.limit("5 per 5 seconds")
def disable_token(token_id):
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    token_record = UserToken.query.get(token_id)
    if not token_record:
        return jsonify({'error': 'Token not found'}), 404

    if token_record.disabled_at is None:
        token_record.disabled_at = datetime.utcnow()
        token_record.disabled_by_id = current_user.id
        db.session.commit()

    return jsonify({
        'message': 'Token disabled',
        'token': _serialize_token_record(token_record)
    }), 200

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

@auth_bp.route('/me', methods=['PUT'])
@login_required
@limiter.limit("5 per minute")
def update_me():
    """Allow users to update their own account info and password"""
    import re
    data = request.get_json() or {}
    user = current_user
    
    # Email validation regex
    email_regex = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    
    # Update username if provided
    if 'username' in data:
        if not data['username'] or not data['username'].strip():
            return jsonify({'error': 'Nome de usuário é obrigatório'}), 400
        username = data['username'].lower().strip()
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user.id:
            return jsonify({'error': 'Nome de usuário já existe'}), 400
        user.username = username
    
    # Update email if provided
    if 'email' in data:
        if not data['email'] or not email_regex.match(data['email']):
            return jsonify({'error': 'Email válido é obrigatório'}), 400
        email = data['email'].lower().strip()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            return jsonify({'error': 'Email já existe'}), 400
        user.email = email
    
    # Update purchaser_name (display name) if provided
    if 'purchaser_name' in data:
        user.purchaser_name = data['purchaser_name']
    
    # Update password if provided (requires current password verification)
    if 'new_password' in data and data['new_password']:
        current_password = data.get('current_password', '')
        if not current_password:
            return jsonify({'error': 'Senha atual é obrigatória'}), 400
        if not check_password_hash(user.password, current_password):
            return jsonify({'error': 'Senha atual incorreta'}), 400
        if len(data['new_password']) < 8:
            return jsonify({'error': 'A nova senha deve ter pelo menos 8 caracteres'}), 400
        user.password = generate_password_hash(data['new_password'])
    
    db.session.commit()
    return jsonify({
        'message': 'Conta atualizada com sucesso',
        'username': user.username,
        'email': user.email,
        'purchaser_name': user.purchaser_name
    }), 200

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