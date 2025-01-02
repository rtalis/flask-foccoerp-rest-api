from flask import Blueprint, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email').lower()
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        response = make_response(jsonify({'message': 'Logged in successfully'}), 200)
        response.set_cookie('session', request.cookies.get('session'), httponly=True, samesite='Lax')
        return response
    return jsonify({'error': 'Invalid credentials'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    response.delete_cookie('session')
    return response

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username').lower()
    email = data.get('email').lower()
    password = data.get('password')
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    hashed_password = generate_password_hash(password, method='sha256')
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/protected', methods=['GET'])
@login_required
def protected():
    return jsonify({'message': 'This is a protected route'}), 200