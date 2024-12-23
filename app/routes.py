from fuzzywuzzy import process
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from app.models import PurchaseOrder, PurchaseItem
from app.utils import format_for_db, parse_xml
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
                cf_pgto=order_data['cf_pgto']
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
                        qtde_saldo=item_data['qtde_saldo']
                    )
                    itemcount += 1
                    db.session.add(item)

        db.session.commit()
        return jsonify({'message': 'Data imported successfully purchases {}, items {}, updated {}'.format(purchasecount - updated, itemcount, updated)}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
        filters.append(PurchaseItem.item_id == item_id)

    if filters:
        query = query.filter(or_(*filters))
    items = query.all()
    result = []
    for item in items:
        item_data = {
            'item_id': item.id,
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
            'items': [{'item_id': item.id,
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
                       'perc_toler': item.perc_toler
                       } for item in items]
        }
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

    result = [{'item_id': item.id, 'purchase_order_id': item.purchase_order_id, 'item_id': item.item_id, 'linha': item.linha, 'cod_pedc': item.cod_pedc, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in matched_items]
    return jsonify(result), 200


@bp.route('/search_item_id', methods=['GET'])
def search_item_id():
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify({'error': 'Item ID is required'}), 400

    items = PurchaseItem.query.filter_by(item_id=item_id).all()
    result = [{'item_id': item.id, 'purchase_order_id': item.purchase_order_id, 'item_id': item.item_id, 'linha': item.linha, 'cod_pedc': item.cod_pedc, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total, 'unidade_medida': item.unidade_medida, 'dt_entrega': item.dt_entrega, 'perc_ipi': item.perc_ipi, 'tot_liquido_ipi': item.tot_liquido_ipi, 'tot_descontos': item.tot_descontos, 'tot_acrescimos': item.tot_acrescimos, 'qtde_canc': item.qtde_canc, 'qtde_canc_toler': item.qtde_canc_toler, 'perc_toler': item.perc_toler} for item in items]
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
