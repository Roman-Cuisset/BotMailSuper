from flask import Flask, jsonify, render_template, request, redirect, url_for, session, send_from_directory, make_response
from datetime import datetime, timedelta
from collections import defaultdict, deque
import csv
import requests
import sys
import os
import json
import hmac
import secrets
from time import monotonic
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

# Add parent directory to path for database import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import get_db, init_db

load_dotenv("secrets.env")

app = Flask(__name__)
app.secret_key = os.getenv("WEB_SECRET_KEY") or os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("WEB_SECRET_KEY or SECRET_KEY must be configured")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
)

init_db()

LOG_FILE = "bot_log.txt"
SESSION_TIMEOUT = 600  # 10 minutes

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
login_attempts = defaultdict(deque)


def _get_admin_password_hash():
    """Return the persisted hash, migrating the legacy environment password once."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'admin_password_hash'"
        ).fetchone()
        if row and row["value"]:
            return row["value"]

        configured_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
        legacy_password = os.getenv("ADMIN_PASSWORD", "")
        if configured_hash:
            password_hash = configured_hash
        elif legacy_password:
            password_hash = generate_password_hash(legacy_password)
        else:
            raise RuntimeError("ADMIN_PASSWORD_HASH or ADMIN_PASSWORD must be configured")

        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)",
            (password_hash,),
        )
        conn.commit()
        return password_hash


def _password_matches(password):
    return bool(password) and check_password_hash(_get_admin_password_hash(), password)


def _login_key():
    return request.remote_addr or "unknown"


def _is_login_limited(key):
    now = monotonic()
    attempts = login_attempts[key]
    while attempts and now - attempts[0] >= LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def tail_lines(path, max_lines=2000, max_bytes=1024 * 1024):
    """Read only the end of a log file instead of loading it all into RAM."""
    if not os.path.exists(path):
        return []
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes))
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if size > max_bytes and lines:
        lines = lines[1:]
    return lines[-max_lines:]

# Database access functions handled by database/db.py

@app.before_request
def session_timeout():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    if request.method == "POST" and not request.path.startswith("/api/miniapp/") and not hmac.compare_digest(
        request.form.get("csrf_token", ""), session["csrf_token"]
    ):
        return "Invalid CSRF token", 400
    if "admin" in session:
        now = datetime.now().timestamp()
        last = session.get("last_active", now)
        if now - last > SESSION_TIMEOUT:
            session.pop("admin", None)
        else:
            session["last_active"] = now


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        key = _login_key()
        if _is_login_limited(key):
            response = make_response(
                render_template("login.html", error="Too many attempts. Try again in 15 minutes."),
                429,
            )
            response.headers["Retry-After"] = str(LOGIN_WINDOW_SECONDS)
            return response
        supplied_password = request.form.get("password", "")
        if _password_matches(supplied_password):
            login_attempts.pop(key, None)
            csrf_token = session.get("csrf_token")
            session.clear()
            session["csrf_token"] = csrf_token or secrets.token_urlsafe(32)
            session["admin"] = True
            session["last_active"] = datetime.now().timestamp()
            return redirect(url_for("index"))
        else:
            login_attempts[key].append(monotonic())
            return render_template("login.html", error="Wrong password")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/logo")
def logo():
    return send_from_directory('.', 'logotype.png')


@app.route("/health")
def health():
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify(status="ok")
    except Exception:
        return jsonify(status="unavailable"), 503

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
    if not session.get("admin"):
        return redirect(url_for("login"))
    return redirect(url_for("settings"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    password_msg = ""
    password_success = False
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old = request.form.get("old_password")
            new = request.form.get("new_password")
            if _password_matches(old) and new and len(new) >= 12:
                with get_db() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)",
                        (generate_password_hash(new),),
                    )
                    conn.commit()
                password_msg = "Password changed successfully."
                password_success = True
            else:
                password_msg = "Incorrect current password, or new password shorter than 12 characters."
    
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
        for line in reversed(tail_lines(LOG_FILE, max_lines=200, max_bytes=256 * 1024)):
            if len(recent_logs) >= 8:
                break
            stripped = line.strip()
            # Skip noisy HTTP/API polling lines
            if not stripped or "HTTP Request:" in stripped or "getUpdates" in stripped:
                continue
            parts = stripped.split(" ", 2)
            if len(parts) >= 3:
                user_part = parts[1] if "user_id=" in parts[1] else "System"
                action = parts[2]
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
        lines = tail_lines(LOG_FILE)
        # Filter out noisy HTTP/API polling lines
        filtered = [l for l in lines if "getUpdates" not in l and "HTTP Request:" not in l]
        logs_content = "".join(filtered) if filtered else "No meaningful logs yet."
            
    return render_template("logs.html", active_page="logs", logs=logs_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
