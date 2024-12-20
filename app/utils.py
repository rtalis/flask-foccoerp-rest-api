def parse_xml(xml_data):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_data)
    purchase_orders = []

    for order in root.findall('.//TPED_COMPRA'):
        cod_pedc = order.find('COD_PEDC').text if order.find('COD_PEDC') is not None else None,
        order_data = {
            'cod_pedc': cod_pedc,
            'dt_emis': order.find('DT_EMIS').text if order.find('DT_EMIS') is not None else None,
            'fornecedor_id': int(order.find('FOR_COD').text) if order.find('FOR_COD') is not None else None,
            'items': []
        }

        for item in order.findall('.//TPEDC_ITEM'):
            item_data = {
                'cod_pedc': cod_pedc,
                'linha': int(item.find('LINHA1').text) if item.find('LINHA1') is not None else None,
                'item_id': int(item.find('ITEM_ID').text) if item.find('ITEM_ID') is not None else None,
                'descricao': item.find('ITEM_DESC_TECNICA').text if item.find('ITEM_DESC_TECNICA') is not None else None,
                'quantidade': float(item.find('QTDE').text.replace(',', '.')) if item.find('QTDE') is not None else None,
                'preco_unitario': float(item.find('PRECO_UNITARIO').text.replace(',', '.')) if item.find('PRECO_UNITARIO') is not None else None,
                'total': float(item.find('TOT_BRUTO').text.replace(',', '.')) if item.find('TOT_BRUTO') is not None else None,
            }
            order_data['items'].append(item_data)

        purchase_orders.append(order_data)

    return {'purchase_orders': purchase_orders}

def format_for_db(purchase_orders):
    formatted_orders = []
    formatted_items = []

    for order in purchase_orders['purchase_orders']:
        formatted_orders.append({
            'cod_pedc': order['cod_pedc'],
            'dt_emis': order['dt_emis'],
            'fornecedor_id': order['fornecedor_id']
        })

        for item in order['items']:
            formatted_items.append({
                'item_id': item['item_id'],
                'descricao': item['descricao'],
                'quantidade': item['quantidade'],
                'preco_unitario': item['preco_unitario'],
                'total': item['total'],
            })

    return formatted_orders, formatted_items