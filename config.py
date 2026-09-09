import os
from dotenv import load_dotenv

load_dotenv("secrets.env")

# Limite d'envois par minute par utilisateur
MAX_MESSAGES_PER_MINUTE = 20

# Activer la suppression automatique de l'historique après N jours (False pour désactiver)
AUTO_CLEANUP_ENABLED = True
DAYS_TO_KEEP_HISTORY = 30  # Nombre de jours avant suppression

# Dossier de sauvegarde locale
LOCAL_SAVE_FOLDER = "TelegramMailBotFiles"

# config.py

# Limite d'envois par minute par utilisateur
MAX_MESSAGES_PER_MINUTE = 20

# Activer la suppression automatique de l'historique après N jours (False pour désactiver)
AUTO_CLEANUP_ENABLED = True
DAYS_TO_KEEP_HISTORY = 30  # Nombre de jours avant suppression

# Dossier de sauvegarde locale
LOCAL_SAVE_FOLDER = "TelegramMailBotFiles"

# Fichier historique chiffré
HISTORY_FILE = "history.json"

# Fichier de logs
LOG_FILE = "bot_log.txt"

# Admin IDs, comma-separated in secrets.env / the process environment.
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}
