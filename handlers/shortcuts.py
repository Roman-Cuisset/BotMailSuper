"""
Quick Shortcuts Commands - Phase 4
Allows users to map drafts to quick commands /quick1, /quick2, etc.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_db
from handlers.drafts import senddraft_command

async def setquick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a quick shortcut to a draft"""
    user_id = update.effective_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /setquick <1-3> <nom_du_brouillon>\n"
            "Exemple: /setquick 1 MonBrouillon"
        )
        return
    
    try:
        slot_id = int(context.args[0])
        if slot_id not in [1, 2, 3]:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Le numéro doit être 1, 2 ou 3.")
        return
        
    draft_name = " ".join(context.args[1:])
    
    # Verify draft exists
    with get_db() as conn:
        draft = conn.execute("""
            SELECT 1 FROM drafts WHERE user_id = ? AND name = ?
        """, (user_id, draft_name)).fetchone()
        
        if not draft:
            await update.message.reply_text(f"❌ Brouillon '{draft_name}' introuvable.")
            return
            
        # Save shortcut
        conn.execute("""
            INSERT OR REPLACE INTO quick_shortcuts (user_id, slot_id, draft_name)
            VALUES (?, ?, ?)
        """, (user_id, slot_id, draft_name))
        conn.commit()
        
    await update.message.reply_text(f"✅ Raccourci /quick{slot_id} associé au brouillon '{draft_name}' !")

async def quick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute a quick shortcut"""
    user_id = update.effective_user.id
    command = update.message.text.split()[0][1:] # remove /
    
    try:
        # Extract slot number from command (quick1 -> 1)
        slot_id = int(command.replace("quick", ""))
    except ValueError:
        return

    with get_db() as conn:
        shortcut = conn.execute("""
            SELECT draft_name FROM quick_shortcuts
            WHERE user_id = ? AND slot_id = ?
        """, (user_id, slot_id)).fetchone()
    
    if not shortcut:
        await update.message.reply_text(
            f"❌ Aucun raccourci défini pour /quick{slot_id}.\n"
            f"Utilisez /setquick {slot_id} <brouillon> pour le configurer."
        )
        return
    
    draft_name = shortcut['draft_name']
    
    # Reuse senddraft logic
    # We need to mock context.args for senddraft_command
    context.args = draft_name.split()
    await senddraft_command(update, context)
