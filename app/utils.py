from datetime import datetime
from flask import jsonify
from app.models import NFEntry, PurchaseAdjustment, PurchaseItem, PurchaseOrder, Quotation
from app import db
from fuzzywuzzy import fuzz
from flask_mail import Mail, Message
from config import Config


def parse_xml(xml_data):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_data)
    purchase_orders = []

    for order in root.findall('.//TPED_COMPRA'):
        cod_pedc = order.find('COD_PEDC').text if order.find('COD_PEDC') is not None else None,

        adjustments = []
        dctacr_list = order.find('LIST_TPEDC_DCTACR')
        if dctacr_list is not None:
            for idx, dctacr in enumerate(dctacr_list.findall('TPEDC_DCTACR')):
                adjustments.append({
                    'tp_apl': dctacr.find('TP_APL').text if dctacr.find('TP_APL') is not None else None,
                    'tp_dctacr1': dctacr.find('TP_DCTACR1').text if dctacr.find('TP_DCTACR1') is not None else None,
                    'tp_vlr1': dctacr.find('TP_VLR1').text if dctacr.find('TP_VLR1') is not None else None,
                    'vlr1': float(dctacr.find('VLR1').text.replace(',', '.')) if dctacr.find('VLR1') is not None and dctacr.find('VLR1').text else None,
                    'order_index': idx,
                })
        order_data = {
            'cod_pedc': cod_pedc,
            'dt_emis': order.find('DT_EMIS').text if order.find('DT_EMIS') is not None else None,
            'fornecedor_id': int(order.find('FOR_COD').text) if order.find('FOR_COD') is not None else None,
            'fornecedor_descricao': order.find('FOR_DESCRICAO').text if order.find('FOR_DESCRICAO') is not None else None,
            'total_bruto': float(order.find('TOT_BRUTO1').text.replace(',', '.')) if order.find('TOT_BRUTO1') is not None and order.find('TOT_BRUTO1').text else None,
            'total_liquido': float(order.find('TOT_LIQUIDO1').text.replace(',', '.')) if order.find('TOT_LIQUIDO1') is not None and order.find('TOT_LIQUIDO1').text else None,
            'total_liquido_ipi': float(order.find('CP_TOT_IPI').text.replace(',', '.')) if order.find('CP_TOT_IPI') is not None and order.find('CP_TOT_IPI').text else None,
            'total_pedido_com_ipi': float(order.find('TOT_LIQUIDO_IPI1').text.replace(',', '.')) if order.find('TOT_LIQUIDO_IPI1') is not None and order.find('TOT_LIQUIDO_IPI1').text else None,
            'posicao': order.find('POSICAO1').text if order.find('POSICAO1') is not None else None,
            'posicao_hist': order.find('POSICAO_HIST1').text if order.find('POSICAO_HIST1') is not None else None,
            'observacao': order.find('OBSERVACAO').text if order.find('OBSERVACAO') is not None else None,
            'contato': order.find('CONTATO').text if order.find('CONTATO') is not None else None,
            'func_nome': order.find('FUNC_NOME').text if order.find('FUNC_NOME') is not None else None,
            'cf_pgto': order.find('CF_PGTO').text if order.find('CF_PGTO') is not None else None,
            'cod_emp1': order.find('EMPR_ID').text if order.find('EMPR_ID') is not None else None,
            'adjustments': adjustments,


            'items': []
        }

        for item in order.findall('.//TPEDC_ITEM'):
         
            item_data = {
                'item_id': int(item.find('ITEM_COD').text) if item.find('ITEM_COD') is not None else None,
                
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
                'qtde_atendida': float(item.find('QTDE_ATENDIDA').text.replace(',', '.')) if item.find('QTDE_ATENDIDA') is not None and item.find('QTDE_ATENDIDA').text else None,
                'qtde_saldo': float(item.find('QTDE_SALDO').text.replace(',', '.')) if item.find('QTDE_SALDO') is not None and item.find('QTDE_SALDO').text else None,
                'cod_emp1': item.find('COD_EMP1').text if item.find('COD_EMP1') is not None else None
            }
            order_data['items'].append(item_data)

        purchase_orders.append(order_data)

    return {'purchase_orders': purchase_orders}

def format_for_db(data):


    purchase_orders = data['purchase_orders']
    formatted_orders = []
    formatted_items = []
    formatted_adjustments = []

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
            'cf_pgto': order['cf_pgto'],
            'cod_emp1': order['cod_emp1'],
            'total_pedido_com_ipi': order['total_pedido_com_ipi']
        })
        for adj in order.get('adjustments', []):
            formatted_adjustments.append({
                'cod_pedc': order['cod_pedc'],
                'cod_emp1': order['cod_emp1'],
                **adj
            })

        for item in order['items']:
            formatted_items.append({
                'item_id': item['item_id'],
                'dt_emis': order['dt_emis'],
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
                'qtde_atendida': item['qtde_atendida'],
                'qtde_saldo': item['qtde_saldo'],
                'purchase_order_id': order['cod_pedc'], 
                'cod_emp1': item['cod_emp1']
            })

    return formatted_orders, formatted_items, formatted_adjustments

def format_for_db_rpdc0250c(xml_data):
    formatted_items = []
    import xml.etree.ElementTree as ET

    data = ET.fromstring(xml_data)
    for g_cod_emp1 in data.findall('.//G_COD_EMP1'):
        cod_emp1 = g_cod_emp1.find('COD_EMP').text
        for cgg_tpedc_item in g_cod_emp1.findall('.//CGG_TPEDC_ITEM'):
            cod_pedc = cgg_tpedc_item.find('CODIGO_PEDIDO').text
            linha = cgg_tpedc_item.find('LINHA1').text
            for g_nfe in cgg_tpedc_item.findall('.//G_NFE'):
                num_nf = g_nfe.find('NUM_NF').text if g_nfe.find('NUM_NF') is not None else None
                dt_ent = g_nfe.find('DT_ENT').text if g_nfe.find('DT_ENT') is not None else None
                if dt_ent:
                    try:
                        dt_ent = datetime.strptime(dt_ent, '%d/%m/%y').date()
                    except ValueError:
                        dt_ent = None
                if num_nf:                
                    formatted_items.append({
                        'cod_emp1': cod_emp1,
                        'cod_pedc': cod_pedc,
                        'linha': linha,
                        'num_nf': num_nf,
                        'dt_ent': dt_ent
                    })
    return formatted_items
def import_ruah(file_content):

    data = parse_xml(file_content)  # Passe o conteúdo do arquivo para a função parse_xml
    formatted_orders, formatted_items, formatted_adjustments = format_for_db(data) #Formate os dados para o banco de dados
    itemcount = 0
    purchasecount = 0
    updated = 0

    for order_data in formatted_orders:       
        existing_order = PurchaseOrder.query.filter_by(
                cod_pedc=order_data['cod_pedc'],
                cod_emp1=order_data['cod_emp1']
            ).first()        
        if existing_order:
            PurchaseItem.query.filter_by(purchase_order_id=existing_order.id).delete()
            PurchaseAdjustment.query.filter_by(purchase_order_id=existing_order.id).delete()
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
            total_pedido_com_ipi=order_data['total_pedido_com_ipi'],
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
                    dt_emis=item_data['dt_emis'],
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

        
        for adj_data in formatted_adjustments:
            if order:
                if adj_data['cod_pedc'] == order_data['cod_pedc'] and adj_data['cod_emp1'] == order_data['cod_emp1']:
                    adjustment = PurchaseAdjustment(
                        purchase_order_id=order.id,
                        cod_pedc=adj_data['cod_pedc'],
                        cod_emp1=adj_data['cod_emp1'],
                        tp_apl=adj_data['tp_apl'],
                        tp_dctacr1=adj_data['tp_dctacr1'],
                        tp_vlr1=adj_data['tp_vlr1'],
                        vlr1=adj_data['vlr1'],
                        order_index=adj_data['order_index']
                    )
                    db.session.add(adjustment)
                
        
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
                dt_ent=item_data.get('dt_ent', ''),
            )
            itemcount += 1
            db.session.add(nf_entry)

    db.session.commit()
    return jsonify({'message': 'Data imported successfully items {}, updated {}'.format(itemcount, updated)}), 201

def parse_rcot0300(xml_data):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_data)
    quotations = []

    for g1 in root.findall('.//G_1'):
        cod_cot = g1.find('COD_COT').text if g1.find('COD_COT') is not None else None
        dt_emissao = g1.find('DT_EMISSAO').text if g1.find('DT_EMISSAO') is not None else None
        dt_emissao = datetime.strptime(dt_emissao, '%d/%m/%y').strftime('%Y-%m-%d') if dt_emissao else None

        for g2 in g1.findall('.//G_2'):
            for g3 in g2.findall('.//G_3'):
                fornecedor_id = g3.find('ID_FORN').text if g3.find('ID_FORN') is not None else None
                fornecedor_descricao = g3.find('FORNECEDOR').text if g3.find('FORNECEDOR') is not None else None

                for g4 in g3.findall('.//G_4'):
                    item_id = g4.find('COD_ITEM').text if g4.find('COD_ITEM') is not None else None
                    descricao = g4.find('DESC_ITEM').text if g4.find('DESC_ITEM') is not None else None
                    quantidade = g4.find('QTDE').text if g4.find('QTDE') is not None else None
                    quantidade = float(quantidade.replace(',', '.')) if quantidade else None
                    preco_unitario = g4.find('PRECO_UNITARIO').text if g4.find('PRECO_UNITARIO') is not None else None
                    preco_unitario = float(preco_unitario.replace(',', '.')) if preco_unitario else None
                    dt_entrega = g4.find('DT_ENTREGA').text if g4.find('DT_ENTREGA') is not None else None
                    dt_entrega = datetime.strptime(dt_entrega, '%d/%m/%y').strftime('%Y-%m-%d') if dt_entrega else None
                    cod_emp1 = g4.find('COD_EMP').text if g4.find('COD_EMP') is not None else None

                    quotation_data = {
                        'cod_cot': cod_cot,
                        'dt_emissao': dt_emissao,
                        'fornecedor_id': fornecedor_id,
                        'fornecedor_descricao': fornecedor_descricao,
                        'item_id': item_id,
                        'descricao': descricao,
                        'quantidade': quantidade,
                        'preco_unitario': preco_unitario,
                        'dt_entrega': dt_entrega,
                        'cod_emp1': cod_emp1
                    }
                    quotations.append(quotation_data)

    return {'quotations': quotations}

def import_rcot0300(file_content):
    data = parse_rcot0300(file_content)
    quotations = data['quotations']
    new_count = 0
    updated_count = 0

    for quotation_data in quotations:
        # Check if quotation already exists
        existing_quotation = Quotation.query.filter_by(
            cod_cot=quotation_data['cod_cot'],
            item_id=quotation_data['item_id'],
            fornecedor_id=quotation_data['fornecedor_id']
        ).first()
        
        if existing_quotation:
            # Update existing quotation
            existing_quotation.dt_emissao = quotation_data['dt_emissao']
            existing_quotation.fornecedor_descricao = quotation_data['fornecedor_descricao']
            existing_quotation.descricao = quotation_data['descricao']
            existing_quotation.quantidade = quotation_data['quantidade']
            existing_quotation.preco_unitario = quotation_data['preco_unitario']
            existing_quotation.dt_entrega = quotation_data['dt_entrega']
            existing_quotation.cod_emp1 = quotation_data['cod_emp1']
            updated_count += 1
        else:
            # Create new quotation
            quotation = Quotation(
                cod_cot=quotation_data['cod_cot'],
                dt_emissao=quotation_data['dt_emissao'],
                fornecedor_id=quotation_data['fornecedor_id'],
                fornecedor_descricao=quotation_data['fornecedor_descricao'],
                item_id=quotation_data['item_id'],
                descricao=quotation_data['descricao'],
                quantidade=quotation_data['quantidade'],
                preco_unitario=quotation_data['preco_unitario'],
                dt_entrega=quotation_data['dt_entrega'],
                cod_emp1=quotation_data['cod_emp1']
            )
            db.session.add(quotation)
            new_count += 1

    db.session.commit()
    return jsonify({
        'message': f'Data imported successfully: {len(quotations)} total quotations ({new_count} new, {updated_count} updated)'
    }), 201


def fuzzy_search(query, items, score_cutoff, search_by_descricao, search_by_observacao):
    results = []
    for item in items:
        if len(results) >= 3000:
            return results
        ratio = fuzz.partial_ratio(query.lower(), item.descricao.lower())
        if ratio >= score_cutoff and search_by_descricao:  # Ajuste o limite conforme necessário
            results.append(item)
        else:
            observacao = item.purchase_order.observacao or ''
            ratio = fuzz.partial_ratio(query.lower(), observacao.lower())
            if ratio >= score_cutoff and search_by_observacao:  # Ajuste o limite conforme necessário
                results.append(item)
    return results


mail = Mail()

def send_login_notification_email(user, ip_address):
    try:
        msg = Message(
            'Nova tentativa de login',
            sender=Config.MAIL_USERNAME,
            recipients=[Config.ADMIN_EMAIL]
        )
        msg.body = f"""
        Novo login detectado:
        Usuário: {user.username}
        Email: {user.email}
        IP: {ip_address}
        Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """
        mail.send(msg)
    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")

def import_rfor0302(file_content):
    import xml.etree.ElementTree as ET
    from app.models import Supplier

    root = ET.fromstring(file_content)
    suppliers = []
    new_count = 0
    updated_count = 0
    
    for g_fornec in root.findall('.//G_FORNEC'):
        cod_for = g_fornec.findtext('COD_FOR')
        existing_supplier = Supplier.query.filter_by(cod_for=cod_for).first()
        
        if existing_supplier:
            existing_supplier.tip_forn = g_fornec.findtext('TIP_FORN')
            existing_supplier.conta_itens = g_fornec.findtext('CONTA_ITENS')
            existing_supplier.insc_est = g_fornec.findtext('INSC_EST')
            existing_supplier.insc_mun = g_fornec.findtext('INSC_MUN')
            existing_supplier.email = g_fornec.findtext('EMAIL')
            existing_supplier.tel_ddd_tel_telefone = g_fornec.findtext('TEL_DDD_TEL_TELEFONE')
            existing_supplier.endereco = g_fornec.findtext('ENDERECO')
            existing_supplier.cep = g_fornec.findtext('CEP')
            existing_supplier.cidade = g_fornec.findtext('CIDADE')
            existing_supplier.uf = g_fornec.findtext('UF')
            existing_supplier.cod_for = g_fornec.findtext('COD_FOR')
            existing_supplier.nvl_forn_cnpj_forn_cpf = g_fornec.findtext('NVL_FORN_CNPJ_FORN_CPF')
            existing_supplier.descricao = g_fornec.findtext('DESCRICAO')
            existing_supplier.bairro = g_fornec.findtext('BAIRRO')
            existing_supplier.cf_fax = g_fornec.findtext('CF_FAX')
            suppliers.append(existing_supplier)
            updated_count += 1
        else:
            # Create new supplier
            supplier = Supplier(
                tip_forn=g_fornec.findtext('TIP_FORN'),
                conta_itens=g_fornec.findtext('CONTA_ITENS'),
                insc_est=g_fornec.findtext('INSC_EST'),
                insc_mun=g_fornec.findtext('INSC_MUN'),
                email=g_fornec.findtext('EMAIL'),
                tel_ddd_tel_telefone=g_fornec.findtext('TEL_DDD_TEL_TELEFONE'),
                endereco=g_fornec.findtext('ENDERECO'),
                cep=g_fornec.findtext('CEP'),
                cidade=g_fornec.findtext('CIDADE'),
                uf=g_fornec.findtext('UF'),
                id_for= g_fornec.findtext('ID_FOR'),
                cod_for=g_fornec.findtext('COD_FOR'),
                nvl_forn_cnpj_forn_cpf=g_fornec.findtext('NVL_FORN_CNPJ_FORN_CPF'),
                descricao=g_fornec.findtext('DESCRICAO'),
                bairro=g_fornec.findtext('BAIRRO'),
                cf_fax=g_fornec.findtext('CF_FAX')
            )
            suppliers.append(supplier)
            db.session.add(supplier)
            new_count += 1
            
    db.session.commit()
    return jsonify({
        'message': f'Suppliers imported: {len(suppliers)} total ({new_count} new, {updated_count} updated)'
    }), 201

def apply_adjustments(base_value, adjustments):
    value = base_value
    for adj in adjustments:
        if adj.tp_apl == 'Pedido':
            if adj.tp_vlr1 == 'Percentual':
                percent = adj.vlr1 or 0
                if adj.tp_dctacr1 == 'Desconto':
                    value -= value * (percent / 100)
                elif adj.tp_dctacr1 == 'Acréscimo':
                    value += value * (percent / 100)
            elif adj.tp_vlr1 == 'Valor':
                amount = adj.vlr1 or 0
                if adj.tp_dctacr1 == 'Desconto':
                    value -= amount
                elif adj.tp_dctacr1 == 'Acréscimo':
                    value += amount
        elif adj.tp_apl == 'Itens':
            if adj.tp_vlr1 == 'Valor':
                amount = adj.vlr1 or 0
                if adj.tp_dctacr1 == 'Desconto':
                    value -= amount
                elif adj.tp_dctacr1 == 'Acréscimo':
                    value += amount

    return value