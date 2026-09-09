"""
Draft Management Commands - Phase 4
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_db
from utils.i18n import tr
import json

async def savedraft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save current message as draft"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /savedraft <nom_du_brouillon>")
        return
    
    draft_name = " ".join(context.args)
    
    # Get current message data from context
    text = context.user_data.get("text", "")
    to_email = context.user_data.get("selected_email", "")
    subject = context.user_data.get("email_subject", "")
    attachments = context.user_data.get("attachments", [])
    
    if not text and not attachments:
        await update.message.reply_text("❌ Aucun message à sauvegarder. Envoyez d'abord un message ou fichier.")
        return
    
    # Serialize attachments (store filenames only)
    attachments_json = json.dumps([att[0] for att in attachments]) if attachments else "[]"
    
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO drafts (user_id, name, to_email, subject, body, attachments)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, draft_name, to_email, subject, text, attachments_json))
            conn.commit()
        
        await update.message.reply_text(f"✅ Brouillon '{draft_name}' sauvegardé !")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")

async def drafts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all drafts"""
    user_id = update.effective_user.id
    
    with get_db() as conn:
        drafts = conn.execute("""
            SELECT name, to_email, subject, created_at
            FROM drafts
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()
    
    if not drafts:
        await update.message.reply_text("📭 Aucun brouillon sauvegardé.")
        return
    
    # Create inline keyboard with drafts
    keyboard = []
    for draft in drafts:
        name = draft['name']
        to = draft['to_email'] or "Non défini"
        subject = draft['subject'] or "Sans sujet"
        
        keyboard.append([
            InlineKeyboardButton(
                f"📧 {name} → {to[:20]}",
                callback_data=f"draft_view:{name}"
            )
        ])
    
    await update.message.reply_text(
        f"📋 Vos brouillons ({len(drafts)}) :\n\nCliquez pour voir les détails :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def senddraft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a draft"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /senddraft <nom_du_brouillon>")
        return
    
    draft_name = " ".join(context.args)
    
    with get_db() as conn:
        draft = conn.execute("""
            SELECT to_email, subject, body, attachments
            FROM drafts
            WHERE user_id = ? AND name = ?
        """, (user_id, draft_name)).fetchone()
    
    if not draft:
        await update.message.reply_text(f"❌ Brouillon '{draft_name}' introuvable.")
        return
    
    # Load draft into context
    context.user_data["text"] = draft['body']
    context.user_data["selected_email"] = draft['to_email']
    context.user_data["email_subject"] = draft['subject']
    
    # Show preview
    from handlers.callbacks import send_preview
    await send_preview(user_id, context)

async def deldraft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a draft"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /deldraft <nom_du_brouillon>")
        return
    
    draft_name = " ".join(context.args)
    
    with get_db() as conn:
        cursor = conn.execute("""
            DELETE FROM drafts
            WHERE user_id = ? AND name = ?
        """, (user_id, draft_name))
        conn.commit()
    
    if cursor.rowcount > 0:
        await update.message.reply_text(f"✅ Brouillon '{draft_name}' supprimé.")
    else:
        await update.message.reply_text(f"❌ Brouillon '{draft_name}' introuvable.")

async def handle_draft_callback(query, context):
    """Handle draft view callback"""
    user_id = query.from_user.id

    if query.data == "draft_list":
        with get_db() as conn:
            rows = conn.execute(
                "SELECT name, to_email FROM drafts WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
        keyboard = [[InlineKeyboardButton(f"📧 {row['name']} → {(row['to_email'] or 'Non défini')[:20]}", callback_data=f"draft_view:{row['name']}")] for row in rows]
        await query.edit_message_text(
            f"📋 Vos brouillons ({len(rows)}) :",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    draft_name = query.data.split(":", 1)[1]

    if query.data.startswith("draft_delete:"):
        with get_db() as conn:
            result = conn.execute(
                "DELETE FROM drafts WHERE user_id = ? AND name = ?", (user_id, draft_name)
            )
            conn.commit()
        await query.edit_message_text("🗑️ Brouillon supprimé." if result.rowcount else "❌ Brouillon introuvable.")
        return

    if query.data.startswith("draft_send:"):
        with get_db() as conn:
            draft = conn.execute(
                "SELECT to_email, subject, body FROM drafts WHERE user_id = ? AND name = ?",
                (user_id, draft_name),
            ).fetchone()
        if not draft:
            await query.edit_message_text("❌ Brouillon introuvable.")
            return
        context.user_data.update({
            "text": draft["body"],
            "email_subject": draft["subject"],
            "attachments": [],
        })
        if draft["to_email"]:
            context.user_data["selected_email"] = draft["to_email"]
            from handlers.callbacks import send_preview
            await query.edit_message_text("📧 Brouillon chargé.")
            await send_preview(user_id, context)
        else:
            from handlers.user import trigger_send_flow
            await query.edit_message_text("📧 Brouillon chargé. Choisissez un destinataire.")
            await trigger_send_flow(user_id, draft["body"], [], context)
        return

    with get_db() as conn:
        draft = conn.execute("""
            SELECT to_email, subject, body, attachments, created_at
            FROM drafts
            WHERE user_id = ? AND name = ?
        """, (user_id, draft_name)).fetchone()
    
    if not draft:
        await query.answer("❌ Brouillon introuvable", show_alert=True)
        return
    
    to = draft['to_email'] or "Non défini"
    subject = draft['subject'] or "Sans sujet"
    body = draft['body'][:100] + "..." if len(draft['body']) > 100 else draft['body']
    created = draft['created_at']
    
    keyboard = [
        [InlineKeyboardButton("📤 Envoyer", callback_data=f"draft_send:{draft_name}")],
        [InlineKeyboardButton("🗑️ Supprimer", callback_data=f"draft_delete:{draft_name}")],
        [InlineKeyboardButton("« Retour", callback_data="draft_list")]
    ]
    
    await query.edit_message_text(
        f"📧 **Brouillon : {draft_name}**\n\n"
        f"**À :** {to}\n"
        f"**Sujet :** {subject}\n"
        f"**Message :** {body}\n\n"
        f"_Créé le {created}_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
