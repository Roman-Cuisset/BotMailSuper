"""
Gmail Authentication Utilities (Device Flow)
Handles OAuth 2.0 Device Flow for user accounts
"""
import json
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from pathlib import Path
from utils.crypto import encrypt_password, decrypt_password
from database.db import get_db

logger = logging.getLogger(__name__)

# Scopes required for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Path to client secrets (same as bot's main credentials)
CREDENTIALS_FILE = Path("credentials.json")

def start_device_flow():
    """
    Initiates the OAuth 2.0 Device Flow.
    Returns (flow, verification_url, user_code)
    """
    if not CREDENTIALS_FILE.exists():
        logger.error(f"❌ credentials.json not found at {CREDENTIALS_FILE.absolute()}")
        return None, None, None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), SCOPES
        )
        # We can't use run_local_server because the user is remote (Telegram).
        # We need to manually trigger the device flow step.
        # However, InstalledAppFlow doesn't expose the device flow initiation easily 
        # without running the console loop.
        # We need to use the underlying oauthlib flow or a custom implementation.
        # Actually, InstalledAppFlow is for "Installed Apps".
        # For a bot where the user is remote, we should ideally use the "Device Authorization Flow".
        # But `google-auth-oauthlib` is high-level.
        
        # Let's use the underlying session to get the authorization URL.
        # Wait, for Device Flow we need a specific endpoint.
        # The standard InstalledAppFlow supports 'console' strategy which prints the URL.
        # But we want to get the URL and code programmatically to send to the user.
        
        # Let's try to use the flow object directly.
        # flow.authorization_url() gives the URL for the standard web flow.
        # For Device Flow (TVs etc), we need to use a different flow.
        # Google's library supports it via `google.oauth2.credentials`? No.
        
        # Let's stick to the standard Web Flow but "manual" copy-paste?
        # No, user wants "Device Flow" (enter code).
        # That requires the "Device Authorization Grant".
        # It seems `google-auth-oauthlib` doesn't support Device Flow out of the box easily?
        # Let's check if we can use `google_auth_oauthlib.flow.Flow`.
        
        # ALTERNATIVE: Use the standard "Copy-Paste" flow (OOB - Out of Band).
        # Google deprecated OOB for new clients.
        # So we MUST use Device Flow or a Web Server.
        # Since we don't have a web server exposed to the public (bot runs locally),
        # Device Flow is the best option.
        
        # To do Device Flow with Google, we need to make a POST request to the device endpoint.
        # Endpoint: https://oauth2.googleapis.com/device/code
        
        # Let's implement it manually using requests if the lib doesn't support it.
        # But wait, `google-auth` might have it.
        
        # Let's look at `google_auth_oauthlib`.
        # If not, we can use `requests` to hit the endpoint.
        
        # For simplicity and speed, let's try to use the standard "Console" flow 
        # but capture the URL? No, that's OOB which is deprecated.
        
        # Let's implement manual Device Flow.
        pass
        
    except Exception as e:
        logger.error(f"Error starting flow: {e}")
        return None, None, None

import requests
import os

def get_client_config():
    if not CREDENTIALS_FILE.exists():
        return None
    with open(CREDENTIALS_FILE, 'r') as f:
        data = json.load(f)
        return data.get('installed') or data.get('web')

def initiate_device_flow():
    """
    Manually initiate Google Device Flow
    """
    config = get_client_config()
    if not config:
        return None
        
    client_id = config['client_id']
    # client_secret is not needed for this step but needed for token exchange
    
    # Discovery doc: https://accounts.google.com/.well-known/openid-configuration
    # Device endpoint: https://oauth2.googleapis.com/device/code
    
    response = requests.post('https://oauth2.googleapis.com/device/code', data={
        'client_id': client_id,
        'scope': ' '.join(SCOPES)
    })
    
    if response.status_code == 200:
        return response.json() # contains device_code, user_code, verification_url, etc.
    else:
        logger.error(f"Device flow init failed: {response.text}")
        return None

def exchange_device_code(device_code):
    """
    Poll for token using device code
    """
    config = get_client_config()
    if not config:
        return None
        
    client_id = config['client_id']
    client_secret = config['client_secret']
    
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': client_id,
        'client_secret': client_secret,
        'device_code': device_code,
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    })
    
    return response.json()

def save_user_credentials(user_id, email, token_response):
    """
    Save the obtained credentials to the database
    """
    # Create Credentials object to get the refresh token and proper format
    # But we received raw JSON. We can construct it.
    # We need to save the whole JSON blob (encrypted) to auth_data.
    
    # We also need to get the user's email address if not provided!
    # The token response doesn't contain email. We need to fetch it.
    
    creds = Credentials(
        token=token_response['access_token'],
        refresh_token=token_response.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=get_client_config()['client_id'],
        client_secret=get_client_config()['client_secret'],
        scopes=SCOPES
    )
    
    # Fetch user profile to get email
    from googleapiclient.discovery import build
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    email_address = profile['emailAddress']
    
    # Serialize credentials to JSON
    creds_json = creds.to_json()
    
    # Encrypt
    encrypted_data = encrypt_password(creds_json)
    
    with get_db() as conn:
        # Check if exists
        exists = conn.execute("SELECT 1 FROM user_emails WHERE user_id = ? AND email_address = ?", (user_id, email_address)).fetchone()
        
        if exists:
            conn.execute("""
                UPDATE user_emails 
                SET auth_data = ?, label = 'Gmail API'
                WHERE user_id = ? AND email_address = ?
            """, (encrypted_data, user_id, email_address))
        else:
            # Check if primary
            count = conn.execute("SELECT COUNT(*) FROM user_emails WHERE user_id = ?", (user_id,)).fetchone()[0]
            is_primary = 1 if count == 0 else 0
            
            conn.execute("""
                INSERT INTO user_emails (user_id, email_address, label, auth_data, is_primary)
                VALUES (?, ?, 'Gmail API', ?, ?)
            """, (user_id, email_address, encrypted_data, is_primary))
            
        conn.commit()
    
    return email_address

def get_gmail_service(user_id, email_address):
    """
    Get authenticated Gmail service for a user
    """
    with get_db() as conn:
        row = conn.execute("""
            SELECT auth_data FROM user_emails 
            WHERE user_id = ? AND email_address = ?
        """, (user_id, email_address)).fetchone()
        
    if not row or not row['auth_data']:
        return None
        
    try:
        creds_json = decrypt_password(row['auth_data'])
        creds = Credentials.from_authorized_user_info(json.loads(creds_json), SCOPES)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update DB with new token? 
            # Credentials object handles refresh automatically in memory, 
            # but good practice to save back if changed.
            # For now, let's just return service.
            
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Error building service for {email_address}: {e}")
        return None
