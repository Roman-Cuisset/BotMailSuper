"""
HTML Template Commands - Phase 4
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.html_templates import apply_template, markdown_to_html

async def htmltemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Choose HTML template for current message"""
    user_id = update.effective_user.id
    
    # Check if there's a message to format
    text = context.user_data.get("text", "")
    if not text:
        await update.message.reply_text(
            "❌ Aucun message à formater. Envoyez d'abord un message."
        )
        return
    
    # Show template options
    keyboard = [
        [InlineKeyboardButton("💼 Business", callback_data="htmltpl:business")],
        [InlineKeyboardButton("😊 Casual", callback_data="htmltpl:casual")],
        [InlineKeyboardButton("📰 Newsletter", callback_data="htmltpl:newsletter")],
        [InlineKeyboardButton("✨ Minimal", callback_data="htmltpl:minimal")],
        [InlineKeyboardButton("📝 Markdown Simple", callback_data="htmltpl:markdown")],
        [InlineKeyboardButton("❌ Annuler", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        "🎨 **Choisissez un template HTML :**\n\n"
        "💼 Business - Professionnel avec en-tête\n"
        "😊 Casual - Décontracté et coloré\n"
        "📰 Newsletter - Style magazine\n"
        "✨ Minimal - Simple et élégant\n"
        "📝 Markdown - Conversion Markdown → HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_html_template_callback(query, context):
    """Handle HTML template selection"""
    user_id = query.from_user.id
    template_name = query.data.split(":", 1)[1]
    
    text = context.user_data.get("text", "")
    if not text:
        await query.edit_message_text("❌ Aucun message à formater")
        return
    
    # Apply template
    if template_name == "markdown":
        html_body = markdown_to_html(text)
    else:
        # Ask for title and footer
        context.user_data["pending_template"] = template_name
        context.user_data["state"] = "awaiting_template_title"
        
        await query.edit_message_text(
            f"🎨 Template **{template_name}** sélectionné !\n\n"
            "Envoyez le **titre** de votre email (ou /skip pour utiliser le défaut) :",
            parse_mode="Markdown"
        )
        return
    
    # Save HTML body
    context.user_data["text"] = html_body
    await query.edit_message_text(
        "✅ Template HTML appliqué ! Votre email sera envoyé en HTML.\n\n"
        "Continuez le processus d'envoi normalement."
    )

async def handle_template_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle template title input"""
    if context.user_data.get("state") != "awaiting_template_title":
        return False
    
    title = update.message.text
    if title == "/skip":
        title = "Message"
    
    context.user_data["template_title"] = title
    context.user_data["state"] = "awaiting_template_footer"
    
    await update.message.reply_text(
        "Envoyez le **footer** (pied de page) ou /skip pour utiliser le défaut :",
        parse_mode="Markdown"
    )
    return True

async def handle_template_footer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle template footer input"""
    if context.user_data.get("state") != "awaiting_template_footer":
        return False
    
    footer = update.message.text
    if footer == "/skip":
        footer = "Sent via Bot Mail Super"
    
    # Apply template
    template_name = context.user_data.get("pending_template", "minimal")
    title = context.user_data.get("template_title", "Message")
    text = context.user_data.get("text", "")
    
    html_body = apply_template(text, template_name, title, footer)
    
    # Save HTML body
    context.user_data["text"] = html_body
    context.user_data["state"] = None
    
    await update.message.reply_text(
        "✅ Template HTML appliqué avec succès !\n\n"
        "Votre email sera envoyé en HTML avec mise en forme.\n"
        "Continuez le processus d'envoi normalement."
    )
    return True
