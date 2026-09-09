import json
import logging
from pathlib import Path
from fnmatch import fnmatch

logger = logging.getLogger(__name__)

EXCLUSIONS_FILE = Path(__file__).parent.parent / "smtp_exclusions.json"

def load_smtp_exclusions():
    """
    Charge la liste d'exclusion SMTP depuis le fichier JSON.
    
    Returns:
        tuple: (exclusions_list, notes_dict)
        - exclusions_list: Liste des patterns d'emails exclus
        - notes_dict: Dictionnaire {pattern: note}
    """
    try:
        exclusions_path = Path(EXCLUSIONS_FILE)
        if not exclusions_path.exists():
            logger.warning(f"⚠️ Fichier {EXCLUSIONS_FILE} non trouvé, création avec liste vide")
            save_smtp_exclusions([], {})
            return [], {}
        
        with open(exclusions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exclusions = data.get('exclusions', [])
        notes = data.get('notes', {})
        
        logger.info(f"✅ {len(exclusions)} pattern(s) d'exclusion SMTP chargé(s)")
        return exclusions, notes
    
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des exclusions SMTP: {e}")
        return [], {}


def save_smtp_exclusions(exclusions, notes):
    """
    Sauvegarde la liste d'exclusion SMTP dans le fichier JSON.
    
    Args:
        exclusions (list): Liste des patterns d'emails exclus
        notes (dict): Dictionnaire {pattern: note}
    """
    try:
        data = {
            'exclusions': exclusions,
            'notes': notes
        }
        
        with open(EXCLUSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ {len(exclusions)} pattern(s) d'exclusion SMTP sauvegardé(s)")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde des exclusions SMTP: {e}")
        return False


def is_smtp_excluded(email):
    """
    Vérifie si une adresse email correspond à un pattern d'exclusion SMTP.
    Supporte les wildcards (ex: *@mail.ru, user@*.com).
    
    Args:
        email (str): Adresse email à vérifier
    
    Returns:
        bool: True si l'email doit utiliser uniquement SMTP, False sinon
    """
    if not email:
        return False
    
    email = email.lower().strip()
    exclusions, _ = load_smtp_exclusions()
    
    for pattern in exclusions:
        pattern = pattern.lower().strip()
        
        # Vérification exacte
        if email == pattern:
            logger.info(f"🔒 Email {email} exclu (correspondance exacte: {pattern})")
            return True
        
        # Vérification avec wildcard
        if '*' in pattern:
            if fnmatch(email, pattern):
                logger.info(f"🔒 Email {email} exclu (pattern wildcard: {pattern})")
                return True
    
    return False


def add_smtp_exclusion(pattern, note=""):
    """
    Ajoute un pattern à la liste d'exclusion SMTP.
    
    Args:
        pattern (str): Pattern d'email à exclure (ex: *@mail.ru, user@example.com)
        note (str): Note optionnelle expliquant la raison de l'exclusion
    
    Returns:
        bool: True si ajouté avec succès, False sinon
    """
    try:
        pattern = pattern.lower().strip()
        
        if not pattern:
            logger.error("❌ Pattern vide, impossible d'ajouter")
            return False
        
        exclusions, notes = load_smtp_exclusions()
        
        if pattern in exclusions:
            logger.warning(f"⚠️ Pattern {pattern} déjà dans la liste d'exclusion")
            return False
        
        exclusions.append(pattern)
        if note:
            notes[pattern] = note
        
        save_smtp_exclusions(exclusions, notes)
        logger.info(f"✅ Pattern {pattern} ajouté à la liste d'exclusion SMTP")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'ajout du pattern {pattern}: {e}")
        return False


def remove_smtp_exclusion(pattern):
    """
    Retire un pattern de la liste d'exclusion SMTP.
    
    Args:
        pattern (str): Pattern d'email à retirer
    
    Returns:
        bool: True si retiré avec succès, False sinon
    """
    try:
        pattern = pattern.lower().strip()
        exclusions, notes = load_smtp_exclusions()
        
        if pattern not in exclusions:
            logger.warning(f"⚠️ Pattern {pattern} non trouvé dans la liste d'exclusion")
            return False
        
        exclusions.remove(pattern)
        notes.pop(pattern, None)
        
        save_smtp_exclusions(exclusions, notes)
        logger.info(f"✅ Pattern {pattern} retiré de la liste d'exclusion SMTP")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erreur lors du retrait du pattern {pattern}: {e}")
        return False


def get_all_exclusions():
    """
    Récupère toutes les exclusions avec leurs notes.
    
    Returns:
        list: Liste de tuples (pattern, note)
    """
    exclusions, notes = load_smtp_exclusions()
    return [(pattern, notes.get(pattern, "")) for pattern in exclusions]
