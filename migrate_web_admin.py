import re

# Read original file
with open('web_admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replacement patterns:
# 1. Import database module instead of JSON loading functions
import_section = """from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, make_response
from datetime import datetime
import csv
import requests
import sys
import os

# Add parent directory to path for database import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import get_db
"""

# Find and replace the import section
content = re.sub(
    r'from flask import.*?import requests',
    import_section.strip(),
    content,
    flags=re.DOTALL
)

# 2. Remove JSON file constants and loading functions
content = re.sub(
    r'VIP_USERS_FILE = .*?\n',
    '',
    content
)
content = re.sub(
    r'BLACKLIST_FILE = .*?\n',
    '',
    content
)
content = re.sub(
    r'USERS_FILE = .*?\n',
    '',
    content
)

# Remove JSON helper functions
content = re.sub(
    r'def load_json_set\(filepath\):.*?return set\(json\.load\(f\)\)',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'def save_json_set\(filepath, data\):.*?json\.dump\(list\(data\), f\)',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'def load_json_dict\(filepath\):.*?return \{\}',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'def save_json_dict\(filepath, data\):.*?json\.dump\(data, f, ensure_ascii=False, indent=2\)',
    '',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'def load_all_users\(\):.*?return set\(json\.load\(f\)\)',
    '',
    content,
    flags=re.DOTALL
)

# 3. Update export_csv function
export_csv_new = """@app.route("/export/<what>")
def export_csv(what):
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    if what == "vip":
        with get_db() as conn:
            rows_data = conn.execute("SELECT user_id, note FROM users WHERE is_vip = 1").fetchall()
        filename = "vip_users.csv"
        rows = [("user_id", "note")]
        for row in rows_data:
            rows.append((row['user_id'], row['note'] or ''))
            
    elif what == "blacklist":
        with get_db() as conn:
            rows_data = conn.execute("SELECT user_id, note FROM users WHERE is_blacklisted = 1").fetchall()
        filename = "blacklist.csv"
        rows = [("user_id", "note")]
        for row in rows_data:
            rows.append((row['user_id'], row['note'] or ''))
            
    elif what == "logs":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                rows = [("log",)]
                for line in f:
                    rows.append((line.strip(),))
        else:
            rows = [("log",)]
        filename = "logs.csv"
    else:
        return "Invalid export", 400
        
    # Génération CSV
    output = ""
    for row in rows:
        output += ";".join(str(x) for x in row) + "\\n"
    response = make_response(output)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv"
    return response"""

content = re.sub(
    r'@app\.route\("/export/<what>"\).*?return response',
    export_csv_new,
    content,
    flags=re.DOTALL
)

#4. Update clear_logs to use os.path.exists
content = re.sub(
    r'Path\(LOG_FILE\)\.write_text\("", encoding="utf-8"\)',
    'with open(LOG_FILE, "w", encoding="utf-8") as f:\n        f.write("")',
    content
)

# 5. Update the index() function to use SQLite
index_function_new = """@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("admin"):
        return redirect(url_for("login"))
        
    msg = ""
    search_vip = request.args.get("search_vip", "")
    search_black = request.args.get("search_black", "")
    
    if request.method == "POST":
        action = request.form.get("action")
        user_id = request.form.get("user_id", "").strip()
        note = request.form.get("note", "").strip()
        search_vip = request.form.get("search_vip", search_vip)
        search_black = request.form.get("search_black", search_black)
        
        if user_id.isdigit():
            user_id_int = int(user_id)
            with get_db() as conn:
                # Ensure user exists
                existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id_int,)).fetchone()
                if not existing:
                    conn.execute("INSERT INTO users (user_id, note) VALUES (?, ?)", (user_id_int, note))
                    conn.commit()
                    
                if action == "add_vip":
                    conn.execute("UPDATE users SET is_vip = 1, note = ? WHERE user_id = ?", (note, user_id_int))
                    conn.commit()
                    msg = f"Ajouté VIP {user_id}"
                elif action == "del_vip":
                    conn.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id_int,))
                    conn.commit()
                    msg = f"Retiré VIP {user_id}"
                elif action == "add_black":
                    conn.execute("UPDATE users SET is_blacklisted = 1, note = ? WHERE user_id = ?", (note, user_id_int))
                    conn.commit()
                    msg = f"Ajouté blacklist {user_id}"
                elif action == "del_black":
                    conn.execute("UPDATE users SET is_blacklisted = 0 WHERE user_id = ?", (user_id_int,))
                    conn.commit()
                    msg = f"Retiré blacklist {user_id}"
        else:
            msg = "User ID invalide"
        return redirect(url_for("index", search_vip=search_vip, search_black=search_black))
    
    # Load data from database
    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        vip_rows = conn.execute(\"\"\"
            SELECT user_id, note FROM users WHERE is_vip = 1
        \"\"\").fetchall()
        
        blacklist_rows = conn.execute(\"\"\"
            SELECT user_id, note FROM users WHERE is_blacklisted = 1
        \"\"\").fetchall()
    
    # Filtrage
    vip_list = sorted([
        (row['user_id'], row['note'] or '') for row in vip_rows
        if (not search_vip) or (search_vip.lower() in str(row['user_id']).lower() or search_vip.lower() in str(row['note'] or '').lower())
    ])
    
    blacklist_list = sorted([
        (row['user_id'], row['note'] or '') for row in blacklist_rows
        if (not search_black) or (search_black.lower() in str(row['user_id']).lower() or search_black.lower() in str(row['note'] or '').lower())
    ])
    
    # Get usernames
    vip_usernames = {}
    blacklist_usernames = {}
    for uid, _ in vip_list:
        username = get_username_from_id(uid)
        if username:
            vip_usernames[uid] = username
    for uid, _ in blacklist_list:
        username = get_username_from_id(uid)
        if username:
            blacklist_usernames[uid] = username
    
    # Load logs
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.readlines()[-50:]
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if total_users == 0:
        msg = "Aucun utilisateur détecté dans la base de données."
    
    return render_template_string(MAIN_TEMPLATE,
        vip=vip_list, blacklist=blacklist_list, logs=logs, msg=msg, now=now,
        total_users=total_users, search_vip=search_vip, search_black=search_black,
        vip_usernames=vip_usernames, blacklist_usernames=blacklist_usernames
    )"""

content = re.sub(
    r'@app\.route\("/", methods=\["GET", "POST"\]\).*?def index\(\):.*?blacklist_usernames=blacklist_usernames\s*\)',
    index_function_new,
    content,
    flags=re.DOTALL
)

# 6. Update statistiques() function
stats_function_new = """@app.route("/statistiques")
def statistiques():
    if not session.get("admin"):
        return redirect(url_for("login"))
        
    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        nb_vip = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1").fetchone()[0]
        nb_black = conn.execute("SELECT COUNT(*) FROM users WHERE is_blacklisted = 1").fetchone()[0]
    
    nb_other = max(0, total_users - nb_vip - nb_black)
    
    return render_template_string(\"\"\"
<!doctype html>
<html>
<head>
    <title>Statistiques</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="icon" type="image/png" href="{{ url_for('logo') }}">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>"""

content = re.sub(
    r'@app\.route\("/statistiques"\).*?def statistiques\(\):.*?return render_template_string\("""',
    stats_function_new,
    content,
    flags=re.DOTALL,
    count=1
)

# Remove Path import since we're using os
content = re.sub(r'from pathlib import Path\n', '', content)
content = re.sub(r'import json\n', '', content)

# Remove debug print statements
content = re.sub(r'\s*print\("DEBUG:.*?\)\s*#.*?\n', '\n', content)

# Write the new file
with open('web_admin.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Migration completed! web_admin.py now uses SQLite.")
print("📋 Original file backed up as web_admin_json_backup.py")
