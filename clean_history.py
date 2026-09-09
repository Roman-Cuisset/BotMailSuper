import sqlite3

# Connect to the database
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

# Delete invalid email from history
cursor.execute("DELETE FROM history WHERE to_email = 'etst'")
conn.commit()

# Show remaining history
cursor.execute("SELECT user_id, to_email, sent_at FROM history ORDER BY sent_at DESC LIMIT 10")
results = cursor.fetchall()

print("✅ Deleted 'etst' from history")
print("\nRemaining history:")
for row in results:
    print(f"  User {row[0]} -> {row[1]} at {row[2]}")

conn.close()
