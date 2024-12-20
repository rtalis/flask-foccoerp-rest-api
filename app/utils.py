def parse_xml(xml_data):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_data)
    purchase_orders = []

    for order in root.findall('.//TPED_COMPRA'):
        order_data = {
            'cod_pedc': order.find('COD_PEDC').text,
            'dt_emis': order.find('DT_EMIS').text,
            'for_cod': order.find('FOR_COD').text,
            'for_descricao': order.find('FOR_DESCRICAO').text,
            'items': []
        }

        for item in order.findall('.//TPEDC_ITEM'):
            item_data = {
                'item_id': item.find('ITEM_ID').text,
                'descricao': item.find('ITEM_DESC_TECNICA').text,
                'qtde': int(item.find('QTDE').text),
                'preco_unitario': float(item.find('PRECO_UNITARIO').text.replace(',', '.')),
                'tot_liquido': float(item.find('TOT_LIQUIDO').text.replace(',', '.'))
            }
            order_data['items'].append(item_data)

        purchase_orders.append(order_data)

    return purchase_orders


def format_for_db(purchase_orders):
    formatted_orders = []
    formatted_items = []

    for order in purchase_orders:
        formatted_orders.append({
            'cod_pedc': order['cod_pedc'],
            'dt_emis': order['dt_emis'],
            'for_cod': order['for_cod'],
            'for_descricao': order['for_descricao']
        })

        for item in order['items']:
            formatted_items.append({
                'item_id': item['item_id'],
                'descricao': item['descricao'],
                'qtde': item['qtde'],
                'preco_unitario': item['preco_unitario'],
                'tot_liquido': item['tot_liquido'],
                'cod_pedc': order['cod_pedc']  # Associando item ao pedido
            })

    return formatted_orders, formatted_items