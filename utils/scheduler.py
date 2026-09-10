"""Crash-safe scheduled delivery worker."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from database.db import get_db
from utils.email_sender import send_email_async, log_action

MAX_ATTEMPTS = 3
RETRY_MINUTES = (1, 5, 20)

def claim_due_email():
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""UPDATE scheduled_emails SET status='pending', processing_started_at=NULL
                        WHERE status='processing' AND processing_started_at < datetime('now', '-15 minutes')""")
        row = conn.execute("""SELECT id,user_id,recipient_email,subject,body,attachments,attempts
                              FROM scheduled_emails WHERE status='pending' AND send_at<=datetime('now')
                              AND (next_retry_at IS NULL OR next_retry_at<=datetime('now'))
                              ORDER BY send_at,id LIMIT 1""").fetchone()
        if not row:
            conn.commit(); return None
        changed = conn.execute("""UPDATE scheduled_emails SET status='processing',processing_started_at=datetime('now')
                                  WHERE id=? AND status='pending'""", (row['id'],)).rowcount
        conn.commit()
        return dict(row) if changed else None

def finish_job(job_id, success, attempts, error=""):
    attempts += 1
    with get_db() as conn:
        if success:
            conn.execute("""UPDATE scheduled_emails SET status='sent',sent_at=datetime('now'),attempts=?,
                            processing_started_at=NULL,last_error='' WHERE id=?""", (attempts,job_id))
            state = 'sent'
        elif attempts >= MAX_ATTEMPTS:
            conn.execute("""UPDATE scheduled_emails SET status='failed',attempts=?,processing_started_at=NULL,
                            last_error=? WHERE id=?""", (attempts,error[:500],job_id)); state='failed'
        else:
            retry_at = datetime.now(timezone.utc)+timedelta(minutes=RETRY_MINUTES[attempts-1])
            conn.execute("""UPDATE scheduled_emails SET status='pending',attempts=?,processing_started_at=NULL,
                            next_retry_at=?,last_error=? WHERE id=?""",
                         (attempts,retry_at.strftime('%Y-%m-%d %H:%M:%S'),error[:500],job_id)); state='retrying'
        conn.commit(); return state

async def scheduled_email_worker(bot=None):
    log_action("📅 Scheduler worker started")
    while True:
        try:
            job=claim_due_email()
            if not job:
                await asyncio.sleep(30); continue
            with get_db() as conn:
                user=conn.execute("SELECT username,is_vip FROM users WHERE user_id=?",(job['user_id'],)).fetchone()
            sender=SimpleNamespace(id=job['user_id'],username=user['username'] if user else None)
            success=await send_email_async(job['recipient_email'],job['subject'] or 'Message via BotMailSuper',
                job['body'],json.loads(job['attachments'] or '[]'),sender_user=sender,is_vip=bool(user and user['is_vip']))
            state=finish_job(job['id'],success,job['attempts'],'SMTP failure' if not success else '')
            log_action(f"Scheduled email #{job['id']}: {state}",job['user_id'])
            if bot and state in {'sent','failed'}:
                msg='✅ Votre e-mail programmé a été accepté par le serveur SMTP.' if state=='sent' else '❌ Votre e-mail programmé a échoué après plusieurs tentatives.'
                try: await bot.send_message(job['user_id'],msg)
                except Exception as exc: log_action(f"Scheduler notification failed: {exc}",job['user_id'])
        except Exception as exc:
            log_action(f"❌ Scheduler error: {exc}"); await asyncio.sleep(10)
