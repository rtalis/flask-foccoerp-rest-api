from datetime import datetime
import string
from urllib import response
import re
from fuzzywuzzy import process, fuzz
from flask import Blueprint, redirect, request, jsonify, current_app
import requests
from sqlalchemy import and_, or_, func, cast, tuple_
from sqlalchemy.sql import exists
from sqlalchemy.orm import joinedload
from flask_login import login_user, logout_user, login_required, current_user
from app.models import LoginHistory, NFEData, NFEDestinatario, NFEntry, PurchaseOrder, PurchaseItem, PurchaseItemNFEMatch, Quotation, User
from app.utils import  apply_adjustments, check_order_fulfillment, fuzzy_search, import_rcot0300, import_rfor0302, import_rpdc0250c, import_ruah,_parse_date
from app import db
import tempfile
import os
import shutil
from config import Config


bp = Blueprint('api', __name__)


UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xml'}


def _build_purchase_payload(items):
    """Group purchase items by order and prepare API payload."""
    grouped_results = {}
    order_keys = set()
    item_ids = set()

    for item in items:
        order = item.purchase_order
        if not order:
            continue
        order_keys.add((order.cod_emp1, item.cod_pedc))
        # Collect item IDs for estimated NFE lookup
        if item.qtde_saldo and item.qtde_saldo > 0:
            item_ids.add(item.id)

    nf_entries_by_order = {}

    if order_keys:
        nf_entries = (
            NFEntry.query
            .filter(tuple_(NFEntry.cod_emp1, NFEntry.cod_pedc).in_(list(order_keys)))
            .all()
        )
        for nf_entry in nf_entries:
            order_key = (nf_entry.cod_emp1, nf_entry.cod_pedc)
            nf_entries_by_order.setdefault(order_key, []).append(nf_entry)

    # Get estimated NFE matches for unfulfilled items
    estimated_nfe_by_item = {}
    if item_ids:
        estimated_matches = (
            PurchaseItemNFEMatch.query
            .filter(PurchaseItemNFEMatch.purchase_item_id.in_(list(item_ids)))
            .order_by(PurchaseItemNFEMatch.match_score.desc())
            .all()
        )
        for match in estimated_matches:
            # Only keep the best match per item (highest score)
            if match.purchase_item_id not in estimated_nfe_by_item:
                estimated_nfe_by_item[match.purchase_item_id] = {
                    'nfe_numero': match.nfe_numero,
                    'match_score': match.match_score,
                    'nfe_fornecedor': match.nfe_fornecedor,
                    'nfe_data_emissao': match.nfe_data_emissao.isoformat() if match.nfe_data_emissao else None
                }

    for item in items:
        cod_pedc = item.cod_pedc
        order = item.purchase_order
        if not order:
            continue

        order_key = (order.cod_emp1, cod_pedc)
        order_nf_entries = nf_entries_by_order.get(order_key, [])

        if order_key not in grouped_results:
            adjustments = getattr(order, 'adjustments', [])
            base_total = order.total_pedido_com_ipi or 0
            adjusted_total = apply_adjustments(base_total, adjustments)

            grouped_results[order_key] = {
                'order': {
                    'order_id': order.id,
                    'cod_pedc': cod_pedc,
                    'dt_emis':  _parse_date(order.dt_emis),
                    'fornecedor_id': order.fornecedor_id,
                    'fornecedor_descricao': order.fornecedor_descricao,
                    'total_bruto': order.total_bruto,
                    'total_pedido_com_ipi': order.total_pedido_com_ipi,
                    'adjusted_total': adjusted_total,
                    'adjustments': [
                        {
                            'tp_apl': adj.tp_apl,
                            'tp_dctacr1': adj.tp_dctacr1,
                            'tp_vlr1': adj.tp_vlr1,
                            'vlr1': adj.vlr1,
                            'order_index': adj.order_index
                        }
                        for adj in adjustments
                    ],
                    'total_liquido': order.total_liquido,
                    'total_liquido_ipi': order.total_liquido_ipi,
                    'posicao': order.posicao,
                    'posicao_hist': order.posicao_hist,
                    'observacao': order.observacao,
                    'contato': order.contato,
                    'func_nome': order.func_nome,
                    'cf_pgto': order.cf_pgto,
                    'is_fulfilled': order.is_fulfilled,
                    'cod_emp1': order.cod_emp1,
                    'nfes': [
                        {
                            'num_nf': nf_entry.num_nf,
                            'id': nf_entry.id,
                            'dt_ent': nf_entry.dt_ent,
                            'qtde': nf_entry.qtde,
                            'linha': nf_entry.linha
                        }
                        for nf_entry in order_nf_entries
                    ]
                },
                'items': []
            }

        grouped_results[order_key]['items'].append({
            'id': item.id,
            'item_id': item.item_id,
            'descricao': item.descricao,
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario,
            'total': item.total,
            'unidade_medida': item.unidade_medida,
            'linha': item.linha,
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
            'estimated_nfe': estimated_nfe_by_item.get(item.id),
        })

    return list(grouped_results.values())


@bp.route('/purchasers', methods=['GET'])
@login_required
def get_purchasers():
    try:
        purchasers = db.session.query(PurchaseOrder.func_nome).distinct().all()
        purchaser_names = [purchaser[0] for purchaser in purchasers]
        return jsonify(purchaser_names), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/companies', methods=['GET'])
@login_required
def get_companies():
    """Get distinct company codes from purchase orders, with names from Company table if available."""
    from app.models import Company
    try:
        # Get distinct cod_emp1 from purchase orders
        purchase_codes = db.session.query(PurchaseOrder.cod_emp1).distinct().all()
        purchase_codes = [code[0] for code in purchase_codes if code[0] is not None]
        
        # Get company names from Company table
        company_names = {}
        companies = Company.query.all()
        for company in companies:
            company_names[str(company.cod_emp1)] = company.name
        
        # Build result with code and optional name
        result = []
        for code in sorted(purchase_codes):
            name = company_names.get(str(code))
            result.append({
                'code': code,
                'name': name,
                'display': f"{code} - {name}" if name else str(code)
            })
        
        return jsonify(result), 200
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
                'dt_emis':  _parse_date(order.dt_emis),
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
                'dt_emis':  _parse_date(order.dt_emis),
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
            'dt_emis': _parse_date(order.dt_emis),
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
            'dt_emis': _parse_date(order.dt_emis),
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
                    'dt_emis': _parse_date(order.dt_emis),
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
            'dt_emis': _parse_date(order.dt_emis),
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


@bp.route('/search_advanced', methods=['GET'])
@login_required
def search_advanced():
    from sqlalchemy import text

    if request.args.get('legacy', 'false').lower() == 'true':
        return search_combined()

    normalized_query = request.args.get('query', '').strip()
    tokens = [token for token in re.split(r'\s+', normalized_query) if token]

    page = max(int(request.args.get('page', 1)), 1)
    per_page = max(min(int(request.args.get('per_page', 20)), 200), 1)
    score_cutoff = int(request.args.get('score_cutoff', 100))
    ignore_diacritics = request.args.get('ignoreDiacritics', 'true').lower() == 'true'
    fields_param = request.args.get('fields', '')
    search_by_func_nome = request.args.get('selectedFuncName', 'todos')
    search_by_cod_emp1 = request.args.get('selectedCodEmp1', 'todos')
    min_value = request.args.get('minValue', type=float)
    max_value = request.args.get('maxValue', type=float)
    value_search_type = request.args.get('valueSearchType', 'item').lower()
    exact_search = request.args.get('exactSearch', 'false').lower() == 'true'
    hide_cancelled = request.args.get('hideCancelled', 'false').lower() == 'true'

    default_fields = {'cod_pedc', 'fornecedor', 'observacao', 'item_id', 'descricao', 'num_nf'}
    fields = {field.strip().lower() for field in fields_param.split(',') if field.strip()} or default_fields

    column_map = {
        'cod_pedc': PurchaseOrder.cod_pedc,
        'fornecedor': PurchaseOrder.fornecedor_descricao,
        'observacao': PurchaseOrder.observacao,
        'item_id': PurchaseItem.item_id,
        'descricao': PurchaseItem.descricao,
        
    }

    include_nf = 'num_nf' in fields
    search_columns = [column_map[key] for key in fields if key in column_map]
    if not search_columns and not include_nf:
        search_columns = [PurchaseItem.descricao]

    remove_accents = None
    if ignore_diacritics and db.engine.name == 'postgresql':
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        remove_accents = lambda col: func.unaccent(col)
    
    def build_like_pattern(term: str) -> str:
        pattern = term.replace('*', '%')
        if exact_search:
            return pattern
        if '%' not in pattern:
            pattern = f'%{pattern}%'
        return pattern

    def apply_ilike(column, pattern):
        if remove_accents:
            col_expr = remove_accents(column)
            search_term = remove_accents(func.cast(pattern, db.String))
            return col_expr.ilike(search_term)
        else:
            return column.ilike(pattern)

    base_query = (
        PurchaseItem.query
        .join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
        .options(joinedload(PurchaseItem.purchase_order).joinedload(PurchaseOrder.adjustments))
    )

    value_filters = []
    if min_value is not None:
        if value_search_type == 'order':
            value_filters.append(PurchaseOrder.total_pedido_com_ipi >= min_value)
        else:
            value_filters.append(PurchaseItem.preco_unitario >= min_value)
    if max_value is not None:
        if value_search_type == 'order':
            value_filters.append(PurchaseOrder.total_pedido_com_ipi <= max_value)
        else:
            value_filters.append(PurchaseItem.preco_unitario <= max_value)
    if value_filters:
        base_query = base_query.filter(and_(*value_filters))

    if search_by_func_nome and search_by_func_nome.lower() != 'todos':
        base_query = base_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))

    if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
        base_query = base_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))

    if hide_cancelled:
        base_query = base_query.filter(PurchaseItem.quantidade > PurchaseItem.qtde_canc)
    token_filters = []
    for token in tokens:
        pattern = build_like_pattern(token)
        term_clauses = [apply_ilike(column, pattern) for column in search_columns]

        if include_nf:
            nf_column = NFEntry.num_nf
            nf_expr = remove_accents(nf_column) if remove_accents else nf_column
            nf_clause = exists().where(and_(
                nf_expr.ilike(pattern),
                NFEntry.cod_emp1 == PurchaseItem.cod_emp1,
                NFEntry.cod_pedc == PurchaseItem.cod_pedc,
                cast(NFEntry.linha, db.String) == cast(PurchaseItem.linha, db.String)
            ))
            term_clauses.append(nf_clause)

        token_filters.append(or_(*term_clauses))

    if token_filters:
        base_query = base_query.filter(and_(*token_filters))

    base_query = base_query.order_by(PurchaseOrder.dt_emis.desc(), PurchaseItem.id.desc())
    if score_cutoff < 100 and tokens:
        items = base_query.all()
        items = fuzzy_search(' '.join(tokens), items, score_cutoff, 'descricao' in fields, 'observacao' in fields)
        purchases_payload = _build_purchase_payload(items)
        return jsonify({
            'purchases': purchases_payload,
            'total_pages': 1,
            'current_page': 1,
            'total_results': len(items)
        }), 200

    items_paginated = base_query.paginate(page=page, per_page=per_page, count=True)
    purchases_payload = _build_purchase_payload(items_paginated.items)

    return jsonify({
        'purchases': purchases_payload,
        'total_pages': items_paginated.pages,
        'current_page': items_paginated.page,
        'total_results': items_paginated.total
    }), 200


@bp.route('/search_advanced/suggestions', methods=['GET'])
@login_required
def search_advanced_suggestions():
    term = request.args.get('term', '').strip()
    limit = max(min(int(request.args.get('limit', 10)), 50), 1)

    if not term:
        return jsonify({'suggestions': []}), 200

    pattern = term.replace('*', '%')
    if '%' not in pattern:
        pattern = f'%{pattern}%'

    suggestions = []
    seen_values = set()

    def append_results(queryset, suggestion_type):
        for value in queryset:
            if not value:
                continue
            key = (suggestion_type, value)
            if key in seen_values:
                continue
            seen_values.add(key)
            suggestions.append({'value': value, 'type': suggestion_type})
            if len(suggestions) >= limit:
                return True
        return False

    if append_results(
        [row[0] for row in db.session.query(PurchaseItem.descricao).filter(PurchaseItem.descricao.ilike(pattern)).limit(limit * 2).all()],
        'descricao'
    ):
        return jsonify({'suggestions': suggestions}), 200

    if append_results(
        [row[0] for row in db.session.query(PurchaseItem.item_id).filter(PurchaseItem.item_id.ilike(pattern)).limit(limit * 2).all()],
        'item_id'
    ):
        return jsonify({'suggestions': suggestions}), 200

    if append_results(
        [row[0] for row in db.session.query(PurchaseOrder.cod_pedc).filter(PurchaseOrder.cod_pedc.ilike(pattern)).limit(limit * 2).all()],
        'cod_pedc'
    ):
        return jsonify({'suggestions': suggestions}), 200

    append_results(
        [row[0] for row in db.session.query(PurchaseOrder.fornecedor_descricao).filter(PurchaseOrder.fornecedor_descricao.ilike(pattern)).limit(limit * 2).all()],
        'fornecedor'
    )

    return jsonify({'suggestions': suggestions}), 200

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
    search_by_num_nf = request.args.get('searchByNumNF', 'false').lower() == 'true' 
    search_by_func_nome = request.args.get('selectedFuncName')
    search_by_cod_emp1 = request.args.get('selectedCodEmp1', 'todos')
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
                value_filters.append(PurchaseItem.preco_unitario >= min_value)
            if max_value is not None:
                value_filters.append(PurchaseItem.preco_unitario <= max_value)
        else:  #order
            if min_value is not None:
                value_filters.append(PurchaseOrder.total_pedido_com_ipi >= min_value)
            if max_value is not None:
                value_filters.append(PurchaseOrder.total_pedido_com_ipi <= max_value)


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
        if search_by_num_nf:
            nf_entries = NFEntry.query.filter(NFEntry.num_nf.ilike(f'%{query}%')).all()
            if nf_entries:
                nf_filters = []
                for nf in nf_entries:
                    nf_filters.append(and_(
                        PurchaseItem.cod_pedc == nf.cod_pedc,
                        PurchaseItem.cod_emp1 == nf.cod_emp1
                    ))
                if nf_filters:
                    filters.append(or_(*nf_filters))

        if not any([search_by_cod_pedc, search_by_fornecedor, search_by_observacao, search_by_item_id, search_by_descricao, search_by_num_nf]):
            filters.append(or_(
                PurchaseItem.descricao.ilike(f'%{query}%'),
                PurchaseItem.item_id.ilike(f'%{query}%'),
                PurchaseOrder.cod_pedc.ilike(f'%{query}%'),
                PurchaseOrder.fornecedor_descricao.ilike(f'%{query}%'),
                PurchaseOrder.observacao.ilike(f'%{query}%')
            ))

    items_query = (
        PurchaseItem.query
        .order_by(PurchaseOrder.dt_emis.desc())
        .join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
        .options(joinedload(PurchaseItem.purchase_order).joinedload(PurchaseOrder.adjustments))
    )
    if value_filters:
            filters.append(and_(*value_filters))
    if filters:
        items_query = items_query.filter(or_(*filters))
    if search_by_func_nome != 'todos':
        items_query = items_query.filter(and_(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%')))
    if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
        items_query = items_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))
    
    if score_cutoff < 100 and query:
        fuzzy_query = (
            PurchaseItem.query
            .order_by(PurchaseOrder.dt_emis.desc())
            .join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
            .options(joinedload(PurchaseItem.purchase_order).joinedload(PurchaseOrder.adjustments))
        )
        if search_by_func_nome != 'todos':
            fuzzy_query =  fuzzy_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))
        if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
            fuzzy_query = fuzzy_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))
        if value_filters:
            fuzzy_query = fuzzy_query.filter(and_(*value_filters))
        items = fuzzy_query.all()
        items = fuzzy_search(query, items, score_cutoff, search_by_descricao, search_by_observacao)
    else:
        items_paginated = items_query.paginate(page=page, per_page=per_page, count=True)
        items = items_paginated.items

    purchases_payload = _build_purchase_payload(items)

    if score_cutoff < 100 and query:
        total_pages = 1
        current_page = 1
    else:
        total_pages = items_paginated.pages
        current_page = items_paginated.page

    return jsonify({
        'purchases': purchases_payload,
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
    search_by_num_nf = request.args.get('searchByNumNF', 'false').lower() == 'true'  # Add this line


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
        search_by_descricao,
        search_by_num_nf
    ])
    
    if multiplier == 0:
        multiplier = 6

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

    final_file_path = os.path.join(UPLOAD_FOLDER, f'{file_id}_complete.xml')

    try:
        chunks = sorted(os.listdir(chunk_dir), key=lambda x: int(x.split('_')[1]))
        with open(final_file_path, 'wb') as outfile:
            for chunk_name in chunks:
                chunk_path = os.path.join(chunk_dir, chunk_name)
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        assembled_size = os.path.getsize(final_file_path)
        with open(final_file_path, 'rb') as f:
            content = f.read()
        if not is_valid_xml(content):
            raise ValueError('Invalid XML file')

        if b'<RPDC0250_RUAH>' in content or b'<RPDC0250>' in content:
            doc_type = 'RPDC0250'
            handler = import_ruah
        elif b'<RPDC0250C>' in content:
            doc_type = 'RPDC0250C'
            handler = import_rpdc0250c
        elif b'<RCOT0300>' in content:
            doc_type = 'RCOT0300'
            handler = import_rcot0300
        elif b'<RFOR0302>' in content:
            doc_type = 'RFOR0302'
            handler = import_rfor0302
        else:
            raise ValueError('Arquivo XML invalido ou não suportado')

        result = handler(content)
        return result

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("process_file: failure | file_id=%s", file_id)
        return jsonify({'error': str(e)}), 500
    

    finally:
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
        'dt_emis': _parse_date(order.dt_emis),
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

    if not request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    
    gemini_api_key = Config.GEMINI_API_KEY
    if not gemini_api_key:
        return jsonify({'error': 'GEMINI_API_KEY not set in environment'}), 500
    
    genai.configure(api_key=gemini_api_key)
    
    try:
        existing_items = []
        items_descriptions = []        
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
                try:
                    import pandas as pd
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
            
            all_parts = [prompt] + content_parts            
            response = model.generate_content(all_parts)            
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
                    supplier_data = json.loads(response_text)
                    extracted_data.append(supplier_data)
                except json.JSONDecodeError:
                    print("Could not extract JSON from response")
        
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
                
                if "matchedItemDescription" in item and item["matchedItemDescription"]:
                    for existing_item in existing_items:
                        if existing_item.get("descricao", "").lower() == item["matchedItemDescription"].lower():
                            matched_item["matchedItemId"] = existing_item.get("item_id", "")
                            
                            matched_item["matchConfidence"] = "Alta"
                            
                            if "last_purchase" in existing_item:
                                matched_item["lastPurchase"] = existing_item["last_purchase"]
                                
                                last_price = existing_item["last_purchase"].get("price", 0)
                                current_price = item.get("unitPrice", 0)
                                
                                if last_price and current_price:
                                    price_diff_pct = ((current_price - last_price) / last_price) * 100
                                    matched_item["priceDifferencePercent"] = round(price_diff_pct, 2)
                            break
                else:
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
            "existingItems": existing_items 
        }), 200
        
    except Exception as e:
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return jsonify({'error': f'Error extracting data: {str(e)}'}), 500
    


@bp.route('/nfe_by_purchase', methods=['GET'])
@login_required
def get_nfe_by_purchase():
    import requests
    import base64
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from app.models import Supplier, NFEData
    from app.utils import parse_and_store_nfe_xml
    
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
            f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
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
                    f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
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
                
                # Extract chave (access key) to check if NFE already exists in database
                chave_acesso_elem = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                if chave_acesso_elem is None or not chave_acesso_elem.text:
                    # Skip invalid XML or NFe without access key
                    continue
                
                chave_acesso = chave_acesso_elem.text

                # Store NFE in the database
                parse_and_store_nfe_xml(xml_content)
                
                numero_nota = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:nNF', ns)
                data_emissao = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:dhEmi', ns)
                nome_fornecedor = root.find('.//nfe:NFe/nfe:infNFe/nfe:emit/nfe:xNome', ns)
                valor_total = root.find('.//nfe:NFe/nfe:infNFe/nfe:total/nfe:ICMSTot/nfe:vNF', ns)

                nfe_data.append({
                    'chave': chave_acesso,
                    'numero': numero_nota.text if numero_nota is not None else '',
                    'data_emissao': data_emissao.text if data_emissao is not None else '',
                    'fornecedor': nome_fornecedor.text if nome_fornecedor is not None else '',
                    'valor': valor_total.text if valor_total is not None else '',
                    'xml_content': xml_content,
                    'stored_in_database': True
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
    
    
@bp.route('/get_danfe_pdf', methods=['GET'])
@login_required
def get_danfe_pdf():
    from app.models import NFEData
    from app.utils import parse_and_store_nfe_xml
    import xml.etree.ElementTree as ET
    
    xml_key = request.args.get('xmlKey')
    if not xml_key:
        return jsonify({'error': 'xmlKey is required'}), 400
    
    try:
        # Check if NFE already exists in the database
        existing_nfe = NFEData.query.filter_by(chave=xml_key).first()
        
        if existing_nfe:
            # Just return NFE details if requested
            if request.args.get('details', 'false').lower() == 'true':
                return jsonify({
                    'source': 'database',
                    'nfe': {
                        'chave': existing_nfe.chave,
                        'numero': existing_nfe.numero,
                        'serie': existing_nfe.serie,
                        'data_emissao': existing_nfe.data_emissao.isoformat() if existing_nfe.data_emissao else None,
                        'natureza_operacao': existing_nfe.natureza_operacao,
                        'emitente': {
                            'nome': existing_nfe.emitente.nome if existing_nfe.emitente else '',
                            'cnpj': existing_nfe.emitente.cnpj if existing_nfe.emitente else '',
                            'inscricao_estadual': existing_nfe.emitente.inscricao_estadual if existing_nfe.emitente else '',
                        },
                        'destinatario': {
                            'nome': existing_nfe.destinatario.nome if existing_nfe.destinatario else '',
                            'cnpj': existing_nfe.destinatario.cnpj if existing_nfe.destinatario else '',
                            'inscricao_estadual': existing_nfe.destinatario.inscricao_estadual if existing_nfe.destinatario else '',
                        },
                        'valor_total': existing_nfe.valor_total,
                        'status': existing_nfe.status_motivo
                    }
                }), 200

        # Use SIEG API to generate DANFE PDF
        # Even if NFE is in database, SIEG generates the official DANFE format
        pdf_response = requests.get(
            f'https://api.sieg.com/api/Arquivos/GerarDanfeViaChave?xmlKey={xml_key}&api_key={Config.SIEG_API_KEY}',
            headers={'Accept': 'application/json'}
        )
        
        if pdf_response.status_code != 200:
            return jsonify({'error': f'Error fetching DaNFe: {pdf_response.status_code} - {pdf_response.text}'}), pdf_response.status_code
        
        return jsonify(pdf_response.json()), 200
    
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500
    
    
@bp.route('/dashboard_summary', methods=['GET'])
@login_required
def dashboard_summary():
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta

    try:
        # Parse date filters - support both months and custom date range
        months = int(request.args.get('months', 6))
        top_limit = int(request.args.get('limit', 8))
        buyer_filter = request.args.get('buyer', '').strip() 
        
        # Custom date range (takes precedence over months if provided)
        start_date_param = request.args.get('start_date', '').strip()
        end_date_param = request.args.get('end_date', '').strip()
        
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                end_date = datetime.now().date()
                start_date = (end_date.replace(day=1) - timedelta(days=months * 31)).replace(day=1)
        else:
            end_date = datetime.now().date()
            start_date = (end_date.replace(day=1) - timedelta(days=months * 31)).replace(day=1)

        # Build base filters for orders
        order_filters = [PurchaseOrder.dt_emis >= start_date, PurchaseOrder.dt_emis <= end_date]
        if buyer_filter and buyer_filter.lower() != 'all':
            order_filters.append(PurchaseOrder.func_nome == buyer_filter)

        # Summary - with buyer filter
        total_orders = db.session.query(func.count()).select_from(PurchaseOrder).filter(
            *order_filters
        ).scalar() or 0

        total_items = db.session.query(func.count()).select_from(PurchaseItem).join(
            PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id
        ).filter(*order_filters).scalar() or 0

        total_value = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0)).filter(
            *order_filters
        ).scalar() or 0.0

        total_suppliers = db.session.query(func.count(func.distinct(PurchaseOrder.fornecedor_id))).filter(
            *order_filters
        ).scalar() or 0

        avg_order_value = float(total_value) / total_orders if total_orders else 0.0

        # Monthly totals (group by year/month) - with buyer filter
        monthly_rows = db.session.query(
            extract('year', PurchaseOrder.dt_emis).label('y'),
            extract('month', PurchaseOrder.dt_emis).label('m'),
            func.count(PurchaseOrder.id).label('order_count'),
            func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).label('total_value')
        ).filter(
            *order_filters
        ).group_by(
            extract('year', PurchaseOrder.dt_emis),
            extract('month', PurchaseOrder.dt_emis)
        ).order_by(
            extract('year', PurchaseOrder.dt_emis),
            extract('month', PurchaseOrder.dt_emis)
        ).all()

        # Monthly items quantity - with buyer filter
        item_filters = [PurchaseOrder.dt_emis >= start_date, PurchaseOrder.dt_emis <= end_date]
        if buyer_filter and buyer_filter.lower() != 'all':
            item_filters.append(PurchaseOrder.func_nome == buyer_filter)
            
        monthly_items_rows = db.session.query(
            extract('year', PurchaseItem.dt_emis).label('y'),
            extract('month', PurchaseItem.dt_emis).label('m'),
            func.count(PurchaseItem.id).label('item_count'),
            func.coalesce(func.sum(PurchaseItem.quantidade), 0).label('total_qty')
        ).join(
            PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id
        ).filter(
            *item_filters
        ).group_by(
            extract('year', PurchaseItem.dt_emis),
            extract('month', PurchaseItem.dt_emis)
        ).order_by(
            extract('year', PurchaseItem.dt_emis),
            extract('month', PurchaseItem.dt_emis)
        ).all()

        monthly_items_map = {}
        for r in monthly_items_rows:
            k = (int(r.y), int(r.m))
            monthly_items_map[k] = {
                'item_count': int(r.item_count or 0),
                'total_qty': float(r.total_qty or 0),
            }

        # Normalize monthly data for last N months
        months_labels = []
        monthly_map = {}
        cur = end_date.replace(day=1)
        for _ in range(months + 1):  
            key = (cur.year, cur.month)
            months_labels.append(f"{cur.strftime('%b')}/{str(cur.year)[-2:]}")
            monthly_map[key] = {'order_count': 0, 'total_value': 0.0}
            prev = (cur.replace(day=1) - timedelta(days=1)).replace(day=1)
            cur = prev


        for r in monthly_rows:
            k = (int(r.y), int(r.m))
            if k in monthly_map:
                monthly_map[k] = {
                    'order_count': int(r.order_count or 0),
                    'total_value': float(r.total_value or 0),
                }

        #monthly list
        monthly_data = []
        cur = (end_date.replace(day=1) - timedelta(days=(months - 1) * 31)).replace(day=1)
        for _ in range(months):
            k = (cur.year, cur.month)
            label = f"{cur.strftime('%b')}/{str(cur.year)[-2:]}"
            v = monthly_map.get(k, {'order_count': 0, 'total_value': 0.0})
            items_v = monthly_items_map.get(k, {'item_count': 0, 'total_qty': 0.0})
            monthly_data.append({
                'month': label,
                'order_count': v['order_count'],
                'total_value': v['total_value'],
                'item_count': items_v['item_count'],
                'total_qty': items_v['total_qty'],
            })
            cur = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)

        # Daily usage
        usage_days = max(int(request.args.get('usage_days', 14)), 1)
        usage_start_date = end_date - timedelta(days=usage_days - 1)

        usage_rows = db.session.query(
            func.date(LoginHistory.login_time).label('login_date'),
            func.count(LoginHistory.id).label('login_count'),
            func.count(func.distinct(LoginHistory.user_id)).label('user_count')
        ).filter(
            LoginHistory.login_time >= usage_start_date
        ).group_by(
            'login_date'
        ).order_by(
            'login_date'
        ).all()

        usage_map = {}
        for row in usage_rows:
            day_value = row.login_date
            if isinstance(day_value, datetime):
                day_value = day_value.date()
            else:
                try:
                    day_value = datetime.strptime(str(day_value), '%Y-%m-%d').date()
                except ValueError:
                    continue

            usage_map[day_value] = {
                'logins': int(row.login_count or 0),
                'unique_users': int(row.user_count or 0)
            }

        daily_usage = []
        for idx in range(usage_days):
            current_day = usage_start_date + timedelta(days=idx)
            stats = usage_map.get(current_day, {'logins': 0, 'unique_users': 0})
            daily_usage.append({
                'date': current_day.isoformat(),
                'logins': stats['logins'],
                'unique_users': stats['unique_users']
            })

        # Top buyers
        if buyer_filter and buyer_filter.lower() != 'all':
            # When filtering by a specific buyer, return only that buyer's data
            buyer_rows = db.session.query(
                PurchaseOrder.func_nome.label('name'),
                func.count(PurchaseOrder.id).label('order_count'),
                func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).label('total_value'),
                func.coalesce(func.avg(PurchaseOrder.total_pedido_com_ipi), 0).label('avg_value'),
                func.coalesce(
                    func.sum(
                        db.session.query(func.count(PurchaseItem.id))
                        .filter(PurchaseItem.purchase_order_id == PurchaseOrder.id)
                        .correlate(PurchaseOrder)
                        .scalar_subquery()
                    ), 0
                ).label('item_count')
            ).filter(
                *order_filters,
                PurchaseOrder.func_nome.isnot(None)
            ).group_by(
                PurchaseOrder.func_nome
            ).order_by(
                func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).desc()
            ).limit(top_limit).all()
        else:
            buyer_rows = db.session.query(
                PurchaseOrder.func_nome.label('name'),
                func.count(PurchaseOrder.id).label('order_count'),
                func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).label('total_value'),
                func.coalesce(func.avg(PurchaseOrder.total_pedido_com_ipi), 0).label('avg_value'),
                func.coalesce(
                    func.sum(
                        db.session.query(func.count(PurchaseItem.id))
                        .filter(PurchaseItem.purchase_order_id == PurchaseOrder.id)
                        .correlate(PurchaseOrder)
                        .scalar_subquery()
                    ), 0
                ).label('item_count')
            ).filter(
                PurchaseOrder.dt_emis >= start_date,
                PurchaseOrder.dt_emis <= end_date,
                PurchaseOrder.func_nome.isnot(None)
            ).group_by(
                PurchaseOrder.func_nome
            ).order_by(
                func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).desc()
            ).limit(top_limit).all()

        buyer_data = [{
            'name': r.name or '—',
            'order_count': int(r.order_count or 0),
            'total_value': float(r.total_value or 0.0),
            'avg_value': float(r.avg_value or 0.0),
            'item_count': int(r.item_count or 0)  
        } for r in buyer_rows]

        # Top suppliers - with buyer filter
        supplier_rows = db.session.query(
            PurchaseOrder.fornecedor_descricao.label('name'),
            func.count(PurchaseOrder.id).label('order_count'),
            func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).label('total_value')
        ).filter(
            *order_filters,
            PurchaseOrder.fornecedor_descricao.isnot(None)
        ).group_by(
            PurchaseOrder.fornecedor_descricao
        ).order_by(
            func.coalesce(func.sum(PurchaseOrder.total_pedido_com_ipi), 0).desc()
        ).limit(top_limit).all()

        supplier_data = [{
            'name': r.name or '—',
            'order_count': int(r.order_count or 0),
            'total_value': float(r.total_value or 0.0)
        } for r in supplier_rows]

        # Top items by spend - with buyer filter
        item_rows = db.session.query(
            PurchaseItem.item_id,
            PurchaseItem.descricao,
            func.coalesce(func.sum(PurchaseItem.total), 0).label('total_spend')
        ).join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id).filter(
            *order_filters
        ).group_by(
            PurchaseItem.item_id, PurchaseItem.descricao
        ).order_by(
            func.coalesce(func.sum(PurchaseItem.total), 0).desc()
        ).limit(top_limit).all()

        top_items = [{
            'item_id': r.item_id,
            'descricao': r.descricao,
            'total_spend': float(r.total_spend or 0.0)
        } for r in item_rows]

        # Recent orders - with buyer filter
        recent_orders_q = db.session.query(PurchaseOrder).filter(
            *order_filters
        ).order_by(PurchaseOrder.dt_emis.desc()).limit(10).all()

        recent_orders = [{
            'cod_pedc': o.cod_pedc,
            'dt_emis': o.dt_emis.isoformat() if o.dt_emis else None,
            'fornecedor_descricao': o.fornecedor_descricao,
            'func_nome': o.func_nome,
            'total_value': float(o.total_pedido_com_ipi or 0.0)
        } for o in recent_orders_q]

        # Order fulfillment stats - with buyer filter
        fulfilled_count = db.session.query(func.count()).select_from(PurchaseOrder).filter(
            *order_filters,
            PurchaseOrder.is_fulfilled == True
        ).scalar() or 0
        
        pending_count = total_orders - fulfilled_count
        fulfillment_rate = (fulfilled_count / total_orders * 100) if total_orders > 0 else 0

        # Total quantity of items purchased - with buyer filter
        total_quantity = db.session.query(
            func.coalesce(func.sum(PurchaseItem.quantidade), 0)
        ).join(
            PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id
        ).filter(*order_filters).scalar() or 0.0

        # NFE statistics (if available) - date filter only (NFE doesn't link to buyer directly)
        nfe_count = 0
        nfe_total_value = 0.0
        try:
            nfe_count = db.session.query(func.count()).select_from(NFEData).filter(
                NFEData.data_emissao >= start_date,
                NFEData.data_emissao <= end_date
            ).scalar() or 0
            nfe_total_value = db.session.query(
                func.coalesce(func.sum(NFEData.valor_total), 0)
            ).filter(
                NFEData.data_emissao >= start_date,
                NFEData.data_emissao <= end_date
            ).scalar() or 0.0
        except Exception:
            pass 

        # Always get all purchasers for dropdown (without buyer filter)
        all_purchasers_rows = db.session.query(
            PurchaseOrder.func_nome.label('name')
        ).filter(
            PurchaseOrder.dt_emis >= start_date,
            PurchaseOrder.dt_emis <= end_date,
            PurchaseOrder.func_nome.isnot(None)
        ).group_by(
            PurchaseOrder.func_nome
        ).order_by(
            PurchaseOrder.func_nome
        ).all()
        
        all_purchasers = [r.name for r in all_purchasers_rows if r.name]

        summary = jsonify({ 'summary': {
                'total_orders': int(total_orders),
                'total_items': int(total_items),
                'total_value': float(total_value),
                'avg_order_value': float(avg_order_value),
                'total_suppliers': int(total_suppliers),
                'total_quantity': float(total_quantity),
                'fulfilled_orders': int(fulfilled_count),
                'pending_orders': int(pending_count),
                'fulfillment_rate': round(fulfillment_rate, 1),
                'nfe_count': int(nfe_count),
                'nfe_total_value': float(nfe_total_value)
            },
            'monthly_data': monthly_data,
            'daily_usage': daily_usage,
            'buyer_data': buyer_data,
            'supplier_data': supplier_data,
            'top_items': top_items,
            'recent_orders': recent_orders,
            'all_purchasers': all_purchasers
        })
        return summary, 200
 
        

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@bp.route('/get_nfe_data', methods=['GET'])
@login_required
def get_nfe_data():
    from app.models import NFEData
    from app.utils import parse_and_store_nfe_xml
    
    xml_key = request.args.get('xmlKey')
    if not xml_key:
        return jsonify({'error': 'xmlKey is required'}), 400
    
    try:
        existing_nfe = NFEData.query.filter_by(chave=xml_key).first()
        
        if existing_nfe:
            items_data = []
            for item in existing_nfe.itens:
                items_data.append({
                    'numero_item': item.numero_item,
                    'codigo': item.codigo,
                    'descricao': item.descricao,
                    'ncm': item.ncm,
                    'cfop': item.cfop,
                    'unidade': item.unidade_comercial,
                    'quantidade': item.quantidade_comercial,
                    'valor_unitario': item.valor_unitario_comercial,
                    'valor_total': item.valor_total_bruto,
                    'icms_valor': item.icms_vicms,
                    'icms_aliquota': item.icms_picms,
                    'pis_valor': item.pis_vpis,
                    'pis_aliquota': item.pis_ppis,
                    'cofins_valor': item.cofins_vcofins,
                    'cofins_aliquota': item.cofins_pcofins
                })
            
            result = {
                'source': 'database',
                'chave': existing_nfe.chave,
                'numero': existing_nfe.numero,
                'serie': existing_nfe.serie,
                'data_emissao': existing_nfe.data_emissao.isoformat() if existing_nfe.data_emissao else None,
                'natureza_operacao': existing_nfe.natureza_operacao,
                'status': existing_nfe.status_motivo,
                'protocolo': existing_nfe.protocolo,
                'valor_total': existing_nfe.valor_total,
                'valor_produtos': existing_nfe.valor_produtos,
                'valor_impostos': existing_nfe.valor_imposto,
                
                'emitente': {
                    'nome': existing_nfe.emitente.nome if existing_nfe.emitente else '',
                    'cnpj': existing_nfe.emitente.cnpj if existing_nfe.emitente else '',
                    'inscricao_estadual': existing_nfe.emitente.inscricao_estadual if existing_nfe.emitente else '',
                    'endereco': {
                        'logradouro': existing_nfe.emitente.logradouro if existing_nfe.emitente else '',
                        'numero': existing_nfe.emitente.numero if existing_nfe.emitente else '',
                        'complemento': existing_nfe.emitente.complemento if existing_nfe.emitente else '',
                        'bairro': existing_nfe.emitente.bairro if existing_nfe.emitente else '',
                        'municipio': existing_nfe.emitente.municipio if existing_nfe.emitente else '',
                        'uf': existing_nfe.emitente.uf if existing_nfe.emitente else '',
                        'cep': existing_nfe.emitente.cep if existing_nfe.emitente else '',
                        'telefone': existing_nfe.emitente.telefone if existing_nfe.emitente else '',
                    }
                },
                
                'destinatario': {
                    'nome': existing_nfe.destinatario.nome if existing_nfe.destinatario else '',
                    'cnpj': existing_nfe.destinatario.cnpj if existing_nfe.destinatario else '',
                    'cpf': existing_nfe.destinatario.cpf if existing_nfe.destinatario else '',
                    'inscricao_estadual': existing_nfe.destinatario.inscricao_estadual if existing_nfe.destinatario else '',
                    'email': existing_nfe.destinatario.email if existing_nfe.destinatario else '',
                    'endereco': {
                        'logradouro': existing_nfe.destinatario.logradouro if existing_nfe.destinatario else '',
                        'numero': existing_nfe.destinatario.numero if existing_nfe.destinatario else '',
                        'complemento': existing_nfe.destinatario.complemento if existing_nfe.destinatario else '',
                        'bairro': existing_nfe.destinatario.bairro if existing_nfe.destinatario else '',
                        'municipio': existing_nfe.destinatario.municipio if existing_nfe.destinatario else '',
                        'uf': existing_nfe.destinatario.uf if existing_nfe.destinatario else '',
                        'cep': existing_nfe.destinatario.cep if existing_nfe.destinatario else '',
                        'telefone': existing_nfe.destinatario.telefone if existing_nfe.destinatario else '',
                    }
                },
                
                'transporte': {
                    'modalidade': existing_nfe.modalidade_frete,
                    'transportadora': {
                        'nome': existing_nfe.transportadora.nome if existing_nfe.transportadora else '',
                        'cnpj': existing_nfe.transportadora.cnpj if existing_nfe.transportadora else '',
                        'inscricao_estadual': existing_nfe.transportadora.inscricao_estadual if existing_nfe.transportadora else '',
                        'endereco': existing_nfe.transportadora.endereco if existing_nfe.transportadora else '',
                        'municipio': existing_nfe.transportadora.municipio if existing_nfe.transportadora else '',
                        'uf': existing_nfe.transportadora.uf if existing_nfe.transportadora else '',
                        'placa': existing_nfe.transportadora.placa if existing_nfe.transportadora else '',
                    },
                    'volumes': [{
                        'quantidade': vol.quantidade,
                        'especie': vol.especie,
                        'peso_bruto': vol.peso_bruto,
                        'peso_liquido': vol.peso_liquido
                    } for vol in existing_nfe.volumes] if existing_nfe.volumes else []
                },
                
                'pagamento': [{
                    'tipo': pag.tipo,
                    'valor': pag.valor
                } for pag in existing_nfe.pagamentos] if existing_nfe.pagamentos else [],
                
     
                'duplicatas': [{
                    'numero': dup.numero,
                    'vencimento': dup.data_vencimento.isoformat() if dup.data_vencimento else None,
                    'valor': dup.valor
                } for dup in existing_nfe.duplicatas] if existing_nfe.duplicatas else [],
                
                'itens': items_data,
                
                'informacoes_adicionais': existing_nfe.informacoes_adicionais,
                'informacoes_fisco': existing_nfe.informacoes_fisco,
                
                'xml_content': existing_nfe.xml_content
            }
            
            return jsonify(result), 200

        xml_response = requests.post(
            f'https://api.sieg.com/BaixarXml?xmlType=1&downloadEvent=true&api_key={Config.SIEG_API_KEY}',
            data=xml_key, 
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )   
        
        if xml_response.status_code != 200:
            return jsonify({'error': f'Error fetching NFe XML: {xml_response.status_code}'}), xml_response.status_code
        
        xml_content = xml_response.text
        nfe_data = parse_and_store_nfe_xml(xml_content)
        
        return get_nfe_data()
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/get_nfe_by_number', methods=['GET'])
@login_required
def get_nfe_by_number():
    """
    Find NFE in the database by its number (num_nf).
    Returns only one NFE if it matches the criteria (number + supplier + date).
    
    Parameters:
    - num_nf (required): The NFE number
    - fornecedor_id (optional): The supplier's ID from purchase order (used to get CNPJ)
    - fornecedor_nome (optional): The supplier's name for matching if no CNPJ
    - dt_ent (optional): The entry date for date matching (YYYY-MM-DD)
    
    Returns the NFE if found and matches criteria, or not found if no match.
    """
    from app.models import NFEData, NFEEmitente, Supplier
    from fuzzywuzzy import fuzz
    from datetime import datetime, timedelta
    
    num_nf = request.args.get('num_nf')
    fornecedor_id = request.args.get('fornecedor_id')
    fornecedor_nome = request.args.get('fornecedor_nome')
    dt_ent_str = request.args.get('dt_ent')
    
    if not num_nf:
        return jsonify({'error': 'num_nf is required'}), 400
    
    try:
        # Clean up num_nf - remove leading zeros for comparison
        num_nf_clean = str(num_nf).lstrip('0')
        
        # Parse entry date if provided
        dt_ent = None
        if dt_ent_str:
            try:
                dt_ent = datetime.strptime(dt_ent_str[:10], '%Y-%m-%d').date()
            except:
                pass
        
        # Special case for Mercado Pago (marketplace - fornecedor won't match)
        if fornecedor_id and str(fornecedor_id) == '1160':
            # For Mercado Pago, search only by number and date validation
            nfes = NFEData.query.filter_by(numero=num_nf).all()
            if not nfes:
                nfes = NFEData.query.filter(NFEData.numero == num_nf_clean).all()
            
            if not nfes:
                return jsonify({'error': 'NFE not found in database', 'found': False}), 404
            
            # If date provided, only return NFE if it's after the purchase date
            if dt_ent:
                for nfe in nfes:
                    nfe_date = nfe.data_emissao
                    if hasattr(nfe_date, 'date'):
                        nfe_date = nfe_date.date()
                    # NFE must be on or after purchase date
                    if nfe_date >= dt_ent:
                        return jsonify({
                            'found': True,
                            'chave': nfe.chave,
                            'numero': nfe.numero,
                            'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                            'valor': nfe.valor_total,
                            'fornecedor': nfe.emitente.nome if nfe.emitente else None,
                            'is_mercadopago': True
                        }), 200
                # No NFE found after purchase date
                return jsonify({'error': 'NFE found but issued before purchase date', 'found': False}), 404
            else:
                # No date validation, return first match
                nfe = nfes[0]
                return jsonify({
                    'found': True,
                    'chave': nfe.chave,
                    'numero': nfe.numero,
                    'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                    'valor': nfe.valor_total,
                    'fornecedor': nfe.emitente.nome if nfe.emitente else None,
                    'is_mercadopago': True
                }), 200
        
        # Normal flow for other suppliers
        # Query NFEs with this number
        nfes = NFEData.query.filter_by(numero=num_nf).all()
        
        # Also try with the cleaned version
        if not nfes:
            nfes = NFEData.query.filter(NFEData.numero == num_nf_clean).all()
        
        if not nfes:
            return jsonify({'error': 'NFE not found in database', 'found': False}), 404
        
        # Get supplier CNPJ from database if fornecedor_id is provided
        fornecedor_cnpj = None
        if fornecedor_id:
            supplier = Supplier.query.filter(Supplier.cod_for == str(fornecedor_id)).first()
            if supplier and supplier.nvl_forn_cnpj_forn_cpf:
                fornecedor_cnpj = ''.join(filter(str.isdigit, str(supplier.nvl_forn_cnpj_forn_cpf)))
        
        # Find the correct NFE by matching supplier (CNPJ or name) and date
        matched_nfe = None
        
        for nfe in nfes:
            # 1. Check CNPJ match (primary criteria if available)
            if fornecedor_cnpj and nfe.emitente and nfe.emitente.cnpj:
                emit_cnpj_clean = ''.join(filter(str.isdigit, str(nfe.emitente.cnpj)))
                if emit_cnpj_clean == fornecedor_cnpj:
                    # CNPJ matches - check date if provided
                    if dt_ent and nfe.data_emissao:
                        nfe_date = nfe.data_emissao
                        if hasattr(nfe_date, 'date'):
                            nfe_date = nfe_date.date()
                        # Allow 30 days tolerance for date matching
                        days_diff = abs((nfe_date - dt_ent).days)
                        if days_diff <= 30:
                            matched_nfe = nfe
                            break
                    else:
                        # No date to check, CNPJ is enough
                        matched_nfe = nfe
                        break
            
            # 2. If no CNPJ available, use supplier name fuzzy matching
            elif not fornecedor_cnpj and fornecedor_nome and nfe.emitente and nfe.emitente.nome:
                name_ratio = fuzz.token_set_ratio(
                    fornecedor_nome.lower(),
                    nfe.emitente.nome.lower()
                )
                # Require high match (80%+) for name-based matching
                if name_ratio >= 80:
                    # Name matches - check date if provided
                    if dt_ent and nfe.data_emissao:
                        nfe_date = nfe.data_emissao
                        if hasattr(nfe_date, 'date'):
                            nfe_date = nfe_date.date()
                        # Allow 30 days tolerance for date matching
                        days_diff = abs((nfe_date - dt_ent).days)
                        if days_diff <= 30:
                            matched_nfe = nfe
                            break
                    else:
                        # No date to check, name match is enough
                        matched_nfe = nfe
                        break
        
        # If no match found with strict criteria, return not found
        if not matched_nfe:
            return jsonify({'error': 'NFE not found matching criteria', 'found': False}), 404
        
        return jsonify({
            'found': True,
            'chave': matched_nfe.chave,
            'numero': matched_nfe.numero,
            'data_emissao': matched_nfe.data_emissao.isoformat() if matched_nfe.data_emissao else None,
            'valor': matched_nfe.valor_total,
            'fornecedor': matched_nfe.emitente.nome if matched_nfe.emitente else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/sync_nfe', methods=['POST'])
@login_required
def sync_nfe_api():
    """API endpoint to manually trigger NFE sync"""
    from app.tasks.sync_nfe import sync_nfe_for_yesterday
    
    try:
        result = sync_nfe_for_yesterday()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@bp.route('/match_purchase_nfe', methods=['GET'])
@login_required
def match_purchase_nfe():
    """
    Find NFEs that match a purchase order and score their similarity.
    
    Parameters:
    - cod_pedc (required): The purchase order code
    - cod_emp1 (required): The company code
    - max_results (optional): Maximum number of matches to return (default: 10)
    
    Returns a list of NFEs scored by how well they fulfill the purchase order.
    """
    from app.utils import score_purchase_nfe_match
    cod_pedc = request.args.get('cod_pedc')
    cod_emp1 = request.args.get('cod_emp1')
    max_results = request.args.get('max_results', default=10, type=int)
    
    result = score_purchase_nfe_match(cod_pedc, cod_emp1)
    
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    
    # Limit matches if needed
    matches = result.get('matches', [])
    if max_results and len(matches) > max_results:
        result['matches'] = matches[:max_results]
    
    return jsonify({
        'purchase_order': result.get('purchase_order'),
        'matches_found': len(result.get('matches', [])),
        'matches': result.get('matches', [])
    }), 200

@bp.route('/user_purchases', methods=['GET'])
@login_required
def get_user_purchases():
    from datetime import datetime, timedelta
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status', 'all')
    username = request.args.get('username')
    
    # Convert string dates to datetime
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = (datetime.now() - timedelta(days=30)).date()
        
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # Get user info
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    query = PurchaseOrder.query.filter(
        PurchaseOrder.dt_emis.between(start_date, end_date)
    )
    
    # If user is not admin, filter by purchaser name
    if user.role != 'admin' and user.system_name:
        query = query.filter(PurchaseOrder.func_nome.ilike(f'%{user.system_name}%'))
    
    # Filter by status if requested
    if status != 'all':
        if status == 'pending':
            query = query.filter(PurchaseOrder.is_fulfilled == False)
        elif status == 'fulfilled':
            query = query.filter(PurchaseOrder.is_fulfilled == True)
    
    purchase_orders = query.order_by(PurchaseOrder.dt_emis.desc()).all()
    
    result = []
    for order in purchase_orders:
        items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
        
        total_items = len(items)
        fulfilled_items = 0
        partially_fulfilled_items = 0
        
        items_data = []
        for item in items:
            # Get NFEs linked to this item
            nfes = NFEntry.query.filter_by(
                cod_emp1=order.cod_emp1,
                cod_pedc=item.cod_pedc,
                linha=str(item.linha)
            ).all()
            
            nfes_data = []
            for nfe in nfes:
                nfes_data.append({
                    'id': nfe.id,
                    'num_nf': nfe.num_nf,
                    'dt_ent': nfe.dt_ent.isoformat() if nfe.dt_ent else None,
                    'qtde': nfe.qtde
                })
            
            # Determine item fulfillment status
            if item.qtde_atendida and item.quantidade:
                if float(item.qtde_atendida) >= float(item.quantidade):
                    fulfilled_items += 1
                elif float(item.qtde_atendida) > 0:
                    partially_fulfilled_items += 1
            
            items_data.append({
                'id': item.id,
                'item_id': item.item_id,
                'descricao': item.descricao,
                'quantidade': item.quantidade,
                'unidade_medida': item.unidade_medida,
                'preco_unitario': item.preco_unitario,
                'total': item.total,
                'qtde_atendida': item.qtde_atendida,
                'nfes': nfes_data
            })
        
        order_status = 'pending'
        if fulfilled_items == total_items:
            order_status = 'fulfilled'
        elif partially_fulfilled_items > 0 or fulfilled_items > 0:
            order_status = 'partial'
        
        # Skip if filtering by 'partial' and this isn't partial
        if status == 'partial' and order_status != 'partial':
            continue
        
        order_data = {
            'id': order.id,
            'cod_pedc': order.cod_pedc,
            'dt_emis': _parse_date(order.dt_emis),
            'fornecedor_descricao': order.fornecedor_descricao,
            'fornecedor_id': order.fornecedor_id,
            'total_pedido_com_ipi': order.total_pedido_com_ipi,
            'status': order_status,
            'is_fulfilled': order.is_fulfilled,
            'expanded': False,  # For UI expansion
            'items': items_data
        }
        
        result.append(order_data)
    
    return jsonify(result), 200



@bp.route('/view_danfe_template/<int:nfe_id>', methods=['GET'])
@login_required
def view_danfe_template(nfe_id):
    """Render the DANFE using the template from cfirmo33/template-nfe"""
    from app.models import NFEData, NFEItem, NFEEmitente, NFEDestinatario
    
    nfe = NFEData.query.get(nfe_id)
    if not nfe:
        return jsonify({'error': 'NFE not found'}), 404
    
    # Format the data for the template
    danfe_data = {
        'chave': nfe.chave,
        'numero': nfe.numero,
        'serie': nfe.serie,
        'data_emissao': nfe.data_emissao.strftime('%d/%m/%Y %H:%M:%S') if nfe.data_emissao else '',
        'natureza_operacao': nfe.natureza_operacao,
        'protocolo': nfe.protocolo,
        'valor_total': nfe.valor_total,
        'emitente': {
            'nome': nfe.emitente.nome if nfe.emitente else '',
            'cnpj': nfe.emitente.cnpj if nfe.emitente else '',
            'endereco': f"{nfe.emitente.logradouro}, {nfe.emitente.numero}" if nfe.emitente else '',
            'bairro': nfe.emitente.bairro if nfe.emitente else '',
            'municipio': nfe.emitente.municipio if nfe.emitente else '',
            'uf': nfe.emitente.uf if nfe.emitente else '',
            'cep': nfe.emitente.cep if nfe.emitente else '',
            'telefone': nfe.emitente.telefone if nfe.emitente else '',
        },
        'destinatario': {
            'nome': nfe.destinatario.nome if nfe.destinatario else '',
            'cnpj': nfe.destinatario.cnpj if nfe.destinatario else '',
            'endereco': f"{nfe.destinatario.logradouro}, {nfe.destinatario.numero}" if nfe.destinatario else '',
            'bairro': nfe.destinatario.bairro if nfe.destinatario else '',
            'municipio': nfe.destinatario.municipio if nfe.destinatario else '',
            'uf': nfe.destinatario.uf if nfe.destinatario else '',
            'cep': nfe.destinatario.cep if nfe.destinatario else '',
        },
        'itens': [
            {
                'codigo': item.codigo,
                'descricao': item.descricao,
                'quantidade': item.quantidade_comercial,
                'unidade': item.unidade_comercial,
                'valor_unitario': item.valor_unitario_comercial,
                'valor_total': item.valor_total_bruto,
                'ncm': item.ncm,
                'cfop': item.cfop,
            } for item in nfe.itens
        ]
    }
    
    # You would use the template from cfirmo33/template-nfe here
    # For now, render a simple HTML template with the data
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DANFE - {nfe.numero}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .danfe-container {{ border: 1px solid #ccc; padding: 20px; max-width: 800px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
            .section {{ margin: 15px 0; }}
            .section-title {{ font-weight: bold; background: #f5f5f5; padding: 5px; }}
            .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
            .item {{ margin-bottom: 5px; }}
            .items-table {{ width: 100%; border-collapse: collapse; }}
            .items-table th, .items-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .items-table th {{ background-color: #f5f5f5; }}
            .totals {{ text-align: right; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="danfe-container">
            <div class="header">
                <div>
                    <h2>DANFE</h2>
                    <p>Documento Auxiliar da Nota Fiscal Eletrônica</p>
                </div>
                <div>
                    <p><strong>Número:</strong> {danfe_data['numero']}</p>
                    <p><strong>Série:</strong> {danfe_data['serie']}</p>
                    <p><strong>Data Emissão:</strong> {danfe_data['data_emissao']}</p>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Chave de Acesso</div>
                <p>{danfe_data['chave']}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Protocolo de Autorização</div>
                <p>{danfe_data['protocolo']}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Natureza da Operação</div>
                <p>{danfe_data['natureza_operacao']}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Emitente</div>
                <div class="grid">
                    <div class="item"><strong>Nome:</strong> {danfe_data['emitente']['nome']}</div>
                    <div class="item"><strong>CNPJ:</strong> {danfe_data['emitente']['cnpj']}</div>
                    <div class="item"><strong>Endereço:</strong> {danfe_data['emitente']['endereco']}</div>
                    <div class="item"><strong>Bairro:</strong> {danfe_data['emitente']['bairro']}</div>
                    <div class="item"><strong>Município:</strong> {danfe_data['emitente']['municipio']}</div>
                    <div class="item"><strong>UF:</strong> {danfe_data['emitente']['uf']}</div>
                    <div class="item"><strong>CEP:</strong> {danfe_data['emitente']['cep']}</div>
                    <div class="item"><strong>Telefone:</strong> {danfe_data['emitente']['telefone']}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Destinatário</div>
                <div class="grid">
                    <div class="item"><strong>Nome:</strong> {danfe_data['destinatario']['nome']}</div>
                    <div class="item"><strong>CNPJ:</strong> {danfe_data['destinatario']['cnpj']}</div>
                    <div class="item"><strong>Endereço:</strong> {danfe_data['destinatario']['endereco']}</div>
                    <div class="item"><strong>Bairro:</strong> {danfe_data['destinatario']['bairro']}</div>
                    <div class="item"><strong>Município:</strong> {danfe_data['destinatario']['municipio']}</div>
                    <div class="item"><strong>UF:</strong> {danfe_data['destinatario']['uf']}</div>
                    <div class="item"><strong>CEP:</strong> {danfe_data['destinatario']['cep']}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">Produtos / Serviços</div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Descrição</th>
                            <th>NCM</th>
                            <th>CFOP</th>
                            <th>Qtd</th>
                            <th>Un</th>
                            <th>Valor Unit.</th>
                            <th>Valor Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([f"<tr><td>{item['codigo']}</td><td>{item['descricao']}</td><td>{item['ncm']}</td><td>{item['cfop']}</td><td>{item['quantidade']}</td><td>{item['unidade']}</td><td>R$ {item['valor_unitario']:.2f}</td><td>R$ {item['valor_total']:.2f}</td></tr>" for item in danfe_data['itens']])}
                    </tbody>
                </table>
            </div>
            
            <div class="totals">
                <p><strong>Valor Total da Nota:</strong> R$ {danfe_data['valor_total']:.2f}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@bp.route('/auto_match_nfes', methods=['GET'])
@login_required
def auto_match_nfes():
    """Find potential NFE matches for pending purchase orders"""
    from app.utils import score_purchase_nfe_match
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', default=50, type=int)
    limit = request.args.get('limit', default=10, type=int)
    
    # Query purchase orders that are not fully fulfilled
    query = PurchaseOrder.query.filter(PurchaseOrder.is_fulfilled == False)
    
    # Filter by date if provided
    if start_date:
        query = query.filter(PurchaseOrder.dt_emis >= start_date)
    if end_date:
        query = query.filter(PurchaseOrder.dt_emis <= end_date)
    
    # Get purchases for the current user if not admin
    if current_user.role != 'admin' and current_user.system_name:
        query = query.filter(PurchaseOrder.func_nome.ilike(f'%{current_user.system_name}%'))
    
    # Get recent unfulfilled orders
    purchase_orders = query.order_by(PurchaseOrder.dt_emis.desc()).limit(100).all()
    
    results = []
    for po in purchase_orders:
        # Skip if no items
        items = PurchaseItem.query.filter_by(purchase_order_id=po.id).all()
        if not items:
            continue
            
        # Find potential matches
        matches = score_purchase_nfe_match(po.cod_pedc)
        
        # Filter by minimum score
        good_matches = [m for m in matches if m["score"] >= min_score]
        if not good_matches:
            continue
            
        # Take best match
        best_match = good_matches[0]
        
        # Add to results
        results.append({
            'purchase_order': {
                'id': po.id,
                'cod_pedc': po.cod_pedc,
                'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                'fornecedor_descricao': po.fornecedor_descricao,
                'total_pedido_com_ipi': po.total_pedido_com_ipi,
                'item_count': len(items)
            },
            'best_match': best_match
        })
    
    # Sort by match score (highest first)
    results.sort(key=lambda x: x['best_match']['score'], reverse=True)
    
    # Limit results
    results = results[:limit]
    
    return jsonify(results), 200


@bp.route('/extract_reference_data', methods=['POST'])
@login_required
def extract_reference_data():
    import json
    import tempfile
    import os
    import google.generativeai as genai
    from datetime import datetime

    # Check if file was uploaded
    if 'reference_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['reference_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    file_extension = file.filename.split('.')[-1].lower()
    file_type = request.form.get('file_type', '')
    
    try:
        temp_file_path = os.path.join(tempfile.gettempdir(), file.filename)
        file.save(temp_file_path)
        
        # Configure Google Generative AI (Gemini)
        gemini_api_key = Config.GEMINI_API_KEY
        if not gemini_api_key:
            return jsonify({'error': 'GEMINI_API_KEY not set in environment'}), 500
        
        genai.configure(api_key=gemini_api_key)
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
        
        content_parts = []
        
        # Process based on file type
        if file_extension in ['csv', 'xlsx', 'xls']:
            # Use existing code for Excel/CSV files
            import pandas as pd
            if file_extension == 'csv':
                df = pd.read_csv(temp_file_path)
            else:
                df = pd.read_excel(temp_file_path)
                
            # Convert dataframe to text for AI processing
            excel_text = "Excel file content:\n\n"
            for sheet_name, sheet_df in pd.read_excel(temp_file_path, sheet_name=None).items():
                excel_text += f"Sheet: {sheet_name}\n"
                excel_text += sheet_df.to_string(index=False, max_rows=100) + "\n\n"
            
            content_parts.append(excel_text)
            
        elif file_extension == 'pdf':
            # Extract text from PDF
            try:
                import PyPDF2
                text_content = ""
                with open(temp_file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page_num in range(len(pdf_reader.pages)):
                        text_content += pdf_reader.pages[page_num].extract_text()
                
                if text_content.strip():
                    content_parts.append(text_content)
                else:
                    # If text extraction yields no results, convert PDF to image
                    try:
                        from pdf2image import convert_from_path
                        images = convert_from_path(temp_file_path, dpi=300, first_page=1, last_page=5)
                        
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
                        return jsonify({'error': f'Failed to process PDF as image: {str(e2)}'}), 500
            except Exception as e:
                return jsonify({'error': f'Failed to extract text from PDF: {str(e)}'}), 500
                
        elif file_extension in ['jpg', 'jpeg', 'png']:
            # Process image directly
            try:
                with open(temp_file_path, 'rb') as img_file:
                    img_data = img_file.read()
                    
                content_parts.append({
                    "mime_type": f"image/{file_extension}",
                    "data": img_data
                })
            except Exception as e:
                return jsonify({'error': f'Failed to process image: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Formato de arquivo não suportado'}), 400
        
        # Create prompt for AI to extract structured data
        prompt = """
        Você é um assistente especializado em extrair informações estruturadas de documentos. 
        Analise o conteúdo fornecido e identifique uma lista de itens com suas características:
        
        1. Código do item (se disponível)
        2. Descrição detalhada do item
        3. Quantidade (se disponível)
        4. Unidade de medida (se disponível)
        
        Retorne apenas um objeto JSON seguindo esta estrutura:
        {
            "items": [
                {
                    "item_id": "código do item ou string vazia se não disponível",
                    "descricao": "descrição completa do item",
                    "quantidade": 0, // número ou 0 se não disponível
                    "unidade_medida": "unidade de medida ou string vazia se não disponível"
                },
                // mais itens conforme necessário
            ]
        }

        Se não conseguir identificar alguma informação, use valores padrão: string vazia para textos e 0 para números.
        Não inclua nenhum outro texto ou explicação na sua resposta, apenas o JSON.
        """
        
        # Add prompt to content parts
        all_parts = [prompt] + content_parts
        
        # Send to AI model
        response = model.generate_content(all_parts)
        response_text = response.text
        
        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            
            if json_match:
                ai_result = json.loads(json_match.group(1))
            else:
                # Try to parse the whole response as JSON
                ai_result = json.loads(response_text)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Failed to parse AI response as JSON: {str(e)}'}), 500
        
        # Process extracted items
        items = []
        for item_data in ai_result.get('items', []):
            item_id = item_data.get('item_id', '')
            description = item_data.get('descricao', '')
            quantity = item_data.get('quantidade', 0)
            
            item = {
                'item_id': item_id,
                'descricao': description,
                'quantidade': quantity,
                'last_purchase': None
            }
            
            # Look up last purchase data if item_id exists
            if item_id:
                last_purchase = PurchaseItem.query.filter_by(item_id=item_id).order_by(PurchaseItem.dt_emis.desc()).first()
                if last_purchase:
                    item['last_purchase'] = {
                        'fornecedor': last_purchase.purchase_order.fornecedor_descricao,
                        'price': last_purchase.preco_unitario,
                        'date': last_purchase.purchase_order.dt_emis,
                        'cod_pedc': last_purchase.cod_pedc
                    }
            
            items.append(item)
        
        # Format the response to match quotation_items endpoint
        response_data = {
            'cod_cot': 'REF-' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'dt_emissao': datetime.now().isoformat(),
            'items': items
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass


# ==================== NFE SEARCH ENDPOINTS ====================

def _check_supplier_match(purchase_order, nfe_emitente):
    """
    Check if a purchase order's supplier matches an NFE emitente.
    Uses CNPJ matching as primary, fuzzy name matching as fallback.
    
    Returns:
        bool: True if supplier matches emitente, False otherwise
    """
    from app.models import Supplier
    from fuzzywuzzy import fuzz
    
    if not purchase_order or not nfe_emitente:
        return False
    
    # Get NFE emitente CNPJ
    emit_cnpj_clean = None
    if nfe_emitente.cnpj:
        emit_cnpj_clean = ''.join(filter(str.isdigit, str(nfe_emitente.cnpj)))
    
    # Get supplier CNPJ from database using fornecedor_id
    fornecedor_cnpj = None
    if purchase_order.fornecedor_id:
        supplier = Supplier.query.filter(Supplier.cod_for == str(purchase_order.fornecedor_id)).first()
        if supplier and supplier.nvl_forn_cnpj_forn_cpf:
            fornecedor_cnpj = ''.join(filter(str.isdigit, str(supplier.nvl_forn_cnpj_forn_cpf)))
    
    # 1. Check CNPJ match (primary criteria)
    if emit_cnpj_clean and fornecedor_cnpj:
        return emit_cnpj_clean == fornecedor_cnpj
    
    # 2. If no CNPJ available, use supplier name fuzzy matching
    if purchase_order.fornecedor_descricao and nfe_emitente.nome:
        name_ratio = fuzz.token_set_ratio(
            purchase_order.fornecedor_descricao.lower(),
            nfe_emitente.nome.lower()
        )
        # Require high match (80%+) for name-based matching
        return name_ratio >= 80
    
    return False


@bp.route('/search_nfe', methods=['GET'])
@login_required
def search_nfe():
    """
    Search for NFEs and find linked purchase orders.
    
    Parameters:
    - query: Search term (NFE number, chave, supplier name, or item description)
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - search_by_number: Search by NFE number (default: true)
    - search_by_chave: Search by chave de acesso (default: true)
    - search_by_fornecedor: Search by supplier name (default: false)
    - search_by_item: Search by item description (default: true)
    - include_estimated: Include AI-estimated matches (default: true)
    """
    from app.models import NFEData, NFEEmitente, NFEItem, NFEntry, PurchaseOrder, PurchaseItem, PurchaseItemNFEMatch
    from datetime import datetime
    from fuzzywuzzy import fuzz
    
    query = request.args.get('query', '').strip()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search_by_number = request.args.get('search_by_number', 'true').lower() == 'true'
    search_by_chave = request.args.get('search_by_chave', 'true').lower() == 'true'
    search_by_fornecedor = request.args.get('search_by_fornecedor', 'false').lower() == 'true'
    search_by_item = request.args.get('search_by_item', 'true').lower() == 'true'
    include_estimated = request.args.get('include_estimated', 'true').lower() == 'true'
    exact_term_search = request.args.get('exact_term_search', 'true').lower() == 'true'
    
    # Allow empty query if date range is provided
    if not query and not start_date_str and not end_date_str:
        return jsonify({'error': 'Query parameter or date range is required'}), 400
    
    try:
        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Build NFE query
        nfe_filters = []
        
        # Only add search filters if query is provided
        if query:
            if search_by_number:
                # Use exact match or LIKE based on exact_term_search
                nfe_filters.append(NFEData.numero == query)
                if not exact_term_search:
                    nfe_filters.append(NFEData.numero.ilike(f'%{query}%'))
            
            if search_by_chave:
                if exact_term_search:
                    nfe_filters.append(NFEData.chave == query)
                else:
                    nfe_filters.append(NFEData.chave.ilike(f'%{query}%'))
        
        # Query NFEs
        nfe_query = NFEData.query
        if nfe_filters:
            nfe_query = nfe_query.filter(or_(*nfe_filters))
        
        # Apply date filters
        if start_date:
            nfe_query = nfe_query.filter(NFEData.data_emissao >= start_date)
        if end_date:
            nfe_query = nfe_query.filter(NFEData.data_emissao <= end_date)
        
        # Order by most recent first
        nfe_query = nfe_query.order_by(NFEData.data_emissao.desc())
        
        nfes = nfe_query.limit(50).all()
        
        # If searching by supplier, also filter by emitente name
        if search_by_fornecedor and query:
            if exact_term_search:
                supplier_nfes = NFEData.query.join(NFEEmitente).filter(
                    NFEEmitente.nome == query
                )
            else:
                supplier_nfes = NFEData.query.join(NFEEmitente).filter(
                    NFEEmitente.nome.ilike(f'%{query}%')
                )
            if start_date:
                supplier_nfes = supplier_nfes.filter(NFEData.data_emissao >= start_date)
            if end_date:
                supplier_nfes = supplier_nfes.filter(NFEData.data_emissao <= end_date)
            
            supplier_nfes = supplier_nfes.order_by(NFEData.data_emissao.desc()).limit(50).all()
            
            # Merge results
            existing_ids = {n.id for n in nfes}
            for nfe in supplier_nfes:
                if nfe.id not in existing_ids:
                    nfes.append(nfe)
        
        # If searching by item description, search NFEItem
        if search_by_item and query:
            if exact_term_search:
                item_nfes = NFEData.query.join(NFEItem).filter(
                    NFEItem.descricao == query
                )
            else:
                item_nfes = NFEData.query.join(NFEItem).filter(
                    NFEItem.descricao.ilike(f'%{query}%')
                )
            if start_date:
                item_nfes = item_nfes.filter(NFEData.data_emissao >= start_date)
            if end_date:
                item_nfes = item_nfes.filter(NFEData.data_emissao <= end_date)
            
            item_nfes = item_nfes.order_by(NFEData.data_emissao.desc()).limit(50).all()
            
            # Merge results
            existing_ids = {n.id for n in nfes}
            for nfe in item_nfes:
                if nfe.id not in existing_ids:
                    nfes.append(nfe)
        
        # Sort all NFEs by date (most recent first) after merging
        nfes = sorted(nfes, key=lambda x: x.data_emissao or datetime.min, reverse=True)
        
        # Hard cap on total NFEs to prevent slow responses on broad queries
        nfes = nfes[:50]
        
        # Format NFE results
        nfe_results = []
        nfe_numbers = set()
        # Track all linked purchases (keys that matched at least one NFE)
        linked_purchase_keys = set()  # (cod_pedc, cod_emp1, linha)
        # Track all potential purchases for checking if they match any NFE
        all_potential_purchases = {}  # key: (cod_pedc, cod_emp1, linha), value: purchase info
        
        for nfe in nfes:
            emitente = NFEEmitente.query.filter_by(nfe_id=nfe.id).first()
            # Get matched items if searching by item
            matched_items = []
            if search_by_item:
                if exact_term_search:
                    items = NFEItem.query.filter(
                        NFEItem.nfe_id == nfe.id,
                        NFEItem.descricao == query
                    ).all()
                else:
                    items = NFEItem.query.filter(
                        NFEItem.nfe_id == nfe.id,
                        NFEItem.descricao.ilike(f'%{query}%')
                    ).all()
                matched_items = [item.descricao for item in items[:3]]  # Limit to 3
            
            # Find linked purchase orders via NFEntry for this NFE
            # Only include purchases where the supplier matches the NFE emitente
            linked_purchases = []
            estimated_purchases = []
            if nfe.numero:
                nf_entries = NFEntry.query.filter(NFEntry.num_nf == nfe.numero).all()
                for entry in nf_entries:
                    po = PurchaseOrder.query.filter_by(
                        cod_pedc=entry.cod_pedc,
                        cod_emp1=entry.cod_emp1
                    ).first()
                    if po:

                        item = PurchaseItem.query.filter_by(
                            cod_pedc=entry.cod_pedc,
                            cod_emp1=entry.cod_emp1,
                            linha=str(entry.linha) if entry.linha else None
                        ).first()

                        # Calculate adjusted total from adjustments
                        adjustments = getattr(po, 'adjustments', [])
                        base_total = po.total_pedido_com_ipi or 0
                        adjusted_total = apply_adjustments(base_total, adjustments)
                        
                        purchase_info = {
                            'cod_pedc': po.cod_pedc,
                            'cod_emp1': po.cod_emp1,
                            'fornecedor': po.fornecedor_descricao,
                            'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                            'total_pedido': adjusted_total,
                            'func_nome': po.func_nome,
                            'item_descricao': item.descricao if item else None,
                            'linha': entry.linha,
                            'quantidade': item.quantidade if item else None,
                            'qtde_atendida': item.qtde_atendida if item else None,
                            'qtde_saldo': item.qtde_saldo if item else None,
                            'preco_unitario': item.preco_unitario if item else None,
                            'total_item': item.total if item else None,
                            'unidade_medida': item.unidade_medida if item else None,
                            'dt_entrega': item.dt_entrega.isoformat() if item and item.dt_entrega else None,
                            'nfe_numero': nfe.numero,
                            'is_estimated': False,
                        }
                        
                        key = (po.cod_pedc, po.cod_emp1, entry.linha)
                        
                        # Track all potential purchases
                        if key not in all_potential_purchases:
                            all_potential_purchases[key] = purchase_info
                        
                        # Check if supplier matches NFE emitente
                        if _check_supplier_match(po, emitente):
                            linked_purchases.append(purchase_info)
                            linked_purchase_keys.add(key)
                
                # Also include estimated matches from PurchaseItemNFEMatch for this NFE
                if include_estimated:
                    estimated_matches = PurchaseItemNFEMatch.query.filter(
                        PurchaseItemNFEMatch.nfe_numero == nfe.numero
                    ).all()
                    
                    for match in estimated_matches:
                        item = PurchaseItem.query.get(match.purchase_item_id)
                        if item:
                            po = PurchaseOrder.query.get(item.purchase_order_id)
                            if po:
                                # Check if already in linked_purchases
                                key = (po.cod_pedc, po.cod_emp1, str(item.linha) if item.linha else None)
                                already_linked = any(
                                    p['cod_pedc'] == po.cod_pedc and p['linha'] == item.linha 
                                    for p in linked_purchases
                                )
                                if not already_linked:
                                    purchase_info = {
                                        'cod_pedc': po.cod_pedc,
                                        'cod_emp1': po.cod_emp1,
                                        'fornecedor': po.fornecedor_descricao,
                                        'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                                        'total_pedido': po.total_liquido,
                                        'func_nome': po.func_nome,
                                        'item_descricao': item.descricao,
                                        'linha': item.linha,
                                        'quantidade': item.quantidade,
                                        'qtde_atendida': item.qtde_atendida,
                                        'qtde_saldo': item.qtde_saldo,
                                        'preco_unitario': item.preco_unitario,
                                        'total_item': item.total,
                                        'unidade_medida': item.unidade_medida,
                                        'dt_entrega': item.dt_entrega.isoformat() if item.dt_entrega else None,
                                        'nfe_numero': nfe.numero,
                                        'is_estimated': True,
                                        'match_score': match.match_score,
                                    }
                                    estimated_purchases.append(purchase_info)
            
            nfe_results.append({
                'id': nfe.id,
                'numero': nfe.numero,
                'chave': nfe.chave,
                'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                'valor_total': nfe.valor_total,
                'fornecedor': emitente.nome if emitente else None,
                'cnpj': emitente.cnpj if emitente else None,
                'matched_items': matched_items,
                'linked_purchases': linked_purchases,
                'estimated_purchases': estimated_purchases,
            })
            if nfe.numero:
                nfe_numbers.add(nfe.numero)
        
        # Build unlinked_purchases_map: purchases that didn't match ANY NFE
        unlinked_purchases_map = {
            k: v for k, v in all_potential_purchases.items() 
            if k not in linked_purchase_keys
        }
        
        # Find linked purchase orders
        purchase_orders = []
        
        # 1. Search in NFEntry (direct links)
        if exact_term_search:
            nf_entries = NFEntry.query.filter(NFEntry.num_nf == query).all()
        else:
            nf_entries = NFEntry.query.filter(
                or_(
                    NFEntry.num_nf == query,
                    NFEntry.num_nf.ilike(f'%{query}%') #??
                )
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        
        for entry in nf_entries:
            po = PurchaseOrder.query.filter_by(
                cod_pedc=entry.cod_pedc,
                cod_emp1=entry.cod_emp1
            ).first()
            
            if po:
                item = PurchaseItem.query.filter_by(
                    cod_pedc=entry.cod_pedc,
                    cod_emp1=entry.cod_emp1,
                    linha=str(entry.linha) if entry.linha else None
                ).first()
                
                # Check if this purchase was already linked to any NFE
                purchase_key = (po.cod_pedc, po.cod_emp1, entry.linha)
                is_linked = purchase_key in linked_purchase_keys
                
                # Find linked NFEData for this num_nf
                linked_nfe_data = None
                if entry.num_nf:
                    nfe_data = NFEData.query.filter_by(numero=entry.num_nf).first()
                    if nfe_data:
                        emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                        
                        linked_nfe_data = {
                            'id': nfe_data.id,
                            'numero': nfe_data.numero,
                            'chave': nfe_data.chave,
                            'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                            'valor_total': nfe_data.valor_total,
                            'fornecedor': emitente.nome if emitente else None,
                            'cnpj': emitente.cnpj if emitente else None,
                        }
                
                purchase_orders.append({
                    'cod_pedc': po.cod_pedc,
                    'cod_emp1': po.cod_emp1,
                    'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                    'fornecedor': po.fornecedor_descricao,
                    'item_descricao': item.descricao if item else None,
                    'valor': item.total if item else po.total_liquido,
                    'match_type': 'linked' if is_linked else 'unlinked',
                    'nfe_numero': entry.num_nf,
                    'nfe_data': linked_nfe_data,
                })
        
        # 2. Search in PurchaseItemNFEMatch (AI-estimated matches)
        if include_estimated:
            if exact_term_search:
                estimated_matches = PurchaseItemNFEMatch.query.filter(
                    PurchaseItemNFEMatch.nfe_numero == query
                ).all()
            else:
                estimated_matches = PurchaseItemNFEMatch.query.filter(
                    or_(
                        PurchaseItemNFEMatch.nfe_numero == query,
                        PurchaseItemNFEMatch.nfe_numero.ilike(f'%{query}%')
                    )
                ).all()
            
            for match in estimated_matches:
                item = PurchaseItem.query.get(match.purchase_item_id)
                if item:
                    po = PurchaseOrder.query.get(item.purchase_order_id)
                    if po:
                        # Check if this PO is already in the list
                        existing = next(
                            (p for p in purchase_orders 
                             if p['cod_pedc'] == po.cod_pedc and p.get('item_descricao') == item.descricao),
                            None
                        )
                        if not existing:
                            # Check if this purchase was linked to any NFE
                            # For estimated matches, we check by (cod_pedc, cod_emp1, linha)
                            purchase_key = (po.cod_pedc, po.cod_emp1, str(item.linha) if item.linha else None)
                            is_linked = purchase_key in linked_purchase_keys
                            
                            # Find linked NFEData for this nfe_numero
                            linked_nfe_data = None
                            if match.nfe_numero:
                                nfe_data = NFEData.query.filter_by(numero=match.nfe_numero).first()
                                if nfe_data:
                                    emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                                    
                                    linked_nfe_data = {
                                        'id': nfe_data.id,
                                        'numero': nfe_data.numero,
                                        'chave': nfe_data.chave,
                                        'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                                        'valor_total': nfe_data.valor_total,
                                        'fornecedor': emitente.nome if emitente else None,
                                        'cnpj': emitente.cnpj if emitente else None,
                                    }
                            
                            purchase_orders.append({
                                'cod_pedc': po.cod_pedc,
                                'cod_emp1': po.cod_emp1,
                                'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                                'fornecedor': po.fornecedor_descricao,
                                'item_descricao': item.descricao,
                                'valor': item.total,
                                'match_type': 'estimated' if is_linked else 'estimated_unlinked',
                                'match_score': match.match_score,
                                'nfe_numero': match.nfe_numero,
                                'nfe_data': linked_nfe_data,
                            })
        
        # 3. Search by purchase order number (cod_pedc) to find linked NFEs
        if exact_term_search:
            purchase_entries = NFEntry.query.filter(
                NFEntry.cod_pedc == query
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        else:
            purchase_entries = NFEntry.query.filter(
                NFEntry.cod_pedc.ilike(f'%{query}%')
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        
        for entry in purchase_entries:
            # Check if already added from section 1
            already_added = any(
                p['cod_pedc'] == entry.cod_pedc and p.get('nfe_numero') == entry.num_nf 
                for p in purchase_orders
            )
            if already_added:
                continue
                
            po = PurchaseOrder.query.filter_by(
                cod_pedc=entry.cod_pedc,
                cod_emp1=entry.cod_emp1
            ).first()
            
            if po:
                item = PurchaseItem.query.filter_by(
                    cod_pedc=entry.cod_pedc,
                    cod_emp1=entry.cod_emp1,
                    linha=str(entry.linha) if entry.linha else None
                ).first()
                
                # Check if this purchase was linked to any NFE
                purchase_key = (po.cod_pedc, po.cod_emp1, entry.linha)
                is_linked = purchase_key in linked_purchase_keys
                
                # Find linked NFEData for this num_nf
                linked_nfe_data = None
                if entry.num_nf:
                    nfe_data = NFEData.query.filter_by(numero=entry.num_nf).first()
                    if nfe_data:
                        emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                        
                        linked_nfe_data = {
                            'id': nfe_data.id,
                            'numero': nfe_data.numero,
                            'chave': nfe_data.chave,
                            'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                            'valor_total': nfe_data.valor_total,
                            'fornecedor': emitente.nome if emitente else None,
                            'cnpj': emitente.cnpj if emitente else None,
                        }
                        # Also add to nfe_results if not already there and is_linked
                        if is_linked and not any(n['id'] == nfe_data.id for n in nfe_results):
                            nfe_results.append({
                                'id': nfe_data.id,
                                'numero': nfe_data.numero,
                                'chave': nfe_data.chave,
                                'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                                'valor_total': nfe_data.valor_total,
                                'fornecedor': emitente.nome if emitente else None,
                                'cnpj': emitente.cnpj if emitente else None,
                                'matched_items': [],
                                'linked_purchases': [{
                                    'cod_pedc': po.cod_pedc,
                                    'cod_emp1': po.cod_emp1,
                                    'fornecedor': po.fornecedor_descricao,
                                    'item_descricao': item.descricao if item else None,
                                    'linha': entry.linha,
                                }],
                            })
                
                purchase_orders.append({
                    'cod_pedc': po.cod_pedc,
                    'cod_emp1': po.cod_emp1,
                    'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                    'fornecedor': po.fornecedor_descricao,
                    'item_descricao': item.descricao if item else None,
                    'valor': item.total if item else po.total_liquido,
                    'match_type': 'linked' if is_linked else 'unlinked',
                    'nfe_numero': entry.num_nf,
                    'nfe_data': linked_nfe_data,
                })
        
        # Convert unlinked_purchases_map to list and sort by dt_emis (most recent first)
        unlinked_purchase_orders = sorted(
            unlinked_purchases_map.values(),
            key=lambda x: x.get('dt_emis') or '',
            reverse=True
        )
        
        return jsonify({
            'nfes': nfe_results,
            'purchase_orders': purchase_orders,
            'unlinked_purchase_orders': unlinked_purchase_orders,
            'query': query,
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    
    company = Company.query.get(company_id)
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
    
    company = Company.query.get(company_id)
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
    
    company = Company.query.get(company_id)
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
    
    company = Company.query.get(company_id)
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