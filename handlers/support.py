from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from utils.i18n import tr
from database.db import get_db

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Usage: /support <message>"))
        return
    
    message = " ".join(context.args)
    username = update.effective_user.username or "Unknown"
    
    # Notify admins
    admin_msg = f"🆘 <b>Support Ticket</b>\nFrom: @{username} (ID: {user_id})\nMessage: {message}\n\nReply with: <code>/reply {user_id} &lt;message&gt;</code>"
    
    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="HTML")
            sent_count += 1
        except Exception:
            pass
            
    if sent_count > 0:
        await update.message.reply_text("✅ Support message sent to admins.")
    else:
        await update.message.reply_text("❌ Failed to contact admins.")

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return # Silent ignore for non-admins
        
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply <user_id> <message>")
        return
        
    try:
        target_id = int(context.args[0])
        message = " ".join(context.args[1:])
        
        await context.bot.send_message(chat_id=target_id, text=f"👨‍💻 <b>Admin Reply:</b>\n{message}", parse_mode="HTML")
        await update.message.reply_text(f"✅ Reply sent to {target_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
