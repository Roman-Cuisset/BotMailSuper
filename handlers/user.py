from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, MAX_ATTACHMENT_BYTES, MAX_TOTAL_ATTACHMENT_BYTES
from utils.i18n import tr
from utils.email_sender import log_action
from utils.state import get_maintenance_mode
from database.db import get_db
import sqlite3
import asyncio
from email.utils import parseaddr


def is_valid_email(value):
    """Apply a conservative validation before handing an address to SMTP."""
    if not value or len(value) > 254 or any(char in value for char in "\r\n"):
        return False
    _, address = parseaddr(value)
    if address != value or address.count("@") != 1:
        return False
    local, domain = address.rsplit("@", 1)
    return bool(local and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def ensure_user(user):
    """Create/update a user even when they interact without calling /start."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username = excluded.username""",
            (user.id, user.username),
        )
        conn.commit()


def attachment_size(message):
    if message.document:
        return message.document.file_size or 0
    if message.photo:
        return message.photo[-1].file_size or 0
    return 0

# Global dict to track media groups: {media_group_id: {'messages': [...], 'task': asyncio.Task}}
media_groups = {}

async def check_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_maintenance_mode() and user_id not in ADMIN_IDS:
        await update.message.reply_text(tr("maintenance_msg", str(user_id)))
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Ensure user exists in DB
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)
        """, (user_id, username))
        conn.commit()
        
        # Check if VIP
        row = conn.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
        is_vip = row['is_vip'] if row else False

    msg = tr("welcome", str(user_id))
    if is_vip:
        msg += "\n\n" + tr("vip_bonuses", str(user_id))
    
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(tr("help_msg", str(user_id)))

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    user_id = update.effective_user.id
    
    with get_db() as conn:
        history = conn.execute("""
            SELECT to_email, sent_at FROM history 
            WHERE user_id = ? 
            ORDER BY sent_at DESC LIMIT 5
        """, (user_id,)).fetchall()
    
    if not history:
        await update.message.reply_text(tr("no_history_user", str(user_id)))
        return

    msg = "\n\n".join([f"📤 {h['sent_at']}\nTo: {h['to_email']}" for h in history])
    await update.message.reply_text(tr("history_header", str(user_id)) + msg)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    user_id = update.effective_user.id
    context.user_data.clear()
    await update.message.reply_text(tr("operation_cancelled", str(user_id)))

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    user_id = update.effective_user.id
    await update.message.reply_text(tr("about_msg", str(user_id)))

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang:fr"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ]
    await update.message.reply_text(
        tr("choose_language", str(user_id)),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with get_db() as conn:
        row = conn.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
        is_vip = row['is_vip'] if row else False
    
    if not is_vip:
        await update.message.reply_text(tr("not_vip", str(user_id)))
        return
    
    await update.message.reply_text(tr("is_vip", str(user_id)) + "\n\n" + tr("vip_bonuses", str(user_id)))

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(tr("my_id", str(user_id), user_id=user_id))

async def addcontact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    user_id = update.effective_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Usage: /addcontact <name> <email>"))
        return
    
    name = context.args[0]
    email = context.args[1]
    
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO contacts (user_id, name, email) VALUES (?, ?, ?)", (user_id, name, email))
            conn.commit()
        await update.message.reply_text(f"✅ Contact '{name}' added.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"❌ Contact '{name}' already exists.")
    except Exception as e:
        await update.message.reply_text(tr("error_generic", str(user_id), error=str(e)))

async def delcontact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_maintenance(update, context): return
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(tr("error_generic", str(user_id), error="Usage: /delcontact <name>"))
        return
    
    name = context.args[0]
    
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM contacts WHERE user_id = ? AND name = ?", (user_id, name))
        conn.commit()
        if cursor.rowcount > 0:
            await update.message.reply_text(f"✅ Contact '{name}' deleted.")
        else:
            await update.message.reply_text(f"❌ Contact '{name}' not found.")

# Multi-Email Management Commands

async def process_collected_media(media_group_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Process all collected media from a media group after a delay"""
    await asyncio.sleep(1)  # Wait 1 second to collect all media
    
    if media_group_id not in media_groups:
        return
    
    messages = media_groups[media_group_id]['messages']
    del media_groups[media_group_id]  # Clean up
    
    if not messages:
        return
    
    # Collect all attachments and captions from the group
    text_parts = []
    attachments = []
    
    for msg in messages:
        if msg.caption and msg.caption not in text_parts:
            text_parts.append(msg.caption)
        
        if msg.document:
            file = await msg.document.get_file()
            file_bytes = await file.download_as_bytearray()
            attachments.append((msg.document.file_name, file_bytes))
        
        if msg.photo:
            largest_photo = msg.photo[-1]
            file = await largest_photo.get_file()
            file_bytes = await file.download_as_bytearray()
            # Use unique filename for each photo
            filename = f"photo_{msg.photo[-1].file_unique_id}.jpg"
            attachments.append((filename, file_bytes))
    
    text = "\n".join(text_parts)
    
    # Store in context
    context.user_data["text"] = text
    context.user_data["attachments"] = attachments
    
    # Show contact selection
    with get_db() as conn:
        contacts = conn.execute("SELECT name, email FROM contacts WHERE user_id = ?", (user_id,)).fetchall()
    
    keyboard = []
    for c in contacts:
        keyboard.append([InlineKeyboardButton(f"👤 {c['name']}", callback_data=f"email:{c['email']}")])
    
    keyboard.append([InlineKeyboardButton(tr("other_button", str(user_id)), callback_data="email:other")])
    
    # Reply to the first message in the group
    await messages[0].reply_text(
        tr("ask_destination", str(user_id)),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    log_action(f"📩 Received message from user {user_id}", user_id)
    
    # Check blacklist
    with get_db() as conn:
        row = conn.execute("SELECT is_blacklisted FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row and row['is_blacklisted']:
            await update.message.reply_text(tr("banned_msg", str(user_id)))
            return

    if await check_maintenance(update, context): return

    # Continue the multi-step HTML template flow before treating the message as
    # a new email body.
    if context.user_data.get("state") == "awaiting_template_title":
        from handlers.html_templates import handle_template_title
        await handle_template_title(update, context)
        return
    if context.user_data.get("state") == "awaiting_template_footer":
        from handlers.html_templates import handle_template_footer
        await handle_template_footer(update, context)
        return
    
    # Check if user is entering email manually
    if context.user_data.get("awaiting_email"):
        email = (update.message.text or "").strip()
        if not is_valid_email(email):
            await update.message.reply_text("❌ Adresse e-mail invalide. Merci de réessayer ou utilisez /cancel.")
            return
        context.user_data["awaiting_email"] = False
        context.user_data["selected_email"] = email
        await update.message.reply_text(tr("email_selected", str(user_id), email=email))
        
        # Import send_preview from callbacks (or move it to a shared module)
        from handlers.callbacks import send_preview
        await send_preview(user_id, context)
        return

    # Check if user is adding a note
    if context.user_data.get("awaiting_note"):
        note = update.message.text.strip()
        context.user_data["awaiting_note"] = False
        
        # Append note to existing text
        existing_text = context.user_data.get("text", "")
        if existing_text:
            context.user_data["text"] = f"{existing_text}\n\n📝 Note: {note}"
        else:
            context.user_data["text"] = f"📝 Note: {note}"
        
        await update.message.reply_text(f"✅ Note added!\n\nNow choose destination:")
        
        # Fetch contacts
        with get_db() as conn:
            contacts = conn.execute("SELECT name, email FROM contacts WHERE user_id = ?", (user_id,)).fetchall()
        
        keyboard = []
        for c in contacts:
            keyboard.append([InlineKeyboardButton(f"👤 {c['name']}", callback_data=f"email:{c['email']}")])
        
        keyboard.append([InlineKeyboardButton(tr("other_button", str(user_id)), callback_data="email:other")])
        
        await context.bot.send_message(
            chat_id=user_id,
            text=tr("ask_destination", str(user_id)),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Check if this is part of a media group (album)
    media_group_id = update.message.media_group_id
    
    if media_group_id:
        # This message is part of a media group
        if media_group_id not in media_groups:
            # First message in this group - initialize
            media_groups[media_group_id] = {
                'messages': [],
                'task': None
            }
        
        current_size = sum(attachment_size(item) for item in media_groups[media_group_id]['messages'])
        new_size = attachment_size(update.message)
        if new_size > MAX_ATTACHMENT_BYTES or current_size + new_size > MAX_TOTAL_ATTACHMENT_BYTES:
            media_groups.pop(media_group_id, None)
            await update.message.reply_text("❌ Pièces jointes trop volumineuses (25 Mo maximum au total).")
            return

        # Add this message to the group
        media_groups[media_group_id]['messages'].append(update.message)
        
        # Cancel existing task if any
        if media_groups[media_group_id]['task']:
            media_groups[media_group_id]['task'].cancel()
        
        # Create new task to process after delay
        task = asyncio.create_task(process_collected_media(media_group_id, user_id, context))
        media_groups[media_group_id]['task'] = task
        
        return  # Don't process immediately
    
    # Process single message content (not part of a group)
    if attachment_size(update.message) > MAX_ATTACHMENT_BYTES:
        await update.message.reply_text("❌ Cette pièce jointe dépasse la limite de 20 Mo.")
        return
    text_parts = []
    attachments = []
    
    if update.message.text:
        text_parts.append(update.message.text)
    
    if update.message.document:
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        attachments.append((update.message.document.file_name, file_bytes))
        if update.message.caption: text_parts.append(update.message.caption)
            
    if update.message.photo:
        largest_photo = update.message.photo[-1]
        file = await largest_photo.get_file()
        file_bytes = await file.download_as_bytearray()
        attachments.append(("photo.jpg", file_bytes))
        if update.message.caption: text_parts.append(update.message.caption)

    text = "\n".join(text_parts)
    
    if text.strip() or attachments:
        # Store message data
        context.user_data["text"] = text
        context.user_data["attachments"] = attachments
        
        # Show contact selection immediately
        with get_db() as conn:
            contacts = conn.execute("SELECT name, email FROM contacts WHERE user_id = ?", (user_id,)).fetchall()
        
        keyboard = []
        for c in contacts:
            keyboard.append([InlineKeyboardButton(f"👤 {c['name']}", callback_data=f"email:{c['email']}")])
        
        keyboard.append([InlineKeyboardButton(tr("other_button", str(user_id)), callback_data="email:other")])
        
        await update.message.reply_text(
            tr("ask_destination", str(user_id)),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(tr("unknown_command", str(user_id)))


async def trigger_send_flow(user_id, text, attachments, context):
    """Start recipient selection for reusable content such as a template."""
    context.user_data["text"] = text
    context.user_data["attachments"] = attachments
    with get_db() as conn:
        contacts = conn.execute(
            "SELECT name, email FROM contacts WHERE user_id = ? ORDER BY name", (user_id,)
        ).fetchall()
    keyboard = [
        [InlineKeyboardButton(f"👤 {contact['name']}", callback_data=f"email:{contact['email']}")]
        for contact in contacts
    ]
    keyboard.append([InlineKeyboardButton(tr("other_button", str(user_id)), callback_data="email:other")])
    await context.bot.send_message(
        chat_id=user_id,
        text=tr("ask_destination", str(user_id)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
