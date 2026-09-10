import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram import BotCommand, MenuButtonWebApp, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError

from config import LOG_FILE
from database.db import init_db
from handlers.callbacks import button_handler
from utils.i18n import load_translations, tr
from utils.email_sender import log_action
from utils.scheduler import scheduled_email_worker
from utils.cleanup import retention_worker
from handlers.drafts import savedraft_command, drafts_command, senddraft_command, deldraft_command
from handlers.templates import savetemplate_command, templates_command, usetemplate_command, deltemplate_command
from handlers.shortcuts import setquick_command, quick_command
from handlers.html_templates import htmltemplate_command
from handlers.vip_features import creategroup_command, addtogroup_command, groups_command, delgroup_command, schedule_command, scheduled_command, cancelschedule_command, mystats_command

# Import handlers
from handlers.user import start, help_command, history_command, cancel_command, about_command, lang_command, vip_command, myid_command, handle_message, addcontact_command, delcontact_command, contacts_command
from handlers.admin import admin_command, ban_command, unban_command, setvip_command, removevip_command, setquota_command, stats_command, maintenance_command, feedback_command, broadcast_command
from handlers.support import support_command, reply_command

# Load env
load_dotenv("secrets.env", override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Logging setup
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
# httpx logs full Telegram Bot API URLs, which include the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_action(f"⚠️ Exception: {context.error}")
    print(f"⚠️ Exception: {context.error}")
    if update and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else None
        try:
            await update.effective_message.reply_text(tr("error_occurred", str(user_id)))
        except TelegramError:
            pass

async def post_init(application):
    # Set commands
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help"),
        BotCommand("history", "Show history"),
        BotCommand("cancel", "Cancel operation"),
        BotCommand("about", "About the bot"),
        BotCommand("lang", "Change language"),
        BotCommand("vip", "VIP info"),
        BotCommand("myid", "Show your user ID"),
        BotCommand("addcontact", "Add a contact"),
        BotCommand("delcontact", "Delete a contact"),
        BotCommand("contacts", "List or search contacts"),
        BotCommand("support", "Contact support"),
    ]
    await application.bot.set_my_commands(commands)
    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    if webapp_url.startswith("https://"):
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Ouvrir BotMailSuper", web_app=WebAppInfo(url=webapp_url))
        )
    
    asyncio.create_task(scheduled_email_worker())
    asyncio.create_task(retention_worker())
    
    print("🤖 Bot started and ready!")

def main():
    # Set console title for easier identification
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("Bot Mail Super")
    except Exception:
        pass

    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found in secrets.env")
        return

    # Init DB and I18n
    init_db()
    load_translations("locales")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # User Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("addcontact", addcontact_command))
    app.add_handler(CommandHandler("delcontact", delcontact_command))
    app.add_handler(CommandHandler("contacts", contacts_command))
    
    # Admin Commands
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("setvip", setvip_command))
    app.add_handler(CommandHandler("removevip", removevip_command))
    app.add_handler(CommandHandler("setquota", setquota_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    app.add_handler(CommandHandler("savedraft", savedraft_command))
    app.add_handler(CommandHandler("drafts", drafts_command))
    app.add_handler(CommandHandler("senddraft", senddraft_command))
    app.add_handler(CommandHandler("deldraft", deldraft_command))
    app.add_handler(CommandHandler("savetemplate", savetemplate_command))
    app.add_handler(CommandHandler("templates", templates_command))
    app.add_handler(CommandHandler("usetemplate", usetemplate_command))
    app.add_handler(CommandHandler("deltemplate", deltemplate_command))
    app.add_handler(CommandHandler("setquick", setquick_command))
    app.add_handler(CommandHandler(["quick1", "quick2", "quick3"], quick_command))
    app.add_handler(CommandHandler("htmltemplate", htmltemplate_command))
    app.add_handler(CommandHandler("creategroup", creategroup_command))
    app.add_handler(CommandHandler("addtogroup", addtogroup_command))
    app.add_handler(CommandHandler("groups", groups_command))
    app.add_handler(CommandHandler("delgroup", delgroup_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("scheduled", scheduled_command))
    app.add_handler(CommandHandler("cancelschedule", cancelschedule_command))
    app.add_handler(CommandHandler("mystats", mystats_command))

    app.add_handler(CommandHandler("userstats", stats_command)) # Alias
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("reply", reply_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(button_handler))

    # Messages (must be last)
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # Errors
    app.add_error_handler(error_handler)

    print("🤖 Bot polling...")
    app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    main()
