"""
Account Handlers
Manage custom email accounts for users
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_db
from utils.crypto import encrypt_password
import logging

logger = logging.getLogger(__name__)

from utils.gmail_auth import initiate_device_flow, exchange_device_code, save_user_credentials
import asyncio

async def connect_gmail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Gmail connection flow"""
    user = update.effective_user
    
    # Init flow
    flow_data = initiate_device_flow()
    if not flow_data:
        await update.message.reply_text("❌ Failed to initialize Google login. Please contact admin.")
        return
        
    verification_url = flow_data['verification_url']
    user_code = flow_data['user_code']
    device_code = flow_data['device_code']
    
    # Store device_code in context to verify later? 
    # Or just pass it in callback data if we use a button.
    # But for security, maybe context user_data is better.
    context.user_data['device_code'] = device_code
    
    await update.message.reply_text(
        f"🔗 **Connect your Gmail Account**\n\n"
        f"1. Visit: {verification_url}\n"
        f"2. Enter code: `{user_code}`\n"
        f"3. Click 'Allow'\n\n"
        f"After you have done this, click the button below.",
        parse_mode='Markdown',
        reply_markup=from_button_text("✅ I have finished", f"finish_connect")
    )

async def finish_connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify connection after user claims to be done"""
    query = update.callback_query
    device_code = context.user_data.get('device_code')
    if not device_code:
        await query.edit_message_text("❌ Session expired. Please try /connect again.")
        return
        
    try:
        # Exchange code for token
        token_response = exchange_device_code(device_code)
        
        if 'error' in token_response:
            error = token_response['error']
            if error == 'authorization_pending':
                await query.edit_message_text(
                    "⏳ Waiting for approval... Please complete the steps on the website and try again.",
                    reply_markup=from_button_text("🔄 Retry Check", "finish_connect")
                )
            else:
                await query.edit_message_text(f"❌ Error: {error}. Please try /connect again.")
        else:
            # Success! Save credentials
            user = update.effective_user
            email = save_user_credentials(user.id, None, token_response)
            
            await query.edit_message_text(f"✅ Success! Connected as **{email}**.")
            
    except Exception as e:
        logger.error(f"Error finishing connect: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")

def from_button_text(text, callback_data):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

async def my_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's custom emails"""
    user = update.effective_user
    
    with get_db() as conn:
        emails = conn.execute("""
            SELECT email_address, label, is_primary 
            FROM user_emails 
            WHERE user_id = ?
        """, (user.id,)).fetchall()
        
    if not emails:
        await update.message.reply_text("You have no custom emails configured. Use /addemail to add one.")
        return
        
    text = "📧 **Your Email Accounts:**\n\n"
    for email in emails:
        status = "🌟 (Default)" if email['is_primary'] else ""
        label = email['label']
        if label == 'Gmail API':
            label = "✅ Gmail API (Connected)"
        text += f"• {email['email_address']} {status}\n"
        text += f"  Type: {label}\n\n"
        
    text += "Use /setdefault <email> to change your sending account."
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_default_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set default sending email"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /setdefault <email>")
        return
        
    target_email = context.args[0]
    
    with get_db() as conn:
        # Verify email belongs to user
        exists = conn.execute("""
            SELECT 1 FROM user_emails 
            WHERE user_id = ? AND email_address = ?
        """, (user.id, target_email)).fetchone()
        
        if not exists:
            await update.message.reply_text("❌ You don't have this email configured.")
            return
            
        # Reset all to 0
        conn.execute("UPDATE user_emails SET is_primary = 0 WHERE user_id = ?", (user.id,))
        
        # Set new primary
        conn.execute("""
            UPDATE user_emails 
            SET is_primary = 1 
            WHERE user_id = ? AND email_address = ?
        """, (user.id, target_email))
        
        conn.commit()
        
    await update.message.reply_text(f"✅ Default sender set to: {target_email}")

async def delete_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a custom email"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /deleteemail <email>")
        return
        
    target_email = context.args[0]
    
    with get_db() as conn:
        conn.execute("""
            DELETE FROM user_emails 
            WHERE user_id = ? AND email_address = ?
        """, (user.id, target_email))
        
        conn.commit()
        
    await update.message.reply_text(f"🗑️ Email {target_email} deleted.")
