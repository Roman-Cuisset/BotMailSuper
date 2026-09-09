import asyncio
from datetime import datetime
import json
from database.db import get_db
from utils.email_sender import send_email_task, log_action

async def scheduled_email_worker():
    """Background worker to send scheduled emails"""
    print("📅 Scheduler worker started")
    log_action("📅 Scheduler worker started")
    while True:
        try:
            with get_db() as conn:
                # Find emails ready to send
                pending = conn.execute("""
                    SELECT id, user_id, recipient_email, subject, body, attachments
                    FROM scheduled_emails
                    WHERE status = 'pending' AND send_at <= datetime('now')
                """).fetchall()
                
                for email in pending:
                    # Send email
                    attachments = json.loads(email['attachments']) if email['attachments'] else []
                    
                    # Get user info for sender name
                    user = conn.execute("SELECT username, is_vip FROM users WHERE user_id = ?", (email['user_id'],)).fetchone()
                    sender_name = user['username'] if user and user['username'] else f"User {email['user_id']}"
                    is_vip = user['is_vip'] if user else False
                    
                    success = await send_email_task(
                        recipient=email['recipient_email'],
                        subject=email['subject'],
                        message_text=email['body'],
                        attachments=attachments,
                        expediteur=sender_name,
                        is_vip=is_vip
                    )
                    
                    # Only mark a job as sent after the provider confirmed it.
                    conn.execute("""
                        UPDATE scheduled_emails
                        SET status = ?, sent_at = CASE WHEN ? = 'sent' THEN datetime('now') ELSE NULL END
                        WHERE id = ?
                    """, ('sent' if success else 'failed', 'sent' if success else 'failed', email['id']))
                    conn.commit()

                    if success:
                        print(f"✅ Sent scheduled email #{email['id']}")
                        log_action(f"✅ Sent scheduled email #{email['id']} to {email['recipient_email']}")
                    else:
                        print(f"❌ Failed scheduled email #{email['id']}")
                        log_action(f"❌ Failed scheduled email #{email['id']} to {email['recipient_email']}")
        
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            log_action(f"❌ Scheduler error: {e}")
        
        # Check every minute
        await asyncio.sleep(60)
