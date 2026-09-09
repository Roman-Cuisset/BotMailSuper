import json
import os
from pathlib import Path

# Global dictionary to store translations
_translations = {}
DEFAULT_LANG = "en"

def load_translations(locales_dir="locales"):
    """Loads translation files from the specified directory."""
    global _translations
    _translations = {}
    
    path = Path(locales_dir)
    if not path.exists():
        print(f"Warning: Locales directory '{locales_dir}' not found.")
        return

    for file in path.glob("*.json"):
        lang_code = file.stem
        try:
            with open(file, "r", encoding="utf-8") as f:
                _translations[lang_code] = json.load(f)
        except Exception as e:
            print(f"Error loading translation file {file}: {e}")

def tr(key, lang=DEFAULT_LANG, **kwargs):
    """
    Translates a key into the target language.
    Supports format strings (e.g., "Hello {name}").
    If lang looks like a user_id (numeric string), fetch the user's language from DB.
    """
    # Check if lang is a user_id (numeric string) and fetch actual language
    if lang and lang.isdigit():
        try:
            from database.db import get_db
            user_id = int(lang)
            with get_db() as conn:
                row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
                if row and row['lang']:
                    lang = row['lang']
                else:
                    lang = DEFAULT_LANG
        except Exception:
            lang = DEFAULT_LANG
    
    lang_data = _translations.get(lang, {})
    text = lang_data.get(key)
    
    # Fallback to default language if key not found
    if text is None:
        text = _translations.get(DEFAULT_LANG, {}).get(key, key)
    
    if text and kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text # Return unformatted text if keys are missing
            
    return text
