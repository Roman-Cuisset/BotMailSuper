import os


def get_webapp_url():
    """Return the configured permanent Mini App URL."""
    configured_url = os.getenv("WEBAPP_URL", "").strip()
    return configured_url if configured_url.startswith("https://") else ""
