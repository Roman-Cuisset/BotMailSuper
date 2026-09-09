import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db, get_db

def load_json(filename):
    if not Path(filename).exists():
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def migrate():
    print("Initializing database...")
    init_db()
    
    users_file = "users.json"
    vip_file = "vip_users.json"
    blacklist_file = "blacklist.json"
    lang_file = "user_lang.json"
    
    users_set = set(load_json(users_file) or [])
    vip_set = set(load_json(vip_file) or [])
    blacklist_set = set(load_json(blacklist_file) or [])
    user_langs = load_json(lang_file) or {}
    
    # Merge all user IDs
    all_user_ids = users_set | vip_set | blacklist_set | set(map(int, user_langs.keys()))
    
    print(f"Found {len(all_user_ids)} unique users to migrate.")
    
    with get_db() as conn:
        cursor = conn.cursor()
        count = 0
        for user_id in all_user_ids:
            try:
                user_id = int(user_id)
                is_vip = user_id in vip_set
                is_blacklisted = user_id in blacklist_set
                lang = user_langs.get(str(user_id), "en")
                
                # Default quota
                quota = 20
                if is_vip:
                    quota = 1_000_000
                
                cursor.execute("""
                    INSERT OR REPLACE INTO users (user_id, lang, quota, is_vip, is_blacklisted)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, lang, quota, is_vip, is_blacklisted))
                count += 1
            except Exception as e:
                print(f"Error migrating user {user_id}: {e}")
        
        conn.commit()
        print(f"Successfully migrated {count} users.")

if __name__ == "__main__":
    migrate()
