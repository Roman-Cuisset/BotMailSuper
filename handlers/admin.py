from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from utils.i18n import tr
from utils.email_sender import log_action
from utils.state import set_maintenance_mode
from database.db import get_db
from datetime import datetime

# Global variable for maintenance mode (needs to be shared or stored in DB/Redis)
# For now, we import it from config but we can't change it there easily if it's immutable.
# In main_pro.py it was a global variable.
# We will use a mutable container or a database setting for maintenance mode in the future.
# For this refactor, we'll keep it simple and assume it's managed in the main state or here.

# Maintenance mode is now stored in DB
def get_maintenance_mode():
    try:
        with get_db() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()
            return row['value'] == '1' if row else False
    except Exception:
        return False

def set_maintenance_mode(value):
    val_str = '1' if value else '0'
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('maintenance_mode', ?)", (val_str,))
        conn.commit()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return

    keyboard = [
        [InlineKeyboardButton("👑 VIP list", callback_data="admin_viplist")],
        [InlineKeyboardButton("🚫 Blacklist", callback_data="admin_blacklist")],
        [InlineKeyboardButton("➕ Add VIP", callback_data="admin_addvip")],
        [InlineKeyboardButton("➖ Remove VIP", callback_data="admin_delvip")],
        [InlineKeyboardButton("🚷 Ban user", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ Unban user", callback_data="admin_unban")],
    ]
    await update.message.reply_text("🛠️ Admin panel:", reply_markup=InlineKeyboardMarkup(keyboard))

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text(tr("ban_usage", str(user_id)))
        return

    try:
        target_id = int(context.args[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_blacklisted = 1 WHERE user_id = ?", (target_id,))
            conn.commit()
        await update.message.reply_text(tr("user_banned", str(user_id), user_id=target_id))
    except ValueError:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Invalid ID"))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text(tr("unban_usage", str(user_id)))
        return

    try:
        target_id = int(context.args[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_blacklisted = 0 WHERE user_id = ?", (target_id,))
            conn.commit()
        await update.message.reply_text(tr("user_unbanned", str(user_id), user_id=target_id))
    except ValueError:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Invalid ID"))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def setvip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setvip <user_id>")
        return

    try:
        target_id = int(context.args[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (target_id,))
            conn.commit()
        await update.message.reply_text(f"✅ User {target_id} is now VIP!")
    except ValueError:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Invalid ID"))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def removevip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removevip <user_id>")
        return

    try:
        target_id = int(context.args[0])
        with get_db() as conn:
            conn.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (target_id,))
            conn.commit()
        await update.message.reply_text(f"✅ User {target_id} VIP status removed.")
    except ValueError:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Invalid ID"))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def setquota_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return

    if len(context.args) < 2:
        await update.message.reply_text(tr("setquota_usage", str(user_id)))
        return

    try:
        target_id = int(context.args[0])
        quota = int(context.args[1])
        if quota < 0:
            raise ValueError("Quota must be zero or greater")
        with get_db() as conn:
            conn.execute(
                """INSERT INTO users (user_id, quota) VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET quota = excluded.quota""",
                (target_id, quota),
            )
            conn.commit()
        await update.message.reply_text(tr("quota_set", str(user_id), user_id=target_id, quota=quota))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return

    if not context.args:
        await update.message.reply_text(tr("maintenance_usage", str(user_id)))
        return

    mode = context.args[0].lower()
    if mode == "on":
        set_maintenance_mode(True)
        await update.message.reply_text(tr("maintenance_enabled", str(user_id)))
    elif mode == "off":
        set_maintenance_mode(False)
        await update.message.reply_text(tr("maintenance_disabled", str(user_id)))
    else:
        await update.message.reply_text(tr("maintenance_usage", str(user_id)))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        blacklisted = conn.execute("SELECT COUNT(*) FROM users WHERE is_blacklisted = 1").fetchone()[0]
        
        # Advanced stats
        today = datetime.now().strftime("%Y-%m-%d")
        daily_row = conn.execute("SELECT message_count FROM daily_stats WHERE date = ?", (today,)).fetchone()
        daily_count = daily_row['message_count'] if daily_row else 0
        
        # Active users (last 24h) - requires adding last_active to users table or inferring from history
        # For now, let's count users who sent a message today from history
        active_today = conn.execute("""
            SELECT COUNT(DISTINCT user_id) FROM history 
            WHERE date(sent_at) = date('now')
        """).fetchone()[0]
    
    msg = tr("stats_msg", str(user_id), active=active_today, blacklisted=blacklisted, total=total)
    msg += f"\n\n📊 <b>Daily Stats ({today}):</b>\nMessages sent: {daily_count}"
    
    await update.message.reply_text(msg, parse_mode="HTML")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return

    # Check if message is a reply or has arguments
    message_to_send = None
    if update.message.reply_to_message:
        message_to_send = update.message.reply_to_message
    else:
        # Parse arguments
        text = " ".join(context.args)
        if not text:
             await update.message.reply_text("Usage: /broadcast <message> OR reply to a message with /broadcast")
             return
    
    # Confirm broadcast
    await update.message.reply_text("📢 Starting broadcast...")
    log_action(f"📢 Starting broadcast by admin {user_id}")
    
    with get_db() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    
    sent_ids = []
    failed_ids = []
    
    for user in users:
        uid = user['user_id']
        try:
            if message_to_send:
                await message_to_send.copy(chat_id=uid)
            else:
                try:
                    await context.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
                except Exception as e:
                    if "Can't parse entities" in str(e):
                        log_action(f"⚠️ Markdown error in broadcast to {uid}, retrying plain text")
                        await context.bot.send_message(chat_id=uid, text=text)
                    else:
                        raise e
            sent_ids.append(uid)
        except Exception as e:
            # Often "Forbidden: bot was blocked by the user"
            failed_ids.append(uid)
            log_action(f"❌ Broadcast failed for {uid}: {e}")
            
    log_action(f"✅ Broadcast finished. Sent: {len(sent_ids)}, Failed: {len(failed_ids)}")
    
    report = f"✅ Broadcast finished.\n\n"
    report += f"📤 <b>Sent ({len(sent_ids)}):</b>\n{', '.join(map(str, sent_ids))}\n\n"
    report += f"❌ <b>Failed ({len(failed_ids)}):</b>\n{', '.join(map(str, failed_ids))}"
    
    await update.message.reply_text(report, parse_mode="HTML")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("admin_only", str(user_id)))
        return
    await update.message.reply_text(tr("feedback_received", str(user_id)))
