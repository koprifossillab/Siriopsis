import os
import tempfile
import time
from pathlib import Path

from django.test import override_settings
from django.urls import reverse

from .base import SafeTestCase


class HealthzTest(SafeTestCase):
    def test_ok(self):
        r = self.client.get(reverse("healthz"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r["Cache-Control"], "no-store")

    def test_stale_backup_is_degraded_not_503(self):
        # degraded 가 503 이면 배포의 기동 게이트가 막힌다 — 200 이어야 한다
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "Siriopsis_20260101.db"
            snap.touch()
            old = time.time() - 10 * 3600
            os.utime(snap, (old, old))
            with override_settings(BACKUP_DIR=Path(d), BACKUP_MAX_AGE_H=3):
                r = self.client.get(reverse("healthz"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "degraded")

    def test_missing_backup_is_degraded_when_gate_on(self):
        with tempfile.TemporaryDirectory() as d:
            with override_settings(BACKUP_DIR=Path(d), BACKUP_MAX_AGE_H=3):
                r = self.client.get(reverse("healthz"))
        self.assertEqual(r.json()["status"], "degraded")


class HomeTest(SafeTestCase):
    def test_home(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Siriopsis")
