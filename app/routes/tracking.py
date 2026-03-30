"""
Phase 6: Tracking Endpoints
Contains 7 endpoints for tracking companies and monitoring NFE availability.
"""

import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Company, NFEData, NFEEmitente, NFEDestinatario, PurchaseOrder
from config import Config
from app.routes.routes import bp


# PHASE 6 ENDPOINTS

@bp.route('/tracked_companies', methods=['GET'])
@login_required
def get_tracked_companies():
    """Get list of companies being tracked for NFE updates."""
    try:
        companies = Company.query.filter_by(is_tracked=True).all()
        result = []
        for company in companies:
            result.append({
                'id': company.id,
                'cod_emp1': company.cod_emp1,
                'name': company.name,
                'cnpj': company.cnpj,
                'last_sync': company.last_nfe_sync.isoformat() if company.last_nfe_sync else None,
                'nfe_count': db.session.query(NFEData).filter(
                    NFEData.destinatario_id == company.id
                ).count(),
                'is_tracked': company.is_tracked
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/tracked_companies', methods=['POST'])
@login_required
def add_tracked_company():
    """Add a company to tracking list."""
    try:
        data = request.get_json()
        cod_emp1 = data.get('cod_emp1')
        name = data.get('name')
        cnpj = data.get('cnpj')
        
        if not cod_emp1:
            return jsonify({'error': 'cod_emp1 is required'}), 400
        
        existing = Company.query.filter_by(cod_emp1=cod_emp1).first()
        if existing:
            existing.is_tracked = True
            db.session.commit()
            return jsonify({
                'status': 'updated',
                'message': f'Company {cod_emp1} is now being tracked'
            }), 200
        
        new_company = Company(
            cod_emp1=cod_emp1,
            name=name or f'Company {cod_emp1}',
            cnpj=cnpj,
            is_tracked=True
        )
        db.session.add(new_company)
        db.session.commit()
        
        return jsonify({
            'status': 'created',
            'id': new_company.id,
            'message': f'Company {cod_emp1} has been added to tracking'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/tracked_companies/<int:company_id>', methods=['DELETE'])
@login_required
def remove_tracked_company(company_id):
    """Remove a company from tracking list."""
    try:
        company = db.session.get(Company, company_id)
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        company.is_tracked = False
        db.session.commit()
        
        return jsonify({
            'status': 'removed',
            'message': f'Company {company.cod_emp1} has been removed from tracking'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/company_nfe_count/<string:cod_emp1>', methods=['GET'])
@login_required
def get_company_nfe_count(cod_emp1):
    """Get count of NFEs for a specific company."""
    try:
        company = Company.query.filter_by(cod_emp1=cod_emp1).first()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        nfe_count = db.session.query(NFEData).count()
        
        # Count by date range
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_count = db.session.query(NFEData).filter(
            NFEData.data_emissao >= thirty_days_ago
        ).count()
        
        return jsonify({
            'cod_emp1': cod_emp1,
            'company_name': company.name,
            'total_nfes': nfe_count,
            'nfes_last_30_days': recent_count,
            'last_sync': company.last_nfe_sync.isoformat() if company.last_nfe_sync else None
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/check_nfe_available/<string:cod_emp1>', methods=['GET'])
@login_required
def check_nfe_available(cod_emp1):
    """Check if NFEs are available from SIEG API for a company."""
    try:
        days_back = request.args.get('days_back', default=30, type=int)
        
        company = Company.query.filter_by(cod_emp1=cod_emp1).first()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        # Check recent NFE data availability
        date_cutoff = datetime.now() - timedelta(days=days_back)
        available_nfes = db.session.query(NFEData).filter(
            NFEData.data_emissao >= date_cutoff
        ).all()
        
        return jsonify({
            'cod_emp1': cod_emp1,
            'nfes_available': len(available_nfes),
            'period_days': days_back,
            'data_available': len(available_nfes) > 0,
            'oldest_nfe': min([nfe.data_emissao for nfe in available_nfes]).isoformat() if available_nfes else None,
            'newest_nfe': max([nfe.data_emissao for nfe in available_nfes]).isoformat() if available_nfes else None
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/sync_company_nfes', methods=['POST'])
@login_required
def sync_company_nfes():
    """Sync NFEs from SIEG API for tracked companies."""
    try:
        data = request.get_json() or {}
        cod_emp1 = data.get('cod_emp1')
        days_back = data.get('days_back', default=30, type=int)
        
        if not cod_emp1:
            return jsonify({'error': 'cod_emp1 is required'}), 400
        
        company = Company.query.filter_by(cod_emp1=cod_emp1).first()
        if not company:
            return jsonify({'error': f'Company {cod_emp1} not found'}), 404
        
        # Call SIEG API to get NFEs
        try:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            sieg_response = requests.get(
                f'https://api.sieg.com/BaixarXml',
                params={
                    'cnpj': company.cnpj or cod_emp1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_key': Config.SIEG_API_KEY
                },
                timeout=30
            )
            
            if sieg_response.status_code != 200:
                return jsonify({
                    'error': f'SIEG API error: {sieg_response.status_code}',
                    'details': sieg_response.text
                }), 502
            
            # Process response and store NFE data
            nfe_count = 0
            try:
                from app.utils import parse_and_store_nfe_xml
                nfes_data = sieg_response.json() if sieg_response.headers.get('content-type') == 'application/json' else []
                
                for nfe_xml in nfes_data:
                    parse_and_store_nfe_xml(nfe_xml)
                    nfe_count += 1
            except Exception as parse_error:
                # Continue even if parsing fails for some NFEs
                nfe_count = -1
            
            # Update company sync time
            company.last_nfe_sync = datetime.now()
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'nfes_synced': nfe_count if nfe_count >= 0 else 'unknown',
                'period': f'{days_back} days',
                'company': cod_emp1,
                'last_sync': company.last_nfe_sync.isoformat()
            }), 200
            
        except requests.Timeout:
            return jsonify({'error': 'SIEG API timeout'}), 504
        except requests.RequestException as e:
            return jsonify({'error': f'SIEG API error: {str(e)}'}), 502
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/sync_company_nfes_chunk', methods=['POST'])
@login_required
def sync_company_nfes_chunk():
    """Sync NFEs from SIEG API in chunks for better performance."""
    try:
        data = request.get_json() or {}
        cod_emp1 = data.get('cod_emp1')
        chunk_size = data.get('chunk_size', default=100, type=int)
        offset = data.get('offset', default=0, type=int)
        
        if not cod_emp1:
            return jsonify({'error': 'cod_emp1 is required'}), 400
        
        company = Company.query.filter_by(cod_emp1=cod_emp1).first()
        if not company:
            return jsonify({'error': f'Company {cod_emp1} not found'}), 404
        
        try:
            # Get NFEs from SIEG with offset and limit
            sieg_response = requests.get(
                f'https://api.sieg.com/BaixarXml',
                params={
                    'cnpj': company.cnpj or cod_emp1,
                    'limit': chunk_size,
                    'offset': offset,
                    'api_key': Config.SIEG_API_KEY
                },
                timeout=30
            )
            
            if sieg_response.status_code != 200:
                return jsonify({
                    'error': f'SIEG API error: {sieg_response.status_code}'
                }), 502
            
            nfes_data = sieg_response.json() if sieg_response.headers.get('content-type') == 'application/json' else []
            nfe_count = 0
            
            try:
                from app.utils import parse_and_store_nfe_xml
                for nfe_xml in nfes_data:
                    parse_and_store_nfe_xml(nfe_xml)
                    nfe_count += 1
            except Exception:
                pass
            
            company.last_nfe_sync = datetime.now()
            db.session.commit()
            
            has_more = len(nfes_data) == chunk_size
            
            return jsonify({
                'status': 'success',
                'nfes_synced': nfe_count,
                'chunk_size': chunk_size,
                'offset': offset,
                'has_more': has_more,
                'next_offset': offset + chunk_size if has_more else None,
                'company': cod_emp1
            }), 200
            
        except requests.Timeout:
            return jsonify({'error': 'SIEG API timeout'}), 504
        except requests.RequestException as e:
            return jsonify({'error': f'SIEG API error: {str(e)}'}), 502
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
