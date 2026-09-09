#!/usr/bin/env python3
"""
Migration script to add PIN security and auto-destruction features
"""
from database.db import get_db

def add_phase2_columns():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check and add PIN column to users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'pin_hash' not in columns:
            print("Adding 'pin_hash' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT DEFAULT ''")
            print("✅ PIN column added!")
        else:
            print("ℹ️  'pin_hash' column already exists.")
        
        # Check and add expires_at column to history table
        cursor.execute("PRAGMA table_info(history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'expires_at' not in columns:
            print("Adding 'expires_at' column to history table...")
            cursor.execute("ALTER TABLE history ADD COLUMN expires_at TIMESTAMP DEFAULT NULL")
            print("✅ Auto-destruction column added!")
        else:
            print("ℹ️  'expires_at' column already exists.")
        
        conn.commit()
        print("\n✅ Phase 2 database migrations complete!")

if __name__ == "__main__":
    add_phase2_columns()
