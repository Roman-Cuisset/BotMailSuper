import sqlite3
import time

print("Attente pour que la base de données soit libre...")
time.sleep(2)

try:
    conn = sqlite3.connect('bot.db', timeout=10)
    cursor = conn.cursor()
    
    # Vérifier les colonnes actuelles
    cursor.execute('PRAGMA table_info(users)')
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Colonnes actuelles: {columns}")
    
    if 'note' not in columns:
        print("Ajout de la colonne 'note'...")
        cursor.execute('ALTER TABLE users ADD COLUMN note TEXT DEFAULT ""')
        conn.commit()
        print("✅ Colonne 'note' ajoutée avec succès!")
        
        # Vérifier à nouveau
        cursor.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Colonnes après modification: {columns}")
    else:
        print("✅ La colonne 'note' existe déjà!")
    
    conn.close()
    
except sqlite3.OperationalError as e:
    print(f"❌ Erreur: {e}")
    print("La base de données est peut-être verrouillée par un autre processus.")
except Exception as e:
    print(f"❌ Erreur inattendue: {e}")
