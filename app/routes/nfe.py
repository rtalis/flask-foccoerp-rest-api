import xml.etree.ElementTree as ET
import base64
import requests
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from flask import request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from app import db
from app.models import (
    NFEData, NFEEmitente, NFEItem, NFEntry, NFEDestinatario, 
    PurchaseItemNFEMatch, PurchaseOrder, PurchaseItem, Company
)
from app.utils import parse_and_store_nfe_xml, apply_adjustments
from app.routes.routes import bp
from config import Config


def _parse_date(date_obj):
    """Parse date object to ISO format string."""
    if date_obj is None:
        return None
    if hasattr(date_obj, 'isoformat'):
        return date_obj.isoformat()
    return str(date_obj)


def _check_supplier_match(purchase_order, nfe_emitente):
    """
    Check if a purchase order's supplier matches an NFE emitente.
    Uses CNPJ matching as primary, fuzzy name matching as fallback.
    
    Returns:
        bool: True if supplier matches emitente, False otherwise
    """
    from app.models import Supplier
    
    if not purchase_order or not nfe_emitente:
        return False
    
    # Get NFE emitente CNPJ
    emit_cnpj_clean = None
    if nfe_emitente.cnpj:
        emit_cnpj_clean = ''.join(filter(str.isdigit, str(nfe_emitente.cnpj)))
    
    # Get supplier CNPJ from database using fornecedor_id
    fornecedor_cnpj = None
    if purchase_order.fornecedor_id:
        supplier = db.session.query(Company).filter(Company.cod_emp1 == str(purchase_order.fornecedor_id)).first()
        if supplier and supplier.nvl_forn_cnpj_forn_cpf:
            fornecedor_cnpj = ''.join(filter(str.isdigit, str(supplier.nvl_forn_cnpj_forn_cpf)))
    
    # 1. Check CNPJ match (primary criteria)
    if emit_cnpj_clean and fornecedor_cnpj:
        return emit_cnpj_clean == fornecedor_cnpj
    
    # 2. If no CNPJ available, use supplier name fuzzy matching
    if purchase_order.fornecedor_descricao and nfe_emitente.nome:
        name_ratio = fuzz.token_set_ratio(
            purchase_order.fornecedor_descricao.lower(),
            nfe_emitente.nome.lower()
        )
        return name_ratio >= 80
    
    return False


# PHASE 3 ENDPOINTS

@bp.route('/get_nfe', methods=['GET'])
@login_required
def get_nfentry():
    cod_pedc = request.args.get('cod_pedc')
    linha = request.args.get('linha')

    if not cod_pedc or not linha:
        return jsonify({'error': 'cod_pedc and linha are required'}), 400

    nf_entries = NFEntry.query.filter(
        NFEntry.cod_pedc == cod_pedc,
        NFEntry.linha == linha
    ).all()

    if not nf_entries:
        return jsonify({'error': 'No entries found'}), 404

    result = []
    for entry in nf_entries:
        result.append({
            'cod_emp1': entry.cod_emp1,
            'cod_pedc': entry.cod_pedc,
            'linha': entry.linha,
            'num_nf': entry.num_nf,
            'text_field': entry.text_field
        })

    return jsonify(result), 200


@bp.route('/purchase_by_nf', methods=['GET'])
@login_required
def get_purchase_by_nf():
    num_nf = request.args.get('num_nf')
    if not num_nf:
        return jsonify({'error': 'num_nf is required'}), 400

    nf_entry = NFEntry.query.filter_by(num_nf=num_nf).first()
    if not nf_entry:
        return jsonify({'error': 'Nota fiscal não encontrada'}), 404

    item = PurchaseItem.query.filter_by(
        cod_pedc=nf_entry.cod_pedc,
        linha=nf_entry.linha,
        cod_emp1=nf_entry.cod_emp1
    ).first()
    if not item:
        return jsonify({'error': 'Item relacionado não encontrado'}), 404

    order = PurchaseOrder.query.filter_by(
        cod_pedc=item.cod_pedc,
        cod_emp1=item.cod_emp1
    ).first()
    if not order:
        return jsonify({'error': 'Pedido de compra não encontrado'}), 404

    items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
    items_data = []
    for i in items:
        items_data.append({
            'id': i.id,
            'item_id': i.item_id,
            'descricao': i.descricao,
            'quantidade': i.quantidade,
            'preco_unitario': i.preco_unitario,
            'total': i.total,
            'unidade_medida': i.unidade_medida,
            'dt_entrega': i.dt_entrega,
            'perc_ipi': i.perc_ipi,
            'tot_liquido_ipi': i.tot_liquido_ipi,
            'tot_descontos': i.tot_descontos,
            'tot_acrescimos': i.tot_acrescimos,
            'qtde_canc': i.qtde_canc,
            'qtde_canc_toler': i.qtde_canc_toler,
            'qtde_atendida': i.qtde_atendida,
            'qtde_saldo': i.qtde_saldo,
            'perc_toler': i.perc_toler
        })

    order_data = {
        'order_id': order.id,
        'cod_pedc': order.cod_pedc,
        'dt_emis': _parse_date(order.dt_emis),
        'fornecedor_id': order.fornecedor_id,
        'fornecedor_descricao': order.fornecedor_descricao,
        'total_bruto': order.total_bruto,
        'total_liquido': order.total_liquido,
        'total_liquido_ipi': order.total_liquido_ipi,
        'posicao': order.posicao,
        'posicao_hist': order.posicao_hist,
        'observacao': order.observacao,
        'contato': order.contato,
        'func_nome': order.func_nome,
        'cf_pgto': order.cf_pgto,
        'cod_emp1': order.cod_emp1,
        'items': items_data
    }

    return jsonify(order_data), 200


@bp.route('/get_danfe_pdf', methods=['GET'])
@login_required
def get_danfe_pdf():
    xml_key = request.args.get('xmlKey')
    retry = request.args.get('retry', 'false').lower() == 'true'
    details = request.args.get('details', 'false').lower() == 'true'

    if not xml_key:
        return jsonify({'error': 'xmlKey is required'}), 400

    def _build_local_pdf_response(nfe_data, source):
        from brazilfiscalreport.danfe import Danfe

        danfe = Danfe(xml=nfe_data.xml_content)
        pdf_output = danfe.output(dest='S')
        pdf_bytes = (
            pdf_output.encode('latin1')
            if isinstance(pdf_output, str)
            else pdf_output
        )
        pdf_base64 = base64.b64encode(pdf_bytes).decode('ascii')
        return jsonify({'pdf': pdf_base64, 'source': source}), 200
    
    try:
        existing_nfe = NFEData.query.filter_by(chave=xml_key).first()
        
        if existing_nfe:
            if details:
                return jsonify({
                    'source': 'database',
                    'nfe': {
                        'chave': existing_nfe.chave,
                        'numero': existing_nfe.numero,
                        'serie': existing_nfe.serie,
                        'data_emissao': existing_nfe.data_emissao.isoformat() if existing_nfe.data_emissao else None,
                        'natureza_operacao': existing_nfe.natureza_operacao,
                        'emitente': {
                            'nome': existing_nfe.emitente.nome if existing_nfe.emitente else '',
                            'cnpj': existing_nfe.emitente.cnpj if existing_nfe.emitente else '',
                            'inscricao_estadual': existing_nfe.emitente.inscricao_estadual if existing_nfe.emitente else '',
                        },
                        'destinatario': {
                            'nome': existing_nfe.destinatario.nome if existing_nfe.destinatario else '',
                            'cnpj': existing_nfe.destinatario.cnpj if existing_nfe.destinatario else '',
                            'inscricao_estadual': existing_nfe.destinatario.inscricao_estadual if existing_nfe.destinatario else '',
                        },
                        'valor_total': existing_nfe.valor_total,
                        'status': existing_nfe.status_motivo
                    }
                }), 200

            if retry:
                return _build_local_pdf_response(existing_nfe, 'retry')

        try:
            pdf_response = requests.get(
                f'https://api.sieg.com/api/Arquivos/GerarDanfeViaChave?xmlKey={xml_key}&api_key={Config.SIEG_API_KEY}',
                headers={'Accept': 'application/json'},
                timeout=5,
            )
            if pdf_response.status_code != 200:
                raise Exception(f'SIEG API error: {pdf_response.status_code} - {pdf_response.text}')
        except requests.Timeout as e:
            if not existing_nfe:
                existing_nfe = NFEData.query.filter_by(chave=xml_key).first()

            if existing_nfe:
                return _build_local_pdf_response(existing_nfe, 'fallback_timeout')

            return jsonify({'error': f'SIEG timeout and no local NFE available: {str(e)}'}), 504
        except Exception as e:
            if not existing_nfe:
                existing_nfe = NFEData.query.filter_by(chave=xml_key).first()

            if existing_nfe:
                return _build_local_pdf_response(existing_nfe, 'fallback_error')

            return jsonify({'error': f'NFE not found: {str(e)}'}), 404

        return jsonify(pdf_response.json()), 200
    
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/get_danfe_data', methods=['GET'])
@login_required
def get_danfe_data():
    chave = request.args.get('chave')
    if not chave:
        return jsonify({'error': 'Parametro "chave" é requerido'}), 400

    nfe = NFEData.query.filter_by(chave=chave).first()
    if not nfe:
        return jsonify({'error': 'NFE não encontrada'}), 404

    emit = nfe.emitente
    dest = nfe.destinatario
    trans = nfe.transportadora
    volumes = [
        {
            'quantidade': v.quantidade,
            'especie': v.especie,
            'marca': v.marca,
            'numeracao': v.numeracao,
            'peso_bruto': v.peso_bruto,
            'peso_liquido': v.peso_liquido,
        } for v in nfe.volumes
    ]
    items = []
    for it in nfe.itens:
        items.append({
            'numero_item': it.numero_item,
            'codigo': it.codigo,
            'descricao': it.descricao,
            'ncm': it.ncm,
            'cfop': it.cfop,
            'unidade': it.unidade_comercial,
            'quantidade': it.quantidade_comercial,
            'valor_unitario': it.valor_unitario_comercial,
            'valor_total': it.valor_total_bruto,
            'icms': {
                'vBC': it.icms_vbc,
                'pICMS': it.icms_picms,
                'vICMS': it.icms_vicms,
                'origem': it.icms_origem,
                'cst': it.icms_cst,
            },
            'ipi': {
                'cEnq': it.ipi_cenq,
                'cst': it.ipi_cst,
            },
            'pis': {
                'cst': it.pis_cst,
                'vBC': it.pis_vbc,
                'pPIS': it.pis_ppis,
                'vPIS': it.pis_vpis,
            },
            'cofins': {
                'cst': it.cofins_cst,
                'vBC': it.cofins_vbc,
                'pCOFINS': it.cofins_pcofins,
                'vCOFINS': it.cofins_vcofins,
            },
            'inf_ad_prod': it.inf_ad_prod,
        })

    emitente = {
        'nome': emit.nome if emit else None,
        'cnpj': emit.cnpj if emit else None,
        'inscricao_estadual': emit.inscricao_estadual if emit else None,
        'telefone': emit.telefone if emit else None,
        'email': emit.email if emit else None,
        'endereco': {
            'logradouro': emit.logradouro if emit else None,
            'numero': emit.numero if emit else None,
            'complemento': emit.complemento if emit else None,
            'bairro': emit.bairro if emit else None,
            'municipio': emit.municipio if emit else None,
            'uf': emit.uf if emit else None,
            'cep': emit.cep if emit else None,
        },
        'logo_url': None
    }

    destinatario = {
        'nome': dest.nome if dest else None,
        'cpf_cnpj': dest.cpf or dest.cnpj if dest else None,
        'inscricao_estadual': dest.inscricao_estadual if dest else None,
        'telefone': dest.telefone if dest else None,
        'email': dest.email if dest else None,
        'endereco': {
            'logradouro': dest.logradouro if dest else None,
            'numero': dest.numero if dest else None,
            'complemento': dest.complemento if dest else None,
            'bairro': dest.bairro if dest else None,
            'municipio': dest.municipio if dest else None,
            'uf': dest.uf if dest else None,
            'cep': dest.cep if dest else None,
        },
    }

    transportadora = None
    if trans:
        transportadora = {
            'nome': trans.nome,
            'cnpj': trans.cnpj,
            'inscricao_estadual': trans.inscricao_estadual,
            'endereco': trans.endereco,
            'municipio': trans.municipio,
            'uf': trans.uf,
            'placa': trans.placa,
            'uf_veiculo': trans.uf_veiculo,
            'rntc': trans.rntc,
        }

    impostos = {
        'valor_total': nfe.valor_total,
        'valor_produtos': nfe.valor_produtos,
        'valor_frete': nfe.valor_frete,
        'valor_seguro': nfe.valor_seguro,
        'valor_desconto': nfe.valor_desconto,
        'valor_icms': nfe.valor_icms,
        'valor_icms_st': nfe.valor_icms_st,
        'valor_ipi': nfe.valor_ipi,
        'valor_pis': nfe.valor_pis,
        'valor_cofins': nfe.valor_cofins,
        'valor_outros': nfe.valor_outros,
    }

    logo_url = None
    try:
        if nfe.emitente and nfe.emitente.cnpj:
            company = Company.query.filter((Company.cnpj == nfe.emitente.cnpj) | (Company.name == nfe.emitente.nome)).first()
            if company and company.logo_path:
                logo_url = company.logo_path
    except Exception:
        logo_url = None

    emitente['logo_url'] = logo_url

    result = {
        'chave': nfe.chave,
        'numero': nfe.numero,
        'serie': nfe.serie,
        'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
        'data_saida': nfe.data_saida.isoformat() if nfe.data_saida else None,
        'natureza_operacao': nfe.natureza_operacao,
        'tipo_operacao': nfe.tipo_operacao,
        'protocolo': nfe.protocolo,
        'data_autorizacao': nfe.data_autorizacao.isoformat() if nfe.data_autorizacao else None,
        'ambiente': nfe.ambiente,
        'modality_frete': nfe.modalidade_frete,
        'informacoes_adicionais': nfe.informacoes_adicionais,
        'emitente': emitente,
        'destinatario': destinatario,
        'transportador': transportadora,
        'impostos': impostos,
        'volumes': volumes,
        'items': items,
    }

    return jsonify(result), 200


@bp.route('/get_nfe_data', methods=['GET'])
@login_required
def get_nfe_data():
    xml_key = request.args.get('xmlKey')
    if not xml_key:
        return jsonify({'error': 'xmlKey is required'}), 400
    
    try:
        existing_nfe = NFEData.query.filter_by(chave=xml_key).first()
        
        if existing_nfe:
            items_data = []
            for item in existing_nfe.itens:
                items_data.append({
                    'numero_item': item.numero_item,
                    'codigo': item.codigo,
                    'descricao': item.descricao,
                    'ncm': item.ncm,
                    'cfop': item.cfop,
                    'unidade': item.unidade_comercial,
                    'quantidade': item.quantidade_comercial,
                    'valor_unitario': item.valor_unitario_comercial,
                    'valor_total': item.valor_total_bruto,
                    'icms_valor': item.icms_vicms,
                    'icms_aliquota': item.icms_picms,
                    'pis_valor': item.pis_vpis,
                    'pis_aliquota': item.pis_ppis,
                    'cofins_valor': item.cofins_vcofins,
                    'cofins_aliquota': item.cofins_pcofins
                })
            
            result = {
                'source': 'database',
                'chave': existing_nfe.chave,
                'numero': existing_nfe.numero,
                'serie': existing_nfe.serie,
                'data_emissao': existing_nfe.data_emissao.isoformat() if existing_nfe.data_emissao else None,
                'natureza_operacao': existing_nfe.natureza_operacao,
                'status': existing_nfe.status_motivo,
                'protocolo': existing_nfe.protocolo,
                'valor_total': existing_nfe.valor_total,
                'valor_produtos': existing_nfe.valor_produtos,
                'valor_impostos': existing_nfe.valor_imposto,
                
                'emitente': {
                    'nome': existing_nfe.emitente.nome if existing_nfe.emitente else '',
                    'cnpj': existing_nfe.emitente.cnpj if existing_nfe.emitente else '',
                    'inscricao_estadual': existing_nfe.emitente.inscricao_estadual if existing_nfe.emitente else '',
                    'endereco': {
                        'logradouro': existing_nfe.emitente.logradouro if existing_nfe.emitente else '',
                        'numero': existing_nfe.emitente.numero if existing_nfe.emitente else '',
                        'complemento': existing_nfe.emitente.complemento if existing_nfe.emitente else '',
                        'bairro': existing_nfe.emitente.bairro if existing_nfe.emitente else '',
                        'municipio': existing_nfe.emitente.municipio if existing_nfe.emitente else '',
                        'uf': existing_nfe.emitente.uf if existing_nfe.emitente else '',
                        'cep': existing_nfe.emitente.cep if existing_nfe.emitente else '',
                        'telefone': existing_nfe.emitente.telefone if existing_nfe.emitente else '',
                    }
                },
                
                'destinatario': {
                    'nome': existing_nfe.destinatario.nome if existing_nfe.destinatario else '',
                    'cnpj': existing_nfe.destinatario.cnpj if existing_nfe.destinatario else '',
                    'cpf': existing_nfe.destinatario.cpf if existing_nfe.destinatario else '',
                    'inscricao_estadual': existing_nfe.destinatario.inscricao_estadual if existing_nfe.destinatario else '',
                    'email': existing_nfe.destinatario.email if existing_nfe.destinatario else '',
                    'endereco': {
                        'logradouro': existing_nfe.destinatario.logradouro if existing_nfe.destinatario else '',
                        'numero': existing_nfe.destinatario.numero if existing_nfe.destinatario else '',
                        'complemento': existing_nfe.destinatario.complemento if existing_nfe.destinatario else '',
                        'bairro': existing_nfe.destinatario.bairro if existing_nfe.destinatario else '',
                        'municipio': existing_nfe.destinatario.municipio if existing_nfe.destinatario else '',
                        'uf': existing_nfe.destinatario.uf if existing_nfe.destinatario else '',
                        'cep': existing_nfe.destinatario.cep if existing_nfe.destinatario else '',
                        'telefone': existing_nfe.destinatario.telefone if existing_nfe.destinatario else '',
                    }
                },
                
                'transporte': {
                    'modalidade': existing_nfe.modalidade_frete,
                    'transportadora': {
                        'nome': existing_nfe.transportadora.nome if existing_nfe.transportadora else '',
                        'cnpj': existing_nfe.transportadora.cnpj if existing_nfe.transportadora else '',
                        'inscricao_estadual': existing_nfe.transportadora.inscricao_estadual if existing_nfe.transportadora else '',
                        'endereco': existing_nfe.transportadora.endereco if existing_nfe.transportadora else '',
                        'municipio': existing_nfe.transportadora.municipio if existing_nfe.transportadora else '',
                        'uf': existing_nfe.transportadora.uf if existing_nfe.transportadora else '',
                        'placa': existing_nfe.transportadora.placa if existing_nfe.transportadora else '',
                    },
                    'volumes': [{
                        'quantidade': vol.quantidade,
                        'especie': vol.especie,
                        'peso_bruto': vol.peso_bruto,
                        'peso_liquido': vol.peso_liquido
                    } for vol in existing_nfe.volumes] if existing_nfe.volumes else []
                },
                
                'pagamento': [{
                    'tipo': pag.tipo,
                    'valor': pag.valor
                } for pag in existing_nfe.pagamentos] if existing_nfe.pagamentos else [],
                
                'duplicatas': [{
                    'numero': dup.numero,
                    'vencimento': dup.data_vencimento.isoformat() if dup.data_vencimento else None,
                    'valor': dup.valor
                } for dup in existing_nfe.duplicatas] if existing_nfe.duplicatas else [],
                
                'itens': items_data,
                
                'informacoes_adicionais': existing_nfe.informacoes_adicionais,
                'informacoes_fisco': existing_nfe.informacoes_fisco,
                
                'xml_content': existing_nfe.xml_content
            }
            
            return jsonify(result), 200

        xml_response = requests.post(
            f'https://api.sieg.com/BaixarXml?xmlType=1&downloadEvent=true&api_key={Config.SIEG_API_KEY}',
            data=xml_key,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            timeout=8,
        )
        
        if xml_response.status_code != 200:
            return jsonify({'error': f'Error fetching NFe XML: {xml_response.status_code}'}), xml_response.status_code
        
        xml_content = xml_response.text
        parse_and_store_nfe_xml(xml_content)
        
        return get_nfe_data()
        
    except requests.Timeout:
        return jsonify({'error': 'Timeout while fetching NFe XML from SIEG'}), 504
    except requests.RequestException as e:
        return jsonify({'error': f'Error contacting SIEG: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/get_nfe_by_number', methods=['GET'])
@login_required
def get_nfe_by_number():
    """Find NFE in the database by its number (num_nf)."""
    num_nf = request.args.get('num_nf')
    fornecedor_id = request.args.get('fornecedor_id')
    fornecedor_nome = request.args.get('fornecedor_nome')
    dt_ent_str = request.args.get('dt_ent')
    chave = request.args.get('chave')
    
    if not num_nf:
        return jsonify({'error': 'num_nf is required'}), 400
    
    try:
        num_nf_clean = str(num_nf).lstrip('0')
        
        dt_ent = None
        if dt_ent_str:
            try:
                dt_ent = datetime.strptime(dt_ent_str[:10], '%Y-%m-%d').date()
            except:
                pass
        
        # Special case for Mercado Pago (marketplace)
        if fornecedor_id and str(fornecedor_id) == '1160':
            nfes = NFEData.query.filter_by(numero=num_nf).all()
            if not nfes:
                nfes = NFEData.query.filter(NFEData.numero == num_nf_clean).all()
            
            if not nfes:
                return jsonify({'error': 'NFE not found in database', 'found': False}), 404
            
            if dt_ent:
                for nfe in nfes:
                    nfe_date = nfe.data_emissao
                    if hasattr(nfe_date, 'date'):
                        nfe_date = nfe_date.date()
                    if nfe_date >= dt_ent:
                        return jsonify({
                            'found': True,
                            'chave': nfe.chave,
                            'numero': nfe.numero,
                            'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                            'valor': nfe.valor_total,
                            'fornecedor': nfe.emitente.nome if nfe.emitente else None,
                            'is_mercadopago': True
                        }), 200
                return jsonify({'error': 'NFE found but issued before purchase date', 'found': False}), 404
            else:
                nfe = nfes[0]
                return jsonify({
                    'found': True,
                    'chave': nfe.chave,
                    'numero': nfe.numero,
                    'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                    'valor': nfe.valor_total,
                    'fornecedor': nfe.emitente.nome if nfe.emitente else None,
                    'is_mercadopago': True
                }), 200
        
        # Normal flow for other suppliers
        nfes = NFEData.query.filter_by(numero=num_nf).all()
        
        if not nfes:
            nfes = NFEData.query.filter(NFEData.numero == num_nf_clean).order_by(NFEData.data_emissao.desc()).all()
        
        if not nfes:
            return jsonify({'error': 'NFE not found in database', 'found': False}), 404
        
        fornecedor_cnpj = None
        if fornecedor_id:
            supplier = Company.query.filter(Company.cod_emp1 == str(fornecedor_id)).first()
            if supplier and supplier.nvl_forn_cnpj_forn_cpf:
                fornecedor_cnpj = ''.join(filter(str.isdigit, str(supplier.nvl_forn_cnpj_forn_cpf)))
        
        matched_nfe = None
        
        for nfe in nfes:
            if fornecedor_cnpj and nfe.emitente and nfe.emitente.cnpj:
                emit_cnpj_clean = ''.join(filter(str.isdigit, str(nfe.emitente.cnpj)))
                if emit_cnpj_clean[:8] == fornecedor_cnpj[:8]:
                    if dt_ent and nfe.data_emissao:
                        nfe_date = nfe.data_emissao
                        if hasattr(nfe_date, 'date'):
                            nfe_date = nfe_date.date()
                        days_diff = abs((nfe_date - dt_ent).days)
                        if days_diff <= 30:
                            matched_nfe = nfe
                            break
                    else:
                        matched_nfe = nfe
                        break
            
            elif not fornecedor_cnpj and fornecedor_nome and nfe.emitente and nfe.emitente.nome:
                name_ratio = fuzz.token_set_ratio(
                    fornecedor_nome.lower(),
                    nfe.emitente.nome.lower()
                )
                if name_ratio >= 80:
                    if dt_ent and nfe.data_emissao:
                        nfe_date = nfe.data_emissao
                        if hasattr(nfe_date, 'date'):
                            nfe_date = nfe_date.date()
                        days_diff = abs((nfe_date - dt_ent).days)
                        if days_diff <= 30:
                            matched_nfe = nfe
                            break
                    else:
                        matched_nfe = nfe
                        break
        
        if not matched_nfe and dt_ent:
            for nfe in nfes:
                if nfe.data_emissao:
                    nfe_date = nfe.data_emissao
                    if hasattr(nfe_date, 'date'):
                        nfe_date = nfe_date.date()
                    days_diff = abs((nfe_date - dt_ent).days)
                    if days_diff <= 15:
                        matched_nfe = nfe
                        break
        
        if not matched_nfe:
            return jsonify({'error': 'NFE not found matching criteria', 'found': False}), 404
        
        return jsonify({
            'found': True,
            'chave': matched_nfe.chave,
            'numero': matched_nfe.numero,
            'data_emissao': matched_nfe.data_emissao.isoformat() if matched_nfe.data_emissao else None,
            'valor': matched_nfe.valor_total,
            'fornecedor': matched_nfe.emitente.nome if matched_nfe.emitente else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/sync_nfe', methods=['POST'])
@login_required
def sync_nfe_api():
    """API endpoint to manually trigger NFE sync"""
    from app.tasks.sync_nfe import sync_nfe_for_yesterday
    
    try:
        result = sync_nfe_for_yesterday()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/match_purchase_nfe', methods=['GET'])
@login_required
def match_purchase_nfe():
    """Find NFEs that match a purchase order and score their similarity."""
    from app.utils import score_purchase_nfe_match
    
    cod_pedc = request.args.get('cod_pedc')
    cod_emp1 = request.args.get('cod_emp1')
    max_results = request.args.get('max_results', default=10, type=int)
    
    result = score_purchase_nfe_match(cod_pedc, cod_emp1)
    
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    
    matches = result.get('matches', [])
    if max_results and len(matches) > max_results:
        result['matches'] = matches[:max_results]
    
    return jsonify({
        'purchase_order': result.get('purchase_order'),
        'matches_found': len(result.get('matches', [])),
        'matches': result.get('matches', [])
    }), 200


@bp.route('/manual_match_nfe', methods=['POST'])
@login_required
def manual_match_nfe():
    """Manually match an NFE to a purchase order item."""
    from app.utils import score_purchase_nfe_match
    
    try:
        data = request.get_json()
        
        nfe_chave = data.get('nfe_chave')
        cod_pedc = data.get('cod_pedc')
        cod_emp1 = data.get('cod_emp1')
        purchase_item_id = data.get('purchase_item_id')
        
        if not all([nfe_chave, cod_pedc, cod_emp1]):
            return jsonify({
                'error': 'Missing required fields: nfe_chave, cod_pedc, cod_emp1'
            }), 400
        
        nfe = NFEData.query.filter_by(chave=nfe_chave).first()
        if not nfe:
            return jsonify({'error': f'NFE with chave {nfe_chave} not found'}), 404
        
        purchase_order = PurchaseOrder.query.filter_by(
            cod_pedc=cod_pedc,
            cod_emp1=cod_emp1
        ).first()
        
        if not purchase_order:
            return jsonify({
                'error': f'Purchase order {cod_pedc} for company {cod_emp1} not found'
            }), 404
        
        if not purchase_item_id:
            unfulfilled_item = PurchaseItem.query.filter(
                PurchaseItem.purchase_order_id == purchase_order.id,
                (PurchaseItem.qtde_atendida == None) | 
                (PurchaseItem.qtde_atendida < PurchaseItem.quantidade)
            ).first()
            
            if unfulfilled_item:
                purchase_item_id = unfulfilled_item.id
        
        match_result = score_purchase_nfe_match(cod_pedc, cod_emp1)
        
        if isinstance(match_result, dict) and 'error' in match_result:
            return jsonify(match_result), 400
        
        nfe_matches = [m for m in match_result.get('matches', []) 
                      if m.get('nfe_id') == nfe.id]
        
        if not nfe_matches:
            match_data = {
                'match_score': 75,
                'description_similarity': None,
                'quantity_match': None,
                'price_diff_pct': None,
                'nfe_fornecedor': nfe.emitente.nome if nfe.emitente else 'Unknown',
                'nfe_data_emissao': nfe.data_emissao,
            }
        else:
            match_data = nfe_matches[0]
        
        new_match = PurchaseItemNFEMatch(
            purchase_item_id=purchase_item_id,
            cod_pedc=cod_pedc,
            cod_emp1=cod_emp1,
            item_seq=purchase_order.purchase_items[0].linha if purchase_order.purchase_items else None,
            nfe_id=nfe.id,
            nfe_chave=nfe.chave,
            nfe_numero=nfe.numero,
            match_score=match_data.get('match_score', 75),
            description_similarity=match_data.get('description_similarity'),
            quantity_match=match_data.get('quantity_match'),
            price_diff_pct=match_data.get('price_diff_pct'),
            nfe_fornecedor=match_data.get('nfe_fornecedor'),
            nfe_data_emissao=match_data.get('nfe_data_emissao'),
            matched_by_user_id=str(current_user.id),
            match_type='manual'
        )
        
        existing_match = PurchaseItemNFEMatch.query.filter_by(
            cod_pedc=cod_pedc,
            cod_emp1=cod_emp1,
            nfe_id=nfe.id
        ).first()
        
        if existing_match:
            existing_match.matched_by_user_id = str(current_user.id)
            existing_match.match_type = 'manual'
            existing_match.updated_at = datetime.now()
            db.session.commit()
            return jsonify({
                'status': 'updated',
                'match_id': existing_match.id,
                'message': f'Match updated by user {current_user.username}'
            }), 200
        
        db.session.add(new_match)
        db.session.commit()
        
        return jsonify({
            'status': 'created',
            'match_id': new_match.id,
            'cod_pedc': new_match.cod_pedc,
            'nfe_numero': new_match.nfe_numero,
            'match_score': new_match.match_score,
            'matched_by': current_user.username,
            'message': f'NFE {nfe.numero} manually matched to purchase order {cod_pedc}'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/view_danfe_template/<int:nfe_id>', methods=['GET'])
@login_required
def view_danfe_template(nfe_id):
    """Render the DANFE template."""
    nfe = db.session.get(NFEData, nfe_id)
    if not nfe:
        return jsonify({'error': 'NFE not found'}), 404
    
    danfe_data = {
        'chave': nfe.chave,
        'numero': nfe.numero,
        'serie': nfe.serie,
        'data_emissao': nfe.data_emissao.strftime('%d/%m/%Y %H:%M:%S') if nfe.data_emissao else '',
        'natureza_operacao': nfe.natureza_operacao,
        'protocolo': nfe.protocolo,
        'valor_total': nfe.valor_total,
        'emitente': {
            'nome': nfe.emitente.nome if nfe.emitente else '',
            'cnpj': nfe.emitente.cnpj if nfe.emitente else '',
            'endereco': f"{nfe.emitente.logradouro}, {nfe.emitente.numero}" if nfe.emitente else '',
            'bairro': nfe.emitente.bairro if nfe.emitente else '',
            'municipio': nfe.emitente.municipio if nfe.emitente else '',
            'uf': nfe.emitente.uf if nfe.emitente else '',
            'cep': nfe.emitente.cep if nfe.emitente else '',
            'telefone': nfe.emitente.telefone if nfe.emitente else '',
        },
        'destinatario': {
            'nome': nfe.destinatario.nome if nfe.destinatario else '',
            'cnpj': nfe.destinatario.cnpj if nfe.destinatario else '',
            'endereco': f"{nfe.destinatario.logradouro}, {nfe.destinatario.numero}" if nfe.destinatario else '',
            'bairro': nfe.destinatario.bairro if nfe.destinatario else '',
            'municipio': nfe.destinatario.municipio if nfe.destinatario else '',
            'uf': nfe.destinatario.uf if nfe.destinatario else '',
            'cep': nfe.destinatario.cep if nfe.destinatario else '',
        },
        'itens': [
            {
                'codigo': item.codigo,
                'descricao': item.descricao,
                'quantidade': item.quantidade_comercial,
                'unidade': item.unidade_comercial,
                'valor_unitario': item.valor_unitario_comercial,
                'valor_total': item.valor_total_bruto,
                'ncm': item.ncm,
                'cfop': item.cfop,
            } for item in nfe.itens
        ]
    }
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DANFE - {nfe.numero}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .danfe-container {{ border: 1px solid #ccc; padding: 20px; max-width: 800px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
            .section {{ margin: 15px 0; }}
            .section-title {{ font-weight: bold; background: #f5f5f5; padding: 5px; }}
            .items-table {{ width: 100%; border-collapse: collapse; }}
            .items-table th, .items-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .items-table th {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <div class="danfe-container">
            <div class="header">
                <h2>DANFE</h2>
                <p>Número: {danfe_data['numero']}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@bp.route('/auto_match_nfes', methods=['GET'])
@login_required
def auto_match_nfes():
    """Find potential NFE matches for pending purchase orders"""
    from app.utils import score_purchase_nfe_match
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', default=50, type=int)
    limit = request.args.get('limit', default=10, type=int)
    
    query = PurchaseOrder.query.filter(PurchaseOrder.is_fulfilled == False)
    
    if start_date:
        query = query.filter(PurchaseOrder.dt_emis >= start_date)
    if end_date:
        query = query.filter(PurchaseOrder.dt_emis <= end_date)
    
    if current_user.role != 'admin' and current_user.system_name:
        query = query.filter(PurchaseOrder.func_nome.ilike(f'%{current_user.system_name}%'))
    
    purchase_orders = query.order_by(PurchaseOrder.dt_emis.desc()).limit(100).all()
    
    results = []
    for po in purchase_orders:
        items = PurchaseItem.query.filter_by(purchase_order_id=po.id).all()
        if not items:
            continue
            
        matches = score_purchase_nfe_match(po.cod_pedc)
        
        good_matches = [m for m in matches if m["score"] >= min_score]
        if not good_matches:
            continue
            
        best_match = good_matches[0]
        
        results.append({
            'purchase_order': {
                'id': po.id,
                'cod_pedc': po.cod_pedc,
                'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                'fornecedor_descricao': po.fornecedor_descricao,
                'total_pedido_com_ipi': po.total_pedido_com_ipi,
                'item_count': len(items)
            },
            'best_match': best_match
        })
    
    results.sort(key=lambda x: x['best_match']['score'], reverse=True)
    
    results = results[:limit]
    
    return jsonify(results), 200


@bp.route('/nfe_by_purchase', methods=['GET'])
@login_required
def get_nfe_by_purchase():
    import requests
    import base64
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from app.models import Supplier, NFEData
    from app.utils import parse_and_store_nfe_xml
    
    cod_pedc = request.args.get('cod_pedc')
    cod_emp1 = request.args.get('cod_emp1')
    if not cod_pedc:
        return jsonify({'error': 'cod_pedc is required'}), 400

    purchase_order_query = PurchaseOrder.query.filter_by(cod_pedc=cod_pedc)
    if cod_emp1:
        purchase_order_query = purchase_order_query.filter_by(cod_emp1=cod_emp1)

    purchase_order = purchase_order_query.first()
    if not purchase_order:
        return jsonify({'error': 'Purchase order not found'}), 404  


    if purchase_order.fornecedor_id:
        supplier = Supplier.query.filter( 
        (Supplier.cod_for == str(purchase_order.fornecedor_id))
        ).first()
    else:
        return jsonify({'error': 'Fornecedor ID not found in purchase order'}), 400
    
    if supplier and supplier.nvl_forn_cnpj_forn_cpf:
        fornecedor_cnpj = supplier.nvl_forn_cnpj_forn_cpf
    else:
        return jsonify({'error': 'Valid fornecedor CNPJ not found in database'}), 400

    fornecedor_cnpj = ''.join(filter(str.isdigit, str(fornecedor_cnpj)))
    
    start_date = purchase_order.dt_emis - relativedelta(days=30)  # Search for NFEs issued within 1 month before the purchase order date, to cover cases where NFE is issued before receive order generation
    #end_date = start_date + timedelta(days=120)  # Search for NFEs issued within 120 days after the purchase order date
    end_date = datetime.now() 
    
    start_date_str = start_date.strftime('%Y-%m-%dT00:00:00.000Z')
    end_date_str = end_date.strftime('%Y-%m-%dT23:59:59.999Z')
    
    sieg_request_data = {
        "XmlType": 1,
        "Take": 0,
        "Skip": 0,
        "DataEmissaoInicio": start_date_str,
        "DataEmissaoFim": end_date_str,
        "CnpjEmit": fornecedor_cnpj,
        "CnpjDest": "",
        "CnpjRem": "",
        "CnpjTom": "",
        "Tag": "",
        "Downloadevent": True,
        "TypeEvent": 0
    }
    try:
        response = requests.post(
            f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
            json=sieg_request_data,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'xmls' not in result or not result['xmls']:
                return jsonify({'message': 'No NFE data found for this purchase order'}), 404
        else:
            if response.status_code == 404:
                # Retry with a date range of one month before the start date, for after receive order purchase generation
                retry_start_date = start_date - relativedelta(months=1)
                retry_start_date_str = retry_start_date.strftime('%Y-%m-%dT00:00:00.000Z')
                retry_request_data = sieg_request_data.copy()
                retry_request_data["DataEmissaoInicio"] = retry_start_date_str

                retry_response = requests.post(
                    f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
                    json=retry_request_data,
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                )

                if retry_response.status_code != 200:
                    return jsonify({'error': 'No NFE data found for this purchase order after retry'}), 404

                result = retry_response.json()
                if 'xmls' not in result or not result['xmls']:
                    return jsonify({'message': 'No NFE data found for this purchase order after retry'}), 404

            else:
                return jsonify({'error': f'Error fetching NFE data: {response.status_code} - {response.text}'}), response.status_code
           
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        nfe_data = []
        for xml_base64 in result['xmls']:
            try:
                xml_content = base64.b64decode(xml_base64).decode('utf-8')
                root = ET.fromstring(xml_content)
                
                # Extract chave (access key) to check if NFE already exists in database
                chave_acesso_elem = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                if chave_acesso_elem is None or not chave_acesso_elem.text:
                    # Skip invalid XML or NFe without access key
                    continue
                
                chave_acesso = chave_acesso_elem.text

                # Store NFE in the database
                parse_and_store_nfe_xml(xml_content)
                
                numero_nota = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:nNF', ns)
                data_emissao = root.find('.//nfe:NFe/nfe:infNFe/nfe:ide/nfe:dhEmi', ns)
                nome_fornecedor = root.find('.//nfe:NFe/nfe:infNFe/nfe:emit/nfe:xNome', ns)
                valor_total = root.find('.//nfe:NFe/nfe:infNFe/nfe:total/nfe:ICMSTot/nfe:vNF', ns)

                nfe_data.append({
                    'chave': chave_acesso,
                    'numero': numero_nota.text if numero_nota is not None else '',
                    'data_emissao': data_emissao.text if data_emissao is not None else '',
                    'fornecedor': nome_fornecedor.text if nome_fornecedor is not None else '',
                    'valor': valor_total.text if valor_total is not None else '',
                    'xml_content': xml_content,
                    'stored_in_database': True
                })
            except Exception as e:
                # Log the error and continue with next XML
                print(f"Error processing XML: {str(e)}")
                continue
        
        return jsonify({
            'purchase_order': cod_pedc,
            'cod_emp1': purchase_order.cod_emp1,
            'fornecedor': purchase_order.fornecedor_descricao,
            'valor': valor_total.text if valor_total is not None else '',
            'data_emissao': data_emissao.text if data_emissao is not None else '',
            'numero_nota': numero_nota.text if numero_nota is not None else '',
            'nfe_data': nfe_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

def extract_xml_value(root, xpath):
    try:
        element = root.find(xpath)
        return element.text if element is not None else ''
    except:
        return ''
    

@bp.route('/search_nfe', methods=['GET'])
@login_required
def search_nfe():
    """
    Search for NFEs and find linked purchase orders.
    
    Parameters:
    - query: Search term (NFE number, chave, supplier name, or item description)
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - search_by_number: Search by NFE number (default: true)
    - search_by_chave: Search by chave de acesso (default: true)
    - search_by_fornecedor: Search by supplier name (default: false)
    - search_by_item: Search by item description (default: true)
    - include_estimated: Include AI-estimated matches (default: true)
    """
    from app.models import NFEData, NFEEmitente, NFEItem, NFEntry, PurchaseOrder, PurchaseItem, PurchaseItemNFEMatch
    from datetime import datetime
    from fuzzywuzzy import fuzz
    
    query = request.args.get('query', '').strip()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search_by_number = request.args.get('search_by_number', 'true').lower() == 'true'
    search_by_chave = request.args.get('search_by_chave', 'true').lower() == 'true'
    search_by_fornecedor = request.args.get('search_by_fornecedor', 'false').lower() == 'true'
    search_by_item = request.args.get('search_by_item', 'true').lower() == 'true'
    include_estimated = request.args.get('include_estimated', 'true').lower() == 'true'
    exact_term_search = request.args.get('exact_term_search', 'true').lower() == 'true'
    
    # Allow empty query if date range is provided
    if not query and not start_date_str and not end_date_str:
        return jsonify({'error': 'Query parameter or date range is required'}), 400
    
    try:
        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Build NFE query
        nfe_filters = []
        
        # Only add search filters if query is provided
        if query:
            if search_by_number:
                # Use exact match or LIKE based on exact_term_search
                nfe_filters.append(NFEData.numero == query)
                if not exact_term_search:
                    nfe_filters.append(NFEData.numero.ilike(f'%{query}%'))
            
            if search_by_chave:
                if exact_term_search:
                    nfe_filters.append(NFEData.chave == query)
                else:
                    nfe_filters.append(NFEData.chave.ilike(f'%{query}%'))
        
        # Query NFEs
        nfe_query = NFEData.query
        if nfe_filters:
            nfe_query = nfe_query.filter(or_(*nfe_filters))
        
        # Apply date filters
        if start_date:
            nfe_query = nfe_query.filter(NFEData.data_emissao >= start_date)
        if end_date:
            nfe_query = nfe_query.filter(NFEData.data_emissao <= end_date)
        
        # Order by most recent first
        nfe_query = nfe_query.order_by(NFEData.data_emissao.desc())
        
        nfes = nfe_query.limit(50).all()
        
        # If searching by supplier, also filter by emitente name
        if search_by_fornecedor and query:
            if exact_term_search:
                supplier_nfes = NFEData.query.join(NFEEmitente).filter(
                    NFEEmitente.nome == query
                )
            else:
                supplier_nfes = NFEData.query.join(NFEEmitente).filter(
                    NFEEmitente.nome.ilike(f'%{query}%')
                )
            if start_date:
                supplier_nfes = supplier_nfes.filter(NFEData.data_emissao >= start_date)
            if end_date:
                supplier_nfes = supplier_nfes.filter(NFEData.data_emissao <= end_date)
            
            supplier_nfes = supplier_nfes.order_by(NFEData.data_emissao.desc()).limit(50).all()
            
            # Merge results
            existing_ids = {n.id for n in nfes}
            for nfe in supplier_nfes:
                if nfe.id not in existing_ids:
                    nfes.append(nfe)
        
        # If searching by item description, search NFEItem
        if search_by_item and query:
            if exact_term_search:
                item_nfes = NFEData.query.join(NFEItem).filter(
                    NFEItem.descricao == query
                )
            else:
                item_nfes = NFEData.query.join(NFEItem).filter(
                    NFEItem.descricao.ilike(f'%{query}%')
                )
            if start_date:
                item_nfes = item_nfes.filter(NFEData.data_emissao >= start_date)
            if end_date:
                item_nfes = item_nfes.filter(NFEData.data_emissao <= end_date)
            
            item_nfes = item_nfes.order_by(NFEData.data_emissao.desc()).limit(50).all()
            
            # Merge results
            existing_ids = {n.id for n in nfes}
            for nfe in item_nfes:
                if nfe.id not in existing_ids:
                    nfes.append(nfe)
        
        # Sort all NFEs by date (most recent first) after merging
        nfes = sorted(nfes, key=lambda x: x.data_emissao or datetime.min, reverse=True)
        
        # Hard cap on total NFEs to prevent slow responses on broad queries
        nfes = nfes[:50]
        
        # Format NFE results
        nfe_results = []
        nfe_numbers = set()
        # Track all linked purchases (keys that matched at least one NFE)
        linked_purchase_keys = set()  # (cod_pedc, cod_emp1, linha)
        # Track all potential purchases for checking if they match any NFE
        all_potential_purchases = {}  # key: (cod_pedc, cod_emp1, linha), value: purchase info
        
        for nfe in nfes:
            emitente = NFEEmitente.query.filter_by(nfe_id=nfe.id).first()
            nfe_items = NFEItem.query.filter_by(nfe_id=nfe.id).all()
            nfe_items_by_numero = {
                item.numero_item: item for item in nfe_items if item.numero_item is not None
            }

            def _resolve_nfe_item_for_purchase(entry, purchase_item, match_obj=None):
                """
                Resolve NFE item for a purchase line with robust fallbacks:
                1) explicit match object nfe_item_id,
                2) saved PurchaseItemNFEMatch for this PO line + NFE number,
                3) weighted score using description + price + quantity (+ line hint).
                """
                if match_obj and match_obj.nfe_item_id:
                    nfe_item_from_match = db.session.get(NFEItem, match_obj.nfe_item_id)
                    if nfe_item_from_match:
                        return nfe_item_from_match

                if purchase_item and purchase_item.linha is not None and nfe.numero:
                    best_saved_match = PurchaseItemNFEMatch.query.filter(
                        PurchaseItemNFEMatch.cod_pedc == purchase_item.cod_pedc,
                        PurchaseItemNFEMatch.cod_emp1 == purchase_item.cod_emp1,
                        PurchaseItemNFEMatch.item_seq == purchase_item.linha,
                        PurchaseItemNFEMatch.nfe_numero == nfe.numero
                    ).order_by(PurchaseItemNFEMatch.match_score.desc()).first()
                    if best_saved_match and best_saved_match.nfe_item_id:
                        nfe_item_from_saved_match = db.session.get(
                            NFEItem, best_saved_match.nfe_item_id
                        )
                        if nfe_item_from_saved_match:
                            return nfe_item_from_saved_match

                linha_candidates = []
                if entry and entry.linha is not None:
                    try:
                        linha_candidates.append(int(entry.linha))
                    except (TypeError, ValueError):
                        pass
                if purchase_item and purchase_item.linha is not None:
                    try:
                        linha_candidates.append(int(purchase_item.linha))
                    except (TypeError, ValueError):
                        pass

                if purchase_item and nfe_items:
                    po_desc = (purchase_item.descricao or "").lower()
                    po_price = (
                        float(purchase_item.preco_unitario)
                        if purchase_item.preco_unitario is not None
                        else None
                    )
                    po_qty = (
                        float(purchase_item.quantidade)
                        if purchase_item.quantidade is not None
                        else None
                    )
                    po_item_code_raw = (purchase_item.item_id or "").strip()

                    def _closeness(a, b):
                        if a is None or b is None:
                            return None
                        a = float(a)
                        b = float(b)
                        if a <= 0 or b <= 0:
                            return None
                        diff_ratio = abs(a - b) / max(a, b)
                        return max(0.0, 1.0 - diff_ratio)

                    def _normalize_code(code_value):
                        if not code_value:
                            return None
                        normalized = "".join(
                            ch for ch in str(code_value).upper() if ch.isalnum()
                        )
                        return normalized or None

                    def _is_valid_code(code_value):
                        normalized = _normalize_code(code_value)
                        if not normalized:
                            return False
                        invalid_tokens = {
                            "SEMGTIN",
                            "NOGTIN",
                            "NA",
                            "NONE",
                            "NULL",
                            "0",
                            "000",
                            "0000",
                        }
                        if normalized in invalid_tokens:
                            return False
                        return len(normalized) >= 3

                    po_item_code = (
                        _normalize_code(po_item_code_raw)
                        if _is_valid_code(po_item_code_raw)
                        else None
                    )

                    # Calculate total item price for PO
                    po_total_price = None
                    if po_price is not None and po_qty is not None and po_price > 0 and po_qty > 0:
                        po_total_price = po_price * po_qty

                    def _code_match_score(po_code, nfe_code):
                        if not po_code or not _is_valid_code(nfe_code):
                            return None
                        normalized_nfe_code = _normalize_code(nfe_code)
                        if po_code == normalized_nfe_code:
                            return 1.0
                        # Allow strong partial match for structured material codes
                        if (
                            len(po_code) >= 6
                            and len(normalized_nfe_code) >= 6
                            and (
                                po_code.endswith(normalized_nfe_code)
                                or normalized_nfe_code.endswith(po_code)
                                or po_code in normalized_nfe_code
                                or normalized_nfe_code in po_code
                            )
                        ):
                            return 0.9
                        return 0.0

                    best_item = None
                    best_weighted_score = -1
                    best_desc_score = 0
                    best_price_score = 0

                    for nfe_item_candidate in nfe_items:
                        candidate_desc = (nfe_item_candidate.descricao or "").lower()
                        desc_score = (
                            fuzz.token_set_ratio(po_desc, candidate_desc) / 100.0
                            if po_desc and candidate_desc
                            else 0.0
                        )
                        price_score = _closeness(
                            po_price, nfe_item_candidate.valor_unitario_comercial
                        )
                        qty_score = _closeness(
                            po_qty, nfe_item_candidate.quantidade_comercial
                        )
                        code_score = _code_match_score(
                            po_item_code, nfe_item_candidate.codigo
                        )
                        line_score = (
                            1.0
                            if nfe_item_candidate.numero_item in linha_candidates
                            else 0.0
                        )

                        # Calculate total item price for NFE
                        nfe_total_price = None
                        nfe_qty = (
                            float(nfe_item_candidate.quantidade_comercial)
                            if nfe_item_candidate.quantidade_comercial is not None
                            else None
                        )
                        nfe_unit_price = (
                            float(nfe_item_candidate.valor_unitario_comercial)
                            if nfe_item_candidate.valor_unitario_comercial is not None
                            else None
                        )
                        if (nfe_unit_price is not None and nfe_qty is not None 
                            and nfe_unit_price > 0 and nfe_qty > 0):
                            nfe_total_price = nfe_unit_price * nfe_qty

                        # Calculate total price match score
                        total_price_score = _closeness(po_total_price, nfe_total_price)

                        # Dynamic weighting: boost price weight when total price matches perfectly
                        if total_price_score is not None and total_price_score >= 0.99:
                            # Perfect or near-perfect total price match: give price dominant weight
                            weight_desc = 0.10
                            weight_price = 0.75
                            weight_code = 0.10
                            weight_qty = 0.05
                        elif price_score is not None and price_score >= 0.98 and desc_score < 0.45:
                            # High unit price match with diverging description
                            weight_desc = 0.15
                            weight_price = 0.65
                            weight_code = 0.15
                            weight_qty = 0.05
                        else:
                            # Default weights
                            weight_desc = 0.45
                            weight_price = 0.35
                            weight_code = 0.15
                            weight_qty = 0.05

                        weighted_sum = desc_score * weight_desc
                        weight_total = weight_desc

                        if price_score is not None:
                            weighted_sum += price_score * weight_price
                            weight_total += weight_price
                        if code_score is not None:
                            weighted_sum += code_score * weight_code
                            weight_total += weight_code
                        if qty_score is not None:
                            weighted_sum += qty_score * weight_qty
                            weight_total += weight_qty

                        # Soft tie-breaker bonus for matching line number.
                        if linha_candidates:
                            weighted_sum += line_score * 0.03
                            weight_total += 0.03

                        final_score = (
                            (weighted_sum / weight_total) if weight_total > 0 else 0.0
                        )

                        if final_score > best_weighted_score:
                            best_weighted_score = final_score
                            best_desc_score = desc_score
                            best_price_score = price_score or 0.0
                            best_item = nfe_item_candidate

                    # Accept high-confidence code match quickly.
                    if best_item and po_item_code and _is_valid_code(best_item.codigo):
                        if _normalize_code(best_item.codigo) == po_item_code:
                            return best_item

                    # Require reasonable confidence; allow price-led match when price is almost exact.
                    if best_item and (
                        best_desc_score >= 0.60
                        or best_weighted_score >= 0.72
                        or (best_price_score >= 0.99 and best_weighted_score >= 0.64)
                    ):
                        return best_item

                # Last fallback: strict line/item number mapping when present
                for linha_cand in linha_candidates:
                    if linha_cand in nfe_items_by_numero:
                        return nfe_items_by_numero[linha_cand]

                return None
            # Get matched items if searching by item
            matched_items = []
            if search_by_item:
                if exact_term_search:
                    items = NFEItem.query.filter(
                        NFEItem.nfe_id == nfe.id,
                        NFEItem.descricao == query
                    ).all()
                else:
                    items = NFEItem.query.filter(
                        NFEItem.nfe_id == nfe.id,
                        NFEItem.descricao.ilike(f'%{query}%')
                    ).all()
                matched_items = [item.descricao for item in items[:3]]  # Limit to 3
            
            # Find linked purchase orders via NFEntry for this NFE
            # Only include purchases where the supplier matches the NFE emitente
            linked_purchases = []
            estimated_purchases = []
            if nfe.numero:
                nf_entries = NFEntry.query.filter(NFEntry.num_nf == nfe.numero).all()
                for entry in nf_entries:
                    po = PurchaseOrder.query.filter_by(
                        cod_pedc=entry.cod_pedc,
                        cod_emp1=entry.cod_emp1
                    ).first()
                    if po:
                        item = PurchaseItem.query.filter_by(
                            cod_pedc=entry.cod_pedc,
                            cod_emp1=entry.cod_emp1,
                            linha=str(entry.linha) if entry.linha else None
                        ).first()
                        nfe_item = _resolve_nfe_item_for_purchase(entry, item)

                        # Calculate adjusted total from adjustments
                        adjustments = getattr(po, 'adjustments', [])
                        base_total = po.total_pedido_com_ipi or 0
                        adjusted_total = apply_adjustments(base_total, adjustments) + (po.vlr_frete_tra or 0)
                        
                        purchase_info = {
                            'cod_pedc': po.cod_pedc,
                            'cod_emp1': po.cod_emp1,
                            'fornecedor': po.fornecedor_descricao,
                            'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                            'total_pedido': adjusted_total,
                            'func_nome': po.func_nome,
                            'vlr_icms_st': po.vlr_icms_st,
                            'moeped': po.moeped,
                            'for_uf': po.for_uf,
                            'tra_cod': po.tra_cod,
                            'tra_descricao': po.tra_descricao,
                            'tra_uf': po.tra_uf,
                            'red_cod': po.red_cod,
                            'red_descricao2': po.red_descricao2,
                            'red_uf': po.red_uf,
                            'tp_frete_tra': po.tp_frete_tra,
                            'tp_vlr_frete_tra': po.tp_vlr_frete_tra,
                            'moetra': po.moetra,
                            'vlr_frete_tra': po.vlr_frete_tra,
                            'tp_frete_red': po.tp_frete_red,
                            'tp_vlr_frete_red': po.tp_vlr_frete_red,
                            'moered': po.moered,
                            'vlr_frete_red': po.vlr_frete_red,
                            'num_talao': po.num_talao,
                            'tipo': po.tipo,
                            'item_descricao': item.descricao if item else None,
                            'linha': entry.linha,
                            'quantidade': item.quantidade if item else None,
                            'qtde_atendida': item.qtde_atendida if item else None,
                            'qtde_saldo': item.qtde_saldo if item else None,
                            'preco_unitario': item.preco_unitario if item else None,
                            'total_item': item.total if item else None,
                            'unidade_medida': item.unidade_medida if item else None,
                            'dt_entrega': item.dt_entrega.isoformat() if item and item.dt_entrega else None,
                            'nfe_numero': nfe.numero,
                            'is_estimated': False,
                            'nfe_item_numero': nfe_item.numero_item if nfe_item else None,
                            'nfe_item_descricao': nfe_item.descricao if nfe_item else None,
                            'nfe_item_quantidade': nfe_item.quantidade_comercial if nfe_item else None,
                            'nfe_item_unidade': nfe_item.unidade_comercial if nfe_item else None,
                            'nfe_item_preco': nfe_item.valor_unitario_comercial if nfe_item else None,
                        }
                        
                        key = (po.cod_pedc, po.cod_emp1, entry.linha)
                        
                        # Track all potential purchases
                        if key not in all_potential_purchases:
                            all_potential_purchases[key] = purchase_info
                        
                        # Check if supplier matches NFE emitente
                        if _check_supplier_match(po, emitente):
                            linked_purchases.append(purchase_info)
                            linked_purchase_keys.add(key)
                
                # Also include estimated matches from PurchaseItemNFEMatch for this NFE
                if include_estimated:
                    estimated_matches = PurchaseItemNFEMatch.query.filter(
                        PurchaseItemNFEMatch.nfe_numero == nfe.numero
                    ).all()
                    
                    for match in estimated_matches:
                        item = db.session.get(PurchaseItem, match.purchase_item_id)
                        if item:
                            po = db.session.get(PurchaseOrder, item.purchase_order_id)
                            if po:
                                # Check if already in linked_purchases
                                key = (po.cod_pedc, po.cod_emp1, str(item.linha) if item.linha else None)
                                already_linked = any(
                                    p['cod_pedc'] == po.cod_pedc and p['linha'] == item.linha 
                                    for p in linked_purchases
                                )
                                if not already_linked:
                                    nfe_item = _resolve_nfe_item_for_purchase(None, item, match)
                                    purchase_info = {
                                        'cod_pedc': po.cod_pedc,
                                        'cod_emp1': po.cod_emp1,
                                        'fornecedor': po.fornecedor_descricao,
                                        'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                                        'total_pedido': po.total_liquido,
                                        'func_nome': po.func_nome,
                                        'item_descricao': item.descricao,
                                        'linha': item.linha,
                                        'quantidade': item.quantidade,
                                        'qtde_atendida': item.qtde_atendida,
                                        'qtde_saldo': item.qtde_saldo,
                                        'preco_unitario': item.preco_unitario,
                                        'total_item': item.total,
                                        'unidade_medida': item.unidade_medida,
                                        'dt_entrega': item.dt_entrega.isoformat() if item.dt_entrega else None,
                                        'nfe_numero': nfe.numero,
                                        'is_estimated': True,
                                        'match_score': match.match_score,
                                        'nfe_item_numero': nfe_item.numero_item if nfe_item else None,
                                        'nfe_item_descricao': match.nfe_item_descricao or (nfe_item.descricao if nfe_item else None),
                                        'nfe_item_quantidade': match.nfe_item_quantidade,
                                        'nfe_item_unidade': nfe_item.unidade_comercial if nfe_item else None,
                                        'nfe_item_preco': match.nfe_item_preco,
                                    }
                                    estimated_purchases.append(purchase_info)
            
            nfe_results.append({
                'id': nfe.id,
                'numero': nfe.numero,
                'chave': nfe.chave,
                'data_emissao': nfe.data_emissao.isoformat() if nfe.data_emissao else None,
                'valor_total': nfe.valor_total,
                'fornecedor': emitente.nome if emitente else None,
                'cnpj': emitente.cnpj if emitente else None,
                'matched_items': matched_items,
                'linked_purchases': linked_purchases,
                'estimated_purchases': estimated_purchases,
                'nfe_items': [{
                    'id': item.id,
                    'numero_item': item.numero_item,
                    'descricao': item.descricao,
                    'unidade': item.unidade_comercial,
                    'quantidade': item.quantidade_comercial,
                    'preco_unitario': item.valor_unitario_comercial,
                } for item in nfe_items],
            })
            if nfe.numero:
                nfe_numbers.add(nfe.numero)
        
        # Build unlinked_purchases_map: purchases that didn't match ANY NFE
        unlinked_purchases_map = {
            k: v for k, v in all_potential_purchases.items() 
            if k not in linked_purchase_keys
        }
        
        # Find linked purchase orders
        purchase_orders = []
        
        # 1. Search in NFEntry (direct links)
        if exact_term_search:
            nf_entries = NFEntry.query.filter(NFEntry.num_nf == query).all()
        else:
            nf_entries = NFEntry.query.filter(
                or_(
                    NFEntry.num_nf == query,
                    NFEntry.num_nf.ilike(f'%{query}%') #??
                )
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        
        for entry in nf_entries:
            po = PurchaseOrder.query.filter_by(
                cod_pedc=entry.cod_pedc,
                cod_emp1=entry.cod_emp1
            ).first()
            
            if po:
                item = PurchaseItem.query.filter_by(
                    cod_pedc=entry.cod_pedc,
                    cod_emp1=entry.cod_emp1,
                    linha=str(entry.linha) if entry.linha else None
                ).first()
                
                # Check if this purchase was already linked to any NFE
                purchase_key = (po.cod_pedc, po.cod_emp1, entry.linha)
                is_linked = purchase_key in linked_purchase_keys
                
                # Find linked NFEData for this num_nf
                linked_nfe_data = None
                if entry.num_nf:
                    nfe_data = NFEData.query.filter_by(numero=entry.num_nf).first()
                    if nfe_data:
                        emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                        
                        linked_nfe_data = {
                            'id': nfe_data.id,
                            'numero': nfe_data.numero,
                            'chave': nfe_data.chave,
                            'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                            'valor_total': nfe_data.valor_total,
                            'fornecedor': emitente.nome if emitente else None,
                            'cnpj': emitente.cnpj if emitente else None,
                        }
                
                purchase_orders.append({
                    'cod_pedc': po.cod_pedc,
                    'cod_emp1': po.cod_emp1,
                    'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                    'fornecedor': po.fornecedor_descricao,
                    'item_descricao': item.descricao if item else None,
                    'valor': item.total if item else po.total_liquido,
                    'match_type': 'linked' if is_linked else 'unlinked',
                    'nfe_numero': entry.num_nf,
                    'nfe_data': linked_nfe_data,
                })
        
        # 2. Search in PurchaseItemNFEMatch (AI-estimated matches)
        if include_estimated:
            if exact_term_search:
                estimated_matches = PurchaseItemNFEMatch.query.filter(
                    PurchaseItemNFEMatch.nfe_numero == query
                ).all()
            else:
                estimated_matches = PurchaseItemNFEMatch.query.filter(
                    or_(
                        PurchaseItemNFEMatch.nfe_numero == query,
                        PurchaseItemNFEMatch.nfe_numero.ilike(f'%{query}%')
                    )
                ).all()
            
            for match in estimated_matches:
                item = db.session.get(PurchaseItem, match.purchase_item_id)
                if item:
                    po = db.session.get(PurchaseOrder, item.purchase_order_id)
                    if po:
                        # Check if this PO is already in the list
                        existing = next(
                            (p for p in purchase_orders 
                             if p['cod_pedc'] == po.cod_pedc and p.get('item_descricao') == item.descricao),
                            None
                        )
                        if not existing:
                            # Check if this purchase was linked to any NFE
                            # For estimated matches, we check by (cod_pedc, cod_emp1, linha)
                            purchase_key = (po.cod_pedc, po.cod_emp1, str(item.linha) if item.linha else None)
                            is_linked = purchase_key in linked_purchase_keys
                            
                            # Find linked NFEData for this nfe_numero
                            linked_nfe_data = None
                            if match.nfe_numero:
                                nfe_data = NFEData.query.filter_by(numero=match.nfe_numero).first()
                                if nfe_data:
                                    emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                                    
                                    linked_nfe_data = {
                                        'id': nfe_data.id,
                                        'numero': nfe_data.numero,
                                        'chave': nfe_data.chave,
                                        'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                                        'valor_total': nfe_data.valor_total,
                                        'fornecedor': emitente.nome if emitente else None,
                                        'cnpj': emitente.cnpj if emitente else None,
                                    }
                            
                            purchase_orders.append({
                                'cod_pedc': po.cod_pedc,
                                'cod_emp1': po.cod_emp1,
                                'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                                'fornecedor': po.fornecedor_descricao,
                                'item_descricao': item.descricao,
                                'valor': item.total,
                                'match_type': 'estimated' if is_linked else 'estimated_unlinked',
                                'match_score': match.match_score,
                                'nfe_numero': match.nfe_numero,
                                'nfe_data': linked_nfe_data,
                            })
        
        # 3. Search by purchase order number (cod_pedc) to find linked NFEs
        if exact_term_search:
            purchase_entries = NFEntry.query.filter(
                NFEntry.cod_pedc == query
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        else:
            purchase_entries = NFEntry.query.filter(
                NFEntry.cod_pedc.ilike(f'%{query}%')
            ).order_by(NFEntry.cod_pedc.desc()).limit(100).all()
        
        for entry in purchase_entries:
            # Check if already added from section 1
            already_added = any(
                p['cod_pedc'] == entry.cod_pedc and p.get('nfe_numero') == entry.num_nf 
                for p in purchase_orders
            )
            if already_added:
                continue
                
            po = PurchaseOrder.query.filter_by(
                cod_pedc=entry.cod_pedc,
                cod_emp1=entry.cod_emp1
            ).first()
            
            if po:
                item = PurchaseItem.query.filter_by(
                    cod_pedc=entry.cod_pedc,
                    cod_emp1=entry.cod_emp1,
                    linha=str(entry.linha) if entry.linha else None
                ).first()
                
                # Check if this purchase was linked to any NFE
                purchase_key = (po.cod_pedc, po.cod_emp1, entry.linha)
                is_linked = purchase_key in linked_purchase_keys
                
                # Find linked NFEData for this num_nf
                linked_nfe_data = None
                if entry.num_nf:
                    nfe_data = NFEData.query.filter_by(numero=entry.num_nf).first()
                    if nfe_data:
                        emitente = NFEEmitente.query.filter_by(nfe_id=nfe_data.id).first()
                        
                        linked_nfe_data = {
                            'id': nfe_data.id,
                            'numero': nfe_data.numero,
                            'chave': nfe_data.chave,
                            'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                            'valor_total': nfe_data.valor_total,
                            'fornecedor': emitente.nome if emitente else None,
                            'cnpj': emitente.cnpj if emitente else None,
                        }
                        # Also add to nfe_results if not already there and is_linked
                        if is_linked and not any(n['id'] == nfe_data.id for n in nfe_results):
                            nfe_data_items = NFEItem.query.filter_by(nfe_id=nfe_data.id).all()
                            nfe_results.append({
                                'id': nfe_data.id,
                                'numero': nfe_data.numero,
                                'chave': nfe_data.chave,
                                'data_emissao': nfe_data.data_emissao.isoformat() if nfe_data.data_emissao else None,
                                'valor_total': nfe_data.valor_total,
                                'fornecedor': emitente.nome if emitente else None,
                                'cnpj': emitente.cnpj if emitente else None,
                                'matched_items': [],
                                'linked_purchases': [{
                                    'cod_pedc': po.cod_pedc,
                                    'cod_emp1': po.cod_emp1,
                                    'fornecedor': po.fornecedor_descricao,
                                    'item_descricao': item.descricao if item else None,
                                    'linha': entry.linha,
                                }],
                                'estimated_purchases': [],
                                'nfe_items': [{
                                    'id': nfe_item.id,
                                    'numero_item': nfe_item.numero_item,
                                    'descricao': nfe_item.descricao,
                                    'unidade': nfe_item.unidade_comercial,
                                    'quantidade': nfe_item.quantidade_comercial,
                                    'preco_unitario': nfe_item.valor_unitario_comercial,
                                } for nfe_item in nfe_data_items],
                            })
                
                purchase_orders.append({
                    'cod_pedc': po.cod_pedc,
                    'cod_emp1': po.cod_emp1,
                    'dt_emis': po.dt_emis.isoformat() if po.dt_emis else None,
                    'fornecedor': po.fornecedor_descricao,
                    'item_descricao': item.descricao if item else None,
                    'valor': item.total if item else po.total_liquido,
                    'match_type': 'linked' if is_linked else 'unlinked',
                    'nfe_numero': entry.num_nf,
                    'nfe_data': linked_nfe_data,
                })
        
        # Convert unlinked_purchases_map to list and sort by dt_emis (most recent first)
        unlinked_purchase_orders = sorted(
            unlinked_purchases_map.values(),
            key=lambda x: x.get('dt_emis') or '',
            reverse=True
        )
        
        return jsonify({
            'nfes': nfe_results,
            'purchase_orders': purchase_orders,
            'unlinked_purchase_orders': unlinked_purchase_orders,
            'query': query,
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500