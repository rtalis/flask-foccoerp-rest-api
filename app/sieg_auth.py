import os
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from config import Config
from app import db
from app.models import SiegToken

# Ensure .env is loaded in standalone execution
load_dotenv()

def get_jwt_token():
    """Retrieves or refreshes the 24-hour JWT token from SIEG."""
    token_record = SiegToken.query.filter_by(token_type='JWT').first()

    # Reuse token if valid for at least 1 more hour
    if token_record and token_record.expires_at > (datetime.now() + timedelta(hours=1)):
        return token_record.access_token

    client_id = getattr(Config, 'SIEG_CLIENT_ID', None) or os.environ.get('SIEG_CLIENT_ID')
    secret_key = getattr(Config, 'SIEG_SECRET_KEY', None) or os.environ.get('SIEG_SECRET_KEY')

    if not client_id or not secret_key:
        raise ValueError(
            f"SIEG credentials missing! SIEG_CLIENT_ID={client_id}, SIEG_SECRET_KEY={'***' if secret_key else None}. "
            "Verify your .env file and config.py."
        )

    headers = {
        'Accept': 'application/json',
        'X-Client-Id': client_id.strip(),
        'X-Secret-Key': secret_key.strip(),
        'Content-Type': 'application/json'
    }

    # Pass data='' exactly like curl -d ''
    response = requests.post(
        'https://api.sieg.com/api/v1/create-jwt',
        headers=headers,
        data='',
        timeout=30
    )

    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Failed to generate JWT: {response.status_code} - {response.text}",
            response=response
        )

    response_data = response.json()
    
    # Handle the discrepancy in SIEG's API (sometimes it returns a dict, sometimes a raw string)
    if isinstance(response_data, dict):
        new_token = response_data.get('Token')
    elif isinstance(response_data, str):
        new_token = response_data
    else:
        new_token = None

    if not new_token:
        raise ValueError(f"Could not extract token from SIEG response: {response.text}")
    if not token_record:
        token_record = SiegToken(token_type='JWT')
        db.session.add(token_record)

    token_record.access_token = new_token
    token_record.expires_at = datetime.now() + timedelta(hours=23)
    db.session.commit()

    return new_token