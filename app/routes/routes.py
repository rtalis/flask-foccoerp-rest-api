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
from app.models import LoginHistory, NFEData, NFEDestinatario, NFEntry, PurchaseOrder, PurchaseItem, PurchaseItemNFEMatch, Quotation, RequestLog, Supplier, User
from app.routes.auth import token_required
from app.utils import  apply_adjustments, check_order_fulfillment, fuzzy_search, import_rcot0300, import_rfor0302, import_rpdc0250c, import_ruah,_parse_date
from app import db
import tempfile
import os
import shutil
from config import Config


bp = Blueprint('api', __name__)

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xml'}

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
            from sqlalchemy import func
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
                    'dt_emis':  _parse_date(order.dt_emis),
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
    search_by_cnpj_fornecedor = request.args.get('searchByCnpjFornecedor', 'false').lower() == 'true'
    search_by_observacao = request.args.get('searchByObservacao', 'false').lower() == 'true'
    search_by_item_id = request.args.get('searchByItemId', 'false').lower() == 'true'
    search_by_descricao = request.args.get('searchByDescricao', 'false').lower() == 'true'
    search_by_num_nf = request.args.get('searchByNumNF', 'false').lower() == 'true'  # Add this line


    count_query = db.session.query(db.func.count(db.distinct(PurchaseItem.cod_pedc))).\
        join(PurchaseOrder, PurchaseItem.purchase_order_id == PurchaseOrder.id)

    if search_by_func_nome != 'todos':
        count_query = count_query.filter(PurchaseOrder.func_nome.ilike(f'%{search_by_func_nome}%'))

    date_from_param = request.args.get('date_from', '').strip()
    date_to_param = request.args.get('date_to', '').strip()
    try:
        if date_from_param:
            date_from = datetime.strptime(date_from_param, '%Y-%m-%d')
            count_query = count_query.filter(PurchaseOrder.dt_emis >= date_from)
        if date_to_param:
            date_to = datetime.strptime(date_to_param, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            count_query = count_query.filter(PurchaseOrder.dt_emis <= date_to)
    except ValueError:
        # ignore invalid date formats
        pass

    base_count = count_query.scalar()

    multiplier = sum([
        search_by_cod_pedc,
        search_by_fornecedor,
        search_by_cnpj_fornecedor,
        search_by_observacao,
        search_by_item_id,
        search_by_descricao,
        search_by_num_nf
    ])
    
    if multiplier == 0:
        multiplier = 7

    estimated_count = base_count * multiplier

    return jsonify({
        'count': estimated_count,
        'estimated_pages': (estimated_count + 199) // 200  # 200 itens por página
    }), 200
    
    
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_xml(content):
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(content)
        return True
    except ET.ParseError:
        return False

def extract_xml_value(root, xpath):
    try:
        element = root.find(xpath)
        return element.text if element is not None else ''
    except:
        return ''
    
    
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

        # Daily usage - use the same date range as the dashboard request
        usage_start_date = start_date
        usage_end_date = end_date
        # Calculate number of days for the iteration loop
        usage_days = max((usage_end_date - usage_start_date).days + 1, 1)

        usage_rows = db.session.query(
            func.date(LoginHistory.login_time).label('login_date'),
            func.count(LoginHistory.id).label('login_count'),
            func.count(func.distinct(LoginHistory.user_id)).label('user_count')
        ).filter(
            func.date(LoginHistory.login_time) >= usage_start_date,
            func.date(LoginHistory.login_time) <= usage_end_date
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


from app.routes import analytics  
from app.routes import search  
from app.routes import nfe 
from app.routes import imports 
from app.routes import quotations  
from app.routes import tracking 
from app.routes import purchases