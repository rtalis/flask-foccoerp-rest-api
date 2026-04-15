from datetime import datetime, timedelta
from flask import request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_

from app import db
from app.models import PurchaseOrder, PurchaseItem, Company, User, NFEntry
from app.utils import apply_adjustments
from app.routes.routes import bp


def _parse_date(date_obj):
    """Parse date object to ISO format string."""
    if date_obj is None:
        return None
    if hasattr(date_obj, 'isoformat'):
        return date_obj.isoformat()
    return str(date_obj)


# PHASE 7 ENDPOINTS

@bp.route('/purchasers', methods=['GET'])
@login_required
def get_purchasers():
    """Get list of all purchasers (func_nome) from purchase orders."""
    try:
        purchasers = db.session.query(PurchaseOrder.func_nome).distinct().all()
        purchaser_names = [purchaser[0] for purchaser in purchasers]
        return jsonify(purchaser_names), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/companies', methods=['GET'])
@login_required
def get_companies():
    """Get distinct company codes from purchase orders with names from Company table."""
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
    """Get all purchase orders with their items."""
    try:
        purchase_orders = PurchaseOrder.query.all()
        result = []
        for order in purchase_orders:
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
                'items': [
                    {
                        'item_id': item.id,
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
                        'perc_toler': item.perc_toler
                    } for item in items
                ]
            }
            result.append(order_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/get_purchase', methods=['GET'])
@login_required
def search_cod_pedc():
    """Get purchase orders by cod_pedc."""
    cod_pedc = request.args.get('cod_pedc')
    if not cod_pedc:
        return jsonify({'error': 'COD_PEDC is required'}), 400

    orders = PurchaseOrder.query.filter_by(cod_pedc=cod_pedc).all()
    result = []
    for order in orders:
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
        }
        result.append(order_data)
    return jsonify(result), 200


@bp.route('/item_details/<id>', methods=['GET'])
@login_required
def get_item_details(id):
    """Get detailed information about a purchase item including price history."""
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
        price_history_data.append({
            'date': entry.dt_emis,
            'price': entry.preco_unitario,
            'cod_pedc': entry.cod_pedc,
            'fornecedor_descricao': purchase_data.fornecedor_descricao
        })

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


@bp.route('/user_purchases', methods=['GET'])
@login_required
def get_user_purchases():
    """Get purchase orders for a specific user with fulfillment status."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status', 'all')
    username = request.args.get('username')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = (datetime.now() - timedelta(days=30)).date()
        
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    query = PurchaseOrder.query.filter(
        PurchaseOrder.dt_emis.between(start_date, end_date)
    )
    
    if user.role != 'admin' and user.system_name:
        query = query.filter(PurchaseOrder.func_nome.ilike(f'%{user.system_name}%'))
    
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
            'expanded': False,
            'items': items_data
        }
        
        result.append(order_data)
    
    return jsonify(result), 200
