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


def _format_date_br(date_obj):
    if not date_obj:
        return ""
    if hasattr(date_obj, "strftime"):
        return date_obj.strftime("%d/%m/%y")
    return str(date_obj)


def _format_datetime_br(date_obj):
    if not date_obj:
        return ""
    if hasattr(date_obj, "strftime"):
        return date_obj.strftime("%d/%m/%Y %H:%M:%S")
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


@bp.route('/purchase_report_data', methods=['GET'])
@login_required
def get_purchase_report_data():
    """Return purchase order data optimized for the Oracle-like report."""
    cod_pedc = request.args.get('cod_pedc')
    cod_emp1 = request.args.get('cod_emp1')

    if not cod_pedc:
        return jsonify({'error': 'cod_pedc is required'}), 400

    order_query = PurchaseOrder.query.filter_by(cod_pedc=cod_pedc)
    if cod_emp1:
        order_query = order_query.filter_by(cod_emp1=cod_emp1)

    order = order_query.order_by(PurchaseOrder.dt_emis.desc()).first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404

    from app.models import Supplier
    company = Company.query.filter_by(cod_emp1=order.cod_emp1).first()
    supplier = None
    if order.fornecedor_id:
        supplier = Supplier.query.filter(
            (Supplier.id_for == order.fornecedor_id) |
            (Supplier.cod_for == str(order.fornecedor_id))
        ).first()
    items = (
        PurchaseItem.query.filter_by(purchase_order_id=order.id)
        .order_by(PurchaseItem.linha.asc())
        .all()
    )

    # total_descontos and total_acrescimos will be calculated with adjustments below
    total_frete = (order.vlr_frete_tra or 0) + (order.vlr_frete_red or 0)
    total_ipi = sum(((item.total or 0) * (item.perc_ipi or 0) / 100) for item in items)

    item_rows = []
    for item in items:
        item_rows.append({
            'emp': order.cod_emp1 or '',
            'linha': item.linha,
            'codigo': item.item_id,
            'descricao': item.descricao,
            'unidade_medida': item.unidade_medida,
            'quantidade': item.quantidade,
            'qtde_atendida': item.qtde_atendida,
            'qtde_canc': item.qtde_canc,
            'preco_unitario': item.preco_unitario,
            'preco_total': item.total,
            'dt_entrega': _format_date_br(item.dt_entrega),
            'perc_ipi': item.perc_ipi,
            'observacao': '',
        })

    from app.models import PurchasePaymentInstallment, PurchaseAdjustment
    installments_query = PurchasePaymentInstallment.query.filter_by(purchase_order_id=order.id).order_by(PurchasePaymentInstallment.num_dias).all()
    adjustments_query = PurchaseAdjustment.query.filter_by(purchase_order_id=order.id).all()
    
    total_descontos = sum((item.tot_descontos or 0) for item in items)
    total_acrescimos = sum((item.tot_acrescimos or 0) for item in items)
    base_value = sum((item.total or 0) for item in items)

    for adj in adjustments_query:
        amount = 0
        if adj.tp_vlr1 == 'Percentual':
            amount = base_value * ((adj.vlr1 or 0) / 100)
        elif adj.tp_vlr1 == 'Valor':
            amount = adj.vlr1 or 0
            
        if adj.tp_dctacr1 == 'Desconto':
            total_descontos += amount
        elif adj.tp_dctacr1 == 'Acréscimo':
            total_acrescimos += amount
    
    vencimentos_list = []
    for inst in installments_query:
        vencimentos_list.append({
            'dias': inst.num_dias,
            'vencimento': _format_date_br(inst.dt_vcto) if inst.dt_vcto else '',
            'tipo_desconto': '',
            'tipo_valor': '',
            'aplicado': '',
            'valor': ''
        })
    for adj in adjustments_query:
        vencimentos_list.append({
            'dias': '',
            'vencimento': '',
            'tipo_desconto': adj.tp_dctacr1 or '',
            'tipo_valor': adj.tp_vlr1 or '',
            'aplicado': adj.tp_apl or '',
            'valor': adj.vlr1 or 0
        })

    payload = {
        'report': {
            'name': 'RPDC0250_RUAH',
            'generated_at': _format_datetime_br(datetime.now()),
            'page': '001',
            'pages': '001',
        },
        'company': {
            'name': company.name if company else '',
            'cnpj': company.cnpj if company else '',
            'inscricao_estadual': company.inscricao_estadual if company else '',
            'address': company.address if company else '',
            'city': company.city if company else '',
            'state': company.state if company else '',
            'zip_code': company.zip_code if company else '',
            'phone': company.phone if company else '',
            'email': company.email if company else '',
            'cod_emp1': order.cod_emp1,
        },
        'order': {
            'cod_pedc': order.cod_pedc,
            'dt_emis': _format_date_br(order.dt_emis),
            'moeda': order.moeped or 'REAL',
            'fornecedor_id': order.fornecedor_id,
            'fornecedor_descricao': order.fornecedor_descricao,
            'fornecedor_cnpj': supplier.nvl_forn_cnpj_forn_cpf if supplier else '',
            'fornecedor_uf': order.for_uf or '',
            'transportadora': f"{order.tra_cod}  {order.tra_descricao}".strip() if order.tra_cod else (order.tra_descricao or ''),
            'transportadora_uf': order.tra_uf or '',
            'tipo_frete': order.tp_frete_tra or '',
            'tipo_valor': order.tp_vlr_frete_tra or '',
            'valor_frete': order.vlr_frete_tra or total_frete,
            'redespacho': f"{order.red_cod}  {order.red_descricao2}".strip() if order.red_cod else (order.red_descricao2 or ''),
            'tipo_frete_2': order.tp_frete_red or '',
            'tipo_valor_2': order.tp_vlr_frete_red or '',
            'valor_frete_2': order.vlr_frete_red or '',
            'comprador': order.func_nome,
            'contato': order.contato,
            'talao': order.num_talao or '',
            'observacao': order.observacao,
            'cf_pgto': order.cf_pgto,
            'total_bruto': order.total_bruto,
            'total_liquido': order.total_liquido,
            'total_final': (order.total_pedido_com_ipi or order.total_liquido_ipi or order.total_liquido or 0) + (order.vlr_frete_tra or 0),
            'total_ipi': total_ipi,
            'total_descontos': total_descontos,
            'total_acrescimos': total_acrescimos,
            'total_icms_st': order.vlr_icms_st or 0,
            'total_frete': total_frete,
            'items': item_rows,
            'vencimentos': vencimentos_list,
        },
        'observacoes': [
            f"E mail para XML: {(company.email if company else '') or ''}",
            'Na observacao da NFE deve constar o numero do pedido de compra.',
            'A NFE deve ser o espelho do pedido(Constar nosso codigo e descricao dos itens)',
            'A cobranca bancaria deve acompanhar a NFE.',
            'O pedido só deve ser faturado no dia da coleta/embarque do material, caso ocorra diferença a mesma deve ser considerada nos vencimentos dos títulos, realizando a postergação do mesmo.',
            'A Data de Entrega indica quando o material deve ser entregue na Ruah, desconsiderando sua Logística, favor contatar o transportador/setor de compras Ruah para que a mesma esteja disponível conforme programado.',
            'O não cumprimento da Data de Entrega pode incidir em penalização do Fornecedor em caso de parada de produção, repassando o custo da mesma.'
        ],
    }

    return jsonify(payload), 200


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
