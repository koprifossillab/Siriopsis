import json
import os
import tempfile
import time
from pathlib import Path

from django.test import override_settings
from django.urls import reverse

from specimens.models import Frame, Slab, Stack

from .base import SafeTestCase


def make_frame():
    slab = Slab.objects.create(slab_no="SP-2016-0052", year=2016)
    stack = Stack.objects.create(slab=slab, kind="ptm", preparation="none", view="whole",
                                 label="SP-2016-52A", source_dir="x", lp_file="x.lp")
    Frame.objects.create(stack=stack, seq=0, path="x/IMG_1.JPG")


class HealthzTest(SafeTestCase):
    def setUp(self):
        make_frame()

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


    def test_failure_flag_is_degraded(self):
        # 백업이 실패해 깃발을 세웠으면 사본이 새것이어도 degraded (ops/backup_db.py)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Siriopsis_20260101_000000.db").touch()
            (Path(d) / "BACKUP_FAIL.backup").write_text("integrity_check=bad", encoding="utf-8")
            with override_settings(BACKUP_DIR=Path(d), BACKUP_MAX_AGE_H=3):
                r = self.client.get(reverse("healthz"))
        self.assertEqual(r.json()["status"], "degraded")
        self.assertIn("integrity_check=bad", " ".join(r.json()["notes"]))

    def test_stale_offsite_is_degraded(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Siriopsis_20260101_000000.db").touch()
            (Path(d) / "offsite_status.json").write_text(json.dumps({"at": time.time() - 72 * 3600}))
            with override_settings(BACKUP_DIR=Path(d), BACKUP_MAX_AGE_H=3, OFFSITE_MAX_AGE_H=48):
                r = self.client.get(reverse("healthz"))
        self.assertEqual(r.json()["status"], "degraded")
        self.assertEqual(r.json()["backup"]["offsite_age_h"], 72.0)


class HealthzEmptyTest(SafeTestCase):
    def test_no_frames_is_degraded(self):
        # 마운트가 어긋나 빈 DB 가 새로 생겨도 "DB 가 열린다" 는 통과한다 — 행 수로 잡는다
        r = self.client.get(reverse("healthz"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "degraded")
        self.assertEqual(r.json()["frames"], 0)


class HomeTest(SafeTestCase):
    def test_home(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Siriopsis")


class SystemPageTest(SafeTestCase):
    def test_changelog_rows_newest_first_with_github_links(self):
        from core.views import changelog
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CHANGELOG.md"
            p.write_text("| 판 | 날짜 | 무엇 |\n|---|---|---|\n"
                         "| — | 2026-10-25 | 첫 ([wetherilli 001](devlog/a.md)) |\n"
                         "| v0.1.0 | 2026-10-26 | `/healthz` <b> |\n", encoding="utf-8")
            rows = changelog(p)
        self.assertEqual([r["ver"] for r in rows], ["v0.1.0", "—"])
        self.assertIn("https://github.com/koprifossillab/Siriopsis/blob/main/devlog/a.md", rows[1]["what"])
        self.assertIn("<code>/healthz</code> &lt;b&gt;", rows[0]["what"])     # 글자 속 태그는 글자로

    def test_page_and_splash(self):
        r = self.client.get(reverse("system"))
        self.assertContains(r, "극지연구소 고생물진화연구실")
        self.assertContains(r, "판 이력")
        self.assertEqual(self.client.get(reverse("splash_asset", args=["ondark.webp"]))["Content-Type"], "image/webp")
        self.assertEqual(self.client.get(reverse("splash_asset", args=["logo.json"])).status_code, 404)
