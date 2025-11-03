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
                qtde = g_nfe.find('QTDE1').text if g_nfe.find('QTDE1') is not None else None
                
                if not num_nf or not num_nf.strip():
                    continue
                    
                if dt_ent:
                    try:
                        dt_ent = datetime.strptime(dt_ent, '%d/%m/%y').date()
                    except ValueError:
                        dt_ent = None
                
                if qtde:
                    try:
                        qtde = float(qtde.replace(',', '.'))
                    except (ValueError, AttributeError):
                        qtde = None
                
                formatted_items.append({
                    'cod_emp1': cod_emp1,
                    'cod_pedc': cod_pedc,
                    'linha': linha,
                    'num_nf': num_nf,
                    'dt_ent': dt_ent,
                    'qtde': qtde  
                })
    return formatted_items
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

        order.is_fulfilled = check_order_fulfillment(order.id)
            
                
        
    db.session.commit()
    return jsonify({'message': 'Data imported successfully purchases {}, items {}, updated {}'.format(purchasecount - updated, itemcount, updated)}), 201

def import_rpdc0250c(file_content):
    formatted_items = format_for_db_rpdc0250c(file_content) 
    itemcount = 0
    updated = 0
    
    unique_combinations = {}
    for item_data in formatted_items:
        if item_data and item_data['num_nf']:
            key = (item_data['cod_emp1'], item_data['cod_pedc'], item_data['linha'], item_data['num_nf'])
            if key not in unique_combinations:
                unique_combinations[key] = item_data

    for key, item_data in unique_combinations.items():
        if item_data:
            existing_entry = NFEntry.query.filter_by(
                cod_emp1=item_data['cod_emp1'],
                cod_pedc=item_data['cod_pedc'],
                linha=item_data['linha'],
                num_nf=item_data['num_nf']
            ).first()

            if existing_entry:
                has_changes = False
                if existing_entry.dt_ent != item_data.get('dt_ent'):
                    existing_entry.dt_ent = item_data.get('dt_ent', '')
                    has_changes = True
                    
                if hasattr(existing_entry, 'qtde') and existing_entry.qtde != item_data.get('qtde'):
                    existing_entry.qtde = item_data.get('qtde')
                    has_changes = True
                
                if has_changes:
                    db.session.commit()
                    updated += 1
            else:
                nf_entry = NFEntry(
                    cod_emp1=item_data['cod_emp1'],
                    cod_pedc=item_data['cod_pedc'],
                    linha=item_data['linha'],
                    num_nf=item_data['num_nf'],
                    dt_ent=item_data.get('dt_ent', ''),
                    qtde=item_data.get('qtde')  
                )
                itemcount += 1
                db.session.add(nf_entry)

    db.session.commit()
    return jsonify({'message': f'Data imported successfully: {itemcount} new entries, {updated} updated'}), 201

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

# Add this new function to your utils.py file

def parse_and_store_nfe_xml(xml_content):
    """
    Parse NFE XML content and store all data in the database
    Returns the NFEData object
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime
    from app.models import (
        NFEData, NFEEmitente, NFEDestinatario, NFEItem, 
        NFETransportadora, NFEVolume, NFEPagamento, NFEDuplicata
    )
    from app import db
    
    # Parse XML
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    root = ET.fromstring(xml_content)
    
    # First check if we're dealing with nfeProc or NFe
    if root.tag.endswith('nfeProc'):
        nfe_elem = root.find('.//nfe:NFe', ns)
        inf_nfe = nfe_elem.find('.//nfe:infNFe', ns)
        prot_nfe = root.find('.//nfe:protNFe', ns)
    else:
        nfe_elem = root
        inf_nfe = nfe_elem.find('.//nfe:infNFe', ns)
        prot_nfe = None
    
    # Extract chave from ID (format: "NFe12345...")
    chave = inf_nfe.attrib.get('Id', '')[3:] if 'Id' in inf_nfe.attrib else ''
    
    # Check if NFE already exists
    existing_nfe = NFEData.query.filter_by(chave=chave).first()
    if existing_nfe:
        return existing_nfe
    
    # Extract basic NFE data
    ide = inf_nfe.find('.//nfe:ide', ns)
    emit = inf_nfe.find('.//nfe:emit', ns)
    dest = inf_nfe.find('.//nfe:dest', ns)
    total = inf_nfe.find('.//nfe:total/nfe:ICMSTot', ns)
    transp = inf_nfe.find('.//nfe:transp', ns)
    transp_info = transp.find('.//nfe:transporta', ns) if transp is not None else None
    infAdic = inf_nfe.find('.//nfe:infAdic', ns)
    
    # Format dates
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            # Handle different date formats
            if 'T' in date_str:
                date_part = date_str.split('T')[0] if 'T' in date_str else date_str
                time_part = date_str.split('T')[1].split('-')[0] if 'T' in date_str else '00:00:00'
                return datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None
    
    # Get decimal values safely
    def safe_float(elem, xpath):
        try:
            val = elem.find(xpath, ns)
            return float(val.text) if val is not None and val.text else 0.0
        except:
            return 0.0
    
    # Get text values safely
    def safe_text(elem, xpath):
        try:
            val = elem.find(xpath, ns)
            return val.text if val is not None else ''
        except:
            return ''
    
    # Create NFE main record
    nfe_data = NFEData(
        chave=chave,
        xml_content=xml_content,
        versao=inf_nfe.attrib.get('versao', ''),
        modelo=safe_text(ide, './/nfe:mod'),
        numero=safe_text(ide, './/nfe:nNF'),
        serie=safe_text(ide, './/nfe:serie'),
        data_emissao=parse_date(safe_text(ide, './/nfe:dhEmi')),
        data_saida=parse_date(safe_text(ide, './/nfe:dhSaiEnt')),
        natureza_operacao=safe_text(ide, './/nfe:natOp'),
        tipo_operacao=safe_text(ide, './/nfe:tpNF'),
        finalidade=safe_text(ide, './/nfe:finNFe'),
        uf_emitente=safe_text(ide, './/nfe:cUF'),
        codigo_municipio=safe_text(ide, './/nfe:cMunFG'),
        ambiente=safe_text(ide, './/nfe:tpAmb'),
        
        # Values from total
        valor_total=safe_float(total, './/nfe:vNF'),
        valor_produtos=safe_float(total, './/nfe:vProd'),
        valor_frete=safe_float(total, './/nfe:vFrete'),
        valor_seguro=safe_float(total, './/nfe:vSeg'),
        valor_desconto=safe_float(total, './/nfe:vDesc'),
        valor_imposto=safe_float(total, './/nfe:vTotTrib'),
        valor_icms=safe_float(total, './/nfe:vICMS'),
        valor_icms_st=safe_float(total, './/nfe:vST'),
        valor_ipi=safe_float(total, './/nfe:vIPI'),
        valor_pis=safe_float(total, './/nfe:vPIS'),
        valor_cofins=safe_float(total, './/nfe:vCOFINS'),
        valor_outros=safe_float(total, './/nfe:vOutro'),
        
        # Additional info
        informacoes_adicionais=safe_text(infAdic, './/nfe:infCpl') if infAdic is not None else '',
        informacoes_fisco=safe_text(infAdic, './/nfe:infAdFisco') if infAdic is not None else '',
        
        # Transport
        modalidade_frete=safe_text(transp, './/nfe:modFrete') if transp is not None else '',
        
        # Protocol data
        status_code=safe_text(prot_nfe, './/nfe:infProt/nfe:cStat') if prot_nfe is not None else '',
        status_motivo=safe_text(prot_nfe, './/nfe:infProt/nfe:xMotivo') if prot_nfe is not None else '',
        protocolo=safe_text(prot_nfe, './/nfe:infProt/nfe:nProt') if prot_nfe is not None else '',
        data_autorizacao=parse_date(safe_text(prot_nfe, './/nfe:infProt/nfe:dhRecbto')) if prot_nfe is not None else None
    )
    
    # Create emitter record
    if emit is not None:
        ender_emit = emit.find('.//nfe:enderEmit', ns)
        emitente = NFEEmitente(
            nfe=nfe_data,
            cnpj=safe_text(emit, './/nfe:CNPJ'),
            cpf=safe_text(emit, './/nfe:CPF'),
            nome=safe_text(emit, './/nfe:xNome'),
            nome_fantasia=safe_text(emit, './/nfe:xFant'),
            inscricao_estadual=safe_text(emit, './/nfe:IE'),
            inscricao_municipal=safe_text(emit, './/nfe:IM'),
            codigo_regime_tributario=safe_text(emit, './/nfe:CRT'),
            
            # Address fields if present
            logradouro=safe_text(ender_emit, './/nfe:xLgr') if ender_emit is not None else '',
            numero=safe_text(ender_emit, './/nfe:nro') if ender_emit is not None else '',
            complemento=safe_text(ender_emit, './/nfe:xCpl') if ender_emit is not None else '',
            bairro=safe_text(ender_emit, './/nfe:xBairro') if ender_emit is not None else '',
            codigo_municipio=safe_text(ender_emit, './/nfe:cMun') if ender_emit is not None else '',
            municipio=safe_text(ender_emit, './/nfe:xMun') if ender_emit is not None else '',
            uf=safe_text(ender_emit, './/nfe:UF') if ender_emit is not None else '',
            cep=safe_text(ender_emit, './/nfe:CEP') if ender_emit is not None else '',
            pais=safe_text(ender_emit, './/nfe:xPais') if ender_emit is not None else '',
            codigo_pais=safe_text(ender_emit, './/nfe:cPais') if ender_emit is not None else '',
            telefone=safe_text(ender_emit, './/nfe:fone') if ender_emit is not None else ''
        )
        db.session.add(emitente)
    
    # Create recipient record
    if dest is not None:
        ender_dest = dest.find('.//nfe:enderDest', ns)
        destinatario = NFEDestinatario(
            nfe=nfe_data,
            cnpj=safe_text(dest, './/nfe:CNPJ'),
            cpf=safe_text(dest, './/nfe:CPF'),
            id_estrangeiro=safe_text(dest, './/nfe:idEstrangeiro'),
            nome=safe_text(dest, './/nfe:xNome'),
            indicador_ie=safe_text(dest, './/nfe:indIEDest'),
            inscricao_estadual=safe_text(dest, './/nfe:IE'),
            inscricao_suframa=safe_text(dest, './/nfe:ISUF'),
            email=safe_text(dest, './/nfe:email'),
            
            # Address fields if present
            logradouro=safe_text(ender_dest, './/nfe:xLgr') if ender_dest is not None else '',
            numero=safe_text(ender_dest, './/nfe:nro') if ender_dest is not None else '',
            complemento=safe_text(ender_dest, './/nfe:xCpl') if ender_dest is not None else '',
            bairro=safe_text(ender_dest, './/nfe:xBairro') if ender_dest is not None else '',
            codigo_municipio=safe_text(ender_dest, './/nfe:cMun') if ender_dest is not None else '',
            municipio=safe_text(ender_dest, './/nfe:xMun') if ender_dest is not None else '',
            uf=safe_text(ender_dest, './/nfe:UF') if ender_dest is not None else '',
            cep=safe_text(ender_dest, './/nfe:CEP') if ender_dest is not None else '',
            pais=safe_text(ender_dest, './/nfe:xPais') if ender_dest is not None else '',
            codigo_pais=safe_text(ender_dest, './/nfe:cPais') if ender_dest is not None else '',
            telefone=safe_text(ender_dest, './/nfe:fone') if ender_dest is not None else ''
        )
        db.session.add(destinatario)
    
    # Process all items
    itens = inf_nfe.findall('.//nfe:det', ns)
    for item_elem in itens:
        num_item = int(item_elem.attrib.get('nItem', '0'))
        prod = item_elem.find('.//nfe:prod', ns)
        imposto = item_elem.find('.//nfe:imposto', ns)
        
        icms_elem = imposto.find('.//nfe:ICMS', ns) if imposto is not None else None
        icms_type = None
        if icms_elem is not None:
            for icms_type_elem in icms_elem:
                if icms_type_elem.tag.split('}')[-1].startswith('ICMS'):
                    icms_type = icms_type_elem
                    break
        
        ipi_elem = imposto.find('.//nfe:IPI', ns) if imposto is not None else None
        ipi_type = None
        if ipi_elem is not None:
            for ipi_type_tag in ['IPITrib', 'IPINT']:
                ipi_type_elem = ipi_elem.find(f'.//nfe:{ipi_type_tag}', ns)
                if ipi_type_elem is not None:
                    ipi_type = ipi_type_elem
                    break
        
        pis_elem = imposto.find('.//nfe:PIS/nfe:PISAliq', ns) if imposto is not None else None
        cofins_elem = imposto.find('.//nfe:COFINS/nfe:COFINSAliq', ns) if imposto is not None else None
        
        # Special elements for fuels, medicines, vehicles, etc.
        comb_elem = prod.find('.//nfe:comb', ns) if prod is not None else None
        
        item = NFEItem(
            nfe=nfe_data,
            numero_item=num_item,
            codigo=safe_text(prod, './/nfe:cProd') if prod is not None else '',
            codigo_ean=safe_text(prod, './/nfe:cEAN') if prod is not None else '',
            descricao=safe_text(prod, './/nfe:xProd') if prod is not None else '',
            ncm=safe_text(prod, './/nfe:NCM') if prod is not None else '',
            cest=safe_text(prod, './/nfe:CEST') if prod is not None else '',
            cfop=safe_text(prod, './/nfe:CFOP') if prod is not None else '',
            unidade_comercial=safe_text(prod, './/nfe:uCom') if prod is not None else '',
            quantidade_comercial=safe_float(prod, './/nfe:qCom') if prod is not None else 0,
            valor_unitario_comercial=safe_float(prod, './/nfe:vUnCom') if prod is not None else 0,
            valor_total_bruto=safe_float(prod, './/nfe:vProd') if prod is not None else 0,
            codigo_ean_tributario=safe_text(prod, './/nfe:cEANTrib') if prod is not None else '',
            unidade_tributavel=safe_text(prod, './/nfe:uTrib') if prod is not None else '',
            quantidade_tributavel=safe_float(prod, './/nfe:qTrib') if prod is not None else 0,
            valor_unitario_tributavel=safe_float(prod, './/nfe:vUnTrib') if prod is not None else 0,
            ind_total=safe_text(prod, './/nfe:indTot') if prod is not None else '',
            
            # ANP data for fuels and lubricants
            codigo_prod_anp=safe_text(comb_elem, './/nfe:cProdANP') if comb_elem is not None else '',
            descricao_anp=safe_text(comb_elem, './/nfe:descANP') if comb_elem is not None else '',
            uf_consumo=safe_text(comb_elem, './/nfe:UFCons') if comb_elem is not None else '',
            
            # Tax data
            valor_total_tributos=safe_float(imposto, './/nfe:vTotTrib') if imposto is not None else 0,
            
            # ICMS data
            icms_origem=safe_text(icms_type, './/nfe:orig') if icms_type is not None else '',
            icms_cst=safe_text(icms_type, './/nfe:CST') if icms_type is not None else '',
            icms_modbc=safe_text(icms_type, './/nfe:modBC') if icms_type is not None else '',
            icms_vbc=safe_float(icms_type, './/nfe:vBC') if icms_type is not None else 0,
            icms_picms=safe_float(icms_type, './/nfe:pICMS') if icms_type is not None else 0,
            icms_vicms=safe_float(icms_type, './/nfe:vICMS') if icms_type is not None else 0,
            
            # IPI data
            ipi_cenq=safe_text(ipi_elem, './/nfe:cEnq') if ipi_elem is not None else '',
            ipi_cst=safe_text(ipi_type, './/nfe:CST') if ipi_type is not None else '',
            
            # PIS data
            pis_cst=safe_text(pis_elem, './/nfe:CST') if pis_elem is not None else '',
            pis_vbc=safe_float(pis_elem, './/nfe:vBC') if pis_elem is not None else 0,
            pis_ppis=safe_float(pis_elem, './/nfe:pPIS') if pis_elem is not None else 0,
            pis_vpis=safe_float(pis_elem, './/nfe:vPIS') if pis_elem is not None else 0,
            
            # COFINS data
            cofins_cst=safe_text(cofins_elem, './/nfe:CST') if cofins_elem is not None else '',
            cofins_vbc=safe_float(cofins_elem, './/nfe:vBC') if cofins_elem is not None else 0,
            cofins_pcofins=safe_float(cofins_elem, './/nfe:pCOFINS') if cofins_elem is not None else 0,
            cofins_vcofins=safe_float(cofins_elem, './/nfe:vCOFINS') if cofins_elem is not None else 0,
            
            # Additional info
            inf_ad_prod=safe_text(item_elem, './/nfe:infAdProd')
        )
        db.session.add(item)
    
    # Create transportadora record if present
    if transp_info is not None:
        transportadora = NFETransportadora(
            nfe=nfe_data,
            cnpj=safe_text(transp_info, './/nfe:CNPJ'),
            cpf=safe_text(transp_info, './/nfe:CPF'),
            nome=safe_text(transp_info, './/nfe:xNome'),
            inscricao_estadual=safe_text(transp_info, './/nfe:IE'),
            endereco=safe_text(transp_info, './/nfe:xEnder'),
            municipio=safe_text(transp_info, './/nfe:xMun'),
            uf=safe_text(transp_info, './/nfe:UF')
        )
        db.session.add(transportadora)
        
        # Add vehicle information if present
        veic_transp = transp.find('.//nfe:veicTransp', ns)
        if veic_transp is not None:
            transportadora.placa = safe_text(veic_transp, './/nfe:placa')
            transportadora.uf_veiculo = safe_text(veic_transp, './/nfe:UF')
            transportadora.rntc = safe_text(veic_transp, './/nfe:RNTC')
    
    # Add volume information if present
    vol_elems = transp.findall('.//nfe:vol', ns) if transp is not None else []
    for vol_elem in vol_elems:
        volume = NFEVolume(
            nfe=nfe_data,
            quantidade=int(safe_text(vol_elem, './/nfe:qVol')) if safe_text(vol_elem, './/nfe:qVol') else 0,
            especie=safe_text(vol_elem, './/nfe:esp'),
            marca=safe_text(vol_elem, './/nfe:marca'),
            numeracao=safe_text(vol_elem, './/nfe:nVol'),
            peso_liquido=safe_float(vol_elem, './/nfe:pesoL'),
            peso_bruto=safe_float(vol_elem, './/nfe:pesoB')
        )
        db.session.add(volume)
    
    # Add payment information
    pag_elem = inf_nfe.find('.//nfe:pag', ns)
    if pag_elem is not None:
        for det_pag in pag_elem.findall('.//nfe:detPag', ns):
            pagamento = NFEPagamento(
                nfe=nfe_data,
                indicador=safe_text(det_pag, './/nfe:indPag'),
                tipo=safe_text(det_pag, './/nfe:tPag'),
                valor=safe_float(det_pag, './/nfe:vPag')
            )
            db.session.add(pagamento)
    
    # Add installment information (duplicatas)
    cobr_elem = inf_nfe.find('.//nfe:cobr', ns)
    if cobr_elem is not None:
        for dup_elem in cobr_elem.findall('.//nfe:dup', ns):
            duplicata = NFEDuplicata(
                nfe=nfe_data,
                numero=safe_text(dup_elem, './/nfe:nDup'),
                data_vencimento=parse_date(safe_text(dup_elem, './/nfe:dVenc')),
                valor=safe_float(dup_elem, './/nfe:vDup')
            )
            db.session.add(duplicata)
    
    # Add to database
    db.session.add(nfe_data)
    db.session.commit()
    
    return nfe_data

def check_order_fulfillment(order_id):
    """Check if all items in a purchase order are fulfilled or fully canceled."""

    def to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    items = PurchaseItem.query.filter_by(purchase_order_id=order_id).all()
    if not items:
        return False

    for item in items:
        quantity = to_float(item.quantidade)
        if quantity is None:
            return False
        if quantity <= 0:
            continue

        attended = to_float(item.qtde_atendida) or 0.0
        canceled = to_float(item.qtde_canc) or 0.0
        canceled_tolerance = to_float(item.qtde_canc_toler) or 0.0
        total_canceled = canceled + canceled_tolerance

        if attended >= quantity:
            continue
        if total_canceled >= quantity:
            continue
        if attended + total_canceled >= quantity:
            continue

        return False

    return True

def score_purchase_nfe_match(purchase_order_id, nfe_id=None):
    """
    Calculate a matching score between a purchase order and an NFE.
    If nfe_id is None, find and score all potential matches in the database.
    
    Returns a score from 0-100 with detailed breakdown of matching criteria.
    """
    from app.models import PurchaseOrder, PurchaseItem, NFEData, NFEItem, NFEEmitente, Supplier
    from fuzzywuzzy import fuzz
    from datetime import timedelta
    import re
    
    # Get purchase order
    purchase_order = PurchaseOrder.query.filter_by(cod_pedc=str(purchase_order_id)).first()
    if not purchase_order:
        return {"error": "Purchase order not found"}
        
    # Get purchase items
    purchase_items = PurchaseItem.query.filter_by(purchase_order_id=purchase_order.id).all()
    if not purchase_items:
        return {"error": "No items found for this purchase order"}
    
    # Get supplier information
    supplier = Supplier.query.filter_by(cod_for=str(purchase_order.fornecedor_id)).first()
    supplier_cnpj = supplier.nvl_forn_cnpj_forn_cpf if supplier else None
    if supplier_cnpj:
        supplier_cnpj = ''.join(filter(str.isdigit, supplier_cnpj))
    
    nfe_candidates = []
    
    if nfe_id:
        # If specific NFE ID provided, only score that one
        nfe = NFEData.query.get(nfe_id)
        if nfe:
            nfe_candidates = [nfe]
    else:
        # Find NFEs by supplier CNPJ
        if supplier_cnpj:
            cnpj_root = supplier_cnpj[:8]  # Get the first 8 digits
            cnpj_matches = NFEData.query.join(NFEEmitente).filter(
                NFEEmitente.cnpj.like(f"{cnpj_root}%"),
                NFEData.data_emissao.between(
                    purchase_order.dt_emis - timedelta(days=30),
                    purchase_order.dt_emis + timedelta(days=90)
                )
            ).all()
            nfe_candidates.extend(cnpj_matches)

        # Find NFEs by supplier name if no CNPJ matches
        if not nfe_candidates:
            # Get all NFEs in the relevant date range
            date_range_nfes = NFEData.query.filter(
                NFEData.data_emissao.between(
                    purchase_order.dt_emis - timedelta(days=30),
                    purchase_order.dt_emis + timedelta(days=90)
                )
            ).all()
            
            # Check supplier name similarity
            for nfe in date_range_nfes:
                if nfe.emitente and nfe.emitente.nome and purchase_order.fornecedor_descricao:
                    name_similarity = fuzz.token_sort_ratio(
                        purchase_order.fornecedor_descricao.lower(),
                        nfe.emitente.nome.lower()
                    )
                    if name_similarity >= 70:  # 70% name similarity threshold
                        nfe_candidates.append(nfe)
    
    # Calculate scores for each candidate
    results = []
    
    for nfe in nfe_candidates:
        # Initialize scoring components (total 100 points)
        score_components = {
            "supplier_match": 0,       # 20 points
            "items_match": 0,          # 40 points
            "total_value_match": 0,    # 30 points
            "date_proximity": 0        # 10 points
        }
        
        # 1. Supplier matching (20 points)
        if supplier_cnpj and nfe.emitente and nfe.emitente.cnpj:
            if supplier_cnpj == nfe.emitente.cnpj:
                score_components["supplier_match"] = 20  # Perfect CNPJ match
            else:
                # Partial CNPJ match check (last 8 digits)
                if len(supplier_cnpj) >= 8 and len(nfe.emitente.cnpj) >= 8:
                    if supplier_cnpj[-8:] == nfe.emitente.cnpj[-8:]:
                        score_components["supplier_match"] = 15
        
        # If no CNPJ match, try name matching
        if score_components["supplier_match"] == 0 and nfe.emitente and nfe.emitente.nome:
            name_similarity = fuzz.token_sort_ratio(
                purchase_order.fornecedor_descricao.lower(),
                nfe.emitente.nome.lower()
            )
            score_components["supplier_match"] = (name_similarity / 100) * 20
        
        # 2. Items matching (40 points)
        matched_items = []
        total_po_items = len(purchase_items)
        
        for po_item in purchase_items:
            best_match = None
            best_score = 0
            
            for nfe_item in nfe.itens:
                # Description similarity (0-100)
                desc_similarity = fuzz.token_set_ratio(
                    po_item.descricao.lower(), 
                    nfe_item.descricao.lower()
                )
                
                # Extract key words for better matching
                po_keywords = set(re.findall(r'\b\w{4,}\b', po_item.descricao.lower()))
                nfe_keywords = set(re.findall(r'\b\w{4,}\b', nfe_item.descricao.lower()))
                
                # Calculate keyword overlap
                if po_keywords and nfe_keywords:
                    overlap = len(po_keywords.intersection(nfe_keywords)) / len(po_keywords.union(nfe_keywords))
                    keyword_score = overlap * 100
                else:
                    keyword_score = 0
                
                # Final description score
                final_desc_score = max(desc_similarity, keyword_score)
                
                # Quantity match (0-100)
                qty_match = 0
                if po_item.quantidade and nfe_item.quantidade_comercial:
                    po_qty = float(po_item.quantidade)
                    nfe_qty = float(nfe_item.quantidade_comercial)
                    
                    if po_qty > 0 and nfe_qty > 0:
                        # Check if quantities are same or NFE qty is a subset of PO qty
                        if abs(po_qty - nfe_qty) < 0.01:  # Same quantity
                            qty_match = 100
                        elif nfe_qty < po_qty:  # Partial delivery
                            qty_match = (nfe_qty / po_qty) * 90  # Slightly penalize partial
                        else:
                            # NFE quantity is greater than PO
                            ratio = po_qty / nfe_qty
                            qty_match = ratio * 80  # More heavily penalize overdelivery
                
                # Price match (0-100)
                price_match = 0
                if po_item.preco_unitario and nfe_item.valor_unitario_comercial:
                    po_price = float(po_item.preco_unitario)
                    nfe_price = float(nfe_item.valor_unitario_comercial)
                    
                    if po_price > 0 and nfe_price > 0:
                        # Calculate price difference percentage
                        price_diff_pct = abs(po_price - nfe_price) / max(po_price, nfe_price)
                        
                        # Score based on how close prices are
                        if price_diff_pct <= 0.01:  # Within 1%
                            price_match = 100
                        elif price_diff_pct <= 0.05:  # Within 5%
                            price_match = 90
                        elif price_diff_pct <= 0.10:  # Within 10%
                            price_match = 75
                        elif price_diff_pct <= 0.20:  # Within 20%
                            price_match = 50
                        else:
                            price_match = max(0, 100 - (price_diff_pct * 500))  # Linear falloff
                
                # Combined item score (weighted: 60% description, 20% quantity, 20% price)
                item_score = (final_desc_score * 0.6) + (qty_match * 0.2) + (price_match * 0.2)
                
                if item_score > best_score:
                    best_score = item_score
                    best_match = {
                        "nfe_item": {
                            "id": nfe_item.id,
                            "description": nfe_item.descricao,
                            "quantity": nfe_item.quantidade_comercial,
                            "price": nfe_item.valor_unitario_comercial
                        },
                        "po_item": {
                            "id": po_item.id,
                            "description": po_item.descricao,
                            "quantity": po_item.quantidade,
                            "price": po_item.preco_unitario
                        },
                        "match_scores": {
                            "description": final_desc_score,
                            "quantity": qty_match,
                            "price": price_match,
                            "total": item_score
                        }
                    }
            
            # Only count matches that have a reasonable score
            if best_score >= 50:
                matched_items.append(best_match)
        
        # Calculate overall items score
        if total_po_items > 0:
            # Average score of matched items
            avg_match_score = sum(m["match_scores"]["total"] for m in matched_items) / total_po_items if matched_items else 0
            
            # Percentage of items matched
            match_coverage = len(matched_items) / total_po_items
            
            # Combined score (weighted by coverage)
            score_components["items_match"] = (avg_match_score / 100) * match_coverage * 40
        
        # 3. Total value match (30 points)
        if purchase_order.total_pedido_com_ipi and nfe.valor_total:
            po_value = float(purchase_order.total_pedido_com_ipi)
            nfe_value = float(nfe.valor_total)
            
            if po_value > 0 and nfe_value > 0:
                # Calculate value difference percentage
                value_diff_pct = abs(po_value - nfe_value) / max(po_value, nfe_value)
                
                # Score based on closeness of values
                if value_diff_pct <= 0.01:  # Within 1%
                    score_components["total_value_match"] = 30
                elif value_diff_pct <= 0.05:  # Within 5%
                    score_components["total_value_match"] = 25
                elif value_diff_pct <= 0.10:  # Within 10%
                    score_components["total_value_match"] = 20
                elif value_diff_pct <= 0.20:  # Within 20%
                    score_components["total_value_match"] = 15
                else:
                    # Partial NFE delivery - check if it's a subset of the PO value
                    if nfe_value < po_value:
                        # Calculate what percentage of the PO this NFE represents
                        coverage_pct = nfe_value / po_value
                        if coverage_pct >= 0.1:  # At least 10% of PO
                            score_components["total_value_match"] = coverage_pct * 15
        
        # 4. Date proximity (10 points)
        if purchase_order.dt_emis and nfe.data_emissao:
            # Calculate days difference
            days_diff = abs((nfe.data_emissao.date() - purchase_order.dt_emis).days)
            
            # Score based on date proximity
            if days_diff <= 7:  # Within 1 week
                score_components["date_proximity"] = 10
            elif days_diff <= 14:  # Within 2 weeks
                score_components["date_proximity"] = 8
            elif days_diff <= 30:  # Within 1 month
                score_components["date_proximity"] = 6
            elif days_diff <= 60:  # Within 2 months
                score_components["date_proximity"] = 4
            elif days_diff <= 90:  # Within 3 months
                score_components["date_proximity"] = 2
        
        # Calculate total score
        total_score = sum(score_components.values())
        
        # Format result
        result = {
            "nfe": {
                "id": nfe.id,
                "chave": nfe.chave,
                "numero": nfe.numero,
                "serie": nfe.serie,
                "emitente": nfe.emitente.nome if nfe.emitente else None,
                "cnpj": nfe.emitente.cnpj if nfe.emitente else None,
                "data_emissao": nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                "valor_total": nfe.valor_total
            },
            "purchase_order": {
                "id": purchase_order.id,
                "cod_pedc": purchase_order.cod_pedc,
                "fornecedor": purchase_order.fornecedor_descricao,
                "data_emissao": purchase_order.dt_emis.isoformat() if purchase_order.dt_emis else None,
                "valor_total": purchase_order.total_pedido_com_ipi
            },
            "score": total_score,
            "score_components": score_components,
            "matched_items": matched_items,
            "matched_items_count": len(matched_items),
            "total_items_count": total_po_items
        }
        
        results.append(result)
    
    # Sort results by score (descending)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results