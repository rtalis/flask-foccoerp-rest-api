import tempfile
import os
from datetime import datetime
from fuzzywuzzy import process
from flask import request, jsonify
from flask_login import login_required

from app import db
from app.models import Quotation
from app.routes.routes import bp


# PHASE 5 ENDPOINTS

@bp.route('/quotations', methods=['GET'])
@login_required
def get_quotations():
    """Get quotations for a specific item."""
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'error': 'item_id is required'}), 400

    quotations = Quotation.query.order_by(Quotation.fornecedor_descricao).filter_by(item_id=item_id).all()
    result = []
    for quotation in quotations:
        result.append({
            'cod_cot': quotation.cod_cot,
            'dt_emissao': quotation.dt_emissao,
            'fornecedor_id': quotation.fornecedor_id,
            'fornecedor_descricao': quotation.fornecedor_descricao,
            'item_id': quotation.item_id,
            'descricao': quotation.descricao,
            'quantidade': quotation.quantidade,
            'unidade_medida': quotation.unidade_medida,
            'preco_unitario': quotation.preco_unitario,
            'dt_entrega': quotation.dt_entrega,
            'cod_emp1': quotation.cod_emp1
        })

    return jsonify(result), 200


@bp.route('/quotations_fuzzy', methods=['GET'])
@login_required
def get_quotations_fuzzy():
    """Get quotations using fuzzy matching on description."""
    descricao = request.args.get('descricao')
    score_cutoff = int(request.args.get('score_cutoff', 80))
    if not descricao:
        return jsonify({'error': 'Descricao is required'}), 400

    all_quotations = Quotation.query.all()
    descriptions = [quotation.descricao for quotation in all_quotations]
    matches = process.extractBests(descricao, descriptions, limit=30, score_cutoff=score_cutoff)
    matched_quotations = [quotation for quotation in all_quotations if quotation.descricao in [match[0] for match in matches]]

    if not matched_quotations:
        return jsonify({'error': 'No quotations found with the given description'}), 404

    result = []
    for quotation in matched_quotations:
        result.append({
            'cod_cot': quotation.cod_cot,
            'dt_emissao': quotation.dt_emissao,
            'fornecedor_id': quotation.fornecedor_id,
            'fornecedor_descricao': quotation.fornecedor_descricao,
            'item_id': quotation.item_id,
            'descricao': quotation.descricao,
            'quantidade': quotation.quantidade,
            'unidade_medida': quotation.unidade_medida,
            'preco_unitario': quotation.preco_unitario,
            'dt_entrega': quotation.dt_entrega,
            'cod_emp1': quotation.cod_emp1
        })

    return jsonify(result), 200


@bp.route('/quotation_items', methods=['GET'])
@login_required
def get_quotation_items():
    """Get items from a specific quotation."""
    cod_cot = request.args.get('cod_cot')
    if not cod_cot:
        return jsonify({'error': 'cod_cot is required'}), 400

    quotation_items = Quotation.query.filter_by(cod_cot=cod_cot).all()
    if not quotation_items:
        return jsonify({'error': 'No items found for this quotation'}), 404

    items = []
    for item in quotation_items:
        items.append({
            'item_id': item.item_id,
            'descricao': item.descricao,
            'quantidade': item.quantidade,
            'unidade_medida': item.unidade_medida,
            'preco_unitario': item.preco_unitario,
            'total': item.quantidade * item.preco_unitario if item.quantidade and item.preco_unitario else None,
            'dt_entrega': item.dt_entrega,
            'fornecedor_id': item.fornecedor_id,
            'fornecedor_descricao': item.fornecedor_descricao,
            'last_purchase': None,
        })

    return jsonify({
        'cod_cot': cod_cot,
        'dt_emissao': quotation_items[0].dt_emissao,
        'items': items,
    }), 200


@bp.route('/extract_quotation_data', methods=['POST'])
@login_required
def extract_quotation_data():
    """
    Extract quotation data from uploaded files using AI.
    Supports PDF and image formats.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file type
        allowed_types = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_types:
            return jsonify({'error': f'Unsupported file type: {file_ext}. Allowed: {", ".join(allowed_types)}'}), 400
        
        # Save file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            # Use Google Gemini API for content extraction
            import google.generativeai as genai
            from config import Config
            
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            
            # Read file as base64
            with open(temp_path, 'rb') as f:
                file_data = f.read()
            
            import base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determine MIME type
            mime_types = {
                'pdf': 'application/pdf',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            mime_type = mime_types.get(file_ext, 'application/octet-stream')
            
            # Call Gemini API
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """Extract all quotation data from this document. Return a JSON with:
            {
                "quotations": [{
                    "item_id": "...",
                    "descricao": "...",
                    "quantidade": 0,
                    "preco_unitario": 0,
                    "fornecedor_nome": "...",
                    "dt_entrega": "YYYY-MM-DD"
                }],
                "extracted_text": "..."
            }"""
            
            response = model.generate_content([
                {
                    "mime_type": mime_type,
                    "data": file_base64
                },
                prompt
            ])
            
            import json
            result = json.loads(response.text)
            
            return jsonify({
                'status': 'success',
                'quotations': result.get('quotations', []),
                'extracted_text': result.get('extracted_text', '')
            }), 200
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@bp.route('/extract_reference_data', methods=['POST'])
@login_required
def extract_reference_data():
    """
    Extract reference data from uploaded files using AI.
    Supports PDF and image formats.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file type
        allowed_types = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_types:
            return jsonify({'error': f'Unsupported file type: {file_ext}. Allowed: {", ".join(allowed_types)}'}), 400
        
        # Save file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            # Use Google Gemini API for content extraction
            import google.generativeai as genai
            from config import Config
            
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            
            # Read file as base64
            with open(temp_path, 'rb') as f:
                file_data = f.read()
            
            import base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determine MIME type
            mime_types = {
                'pdf': 'application/pdf',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            mime_type = mime_types.get(file_ext, 'application/octet-stream')
            
            # Call Gemini API
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """Extract all reference data from this document. This includes:
            - Item references
            - Product codes  
            - Categories
            - Specifications
            - Pricing information
            - Supplier information
            
            Return a JSON with:
            {
                "references": [{
                    "type": "...",
                    "code": "...",
                    "description": "...",
                    "value": "..."
                }],
                "extracted_text": "..."
            }"""
            
            response = model.generate_content([
                {
                    "mime_type": mime_type,
                    "data": file_base64
                },
                prompt
            ])
            
            import json
            result = json.loads(response.text)
            
            return jsonify({
                'status': 'success',
                'references': result.get('references', []),
                'extracted_text': result.get('extracted_text', '')
            }), 200
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
