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
            'fornecedor_descricao': order.find('FOR_DESCRICAO').text if order.find('FOR_DESCRICAO') is not None else None,
            'total_bruto': float(order.find('TOT_BRUTO1').text.replace(',', '.')) if order.find('TOT_BRUTO1') is not None and order.find('TOT_BRUTO1').text else None,
            'total_liquido': float(order.find('TOT_LIQUIDO1').text.replace(',', '.')) if order.find('TOT_LIQUIDO1') is not None and order.find('TOT_LIQUIDO1').text else None,
            'total_liquido_ipi': float(order.find('CP_TOT_IPI').text.replace(',', '.')) if order.find('CP_TOT_IPI') is not None and order.find('TOT_LIQUIDO_IPI1').text else None,
            'posicao': order.find('POSICAO1').text if order.find('POSICAO1') is not None else None,
            'posicao_hist': order.find('POSICAO_HIST1').text if order.find('POSICAO_HIST1') is not None else None,
            'observacao': order.find('OBSERVACAO').text if order.find('OBSERVACAO') is not None else None,
            'contato': order.find('CONTATO').text if order.find('CONTATO') is not None else None,
            'func_nome': order.find('FUNC_NOME').text if order.find('FUNC_NOME') is not None else None,
            'cf_pgto': order.find('CF_PGTO').text if order.find('CF_PGTO') is not None else None,



            'items': []
        }

        for item in order.findall('.//TPEDC_ITEM'):
         
            item_data = {
                'item_id': int(item.find('ITEM_ID').text) if item.find('ITEM_ID') is not None else None,
                'cod_pedc': cod_pedc,
                'linha': item.find('LINHA1').text if item.find('LINHA1') is not None else None,
                'descricao': item.find('ITEM_DESC_TECNICA').text if item.find('ITEM_DESC_TECNICA') is not None else None,
                'quantidade': float(item.find('QTDE').text.replace(',', '.')) if item.find('QTDE') is not None and item.find('QTDE').text else None,
                'preco_unitario': float(item.find('PRECO_UNITARIO').text.replace(',', '.')) if item.find('PRECO_UNITARIO') is not None and item.find('PRECO_UNITARIO').text else None,
                'total': float(item.find('TOT_BRUTO').text.replace(',', '.')) if item.find('TOT_BRUTO') is not None and item.find('TOT_BRUTO').text else None,
                'unidade_medida': item.find('UNID_MED').text if item.find('UNID_MED') is not None else None,
                'dt_entrega': item.find('DT_ENTREGA').text if item.find('DT_ENTREGA') is not None else None,
                'perc_ipi': float(item.find('PERC_IPI').text.replace(',', '.')) if item.find('PERC_IPI') is not None and item.find('PERC_IPI').text else None,
                'tot_liquido_ipi': float(item.find('TOT_LIQUIDO_IPI').text.replace(',', '.')) if item.find('TOT_LIQUIDO_IPI') is not None and item.find('TOT_LIQUIDO_IPI').text else None,
                'tot_descontos': float(item.find('TOT_DESCONTOS').text.replace(',', '.')) if item.find('TOT_DESCONTOS') is not None and item.find('TOT_DESCONTOS').text else None,
                'tot_acrescimos': float(item.find('TOT_ACRESCIMOS').text.replace(',', '.')) if item.find('TOT_ACRESCIMOS') is not None and item.find('TOT_ACRESCIMOS').text else None,
                'qtde_canc': float(item.find('QTDE_CANC').text.replace(',', '.')) if item.find('QTDE_CANC') is not None and item.find('QTDE_CANC').text else None,
                'qtde_canc_toler': float(item.find('QTDE_CANC_TOLER').text.replace(',', '.')) if item.find('QTDE_CANC_TOLER') is not None and item.find('QTDE_CANC_TOLER').text else None,
                'perc_toler': float(item.find('PERC_TOLER').text.replace(',', '.')) if item.find('PERC_TOLER') is not None and item.find('PERC_TOLER').text else None,
            }
            order_data['items'].append(item_data)

        purchase_orders.append(order_data)

    return {'purchase_orders': purchase_orders}

def format_for_db(data):
    purchase_orders = data['purchase_orders']
    formatted_orders = []
    formatted_items = []

    for order in purchase_orders:
        formatted_orders.append({
            'cod_pedc': order['cod_pedc'],
            'dt_emis': order['dt_emis'],
            'fornecedor_id': order['fornecedor_id'],
            'fornecedor_descricao': order['fornecedor_descricao'],
            'total_bruto': order['total_bruto'],
            'total_liquido': order['total_liquido'],
            'total_liquido_ipi': order['total_liquido_ipi'],
            'posicao': order['posicao'],
            'posicao_hist': order['posicao_hist'],
            'observacao': order['observacao'],
            'contato': order['contato'],
            'func_nome': order['func_nome'],
            'cf_pgto': order['cf_pgto']
            
        })

        for item in order['items']:
            formatted_items.append({
                'item_id': item['item_id'],
                'descricao': item['descricao'],
                'cod_pedc': order['cod_pedc'],
                'linha': item['linha'],
                'quantidade': item['quantidade'],
                'preco_unitario': item['preco_unitario'],
                'total': item['total'],
                'unidade_medida': item['unidade_medida'],
                'dt_entrega': item['dt_entrega'],
                'perc_ipi': item['perc_ipi'],
                'tot_liquido_ipi': item['tot_liquido_ipi'],
                'tot_descontos': item['tot_descontos'],
                'tot_acrescimos': item['tot_acrescimos'],
                'qtde_canc': item['qtde_canc'],
                'qtde_canc_toler': item['qtde_canc_toler'],
                'perc_toler': item['perc_toler'],
                'purchase_order_id': order['cod_pedc']  # Associando item ao pedido
            })

    return formatted_orders, formatted_items