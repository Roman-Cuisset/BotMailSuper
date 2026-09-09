#!/usr/bin/env python3
"""
Migration script to add encrypted_password column to user_emails table
"""
from database.db import get_db

def add_password_column():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check columns
        cursor.execute("PRAGMA table_info(user_emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'encrypted_password' not in columns:
            print("Adding 'encrypted_password' column to user_emails table...")
            cursor.execute("ALTER TABLE user_emails ADD COLUMN encrypted_password TEXT DEFAULT ''")
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("ℹ️  Column already exists.")

if __name__ == "__main__":
    add_password_column()
