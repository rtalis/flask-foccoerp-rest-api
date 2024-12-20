from flask import Blueprint, request, jsonify
from app.models import PurchaseOrder, PurchaseItem
from app.utils import parse_xml
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
        data = parse_xml(file)
        purchase_orders = data.get('purchase_orders', [])
        purchase_items = data.get('purchase_items', [])

        for order_data in purchase_orders:
            order = PurchaseOrder(**order_data)
            db.session.add(order)
            db.session.flush()  # To get the order ID for items

            for item_data in purchase_items:
                item = PurchaseItem(**item_data, order_id=order.id)
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
            items = PurchaseItem.query.filter_by(order_id=order.id).all()
            order_data = {
                'order_id': order.id,
                'order_date': order.order_date,
                'customer_name': order.customer_name,
                'items': [{'item_id': item.id, 'product_name': item.product_name, 'quantity': item.quantity, 'price': item.price} for item in items]
            }
            result.append(order_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500