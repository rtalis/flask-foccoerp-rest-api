def parse_xml(xml_data):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_data)
    purchase_orders = []

    for order in root.findall('.//TPED_COMPRA'):
        order_data = {
            'cod_pedc': order.find('COD_PEDC').text if order.find('COD_PEDC') is not None else None,
            'dt_emis': order.find('DT_EMIS').text if order.find('DT_EMIS') is not None else None,
            'fornecedor_id': int(order.find('FOR_COD').text) if order.find('FOR_COD') is not None else None,
            'fornecedor_descricao': order.find('FOR_DESCRICAO').text if order.find('FOR_DESCRICAO') is not None else None,
            'total_bruto': float(order.find('TOT_BRUTO1').text.replace(',', '.')) if order.find('TOT_BRUTO1') is not None else None,
            'total_liquido': float(order.find('TOT_LIQUIDO1').text.replace(',', '.')) if order.find('TOT_LIQUIDO1') is not None else None,
            'total_liquido_ipi': float(order.find('CP_TOT_IPI').text.replace(',', '.')) if order.find('CP_TOT_IPI') is not None else None,
            'posicao': order.find('POSICAO1').text if order.find('POSICAO1') is not None else None,
            'posicao_hist': order.find('POSICAO_HIST1').text if order.find('POSICAO_HIST1') is not None else None,
            'observacao': order.find('OBSERVACAO').text if order.find('OBSERVACAO') is not None else None,
            'func_nome': order.find('FUNC_NOME').text if order.find('FUNC_NOME') is not None else None,
            'contato': order.find('CONTATO').text if order.find('CONTATO') is not None else None,
            'tp_frete_tra': order.find('TP_FRETE_TRA').text if order.find('TP_FRETE_TRA') is not None else None,
            'empr_id': int(order.find('EMPR_ID').text) if order.find('EMPR_ID') is not None else None,
            'list_tpedc_pgto': order.find('CF_PGTO').text if order.find('CF_PGTO') is not None else None,
            'items': []
        }

        for item in order.findall('.//TPEDC_ITEM'):
            item_data = {
                'item_id': int(item.find('ITEM_ID').text) if item.find('ITEM_ID') is not None else None,
                'cod_pedc': item.find('COD_PEDC').text if item.find('COD_PEDC') is not None else None,
                'linha': int(item.find('LINHA').text) if item.find('LINHA') is not None else None,
                'descricao': item.find('DESCRICAO').text if item.find('DESCRICAO') is not None else None,
                'quantidade': float(item.find('QUANTIDADE').text.replace(',', '.')) if item.find('QUANTIDADE') is not None else None,
                'preco_unitario': float(item.find('PRECO_UNITARIO').text.replace(',', '.')) if item.find('PRECO_UNITARIO') is not None else None,
                'total': float(item.find('TOTAL').text.replace(',', '.')) if item.find('TOTAL') is not None else None,
                'unidade_medida': item.find('UNIDADE_MEDIDA').text if item.find('UNIDADE_MEDIDA') is not None else None,
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

    return purchase_orders

def format_for_db(data):
    formatted_orders = []
    formatted_items = []

    for order in data:
        formatted_order = {
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
            'func_nome': order['func_nome'],
            'contato': order['contato'],
            'tp_frete_tra': order['tp_frete_tra'],
            'empr_id': order['empr_id'],
            'list_tpedc_pgto': order['list_tpedc_pgto']
        }
        formatted_orders.append(formatted_order)

        for item in order['items']:
            formatted_item = {
                'purchase_order_id': order['cod_pedc'],
                'item_id': item['item_id'],
                'cod_pedc': item['cod_pedc'],
                'linha': item['linha'],
                'descricao': item['descricao'],
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
                'perc_toler': item['perc_toler']
            }
            formatted_items.append(formatted_item)

    return formatted_orders, formatted_items