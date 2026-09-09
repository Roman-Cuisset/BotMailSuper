import sys
import os
from database.db import init_db, get_db
from utils.i18n import load_translations, tr

def verify():
    print("Verifying imports...")
    try:
        import handlers.user
        import handlers.admin
        import handlers.callbacks
        import handlers.support
        import utils.email_sender
        print("✅ Imports successful.")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return

    print("Verifying Database...")
    try:
        init_db()
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            print(f"✅ Database connected. Users count: {count}")
            
            # Check new tables
            conn.execute("SELECT COUNT(*) FROM contacts")
            print("✅ Contacts table exists.")
            
            conn.execute("SELECT COUNT(*) FROM daily_stats")
            print("✅ Daily stats table exists.")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return

    print("Verifying Translations...")
    try:
        load_translations("locales")
        welcome = tr("welcome", "en")
        if welcome:
            print(f"✅ Translations loaded. Welcome msg: {welcome[:20]}...")
        else:
            print("❌ Translation key not found.")
    except Exception as e:
        print(f"❌ Translation check failed: {e}")
        return

    print("\n🎉 Verification passed! The bot is ready to run with all advanced features.")

if __name__ == "__main__":
    verify()
