import os
from pathlib import Path


RUNTIME_URL_FILE = Path(__file__).resolve().parents[1] / ".runtime" / "public_url"


def get_webapp_url():
    """Return the live tunnel URL, falling back to the configured static URL."""
    try:
        runtime_url = RUNTIME_URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        runtime_url = ""
    if runtime_url.startswith("https://"):
        return runtime_url
    configured_url = os.getenv("WEBAPP_URL", "").strip()
    return configured_url if configured_url.startswith("https://") else ""
