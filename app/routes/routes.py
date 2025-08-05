from urllib import response
from fuzzywuzzy import process, fuzz
from flask import Blueprint, redirect, request, jsonify
import requests
from sqlalchemy import and_, or_
from flask_login import login_user, logout_user, login_required, current_user
from app.models import NFEntry, PurchaseOrder, PurchaseItem, Quotation, User
from app.utils import  apply_adjustments, fuzzy_search, import_rcot0300, import_rfor0302, import_rpdc0250c, import_ruah
from werkzeug.utils import secure_filename
from app import db
import tempfile
import os
from config import Config


bp = Blueprint('api', __name__)


UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xml'}


@bp.route('/purchasers', methods=['GET'])
@login_required
def get_purchasers():
    try:
        purchasers = db.session.query(PurchaseOrder.func_nome).distinct().all()
        purchaser_names = [purchaser[0] for purchaser in purchasers]
        return jsonify(purchaser_names), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/purchases', methods=['GET'])
@login_required
def get_purchases():
    try:
        purchase_orders = PurchaseOrder.query.all()
        result = []
        for order in purchase_orders:
            items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
            order_data = {
                'order_id': order.id,
                'cod_pedc': order.cod_pedc,
                'dt_emis': order.dt_emis,
                'fornecedor_id': order.fornecedor_id,
                'fornecedor_descricao': order.fornecedor_descricao,
                'total_bruto': order.total_bruto,
                'total_liquido': order.total_liquido,
                'total_liquido_ipi': order.total_liquido_ipi,
                'posicao': order.posicao,
                'posicao_hist': order.posicao_hist,
                'observacao': order.observacao,
                'items': [{'item_id': item.id, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in items]
            }
            result.append(order_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@bp.route('/search_items', methods=['GET'])
@login_required
def search_items():
    descricao = request.args.get('descricao')
    item_id = request.args.get('item_id')
    filters = []
    query = PurchaseItem.query
    
    if descricao:
        filters.append(PurchaseItem.descricao.ilike(f'%{descricao}%'))
    if item_id:
        filters.append(PurchaseItem.item_id.ilike(f'%{item_id}%'))

    if filters:
        query = query.filter(or_(*filters))
        items = query.order_by(PurchaseItem.dt_emis.desc()).all()
    else:
        items = PurchaseItem.query.order_by(PurchaseItem.dt_emis.desc()).limit(200).all()
        
    
    result = []
    for item in items:
        item_data = {
            'id': item.id,
            'purchase_order_id': item.purchase_order_id,
            'item_id': item.item_id,
            'linha': item.linha,
            'cod_pedc': item.cod_pedc,
            'descricao': item.descricao,
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario,
            'total': item.total,
            'unidade_medida': item.unidade_medida,
            'dt_entrega': item.dt_entrega,
            'perc_ipi': item.perc_ipi,
            'tot_liquido_ipi': item.tot_liquido_ipi,
            'tot_descontos': item.tot_descontos,
            'tot_acrescimos': item.tot_acrescimos,
            'qtde_canc': item.qtde_canc,
            'qtde_canc_toler': item.qtde_canc_toler,
            'perc_toler': item.perc_toler,
            'qtde_atendida': item.qtde_atendida,
            'qtde_saldo': item.qtde_saldo
        }
        order = PurchaseOrder.query.get(item.purchase_order_id)
        if order:
            item_data['order'] = {
                'order_id': order.id,
                'cod_pedc': order.cod_pedc,
                'dt_emis': order.dt_emis,
                'fornecedor_id': order.fornecedor_id,
                'fornecedor_descricao': order.fornecedor_descricao,
                'total_bruto': order.total_bruto,
                'total_liquido': order.total_liquido,
                'total_liquido_ipi': order.total_liquido_ipi,
                'posicao': order.posicao,
                'posicao_hist': order.posicao_hist,
                'observacao': order.observacao,
                'contato': order.contato,
                'func_nome': order.func_nome,
                'cf_pgto': order.cf_pgto,
            }
        nf_entries = NFEntry.query.filter_by(
            cod_emp1=order.cod_emp1,  
            cod_pedc=item.cod_pedc,  
            linha=item.linha 
        ).all()
        nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id, 'dt_ent': nf_entry.dt_ent} for nf_entry in NFEntry.query.filter_by(cod_emp1=item.purchase_order.cod_emp1, cod_pedc=item.cod_pedc, linha=item.linha).all()]
        item_data['nfes'] = nfes
        result.append(item_data)
    return jsonify(result), 200



@bp.route('/search_purchases', methods=['GET'])
@login_required
def search_purchases():
    cod_pedc = request.args.get('cod_pedc')
    fornecedor_descricao = request.args.get('fornecedor_descricao')
    observacao = request.args.get('observacao')

    query = PurchaseOrder.query
    filters = []

    if cod_pedc:
        filters.append(PurchaseOrder.cod_pedc.ilike(f'%{cod_pedc}%'))
    if fornecedor_descricao:
        filters.append(PurchaseOrder.fornecedor_descricao.ilike(f'%{fornecedor_descricao}%'))
    if observacao:
        filters.append(PurchaseOrder.observacao.ilike(f'%{observacao}%'))

    if filters:
        query = query.filter(or_(*filters))
        orders = query.order_by(PurchaseOrder.dt_emis.desc()).all()
    else:
        orders = PurchaseOrder.query.order_by(PurchaseOrder.dt_emis.desc()).limit(200).all()

    
    result = []
    for order in orders:
        items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
        order_data = {
            'order_id': order.id,
            'cod_pedc': order.cod_pedc,
            'dt_emis': order.dt_emis,
            'fornecedor_id': order.fornecedor_id,
            'fornecedor_descricao': order.fornecedor_descricao,
            'total_bruto': order.total_bruto,
            'total_liquido': order.total_liquido,
            'total_liquido_ipi': order.total_liquido_ipi,
            'posicao': order.posicao,
            'posicao_hist': order.posicao_hist,
            'observacao': order.observacao,
            'contato': order.contato,
            'func_nome': order.func_nome,
            'cf_pgto': order.cf_pgto,
            'items': []
        }

        for item in items:
            nf_entries = NFEntry.query.filter_by(
                cod_emp1=order.cod_emp1,
                cod_pedc=item.cod_pedc,
                linha=item.linha
            ).all()
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id, 'dt_ent': nf_entry.dt_ent} for nf_entry in NFEntry.query.filter_by(cod_emp1=item.purchase_order.cod_emp1, cod_pedc=item.cod_pedc, linha=item.linha).all()]

            item_data = {
                'id': item.id,
                'item_id': item.item_id,
                'descricao': item.descricao,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'total': item.total,
                'unidade_medida': item.unidade_medida,
                'dt_entrega': item.dt_entrega,
                'perc_ipi': item.perc_ipi,
                'tot_liquido_ipi': item.tot_liquido_ipi,
                'tot_descontos': item.tot_descontos,
                'tot_acrescimos': item.tot_acrescimos,
                'qtde_canc': item.qtde_canc,
                'qtde_canc_toler': item.qtde_canc_toler,
                'qtde_atendida': item.qtde_atendida,
                'qtde_saldo': item.qtde_saldo,
                'perc_toler': item.perc_toler,
                'nfes': nfes
            }
            order_data['items'].append(item_data)
        result.append(order_data)
    return jsonify(result), 200

@bp.route('/search_item_id', methods=['GET'])
@login_required
def search_item_id():
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'error': 'Item ID is required'}), 400

    items = PurchaseItem.query.filter_by(item_id=item_id).all()
    result = [{'id': item.id, 'purchase_order_id': item.purchase_order_id, 'item_id': item.item_id, 'linha': item.linha, 'cod_pedc': item.cod_pedc, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in items]
    return jsonify(result), 200

@bp.route('/get_purchase', methods=['GET'])
@login_required
def search_cod_pedc():
    cod_pedc = request.args.get('cod_pedc')
    if not cod_pedc:
        return jsonify({'error': 'COD_PEDC is required'}), 400

    orders = PurchaseOrder.query.filter_by(cod_pedc=cod_pedc).all()
    result = []
    for order in orders:
        #items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
        order_data = {
            'order_id': order.id,
            'cod_pedc': order.cod_pedc,
            'dt_emis': order.dt_emis,
            'fornecedor_id': order.fornecedor_id,
            'fornecedor_descricao': order.fornecedor_descricao,
            'total_bruto': order.total_bruto,
            'total_liquido': order.total_liquido,
            'total_liquido_ipi': order.total_liquido_ipi,
            'posicao': order.posicao,
            'posicao_hist': order.posicao_hist,
            'observacao': order.observacao,
          #  'items': [{'item_id': item.id, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in items]
        }
        result.append(order_data)
    return jsonify(result), 200


@bp.route('/search_fuzzy', methods=['GET'])
@login_required
def search_fuzzy():
    query = request.args.get('query')
    score_cutoff = int(request.args.get('score_cutoff', 80))

    if not query or not score_cutoff:
        return jsonify({'error': 'Query required'}), 400

    all_items = PurchaseItem.query.order_by(PurchaseItem.dt_emis.desc()).all()
    all_orders = PurchaseOrder.query.order_by(PurchaseOrder.dt_emis.desc()).all()
   
    item_descriptions = {item.descricao: item for item in all_items if item.descricao is not None}
    order_observations = {order.observacao: order for order in all_orders if order.observacao is not None}



    item_matches = process.extractBests(str(query), item_descriptions.keys(), score_cutoff=score_cutoff, scorer=fuzz.partial_ratio)
    order_matches = process.extractBests(str(query), order_observations.keys(), score_cutoff=score_cutoff,scorer=fuzz.partial_ratio)
    matched_items = [item for item in all_items if item.descricao in [match[0] for match in item_matches]]
    matched_orders = [order for order in all_orders if order.observacao in [match[0] for match in order_matches]]

    item_result = []
    for item in matched_items:
            item_data = {
                'id': item.id,
                'purchase_order_id': item.purchase_order_id,
                'item_id': item.item_id,
                'linha': item.linha,
                'cod_pedc': item.cod_pedc,
                'descricao': item.descricao,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'total': item.total,
                'unidade_medida': item.unidade_medida,
                'dt_entrega': item.dt_entrega,
                'perc_ipi': item.perc_ipi,
                'tot_liquido_ipi': item.tot_liquido_ipi,
                'tot_descontos': item.tot_descontos,
                'tot_acrescimos': item.tot_acrescimos,
                'qtde_canc': item.qtde_canc,
                'qtde_canc_toler': item.qtde_canc_toler,
                'perc_toler': item.perc_toler,
                'qtde_atendida': item.qtde_atendida,
                'qtde_saldo': item.qtde_saldo
            }
            order = PurchaseOrder.query.get(item.purchase_order_id)
            if order:
                item_data['order'] = {
                    'order_id': order.id,
                    'cod_pedc': order.cod_pedc,
                    'dt_emis': order.dt_emis,
                    'fornecedor_id': order.fornecedor_id,
                    'fornecedor_descricao': order.fornecedor_descricao,
                    'total_bruto': order.total_bruto,
                    'total_liquido': order.total_liquido,
                    'total_liquido_ipi': order.total_liquido_ipi,
                    'posicao': order.posicao,
                    'posicao_hist': order.posicao_hist,
                    'observacao': order.observacao,
                    'contato': order.contato,
                    'func_nome': order.func_nome,
                    'cf_pgto': order.cf_pgto,
                }
            nf_entries = NFEntry.query.filter_by(
                cod_emp1=order.cod_emp1,  
            cod_pedc=item.cod_pedc,  
            linha=item.linha 
            ).all()
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id, 'dt_ent': nf_entry.dt_ent} for nf_entry in NFEntry.query.filter_by(cod_emp1=item.purchase_order.cod_emp1, cod_pedc=item.cod_pedc, linha=item.linha).all()]
            item_data['nfes'] = nfes
            item_result.append(item_data)

    order_result = []
    for order in matched_orders:
        items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
        order_data = {
            'order_id': order.id,
            'cod_pedc': order.cod_pedc,
            'dt_emis': order.dt_emis,
            'fornecedor_id': order.fornecedor_id,
            'fornecedor_descricao': order.fornecedor_descricao,
            'total_bruto': order.total_bruto,
            'total_liquido': order.total_liquido,
            'total_liquido_ipi': order.total_liquido_ipi,
            'posicao': order.posicao,
            'posicao_hist': order.posicao_hist,
            'observacao': order.observacao,
            'contato': order.contato,
            'func_nome': order.func_nome,
            'cf_pgto': order.cf_pgto,
            'items': []
        }

        for item in items:
            nf_entries = NFEntry.query.filter_by(
                cod_emp1=order.cod_emp1,
                cod_pedc=item.cod_pedc,
                linha=item.linha
            ).all()
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id, 'dt_ent': nf_entry.dt_ent} for nf_entry in NFEntry.query.filter_by(cod_emp1=item.purchase_order.cod_emp1, cod_pedc=item.cod_pedc, linha=item.linha).all()]

            item_data = {
                'id': item.id,
                'item_id': item.item_id,
                'descricao': item.descricao,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'total': item.total,
                'unidade_medida': item.unidade_medida,
                'dt_entrega': item.dt_entrega,
                'perc_ipi': item.perc_ipi,
                'tot_liquido_ipi': item.tot_liquido_ipi,
                'tot_descontos': item.tot_descontos,
                'tot_acrescimos': item.tot_acrescimos,
                'qtde_canc': item.qtde_canc,
                'qtde_canc_toler': item.qtde_canc_toler,
                'qtde_atendida': item.qtde_atendida,
                'qtde_saldo': item.qtde_saldo,
                'perc_toler': item.perc_toler,
                'nfes': nfes
            }
            order_data['items'].append(item_data)
            order_result.append(order_data)

    return jsonify({'items': item_result, 'purchases': order_result}), 200

@bp.route('/get_nfe', methods=['GET'])
@login_required
def get_nfentry():
    cod_pedc = request.args.get('cod_pedc')
    linha = request.args.get('linha')

    if not cod_pedc or not linha:
        return jsonify({'error': 'cod_pedc and linha are required'}), 400

    nf_entries = NFEntry.query.join(PurchaseItem).filter(
        PurchaseItem.cod_pedc == cod_pedc,
        PurchaseItem.linha == linha
    ).all()

    if not nf_entries:
        return jsonify({'error': 'No entries found'}), 404

    result = []
    for entry in nf_entries:
        result.append({
            'cod_emp1': entry.cod_emp1,
            'cod_pedc': entry.cod_pedc,
            'linha': entry.linha,
            'num_nf': entry.num_nf,
            'text_field': entry.text_field
        })

    return jsonify(result), 200



@bp.route('/item_details/<id>', methods=['GET'])
@login_required
def get_item_details(id):
    desc_for = ''
    comprador = ''
    item = PurchaseItem.query.filter_by(id=id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    price_history = PurchaseItem.query.order_by(PurchaseItem.dt_emis).filter_by(item_id=item.item_id).all()
    price_history_data = []
    for entry in price_history:
        purchase_data = PurchaseOrder.query.order_by(PurchaseOrder.dt_emis).filter_by(cod_pedc=entry.cod_pedc).first()
        if item.cod_pedc == purchase_data.cod_pedc:
            desc_for = purchase_data.fornecedor_descricao
            comprador = purchase_data.func_nome
        entry.fornecedor_descricao = purchase_data.fornecedor_descricao
        price_history_data.append({'date': entry.dt_emis,
                               'price': entry.preco_unitario,
                               'cod_pedc': entry.cod_pedc,
                               'fornecedor_descricao': purchase_data.fornecedor_descricao})

    item_data = {
        'item_id': item.item_id,
        'descricao': item.descricao,
        'fornecedor_descricao': desc_for,
        'cod_pedc': item.cod_pedc,
        'comprador': comprador,
        'quantidade': item.quantidade,
        'preco_unitario': item.preco_unitario,
        'total': item.total,
    }

    return jsonify({'item': item_data, 'priceHistory': price_history_data}), 200

@bp.route('/quotations', methods=['GET'])
@login_required
def get_quotations():
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
            'preco_unitario': quotation.preco_unitario,
            'dt_entrega': quotation.dt_entrega,
            'cod_emp1': quotation.cod_emp1
        })

    return jsonify(result), 200

@bp.route('/search_item_fuzzy', methods=['GET'])
@login_required
def search_item_fuzzy():
    descricao = request.args.get('descricao')
    score_cutoff = int(request.args.get('score_cutoff', 80))  # Padrão para 80% de similaridade
    if not descricao:
        return jsonify({'error': 'Descricao is required'}), 400

    all_items = PurchaseItem.query.all()
    descriptions = [item.descricao for item in all_items]
    matches = process.extractBests(descricao, descriptions, limit=10, score_cutoff=score_cutoff)
    matched_items = [item for item in all_items if item.descricao in [match[0] for match in matches]]

    if not matched_items:
        return jsonify({'error': 'No items found with the given description'}), 404

    item = matched_items[0]
        #price_history = PurchaseItem.query.filter_by(item_id=item.item_id).all()
    price_history_data = []
    for entry in matched_items:
        purchase_data = PurchaseOrder.query.filter_by(cod_pedc=entry.cod_pedc).first()
        entry.fornecedor_descricao = purchase_data.fornecedor_descricao
        price_history_data.append({'date': entry.dt_emis,
                                'price': entry.preco_unitario,
                                'cod_pedc': entry.cod_pedc,
                                'fornecedor_descricao': purchase_data.fornecedor_descricao})

    item_data = {
        'item_id': item.item_id,
        'descricao': item.descricao,
        'fornecedor_descricao': purchase_data.fornecedor_descricao,
        'cod_pedc': item.cod_pedc,
        'comprador': purchase_data.func_nome,
        'quantidade': item.quantidade,
        'preco_unitario': item.preco_unitario,
        'total': item.total,
    }

    return jsonify({'item': item_data, 'priceHistory': price_history_data}), 200

@bp.route('/quotations_fuzzy', methods=['GET'])
@login_required
def get_quotations_fuzzy():
    descricao = request.args.get('descricao')
    score_cutoff = int(request.args.get('score_cutoff', 80))  # Padrão para 80% de similaridade
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
            'preco_unitario': quotation.preco_unitario,
            'dt_entrega': quotation.dt_entrega,
            'cod_emp1': quotation.cod_emp1
        })

    return jsonify(result), 200

@bp.route('/search_combined', methods=['GET'])
@login_required
def search_combined():
    from sqlalchemy import text

    query = request.args.get('query', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    score_cutoff = int(request.args.get('score_cutoff', 80))
    search_by_cod_pedc = request.args.get('searchByCodPedc', 'false').lower() == 'true'
    search_by_fornecedor = request.args.get('searchByFornecedor', 'false').lower() == 'true'
    search_by_observacao = request.args.get('searchByObservacao', 'false').lower() == 'true'
    search_by_item_id = request.args.get('searchByItemId', 'false').lower() == 'true'
    search_by_descricao = request.args.get('searchByDescricao', 'false').lower() == 'true'
    search_by_func_nome = request.args.get('selectedFuncName')
    min_value = request.args.get('minValue', type=float)
    max_value = request.args.get('maxValue', type=float)
    value_search_type = request.args.get('valueSearchType', 'item')
    value_filters = []
    ignore_diacritics = request.args.get('ignoreDiacritics', 'false').lower() == 'true'

    if ignore_diacritics:
        if db.engine.name == 'postgresql':
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            remove_accents = lambda col: db.func.unaccent(col)

    if min_value is not None or max_value is not None:
        
        if value_search_type == 'item':
            if min_value is not None:
                value_filters.append(PurchaseItem.total >= min_value)
            if max_value is not None:
                value_filters.append(PurchaseItem.total <= max_value)
        else:  #order
            if min_value is not None:
                value_filters.append(PurchaseOrder.total_bruto >= min_value)
            if max_value is not None:
                value_filters.append(PurchaseOrder.total_bruto <= max_value)
        
    
    filters = []
    if query:
        query = query.upper()
        if search_by_cod_pedc:
            filters.append(PurchaseOrder.cod_pedc.ilike(f'%{query}%'))
        if search_by_fornecedor:
            filters.append(PurchaseOrder.fornecedor_descricao.ilike(f'%{query}%'))
        if search_by_observacao:
            filters.append(PurchaseOrder.observacao.ilike(f'%{query}%'))
        if search_by_item_id:
            filters.append(PurchaseItem.item_id.ilike(f'%{query}%'))
        if search_by_descricao:
            filters.append(PurchaseItem.descricao.ilike(f'%{query}%'))
            #filters.append(remove_accents(PurchaseItem.descricao).contains(query))
        if not any([search_by_cod_pedc, search_by_fornecedor, search_by_observacao, search_by_item_id, search_by_descricao]):
            filters.append(or_(
                PurchaseItem.descricao.ilike(f'%{query}%'),
                PurchaseItem.item_id.ilike(f'%{query}%'),
                PurchaseOrder.cod_pedc.ilike(f'%{query}%'),
                PurchaseOrder.fornecedor_descricao.ilike(f'%{query}%'),
                PurchaseOrder.observacao.ilike(f'%{query}%')
            ))

    items_query = PurchaseItem.query.order_by(PurchaseOrder.dt_emis.desc()).join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
    if value_filters:
            filters.append(and_(*value_filters))
    if filters:
        items_query = items_query.filter(or_(*filters))
    if search_by_func_nome != 'todos':
        items_query = items_query.filter(and_(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%')))
    
    if score_cutoff < 100:
        fuzzy_query = PurchaseItem.query.order_by(PurchaseOrder.dt_emis.desc()).join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
        if search_by_func_nome != 'todos':
            fuzzy_query =  fuzzy_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))
        if value_filters:
            fuzzy_query = fuzzy_query.filter(and_(*value_filters))
        items = fuzzy_query.all()
        items = fuzzy_search(query, items, score_cutoff, search_by_descricao, search_by_observacao)
    else:
        items_paginated = items_query.paginate(page=page, per_page=per_page, count=True)
        items = items_paginated.items

    grouped_results = {}
    for item in items:
        cod_pedc = item.cod_pedc
        if cod_pedc not in grouped_results:
            order = item.purchase_order
            adjustments = order.adjustments  
            base_total = order.total_pedido_com_ipi or 0
            adjusted_total = apply_adjustments(base_total, adjustments)
            grouped_results[cod_pedc] = {
                'order': {
                    'order_id': item.purchase_order_id,
                    'cod_pedc': item.cod_pedc,
                    'dt_emis': item.purchase_order.dt_emis,
                    'fornecedor_id': item.purchase_order.fornecedor_id,
                    'fornecedor_descricao': item.purchase_order.fornecedor_descricao,
                    'total_bruto': item.purchase_order.total_bruto,
                    'total_pedido_com_ipi': item.purchase_order.total_pedido_com_ipi,
                    'adjusted_total': adjusted_total,
                    'adjustments': [
                        {
                            'tp_apl': adj.tp_apl,
                            'tp_dctacr1': adj.tp_dctacr1,
                            'tp_vlr1': adj.tp_vlr1,
                            'vlr1': adj.vlr1,
                            'order_index': adj.order_index
                        } for adj in adjustments
                    ],
                    'total_liquido': item.purchase_order.total_liquido,
                    'total_liquido_ipi': item.purchase_order.total_liquido_ipi,
                    'posicao': item.purchase_order.posicao,
                    'posicao_hist': item.purchase_order.posicao_hist,
                    'observacao': item.purchase_order.observacao,
                    'contato': item.purchase_order.contato,
                    'func_nome': item.purchase_order.func_nome,
                    'cf_pgto': item.purchase_order.cf_pgto,
                    'cod_emp1': item.purchase_order.cod_emp1,
                    
                    'nfes': [
                        {
                            'num_nf': nf_entry.num_nf,
                            'id': nf_entry.id,
                            'dt_ent': nf_entry.dt_ent
                        } for nf_entry in NFEntry.query.filter_by(cod_emp1=item.purchase_order.cod_emp1, cod_pedc=item.cod_pedc, linha=item.linha).all()]
                },
                'items': []
            }
        item_data = {
            'id': item.id,
            'item_id': item.item_id,
            'descricao': item.descricao,
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario,
            'total': item.total,
            'unidade_medida': item.unidade_medida,
            'dt_entrega': item.dt_entrega,
            'perc_ipi': item.perc_ipi,
            'tot_liquido_ipi': item.tot_liquido_ipi,
            'tot_descontos': item.tot_descontos,
            'tot_acrescimos': item.tot_acrescimos,
            'qtde_canc': item.qtde_canc,
            'qtde_canc_toler': item.qtde_canc_toler,
            'perc_toler': item.perc_toler,
            'qtde_atendida': item.qtde_atendida,
            'qtde_saldo': item.qtde_saldo,
        }
        grouped_results[cod_pedc]['items'].append(item_data)

    if score_cutoff < 100:
        total_pages = 1
        current_page = 1
    else:
        total_pages = items_paginated.pages
        current_page = items_paginated.page

    return jsonify({
        'purchases': list(grouped_results.values()),
        'total_pages': total_pages,
        'current_page': current_page
    }), 200
    
@bp.route('/last_update', methods=['GET'])
@login_required
def get_last_update():
    try:
        last_order = PurchaseOrder.query.order_by(PurchaseOrder.dt_emis.desc()).first()
        if last_order:
            return jsonify({
                'last_updated': last_order.dt_emis
            }), 200
        return jsonify({'error': 'No orders found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@bp.route('/count_results', methods=['GET'])
@login_required
def count_results():
    search_by_func_nome = request.args.get('selectedFuncName')
    score_cutoff = int(request.args.get('score_cutoff', 80))
    search_by_cod_pedc = request.args.get('searchByCodPedc', 'false').lower() == 'true'
    search_by_fornecedor = request.args.get('searchByFornecedor', 'false').lower() == 'true'
    search_by_observacao = request.args.get('searchByObservacao', 'false').lower() == 'true'
    search_by_item_id = request.args.get('searchByItemId', 'false').lower() == 'true'
    search_by_descricao = request.args.get('searchByDescricao', 'false').lower() == 'true'

    count_query = db.session.query(db.func.count(db.distinct(PurchaseItem.cod_pedc))).\
        join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)

    if search_by_func_nome != 'todos':
        count_query = count_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))

    base_count = count_query.scalar()

    multiplier = sum([
        search_by_cod_pedc,
        search_by_fornecedor,
        search_by_observacao,
        search_by_item_id,
        search_by_descricao
    ])
    
    if multiplier == 0:
        multiplier = 5

    estimated_count = base_count * multiplier

    return jsonify({
        'count': estimated_count,
        'estimated_pages': (estimated_count + 199) // 200  # 200 itens por página
    }), 200
    
    
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_chunk', methods=['POST'])
@login_required
def upload_chunk():

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    chunk_index = int(request.form['chunkIndex'])
    file_id = request.form['fileId']

    try:
        chunk_dir = os.path.join(UPLOAD_FOLDER, file_id)
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}')
        file.save(chunk_path)

        return jsonify({'message': 'Chunk uploaded successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/process_file', methods=['POST'])
@login_required
def process_file():
    file_id = request.json.get('fileId')
    if not file_id:
        return jsonify({'error': 'No file ID provided'}), 400

    chunk_dir = os.path.join(UPLOAD_FOLDER, file_id)
    if not os.path.exists(chunk_dir):
        return jsonify({'error': 'File chunks not found'}), 404

    try:
        chunks = sorted(os.listdir(chunk_dir), key=lambda x: int(x.split('_')[1]))
        final_file_path = os.path.join(UPLOAD_FOLDER, f'{file_id}_complete.xml')
        with open(final_file_path, 'wb') as outfile:
            for chunk_name in chunks:
                chunk_path = os.path.join(chunk_dir, chunk_name)
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())

        with open(final_file_path, 'rb') as f:
            content = f.read()
            if not is_valid_xml(content):
                raise ValueError('Invalid XML file')

            if b'<RPDC0250_RUAH>' in content or b'<RPDC0250>' in content:
                result = import_ruah(content)
            elif b'<RPDC0250C>' in content:
                result = import_rpdc0250c(content)
            elif b'<RCOT0300>' in content:
                result = import_rcot0300(content)
            elif b'<RFOR0302>' in content:
                result = import_rfor0302(content)
            else:
                raise ValueError('Arquivo XML invalido ou não suportado')

        return result

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

    finally:
        import shutil
        shutil.rmtree(chunk_dir, ignore_errors=True)
        if os.path.exists(final_file_path):
            os.remove(final_file_path)

def is_valid_xml(content):
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(content)
        return True
    except ET.ParseError:
        return False
    
    
# Old endpoint for importing XML files
@bp.route('/import', methods=['POST'])
@login_required
def import_xml():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        file_content = file.read()  # Leia o conteúdo do arquivo
        if b'<RPDC0250_RUAH>' in file_content or b'<RPDC0250>' in file_content:            
            return import_ruah(file_content)
        elif b'<RPDC0250C>' in file_content:
            return import_rpdc0250c(file_content)
        elif b'<RCOT0300>' in file_content:
            return import_rcot0300(file_content)
        elif b'<RFOR0302>' in file_content:
            return import_rfor0302(file_content)
        else:
            return jsonify({'error': 'Invalid XML header'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
    
@bp.route('/purchase_by_nf', methods=['GET'])
@login_required
def get_purchase_by_nf():
    num_nf = request.args.get('num_nf')
    if not num_nf:
        return jsonify({'error': 'num_nf is required'}), 400

    nf_entry = NFEntry.query.filter_by(num_nf=num_nf).first()
    if not nf_entry:
        return jsonify({'error': 'Nota fiscal não encontrada'}), 404

    # Encontrar o item de compra relacionado
    item = PurchaseItem.query.filter_by(
        cod_pedc=nf_entry.cod_pedc,
        linha=nf_entry.linha,
        cod_emp1=nf_entry.cod_emp1
    ).first()
    if not item:
        return jsonify({'error': 'Item relacionado não encontrado'}), 404

    # Encontrar o pedido de compra relacionado
    order = PurchaseOrder.query.filter_by(
        cod_pedc=item.cod_pedc,
        cod_emp1=item.cod_emp1
    ).first()
    if not order:
        return jsonify({'error': 'Pedido de compra não encontrado'}), 404

    # Buscar todos os itens do pedido
    items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
    items_data = []
    for i in items:
        items_data.append({
            'id': i.id,
            'item_id': i.item_id,
            'descricao': i.descricao,
            'quantidade': i.quantidade,
            'preco_unitario': i.preco_unitario,
            'total': i.total,
            'unidade_medida': i.unidade_medida,
            'dt_entrega': i.dt_entrega,
            'perc_ipi': i.perc_ipi,
            'tot_liquido_ipi': i.tot_liquido_ipi,
            'tot_descontos': i.tot_descontos,
            'tot_acrescimos': i.tot_acrescimos,
            'qtde_canc': i.qtde_canc,
            'qtde_canc_toler': i.qtde_canc_toler,
            'qtde_atendida': i.qtde_atendida,
            'qtde_saldo': i.qtde_saldo,
            'perc_toler': i.perc_toler
        })

    order_data = {
        'order_id': order.id,
        'cod_pedc': order.cod_pedc,
        'dt_emis': order.dt_emis,
        'fornecedor_id': order.fornecedor_id,
        'fornecedor_descricao': order.fornecedor_descricao,
        'total_bruto': order.total_bruto,
        'total_liquido': order.total_liquido,
        'total_liquido_ipi': order.total_liquido_ipi,
        'posicao': order.posicao,
        'posicao_hist': order.posicao_hist,
        'observacao': order.observacao,
        'contato': order.contato,
        'func_nome': order.func_nome,
        'cf_pgto': order.cf_pgto,
        'cod_emp1': order.cod_emp1,
        'items': items_data
    }

    return jsonify(order_data), 200



@bp.route('/nfe_by_purchase', methods=['GET'])
@login_required
def get_nfe_by_purchase():
    import requests
    import base64
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from app.models import Supplier
    
    cod_pedc = request.args.get('cod_pedc')
    if not cod_pedc:
        return jsonify({'error': 'cod_pedc is required'}), 400
    
    purchase_order = PurchaseOrder.query.filter_by(cod_pedc=cod_pedc).first()
    if not purchase_order:
        return jsonify({'error': 'Purchase order not found'}), 404  

    if purchase_order.fornecedor_id:
        supplier = Supplier.query.filter( 
        (Supplier.cod_for == str(purchase_order.fornecedor_id))
        ).first()
    else:
        return jsonify({'error': 'Fornecedor ID not found in purchase order'}), 400
    
    if supplier and supplier.nvl_forn_cnpj_forn_cpf:
        fornecedor_cnpj = supplier.nvl_forn_cnpj_forn_cpf
    else:
        return jsonify({'error': 'Valid fornecedor CNPJ not found in database'}), 400

    fornecedor_cnpj = ''.join(filter(str.isdigit, str(fornecedor_cnpj)))
    
    start_date = purchase_order.dt_emis
    end_date = datetime.now()
    
    start_date_str = start_date.strftime('%Y-%m-%dT00:00:00.000Z')
    end_date_str = end_date.strftime('%Y-%m-%dT23:59:59.999Z')
    
    sieg_request_data = {
        "XmlType": 1,
        "Take": 0,
        "Skip": 0,
        "DataEmissaoInicio": start_date_str,
        "DataEmissaoFim": end_date_str,
        "CnpjEmit": fornecedor_cnpj,
        "CnpjDest": "",
        "CnpjRem": "",
        "CnpjTom": "",
        "Tag": "",
        "Downloadevent": True,
        "TypeEvent": 0
    }
    try:
        response = requests.post(
            'https://api.sieg.com/BaixarXmlsV2?api_key={}'.format(Config.SIEG_API_KEY),
            json=sieg_request_data,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'xmls' not in result or not result['xmls']:
                return jsonify({'message': 'No NFE data found for this purchase order'}), 404
        else:
            if response.status_code == 404:
                # Retry with a date range of one month before the start date, for after receive order purchase generation
                retry_start_date = start_date - relativedelta(months=1)
                retry_start_date_str = retry_start_date.strftime('%Y-%m-%dT00:00:00.000Z')
                retry_request_data = sieg_request_data.copy()
                retry_request_data["DataEmissaoInicio"] = retry_start_date_str

                retry_response = requests.post(
                    'https://api.sieg.com/BaixarXmlsV2?api_key={}'.format(Config.SIEG_API_KEY),
                    json=retry_request_data,
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                )

                if retry_response.status_code != 200:
                    return jsonify({'error': 'No NFE data found for this purchase order after retry'}), 404

                result = retry_response.json()
                if 'xmls' not in result or not result['xmls']:
                    return jsonify({'message': 'No NFE data found for this purchase order after retry'}), 404

            else:
                return jsonify({'error': f'Error fetching NFE data: {response.status_code} - {response.text}'}), response.status_code
           
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        nfe_data = []
        for xml_base64 in result['xmls']:
            try:
                xml_content = base64.b64decode(xml_base64).decode('utf-8')
                root = ET.fromstring(xml_content)
                # Extract NFE data
                chave_acesso = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                numero_nota = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:nNF', ns)
                data_emissao = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:dhEmi', ns)
                nome_fornecedor = root.find('.//nfe:NFe/nfe:infNFe/nfe:emit/nfe:xNome', ns)
                valor_total = root.find('.//nfe:NFe/nfe:infNFe/nfe:total/nfe:ICMSTot/nfe:vNF', ns)

                if chave_acesso.text != "":
                    nfe_data.append({
                        'chave': chave_acesso.text,
                        'numero': numero_nota.text,
                        'data_emissao': data_emissao.text,
                        'fornecedor': nome_fornecedor.text,
                        'valor': valor_total.text,
                        'xml_content': xml_content
                    })
            except Exception as e:
                # Log the error and continue with next XML
                print(f"Error processing XML: {str(e)}")
                continue
        
        return jsonify({
            'purchase_order': cod_pedc,
            'fornecedor': purchase_order.fornecedor_descricao,
            'valor': valor_total.text if valor_total is not None else '',
            'data_emissao': data_emissao.text if data_emissao is not None else '',
            'numero_nota': numero_nota.text if numero_nota is not None else '',
            'nfe_data': nfe_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

def extract_xml_value(root, xpath):
    try:
        element = root.find(xpath)
        return element.text if element is not None else ''
    except:
        return ''
    
@bp.route('/quotation_items', methods=['GET'])
@login_required
def get_quotation_items():
    cod_cot = request.args.get('cod_cot')
    if not cod_cot:
        return jsonify({'error': 'cod_cot is required'}), 400

    quotations = Quotation.query.filter_by(cod_cot=cod_cot).all()
    if not quotations:
        return jsonify({'error': 'Quotation not found'}), 404
    
    unique_items = {}    
    # Process all quotations to get unique items by description only
    for quotation in quotations:
        item_key = quotation.descricao.strip().lower() if quotation.descricao else ""
        
        if item_key not in unique_items:
            last_purchase = PurchaseItem.query.join(PurchaseOrder)\
                .filter(PurchaseItem.descricao.ilike(f"%{quotation.descricao}%"))\
                .order_by(PurchaseOrder.dt_emis.desc())\
                .first()
            
            last_purchase_data = None
            if last_purchase:
                last_purchase_data = {
                    'price': last_purchase.preco_unitario,
                    'date': last_purchase.purchase_order.dt_emis,
                    'cod_pedc': last_purchase.cod_pedc,
                    'fornecedor': last_purchase.purchase_order.fornecedor_descricao
                }
            
            unique_items[item_key] = {
                'item_id': quotation.item_id,
                'descricao': quotation.descricao,
                'quantidade': quotation.quantidade,
                'dt_emissao': quotation.dt_emissao,
                'last_purchase': last_purchase_data,
                'fornecedores': []
            }

        supplier_exists = False
        for supplier in unique_items[item_key]['fornecedores']:
            if supplier['fornecedor_id'] == quotation.fornecedor_id:
                supplier_exists = True
                break
                
        if not supplier_exists:
            unique_items[item_key]['fornecedores'].append({
                'fornecedor_id': quotation.fornecedor_id,
                'fornecedor_descricao': quotation.fornecedor_descricao,
                'preco_unitario': quotation.preco_unitario
            })

    quotation_data = {
        'cod_cot': quotations[0].cod_cot,
        'dt_emissao': quotations[0].dt_emissao,
        'items': list(unique_items.values())
    }

    return jsonify(quotation_data), 200

@bp.route('/extract_quotation_data', methods=['POST'])
@login_required
def extract_quotation_data():
    import json
    import tempfile
    import os
    import google.generativeai as genai
    from datetime import datetime

    # Check if files were uploaded
    if not request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    # Get quotation reference number if provided
    cod_cot = request.form.get('cod_cot', '')
    
    # Setup Google Generative AI (Gemini)
    gemini_api_key = Config.GEMINI_API_KEY
    if not gemini_api_key:
        return jsonify({'error': 'GEMINI_API_KEY not set in environment'}), 500
    
    genai.configure(api_key=gemini_api_key)
    
    try:
        # Fetch existing items if we have a quotation code
        existing_items = []
        items_descriptions = []
        
        if cod_cot:
            quotations = Quotation.query.filter_by(cod_cot=cod_cot).all()
            for quotation in quotations:
                # Store item descriptions for prompt
                if quotation.descricao and quotation.descricao not in items_descriptions:
                    items_descriptions.append(quotation.descricao)
                
                existing_item = {
                    'item_id': quotation.item_id,
                    'descricao': quotation.descricao,
                    'quantidade': quotation.quantidade,
                    'preco_unitario': quotation.preco_unitario,
                    'fornecedor_id': quotation.fornecedor_id,
                    'fornecedor_descricao': quotation.fornecedor_descricao
                }
                
                # Get last purchase data
                last_purchase = PurchaseItem.query.join(PurchaseOrder)\
                    .filter(PurchaseItem.descricao.ilike(f"%{quotation.descricao}%"))\
                    .order_by(PurchaseOrder.dt_emis.desc())\
                    .first()
                
                if last_purchase:
                    existing_item['last_purchase'] = {
                        'price': last_purchase.preco_unitario,
                        'date': last_purchase.purchase_order.dt_emis,
                        'cod_pedc': last_purchase.cod_pedc,
                        'fornecedor': last_purchase.purchase_order.fornecedor_descricao
                    }
                
                existing_items.append(existing_item)

        # Process uploaded files
        temp_files = []
        file_types = []
        
        for key in request.files:
            file = request.files[key]
            file_extension = file.filename.split('.')[-1].lower()
            
            # Determine file type and appropriate temporary file suffix
            if file_extension in ['xls', 'xlsx']:
                file_type = 'excel'
                suffix = '.xlsx'
            elif file_extension in ['pdf']:
                file_type = 'pdf'
                suffix = '.pdf'
            elif file_extension in ['jpg', 'jpeg', 'png']:
                file_type = 'image'
                suffix = f'.{file_extension}'
            else:
                continue  # Skip unsupported file types
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            file.save(temp_file.name)
            temp_files.append(temp_file.name)
            file_types.append(file_type)
        
        if not temp_files:
            return jsonify({'error': 'No supported files uploaded'}), 400

        generation_config = {
            "temperature": 0.1,  
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,
        }
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config
        )
        extracted_data = []
        
        for i, file_path in enumerate(temp_files):
            file_type = file_types[i]
            content_parts = []
            
            if file_type == 'pdf':
                # For PDFs, try text extraction first as it's more reliable for matching
                try:
                    import PyPDF2
                    pdf_text = ""
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page_num in range(min(5, len(pdf_reader.pages))):
                            pdf_text += pdf_reader.pages[page_num].extract_text()
                    
                    if pdf_text.strip():
                        content_parts.append(pdf_text)
                    else:
                        # If text extraction yields no results, fallback to image conversion
                        raise ValueError("PDF text extraction yielded empty results")
                        
                except Exception as e:
                    print(f"Error extracting PDF text: {str(e)}")
                    try:
                        # Fallback to image conversion
                        from pdf2image import convert_from_path
                        images = convert_from_path(file_path, dpi=300, first_page=1, last_page=5)
                        
                        for img in images:
                            import io
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG')
                            img_byte_arr = img_byte_arr.getvalue()
                            
                            content_parts.append({
                                "mime_type": "image/png",
                                "data": img_byte_arr
                            })
                    except Exception as e2:
                        print(f"Error converting PDF to image: {str(e2)}")
                        continue
            
            elif file_type == 'excel':
                # Extract data from Excel
                try:
                    import pandas as pd
                    # Read all sheets
                    excel_data = pd.read_excel(file_path, sheet_name=None)
                    excel_text = "Excel file content:\n\n"
                    
                    for sheet_name, df in excel_data.items():
                        excel_text += f"Sheet: {sheet_name}\n"
                        excel_text += df.to_string(index=False, max_rows=100) + "\n\n"
                    
                    content_parts.append(excel_text)
                except Exception as e:
                    print(f"Error processing Excel file: {str(e)}")
                    continue
            
            elif file_type == 'image':
                # Process image directly
                try:
                    with open(file_path, 'rb') as img_file:
                        img_data = img_file.read()
                        
                    content_parts.append({
                        "mime_type": f"image/{file_path.split('.')[-1].lower()}",
                        "data": img_data
                    })
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    continue
            
            # Prepare enhanced prompt for Gemini that includes item descriptions from quotation
            items_list_text = ""
            if items_descriptions:
                items_list_text = "Os itens que estou procurando na cotação são:\n"
                for idx, desc in enumerate(items_descriptions, 1):
                    items_list_text += f"{idx}. {desc}\n"
            
            prompt = f"""
            Extraia informações estruturadas desta cotação em formato detalhado. Preciso das seguintes informações:
            1. Nome do fornecedor/empresa
            2. Data da cotação
            3. Lista completa de itens com seus respectivos:
               - Código (se disponível)
               - Descrição detalhada
               - Quantidade
               - Unidade (un, kg, caixa, etc.)
               - Preço unitário (se disponível, 0 caso não informado)
               - Preço total
               - Fabricante/marca (se disponível)

            {items_list_text}

            Para cada item encontrado, tente identificar a qual dos itens listados acima ele corresponde.
            O código pode ser diferente, use principalmente a descrição para fazer a correspondência.
            
            Tenha cautela para não trocar o valor total pelo valor unitário e não confunda com o preço total da cotação.

            Observe atentamente os valores e formatos. Retorne um JSON válido com esta estrutura:
            ```json
            {{
              "supplier": "Nome do Fornecedor",
              "date": "Data da Cotação (formato YYYY-MM-DD)",
              "items": [
                {{
                  "code": "código do item (se disponível)",
                  "description": "descrição completa do item",
                  "quantity": 1,
                  "unit": "unidade (un, kg, etc.)",
                  "unitPrice": 99.99,
                  "totalPrice": 99.99,
                  "manufacturer": "nome do fabricante (se disponível)",
                  "matchedItemDescription": "descrição do item da lista que corresponde (se encontrado)"
                }}
              ],
              "totalValue": 999.99
            }}
            ```
            
            Caso não consiga identificar algum valor, use valores vazios para strings ("") e 0 para números.
            """
            
            # Add the prompt to the beginning of content_parts
            all_parts = [prompt] + content_parts
            
            # Make request to Gemini
            response = model.generate_content(all_parts)
            
            # Parse and process response
            response_text = response.text
            
            # Extract JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            
            if json_match:
                try:
                    supplier_data = json.loads(json_match.group(1))
                    extracted_data.append(supplier_data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON in response: {json_match.group(1)}")
            else:
                try:
                    # Try to parse the whole response as JSON
                    supplier_data = json.loads(response_text)
                    extracted_data.append(supplier_data)
                except json.JSONDecodeError:
                    print("Could not extract JSON from response")
        
        # Match extracted items with existing items (for cases where Gemini didn't provide matches)
        matched_results = []
        
        for supplier_data in extracted_data:
            matched_supplier = {
                "supplier": supplier_data.get("supplier", ""),
                "date": supplier_data.get("date", ""),
                "items": [],
                "totalValue": supplier_data.get("totalValue", 0)
            }
            
            for item in supplier_data.get("items", []):
                matched_item = item.copy()
                
                # If Gemini already provided a match, use it
                if "matchedItemDescription" in item and item["matchedItemDescription"]:
                    # Find the corresponding item_id in existing_items
                    for existing_item in existing_items:
                        if existing_item.get("descricao", "").lower() == item["matchedItemDescription"].lower():
                            matched_item["matchedItemId"] = existing_item.get("item_id", "")
                            
                            # Determine confidence based on exact match
                            matched_item["matchConfidence"] = "Alta"
                            
                            # Add last purchase info if available
                            if "last_purchase" in existing_item:
                                matched_item["lastPurchase"] = existing_item["last_purchase"]
                                
                                # Calculate price difference percentage
                                last_price = existing_item["last_purchase"].get("price", 0)
                                current_price = item.get("unitPrice", 0)
                                
                                if last_price and current_price:
                                    price_diff_pct = ((current_price - last_price) / last_price) * 100
                                    matched_item["priceDifferencePercent"] = round(price_diff_pct, 2)
                            break
                else:
                    # Fallback to our own matching logic if Gemini didn't provide a match
                    best_match = None
                    best_match_score = 0
                    
                    if existing_items:
                        for existing_item in existing_items:
                            try:
                                from difflib import SequenceMatcher
                                
                                item_desc = item.get('description', '').lower()
                                existing_desc = existing_item.get('descricao', '').lower()
                                
                                ratio = SequenceMatcher(None, item_desc, existing_desc).ratio() * 100
                                match_score = int(ratio)
                                
                                if match_score > best_match_score:
                                    best_match_score = match_score
                                    best_match = existing_item
                            except Exception as e:
                                print(f"Error matching items: {str(e)}")
                                continue
                    
                    # Add match information
                    if best_match:
                        matched_item["matchedItemId"] = best_match.get("item_id", "")
                        matched_item["matchedItemDescription"] = best_match.get("descricao", "")
                        
                        if best_match_score >= 85:
                            matched_item["matchConfidence"] = "Alta"
                        elif best_match_score >= 70:
                            matched_item["matchConfidence"] = "Média"
                        else:
                            matched_item["matchConfidence"] = "Baixa"
                        
                        # Add last purchase info if available
                        if "last_purchase" in best_match:
                            matched_item["lastPurchase"] = best_match["last_purchase"]
                            
                            # Calculate price difference percentage
                            last_price = best_match["last_purchase"].get("price", 0)
                            current_price = item.get("unitPrice", 0)
                            
                            if last_price and current_price:
                                price_diff_pct = ((current_price - last_price) / last_price) * 100
                                matched_item["priceDifferencePercent"] = round(price_diff_pct, 2)
                    else:
                        matched_item["matchedItemDescription"] = ""
                        matched_item["matchConfidence"] = "Não encontrado"
                
                matched_supplier["items"].append(matched_item)
            
            matched_results.append(matched_supplier)
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return jsonify({
            "extractedData": matched_results,
            "existingItems": existing_items if cod_cot else []
        }), 200
        
    except Exception as e:
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return jsonify({'error': f'Error extracting data: {str(e)}'}), 500
    
@bp.route('/get_danfe_pdf', methods=['GET'])
@login_required
def get_danfe_pdf():
    xml_key = request.args.get('xmlKey')
    if not xml_key:
        return jsonify({'error': 'xmlKey is required'}), 400
    
    try:
        response = requests.get(
            f'https://api.sieg.com/api/Arquivos/GerarDanfeViaChave?xmlKey={xml_key}&api_key={Config.SIEG_API_KEY}',
            headers={'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'error': f'Error fetching DaNFe: {response.status_code} - {response.text}'}), response.status_code
    
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500