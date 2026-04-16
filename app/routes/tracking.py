import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Company, NFEData, NFEEmitente, NFEDestinatario, PurchaseOrder
from config import Config
from app.routes.routes import bp



@bp.route('/tracked_companies', methods=['GET'])
@login_required
def get_tracked_companies():
    """Get all tracked companies (for NFE sync)."""
    from app.models import Company
    
    companies = Company.query.order_by(Company.name).all()
    
    return jsonify({
        'companies': [{
            'id': c.id,
            'cod_emp1': c.cod_emp1,
            'name': c.name,
            'cnpj': c.cnpj,
            'fantasy_name': c.fantasy_name,
            'city': c.city,
            'state': c.state,
        } for c in companies]
    }), 200



@bp.route('/tracked_companies', methods=['POST'])
@login_required
def add_tracked_company():
    """Add a new company to track for NFE sync."""
    from app.models import Company
    
    data = request.get_json()
    cnpj = data.get('cnpj', '').strip()
    name = data.get('name', '').strip()
    cod_emp1 = data.get('cod_emp1', '').strip()
    
    if not cnpj:
        return jsonify({'error': 'CNPJ is required'}), 400
    
    if not cod_emp1:
        return jsonify({'error': 'Código da empresa (cod_emp1) is required'}), 400
    
    # Clean CNPJ
    cnpj_clean = ''.join(filter(str.isdigit, cnpj))
    
    if len(cnpj_clean) != 14:
        return jsonify({'error': 'CNPJ must have 14 digits'}), 400
    
    # Check if CNPJ already exists
    existing = Company.query.filter_by(cnpj=cnpj_clean).first()
    if existing:
        return jsonify({'error': 'Company with this CNPJ already exists'}), 400
    
    # Check if cod_emp1 already exists
    existing_cod = Company.query.filter_by(cod_emp1=cod_emp1).first()
    if existing_cod:
        return jsonify({'error': f'Company with cod_emp1 "{cod_emp1}" already exists'}), 400
    
    try:
        company = Company(
            cod_emp1=cod_emp1,
            cnpj=cnpj_clean,
            name=name or f'Empresa {cod_emp1}',
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Company added successfully',
            'company': {
                'id': company.id,
                'cod_emp1': company.cod_emp1,
                'name': company.name,
                'cnpj': company.cnpj,
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/tracked_companies/<int:company_id>', methods=['DELETE'])
@login_required
def remove_tracked_company(company_id):
    """Remove a company from tracking."""
    from app.models import Company
    
    company = db.session.get(Company, company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        db.session.delete(company)
        db.session.commit()
        return jsonify({'message': 'Company removed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




@bp.route('/tracked_companies/<int:company_id>/nfe_count', methods=['GET'])
@login_required
def get_company_nfe_count(company_id):
    """Get NFE count for a company from database."""
    from app.models import Company, NFEData, NFEEmitente
    
    company = db.session.get(Company, company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        # Count NFEs where this company's CNPJ is either emitente or destinatário
        cnpj_clean = ''.join(filter(str.isdigit, company.cnpj)) if company.cnpj else ''
        
        if not cnpj_clean:
            nfe_count = 0
        else:
            # Count NFEs where company is emitente (sender)
            nfe_count_emitente = db.session.query(NFEData).join(
                NFEEmitente, NFEData.id == NFEEmitente.nfe_id
            ).filter(
                NFEEmitente.cnpj.ilike(f'%{cnpj_clean}%') 
            ).count()
            
            # Count NFEs where company is destinatário (receiver)
            nfe_count_destinatario = db.session.query(NFEData).join(
                NFEDestinatario, NFEData.id == NFEDestinatario.nfe_id
            ).filter(
                NFEDestinatario.cnpj.ilike(f'%{cnpj_clean}%')
            ).count()
            
            # Get unique NFE IDs (in case same NFE appears in both - shouldn't happen but just in case)
            nfe_ids_emitente = set(nfe.id for nfe in db.session.query(NFEData.id).join(
                NFEEmitente, NFEData.id == NFEEmitente.nfe_id
            ).filter(
                NFEEmitente.cnpj.ilike(f'%{cnpj_clean}%')
            ).all())
            
            nfe_ids_destinatario = set(nfe.id for nfe in db.session.query(NFEData.id).join(
                NFEDestinatario, NFEData.id == NFEDestinatario.nfe_id
            ).filter(
                NFEDestinatario.cnpj.ilike(f'%{cnpj_clean}%')
            ).all())
            
            # Total unique NFEs
            nfe_count = len(nfe_ids_emitente | nfe_ids_destinatario)
        
        return jsonify({
            'company_id': company_id,
            'company_name': company.name,
            'cnpj': company.cnpj,
            'nfe_count': nfe_count,
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@bp.route('/tracked_companies/check_nfe_available', methods=['POST'])
@login_required
def check_nfe_available():
    """Check how many NFEs are available in SIEG for a CNPJ in a date range."""
    import requests
    from config import Config
    from datetime import datetime
    
    data = request.get_json()
    cnpj = data.get('cnpj', '').strip()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not cnpj:
        return jsonify({'error': 'CNPJ is required'}), 400
    
    cnpj_clean = ''.join(filter(str.isdigit, cnpj))
    
    if not start_date or not end_date:
        return jsonify({'error': 'Date range is required'}), 400
    
    try:
        # Call SIEG API to check available NFEs
        sieg_request_data = {
            "XmlType": 1,
            "DataEmissaoInicio": start_date,
            "DataEmissaoFim": end_date,
            "CnpjDest": cnpj_clean,
        }
        
        response = requests.post(
            f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
            json=sieg_request_data,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': f'SIEG API error: {response.status_code}',
                'available': 0
            }), 200
        
        result = response.json()
        count = len(result.get('xmls', []))
        
        return jsonify({
            'cnpj': cnpj_clean,
            'start_date': start_date,
            'end_date': end_date,
            'available': count,
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout', 'available': 0}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'available': 0}), 200




@bp.route('/tracked_companies/<int:company_id>/sync_nfes', methods=['POST'])
@login_required
def sync_company_nfes(company_id):
    """Sync NFEs for a specific company within a date range (15-day chunks)."""
    import requests
    import base64
    import xml.etree.ElementTree as ET
    from config import Config
    from datetime import datetime, timedelta
    from app.models import Company, NFEData
    from app.utils import parse_and_store_nfe_xml
    
    company = db.session.get(Company, company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    if not company.cnpj:
        return jsonify({'error': 'Company has no CNPJ'}), 400
    
    data = request.get_json()
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Date range is required'}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    cnpj_clean = ''.join(filter(str.isdigit, company.cnpj))
    
    total_nfes = 0
    new_nfes = 0
    errors = []
    
    try:
        # Process in 15-day chunks
        current_start = start_date
        chunk_size = timedelta(days=15)
        
        while current_start < end_date:
            current_end = min(current_start + chunk_size, end_date)
            
            chunk_start_str = current_start.strftime('%Y-%m-%d')
            chunk_end_str = current_end.strftime('%Y-%m-%d')
            
            # Call SIEG API
            sieg_request_data = {
                "XmlType": 1,
                "DataEmissaoInicio": chunk_start_str,
                "DataEmissaoFim": chunk_end_str,
                "CnpjDest": cnpj_clean,
            }
            
            response = requests.post(
                f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
                json=sieg_request_data,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=60
            )
            
            if response.status_code != 200:
                errors.append(f'Error fetching NFEs for {chunk_start_str} to {chunk_end_str}')
                current_start = current_end
                continue
            
            result = response.json()
            xmls = result.get('xmls', [])
            
            for xml_base64 in xmls:
                try:
                    xml_content = base64.b64decode(xml_base64).decode('utf-8')
                    
                    # Parse XML to get access key
                    root = ET.fromstring(xml_content)
                    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    chave_elem = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                    if chave_elem is None or not chave_elem.text:
                        continue
                    
                    chave = chave_elem.text
                    
                    # Check if already exists
                    existing = NFEData.query.filter_by(chave=chave).first()
                    if existing:
                        total_nfes += 1
                        continue
                    
                    # Store NFE
                    parse_and_store_nfe_xml(xml_content)
                    new_nfes += 1
                    total_nfes += 1
                    
                except Exception as e:
                    errors.append(f'Error processing NFE: {str(e)}')
                    continue
            
            current_start = current_end
        
        return jsonify({
            'status': 'success',
            'company_id': company_id,
            'company_name': company.name,
            'total_processed': total_nfes,
            'new_nfes': new_nfes,
            'already_existed': total_nfes - new_nfes,
            'errors': errors[:10] if errors else [],  # Limit errors returned
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@bp.route('/tracked_companies/<int:company_id>/sync_chunk', methods=['POST'])
@login_required
def sync_company_nfes_chunk(company_id):
    """Sync a single 15-day chunk of NFEs for a company. Returns progress info."""
    import requests
    import base64
    import xml.etree.ElementTree as ET
    from config import Config
    from datetime import datetime
    from app.models import Company, NFEData
    from app.utils import parse_and_store_nfe_xml
    
    company = db.session.get(Company, company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    if not company.cnpj:
        return jsonify({'error': 'Company has no CNPJ'}), 400
    
    data = request.get_json()
    chunk_start = data.get('chunk_start')
    chunk_end = data.get('chunk_end')
    
    if not chunk_start or not chunk_end:
        return jsonify({'error': 'Chunk dates are required'}), 400
    
    cnpj_clean = ''.join(filter(str.isdigit, company.cnpj))
    
    new_nfes = 0
    already_existed = 0
    errors = []
    
    try:
        sieg_request_data = {
            "XmlType": 1,
            "DataEmissaoInicio": chunk_start,
            "DataEmissaoFim": chunk_end,
            "CnpjDest": cnpj_clean,
        }
        
        response = requests.post(
            f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
            json=sieg_request_data,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            timeout=60
        )
        
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'error': f'SIEG API error: {response.status_code}',
                'chunk_start': chunk_start,
                'chunk_end': chunk_end,
            }), 200
        
        result = response.json()
        xmls = result.get('xmls', [])
        
        for xml_base64 in xmls:
            try:
                xml_content = base64.b64decode(xml_base64).decode('utf-8')
                
                root = ET.fromstring(xml_content)
                ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                
                chave_elem = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                if chave_elem is None or not chave_elem.text:
                    continue
                
                chave = chave_elem.text
                
                existing = NFEData.query.filter_by(chave=chave).first()
                if existing:
                    already_existed += 1
                    continue
                
                parse_and_store_nfe_xml(xml_content)
                new_nfes += 1
                
            except Exception as e:
                errors.append(str(e))
                continue
        
        return jsonify({
            'status': 'success',
            'chunk_start': chunk_start,
            'chunk_end': chunk_end,
            'found': len(xmls),
            'new_nfes': new_nfes,
            'already_existed': already_existed,
            'errors': len(errors),
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e),
            'chunk_start': chunk_start,
            'chunk_end': chunk_end,
        }), 200

