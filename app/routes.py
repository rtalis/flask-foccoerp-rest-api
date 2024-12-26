from fuzzywuzzy import process
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from app.models import NFEntry, PurchaseOrder, PurchaseItem
from app.utils import format_for_db, format_for_db_rpdc0250c, parse_xml
from app import db

bp = Blueprint('api', __name__)

@bp.route('/import', methods=['POST'])
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
        else:
            return jsonify({'error': 'Invalid XML header'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def import_ruah(file_content):
    data = parse_xml(file_content)  # Passe o conteúdo do arquivo para a função parse_xml
    formatted_orders, formatted_items = format_for_db(data)  # Formate os dados para o banco de dados
    itemcount = 0
    purchasecount = 0
    updated = 0

    for order_data in formatted_orders:
        existing_order = PurchaseOrder.query.filter_by(cod_pedc=order_data['cod_pedc']).first()
        if existing_order:
            PurchaseItem.query.filter_by(purchase_order_id=existing_order.id).delete()
            db.session.delete(existing_order)
            db.session.commit()
            updated += 1

        # Adicione o novo pedido de compra
        order = PurchaseOrder(
            cod_pedc=order_data['cod_pedc'],
            dt_emis=order_data['dt_emis'],
            fornecedor_id=order_data['fornecedor_id'],
            fornecedor_descricao=order_data['fornecedor_descricao'],
            total_bruto=order_data['total_bruto'],
            total_liquido=order_data['total_liquido'],
            total_liquido_ipi=order_data['total_liquido_ipi'],
            posicao=order_data['posicao'],
            posicao_hist=order_data['posicao_hist'],
            observacao=order_data['observacao'],
            contato=order_data['contato'],
            func_nome=order_data['func_nome'],
            cf_pgto=order_data['cf_pgto'],
            cod_emp1=order_data['cod_emp1']
        )
        purchasecount += 1
        db.session.add(order)
        db.session.flush()  # To get the order ID for items

        for item_data in formatted_items:
            if item_data['purchase_order_id'] == order_data['cod_pedc']:
                item = PurchaseItem(
                    purchase_order_id=order.id,
                    item_id=item_data['item_id'],
                    linha=item_data['linha'],
                    cod_pedc=item_data['cod_pedc'],
                    descricao=item_data['descricao'],
                    quantidade=item_data['quantidade'],
                    preco_unitario=item_data['preco_unitario'],
                    total=item_data['total'],
                    unidade_medida=item_data['unidade_medida'],
                    dt_entrega=item_data['dt_entrega'],
                    perc_ipi=item_data['perc_ipi'],
                    tot_liquido_ipi=item_data['tot_liquido_ipi'],
                    tot_descontos=item_data['tot_descontos'],
                    tot_acrescimos=item_data['tot_acrescimos'],
                    qtde_canc=item_data['qtde_canc'],
                    qtde_canc_toler=item_data['qtde_canc_toler'],
                    perc_toler=item_data['perc_toler'],
                    qtde_atendida=item_data['qtde_atendida'],
                    qtde_saldo=item_data['qtde_saldo'],
                    cod_emp1=item_data['cod_emp1']
                )
                itemcount += 1
                db.session.add(item)

    db.session.commit()
    return jsonify({'message': 'Data imported successfully purchases {}, items {}, updated {}'.format(purchasecount - updated, itemcount, updated)}), 201

def import_rpdc0250c(file_content):
    formatted_items = format_for_db_rpdc0250c(file_content) 
    itemcount = 0
    updated = 0

    for item_data in formatted_items:
        if item_data:
            existing_entry = NFEntry.query.filter_by(
                cod_emp1=item_data['cod_emp1'],
                cod_pedc=item_data['cod_pedc'],
                linha=item_data['linha']
            ).first()

            if existing_entry:
                db.session.delete(existing_entry)
                db.session.commit()
                updated += 1

            nf_entry = NFEntry(
                cod_emp1=item_data['cod_emp1'],
                cod_pedc=item_data['cod_pedc'],
                linha=item_data['linha'],
                num_nf=item_data['num_nf'],
                text_field=item_data.get('text_field', ''),
            )
            itemcount += 1
            db.session.add(nf_entry)

    db.session.commit()
    return jsonify({'message': 'Data imported successfully items {}, updated {}'.format(itemcount, updated)}), 201


@bp.route('/purchases', methods=['GET'])
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
    items = query.all()
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

    orders = query.all()
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



@bp.route('/search_item_fuzzy', methods=['GET'])
def search_item_fuzzy():
    descricao = request.args.get('descricao')
    if not descricao:
        return jsonify({'error': 'Descricao is required'}), 400

    score_cutoff = int(request.args.get('score_cutoff', 80))  # Padrão para 80% de similaridade
    all_items = PurchaseItem.query.all()
    descriptions = [item.descricao for item in all_items]
    matches = process.extractBests(descricao, descriptions, limit=10, score_cutoff=score_cutoff)
    matched_items = [item for item in all_items if item.descricao in [match[0] for match in matches]]

    result = [{'id':item.id, 'purchase_order_id': item.purchase_order_id, 'item_id': item.item_id, 'linha': item.linha, 'cod_pedc': item.cod_pedc, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in matched_items]
    return jsonify(result), 200


@bp.route('/search_item_id', methods=['GET'])
def search_item_id():
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'error': 'Item ID is required'}), 400

    items = PurchaseItem.query.filter_by(item_id=item_id).all()
    result = [{'id': item.id, 'purchase_order_id': item.purchase_order_id, 'item_id': item.item_id, 'linha': item.linha, 'cod_pedc': item.cod_pedc, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in items]
    return jsonify(result), 200

@bp.route('/get_purchase', methods=['GET'])
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
def search_fuzzy():
    query = request.args.get('query')
    cod_pedc = request.args.get('cod_pedc')
    fornecedor_descricao = request.args.get('fornecedor_descricao')
    observacao = request.args.get('observacao')
    descricao = request.args.get('descricao')
    item_id = request.args.get('item_id')
    score_cutoff = int(request.args.get('score_cutoff', 80))

    if not query or not score_cutoff:
        return jsonify({'error': 'Query required'}), 400

    all_items = PurchaseItem.query.all()
    all_orders = PurchaseOrder.query.all()
   
    item_descriptions = [item.descricao for item in all_items]
    order_observations = [order.observacao for order in all_orders]

    item_matches = process.extractBests(query, item_descriptions, score_cutoff=score_cutoff)
    order_matches = process.extractBests(query, order_observations, score_cutoff=score_cutoff)

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