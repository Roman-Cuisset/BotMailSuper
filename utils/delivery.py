"""Atomic delivery reservations shared by the bot and Mini App."""

from datetime import datetime, timezone
import json
import sqlite3
import uuid

from database.db import get_db
from config import STORE_HISTORY_CONTENT


COUNTED_STATUSES = ("queued", "sending", "accepted", "sent")


class DeliveryLimitError(Exception):
    pass


def reserve_delivery(user_id, recipient, subject, body="", attachments=None, request_key=None):
    """Reserve one quota unit and create an idempotent history row atomically."""
    request_key = request_key or uuid.uuid4().hex
    attachment_names = [item[0] if isinstance(item, (list, tuple)) else str(item) for item in (attachments or [])]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id, status FROM history WHERE user_id = ? AND request_key = ?",
            (user_id, request_key),
        ).fetchone()
        if existing:
            conn.commit()
            return existing["id"], existing["status"], True
        user = conn.execute(
            "SELECT quota, is_vip, is_blacklisted FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not user:
            conn.rollback()
            raise DeliveryLimitError("Utilisateur introuvable")
        if user["is_blacklisted"]:
            conn.rollback()
            raise DeliveryLimitError("Votre compte est bloqué")
        used = conn.execute(
            "SELECT COUNT(*) FROM history WHERE user_id = ? AND status IN (?,?,?,?) "
            "AND date(sent_at) = date('now')",
            (user_id, *COUNTED_STATUSES),
        ).fetchone()[0]
        if not user["is_vip"] and user["quota"] >= 0 and used >= user["quota"]:
            conn.rollback()
            raise DeliveryLimitError(f"Quota quotidien atteint ({user['quota']} e-mails)")
        try:
            cursor = conn.execute(
                """INSERT INTO history
                   (user_id, to_email, subject, status, error, sent_at, details, body,
                    attachments, request_key, attempts, updated_at)
                   VALUES (?, ?, ?, 'queued', '', ?, 'Reserved for delivery', ?, ?, ?, 0, ?)""",
                (user_id, recipient, subject, now, body if STORE_HISTORY_CONTENT else "",
                 json.dumps(attachment_names, ensure_ascii=False) if STORE_HISTORY_CONTENT else "[]", request_key, now),
            )
            conn.commit()
            return cursor.lastrowid, "queued", False
        except sqlite3.IntegrityError:
            conn.rollback()
            existing = conn.execute(
                "SELECT id, status FROM history WHERE user_id = ? AND request_key = ?",
                (user_id, request_key),
            ).fetchone()
            return existing["id"], existing["status"], True


def mark_delivery(history_id, success, error=""):
    status = "accepted" if success else "failed"
    with get_db() as conn:
        conn.execute(
            """UPDATE history SET status = ?, error = ?, details = ?,
               attempts = attempts + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (status, error[:500], "Accepted by SMTP" if success else "SMTP failure", history_id),
        )
        conn.commit()


def mark_sending(history_id):
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE history SET status='sending', updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status='queued'", (history_id,)
        )
        conn.commit()
        return cursor.rowcount == 1
