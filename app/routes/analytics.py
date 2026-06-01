from datetime import datetime, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, case, func
from app import db
from app.models import LoginHistory, RequestLog, User, ReportCategory
from app.routes.routes import bp


@bp.route('/usage_report', methods=['GET'])
@login_required
def usage_report():
    if getattr(current_user, 'role', 'viewer') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    days = request.args.get('days', 30, type=int)
    days = max(1, min(days, 365))
    cutoff = datetime.now() - __import__('datetime').timedelta(days=days)

    # 1. User Engagement (Logins & Requests)
    users_query = (
        db.session.query(
            User.id,
            User.username,
            User.email,
            func.count(LoginHistory.id.distinct()).label('login_count'),
            func.count(RequestLog.id.distinct()).label('request_count')
        )
        .outerjoin(LoginHistory, and_(LoginHistory.user_id == User.id, LoginHistory.login_time >= cutoff))
        .outerjoin(RequestLog, and_(RequestLog.user_id == User.id, RequestLog.timestamp >= cutoff))
        .group_by(User.id, User.username, User.email)
        .all()
    )

    # 2. General Performance Metrics
    metrics_query = db.session.query(
        func.count(RequestLog.id).label('total_requests'),
        func.sum(case((RequestLog.status_code >= 400, 1), else_=0)).label('total_errors'),
        func.avg(RequestLog.duration_ms).label('avg_duration')
    ).filter(RequestLog.timestamp >= cutoff).first()

    # 3. Time Series: Activity & Health
    daily_stats = (
        db.session.query(
            func.date_trunc('day', RequestLog.timestamp).label('day'),
            func.count(RequestLog.id).label('total_requests'),
            func.sum(case((RequestLog.status_code >= 400, 1), else_=0)).label('error_count'),
            func.avg(RequestLog.duration_ms).label('avg_duration')
        )
        .filter(RequestLog.timestamp >= cutoff)
        .group_by('day')
        .order_by('day')
        .all()
    )

    # 4. Status Code Distribution
    status_distribution = (
        db.session.query(
            RequestLog.status_code,
            func.count(RequestLog.id).label('count')
        )
        .filter(RequestLog.timestamp >= cutoff)
        .group_by(RequestLog.status_code)
        .all()
    )

    # 5. Top Search Terms (from stored search_term in RequestLog)
    search_terms_result = (
        db.session.query(RequestLog.search_term, func.count(RequestLog.id).label('count'))
        .filter(
            RequestLog.timestamp >= cutoff,
            RequestLog.search_term.isnot(None),
            RequestLog.search_term != ''
        )
        .group_by(RequestLog.search_term)
        .order_by(func.count(RequestLog.id).desc())
        .limit(10)
        .all()
    )
    
    top_search_terms = [{'term': s.search_term, 'count': s.count} for s in search_terms_result]

    # 6. Top Endpoints
    raw_endpoints = (
        db.session.query(RequestLog.endpoint, RequestLog.method, RequestLog.status_code)
        .filter(RequestLog.timestamp >= cutoff)
        .all()
    )

    endpoint_counter = {}

    for log in raw_endpoints:
        # Base endpoint grouping (stripping parameters)
        base_path = log.endpoint.split('?')[0] if log.endpoint else '/'
        ep_key = f"{log.method} {base_path}"
        endpoint_counter[ep_key] = endpoint_counter.get(ep_key, 0) + 1

    # Sort dictionaries to get Top 10
    top_endpoints = sorted(endpoint_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    categories = (
        ReportCategory.query
        .order_by(ReportCategory.name)
        .all()
    )

    return jsonify({
        'users': [{
            'user_id': u.id,
            'username': u.username,
            'email': u.email,
            'login_count': u.login_count,
            'request_count': u.request_count
        } for u in users_query],
        
        'metrics': {
            'total_requests': metrics_query.total_requests or 0,
            'total_errors': int(metrics_query.total_errors or 0),
            'avg_duration_ms': round(metrics_query.avg_duration or 0, 2)
        },
        
        'daily_stats': [{
            'date': d.day.isoformat(),
            'requests': d.total_requests,
            'errors': int(d.error_count or 0),
            'avg_duration': round(d.avg_duration or 0, 2)
        } for d in daily_stats],
        
        'status_codes': [{'code': s.status_code or 'Unknown', 'count': s.count} for s in status_distribution],
        'top_endpoints': [{'endpoint': ep[0], 'count': ep[1]} for ep in top_endpoints],
        'top_searches': top_search_terms,
        'report_categories': [{'id': rc.id, 'name': rc.name} for rc in categories],
        'period_days': days,
    }), 200


@bp.route('/admin-email', methods=['GET'])
@login_required
def get_admin_email():
    """Return the admin email address for frontend use."""
    admin_email = current_app.config.get('ADMIN_EMAIL', '')
    return jsonify({'email': admin_email}), 200
