"""
Migration script to create quick_shortcuts table for Phase 4
"""
from database.db import get_db

def create_shortcuts_table():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create quick_shortcuts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_shortcuts (
                user_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                draft_name TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, slot_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("✅ quick_shortcuts table created successfully!")

if __name__ == "__main__":
    create_shortcuts_table()
