import os
from dotenv import load_dotenv

load_dotenv("secrets.env")

# Limite d'envois par minute par utilisateur
MAX_MESSAGES_PER_MINUTE = 20

# Activer la suppression automatique de l'historique après N jours (False pour désactiver)
AUTO_CLEANUP_ENABLED = True
DAYS_TO_KEEP_HISTORY = 30  # Nombre de jours avant suppression
STORE_HISTORY_CONTENT = os.getenv("STORE_HISTORY_CONTENT", "true").lower() == "true"

# Telegram files are downloaded into memory before sending.
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 25 * 1024 * 1024

# Fichier de logs
LOG_FILE = "bot_log.txt"

# Admin IDs, comma-separated in secrets.env / the process environment.
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}
