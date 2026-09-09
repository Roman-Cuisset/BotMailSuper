"""
Email Templates Handler - v3.5
Allows all users to save and reuse email templates
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_db
from utils.i18n import tr
from utils.email_sender import log_action
from config import ADMIN_IDS

async def savetemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save current message as email template"""
    user_id = update.effective_user.id
    log_action(f"💾 User {user_id} requested save template", user_id)
    
    # Check if user provided template name
    if not context.args:
        await update.message.reply_text(tr("savetemplate_usage", str(user_id)))
        return
    
    template_name = " ".join(context.args)
    
    # Check if there's a message to save
    if "text" not in context.user_data:
        await update.message.reply_text(tr("no_message_to_save", str(user_id)))
        return
    
    body = context.user_data["text"]
    subject = context.user_data.get("email_subject", "")
    
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO templates (user_id, name, subject, body)
                VALUES (?, ?, ?, ?)
            """, (user_id, template_name, subject, body))
            conn.commit()
        
        await update.message.reply_text(tr("template_saved", str(user_id), name=template_name))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved templates"""
    user_id = update.effective_user.id
    
    try:
        with get_db() as conn:
            templates = conn.execute("""
                SELECT name, subject, created_at FROM templates
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)).fetchall()
        
        if not templates:
            await update.message.reply_text(tr("no_templates", str(user_id)))
            return
        
        template_list = []
        for t in templates:
            subject_preview = t['subject'][:30] + "..." if t['subject'] and len(t['subject']) > 30 else t['subject'] or "(no subject)"
            template_list.append(f"📧 **{t['name']}**\n   _{subject_preview}_")
        
        message = tr("template_list", str(user_id), templates="\n\n".join(template_list))
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def usetemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use a saved template"""
    user_id = update.effective_user.id
    log_action(f"📂 User {user_id} requested use template", user_id)
    
    if not context.args:
        await update.message.reply_text(tr("usetemplate_usage", str(user_id)))
        return
    
    template_name = " ".join(context.args)
    
    try:
        with get_db() as conn:
            template = conn.execute("""
                SELECT subject, body FROM templates
                WHERE user_id = ? AND name = ?
            """, (user_id, template_name)).fetchone()
        
        if not template:
            await update.message.reply_text(tr("template_not_found", str(user_id), name=template_name))
            return
        
        # Store template content in user_data
        context.user_data["email_subject"] = template['subject']
        context.user_data["email_body"] = template['body']
        context.user_data["attachments"] = []
        
        # Show preview and ask for recipient
        preview = f"**Subject:** {template['subject']}\n\n{template['body'][:200]}"
        if len(template['body']) > 200:
            preview += "..."
        
        await update.message.reply_text(
            tr("template_loaded", str(user_id), name=template_name, preview=preview),
            parse_mode="Markdown"
        )
        
        # Trigger send flow
        # Trigger send flow
        from handlers.user import trigger_send_flow
        await trigger_send_flow(user_id, template['body'], [], context)
        
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def deltemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a saved template"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(tr("deltemplate_usage", str(user_id)))
        return
    
    template_name = " ".join(context.args)
    
    try:
        with get_db() as conn:
            result = conn.execute("""
                DELETE FROM templates
                WHERE user_id = ? AND name = ?
            """, (user_id, template_name))
            conn.commit()
        
        if result.rowcount > 0:
            await update.message.reply_text(tr("template_deleted", str(user_id), name=template_name))
        else:
            await update.message.reply_text(tr("template_not_found", str(user_id), name=template_name))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))
