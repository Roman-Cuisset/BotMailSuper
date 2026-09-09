"""
Weekly Report Generator
Generates usage statistics and sends email reports
"""
import sys
import os
import logging
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from database.db import get_db
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv("secrets.env")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", EMAIL_SENDER)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_weekly_stats():
    """Get statistics for the past week"""
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    with get_db() as conn:
        # Total emails sent this week
        total_emails = conn.execute("""
            SELECT COUNT(*) FROM history 
            WHERE sent_at >= ?
        """, (week_ago,)).fetchone()[0]
        
        # Active users (sent at least one email)
        active_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) FROM history 
            WHERE sent_at >= ?
        """, (week_ago,)).fetchone()[0]
        
        # VIP activity
        vip_emails = conn.execute("""
            SELECT COUNT(*) FROM history h
            JOIN users u ON h.user_id = u.user_id
            WHERE h.sent_at >= ? AND u.is_vip = 1
        """, (week_ago,)).fetchone()[0]
        
        # Top recipients
        top_recipients = conn.execute("""
            SELECT to_email, COUNT(*) as count
            FROM history
            WHERE sent_at >= ?
            GROUP BY to_email
            ORDER BY count DESC
            LIMIT 5
        """, (week_ago,)).fetchall()
        
        # Total users
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        vip_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1").fetchone()[0]
        
    return {
        'total_emails': total_emails,
        'active_users': active_users,
        'vip_emails': vip_emails,
        'top_recipients': top_recipients,
        'total_users': total_users,
        'vip_users': vip_users,
        'week_start': week_ago,
        'week_end': datetime.now().strftime('%Y-%m-%d')
    }

def generate_report_html(stats):
    """Generate HTML email report"""
    recipients_html = ""
    for recipient, count in stats['top_recipients']:
        recipients_html += f"<li>{recipient}: <b>{count}</b> emails</li>\n"
    
    if not recipients_html:
        recipients_html = "<li>Aucun destinataire cette semaine</li>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #0d6efd; border-bottom: 3px solid #0d6efd; padding-bottom: 10px; }}
            .stat-card {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #0d6efd; }}
            .stat-card h3 {{ margin: 0 0 10px 0; color: #333; }}
            .stat-card .number {{ font-size: 32px; font-weight: bold; color: #0d6efd; }}
            ul {{ background: #f8f9fa; padding: 15px 30px; border-radius: 5px; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Rapport Hebdomadaire - Bot Mail Super</h1>
            <p>Période: <b>{stats['week_start']}</b> au <b>{stats['week_end']}</b></p>
            
            <div class="stat-card">
                <h3>📧 Emails Envoyés</h3>
                <div class="number">{stats['total_emails']}</div>
            </div>
            
            <div class="stat-card">
                <h3>👥 Utilisateurs Actifs</h3>
                <div class="number">{stats['active_users']}</div>
                <p style="margin: 5px 0 0 0; color: #666;">Sur {stats['total_users']} utilisateurs totaux</p>
            </div>
            
            <div class="stat-card">
                <h3>⭐ Activité VIP</h3>
                <div class="number">{stats['vip_emails']}</div>
                <p style="margin: 5px 0 0 0; color: #666;">{stats['vip_users']} utilisateurs VIP</p>
            </div>
            
            <h3 style="margin-top: 30px;">🎯 Top 5 Destinataires</h3>
            <ul>
                {recipients_html}
            </ul>
            
            <div class="footer">
                Bot Mail Super - Rapport généré automatiquement<br>
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_weekly_report():
    """Generate and send weekly report"""
    try:
        stats = get_weekly_stats()
        html = generate_report_html(stats)
        subject = f"📊 Rapport Hebdomadaire - {stats['week_start']} au {stats['week_end']}"
        text_body = "Rapport hebdomadaire du Bot Mail Super"
        
        logger.info(f"📧 Sending weekly report via SMTP to {ADMIN_EMAIL}...")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ADMIN_EMAIL
        
        msg.set_content(text_body)
        msg.add_alternative(html, subtype='html')
        
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        print(f"✅ Weekly report sent via SMTP to {ADMIN_EMAIL}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending weekly report: {e}")
        return False

if __name__ == "__main__":
    # Test report generation
    print("Generating test report...")
    send_weekly_report()
