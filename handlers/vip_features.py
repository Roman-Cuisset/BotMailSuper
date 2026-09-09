"""
VIP Features Handler - v3.5
VIP-exclusive features: Contact Groups, Scheduled Emails, Personal Analytics
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_db
from utils.i18n import tr
from utils.email_sender import log_action
from datetime import datetime
import json

def check_vip(user_id):
    """Check if user is VIP"""
    with get_db() as conn:
        row = conn.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row and row['is_vip']

# ==================== CONTACT GROUPS (VIP ONLY) ====================

async def creategroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create contact group (VIP only)"""
    user_id = update.effective_user.id
    log_action(f"👥 User {user_id} requested create group", user_id)
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text(tr("creategroup_usage", str(user_id)))
        return
    
    group_name = " ".join(context.args)
    
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO contact_groups (user_id, group_name)
                VALUES (?, ?)
            """, (user_id, group_name))
            conn.commit()
        
        await update.message.reply_text(tr("group_created", str(user_id), name=group_name))
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            await update.message.reply_text(tr("group_exists", str(user_id), name=group_name))
        else:
            await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def addtogroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add contact to group (VIP only)"""
    user_id = update.effective_user.id
    log_action(f"👥 User {user_id} requested add to group", user_id)
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(tr("addtogroup_usage", str(user_id)))
        return
    
    group_name = context.args[0]
    contact_name = " ".join(context.args[1:])
    
    try:
        with get_db() as conn:
            # Get group ID
            group = conn.execute("""
                SELECT id FROM contact_groups
                WHERE user_id = ? AND group_name = ?
            """, (user_id, group_name)).fetchone()
            
            if not group:
                await update.message.reply_text(tr("group_not_found", str(user_id), name=group_name))
                return
            
            # Get contact ID
            contact = conn.execute("""
                SELECT id FROM contacts
                WHERE user_id = ? AND name = ?
            """, (user_id, contact_name)).fetchone()
            
            if not contact:
                await update.message.reply_text(tr("contact_not_found", str(user_id), name=contact_name))
                return
            
            # Add to group
            conn.execute("""
                INSERT OR IGNORE INTO group_members (group_id, contact_id)
                VALUES (?, ?)
            """, (group['id'], contact['id']))
            conn.commit()
        
        await update.message.reply_text(tr("contact_added_to_group", str(user_id), contact=contact_name, group=group_name))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all contact groups (VIP only)"""
    user_id = update.effective_user.id
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    try:
        with get_db() as conn:
            groups = conn.execute("""
                SELECT cg.id, cg.group_name, COUNT(gm.id) as member_count
                FROM contact_groups cg
                LEFT JOIN group_members gm ON cg.id = gm.group_id
                WHERE cg.user_id = ?
                GROUP BY cg.id
                ORDER BY cg.created_at DESC
            """, (user_id,)).fetchall()
        
        if not groups:
            await update.message.reply_text(tr("no_groups", str(user_id)))
            return
        
        group_list = []
        for g in groups:
            group_list.append(f"👥 **{g['group_name']}** ({g['member_count']} members)")
        
        message = tr("group_list", str(user_id), groups="\n".join(group_list))
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def delgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a contact group (VIP only)"""
    user_id = update.effective_user.id
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text(tr("delgroup_usage", str(user_id)))
        return
    
    group_name = " ".join(context.args)
    
    try:
        with get_db() as conn:
            result = conn.execute("""
                DELETE FROM contact_groups
                WHERE user_id = ? AND group_name = ?
            """, (user_id, group_name))
            conn.commit()
        
        if result.rowcount > 0:
            await update.message.reply_text(tr("group_deleted", str(user_id), name=group_name))
        else:
            await update.message.reply_text(tr("group_not_found", str(user_id), name=group_name))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

# ==================== SCHEDULED EMAILS (VIP ONLY) ====================

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule an email for later (VIP only)"""
    user_id = update.effective_user.id
    log_action(f"📅 User {user_id} requested schedule email", user_id)
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    # Check if there's a message to schedule
    if not (context.user_data.get("email_body") or context.user_data.get("text")) or "selected_email" not in context.user_data:
        await update.message.reply_text(tr("no_message_to_schedule", str(user_id)))
        return
    
    if not context.args:
        await update.message.reply_text(tr("schedule_usage", str(user_id)))
        return
    
    # Parse datetime (format: DD/MM/YYYY HH:MM)
    datetime_str = " ".join(context.args)
    try:
        send_at = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
    except ValueError:
        await update.message.reply_text(tr("schedule_invalid_format", str(user_id)))
        return
    
    # Check if datetime is in the future
    if send_at <= datetime.now():
        await update.message.reply_text(tr("schedule_past_time", str(user_id)))
        return
    
    # Save scheduled email
    try:
        with get_db() as conn:
            # Binary Telegram attachments are intentionally not persisted in
            # SQLite. They require dedicated encrypted object storage.
            if context.user_data.get("attachments"):
                await update.message.reply_text("❌ La programmation avec pièces jointes n'est pas encore disponible.")
                return
            attachments_json = "[]"
            conn.execute("""
                INSERT INTO scheduled_emails (user_id, recipient_email, subject, body, attachments, send_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                context.user_data["selected_email"],
                context.user_data.get("email_subject", ""),
                context.user_data.get("email_body") or context.user_data.get("text", ""),
                attachments_json,
                send_at
            ))
            conn.commit()
        
        await update.message.reply_text(tr("email_scheduled", str(user_id), time=send_at.strftime("%d/%m/%Y %H:%M")))
        
        # Clear user data
        context.user_data.clear()
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def scheduled_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View scheduled emails (VIP only)"""
    user_id = update.effective_user.id
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    try:
        with get_db() as conn:
            scheduled = conn.execute("""
                SELECT id, recipient_email, subject, send_at, status
                FROM scheduled_emails
                WHERE user_id = ? AND status = 'pending'
                ORDER BY send_at ASC
            """, (user_id,)).fetchall()
        
        if not scheduled:
            await update.message.reply_text(tr("no_scheduled_emails", str(user_id)))
            return
        
        email_list = []
        for email in scheduled:
            send_time = datetime.fromisoformat(email['send_at']).strftime("%d/%m %H:%M")
            subject = email['subject'][:30] + "..." if email['subject'] and len(email['subject']) > 30 else email['subject'] or "(no subject)"
            email_list.append(f"📅 **ID {email['id']}** → {email['recipient_email']}\n   _{subject}_ at {send_time}")
        
        message = tr("scheduled_list", str(user_id), emails="\n\n".join(email_list))
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def cancelschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel a scheduled email (VIP only)"""
    user_id = update.effective_user.id
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(tr("cancelschedule_usage", str(user_id)))
        return
    
    email_id = int(context.args[0])
    
    try:
        with get_db() as conn:
            result = conn.execute("""
                DELETE FROM scheduled_emails
                WHERE id = ? AND user_id = ? AND status = 'pending'
            """, (email_id, user_id))
            conn.commit()
        
        if result.rowcount > 0:
            await update.message.reply_text(tr("schedule_cancelled", str(user_id), id=email_id))
        else:
            await update.message.reply_text(tr("schedule_not_found", str(user_id), id=email_id))
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

# ==================== PERSONAL ANALYTICS (VIP ONLY) ====================

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View personal email statistics (VIP only)"""
    user_id = update.effective_user.id
    log_action(f"📊 User {user_id} requested stats", user_id)
    
    if not check_vip(user_id):
        await update.message.reply_text(tr("vip_feature_only", str(user_id)))
        return
    
    try:
        with get_db() as conn:
            # Total emails sent
            total = conn.execute("""
                SELECT COUNT(*) as count FROM history WHERE user_id = ?
            """, (user_id,)).fetchone()['count']
            
            # Emails this month
            this_month = conn.execute("""
                SELECT COUNT(*) as count FROM history
                WHERE user_id = ? AND strftime('%Y-%m', sent_at) = strftime('%Y-%m', 'now')
            """, (user_id,)).fetchone()['count']
            
            # Top 5 recipients
            top_recipients = conn.execute("""
                SELECT to_email, COUNT(*) as count
                FROM history
                WHERE user_id = ?
                GROUP BY to_email
                ORDER BY count DESC
                LIMIT 5
            """, (user_id,)).fetchall()
            
            # Average per day (last 30 days)
            avg_per_day = conn.execute("""
                SELECT COUNT(*)/30.0 as avg FROM history
                WHERE user_id = ? AND sent_at >= datetime('now', '-30 days')
            """, (user_id,)).fetchone()['avg']
        
        # Format top recipients
        top_list = []
        for i, r in enumerate(top_recipients, 1):
            top_list.append(f"{i}. **{r['to_email']}** ({r['count']} emails)")
        
        stats_text = tr("mystats_content", str(user_id),
            total=total,
            this_month=this_month,
            avg_per_day=f"{avg_per_day:.1f}",
            top_recipients="\n".join(top_list) if top_list else "N/A"
        )
        
        await update.message.reply_text(stats_text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

# ==================== CALLBACK HANDLERS ====================

async def handle_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group-related callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not check_vip(user_id):
        await query.answer(tr("vip_feature_only", str(user_id)), show_alert=True)
        return
    
    # Placeholder for future group callback implementations
    await query.answer("Group callback not yet implemented")

async def handle_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle schedule-related callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not check_vip(user_id):
        await query.answer(tr("vip_feature_only", str(user_id)), show_alert=True)
        return
    
    # Placeholder for future schedule callback implementations
    await query.answer("Schedule callback not yet implemented")
