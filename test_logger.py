import logging
from logging.handlers import RotatingFileHandler
import sys

# Configuration du logger
logger = logging.getLogger('telegram_bot')
logger.setLevel(logging.INFO)

# Filtre personnalisé pour exclure les requêtes getUpdates
class TelegramFilter(logging.Filter):
    def filter(self, record):
        # Filtrer les requêtes HTTP de routine
        if "HTTP Request" in record.msg and "getUpdates" in record.msg:
            return False
        return True

# Handler pour le fichier avec rotation
file_handler = RotatingFileHandler(
    'filtered_bot_log.txt',
    maxBytes=1024*1024,  # 1MB max
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Handler pour la console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Format personnalisé
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Ajout du filtre
file_handler.addFilter(TelegramFilter())
console_handler.addFilter(TelegramFilter())

# Configuration des handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def test_logging():
    print("\nDémarrage du test de logging...")
    
    # Test des requêtes à filtrer
    logger.info("HTTP Request: POST /bot123/getUpdates")  # Devrait être filtré
    logger.info("HTTP Request: GET /bot123/getMe")  # Ne devrait pas être filtré
    
    # Test des actions utilisateurs
    logger.info("User @test sent command /start")  # Devrait apparaître
    logger.info("Action: User 123456 joined the chat")  # Devrait apparaître
    
    # Test des erreurs
    logger.error("Database connection failed")  # Devrait apparaître
    logger.error("Network timeout")  # Devrait apparaître
    
    print("\nTest terminé! Vérifiez filtered_bot_log.txt")

if __name__ == "__main__":
    test_logging()
