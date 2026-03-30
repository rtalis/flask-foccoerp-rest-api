"""
Phase 2: Search Endpoints
Contains 9 search-related endpoints for items, purchases, and NFE queries.
"""

import re
from datetime import datetime
from fuzzywuzzy import process, fuzz
from flask import request, jsonify
from sqlalchemy import and_, or_, func, cast, tuple_
from sqlalchemy.sql import exists
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user

from app import db
from app.models import PurchaseOrder, PurchaseItem, NFEntry, PurchaseItemNFEMatch, Supplier
from app.utils import fuzzy_search, apply_adjustments
from app.routes.routes import bp


def _parse_date(date_obj):
    """Parse date object to ISO format string."""
    if date_obj is None:
        return None
    if hasattr(date_obj, 'isoformat'):
        return date_obj.isoformat()
    return str(date_obj)


def apply_user_scopes(query, model):
    """
    Applies data filtering constraints onto an active SQLAlchemy query based on the user's data_filters.
    Expected data_filters schema: {"observacao_contains": ["keyword1"], "department_equals": ["TI"]} 
    """
    if getattr(current_user, 'role', 'viewer') == 'admin':
        return query
    
    filters_config = getattr(current_user, 'data_filters', {}) or {}
    
    if "observacao_contains" in filters_config:
        keywords = filters_config["observacao_contains"]
        if keywords and hasattr(model, 'observacao'):
            if db.engine.name == 'postgresql':
                filter_clauses = [
                    func.unaccent(model.observacao).ilike(func.unaccent(func.cast(f"%{kw}%", db.String))) 
                    for kw in keywords
                ]
            else:
                filter_clauses = [model.observacao.ilike(f"%{kw}%") for kw in keywords]
            query = query.filter(or_(*filter_clauses))
            
    return query


def _build_purchase_payload(items):
    """Group purchase items by order and prepare API payload."""
    from app.routes.routes import bp  # noqa: E402
    
    grouped_results = {}
    order_keys = set()
    item_ids = set()

    for item in items:
        order = item.purchase_order
        if not order:
            continue
        order_keys.add((order.cod_emp1, item.cod_pedc))
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

    estimated_nfe_by_item = {}
    if item_ids:
        estimated_matches = (
            PurchaseItemNFEMatch.query
            .filter(PurchaseItemNFEMatch.purchase_item_id.in_(list(item_ids)))
            .order_by(PurchaseItemNFEMatch.match_score.desc())
            .all()
        )
        for match in estimated_matches:
            if match.purchase_item_id not in estimated_nfe_by_item:
                estimated_nfe_by_item[match.purchase_item_id] = {
                    'nfe_numero': match.nfe_numero,
                    'match_score': match.match_score,
                    'nfe_fornecedor': match.nfe_fornecedor,
                    'nfe_chave': match.nfe_chave,
                    'nfe_data_emissao': match.nfe_data_emissao.isoformat() if match.nfe_data_emissao else None
                }

    user_caps = getattr(current_user, 'capabilities', []) or []
    can_view_financials = 'view_financials' in user_caps or current_user.role == 'admin'
    can_view_nfes = 'view_nfes' in user_caps or current_user.role == 'admin'

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
                    'dt_emis': _parse_date(order.dt_emis),
                    'fornecedor_id': order.fornecedor_id,
                    'fornecedor_descricao': order.fornecedor_descricao,
                    'total_bruto': order.total_bruto if can_view_financials else None,
                    'total_pedido_com_ipi': order.total_pedido_com_ipi if can_view_financials else None,
                    'adjusted_total': adjusted_total if can_view_financials else None,
                    'adjustments': [
                        {
                            'tp_apl': adj.tp_apl,
                            'tp_dctacr1': adj.tp_dctacr1,
                            'tp_vlr1': adj.tp_vlr1,
                            'vlr1': adj.vlr1 if can_view_financials else None,
                            'order_index': adj.order_index
                        }
                        for adj in adjustments
                    ] if can_view_financials else [],
                    'total_liquido': order.total_liquido if can_view_financials else None,
                    'total_liquido_ipi': order.total_liquido_ipi if can_view_financials else None,
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
                            'num_nf': nf_entry.num_nf if can_view_nfes else None,
                            'id': nf_entry.id if can_view_nfes else None,
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
            'preco_unitario': item.preco_unitario if can_view_financials else None,
            'total': item.total if can_view_financials else None,
            'unidade_medida': item.unidade_medida,
            'linha': item.linha,
            'dt_entrega': item.dt_entrega,
            'perc_ipi': item.perc_ipi,
            'tot_liquido_ipi': item.tot_liquido_ipi if can_view_financials else None,
            'tot_descontos': item.tot_descontos if can_view_financials else None,
            'tot_acrescimos': item.tot_acrescimos if can_view_financials else None,
            'qtde_canc': item.qtde_canc,
            'qtde_canc_toler': item.qtde_canc_toler,
            'perc_toler': item.perc_toler,
            'qtde_atendida': item.qtde_atendida,
            'qtde_saldo': item.qtde_saldo,
            'estimated_nfe': estimated_nfe_by_item.get(item.id) if can_view_nfes else None,
        })

    return list(grouped_results.values())


# PHASE 2 ENDPOINTS

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
        order = db.session.get(PurchaseOrder, item.purchase_order_id)
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
        result.append(item_data)
    return jsonify(result), 200


@bp.route('/search_purchases', methods=['GET'])
@login_required
def search_purchases():
    cod_pedc = request.args.get('cod_pedc')
    fornecedor_descricao = request.args.get('fornecedor_descricao')
    observacao = request.args.get('observacao')

    query = PurchaseOrder.query
    query = apply_user_scopes(query, PurchaseOrder)
    
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
        orders = query.order_by(PurchaseOrder.dt_emis.desc()).limit(200).all()

    
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
    order_matches = process.extractBests(str(query), order_observations.keys(), score_cutoff=score_cutoff, scorer=fuzz.partial_ratio)
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
            order = db.session.get(PurchaseOrder, item.purchase_order_id)
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


@bp.route('/search_item_fuzzy', methods=['GET'])
@login_required
def search_item_fuzzy():
    descricao = request.args.get('descricao')
    score_cutoff = int(request.args.get('score_cutoff', 80))
    if not descricao:
        return jsonify({'error': 'Descricao is required'}), 400

    all_items = PurchaseItem.query.all()
    descriptions = [item.descricao for item in all_items]
    matches = process.extractBests(descricao, descriptions, limit=10, score_cutoff=score_cutoff)
    matched_items = [item for item in all_items if item.descricao in [match[0] for match in matches]]

    if not matched_items:
        return jsonify({'error': 'No items found with the given description'}), 404

    item = matched_items[0]
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


@bp.route('/search_advanced', methods=['GET'])
@login_required
def search_advanced():
    """Advanced search with multiple filters, fuzzy matching, and pagination."""
    
    if request.args.get('legacy', 'false').lower() == 'true':
        # Fallback to legacy combined search
        from app.routes.search import search_combined  # noqa: E402
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
    date_from_param = request.args.get('date_from', '').strip()
    date_to_param = request.args.get('date_to', '').strip()
    
    date_from = None
    date_to = None
    try:
        if date_from_param:
            date_from = datetime.strptime(date_from_param, '%Y-%m-%d')
        if date_to_param:
            date_to = datetime.strptime(date_to_param, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        date_from = None
        date_to = None

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
    include_cnpj_fornecedor = 'cnpj_fornecedor' in fields
    search_columns = [column_map[key] for key in fields if key in column_map]
    if not search_columns and not include_nf:
        search_columns = [PurchaseItem.descricao]

    remove_accents = None
    if ignore_diacritics and db.engine.name == 'postgresql':
        db.session.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
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

    def normalize_cnpj_string(cnpj: str) -> str:
        """Normalize CNPJ/CPF string by removing non-digits."""
        return re.sub(r'[^0-9]', '', cnpj)
    
    def is_valid_cnpj_search(token: str) -> bool:
        """Check if token is a valid CNPJ or CPF for searching."""
        cleaned = normalize_cnpj_string(token)
        return len(cleaned) in (11, 14)

    def is_valid_search_pattern(token: str) -> bool:
        """Check if a search pattern is valid for text search."""
        if re.match(r'^[\*\./\-\s]+$', token):
            return False
        return True

    valid_tokens = [token for token in tokens if is_valid_search_pattern(token)]
    valid_cnpj_tokens = [token for token in tokens if include_cnpj_fornecedor and is_valid_cnpj_search(token)]
    
    if normalized_query and not valid_tokens and not valid_cnpj_tokens:
        return jsonify({
            'purchases': [],
            'total_pages': 0,
            'current_page': 1,
            'total_results': 0
        }), 200

    base_query = (
        PurchaseItem.query
        .join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
        .options(joinedload(PurchaseItem.purchase_order).joinedload(PurchaseOrder.adjustments))
    )

    base_query = apply_user_scopes(base_query, PurchaseOrder)

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

    if date_from is not None:
        base_query = base_query.filter(PurchaseOrder.dt_emis >= date_from)
    if date_to is not None:
        base_query = base_query.filter(PurchaseOrder.dt_emis <= date_to)

    if search_by_func_nome and search_by_func_nome.lower() != 'todos':
        base_query = base_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))

    if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
        base_query = base_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))

    if hide_cancelled:
        base_query = base_query.filter(PurchaseItem.quantidade > PurchaseItem.qtde_canc)
    
    token_filters = []
    
    for token in valid_tokens:
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

            nfe_match_clause = exists().where(and_(
                PurchaseItemNFEMatch.cod_emp1 == PurchaseItem.cod_emp1,
                PurchaseItemNFEMatch.cod_pedc == PurchaseItem.cod_pedc,
                apply_ilike(PurchaseItemNFEMatch.nfe_numero, pattern)
            ))
            term_clauses.append(nfe_match_clause)

        if include_cnpj_fornecedor and token in valid_cnpj_tokens:
            normalized_cnpj = normalize_cnpj_string(token)
            
            cnpj_clause = db.session.query(Supplier).filter(
                and_(
                    or_(
                        Supplier.id_for == PurchaseOrder.fornecedor_id,
                        Supplier.cod_for == cast(PurchaseOrder.fornecedor_id, db.String),
                        func.ltrim(Supplier.cod_for, '0') == func.ltrim(cast(PurchaseOrder.fornecedor_id, db.String), '0')
                    ),
                    Supplier.cnpj_cpf_normalized == normalized_cnpj
                )
            ).exists()
            term_clauses.append(cnpj_clause)

        if term_clauses:
            token_filters.append(or_(*term_clauses))

    if token_filters:
        base_query = base_query.filter(and_(*token_filters))

    if score_cutoff < 100 and valid_tokens:
        items = base_query.order_by(PurchaseOrder.dt_emis.desc(), PurchaseItem.id.desc()).all()
        items = fuzzy_search(' '.join(valid_tokens), items, score_cutoff, 'descricao' in fields, 'observacao' in fields)
        purchases_payload = _build_purchase_payload(items)
        return jsonify({
            'purchases': purchases_payload,
            'total_pages': 1,
            'current_page': 1,
            'total_results': len(items)
        }), 200

    order_ids_subquery = (
        base_query
        .with_entities(PurchaseItem.purchase_order_id)
        .distinct()
        .subquery()
    )

    orders_paginated = (
        PurchaseOrder.query
        .filter(PurchaseOrder.id.in_(
            db.session.query(order_ids_subquery.c.purchase_order_id)
        ))
        .order_by(PurchaseOrder.dt_emis.desc(), PurchaseOrder.id.desc())
        .paginate(page=page, per_page=per_page, count=True)
    )

    paginated_order_ids = [o.id for o in orders_paginated.items]

    items = (
        base_query
        .filter(PurchaseItem.purchase_order_id.in_(paginated_order_ids))
        .order_by(PurchaseOrder.dt_emis.desc(), PurchaseItem.id.desc())
        .all()
    )

    purchases_payload = _build_purchase_payload(items)

    return jsonify({
        'purchases': purchases_payload,
        'total_pages': orders_paginated.pages,
        'current_page': orders_paginated.page,
        'total_results': orders_paginated.total
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
    """Legacy combined search endpoint with backward compatibility."""
    
    query = request.args.get('query', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    score_cutoff = int(request.args.get('score_cutoff', 80))
    search_by_cod_pedc = request.args.get('searchByCodPedc', 'false').lower() == 'true'
    search_by_fornecedor = request.args.get('searchByFornecedor', 'false').lower() == 'true'
    search_by_cnpj_fornecedor = request.args.get('searchByCnpjFornecedor', 'false').lower() == 'true'
    search_by_observacao = request.args.get('searchByObservacao', 'false').lower() == 'true'
    search_by_item_id = request.args.get('searchByItemId', 'false').lower() == 'true'
    search_by_descricao = request.args.get('searchByDescricao', 'false').lower() == 'true'
    search_by_num_nf = request.args.get('searchByNumNF', 'false').lower() == 'true' 
    search_by_func_nome = request.args.get('selectedFuncName')
    search_by_cod_emp1 = request.args.get('selectedCodEmp1', 'todos')
    min_value = request.args.get('minValue', type=float)
    max_value = request.args.get('maxValue', type=float)
    value_search_type = request.args.get('valueSearchType', 'item')
    ignore_diacritics = request.args.get('ignoreDiacritics', 'false').lower() == 'true'
    date_from_param = request.args.get('date_from', '').strip()
    date_to_param = request.args.get('date_to', '').strip()
    
    date_from = None
    date_to = None
    try:
        if date_from_param:
            date_from = datetime.strptime(date_from_param, '%Y-%m-%d')
        if date_to_param:
            date_to = datetime.strptime(date_to_param, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        date_from = None
        date_to = None

    value_filters = []
    if min_value is not None or max_value is not None:        
        if value_search_type == 'item':
            if min_value is not None:
                value_filters.append(PurchaseItem.preco_unitario >= min_value)
            if max_value is not None:
                value_filters.append(PurchaseItem.preco_unitario <= max_value)
        else:
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
        if search_by_cnpj_fornecedor:
            cnpj_pattern = re.sub(r'[^0-9*]', '', query)
            if cnpj_pattern:
                cnpj_pattern = cnpj_pattern.replace('*', '%')
                if '%' not in cnpj_pattern:
                    cnpj_pattern = f'%{cnpj_pattern}%'
                normalized_supplier_cnpj = func.coalesce(cast(Supplier.nvl_forn_cnpj_forn_cpf, db.String), '')
                for char in ('.', '/', '-', ' '):
                    normalized_supplier_cnpj = func.replace(normalized_supplier_cnpj, char, '')
                filters.append(exists().where(and_(
                    or_(
                        Supplier.id_for == PurchaseOrder.fornecedor_id,
                        Supplier.cod_for == cast(PurchaseOrder.fornecedor_id, db.String),
                        func.ltrim(Supplier.cod_for, '0') == func.ltrim(cast(PurchaseOrder.fornecedor_id, db.String), '0')
                    ),
                    normalized_supplier_cnpj.ilike(cnpj_pattern)
                )))
        if search_by_observacao:
            filters.append(PurchaseOrder.observacao.ilike(f'%{query}%'))
        if search_by_item_id:
            filters.append(PurchaseItem.item_id.ilike(f'%{query}%'))
        if search_by_descricao:
            filters.append(PurchaseItem.descricao.ilike(f'%{query}%'))
        if search_by_num_nf:
            nf_filters = []

            nf_entries = NFEntry.query.filter(NFEntry.num_nf.ilike(f'%{query}%')).all()
            if nf_entries:
                for nf in nf_entries:
                    nf_filters.append(and_(
                        PurchaseItem.cod_pedc == nf.cod_pedc,
                        PurchaseItem.cod_emp1 == nf.cod_emp1
                    ))

            nfe_matches = PurchaseItemNFEMatch.query.filter(
                PurchaseItemNFEMatch.nfe_numero.ilike(f'%{query}%')
            ).all()
            if nfe_matches:
                for match in nfe_matches:
                    nf_filters.append(and_(
                        PurchaseItem.cod_pedc == match.cod_pedc,
                        PurchaseItem.cod_emp1 == match.cod_emp1
                    ))

            if nf_filters:
                filters.append(or_(*nf_filters))

        if not any([search_by_cod_pedc, search_by_fornecedor, search_by_cnpj_fornecedor, search_by_observacao, search_by_item_id, search_by_descricao, search_by_num_nf]):
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
    if search_by_func_nome and search_by_func_nome != 'todos':
        items_query = items_query.filter(and_(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%')))
    if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
        items_query = items_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))
    if date_from is not None:
        items_query = items_query.filter(PurchaseOrder.dt_emis >= date_from)
    if date_to is not None:
        items_query = items_query.filter(PurchaseOrder.dt_emis <= date_to)
    
    if score_cutoff < 100 and query:
        fuzzy_query = (
            PurchaseItem.query
            .order_by(PurchaseOrder.dt_emis.desc())
            .join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)
            .options(joinedload(PurchaseItem.purchase_order).joinedload(PurchaseOrder.adjustments))
        )
        if search_by_func_nome != 'todos':
            fuzzy_query = fuzzy_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))
        if search_by_cod_emp1 and str(search_by_cod_emp1).lower() != 'todos':
            fuzzy_query = fuzzy_query.filter(PurchaseOrder.cod_emp1 == str(search_by_cod_emp1))
        if value_filters:
            fuzzy_query = fuzzy_query.filter(and_(*value_filters))
        items = fuzzy_query.all()
        items = fuzzy_search(query, items, score_cutoff, search_by_descricao, search_by_observacao)
        items_paginated = None
    else:
        items_paginated = items_query.paginate(page=page, per_page=per_page, count=True)
        items = items_paginated.items

    purchases_payload = _build_purchase_payload(items)

    if score_cutoff < 100 and query:
        total_pages = 1
        current_page = 1
        total_results = len(items)
    else:
        total_pages = items_paginated.pages
        current_page = items_paginated.page
        total_results = items_paginated.total

    return jsonify({
        'purchases': purchases_payload,
        'total_pages': total_pages,
        'current_page': current_page,
        'total_results': total_results
    }), 200
