#!/usr/bin/env python3
"""
Migration script to create drafts table for Phase 4
"""
from database.db import get_db

def create_drafts_table():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create drafts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                to_email TEXT,
                subject TEXT,
                body TEXT,
                attachments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        """)
        
        conn.commit()
        print("✅ drafts table created successfully!")

if __name__ == "__main__":
    create_drafts_table()
