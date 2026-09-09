"""
Gmail API Integration Module
Handles OAuth 2.0 authentication and email sending via Gmail API
"""

import os
import base64
import logging
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Paths for credentials
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


def authenticate_gmail(interactive=False):
    """
    Authenticate with Gmail API using OAuth 2.0
    Returns the Gmail API service object or None if authentication fails
    
    Args:
        interactive (bool): If True, allows opening browser for authentication.
                          If False, fails if no valid token exists.
    """
    creds = None
    
    # Check if token.json exists (previously authenticated)
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            logger.info("✅ Loaded existing Gmail API credentials from token.json")
        except Exception as e:
            logger.error(f"❌ Error loading token.json: {e}")
            creds = None
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("🔄 Refreshing expired Gmail API token...")
                creds.refresh(Request())
                logger.info("✅ Token refreshed successfully")
            except Exception as e:
                logger.error(f"❌ Error refreshing token: {e}")
                creds = None
        
        # If still no valid creds, do full OAuth flow
        if not creds:
            if not interactive:
                logger.error("❌ No valid credentials found and interactive mode disabled. Cannot authenticate.")
                return None

            if not CREDENTIALS_FILE.exists():
                logger.error(f"❌ credentials.json not found at {CREDENTIALS_FILE.absolute()}")
                logger.error("Please follow the setup guide in GMAIL_API_SETUP.md")
                return None
            
            try:
                logger.info("🔐 Starting OAuth 2.0 authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("✅ Authentication successful!")
            except Exception as e:
                logger.error(f"❌ OAuth authentication failed: {e}")
                return None
        
        # Save credentials for future use
        try:
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"✅ Saved credentials to {TOKEN_FILE}")
        except Exception as e:
            logger.error(f"⚠️ Warning: Could not save token.json: {e}")
    
    # Build and return Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("✅ Gmail API service initialized")
        return service
    except Exception as e:
        logger.error(f"❌ Error building Gmail service: {e}")
        return None


def create_message_with_attachment(sender, to, subject, body_text, body_html, attachments):
    """
    Create a MIME message with optional attachments
    
    Args:
        sender: Email address of sender
        to: Email address of recipient
        subject: Email subject
        body_text: Plain text body (fallback)
        body_html: HTML body (main content)
        attachments: List of tuples (filename, file_content_bytes)
    
    Returns:
        Dict with base64url encoded message
    """
    try:
        # Create multipart message
        message = MIMEMultipart('alternative')
        message['To'] = to
        message['From'] = sender
        message['Subject'] = subject
        
        # Attach text and HTML parts
        if body_text:
            text_part = MIMEText(body_text, 'plain', 'utf-8')
            message.attach(text_part)
        
        if body_html:
            html_part = MIMEText(body_html, 'html', 'utf-8')
            message.attach(html_part)
        
        # Attach files if any
        for filename, content in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            message.attach(part)
        
        # Encode message to base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}
    
    except Exception as e:
        logger.error(f"❌ Error creating MIME message: {e}")
        return None


def send_email_via_gmail_api(to_address, subject, body_text, body_html, attachments=None, sender_email=None, service_override=None):
    """
    Send an email using Gmail API
    
    Args:
        to_address: Recipient email address
        subject: Email subject
        body_text: Plain text body (fallback)
        body_html: HTML body content
        attachments: List of tuples (filename, file_content_bytes)
        sender_email: Sender email (default: from environment)
        service_override: Optional Gmail service object to use instead of default auth
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Authenticate
        if service_override:
            service = service_override
        else:
            service = authenticate_gmail()
            
        if not service:
            logger.error("❌ Gmail API authentication failed")
            return False
        
        # Get sender email from environment if not provided
        if not sender_email:
            from dotenv import load_dotenv
            load_dotenv("secrets.env")
            sender_email = os.getenv("EMAIL_SENDER")
        
        if not sender_email:
            logger.error("❌ EMAIL_SENDER not set")
            return False
        
        # Create message
        if attachments is None:
            attachments = []
        
        message = create_message_with_attachment(
            sender=sender_email,
            to=to_address,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments
        )
        
        if not message:
            logger.error("❌ Failed to create email message")
            return False
        
        # Send message
        logger.info(f"📧 Sending email via Gmail API to {to_address}...")
        result = service.users().messages().send(userId='me', body=message).execute()
        
        logger.info(f"✅ Email sent successfully via Gmail API! Message ID: {result.get('id')}")
        return True
    
    except HttpError as error:
        logger.error(f"❌ Gmail API HTTP error: {error}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending email via Gmail API: {e}")
        return False


# Quick test function (for development)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Gmail API authentication...")
    service = authenticate_gmail(interactive=True)
    
    if service:
        print("✅ Authentication successful!")
        print("You can now use Gmail API to send emails.")
    else:
        print("❌ Authentication failed.")
        print("Please check GMAIL_API_SETUP.md for setup instructions.")
