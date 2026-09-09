import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import database.db as database
from database.db import init_db
from mini_app import validate_init_data
from mini_app_server import app as mini_app
from web_admin import app as admin_app, login_attempts


def signed_init_data(token, user):
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "test-query",
        "user": json.dumps(user, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


class CoreFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = handle.name
        handle.close()
        database.DB_FILE = cls.db_path
        init_db()
        cls.client = mini_app.test_client()
        cls.token = os.environ["TELEGRAM_TOKEN"]
        cls.user = {"id": 99887766, "first_name": "Test", "username": "test_user", "language_code": "fr"}
        cls.init_data = signed_init_data(cls.token, cls.user)
        cls.headers = {"Authorization": f"tma {cls.init_data}"}

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.db_path)

    def test_signed_telegram_authentication(self):
        self.assertEqual(validate_init_data(self.init_data, self.token)["id"], self.user["id"])
        with self.assertRaises(ValueError):
            validate_init_data(self.init_data + "x", self.token)

    def test_mini_app_crud_and_delivery(self):
        response = self.client.get("/api/miniapp/bootstrap", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/miniapp/contacts",
            json={"name": "Alice", "email": "alice@example.com"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201)
        contact_id = response.get_json()["contact"]["id"]

        response = self.client.post(
            "/api/miniapp/drafts",
            json={"name": "Test", "to_email": "alice@example.com", "subject": "Bonjour", "body": "Message"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201)
        draft_id = response.get_json()["draft"]["id"]

        with patch("mini_app.send_email", return_value=True):
            response = self.client.post(
                "/api/miniapp/send",
                data={"recipients": "alice@example.com", "subject": "Bonjour", "body": "Message"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["results"][0]["status"], "sent")

        self.assertEqual(self.client.delete(f"/api/miniapp/contacts/{contact_id}", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/miniapp/drafts/{draft_id}", headers=self.headers).status_code, 200)

    def test_admin_login_rate_limit(self):
        login_attempts.clear()
        client = admin_app.test_client()
        response = client.get("/login")
        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as current_session:
            csrf = current_session["csrf_token"]
        for _ in range(5):
            client.post("/login", data={"password": "wrong-password", "csrf_token": csrf})
        response = client.post("/login", data={"password": "wrong-password", "csrf_token": csrf})
        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
