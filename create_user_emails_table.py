#!/usr/bin/env python3
"""
Migration script to create user_emails table for multi-email support
"""
from database.db import get_db

def create_user_emails_table():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create user_emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_address TEXT NOT NULL,
                label TEXT DEFAULT '',
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, email_address)
            )
        """)
        
        conn.commit()
        print("✅ user_emails table created successfully!")

if __name__ == "__main__":
    create_user_emails_table()
