"""Telegram Mini App routes and signed initData authentication."""

from datetime import datetime, timezone
from functools import wraps
from hashlib import sha256
from types import SimpleNamespace
from urllib.parse import parse_qsl
import hmac
import json
import os
import socket
import time

from flask import jsonify, render_template, request
from werkzeug.utils import secure_filename

from config import MAX_ATTACHMENT_BYTES, MAX_TOTAL_ATTACHMENT_BYTES
from database.db import get_db
from handlers.user import is_valid_email
from utils.email_sender import send_email
from utils.delivery import DeliveryLimitError, mark_delivery, mark_sending, reserve_delivery


MAX_INIT_DATA_AGE = 24 * 60 * 60
MAX_RECIPIENTS = 10
VIP_MAX_RECIPIENTS = 50
MAX_ATTACHMENTS = 10


def validate_init_data(raw_init_data, bot_token=None, max_age=MAX_INIT_DATA_AGE):
    """Validate Telegram WebApp initData and return its user payload."""
    if not raw_init_data:
        raise ValueError("Missing Telegram authentication")
    values = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise ValueError("Missing authentication hash")

    token = bot_token or os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not configured")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", token.encode(), sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid Telegram authentication")

    try:
        auth_date = int(values["auth_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid authentication date") from exc
    now = int(time.time())
    if auth_date > now + 60 or now - auth_date > max_age:
        raise ValueError("Expired Telegram authentication")

    try:
        user = json.loads(values["user"])
        user["id"] = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid Telegram user") from exc
    return user


def _extract_init_data():
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("tma "):
        return authorization[4:]
    return request.headers.get("X-Telegram-Init-Data", "")


def telegram_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            telegram_user = validate_init_data(_extract_init_data())
        except (ValueError, RuntimeError) as exc:
            return jsonify(error=str(exc)), 401
        request.telegram_user = telegram_user
        return view(*args, **kwargs)

    return wrapped


def _ensure_user(telegram_user):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username, lang) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username = excluded.username""",
            (
                telegram_user["id"],
                telegram_user.get("username"),
                telegram_user.get("language_code") or "en",
            ),
        )
        conn.commit()


def _user_limits(user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT quota, is_vip, is_blacklisted FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        sent_today = conn.execute(
            """SELECT COUNT(*) FROM history
               WHERE user_id = ? AND status IN ('sent', 'accepted') AND date(sent_at) = date('now')""",
            (user_id,),
        ).fetchone()[0]
    result = dict(row) | {"sent_today": sent_today}
    # VIP is advertised by the bot as having no sending quota.
    if result["is_vip"]:
        result["quota"] = -1
    return result


def _domain_resolves(address):
    """Reject obviously impossible domains before SMTP accepts and later bounces them."""
    domain = address.rsplit("@", 1)[-1]
    try:
        socket.getaddrinfo(domain, 25, type=socket.SOCK_STREAM)
        return True
    except (socket.gaierror, UnicodeError):
        return False


def _serialize_rows(rows):
    return [dict(row) for row in rows]


def register_mini_app(app):
    @app.route("/miniapp")
    def miniapp_index():
        return render_template("miniapp.html")

    @app.route("/api/miniapp/bootstrap")
    @telegram_auth
    def miniapp_bootstrap():
        telegram_user = request.telegram_user
        _ensure_user(telegram_user)
        user_id = telegram_user["id"]
        with get_db() as conn:
            contacts = conn.execute(
                "SELECT id, name, email FROM contacts WHERE user_id = ? ORDER BY name COLLATE NOCASE",
                (user_id,),
            ).fetchall()
            drafts = conn.execute(
                """SELECT id, name, to_email, subject, body, created_at FROM drafts
                   WHERE user_id = ? ORDER BY created_at DESC""",
                (user_id,),
            ).fetchall()
            history = conn.execute(
                """SELECT id, to_email, subject, status, error, sent_at, body, attachments FROM history
                   WHERE user_id = ? ORDER BY id DESC LIMIT 50""",
                (user_id,),
            ).fetchall()
            accounts = conn.execute(
                """SELECT id, email_address, label, is_primary FROM user_emails
                   WHERE user_id = ? ORDER BY is_primary DESC, id""",
                (user_id,),
            ).fetchall()
            language_row = conn.execute(
                "SELECT lang FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        limits = _user_limits(user_id)
        return jsonify(
            user=telegram_user,
            contacts=_serialize_rows(contacts),
            drafts=_serialize_rows(drafts),
            history=_serialize_rows(history),
            accounts=_serialize_rows(accounts),
            quota={"limit": limits["quota"], "used": limits["sent_today"]},
            is_vip=bool(limits["is_vip"]),
            lang=language_row["lang"] if language_row else "en",
        )

    @app.route("/api/miniapp/language", methods=["PUT"])
    @telegram_auth
    def miniapp_language():
        user_id = request.telegram_user["id"]
        _ensure_user(request.telegram_user)
        lang = str((request.get_json(silent=True) or {}).get("lang", ""))
        if lang not in {"en", "fr", "ru"}:
            return jsonify(error="Unsupported language"), 400
        with get_db() as conn:
            conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
            conn.commit()
        return jsonify(lang=lang)

    @app.route("/api/miniapp/contacts", methods=["POST"])
    @telegram_auth
    def miniapp_save_contact():
        user_id = request.telegram_user["id"]
        _ensure_user(request.telegram_user)
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()[:80]
        email = str(payload.get("email", "")).strip().lower()
        if not name or not is_valid_email(email):
            return jsonify(error="Nom ou adresse e-mail invalide"), 400
        with get_db() as conn:
            conn.execute(
                """INSERT INTO contacts (user_id, name, email) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, name) DO UPDATE SET email = excluded.email""",
                (user_id, name, email),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, email FROM contacts WHERE user_id = ? AND name = ?",
                (user_id, name),
            ).fetchone()
        return jsonify(contact=dict(row)), 201

    @app.route("/api/miniapp/contacts/<int:contact_id>", methods=["DELETE"])
    @telegram_auth
    def miniapp_delete_contact(contact_id):
        user_id = request.telegram_user["id"]
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM contacts WHERE id = ? AND user_id = ?", (contact_id, user_id)
            )
            conn.commit()
        return (jsonify(ok=True), 200) if cursor.rowcount else (jsonify(error="Contact introuvable"), 404)

    @app.route("/api/miniapp/contacts/<int:contact_id>", methods=["PUT"])
    @telegram_auth
    def miniapp_update_contact(contact_id):
        user_id = request.telegram_user["id"]
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()[:80]
        email = str(payload.get("email", "")).strip().lower()
        if not name or not is_valid_email(email):
            return jsonify(error="Nom ou adresse e-mail invalide"), 400
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "UPDATE contacts SET name = ?, email = ? WHERE id = ? AND user_id = ?",
                    (name, email, contact_id, user_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id, name, email FROM contacts WHERE id = ? AND user_id = ?",
                    (contact_id, user_id),
                ).fetchone()
        except Exception as exc:
            if "UNIQUE constraint" in str(exc):
                return jsonify(error="Un contact porte déjà ce nom"), 409
            raise
        return jsonify(contact=dict(row)) if cursor.rowcount else (jsonify(error="Contact introuvable"), 404)

    @app.route("/api/miniapp/drafts", methods=["POST"])
    @telegram_auth
    def miniapp_save_draft():
        user_id = request.telegram_user["id"]
        _ensure_user(request.telegram_user)
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()[:80]
        recipient = str(payload.get("to_email", "")).strip()[:254]
        subject = str(payload.get("subject", "")).strip()[:200]
        body = str(payload.get("body", ""))[:50000]
        if not name:
            return jsonify(error="Le nom du brouillon est obligatoire"), 400
        if recipient and not is_valid_email(recipient):
            return jsonify(error="Adresse e-mail invalide"), 400
        with get_db() as conn:
            conn.execute(
                """INSERT INTO drafts (user_id, name, to_email, subject, body)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, name) DO UPDATE SET
                   to_email = excluded.to_email, subject = excluded.subject,
                   body = excluded.body, created_at = CURRENT_TIMESTAMP""",
                (user_id, name, recipient, subject, body),
            )
            conn.commit()
            row = conn.execute(
                """SELECT id, name, to_email, subject, body, created_at FROM drafts
                   WHERE user_id = ? AND name = ?""",
                (user_id, name),
            ).fetchone()
        return jsonify(draft=dict(row)), 201

    @app.route("/api/miniapp/drafts/<int:draft_id>", methods=["DELETE"])
    @telegram_auth
    def miniapp_delete_draft(draft_id):
        user_id = request.telegram_user["id"]
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM drafts WHERE id = ? AND user_id = ?", (draft_id, user_id)
            )
            conn.commit()
        return (jsonify(ok=True), 200) if cursor.rowcount else (jsonify(error="Brouillon introuvable"), 404)

    @app.route("/api/miniapp/account", methods=["DELETE"])
    @telegram_auth
    def miniapp_delete_account():
        user_id = request.telegram_user["id"]
        confirmation = (request.get_json(silent=True) or {}).get("confirmation")
        if confirmation != "DELETE":
            return jsonify(error="Confirmation DELETE requise"), 400
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM history WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM scheduled_emails WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()
        return jsonify(ok=True)

    @app.route("/api/miniapp/send", methods=["POST"])
    @telegram_auth
    def miniapp_send():
        telegram_user = request.telegram_user
        _ensure_user(telegram_user)
        user_id = telegram_user["id"]
        limits = _user_limits(user_id)
        if limits["is_blacklisted"]:
            return jsonify(error="Votre compte est bloqué"), 403

        recipients = [
            item.strip().lower()
            for item in request.form.get("recipients", "").replace(";", ",").split(",")
            if item.strip()
        ]
        recipient_limit = VIP_MAX_RECIPIENTS if limits["is_vip"] else MAX_RECIPIENTS
        if not recipients or len(recipients) > recipient_limit or any(not is_valid_email(item) for item in recipients):
            return jsonify(error=f"Indiquez entre 1 et {recipient_limit} adresses valides"), 400
        invalid_domains = [item for item in recipients if not _domain_resolves(item)]
        if invalid_domains:
            return jsonify(error=f"Domaine e-mail introuvable : {invalid_domains[0].rsplit('@', 1)[1]}"), 400
        if limits["quota"] >= 0 and limits["sent_today"] + len(recipients) > limits["quota"]:
            return jsonify(error="Quota quotidien insuffisant pour cet envoi"), 429

        subject = request.form.get("subject", "").strip()[:200] or "Message via BotMailSuper"
        body = request.form.get("body", "")[:50000]
        anonymous = bool(limits["is_vip"] and request.form.get("anonymous") == "true")
        # Browsers may submit an empty file part even when no file was chosen.
        files = [item for item in request.files.getlist("attachments") if item and item.filename]
        if len(files) > MAX_ATTACHMENTS:
            return jsonify(error=f"{MAX_ATTACHMENTS} pièces jointes maximum"), 400

        attachments = []
        total_size = 0
        for uploaded in files:
            content = uploaded.read(MAX_ATTACHMENT_BYTES + 1)
            if len(content) > MAX_ATTACHMENT_BYTES:
                return jsonify(error="Une pièce jointe dépasse 20 Mo"), 413
            total_size += len(content)
            if total_size > MAX_TOTAL_ATTACHMENT_BYTES:
                return jsonify(error="Les pièces jointes dépassent 25 Mo au total"), 413
            filename = secure_filename(uploaded.filename or "attachment") or "attachment"
            attachments.append((filename, content))

        sender = SimpleNamespace(id=user_id, username=telegram_user.get("username"))
        results = []
        base_request_key = request.headers.get("Idempotency-Key", "").strip()[:120]
        for position, recipient in enumerate(recipients):
            request_key = f"{base_request_key}:{position}" if base_request_key else None
            try:
                history_id, previous_status, duplicate = reserve_delivery(
                    user_id, recipient, subject, body, attachments, request_key
                )
            except DeliveryLimitError as exc:
                results.append({"email": recipient, "status": "rejected", "error": str(exc)})
                continue
            if duplicate:
                results.append({"email": recipient, "status": previous_status, "duplicate": True})
                continue
            if not mark_sending(history_id):
                results.append({"email": recipient, "status": "sending", "duplicate": True})
                continue
            success = send_email(
                recipient,
                subject,
                body,
                attachments,
                sender_user=sender,
                is_vip=bool(limits["is_vip"]),
                anonymous=anonymous,
            )
            status = "accepted" if success else "failed"
            mark_delivery(history_id, success, "Échec SMTP" if not success else "")
            results.append({"email": recipient, "status": status})
        if any(item["status"] == "rejected" for item in results):
            status_code = 429
        else:
            status_code = 200 if all(item["status"] in {"accepted", "sent"} or item.get("duplicate") for item in results) else 502
        return jsonify(results=results), status_code
