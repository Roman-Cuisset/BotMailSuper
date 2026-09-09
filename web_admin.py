from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, make_response
from datetime import datetime, timedelta
import csv
import requests
import sys
import os
import json
import hmac
from dotenv import load_dotenv

# Add parent directory to path for database import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import get_db

load_dotenv("secrets.env")

app = Flask(__name__)
app.secret_key = os.getenv("WEB_SECRET_KEY") or os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("WEB_SECRET_KEY or SECRET_KEY must be configured")

LOG_FILE = "bot_log.txt"
SESSION_TIMEOUT = 600  # 10 minutes

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Database access functions handled by database/db.py

@app.before_request
def session_timeout():
    if "admin" in session:
        now = datetime.now().timestamp()
        last = session.get("last_active", now)
        if now - last > SESSION_TIMEOUT:
            session.pop("admin", None)
        else:
            session["last_active"] = now

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        supplied_password = request.form.get("password", "")
        if ADMIN_PASSWORD and hmac.compare_digest(supplied_password, ADMIN_PASSWORD):
            session["admin"] = True
            session["last_active"] = datetime.now().timestamp()
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Wrong password")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/logo")
def logo():
    return send_from_directory('.', 'logotype.png')

@app.route("/export/<what>")
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
        output += ";".join(str(x) for x in row) + "\n"
    response = make_response(output)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route("/clear_logs", methods=["POST"])
def clear_logs():
    if not session.get("admin"):
        return redirect(url_for("login"))
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
    return redirect(url_for("index"))

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    global ADMIN_PASSWORD
    if not session.get("admin"):
        return redirect(url_for("login"))
    msg = ""
    success = False
    if request.method == "POST":
        old = request.form.get("old_password")
        new = request.form.get("new_password")
        if old == ADMIN_PASSWORD and new:
            ADMIN_PASSWORD = new
            msg = "Mot de passe changé avec succès (valable jusqu'au redémarrage du serveur) !"
            success = True
        else:
            msg = "Ancien mot de passe incorrect ou nouveau mot de passe vide."
    return render_template_string("""
<!doctype html>
<html>
<head>
    <title>Changer le mot de passe admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="icon" type="image/png" href="{{ url_for('logo') }}">
    <style>
        body { background: #f8f9fa; }
        .center-card {
            max-width: 400px;
            margin: 60px auto;
        }
        .logo-round {
            height:48px;
            width:48px;
            object-fit:cover;
            border-radius:50%;
            margin-bottom: 16px;
            border:2px solid #e5e5e5;
            background:#fff;
            display:block;
            margin-left:auto;
            margin-right:auto;
            transition: box-shadow 0.2s, transform 0.2s;
        }
        .logo-round:hover {
            box-shadow: 0 0 0 4px #0d6efd33;
            transform: scale(1.08);
        }
        .card.rounded-4 {
            border-radius: 2rem !important;
            box-shadow: 0 6px 32px 0 #0001;
            transition: box-shadow 0.2s;
        }
        .card.rounded-4:hover {
            box-shadow: 0 12px 48px 0 #0002;
        }
        .toggle-pwd {
            cursor: pointer;
            position: absolute;
            right: 18px;
            top: 38px;
            /* Ajustement vertical précis pour l'alignement */
            color: #888;
            z-index: 2;
            padding: 0;
            background: none;
            border: none;
        }
        .position-relative {
                <div class="mb-3 position-relative">
                    <label for="old_password" class="form-label">Ancien mot de passe</label>
                    <input type="password" name="old_password" id="old_password" class="form-control" required autofocus>
                    <span class="toggle-pwd" onclick="togglePwd('old_password', this)">
                        <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zm-8 4.5c-3.314 0-6-3.134-6-4.5s2.686-4.5 6-4.5 6 3.134 6 4.5-2.686 4.5-6 4.5z"/>
                            <path d="M8 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 5a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
                        </svg>
                    </span>
                </div>
                <div class="mb-3 position-relative">
                    <label for="new_password" class="form-label">Nouveau mot de passe</label>
                    <input type="password" name="new_password" id="new_password" class="form-control" required>
                    <span class="toggle-pwd" onclick="togglePwd('new_password', this)">
                        <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zm-8 4.5c-3.314 0-6-3.134-6-4.5s2.686-4.5 6-4.5 6 3.134 6 4.5-2.686 4.5-6 4.5z"/>
                            <path d="M8 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 5a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
                        </svg>
                    </span>
                </div>
                <div class="d-grid gap-2">
                    <button class="btn btn-primary" type="submit">Changer</button>
                    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary">Retour</a>
                </div>
            </form>
        </div>
    </div>
</div>
<script>
function togglePwd(fieldId, el) {
    var input = document.getElementById(fieldId);
    if (input.type === "password") {
        input.type = "text";
        el.innerHTML = `<svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M13.359 11.238l1.42 1.42a.75.75 0 0 1-1.06 1.06l-1.42-1.42A7.48 7.48 0 0 1 8 13.5c-5 0-8-5.5-8-5.5a15.6 15.6 0 0 1 3.34-3.746l-1.42-1.42a.75.75 0 1 1 1.06-1.06l1.42 1.42A7.48 7.48 0 0 1 8 2.5c5 0 8 5.5 8 5.5a15.6 15.6 0 0 1-3.34 3.746zM8 4.5c-3.314 0-6 3.134-6 4.5s2.686 4.5 6 4.5 6-3.134 6-4.5-2.686-4.5-6-4.5zm0 2a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z"/>
        </svg>`;
    } else {
        input.type = "password";
        el.innerHTML = `<svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zm-8 4.5c-3.314 0-6-3.134-6-4.5s2.686-4.5 6-4.5 6 3.134 6 4.5-2.686 4.5-6 4.5z"/>
            <path d="M8 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 5a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
        </svg>`;
    }
}
</script>
</body>
</html>
    """, msg=msg, success=success)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global ADMIN_PASSWORD
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    password_msg = ""
    password_success = False
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old = request.form.get("old_password")
            new = request.form.get("new_password")
            if old == ADMIN_PASSWORD and new:
                ADMIN_PASSWORD = new
                password_msg = "Password changed successfully (valid until server restart)!"
                password_success = True
            else:
                password_msg = "Incorrect current password or empty new password."
    
    return render_template(
        "settings.html",
        active_page="settings",
        password_msg=password_msg,
        password_success=password_success,
        session_timeout=SESSION_TIMEOUT
    )

@app.route("/users")
def users():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    search = request.args.get("search", "").lower()
    
    with get_db() as conn:
        rows = conn.execute("SELECT user_id, username, is_vip, is_blacklisted, note FROM users").fetchall()
    
    users_list = []
    for row in rows:
        # Filter if search term is present
        if search:
            search_str = f"{row['user_id']} {row['username'] or ''} {row['note'] or ''}".lower()
            if search not in search_str:
                continue
                
        users_list.append({
            "user_id": row['user_id'],
            "username": row['username'],
            "is_vip": bool(row['is_vip']),
            "is_blacklisted": bool(row['is_blacklisted']),
            "note": row['note']
        })
    
    # Sort by VIP then ID
    users_list.sort(key=lambda x: (not x['is_vip'], x['user_id']))
    
    return render_template("users.html", active_page="users", users=users_list, search=search)

@app.route("/update_user", methods=["POST"])
def update_user():
    if not session.get("admin"):
        return redirect(url_for("login"))
        
    action = request.form.get("action")
    user_id = request.form.get("user_id")
    note = request.form.get("note", "").strip()
    
    if not user_id:
        return redirect(url_for("users"))
        
    try:
        user_id = int(user_id)
        with get_db() as conn:
            if action == "add_user":
                is_vip = 1 if request.form.get("is_vip") else 0
                conn.execute("""
                    INSERT INTO users (user_id, note, is_vip) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET note=excluded.note, is_vip=excluded.is_vip
                """, (user_id, note, is_vip))
                
            elif action == "add_vip":
                conn.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (user_id,))
                
            elif action == "del_vip":
                conn.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
                
            elif action == "ban":
                conn.execute("UPDATE users SET is_blacklisted = 1 WHERE user_id = ?", (user_id,))
                
            elif action == "unban":
                conn.execute("UPDATE users SET is_blacklisted = 0 WHERE user_id = ?", (user_id,))
                
            elif action == "update_note":
                conn.execute("UPDATE users SET note = ? WHERE user_id = ?", (note, user_id))
                
            conn.commit()
    except Exception as e:
        print(f"Error updating user {user_id}: {e}")
        
    return redirect(url_for("users"))


@app.route("/")
@app.route("/dashboard")
def index():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    # Fetch stats
    stats = {
        "total_users": 0,
        "new_users_today": 0,
        "total_emails": 0,
        "emails_today": 0,
        "vip_users": 0,
        "active_today": 0
    }
    
    with get_db() as conn:
        # User stats
        stats["total_users"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        stats["vip_users"] = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1").fetchone()[0]
        
        # Email stats
        stats["total_emails"] = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        
        # Today's stats
        today = datetime.now().strftime("%Y-%m-%d")
        stats["emails_today"] = conn.execute(
            "SELECT COUNT(*) FROM history WHERE date(sent_at) = ?", (today,)
        ).fetchone()[0]
        
        # Active users today (unique users who sent emails)
        stats["active_today"] = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM history WHERE date(sent_at) = ?", (today,)
        ).fetchone()[0]

    # Chart Data (Last 7 days)
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        chart_labels.append(date)
        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM history WHERE date(sent_at) = ?", (date,)
            ).fetchone()[0]
            chart_data.append(count)

    # Recent Logs
    recent_logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines[-50:]): # Scan last 50, keep up to 8
                if len(recent_logs) >= 8:
                    break
                stripped = line.strip()
                # Skip noisy HTTP/API request lines
                if not stripped or "HTTP Request:" in stripped or "getUpdates" in stripped:
                    continue
                parts = stripped.split(" ", 2)
                if len(parts) >= 3:
                    user_part = parts[1] if "user_id=" in parts[1] else "System"
                    action = parts[2]
                    # Truncate long action text
                    if len(action) > 80:
                        action = action[:77] + "..."
                    recent_logs.append({
                        "time": parts[0],
                        "user": user_part.replace("[user_id=", "").replace("]", ""),
                        "action": action
                    })

    return render_template(
        "dashboard.html", 
        active_page="dashboard",
        stats=stats,
        chart_labels=chart_labels,
        chart_data=chart_data,
        recent_logs=recent_logs
    )

@app.route("/logs")
def logs():
    if not session.get("admin"):
        return redirect(url_for("login"))
        
    logs_content = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Filter out noisy HTTP/API polling lines
            filtered = [l for l in lines if "getUpdates" not in l and "HTTP Request:" not in l]
            logs_content = "".join(filtered) if filtered else "No meaningful logs yet."
            
    return render_template("logs.html", active_page="logs", logs=logs_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
