#!/usr/bin/env python3
"""
Migration script to add signature column to users table
"""
from database.db import get_db

def add_signature_column():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'signature' not in columns:
            print("Adding 'signature' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN signature TEXT DEFAULT ''")
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("ℹ️  Column 'signature' already exists.")

if __name__ == "__main__":
    add_signature_column()
