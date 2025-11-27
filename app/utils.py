import logging
from collections import defaultdict
from datetime import datetime, date
from flask import jsonify, current_app, has_app_context
from app.models import NFEntry, PurchaseAdjustment, PurchaseItem, PurchaseOrder, Quotation
from app import db
from fuzzywuzzy import fuzz
from flask_mail import Mail, Message
from config import Config





def _parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        trimmed = value.strip()
        for fmt in ('%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d'):
            try:
                parsed = datetime.strptime(trimmed, fmt)
                parsed = parsed.replace(hour=12, minute=0, second=0, microsecond=0)
                return parsed.date()
            except ValueError:
                continue

    return None


def parse_xml(xml_data):
    import xml.etree.ElementTree as ET

    purchase_orders = []
    total_items = 0

    try:
        root = ET.fromstring(xml_data)

        for order in root.findall('.//TPED_COMPRA'):
            cod_pedc = order.find('COD_PEDC').text if order.find('COD_PEDC') is not None else None

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

            total_items += len(order_data['items'])
            purchase_orders.append(order_data)

        return {'purchase_orders': purchase_orders}
    except Exception:
        raise Exception('Failed to parse XML data')
  

def format_for_db(data):
    namespace = 'format_for_db'

    purchase_orders = data['purchase_orders']
    formatted_orders = []
    formatted_items = []
    formatted_adjustments = []

    try:

        for order in purchase_orders:
            raw_cod_pedc = order.get('cod_pedc')
            cod_pedc = raw_cod_pedc.strip() if isinstance(raw_cod_pedc, str) else raw_cod_pedc
            order_date = _parse_date(order.get('dt_emis'))

            formatted_orders.append({
                'cod_pedc': cod_pedc,
                'dt_emis': order_date,
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
                    'cod_pedc': cod_pedc,
                    'cod_emp1': order['cod_emp1'],
                    **adj
                })

            for item in order['items']:
                item_delivered = _parse_date(item.get('dt_entrega'))
                formatted_items.append({
                    'item_id': item['item_id'],
                    'dt_emis': order_date,
                    'descricao': item['descricao'],
                    'cod_pedc': cod_pedc,
                    'linha': item['linha'],
                    'quantidade': item['quantidade'],
                    'preco_unitario': item['preco_unitario'],
                    'total': item['total'],
                    'unidade_medida': item['unidade_medida'],
                    'dt_entrega': item_delivered,
                    'perc_ipi': item['perc_ipi'],
                    'tot_liquido_ipi': item['tot_liquido_ipi'],
                    'tot_descontos': item['tot_descontos'],
                    'tot_acrescimos': item['tot_acrescimos'],
                    'qtde_canc': item['qtde_canc'],
                    'qtde_canc_toler': item['qtde_canc_toler'],
                    'perc_toler': item['perc_toler'],
                    'qtde_atendida': item['qtde_atendida'],
                    'qtde_saldo': item['qtde_saldo'],
                    'purchase_order_id': cod_pedc,
                    'cod_emp1': item['cod_emp1']
                })

        return formatted_orders, formatted_items, formatted_adjustments
    except Exception:
        raise Exception('Failed to format data for DB')

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

def import_ruah(file_content):
    formatted_orders = []
    formatted_items = []
    formatted_adjustments = []
    itemcount = 0
    purchasecount = 0
    updated = 0

    try:
        data = parse_xml(file_content)

        formatted_orders, formatted_items, formatted_adjustments = format_for_db(data)

        # Group items and adjustments once to avoid repeatedly scanning entire lists per order.
        items_by_key = defaultdict(list)
        for item in formatted_items:
            key = (item['purchase_order_id'], item['cod_emp1'])
            items_by_key[key].append(item)

        adjustments_by_key = defaultdict(list)
        for adj in formatted_adjustments:
            key = (adj['cod_pedc'], adj['cod_emp1'])
            adjustments_by_key[key].append(adj)

        # Bulk fetch existing orders
        incoming_cod_pedcs = {o['cod_pedc'] for o in formatted_orders}
        existing_orders = PurchaseOrder.query.filter(PurchaseOrder.cod_pedc.in_(incoming_cod_pedcs)).all()
        existing_orders_map = {(o.cod_pedc, o.cod_emp1): o for o in existing_orders}

        orders_to_update_ids = []
        processed_orders = []

        for order_data in formatted_orders:
            order_key = (order_data['cod_pedc'], order_data['cod_emp1'])
            existing_order = existing_orders_map.get(order_key)

            order_details = {
                'cod_pedc': order_data['cod_pedc'],
                'dt_emis': order_data['dt_emis'],
                'fornecedor_id': order_data['fornecedor_id'],
                'fornecedor_descricao': order_data['fornecedor_descricao'],
                'total_bruto': order_data['total_bruto'],
                'total_liquido': order_data['total_liquido'],
                'total_liquido_ipi': order_data['total_liquido_ipi'],
                'total_pedido_com_ipi': order_data['total_pedido_com_ipi'],
                'posicao': order_data['posicao'],
                'posicao_hist': order_data['posicao_hist'],
                'observacao': order_data['observacao'],
                'contato': order_data['contato'],
                'func_nome': order_data['func_nome'],
                'cf_pgto': order_data['cf_pgto'],
                'cod_emp1': order_data['cod_emp1'],
            }

            if existing_order:
                for field, value in order_details.items():
                    setattr(existing_order, field, value)
                orders_to_update_ids.append(existing_order.id)
                order = existing_order
                updated += 1
            else:
                order = PurchaseOrder(**order_details)
                db.session.add(order)
            
            processed_orders.append((order, order_data))
            purchasecount += 1

        # Bulk delete items and adjustments for updated orders
        if orders_to_update_ids:
            PurchaseItem.query.filter(PurchaseItem.purchase_order_id.in_(orders_to_update_ids)).delete(synchronize_session=False)
            PurchaseAdjustment.query.filter(PurchaseAdjustment.purchase_order_id.in_(orders_to_update_ids)).delete(synchronize_session=False)

        for order, order_data in processed_orders:
            order_key = (order_data['cod_pedc'], order_data['cod_emp1'])
            order_items = items_by_key.get(order_key, [])
            order_adjustments = adjustments_by_key.get(order_key, [])

            for item_data in order_items:
                item = PurchaseItem(
                    purchase_order=order,
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

            for adj_data in order_adjustments:
                adjustment = PurchaseAdjustment(
                    purchase_order=order,
                    cod_pedc=adj_data['cod_pedc'],
                    cod_emp1=adj_data['cod_emp1'],
                    tp_apl=adj_data['tp_apl'],
                    tp_dctacr1=adj_data['tp_dctacr1'],
                    tp_vlr1=adj_data['tp_vlr1'],
                    vlr1=adj_data['vlr1'],
                    order_index=adj_data['order_index']
                )
                db.session.add(adjustment)

            order.is_fulfilled = check_order_fulfillment_memory(order_items)

        db.session.commit()
        message = 'Data imported successfully purchases {}, items {}, updated {}'.format(
            purchasecount - updated,
            itemcount,
            updated,
        )
        return jsonify({'message': message}), 201
    except Exception:
        db.session.rollback()
        raise Exception('Failed to import RUAH data')

        

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

    # Bulk fetch existing entries
    cod_pedcs = {item['cod_pedc'] for item in unique_combinations.values()}
    existing_entries = NFEntry.query.filter(NFEntry.cod_pedc.in_(cod_pedcs)).all()
    existing_map = {(e.cod_emp1, e.cod_pedc, e.linha, e.num_nf): e for e in existing_entries}

    for key, item_data in unique_combinations.items():
        existing_entry = existing_map.get(key)

        if existing_entry:
            has_changes = False
            if existing_entry.dt_ent != item_data.get('dt_ent'):
                existing_entry.dt_ent = item_data.get('dt_ent', '')
                has_changes = True
                
            if hasattr(existing_entry, 'qtde') and existing_entry.qtde != item_data.get('qtde'):
                existing_entry.qtde = item_data.get('qtde')
                has_changes = True
            
            if has_changes:
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

    cod_cots = {q['cod_cot'] for q in quotations}
    existing_quotations = Quotation.query.filter(Quotation.cod_cot.in_(cod_cots)).all()
    existing_map = {(q.cod_cot, q.item_id, str(q.fornecedor_id)): q for q in existing_quotations}

    for quotation_data in quotations:
        # Check if quotation already exists
        key = (quotation_data['cod_cot'], quotation_data['item_id'], str(quotation_data['fornecedor_id']))
        existing_quotation = existing_map.get(key)
        
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
    suppliers_data = []
    
    for g_fornec in root.findall('.//G_FORNEC'):
        suppliers_data.append({
            'cod_for': g_fornec.findtext('COD_FOR'),
            'tip_forn': g_fornec.findtext('TIP_FORN'),
            'conta_itens': g_fornec.findtext('CONTA_ITENS'),
            'insc_est': g_fornec.findtext('INSC_EST'),
            'insc_mun': g_fornec.findtext('INSC_MUN'),
            'email': g_fornec.findtext('EMAIL'),
            'tel_ddd_tel_telefone': g_fornec.findtext('TEL_DDD_TEL_TELEFONE'),
            'endereco': g_fornec.findtext('ENDERECO'),
            'cep': g_fornec.findtext('CEP'),
            'cidade': g_fornec.findtext('CIDADE'),
            'uf': g_fornec.findtext('UF'),
            'id_for': g_fornec.findtext('ID_FOR'),
            'nvl_forn_cnpj_forn_cpf': g_fornec.findtext('NVL_FORN_CNPJ_FORN_CPF'),
            'descricao': g_fornec.findtext('DESCRICAO'),
            'bairro': g_fornec.findtext('BAIRRO'),
            'cf_fax': g_fornec.findtext('CF_FAX')
        })

    cod_fors = {s['cod_for'] for s in suppliers_data if s['cod_for']}
    existing_suppliers = Supplier.query.filter(Supplier.cod_for.in_(cod_fors)).all()
    existing_map = {s.cod_for: s for s in existing_suppliers}

    new_count = 0
    updated_count = 0
    
    for s_data in suppliers_data:
        cod_for = s_data['cod_for']
        if not cod_for:
            continue
            
        existing_supplier = existing_map.get(cod_for)
        
        if existing_supplier:
            existing_supplier.tip_forn = s_data['tip_forn']
            existing_supplier.conta_itens = s_data['conta_itens']
            existing_supplier.insc_est = s_data['insc_est']
            existing_supplier.insc_mun = s_data['insc_mun']
            existing_supplier.email = s_data['email']
            existing_supplier.tel_ddd_tel_telefone = s_data['tel_ddd_tel_telefone']
            existing_supplier.endereco = s_data['endereco']
            existing_supplier.cep = s_data['cep']
            existing_supplier.cidade = s_data['cidade']
            existing_supplier.uf = s_data['uf']
            existing_supplier.nvl_forn_cnpj_forn_cpf = s_data['nvl_forn_cnpj_forn_cpf']
            existing_supplier.descricao = s_data['descricao']
            existing_supplier.bairro = s_data['bairro']
            existing_supplier.cf_fax = s_data['cf_fax']
            updated_count += 1
        else:
            # Create new supplier
            supplier = Supplier(**s_data)
            db.session.add(supplier)
            new_count += 1
            
    db.session.commit()
    return jsonify({
        'message': f'Suppliers imported: {len(suppliers_data)} total ({new_count} new, {updated_count} updated)'
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

def check_order_fulfillment_memory(items_data):
    """Check fulfillment based on item data dicts."""
    if not items_data:
        return False

    for item in items_data:
        quantity = item.get('quantidade')
        if quantity is None:
            return False
        if quantity <= 0:
            continue

        attended = item.get('qtde_atendida') or 0.0
        canceled = item.get('qtde_canc') or 0.0
        canceled_tolerance = item.get('qtde_canc_toler') or 0.0
        total_canceled = canceled + canceled_tolerance

        if attended >= quantity:
            continue
        if total_canceled >= quantity:
            continue
        if attended + total_canceled >= quantity:
            continue

        return False

    return True

def score_purchase_nfe_match(cod_pedc, nfe_id=None, cod_emp1=None):
    """
    Advanced matching for Purchase Orders vs NFEs.
    Handles:
    1. Split Shipments (1 PO -> Multiple NFes) - via Composite Matching
    2. Consolidated Invoices (Multiple POs -> 1 NFe) - via Subset Matching
    3. Fuzzy Supplier Matching
    """
    from app.models import PurchaseOrder, PurchaseItem, NFEData, NFEItem, NFEEmitente, Supplier
    from fuzzywuzzy import fuzz
    from datetime import timedelta
    import re
    from itertools import combinations

    def clean_digits(s):
        return ''.join(filter(str.isdigit, str(s))) if s else ""

    def extract_po_numbers(text):
        """Extracts potential PO numbers from NFe observation fields."""
        if not text: return []
        # Look for patterns like "PED 36000", "PEDIDO: 36000", "PO 36000"
        return re.findall(r'(?:PED|PEDIDO|PO|ORDEM)[\s\.:]*(\d+)', text, re.IGNORECASE)

    def get_token_overlap(str1, str2):
        """Calculate keyword overlap between two item descriptions."""
        s1 = set(re.findall(r'\b\w{3,}\b', str1.lower()))
        s2 = set(re.findall(r'\b\w{3,}\b', str2.lower()))
        if not s1 or not s2: return 0
        return len(s1.intersection(s2)) / len(s1.union(s2))

    # --- 1. Fetch Data ---
    purchase_order = PurchaseOrder.query.filter_by(cod_pedc=str(cod_pedc), cod_emp1=cod_emp1).first()
    if not purchase_order:
        return {"error": "Purchase order not found"}

    purchase_items = PurchaseItem.query.filter_by(purchase_order_id=purchase_order.id).all()
    if not purchase_items:
        return {"error": "No items found for this purchase order"}

    supplier = Supplier.query.filter_by(cod_for=str(purchase_order.fornecedor_id)).first()
    supplier_cnpj = clean_digits(supplier.nvl_forn_cnpj_forn_cpf) if supplier else None

    adjustments = getattr(purchase_order, 'adjustments', [])
    base_total = purchase_order.total_pedido_com_ipi or 0
    po_adjusted_total = apply_adjustments(base_total, adjustments)

    # --- 2. Candidate Selection Strategy ---
    nfe_candidates = []

    if nfe_id:
        nfe = NFEData.query.get(nfe_id)
        if nfe: nfe_candidates = [nfe]
    else:
        # A. CNPJ Root Match (First 8 digits)
        if supplier_cnpj:
            cnpj_root = supplier_cnpj[:8]
            cnpj_matches = NFEData.query.join(NFEEmitente).filter(
                NFEEmitente.cnpj.like(f"{cnpj_root}%"),
                NFEData.data_emissao.between(
                    purchase_order.dt_emis - timedelta(days=10), # Slight buffer before
                    purchase_order.dt_emis + timedelta(days=120)
                )
            ).all()
            nfe_candidates.extend(cnpj_matches)

        # B. PO Number Explicit Reference (Check infAdic/infCpl)
        # Assuming NFEData has a field 'inf_adicional' or similar containing the XML <infCpl>
        ref_matches = NFEData.query.filter(
            NFEData.informacoes_adicionais.ilike(f"%{cod_pedc}%"),
            NFEData.data_emissao >= purchase_order.dt_emis
        ).all()
        for m in ref_matches:
            if m not in nfe_candidates:
                nfe_candidates.append(m)

        # C. Name Fuzzy Match (Fallback if CNPJ fails or is empty)
        if not nfe_candidates and purchase_order.fornecedor_descricao:
            date_range_nfes = NFEData.query.filter(
                NFEData.data_emissao.between(
                    purchase_order.dt_emis - timedelta(days=10),
                    purchase_order.dt_emis + timedelta(days=120)
                )
            ).all()
            
            for nfe in date_range_nfes:
                if nfe.emitente and nfe.emitente.nome:
                    ratio = fuzz.token_sort_ratio(
                        purchase_order.fornecedor_descricao.lower(), 
                        nfe.emitente.nome.lower()
                    )
                    if ratio > 75: 
                        nfe_candidates.append(nfe)

    # Dictionary to store structured NFe objects for combination logic
    candidate_structs = []

    # --- 3. Individual Scoring ---
    for nfe in nfe_candidates:
        score_components = {
            "supplier": 0, "items": 0, "value": 0, "date": 0, "reference": 0
        }
        
        # A. Supplier (20 pts)
        nfe_cnpj = clean_digits(nfe.emitente.cnpj) if nfe.emitente else ""
        if supplier_cnpj and nfe_cnpj:
            if supplier_cnpj == nfe_cnpj:
                score_components["supplier"] = 20
            elif supplier_cnpj[:8] == nfe_cnpj[:8]:
                score_components["supplier"] = 18 # Branch difference
            elif supplier_cnpj[:12] == nfe_cnpj[:12]: # Only check digit difference
                score_components["supplier"] = 19
        else:
            # Fuzzy Name Fallback
            name_sim = fuzz.token_sort_ratio(purchase_order.fornecedor_descricao, nfe.emitente.nome)
            if name_sim > 80: score_components["supplier"] = 15

        # B. Reference Check (Bonus 10 pts)
        # Check if PO number appears in NFe remarks
        if nfe.informacoes_adicionais:
            found_pos = extract_po_numbers(nfe.informacoes_adicionais)
            if str(cod_pedc) in found_pos:
                score_components["reference"] = 10

        # C. Items Matching (40 pts) & D. Value (20 pts)
        # We process items to build a mapping for the Composite step later
        matched_lines = []
        nfe_items_pool = [
            {
                'id': i.id, 
                'desc': i.descricao, 
                'qty': float(i.quantidade_comercial), 
                'val': float(i.valor_unitario_comercial),
                'used': 0.0
            } 
            for i in nfe.itens
        ]

        total_po_lines_matched = 0
        
        for po_item in purchase_items:
            po_qty = float(po_item.quantidade)
            best_line_match = None
            highest_line_score = 0
            
            for n_idx, n_item in enumerate(nfe_items_pool):
                # Text Similarity
                text_score = fuzz.token_set_ratio(po_item.descricao, n_item['desc'])
                overlap_score = get_token_overlap(po_item.descricao, n_item['desc']) * 100
                final_text_score = max(text_score, overlap_score)
                
                if final_text_score < 60: continue

                # Price Check
                price_diff = abs(float(po_item.preco_unitario) - n_item['val'])
                price_score = 100 if price_diff < 0.05 else max(0, 100 - (price_diff * 10))

                # Combined Line Score
                line_score = (final_text_score * 0.7) + (price_score * 0.3)
                
                if line_score > highest_line_score:
                    highest_line_score = line_score
                    best_line_match = n_idx

            if best_line_match is not None:
                # We found a matching product description/price
                n_item = nfe_items_pool[best_line_match]
                
                # Logic: Is this a Split Shipment or a Consolidated Invoice?
                matched_qty = min(po_qty, n_item['qty'])
                
                # Record the match
                matched_lines.append({
                    "po_item_id": po_item.id,
                    "nfe_item_id": n_item['id'],
                    "qty_matched": matched_qty,
                    "po_qty": po_qty,
                    "line_score": highest_line_score
                })
                
                if highest_line_score > 80:
                    total_po_lines_matched += 1

        # Calculate Item Score based on Coverage
        if len(purchase_items) > 0:
            coverage = total_po_lines_matched / len(purchase_items)
            score_components["items"] = coverage * 40

        # Value Score (Context Aware)
        po_total = float(po_adjusted_total or 0)
        nfe_total = float(nfe.valor_total or 0)
        
        if po_total > 0:
            if abs(po_total - nfe_total) < 1.0:
                score_components["value"] = 20 # Perfect Match
            elif nfe_total < po_total:
                # Partial Shipment (Split)
                ratio = nfe_total / po_total
                score_components["value"] = ratio * 15 
            elif nfe_total > po_total:
                # Multi-PO Invoice (Consolidated)
                # If we matched all items perfectly, full points for value
                # even if NFe total is higher
                if score_components["items"] > 35:
                     score_components["value"] = 20
                else:
                    score_components["value"] = 5 # Penalize mismatch

        # Date Score (10 pts)
        if nfe.numero == '47163' or nfe.numero == '457203':
            print("Debug NFe 457203 Date:", nfe.data_emissao, purchase_order.dt_emis)
        if nfe.data_emissao:
            days =  abs((nfe.data_emissao.date() - purchase_order.dt_emis).days)
            if 0 <= days <= 10: score_components["date"] = 10
            elif 0 <= days <= 30: score_components["date"] = 8
            elif 30 < days <= 90: score_components["date"] = 5
            else: score_components["date"] = 0

        final_score = sum(score_components.values())
        
        # Store structured data for the next phase
        struct = {
            "nfe_obj": nfe,
            "id": nfe.id,
            "score": final_score,
            "components": score_components,
            "matched_lines": matched_lines,
            "nfe_total": nfe_total
        }
        candidate_structs.append(struct)

    # --- 4. Composite Matching (The "Split Shipment" Logic) ---
    # Try to combine top partial matches to see if they form a complete PO
    
    # Filter for candidates that are likely partials (e.g., score between 30 and 90)
    partial_candidates = [c for c in candidate_structs if 30 < c['score'] < 95]
    
    # We limit combinations to avoid performance hits (max group size 3)
    composite_results = []
    
    if len(partial_candidates) >= 2:
        # Sort by date to prioritize consecutive invoices
        partial_candidates.sort(key=lambda x: x['nfe_obj'].data_emissao)
        
        # Try combining 2 or 3 invoices
        for r in range(2, min(4, len(partial_candidates) + 1)):
            for combo in combinations(partial_candidates, r):
                
                # Check 1: Supplier must be same for all in combo
                if len(set(c['nfe_obj'].emitente.cnpj for c in combo if c['nfe_obj'].emitente)) > 1:
                    continue

                # Check 2: Sum of values matches PO?
                combo_total_val = sum(c['nfe_total'] for c in combo)
                po_total = float(po_adjusted_total or 0)
                
                val_match = False
                if abs(combo_total_val - po_total) < (po_total * 0.05): # 5% tolerance
                    val_match = True
                    
                #todo calculo errado, 1920 == 1230 em ped 35500

                # Check 3: Item Quantity Aggregation
                # We need to sum up the quantities matched across these NFEs for each PO item
                item_aggregator = {} # {po_item_id: total_qty_found}
                
                for cand in combo:
                    for line in cand['matched_lines']:
                        pid = line['po_item_id']
                        item_aggregator[pid] = item_aggregator.get(pid, 0) + line['qty_matched']
                
                # Verify if aggregation fulfills the PO
                items_fulfilled = 0
                for po_item in purchase_items:
                    req_qty = float(po_item.quantidade)
                    found_qty = item_aggregator.get(po_item.id, 0)
                    if abs(req_qty - found_qty) < 0.1: # Floating point tolerance
                        items_fulfilled += 1
                
                percent_fulfilled = items_fulfilled / len(purchase_items) if purchase_items else 0
                
                if percent_fulfilled > 0.9 or (val_match and percent_fulfilled > 0.7):
                    # Found a Valid Combination!
                    composite_score = 98 # High confidence
                    composite_entry = {
                        "type": "composite",
                        "nfes": [
                            {
                                "id": c['id'], 
                                "numero": c['nfe_obj'].numero,
                                "val": c['nfe_total'],
                                "individual_score": c['score']
                            } 
                            for c in combo
                        ],
                        "score": composite_score,
                        "reason": f"Combined {len(combo)} NFEs perfectly match PO quantity/value."
                    }
                    composite_results.append(composite_entry)

    # --- 5. Finalize Results ---
    # Convert individual structs to output format
    final_output = []
    
    # Add individual scores
    for c in candidate_structs:
        final_output.append({
            "type": "single",
            "nfe": {
                "id": c['id'],
                "numero": c['nfe_obj'].numero,
                "chave": c['nfe_obj'].chave,
                "emitente": c['nfe_obj'].emitente.nome,
                "valor": c['nfe_total']
            },
            "score": c['score'],
            "details": c['components'],
            "warning": "Partial Match" if c['score'] < 100 and c['score'] > 50 else None
        })

    # Add composite scores to the top
    for comp in composite_results:
        final_output.append(comp)

    # Sort descending by score
    final_output.sort(key=lambda x: x['score'], reverse=True)
    
    return final_output