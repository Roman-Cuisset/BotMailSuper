"""Small privacy-oriented retention worker."""

import asyncio

from config import AUTO_CLEANUP_ENABLED, DAYS_TO_KEEP_HISTORY
from database.db import get_db
from utils.email_sender import log_action


def cleanup_old_history():
    if not AUTO_CLEANUP_ENABLED:
        return 0
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM history WHERE sent_at < datetime('now', ?)",
            (f"-{DAYS_TO_KEEP_HISTORY} days",),
        )
        conn.commit()
        return cursor.rowcount


async def retention_worker():
    while True:
        try:
            removed = cleanup_old_history()
            if removed:
                log_action(f"🧹 Removed {removed} expired history row(s)")
        except Exception as exc:
            log_action(f"❌ Retention cleanup error: {exc}")
        await asyncio.sleep(24 * 60 * 60)
