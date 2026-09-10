# BotMailSuper

BotMailSuper quickly turns Telegram text, photos, documents, or albums into emails. The project includes the bot, an administration panel, and a Telegram Mini App.

## Main features

- SMTP sending with confirmation of the actual delivery result
- Editable subject, preview, and retry button
- Searchable, paginated contacts, groups, templates, and drafts
- Scheduled sending, quotas, VIP features, blacklist, and statistics
- Mini App: composer, contacts, drafts, history, and SMTP account
- French, English, and Russian

The former Gmail API integration has been removed. The service uses SMTP only.

## Installation

1. Install Python 3.10 or later and PM2.
2. Create the virtual environment: `python3 -m venv .venv`.
3. Install the dependencies: `.venv/bin/pip install -r requirements.txt`.
4. Copy `secrets.env.example` to `secrets.env`, then fill in the required values.
5. Configure DuckDNS and the Caddy proxy provided in `deploy/`.
6. Start the services: `./start.sh`.

PM2 starts four processes:

- `bot-telegram`: Telegram bot and workers;
- `bot-web`: administration on port 5000;
- `bot-miniapp`: local Mini App on port 5010;
- `bot-public-tunnel`: fixed HTTPS ngrok domain and Telegram button synchronization.

The Mini App uses the public HTTPS address defined in `WEBAPP_URL`. In the current deployment, Caddy publishes it under `/botmailsuper/` and automatically renews the TLS certificate.

In local production, the `bot-public-tunnel` process maintains the free ngrok development domain, writes the active URL to `.runtime/public_url`, and updates the Telegram button. No purchased domain or open router port is required, and the ngrok domain remains unchanged after a restart.

## Administration

Open `/login` on port 5000. On the first startup, `ADMIN_PASSWORD` is automatically converted into a persistent hash in SQLite. Changes made in **Settings** are persistent. Connections are protected by CSRF, hardened cookies, session expiration, and login-attempt rate limiting.

## Tests

```bash
.venv/bin/python -m unittest -v test_core.py
.venv/bin/python verify_refactor.py
.venv/bin/python test_improvements.py
.venv/bin/python test_email_rendering.py
.venv/bin/python test_i18n.py
```

## Data and security

Never publish `secrets.env`, the SQLite database, logs, sessions, or tokens. Attachments remain in memory while being sent and are not stored on disk. Logs rotate automatically and mask recipient addresses. History older than 30 days is deleted daily when `AUTO_CLEANUP_ENABLED` is enabled.
