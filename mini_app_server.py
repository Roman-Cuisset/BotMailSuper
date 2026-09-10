"""Dedicated public-facing server for the Telegram Mini App."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from database.db import get_db, init_db
from mini_app import register_mini_app


load_dotenv("secrets.env")

app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=26 * 1024 * 1024,
    SECRET_KEY=os.getenv("WEB_SECRET_KEY") or os.getenv("SECRET_KEY"),
)
init_db()
register_mini_app(app)


@app.route("/logo")
def logo():
    return send_from_directory(".", "logotype.png")


@app.route("/health")
def health():
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify(status="ok")
    except Exception:
        return jsonify(status="unavailable"), 503


@app.after_request
def security_headers(response):
    allowed_origin = "https://roman-cuisset.github.io"
    if request.path.startswith("/api/miniapp/") and request.headers.get("Origin") == allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, ngrok-skip-browser-warning"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://telegram.org; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org"
    )
    return response
