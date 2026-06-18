"""
Script to sync NFE data from SIEG API for the previous day
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import base64
import xml.etree.ElementTree as ET
import time
import requests
from flask import current_app

s = sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.utils import parse_and_store_nfe_xml
from app.models import NFEData, Company
from config import Config

# ------------------------------
# Configuration for rate limiting
# ------------------------------
REQUEST_DELAY_SECONDS = 2      # Wait between companies (to avoid 429)
MAX_RETRIES = 3                # Number of retries on 429
INITIAL_BACKOFF = 5            # Initial backoff seconds for 429

# ------------------------------
# Logging setup
# ------------------------------
logger = logging.getLogger('nfe_sync')
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler (if writable)
try:
    log_dir = "/var/log/foccoerp"
    if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
        file_handler = logging.FileHandler(os.path.join(log_dir, "nfe_sync.log"))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
except Exception:
    pass  


def make_sieg_request_with_retry(company, start_date_str, end_date_str, max_retries=MAX_RETRIES):
    """
    Make a request to SIEG API with exponential backoff on 429 errors.
    Returns the response JSON on success, or raises an exception on failure.
    """
    cnpj = ''.join(filter(str.isdigit, company.cnpj))
    sieg_request_data = {
        "XmlType": 1,
        "DataEmissaoInicio": start_date_str,
        "DataEmissaoFim": end_date_str,
        "CnpjDest": cnpj,
    }

    url = f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    backoff = INITIAL_BACKOFF
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            response = requests.post(url, json=sieg_request_data, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                logger.info(f"No NFEs found for company {company.name}")
                return {"xmls": []}
            if response.status_code == 400:
                logger.error(f"Bad Request for company {company.name}: {response.text}")
                return {"xmls": []}

            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = backoff
                else:
                    wait = backoff

                logger.warning(
                    f"Rate limited (429) for company {company.name}. "
                    f"Retry {attempt+1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
                backoff *= 2  # exponential backoff
                continue

            # Other non-200 statuses – raise exception
            logger.error(f"API error for {company.name}: {response.status_code} - {response.text}")
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception for {company.name}: {e}")
            if attempt < max_retries:
                wait = backoff
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
                backoff *= 2
            else:
                raise  # re-raise after all retries

    raise Exception(f"Failed to fetch NFEs for {company.name} after {max_retries} retries")


def sync_nfe_for_yesterday():
    """
    Sync NFE data from SIEG API for the previous day
    """
    app = create_app()
    with app.app_context():
        logger.info("Starting NFE sync for yesterday")

        # Calculate date range for yesterday
        today = datetime.now().date()
        yesterday = today - timedelta(days=5)
        start_date_str = yesterday.strftime('%Y-%m-%d')
        end_date_str = today.strftime('%Y-%m-%d')

        # Get all companies from the database
        companies = Company.query.all()

        if not companies:
            logger.warning("No companies found in the database")

        total_nfes = 0
        new_nfes = 0

        # Process each company with a delay between requests
        for idx, company in enumerate(companies):
            # Skip companies without CNPJ
            if not company.cnpj:
                logger.warning(f"Company {company.name} (cod_emp1: {company.cod_emp1}) has no CNPJ")
                continue

            logger.info(f"Fetching NFEs for company {company.name} (CNPJ: {company.cnpj})")

            try:
                # Make request with retry logic
                result = make_sieg_request_with_retry(company, start_date_str, end_date_str)

                if 'xmls' not in result or not result['xmls']:
                    logger.info(f"No NFEs found for company {company.name}")
                else:
                    logger.info(f"Found {len(result['xmls'])} NFEs for company {company.name}")

                    # Process each NFE
                    for xml_base64 in result['xmls']:
                        try:
                            # Decode XML
                            xml_content = base64.b64decode(xml_base64).decode('utf-8')

                            # Parse XML to get access key
                            root = ET.fromstring(xml_content)
                            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

                            chave_acesso_elem = root.find('.//nfe:protNFe/nfe:infProt/nfe:chNFe', ns)
                            if chave_acesso_elem is None or not chave_acesso_elem.text:
                                logger.warning("Skipping NFE without access key")
                                continue

                            chave_acesso = chave_acesso_elem.text

                            # Check if NFE already exists
                            existing_nfe = NFEData.query.filter_by(chave=chave_acesso).first()
                            if existing_nfe:
                                logger.info(f"NFE {chave_acesso} already exists in database")
                                continue

                            # Store NFE in database
                            nfe_data = parse_and_store_nfe_xml(xml_content)
                            logger.info(f"Stored new NFE: {chave_acesso}")
                            new_nfes += 1

                        except Exception as e:
                            logger.error(f"Error processing NFE: {str(e)}")
                            continue

                    total_nfes += len(result['xmls'])

            except Exception as e:
                logger.error(f"Error processing company {company.name}: {str(e)}")
                # Continue with next company

            # Cooldown between companies (except after the last one)
            if idx < len(companies) - 1:
                logger.info(f"Waiting {REQUEST_DELAY_SECONDS}s before next company...")
                time.sleep(REQUEST_DELAY_SECONDS)

        logger.info(f"NFE sync completed. Processed {total_nfes} NFEs, added {new_nfes} new NFEs")

        return {
            "status": "success",
            "total_nfes": total_nfes,
            "new_nfes": new_nfes
        }


if __name__ == "__main__":
    sync_nfe_for_yesterday()