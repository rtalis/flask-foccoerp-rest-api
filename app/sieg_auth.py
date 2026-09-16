import requests
from datetime import datetime, timedelta
from app.models import SiegToken
from app import db
from config import Config

def get_jwt_token():
    """Generates a new JWT token if expired, or returns the active one."""
    token_record = SiegToken.query.filter_by(token_type='JWT').first()
    
    # If token exists and is valid for at least 1 more hour
    if token_record and token_record.expires_at > (datetime.now() + timedelta(hours=1)):
        return token_record.access_token

    # Otherwise, generate a new one
    headers = {
        'clientId': Config.SIEG_CLIENT_ID,
        'secretKey': Config.SIEG_SECRET_KEY,
        'Accept': 'application/json'
    }
    response = requests.post('https://api.sieg.com/api/v1/create-jwt', headers=headers)
    response.raise_for_status()
    
    new_token = response.json().get('Token')
    
    if not token_record:
        token_record = SiegToken(token_type='JWT')
        db.session.add(token_record)
        
    token_record.access_token = new_token
    token_record.expires_at = datetime.now() + timedelta(hours=23) # Expires in 24h
    db.session.commit()
    
    return new_token