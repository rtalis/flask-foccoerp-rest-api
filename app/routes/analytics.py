from datetime import datetime, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, func

from app import db
from app.models import LoginHistory, RequestLog, User
from app.routes.routes import bp


@bp.route('/usage_report', methods=['GET'])
@login_required
def usage_report():
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    # Parse date parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    include_import = request.args.get('include_import', 'false').lower() == 'true'
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
    else:
        days = request.args.get('days', 30, type=int)
        if days < 1 or days > 365:
            days = 30
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

    logins_query = (
        db.session.query(
            User.id,
            User.username,
            User.email,
            func.count(LoginHistory.id).label('login_count')
        )
        .outerjoin(LoginHistory, and_(
            LoginHistory.user_id == User.id,
            LoginHistory.login_time >= start_date,
            LoginHistory.login_time <= end_date
        ))
        .group_by(User.id, User.username, User.email)
        .all()
    )

    requests_query = (
        db.session.query(
            User.id,
            User.username,
            func.count(RequestLog.id).label('request_count')
        )
        .outerjoin(RequestLog, and_(
            RequestLog.user_id == User.id,
            RequestLog.timestamp >= start_date,
            RequestLog.timestamp <= end_date
        ))
        .group_by(User.id, User.username)
        .all()
    )

    daily_logins = (
        db.session.query(
            func.date_trunc('day', LoginHistory.login_time).label('day'),
            func.count(LoginHistory.id).label('count')
        )
        .filter(and_(LoginHistory.login_time >= start_date, LoginHistory.login_time <= end_date))
        .group_by('day')
        .order_by('day')
        .all()
    )

    daily_requests = (
        db.session.query(
            func.date_trunc('day', RequestLog.timestamp).label('day'),
            func.count(RequestLog.id).label('count')
        )
        .filter(and_(RequestLog.timestamp >= start_date, RequestLog.timestamp <= end_date))
        .group_by('day')
        .order_by('day')
        .all()
    )

    top_endpoints_query = (
        db.session.query(
            RequestLog.endpoint,
            RequestLog.method,
            func.count(RequestLog.id).label('count')
        )
        .filter(and_(RequestLog.timestamp >= start_date, RequestLog.timestamp <= end_date))
    )
    
    # Filter out api/import by default
    if not include_import:
        top_endpoints_query = top_endpoints_query.filter(RequestLog.endpoint != '/api/import')
    
    top_endpoints = (
        top_endpoints_query
        .group_by(RequestLog.endpoint, RequestLog.method)
        .order_by(func.count(RequestLog.id).desc())
        .limit(10)
        .all()
    )

    requests_map = {r.id: r.request_count for r in requests_query}

    users_data = []
    for row in logins_query:
        users_data.append({
            'user_id': row.id,
            'username': row.username,
            'email': row.email,
            'login_count': row.login_count,
            'request_count': requests_map.get(row.id, 0),
        })

    return jsonify({
        'users': users_data,
        'daily_logins': [{'date': d.day.isoformat(), 'count': d.count} for d in daily_logins],
        'daily_requests': [{'date': d.day.isoformat(), 'count': d.count} for d in daily_requests],
        'top_endpoints': [{'endpoint': e.endpoint, 'method': e.method, 'count': e.count} for e in top_endpoints],
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'include_import': include_import,
    }), 200


@bp.route('/config/admin-email', methods=['GET'])
@login_required
def get_admin_email():
    """Return the admin email address for frontend use."""
    admin_email = current_app.config.get('ADMIN_EMAIL', '')
    return jsonify({'email': admin_email}), 200
