from fuzzywuzzy import process, fuzz
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from flask_login import login_user, logout_user, login_required, current_user
from app.models import NFEntry, PurchaseOrder, PurchaseItem, Quotation, User
from app.utils import  import_rcot0300, import_rpdc0250c, import_ruah

from app import db

bp = Blueprint('api', __name__)


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
        if b'<RPDC0250_RUAH>' in file_content:
            return import_ruah(file_content)
        elif b'<RPDC0250C>' in file_content:
            return import_rpdc0250c(file_content)
        elif b'<RCOT0300>' in file_content:
            return import_rcot0300(file_content)
        else:
            return jsonify({'error': 'Invalid XML header'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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
        nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id} for nf_entry in nf_entries]
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
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id} for nf_entry in nf_entries]

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
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id} for nf_entry in nf_entries]
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
            nfes = [{'num_nf': nf_entry.num_nf, 'id': nf_entry.id} for nf_entry in nf_entries]

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

    price_history = PurchaseItem.query.filter_by(item_id=item.item_id).all()
    price_history_data = []
    for entry in price_history:
        purchase_data = PurchaseOrder.query.filter_by(cod_pedc=entry.cod_pedc).first()
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
    matches = process.extractBests(descricao, descriptions, limit=10, score_cutoff=score_cutoff)
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