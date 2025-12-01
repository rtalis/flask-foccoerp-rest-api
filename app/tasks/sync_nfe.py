"""
Script to sync NFE data from SIEG API for the previous day
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import base64
import xml.etree.ElementTree as ET
from flask import current_app

s = sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.utils import parse_and_store_nfe_xml
from app.models import NFEData, Company
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/var/log/foccoerp/nfe_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('nfe_sync')

def sync_nfe_for_yesterday():
    """
    Sync NFE data from SIEG API for the previous day
    """
    import requests
    
    app = create_app()
    with app.app_context():
        logger.info("Starting NFE sync for yesterday")
        
        # Calculate date range for yesterday
        today = datetime.now().date()
        yesterday = today - timedelta(days=4) 
        start_date_str = yesterday.strftime('%Y-%m-%d')
        end_date_str = today.strftime('%Y-%m-%d')
        
        # Get all companies from the database
        companies = Company.query.all()
        
        if not companies:
            logger.warning("No companies found in the database")
            
        total_nfes = 0
        new_nfes = 0
        
        # For each company, get NFEs
        for company in companies:
            try:
                # Skip companies without CNPJ
                if not company.cnpj:
                    logger.warning(f"Company {company.name} (cod_emp1: {company.cod_emp1}) has no CNPJ")
                    continue
                
                # Clean CNPJ
                cnpj = ''.join(filter(str.isdigit, company.cnpj))
                
                logger.info(f"Fetching NFEs for company {company.name} (CNPJ: {cnpj})")
                
                # Prepare request to SIEG API
                sieg_request_data = {
                    "XmlType": 1,  # 1 for NFE
                    "Take": 0,
                    "Skip": 0,
                    "DataEmissaoInicio": start_date_str,
                    "DataEmissaoFim": end_date_str,
                    "CnpjDest": cnpj,  # Company as recipient
                    "CnpjEmit": "",
                    "CnpjRem": "",
                    "CnpjTom": "",
                    "Tag": "",
                    "Downloadevent": True,
                    "TypeEvent": 0
                }
                
                # Make request to SIEG API
                response = requests.post(
                    f'https://api.sieg.com/BaixarXmlsV2?api_key={Config.SIEG_API_KEY}',
                    json=sieg_request_data,
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                )
                
                if response.status_code != 200:
                    logger.error(f"Error fetching NFEs for company {company.name}: {response.status_code} - {response.text}")
                    continue
                
                result = response.json()
                
                if 'xmls' not in result or not result['xmls']:
                    logger.info(f"No NFEs found for company {company.name}")
                    continue
                
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
                            # Skip invalid XML or NFe without access key
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
                continue
        
        logger.info(f"NFE sync completed. Processed {total_nfes} NFEs, added {new_nfes} new NFEs")
        
        return {
            "status": "success",
            "total_nfes": total_nfes,
            "new_nfes": new_nfes
        }

if __name__ == "__main__":
    sync_nfe_for_yesterday()