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

def score_purchase_nfe_match(cod_pedc, cod_emp1):
    """
    Find and score NFEs that might fulfill a purchase order.
    
    Scoring Strategy (0-100 points):
    - CNPJ Match (0-30 points): Supplier CNPJ matching
    - Item Matching (0-35 points): Description, quantity, price matching
    - Value Match (0-20 points): Total value alignment  
    - PO Reference (0-15 points): PO number in NFe additional info
    
    Handles:
    - Fully fulfilled orders (all items have qtde_atendida == quantidade)
    - Partially fulfilled orders (some items still need NFes)
    - Single NFe fulfilling entire order
    - Multiple NFes fulfilling one order over time
    - Different CNPJ roots (subsidiary/branch scenarios) - uses stricter matching
    
    Args:
        cod_pedc: The purchase order code
        cod_emp1: The company code
        
    Returns:
        List of NFEs scored by how well they match the purchase order.
    """
    import re
    from fuzzywuzzy import fuzz
    from app.models import PurchaseOrder, PurchaseItem, NFEData, NFEItem, NFEEmitente
    
    # Validate required parameters
    if not cod_pedc:
        return {'error': 'cod_pedc is required'}
    if not cod_emp1:
        return {'error': 'cod_emp1 is required'}
    
    # Fetch the purchase order
    purchase_order = PurchaseOrder.query.filter_by(
        cod_pedc=str(cod_pedc),
        cod_emp1=str(cod_emp1)
    ).first()
    
    if not purchase_order:
        return {'error': f'Purchase order {cod_pedc} not found for company {cod_emp1}'}
    
    purchase_items = PurchaseItem.query.filter_by(
        purchase_order_id=purchase_order.id
    ).all()
    
    if not purchase_items:
        return {'error': f'No items found for purchase order {cod_pedc}'}
    
    po_data = {
        'id': purchase_order.id,
        'cod_pedc': purchase_order.cod_pedc,
        'fornecedor': purchase_order.fornecedor_descricao or '',
        'fornecedor_id': purchase_order.fornecedor_id,
        'valor_total': purchase_order.total_liquido or purchase_order.total_bruto or 0,
        'dt_emis': purchase_order.dt_emis,
        'is_fulfilled': purchase_order.is_fulfilled,
        'itens': []
    }
    
    unfulfilled_items = []
    partially_fulfilled_items = []
    fulfilled_items = []
    
    for item in purchase_items:
        qty = float(item.quantidade or 0)
        atendida = float(item.qtde_atendida or 0)
        remaining = max(0, qty - atendida)
        
        item_data = {
            'id': item.id,
            'descricao': item.descricao or '',
            'codigo': item.item_id or '',
            'quantidade': qty,
            'qtde_atendida': atendida,
            'qtde_remaining': remaining,
            'preco_unitario': float(item.preco_unitario or 0),
            'valor_total': qty * float(item.preco_unitario or 0),
            'valor_remaining': remaining * float(item.preco_unitario or 0)
        }
        
        po_data['itens'].append(item_data)
        
        if remaining <= 0:
            fulfilled_items.append(item_data)
        elif atendida > 0:
            partially_fulfilled_items.append(item_data)
        else:
            unfulfilled_items.append(item_data)
    
    # Calculate remaining value
    total_remaining_value = sum(i['valor_remaining'] for i in po_data['itens'])
    
    supplier_name = po_data['fornecedor'].lower()
    
    all_nfes = NFEData.query.all()
    
    # Helper functions
    def clean_digits(text):
        if not text:
            return ""
        return re.sub(r'\D', '', str(text))
    
    def get_cnpj_root(cnpj):
        """Get first 8 digits of CNPJ (company root)"""
        digits = clean_digits(cnpj)
        return digits[:8] if len(digits) >= 8 else digits
    
    def extract_po_numbers(text):
        """Extract potential PO numbers from NFe text"""
        if not text:
            return set()
        patterns = [
            r'(?:pedido|ped|po|order|ord|pc)[:\s#]*(\d{4,})',
            r'(?:p/c)[:\s#]*(\d{4,})',
            r'\b(\d{5,8})\b',
        ]
        numbers = set()
        text_lower = str(text).lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            numbers.update(matches)
        return numbers
    
    def match_items(po_items, nfe_items_db, use_original_qty=False):
        """
        Match PO items to NFE items and calculate match quality.
        Args:
            po_items: List of purchase order items
            nfe_items_db: List of NFE items from database
            use_original_qty: If True, use original quantidade instead of remaining
        Returns: (matched_items, total_match_score, coverage_ratio)
        """
        matches = []
        matched_nfe_ids = set()
        
        for po_item in po_items:
            # Use original quantity for fulfilled orders, remaining for unfulfilled
            po_qty = po_item['quantidade'] if use_original_qty else po_item['qtde_remaining']
            if po_qty <= 0:
                continue
                
            po_desc = po_item['descricao'].lower()
            po_price = po_item['preco_unitario']
            
            best_match = None
            best_score = 0
            
            for nfe_item in nfe_items_db:
                if nfe_item.id in matched_nfe_ids:
                    continue
                    
                nfe_desc = (nfe_item.descricao or '').lower()
                nfe_qty = float(nfe_item.quantidade_comercial or 0)
                nfe_price = float(nfe_item.valor_unitario_comercial or 0)
                
                # Description match (0-100)
                desc_score = 0
                if po_desc and nfe_desc:
                    desc_score = max(
                        fuzz.token_set_ratio(po_desc, nfe_desc),
                        fuzz.token_sort_ratio(po_desc, nfe_desc),
                        fuzz.partial_ratio(po_desc, nfe_desc)
                    )
                
                # Quantity match (0-100)
                qty_score = 0
                if po_qty > 0:
                    qty_ratio = min(nfe_qty, po_qty) / po_qty
                    if qty_ratio >= 0.95:
                        qty_score = 100
                    elif qty_ratio >= 0.8:
                        qty_score = 85
                    elif qty_ratio >= 0.5:
                        qty_score = 70
                    else:
                        qty_score = qty_ratio * 100
                
                # Price match (0-100)
                price_score = 0
                if po_price > 0 and nfe_price > 0:
                    price_diff_pct = abs(po_price - nfe_price) / po_price * 100
                    if price_diff_pct < 1:
                        price_score = 100
                    elif price_diff_pct < 5:
                        price_score = 90
                    elif price_diff_pct < 10:
                        price_score = 80
                    elif price_diff_pct < 20:
                        price_score = 60
                    elif price_diff_pct < 50:
                        price_score = 30
                    else:
                        price_score = 0
                
                # Skip if both description AND price match are too low
                # Allow low description match if price matches very well (same product, different naming)
                if desc_score < 35 and price_score < 80:
                    continue
                if desc_score < 25:  
                    continue
                
                # Combined score: adjust weights based on match quality
                # If description is weak but price is strong, trust price more
                if desc_score < 45 and price_score >= 80:
                    combined = (desc_score * 0.25) + (qty_score * 0.35) + (price_score * 0.40)
                else:
                    combined = (desc_score * 0.50) + (qty_score * 0.30) + (price_score * 0.20)
                
                if combined > best_score:
                    best_score = combined
                    best_match = {
                        'po_item_id': po_item['id'],
                        'po_item_desc': po_item['descricao'],
                        'nfe_item_id': nfe_item.id,
                        'nfe_item_desc': nfe_item.descricao,
                        'desc_score': desc_score,
                        'qty_score': qty_score,
                        'price_score': price_score,
                        'combined_score': round(combined, 2),
                        'po_qty': po_qty,
                        'nfe_qty': nfe_qty,
                        'po_price': po_price,
                        'nfe_price': nfe_price
                    }
            
            if best_match and best_match['combined_score'] >= 45:
                matches.append(best_match)
                matched_nfe_ids.add(best_match['nfe_item_id'])
        
        # Calculate coverage - use appropriate quantity based on mode
        if use_original_qty:
            items_to_match_count = len([i for i in po_items if i['quantidade'] > 0])
        else:
            items_to_match_count = len([i for i in po_items if i['qtde_remaining'] > 0])
        coverage = len(matches) / items_to_match_count if items_to_match_count > 0 else 0
        avg_score = sum(m['combined_score'] for m in matches) / len(matches) if matches else 0
        
        return matches, avg_score, coverage
    
    results = []
    po_num_clean = clean_digits(str(cod_pedc))
    
    for nfe in all_nfes:
        # Get NFE emitente info
        emitente = NFEEmitente.query.filter_by(nfe_id=nfe.id).first()
        nfe_supplier = emitente.nome if emitente else ''
        nfe_cnpj = emitente.cnpj if emitente else ''
        
        # Get NFE items
        nfe_items_db = NFEItem.query.filter_by(nfe_id=nfe.id).all()
        
        nfe_value = float(nfe.valor_total or 0)
        nfe_info_adic = str(nfe.informacoes_adicionais or '').lower()
        
        score = 0
        breakdown = {}
        
        # === 1. CNPJ/Supplier Match (0-30 points) ===
        cnpj_score = 0
        supplier_match_type = 'none'
        
        # Check supplier name similarity
        supplier_similarity = 0
        if nfe_supplier and supplier_name:
            supplier_similarity = fuzz.token_set_ratio(nfe_supplier.lower(), supplier_name)
        
        if supplier_similarity >= 85:
            cnpj_score = 30
            supplier_match_type = 'exact_name'
        elif supplier_similarity >= 70:
            cnpj_score = 25
            supplier_match_type = 'high_similarity'
        elif supplier_similarity >= 55:
            cnpj_score = 15
            supplier_match_type = 'partial_name'
        elif supplier_similarity >= 40:
            # Possible subsidiary/branch - will need stronger item matching
            cnpj_score = 5
            supplier_match_type = 'possible_related'
        
        score += cnpj_score
        breakdown['cnpj_score'] = cnpj_score
        breakdown['supplier_match_type'] = supplier_match_type
        breakdown['supplier_similarity'] = supplier_similarity
        
        # === 2. PO Reference in NFe (0-15 points) ===
        po_ref_score = 0
        po_ref_type = 'none'
        
        nfe_po_refs = extract_po_numbers(nfe_info_adic)
        
        if po_num_clean and po_num_clean in nfe_info_adic:
            po_ref_score = 15
            po_ref_type = 'exact_in_info'
        elif po_num_clean and any(po_num_clean == ref for ref in nfe_po_refs):
            po_ref_score = 12
            po_ref_type = 'extracted_exact'
        elif po_num_clean and any(po_num_clean in ref for ref in nfe_po_refs):
            po_ref_score = 8
            po_ref_type = 'extracted_partial'
        
        score += po_ref_score
        breakdown['po_ref_score'] = po_ref_score
        breakdown['po_ref_type'] = po_ref_type
        
        # === 3. Item Matching (0-35 points) ===
        # Always match against ALL items to find historical fulfillments
        # Use original quantities for fulfilled items
        all_items = po_data['itens']
        
        # Match against all items using original quantities
        item_matches, avg_match_quality, coverage = match_items(all_items, nfe_items_db, use_original_qty=True)
        
        # Item score based on coverage and quality
        # coverage * 20 (up to 20 points) + quality * 15 / 100 (up to 15 points)
        item_score = (coverage * 20) + (avg_match_quality * 15 / 100)
        
        score += item_score
        breakdown['item_score'] = round(item_score, 2)
        breakdown['items_matched'] = len(item_matches)
        breakdown['items_to_match'] = len(all_items)
        breakdown['coverage_pct'] = round(coverage * 100, 2)
        breakdown['avg_match_quality'] = round(avg_match_quality, 2)
        
        # === 4. Value Match (0-20 points) ===
        value_score = 0
        value_match_type = 'none'
        
        # Compare against remaining value or total value
        compare_value = total_remaining_value if total_remaining_value > 0 else po_data['valor_total']
        
        if compare_value > 0 and nfe_value > 0:
            value_diff_pct = abs(nfe_value - compare_value) / compare_value * 100
            
            if value_diff_pct < 1:
                value_score = 20
                value_match_type = 'exact'
            elif value_diff_pct < 3:
                value_score = 18
                value_match_type = 'very_close'
            elif value_diff_pct < 5:
                value_score = 15
                value_match_type = 'close'
            elif value_diff_pct < 10:
                value_score = 12
                value_match_type = 'near'
            elif value_diff_pct < 20:
                value_score = 8
                value_match_type = 'approximate'
            elif nfe_value < compare_value:
                # Partial fulfillment - NFe is portion of remaining
                portion = nfe_value / compare_value
                if portion >= 0.2:
                    value_score = 5
                    value_match_type = 'partial'
        
        score += value_score
        breakdown['value_score'] = value_score
        breakdown['value_match_type'] = value_match_type
        breakdown['nfe_value'] = nfe_value
        breakdown['compare_value'] = round(compare_value, 2)
        breakdown['value_diff_pct'] = round(value_diff_pct, 2) if compare_value > 0 and nfe_value > 0 else None
        
        # === 5. Date Proximity Bonus (0-10 points) ===
        date_bonus = 0
        days_from_po = None
        po_date = po_data.get('dt_emis')
        nfe_date = nfe.data_emissao.date() if nfe.data_emissao else None
        
        if po_date and nfe_date:
            days_from_po = abs((nfe_date - po_date).days)
            # NFE should be after PO date (or within a few days before for corrections)
            if nfe_date >= po_date:
                if days_from_po <= 7:
                    date_bonus = 10
                elif days_from_po <= 14:
                    date_bonus = 8
                elif days_from_po <= 30:
                    date_bonus = 6
                elif days_from_po <= 60:
                    date_bonus = 4
                elif days_from_po <= 90:
                    date_bonus = 2
            else:
                # NFE before PO - less likely to be correct, small penalty
                if days_from_po <= 7:  # Small allowance for pre-dated NFEs
                    date_bonus = 2
        
        score += date_bonus
        breakdown['date_bonus'] = date_bonus
        breakdown['days_from_po'] = days_from_po
        
        # === Apply penalties/bonuses ===
        
        # Bonus: If supplier match is weak but items match very well, boost score
        if supplier_match_type in ['possible_related', 'none'] and coverage >= 0.8 and avg_match_quality >= 70:
            bonus = 10
            score += bonus
            breakdown['weak_supplier_strong_items_bonus'] = bonus
        
        # Penalty: If supplier doesn't match at all and items are weak
        if supplier_similarity < 30 and coverage < 0.5:
            score = score * 0.5
            breakdown['low_confidence_penalty'] = True
        
        # Only include NFEs with meaningful scores
        if score >= 10:
            match_quality = 'high' if score >= 70 else 'medium' if score >= 45 else 'low'
            
            results.append({
                'nfe_id': nfe.id,
                'nfe_number': nfe.numero,
                'nfe_chave': nfe.chave,
                'nfe_value': nfe_value,
                'nfe_date': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                'nfe_supplier': nfe_supplier,
                'nfe_cnpj': nfe_cnpj,
                'score': round(score, 2),
                'max_possible_score': 110,  # Now up to 110 with date bonus
                'match_quality': match_quality,
                'breakdown': breakdown,
                'item_matches': item_matches
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # === COMBINE NFEs FROM SAME SUPPLIER ===
    # Group NFEs from the same supplier within 45 days of each other
    from datetime import timedelta
    from collections import defaultdict
    
    MAX_DAYS_FROM_PO = 120  # Allow NFEs up to 120 days after PO
    MAX_DAYS_BETWEEN_NFES = 45  # NFEs must be within 45 days of each other
    po_date = po_data.get('dt_emis')
    
    combined_results = []
    
    # Group results by supplier (using CNPJ as key)
    supplier_groups = defaultdict(list)
    for r in results:
        supplier_key = r.get('nfe_cnpj', '') or r.get('nfe_supplier', '')
        if supplier_key:
            supplier_groups[supplier_key].append(r)
    
    # Track which NFEs have been combined
    combined_nfe_ids = set()
    
    for supplier_key, supplier_nfes in supplier_groups.items():
        if len(supplier_nfes) < 2:
            continue
            
        # Sort by date
        supplier_nfes_with_date = []
        for nfe in supplier_nfes:
            nfe_date = None
            if nfe.get('nfe_date'):
                try:
                    from datetime import datetime
                    if isinstance(nfe['nfe_date'], str):
                        nfe_date = datetime.fromisoformat(nfe['nfe_date']).date()
                    else:
                        nfe_date = nfe['nfe_date']
                except:
                    pass
            supplier_nfes_with_date.append((nfe, nfe_date))
        
        # Sort by score (highest first) to prioritize best matches for combination
        supplier_nfes_with_date.sort(key=lambda x: x[0]['score'], reverse=True)
        
        # Get PO value for limiting combined value
        po_value = po_data.get('valor_total', 0)
        MAX_COMBINED_VALUE_RATIO = 2.0  # Combined value shouldn't exceed 200% of PO value
        
        # Find groups of NFEs that can be combined
        i = 0
        while i < len(supplier_nfes_with_date):
            group_start = supplier_nfes_with_date[i]
            if group_start[0]['nfe_id'] in combined_nfe_ids:
                i += 1
                continue
                
            group = [group_start]
            start_date = group_start[1]
            group_value = group_start[0].get('nfe_value', 0)
            
            # Check date constraints for the first NFE
            if start_date and po_date:
                days_from_po = abs((start_date - po_date).days)
                if days_from_po > MAX_DAYS_FROM_PO:
                    i += 1
                    continue
            
            # Find additional NFEs that can be combined (within date and value limits)
            j = i + 1
            while j < len(supplier_nfes_with_date):
                next_nfe, next_date = supplier_nfes_with_date[j]
                
                if next_nfe['nfe_id'] in combined_nfe_ids:
                    j += 1
                    continue
                
                # Check if within 120 days from PO
                if next_date and po_date:
                    days_from_po = abs((next_date - po_date).days)
                    if days_from_po > MAX_DAYS_FROM_PO:
                        j += 1
                        continue
                
                # Check if within 45 days from ANY NFE already in group
                date_ok = False
                if next_date:
                    for g_nfe, g_date in group:
                        if g_date:
                            days_between = abs((next_date - g_date).days)
                            if days_between <= MAX_DAYS_BETWEEN_NFES:
                                date_ok = True
                                break
                else:
                    date_ok = True  # No date info, allow it
                
                if not date_ok:
                    j += 1
                    continue
                
                # Check if adding this NFE would exceed value limit
                next_value = next_nfe.get('nfe_value', 0)
                if po_value > 0 and (group_value + next_value) > (po_value * MAX_COMBINED_VALUE_RATIO):
                    j += 1
                    continue
                
                group.append((next_nfe, next_date))
                group_value += next_value
                j += 1
            
            # Only create combined result if we have 2+ NFEs
            if len(group) >= 2:
                # Calculate combined metrics
                combined_nfe_numbers = [g[0]['nfe_number'] for g in group]
                combined_value = sum(g[0]['nfe_value'] for g in group)
                combined_item_matches = []
                matched_po_item_ids = set()
                
                for g in group:
                    for item_match in g[0].get('item_matches', []):
                        po_item_id = item_match.get('po_item_id')
                        # Avoid duplicate matches for the same PO item
                        if po_item_id not in matched_po_item_ids:
                            combined_item_matches.append(item_match)
                            matched_po_item_ids.add(po_item_id)
                        else:
                            # Add quantity from this NFE to existing match
                            for existing in combined_item_matches:
                                if existing.get('po_item_id') == po_item_id:
                                    existing['nfe_qty'] = existing.get('nfe_qty', 0) + item_match.get('nfe_qty', 0)
                                    break
                
                # Calculate combined coverage
                total_items = len(po_data['itens'])
                combined_coverage = len(matched_po_item_ids) / total_items if total_items > 0 else 0
                
                # Calculate combined score
                # Base it on the best individual score + bonus for better coverage
                best_individual_score = max(g[0]['score'] for g in group)
                avg_individual_score = sum(g[0]['score'] for g in group) / len(group)
                
                # Coverage bonus: up to 15 extra points for better combined coverage
                best_individual_coverage = max(g[0]['breakdown'].get('coverage_pct', 0) for g in group) / 100
                coverage_improvement = combined_coverage - best_individual_coverage
                coverage_bonus = max(0, coverage_improvement * 30)  # Up to 30 bonus points
                
                # Value match bonus/penalty: if combined value is closer to PO value
                combined_value_diff = abs(combined_value - po_data['valor_total']) / po_data['valor_total'] * 100 if po_data['valor_total'] > 0 else 100
                best_value_diff = min(g[0]['breakdown'].get('value_diff_pct', 100) or 100 for g in group)
                value_improvement_bonus = 0
                value_excess_penalty = 0
                
                if combined_value_diff < best_value_diff:
                    value_improvement_bonus = min(10, (best_value_diff - combined_value_diff) * 0.5)
                
                # Penalty if combined value exceeds PO value significantly
                if combined_value > po_data['valor_total']:
                    excess_pct = (combined_value - po_data['valor_total']) / po_data['valor_total'] * 100
                    if excess_pct > 50:  # More than 50% over
                        value_excess_penalty = min(30, excess_pct * 0.3)  # Up to 30 point penalty
                    elif excess_pct > 20:  # More than 20% over
                        value_excess_penalty = min(15, excess_pct * 0.2)  # Up to 15 point penalty
                
                combined_score = best_individual_score + coverage_bonus + value_improvement_bonus - value_excess_penalty
                combined_score = max(10, min(100, combined_score))  # Cap between 10 and 100
                
                # Mark these NFEs as combined
                for g in group:
                    combined_nfe_ids.add(g[0]['nfe_id'])
                
                combined_result = {
                    'nfe_id': f"combined_{'+'.join(combined_nfe_numbers)}",
                    'nfe_number': ' + '.join(combined_nfe_numbers),
                    'nfe_chave': None,
                    'nfe_value': combined_value,
                    'nfe_date': group[0][1].isoformat() if group[0][1] else None,
                    'nfe_supplier': group[0][0]['nfe_supplier'],
                    'nfe_cnpj': group[0][0]['nfe_cnpj'],
                    'score': round(combined_score, 2),
                    'max_possible_score': 110,
                    'match_quality': 'high' if combined_score >= 70 else 'medium' if combined_score >= 45 else 'low',
                    'is_combined': True,
                    'combined_nfes': [g[0]['nfe_number'] for g in group],
                    'combined_count': len(group),
                    'breakdown': {
                        'type': 'combined',
                        'individual_scores': [g[0]['score'] for g in group],
                        'best_individual_score': best_individual_score,
                        'coverage_bonus': round(coverage_bonus, 2),
                        'value_improvement_bonus': round(value_improvement_bonus, 2),
                        'value_excess_penalty': round(value_excess_penalty, 2),
                        'combined_coverage_pct': round(combined_coverage * 100, 2),
                        'combined_value_diff_pct': round(combined_value_diff, 2),
                        'po_value': po_data['valor_total'],
                        'items_matched': len(matched_po_item_ids),
                        'items_to_match': total_items,
                        'cnpj_score': group[0][0]['breakdown'].get('cnpj_score', 0),
                        'supplier_match_type': group[0][0]['breakdown'].get('supplier_match_type', 'unknown')
                    },
                    'item_matches': combined_item_matches
                }
                combined_results.append(combined_result)
            
            i += 1
    
    # Add combined results to the main results list
    all_results = results + combined_results
    
    # Sort all results by score
    all_results.sort(key=lambda x: x['score'], reverse=True)
    
    # Add purchase order info to response
    return {
        'purchase_order': {
            'id': po_data['id'],
            'cod_pedc': po_data['cod_pedc'],
            'fornecedor': po_data['fornecedor'],
            'valor_total': po_data['valor_total'],
            'valor_remaining': round(total_remaining_value, 2),
            'is_fulfilled': po_data['is_fulfilled'],
            'items_total': len(po_data['itens']),
            'items_fulfilled': len(fulfilled_items),
            'items_partial': len(partially_fulfilled_items),
            'items_unfulfilled': len(unfulfilled_items)
        },
        'matches': all_results
    }
