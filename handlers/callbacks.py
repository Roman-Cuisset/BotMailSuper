from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS  
from utils.i18n import tr
from utils.email_sender import send_email_async, log_action
from database.db import get_db
from datetime import datetime
from collections import defaultdict, deque
from time import monotonic
import json
from config import MAX_MESSAGES_PER_MINUTE


recent_sends = defaultdict(deque)


def send_allowed(user_id):
    now = monotonic()
    timestamps = recent_sends[user_id]
    while timestamps and now - timestamps[0] >= 60:
        timestamps.popleft()
    if len(timestamps) >= MAX_MESSAGES_PER_MINUTE:
        return False
    timestamps.append(now)
    return True


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    if query.data == "home_history":
        with get_db() as conn:
            rows = conn.execute(
                "SELECT to_email, sent_at, status FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 5",
                (user_id,),
            ).fetchall()
        message = "🕓 Derniers envois :\n\n" + ("\n".join(
            f"{'✅' if row['status'] == 'sent' else '❌'} {row['to_email']} · {row['sent_at']}" for row in rows
        ) if rows else "Aucun historique.")
        await query.edit_message_text(message)
        return

    if query.data in {"home_contacts"} or query.data.startswith("contacts_page:"):
        from handlers.user import contact_keyboard
        page = int(query.data.split(":", 1)[1]) if ":" in query.data else 0
        search = context.user_data.get("contact_search", "")
        markup, count, page, max_page = contact_keyboard(user_id, page, search)
        await query.edit_message_text(
            f"👥 {count} contact(s)" + (f" · page {page + 1}/{max_page + 1}" if count else ""),
            reply_markup=markup,
        )
        return

    if query.data == "home_drafts":
        with get_db() as conn:
            rows = conn.execute(
                "SELECT name, to_email FROM drafts WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            ).fetchall()
        keyboard = [[InlineKeyboardButton(
            f"📧 {row['name']} → {(row['to_email'] or 'Non défini')[:20]}",
            callback_data=f"draft_view:{row['name']}",
        )] for row in rows]
        await query.edit_message_text(
            f"📋 Vos brouillons ({len(rows)})" if rows else "📭 Aucun brouillon sauvegardé.",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        )
        return

    if query.data == "home_language":
        keyboard = [[
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang:fr"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        ]]
        await query.edit_message_text(tr("choose_language", str(user_id)), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data.startswith("htmltpl:"):
        from handlers.html_templates import handle_html_template_callback
        await handle_html_template_callback(query, context)
        return

    if query.data.startswith("draft_"):
        from handlers.drafts import handle_draft_callback
        await handle_draft_callback(query, context)
        return
    
    # Language selection
    if query.data.startswith("lang:"):
        code = query.data.split(":", 1)[1]
        with get_db() as conn:
            conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (code, user_id))
            conn.commit()
        
        log_action(f"🌐 User {user_id} changed language to {code}", user_id)
        await query.edit_message_text(tr("lang_set", code))
        return

    # Email selection - simplified (no VIP multi-select)
    if query.data == "quick_send":
        await query.edit_message_text(tr("please_select_destination", str(user_id)))
        from handlers.user import contact_keyboard
        markup, _, _, _ = contact_keyboard(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=tr("ask_destination", str(user_id)),
            reply_markup=markup
        )
        return


    # Add Note - Allow user to add a note to the message
    if query.data == "add_note":
        context.user_data["awaiting_note"] = True
        await query.edit_message_text(tr("please_type_note", str(user_id)))
        return

    if query.data == "edit_subject":
        context.user_data["awaiting_subject"] = True
        await query.edit_message_text("✏️ Écrivez le nouveau sujet (200 caractères maximum), ou /cancel.")
        return

    # Email selection
    if query.data.startswith("email:"):
        email = query.data.split(":", 1)[1]
        if email == "other":
            context.user_data["awaiting_email"] = True
            await query.edit_message_text(tr("enter_email", str(user_id)))
        else:
            context.user_data["selected_email"] = email
            log_action("📧 Recipient selected", user_id)
            await query.edit_message_text(tr("email_selected", str(user_id), email=email))
            await send_preview(user_id, context)
        return

    # Confirm send
    if query.data in {"confirm_send", "retry_send"}:
        content = context.user_data
        if "text" not in content and "attachments" not in content:
             await query.edit_message_text(tr("no_message_to_send", str(user_id)))
             return
             
        to = content.get("selected_email")
        text = content.get("text", "")
        attachments = content.get("attachments", [])
        
        if not to:
            await query.edit_message_text(tr("no_message_to_send", str(user_id)))
            return

        # Enforce both the per-minute abuse limit and the configured daily user quota.
        with get_db() as conn:
            row = conn.execute("SELECT is_vip, quota FROM users WHERE user_id = ?", (user_id,)).fetchone()
            is_vip = row['is_vip'] if row else False
            quota = row['quota'] if row else 20
            sent_today = conn.execute(
                "SELECT COUNT(*) FROM history WHERE user_id = ? AND status IN ('sent', 'accepted') AND date(sent_at) = date('now')",
                (user_id,),
            ).fetchone()[0]
        if not is_vip and not send_allowed(user_id):
            await query.edit_message_text("❌ Trop d'envois en une minute. Réessayez dans quelques instants.")
            return
        if not is_vip and quota >= 0 and sent_today >= quota:
            await query.edit_message_text(f"❌ Quota quotidien atteint ({quota} e-mails).")
            return

        username = query.from_user.username or ""
        default_subject = "Message from VIP user" if is_vip else (
            f"Message from @{username}" if username else f"Message from user {user_id}"
        )
        subject = content.get("email_subject") or default_subject
            
        await query.edit_message_text("⏳ Envoi en cours…")
        success = await send_email_async(to, subject, text, attachments, sender_user=query.from_user, is_vip=is_vip)
        
        if success:
            # Save to history
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO history (user_id, to_email, subject, status, error, details, body, attachments)
                    VALUES (?, ?, ?, 'accepted', '', ?, ?, ?)
                """, (user_id, to, subject, "Accepted by SMTP via bot", text, json.dumps([name for name, _ in attachments], ensure_ascii=False)))
                conn.commit()
            
            log_action("✅ Email accepted by SMTP", user_id)
            await query.edit_message_text(tr("sent_success", str(user_id), email=to))
            context.user_data.clear()
        else:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO history (user_id, to_email, subject, status, error, details)
                    VALUES (?, ?, ?, 'failed', 'SMTP failure', ?)
                """, (user_id, to, subject, "Failed via bot"))
                conn.commit()
            keyboard = [[
                InlineKeyboardButton("🔄 Réessayer", callback_data="retry_send"),
                InlineKeyboardButton(tr("cancel_button", str(user_id)), callback_data="cancel_send"),
            ]]
            await query.edit_message_text(tr("sent_fail", str(user_id)), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Cancel send
    if query.data == "cancel_send":
        context.user_data.clear()
        await query.edit_message_text(tr("operation_cancelled", str(user_id)))
        return

    # Admin callbacks
    if user_id in ADMIN_IDS:
        if query.data == "admin_viplist":
            with get_db() as conn:
                rows = conn.execute("SELECT user_id FROM users WHERE is_vip = 1").fetchall()
                vip_list = "\n".join(str(r['user_id']) for r in rows)
            await query.edit_message_text(f"VIP users:\n{vip_list or 'None'}")
            return
        
        if query.data == "admin_blacklist":
            with get_db() as conn:
                rows = conn.execute("SELECT user_id FROM users WHERE is_blacklisted = 1").fetchall()
                blist = "\n".join(str(r['user_id']) for r in rows)
            await query.edit_message_text(f"Blacklisted users:\n{blist or 'None'}")
            return
            
        if query.data in ["admin_addvip", "admin_delvip", "admin_ban", "admin_unban"]:
             await query.edit_message_text("Please use the corresponding command:\n/vip <id>\n/ban <id>\netc.")
             return

async def send_preview(user_id, context):
    content = context.user_data
    text = content.get("text", "(No text)").strip()
    attachments = content.get("attachments", [])
    email = content.get("selected_email", "")
    subject = content.get("email_subject", "") or "Automatique"
    
    preview_msg = tr("preview_msg", str(user_id), 
                     text=text, 
                     attachments_count=len(attachments), 
                     email=email)
    
    preview_msg += f"\nSujet : {subject}"
    keyboard = [
        [InlineKeyboardButton("✏️ Modifier le sujet", callback_data="edit_subject")],
        [InlineKeyboardButton(tr("send_button", str(user_id)), callback_data="confirm_send")],
        [InlineKeyboardButton(tr("cancel_button", str(user_id)), callback_data="cancel_send")]
    ]
    
    await context.bot.send_message(chat_id=user_id, text=preview_msg, reply_markup=InlineKeyboardMarkup(keyboard))
