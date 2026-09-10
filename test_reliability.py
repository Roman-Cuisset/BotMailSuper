import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

import database.db as database
from utils.delivery import DeliveryLimitError, reserve_delivery
from utils.html_sanitizer import sanitize_email_html
from utils.scheduler import claim_due_email, finish_job


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_FILE
        database.DB_FILE = os.path.join(self.temp.name, "test.db")
        database.init_db()

    def tearDown(self):
        database.DB_FILE = self.old_db
        self.temp.cleanup()

    def test_quota_reservation_is_atomic(self):
        with database.get_db() as conn:
            conn.execute("INSERT INTO users(user_id,quota) VALUES(1,1)")
            conn.commit()
        barrier = threading.Barrier(2)
        def attempt(key):
            barrier.wait()
            try:
                reserve_delivery(1, f"{key}@example.com", "subject", request_key=key)
                return True
            except DeliveryLimitError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("one", "two")))
        self.assertEqual(sum(results), 1)

    def test_idempotency_key_does_not_duplicate(self):
        with database.get_db() as conn:
            conn.execute("INSERT INTO users(user_id,quota) VALUES(1,5)")
            conn.commit()
        first = reserve_delivery(1, "a@example.com", "subject", request_key="same")
        second = reserve_delivery(1, "a@example.com", "subject", request_key="same")
        self.assertEqual(first[0], second[0])
        self.assertTrue(second[2])

    def test_scheduler_claims_job_only_once_and_retries(self):
        with database.get_db() as conn:
            conn.execute("INSERT INTO users(user_id,is_vip) VALUES(1,1)")
            conn.execute("""INSERT INTO scheduled_emails(user_id,recipient_email,body,send_at)
                            VALUES(1,'a@example.com','hello',datetime('now','-1 minute'))""")
            conn.commit()
        job = claim_due_email()
        self.assertIsNotNone(job)
        self.assertIsNone(claim_due_email())
        self.assertEqual(finish_job(job["id"], False, 0, "temporary"), "retrying")

    def test_html_sanitizer_blocks_active_content(self):
        clean = sanitize_email_html('<p onclick="x()">ok<script>alert(1)</script><a href="javascript:x">bad</a></p>')
        self.assertEqual(clean, "<p>ok<a>bad</a></p>")


if __name__ == "__main__":
    unittest.main()
