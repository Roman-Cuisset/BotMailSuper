import sqlite3
from contextlib import contextmanager

DB_FILE = "bot.db"

def init_db():
    """Initializes the database with the required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                lang TEXT DEFAULT 'en',
                quota INTEGER DEFAULT 20,
                is_vip BOOLEAN DEFAULT 0,
                is_blacklisted BOOLEAN DEFAULT 0,
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Columns introduced by older one-off migration scripts. Keeping them
        # here makes a fresh installation and an upgraded installation behave
        # identically.
        user_columns = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
        if "signature" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN signature TEXT DEFAULT ''")
        
        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                to_email TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                to_email TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                attachments TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_shortcuts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL CHECK(slot_id BETWEEN 1 AND 3),
                draft_name TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, slot_id)
            )
        """)

        # Contacts table (Personal Address Book)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, name)
            )
        """)

        # Daily Stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                message_count INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0
            )
        """)
        
        # Email Templates table (All Users) - v3.5
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, name)
            )
        """)
        
        # Contact Groups table (VIP Only) - v3.5
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, group_name)
            )
        """)
        
        # Group Members table (VIP Only) - v3.5
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES contact_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
                UNIQUE(group_id, contact_id)
            )
        """)
        
        # Scheduled Emails table (VIP Only) - v3.5
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                attachments TEXT,
                send_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Settings table (Global Config)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Insert default maintenance mode if not exists
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', '0')")
        
        # User Emails table (Multi-Account) - Phase 2
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_address TEXT NOT NULL,
                label TEXT DEFAULT '',
                encrypted_password TEXT DEFAULT '',
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, email_address)
            )
        """)
        
        conn.commit()

@contextmanager
def get_db():
    """Context manager for database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
