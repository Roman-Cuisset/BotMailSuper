#!/usr/bin/env python3
"""
Migration script to add auth_data column to user_emails table for OAuth tokens
"""
from database.db import get_db

def add_auth_data_column():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check columns
        cursor.execute("PRAGMA table_info(user_emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'auth_data' not in columns:
            print("Adding 'auth_data' column to user_emails table...")
            cursor.execute("ALTER TABLE user_emails ADD COLUMN auth_data TEXT DEFAULT ''")
            conn.commit()
            print("✅ Column 'auth_data' added successfully!")
        else:
            print("ℹ️  Column 'auth_data' already exists.")

if __name__ == "__main__":
    add_auth_data_column()
