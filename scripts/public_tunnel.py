#!/usr/bin/env python3
"""Keep a free Cloudflare Quick Tunnel alive and update Telegram automatically."""

import json
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit
from pathlib import Path

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
CLOUDFLARED = ROOT / ".tools" / "cloudflared"
SECRETS = ROOT / "secrets.env"
RUNTIME_DIR = ROOT / ".runtime"
RUNTIME_URL = RUNTIME_DIR / "public_url"
TUNNEL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
child = None


def atomic_write(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    if mode is not None:
        temporary.chmod(mode)
    temporary.replace(path)


def update_secrets(webapp_url):
    lines = SECRETS.read_text(encoding="utf-8").splitlines()
    replacement = f"WEBAPP_URL={webapp_url}"
    updated = []
    found = False
    for line in lines:
        if line.startswith("WEBAPP_URL="):
            updated.append(replacement)
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(replacement)
    atomic_write(SECRETS, "\n".join(updated) + "\n", 0o600)


def public_healthcheck(url):
    last_error = None
    hostname = urlsplit(url).hostname
    for _ in range(90):
        try:
            dns = subprocess.run(
                ["dig", "+short", "@1.1.1.1", hostname, "A"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            addresses = [line.strip() for line in dns.stdout.splitlines() if line.strip()]
            for address in addresses:
                check = subprocess.run(
                    [
                        "curl", "--silent", "--show-error", "--max-time", "10",
                        "--resolve", f"{hostname}:443:{address}",
                        "--output", "/dev/null", "--write-out", "%{http_code}",
                        f"{url}/health",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if check.returncode == 0 and check.stdout == "200":
                    return True
            last_error = check.stderr if addresses else "DNS public pas encore propagé"
        except (OSError, subprocess.SubprocessError) as error:
            last_error = error
        time.sleep(1)
    if last_error:
        print(f"Dernière erreur du contrôle public : {last_error}", file=sys.stderr, flush=True)
    return False


def update_telegram(webapp_url):
    token = dotenv_values(SECRETS).get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN absent de secrets.env")
    payload = json.dumps({
        "menu_button": {
            "type": "web_app",
            "text": "Ouvrir BotMailSuper",
            "web_app": {"url": webapp_url},
        }
    }).encode("utf-8")
    last_error = None
    for _ in range(12):
        try:
            set_request = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/setChatMenuButton",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(set_request, timeout=20) as response:
                result = json.load(response)
            if not result.get("ok"):
                last_error = "Telegram a refusé la mise à jour du bouton"
            else:
                get_url = f"https://api.telegram.org/bot{token}/getChatMenuButton"
                with urllib.request.urlopen(get_url, timeout=20) as response:
                    current = json.load(response).get("result", {})
                if current.get("web_app", {}).get("url") == webapp_url:
                    return
                last_error = "le bouton Telegram n'est pas encore synchronisé"
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(5)
    raise RuntimeError(f"mise à jour Telegram impossible : {last_error}")


def publish_url(url):
    print(f"Tunnel Cloudflare obtenu, validation en cours : {url}", flush=True)
    if not public_healthcheck(url):
        raise RuntimeError("le tunnel Cloudflare ne répond pas au contrôle public")
    public_frontend = dotenv_values(SECRETS).get("PUBLIC_WEBAPP_URL", "").strip().rstrip("/")
    if public_frontend.startswith("https://"):
        webapp_url = f"{public_frontend}/?api={quote(url, safe='')}"
    else:
        webapp_url = f"{url}/miniapp"
    update_secrets(webapp_url)
    update_telegram(webapp_url)
    # The runtime URL is the readiness marker: publish it only after Telegram agrees.
    atomic_write(RUNTIME_URL, webapp_url + "\n", 0o600)
    print(f"Mini App publique prête : {webapp_url}", flush=True)


def stop_child(signum, _frame):
    if child and child.poll() is None:
        child.send_signal(signum)


def run():
    global child
    if not CLOUDFLARED.is_file():
        raise RuntimeError(f"cloudflared introuvable : {CLOUDFLARED}")
    child = subprocess.Popen(
        [
            str(CLOUDFLARED),
            "tunnel",
            "--no-autoupdate",
            "--protocol",
            "http2",
            "--url",
            "http://127.0.0.1:5010",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    published = None
    for line in child.stdout:
        match = TUNNEL_PATTERN.search(line)
        if match and match.group(0) != published:
            published = match.group(0)
            try:
                publish_url(published)
            except Exception as error:
                print(f"Mise à jour du tunnel impossible : {error}", file=sys.stderr, flush=True)
        elif " ERR " in line or " WRN " in line:
            print(line.rstrip(), flush=True)
    return child.wait()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    raise SystemExit(run())
