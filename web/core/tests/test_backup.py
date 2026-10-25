"""`ops/backup_db.py` — 검증된 사본만 채택하고, 실패하면 정리하지 않고 깃발을 세운다 (wetherilli 008).

스크립트는 Django 를 부르지 않아 파일로 불러온다. 시험은 임시 디렉터리에 저만의 SQLite 를 만든다 — 운영·개발 DB 를 열지 않는다.
"""
import importlib.util
import os
import sqlite3
import tempfile
import time
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from .base import SafeTestCase

_spec = importlib.util.spec_from_file_location(
    "backup_db", Path(__file__).resolve().parents[3] / "ops" / "backup_db.py")
backup_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup_db)


def run(*argv):
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return backup_db.main(list(argv))


class BackupTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        self.db, self.out, self.nas = d / "live.db", d / "backup", d / "nas"
        con = sqlite3.connect(self.db)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("create table specimens_stack (id integer primary key)")
        con.execute("insert into specimens_stack values (1)")
        con.commit()
        self.live = con           # 열어 둔 채로 — 살아 있는 WAL DB 에서 뜬다

    def tearDown(self):
        self.live.close()
        self._tmp.cleanup()

    def snaps(self, d=None):
        return sorted((d or self.out).glob("Siriopsis_*.db"))

    def test_snapshot_is_single_verified_file(self):
        self.assertEqual(run("--db", str(self.db), "--out", str(self.out)), 0)
        (snap,) = self.snaps()
        con = sqlite3.connect(snap)
        self.assertEqual(con.execute("pragma journal_mode").fetchone()[0], "delete")
        self.assertEqual(con.execute("select count(*) from specimens_stack").fetchone()[0], 1)
        con.close()
        self.assertEqual([p.name for p in self.out.iterdir() if not p.name.endswith(".db")], [])

    def test_rotation_keeps_manual(self):
        run("--db", str(self.db), "--out", str(self.out), "--note", "before-merge")
        for i in range(3):
            (self.out / f"Siriopsis_2026010{i}_000000.db").touch()
        run("--db", str(self.db), "--out", str(self.out), "--keep", "2")
        self.assertEqual(len(self.snaps()), 2)
        self.assertEqual(len(self.snaps(self.out / "manual")), 1)     # 손으로 뜬 것은 순환이 안 건드린다

    def test_failure_raises_flag_and_skips_rotation(self):
        for i in range(3):
            self.out.mkdir(exist_ok=True)
            (self.out / f"Siriopsis_2026010{i}_000000.db").touch()
        broken = self.db.with_name("broken.db")
        broken.write_bytes(b"not a database" * 100)
        self.assertEqual(run("--db", str(broken), "--out", str(self.out), "--keep", "1"), 1)
        self.assertEqual(len(self.snaps()), 3)                          # 지난 사본을 밀어내지 않는다
        self.assertTrue((self.out / "BACKUP_FAIL.backup").exists())
        self.assertTrue(list(self.out.glob("*.corrupt")))

    def test_success_clears_only_own_flag(self):
        self.out.mkdir()
        (self.out / "BACKUP_FAIL.backup").write_text("x")
        (self.out / "BACKUP_FAIL.offsite").write_text("x")
        run("--db", str(self.db), "--out", str(self.out))
        self.assertEqual([p.name for p in self.out.glob("BACKUP_FAIL.*")], ["BACKUP_FAIL.offsite"])

    def test_offsite_sends_newest_and_does_not_overwrite_same_day(self):
        run("--db", str(self.db), "--out", str(self.out))
        self.assertEqual(run("--out", str(self.out), "--offsite", str(self.nas)), 0)
        self.assertEqual(run("--out", str(self.out), "--offsite", str(self.nas)), 0)
        self.assertEqual(len(list(self.nas.glob("Siriopsis_*.db"))), 2)  # .2 로 잇는다
        self.assertTrue((self.out / "offsite_status.json").exists())

    def test_offsite_refuses_stale_snapshot(self):
        run("--db", str(self.db), "--out", str(self.out))
        (snap,) = self.snaps()
        old = time.time() - 5 * 3600
        os.utime(snap, (old, old))
        self.assertEqual(run("--out", str(self.out), "--offsite", str(self.nas)), 1)
        self.assertFalse(list(self.nas.glob("Siriopsis_*.db")) if self.nas.exists() else [])
        self.assertTrue((self.out / "BACKUP_FAIL.offsite").exists())

    def test_bad_integrity_is_not_adopted(self):
        # 뜨기는 됐는데 검사가 ok 가 아닌 사본 — 실제로 만들기 어려워 검사를 갈아 끼운다
        real = backup_db.check
        backup_db.check = lambda path: ("*** page 3 corrupt", {})
        try:
            self.assertEqual(run("--db", str(self.db), "--out", str(self.out)), 1)
        finally:
            backup_db.check = real
        self.assertEqual(self.snaps(), [])
        self.assertTrue(list(self.out.glob("*.corrupt")))
        self.assertTrue((self.out / "BACKUP_FAIL.backup").exists())
