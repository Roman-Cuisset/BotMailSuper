from database.db import get_db
from utils.html_templates import is_html
import os
import asyncio
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
import logging
import html as html_lib
from utils.crypto import decrypt_password
from utils.html_sanitizer import sanitize_email_html

# Load environment variables
load_dotenv("secrets.env")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

logger = logging.getLogger(__name__)


def recipient_log_label(address):
    """Keep recipient addresses out of operational log files."""
    domain = address.rsplit("@", 1)[-1] if "@" in address else "invalid"
    return f"recipient@{domain}"

def log_action(message, user_id=None):
    prefix = f"[user_id={user_id}] " if user_id else ""
    logger.info(f"{prefix}{message}")

def render_email_html(expediteur, message_content, attachments, is_vip=False, anonymous=False):
    html_path = Path("receptiondesing.html")
    if not html_path.exists():
        # fallback simple
        att_list = "<br>".join(f"- {html_lib.escape(str(name))}" for name, _ in attachments) if attachments else "No attachment"
        return f"<b>Sender:</b> {html_lib.escape(str(expediteur))}<br><b>Message:</b><br>{html_lib.escape(message_content)}<br><b>Attachments:</b><br>{att_list}"
    
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    
    # Pour VIP, masquer l'expéditeur si besoin
    if anonymous:
        expediteur = "VIP user (anonymous)"
    
    # Correction : toujours une liste <li> même si un seul fichier
    if attachments:
        att_html = "".join(f"<li>{html_lib.escape(str(name))}</li>" for name, _ in attachments)
    else:
        att_html = "<li>No attachment</li>"
    
    # Message vide si besoin
    if not message_content.strip():
        message_content = "<i>No message</i>"
    else:
        # Escape HTML characters to prevent injection
        message_content = html_lib.escape(message_content)
        # Replace newlines with <br>
        message_content = message_content.replace("\n", "<br>")
    
    html = html.replace("{{expediteur}}", html_lib.escape(str(expediteur)))
    html = html.replace("{{message_content}}", message_content)
    html = html.replace("{{attachments_list}}", att_html)
    return html

def _send_email_sync(to_address, subject, body, attachments, sender_user=None, is_vip=False, sender_name_override=None, anonymous=False):
    try:
        # Get signature if VIP
        signature = ""
        if is_vip and sender_user:
            with get_db() as conn:
                row = conn.execute("SELECT signature FROM users WHERE user_id = ?", (sender_user.id,)).fetchone()
                if row and row['signature']:
                    signature = row['signature']
        
        # Append signature to body if exists
        if signature:
            body = f"{body}\n\n---\n{signature}"
        
        # Check for custom user email
        custom_account = None
        if sender_user:
            with get_db() as conn:
                # Get primary email for user
                row = conn.execute("""
                    SELECT email_address, label, encrypted_password
                    FROM user_emails 
                    WHERE user_id = ? AND is_primary = 1
                """, (sender_user.id,)).fetchone()
                
                if row:
                    try:
                        # SMTP config is stored as host:port in label.
                        smtp_host, smtp_port = row['label'].split(':', 1)
                        custom_account = {
                            'email': row['email_address'],
                            'password': decrypt_password(row['encrypted_password']),
                            'host': smtp_host,
                            'port': int(smtp_port),
                        }
                            
                        logger.info("📧 Using a custom SMTP account")
                    except Exception as e:
                        logger.error(f"❌ Error parsing custom account config: {e}")
                        custom_account = None

        # Determine sender email
        current_sender_email = custom_account['email'] if custom_account else EMAIL_SENDER

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = current_sender_email
        msg["To"] = to_address

        # Determine expediteur name
        if sender_name_override:
            expediteur = sender_name_override
        else:
            expediteur = f"@{sender_user.username}" if sender_user and sender_user.username else f"user {sender_user.id}" if sender_user else "BotMailSuper"
        
        # Check if body is HTML
        body_is_html = is_html(body)
        
        # Prepare HTML and text bodies
        if body_is_html:
            html_body = sanitize_email_html(body)
            text_body = "You received a message via BotMailSuper."
        else:
            # Use template
            html_body = render_email_html(expediteur, body, attachments, is_vip=is_vip, anonymous=anonymous)
            text_body = "You received a message via BotMailSuper."
        
        # Set content
        msg.set_content(text_body, subtype='plain')
        msg.add_alternative(html_body, subtype='html')

        # Add attachments
        for filename, content in attachments:
            msg.add_attachment(content, maintype="application", subtype="octet-stream", filename=filename)
        
        if custom_account:
            try:
                logger.info(f"📧 Sending via custom SMTP ({custom_account['host']}:{custom_account['port']})")
                with smtplib.SMTP_SSL(custom_account['host'], custom_account['port']) as smtp:
                    smtp.login(custom_account['email'], custom_account['password'])
                    smtp.send_message(msg)
                log_action(f"✅ Email sent via custom SMTP to {recipient_log_label(to_address)}")
                return True
            except Exception as e:
                logger.error(f"❌ Custom SMTP failed: {e}")
                return False

        logger.info(f"📧 Sending email via default SMTP to {recipient_log_label(to_address)}")
        
        if EMAIL_SENDER is None or EMAIL_PASSWORD is None:
            raise ValueError("EMAIL_SENDER and EMAIL_PASSWORD must not be None")
            
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        log_action(f"✅ Email sent via default SMTP to {recipient_log_label(to_address)}")
        return True
        
    except Exception as e:
        log_action(f"❌ SMTP error for {recipient_log_label(to_address)}: {e}")
        return False

def send_email(to_address, subject, body, attachments, sender_user=None, is_vip=False, sender_name_override=None, anonymous=False):
    """Synchronous entry point for WSGI workers and scripts."""
    return _send_email_sync(
        to_address, subject, body, attachments, sender_user, is_vip, sender_name_override, anonymous
    )

async def send_email_async(to_address, subject, body, attachments, sender_user=None, is_vip=False, sender_name_override=None, anonymous=False):
    """Send outside the event loop and return the provider's real result."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _send_email_sync,
        to_address,
        subject,
        body,
        attachments,
        sender_user,
        is_vip,
        sender_name_override,
        anonymous,
    )


async def send_email_task(recipient, subject, message_text, attachments, expediteur, is_vip):
    """Async wrapper for scheduler to use"""
    # Scheduler passes 'expediteur' string as sender name
    return await send_email_async(recipient, subject, message_text, attachments, sender_user=None, is_vip=is_vip, sender_name_override=expediteur)
