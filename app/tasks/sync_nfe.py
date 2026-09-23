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
import base64
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
            else:
                logger.error(f"Error {response.status_code} fetching XMLs: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            time.sleep(backoff)
            backoff *= 2

    return all_xmls


def fetch_sieg_events(payload):
    """Fetches document events (Cancellations, CC-e) from /api/v1/baixar-eventos."""
    jwt_token = get_jwt_token()
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'x-api-key': Config.SIEG_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload['Take'] = 50
    payload['Skip'] = 0
    all_events = []

    while True:
        try:
            response = requests.post('https://api.sieg.com/api/v1/baixar-eventos', json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                data = response.json()
                events = data.get('Eventos', [])
                if not events:
                    break

                all_events.extend(events)
                if len(events) < 50:
                    break

                payload['Skip'] += 50
                time.sleep(REQUEST_DELAY_SECONDS)
            else:
                break
        except requests.RequestException:
            break

    return all_events


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
        total_synced = 0

        for company in companies:
            if not company.cnpj:
                continue

            clean_cnpj = ''.join(filter(str.isdigit, company.cnpj))
            logger.info(f"Processing company: {company.name} ({clean_cnpj})")

            # Sync NF-e (1) and NFS-e (3)
            for xml_type in [1, 3]:
                payload = {
                    "TipoXml": xml_type,
                    "DataEmissaoInicio": f"{start_date_str}T00:00:00.000Z",
                    "DataEmissaoFim": f"{end_date_str}T23:59:59.999Z",
                    "CnpjDest": clean_cnpj
                }

                xml_list = fetch_sieg_zip_paginated('https://api.sieg.com/api/v1/baixar-xmls', payload, company.name)

                for xml_content in xml_list:
                    chave = extract_document_key(xml_content)
                    if not chave or NFEData.query.filter_by(chave=chave).first():
                        continue

                    try:
                        if xml_type == 1:
                            parse_and_store_nfe_xml(xml_content)
                        elif xml_type == 3:
                            parse_and_store_nfse_xml(xml_content, chave)
                        total_synced += 1
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error parsing document {chave}: {e}")

            # Sync Events
            events_payload = {
                "TipoXml": 1,
                "DataInicioEvento": f"{start_date_str}T00:00:00.000Z",
                "DataFimEvento": f"{end_date_str}T23:59:59.999Z",
                "CnpjDest": clean_cnpj
            }
            events = fetch_sieg_events(events_payload)

            for evt in events:
                chave_doc = evt.get('ChaveXml')
                nfe = NFEData.query.filter_by(chave=chave_doc).first()
                if not nfe:
                    continue

                protocolo = str(evt.get('Protocolo', ''))
                if not NFEEvento.query.filter_by(protocolo=protocolo).first():
                    data_str = evt.get('DataEvento', '')
                    data_evento = datetime.strptime(data_str[:19], "%Y-%m-%dT%H:%M:%S") if data_str else datetime.now()
                    xml_evt = base64.b64decode(evt.get('Xml')).decode('utf-8') if evt.get('Xml') else None
                    
                    try:
                        novo_evento = NFEEvento(
                            nfe_id=nfe.id,
                            tipo_evento=evt.get('TipoEvento'),
                            descricao=evt.get('Descricao'),
                            protocolo=protocolo,
                            data_evento=data_evento,
                            xml_content=xml_evt
                        )
                        db.session.add(novo_evento)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error saving event for document {chave_doc}: {e}")

            time.sleep(REQUEST_DELAY_SECONDS)

        logger.info(f"Sync complete. New documents processed: {total_synced}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manual trigger for NFE sync via SIEG API.")
    parser.add_argument('--start', type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument('--end', type=str, help="End date in YYYY-MM-DD format")
    parser.add_argument('--company', type=int, help="Specific Company ID to sync")
    args = parser.parse_args()

    run_sync(start_date_str=args.start, end_date_str=args.end, company_id=args.company)