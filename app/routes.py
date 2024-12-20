from flask import Blueprint, request, jsonify
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

        for order_data in formatted_orders:
            order = PurchaseOrder(
                cod_pedc=order_data['cod_pedc'],
                dt_emis=order_data['dt_emis'],
                fornecedor_id=order_data['fornecedor_id']
            )
            db.session.add(order)
            db.session.flush()  # To get the order ID for items

            for item_data in formatted_items:
                item = PurchaseItem(
                    purchase_order_id=order.id,
                    item_id=item_data['item_id'],
                    descricao=item_data['descricao'],
                    quantidade=item_data['quantidade'],
                    preco_unitario=item_data['preco_unitario'],
                )
                db.session.add(item)

        db.session.commit()
        return jsonify({'message': 'Data imported successfully'}), 201

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
                'items': [{'item_id': item.id, 'descricao': item.descricao, 'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario, 'total': item.total} for item in items]
            }
            result.append(order_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500