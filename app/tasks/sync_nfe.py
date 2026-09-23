"""
Sync routine for SIEG API v1: NF-e, NFS-e, and Events.
"""
import os
import sys
import io
import zipfile
import logging
import re
import time
import argparse
from datetime import datetime, timedelta
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models import NFEData, Company, NFEEvento
from app.utils import parse_and_store_nfe_xml, parse_and_store_nfse_xml
from app.sieg_auth import get_jwt_token
from config import Config

REQUEST_DELAY_SECONDS = 2
INITIAL_BACKOFF = 5

logger = logging.getLogger('nfe_sync')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def fetch_sieg_zip_paginated(url, payload, company_name):
    """Fetches paginated binary ZIP responses and returns uncompressed XML strings."""
    jwt_token = get_jwt_token()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'x-api-key': Config.SIEG_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    all_xmls = []
    payload['Take'] = 50
    payload['Skip'] = 0
    backoff = INITIAL_BACKOFF
    xml_type_name = "NFS-e" if payload.get("TipoXml") == 3 else "NF-e"

    while True:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)

            if response.status_code == 200:
                if not response.content:
                    break

                try:
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        xml_names = [name for name in z.namelist() if name.lower().endswith('.xml')]
                        if not xml_names:
                            break

                        for name in xml_names:
                            with z.open(name) as f:
                                all_xmls.append(f.read().decode('utf-8'))

                        if len(xml_names) < 50:
                            break

                except zipfile.BadZipFile:
                    logger.error(f"Response was not a valid ZIP for {company_name}: {response.text[:200]}")
                    break

                payload['Skip'] += 50
                time.sleep(REQUEST_DELAY_SECONDS)
                backoff = INITIAL_BACKOFF

            elif response.status_code == 429:
                wait = int(response.headers.get('Retry-After', backoff))
                logger.warning(f"Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                backoff *= 2
                continue
                
            elif response.status_code in (400, 404):
                try:
                    err_data = response.json()
                    err_msg = err_data.get("ErrorMessage", "")
                    
                    if response.status_code == 404 or "Nenhum arquivo" in err_msg:
                        pass # Silently ignore so we can print the final tally at the end instead
                    else:
                        logger.warning(f"SIEG rejected {xml_type_name} request for {company_name}: {err_msg}")
                except ValueError:
                    logger.warning(f"API returned {response.status_code} for {company_name}: {response.text}")
                break
                
            else:
                logger.error(f"Error {response.status_code} fetching XMLs: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            time.sleep(backoff)
            backoff *= 2

    return all_xmls


def extract_document_key(xml_content):
    """Extracts 44-digit NF-e key or 50-digit national NFS-e key."""
    match = re.search(r'Id="(?:NFe|CFe|CTe|NFS)(\d{44,50})"', xml_content, re.IGNORECASE)
    if match:
        return match.group(1)
    tag_match = re.search(r'<(?:chNFe|chCTe|chCFe)>(\d{44})</(?:chNFe|chCTe|chCFe)>', xml_content)
    if tag_match:
        return tag_match.group(1)
    return None


def run_sync(start_date_str=None, end_date_str=None, company_id=None):
    """Main execution routine with optional filters."""
    app = create_app()
    with app.app_context():
        logger.info("Starting synchronization process...")
        
        if not start_date_str or not end_date_str:
            today = datetime.now().date()
            yesterday = today - timedelta(days=2)
            start_date_str = yesterday.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')

        logger.info(f"Sync timeframe: {start_date_str} to {end_date_str}")

        query = Company.query
        if company_id:
            query = query.filter_by(id=company_id)
            
        companies = query.all()
        
        # Global Counters
        global_xmls_new = 0
        global_xmls_skipped = 0
        global_events_new = 0
        global_events_skipped = 0

        for company in companies:
            if not company.cnpj:
                continue

            clean_cnpj = ''.join(filter(str.isdigit, company.cnpj))
            logger.info(f"Processing company: {company.name} ({clean_cnpj})")
            
            company_xmls_new = 0
            company_xmls_skipped = 0
            company_events_new = 0
            company_events_skipped = 0

            # Sync NF-e (1) and NFS-e (3)
            for xml_type in [1, 3]:
                payload = {
                    "TipoXml": xml_type,
                    "DataEmissaoInicio": start_date_str,
                    "DataEmissaoFim": end_date_str,
                    "CnpjDest": clean_cnpj,
                    "BaixarEventos": True  # Force SIEG to include events in the ZIP
                }

                xml_list = fetch_sieg_zip_paginated('https://api.sieg.com/api/v1/baixar-xmls', payload, company.name)

                invoices_xmls = []
                events_xmls = []

                # Separate Invoices from Events
                for xml_content in xml_list:
                    if 'procEventoNFe' in xml_content or 'resEvento' in xml_content or '<evento' in xml_content:
                        events_xmls.append(xml_content)
                    else:
                        invoices_xmls.append(xml_content)

                # 1. Process Invoices FIRST so they exist in the DB
                for xml_content in invoices_xmls:
                    chave = extract_document_key(xml_content)
                    if not chave:
                        continue
                        
                    if NFEData.query.filter_by(chave=chave).first():
                        company_xmls_skipped += 1
                        continue

                    try:
                        if xml_type == 1:
                            parse_and_store_nfe_xml(xml_content)
                        elif xml_type == 3:
                            parse_and_store_nfse_xml(xml_content, chave)
                            
                        company_xmls_new += 1
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error parsing document {chave}: {e}")

                # 2. Process Events SECOND and link them to the newly saved Invoices
                for xml_content in events_xmls:
                    chave_match = re.search(r'<chNFe[^>]*>(\d+)</chNFe>', xml_content)
                    if not chave_match:
                        continue
                        
                    chave_doc = chave_match.group(1)
                    
                    nfe = NFEData.query.filter_by(chave=chave_doc).first()
                    if not nfe:
                        # NFE not in DB (might have been issued outside our date range filter)
                        company_events_skipped += 1
                        continue 

                    prot_match = re.search(r'<nProt[^>]*>(\d+)</nProt>', xml_content)
                    protocolo = prot_match.group(1) if prot_match else "SEM_PROTOCOLO"
                    
                    if NFEEvento.query.filter_by(protocolo=protocolo).first():
                        company_events_skipped += 1
                        continue
                        
                    tp_match = re.search(r'<tpEvento[^>]*>(\d+)</tpEvento>', xml_content)
                    tipo_evento = tp_match.group(1) if tp_match else ""
                    
                    desc_match = re.search(r'<(?:xEvento|descEvento)[^>]*>([^<]+)</(?:xEvento|descEvento)>', xml_content)
                    descricao = desc_match.group(1) if desc_match else "Evento"
                    
                    data_match = re.search(r'<(?:dhRegEvento|dhEvento)[^>]*>([^<]+)</(?:dhRegEvento|dhEvento)>', xml_content)
                    data_str = data_match.group(1) if data_match else ""
                    
                    if data_str:
                        # Parse standard SEFAZ timestamp format (e.g. 2026-09-09T09:24:17-03:00)
                        data_evento = datetime.strptime(data_str[:19], "%Y-%m-%dT%H:%M:%S")
                    else:
                        data_evento = datetime.now()
                    
                    try:
                        novo_evento = NFEEvento(
                            nfe_id=nfe.id,
                            tipo_evento=tipo_evento,
                            descricao=descricao,
                            protocolo=protocolo,
                            data_evento=data_evento,
                            xml_content=xml_content # Saves the raw XML string, no base64 needed here
                        )
                        db.session.add(novo_evento)
                        db.session.commit()
                        company_events_new += 1
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error saving event for document {chave_doc}: {e}")

            logger.info(f"Completed {company.name} | XMLs: {company_xmls_new} new, {company_xmls_skipped} skipped | Events: {company_events_new} new, {company_events_skipped} skipped.")
            
            # Add to global counters
            global_xmls_new += company_xmls_new
            global_xmls_skipped += company_xmls_skipped
            global_events_new += company_events_new
            global_events_skipped += company_events_skipped
            
            time.sleep(REQUEST_DELAY_SECONDS)

        logger.info(
            f"Global Sync Complete | "
            f"Total XMLs: {global_xmls_new} new, {global_xmls_skipped} skipped | "
            f"Total Events: {global_events_new} new, {global_events_skipped} skipped."
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manual trigger for NFE sync via SIEG API.")
    parser.add_argument('--start', type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument('--end', type=str, help="End date in YYYY-MM-DD format")
    parser.add_argument('--company', type=int, help="Specific Company ID to sync")
    args = parser.parse_args()

    run_sync(start_date_str=args.start, end_date_str=args.end, company_id=args.company)