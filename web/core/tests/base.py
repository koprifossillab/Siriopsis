"""모든 시험이 딛는 바닥. ForGIA `tests/base.py` 에서 왔다.
**운영 자료에 닿지 않는다는 것을 여기서 확인한다** (.guides/workflow.md §7).

사람이 "시험 DB 는 사본이다" 를 기억하는 대신 베이스 클래스가 확인한다.
파일 자리(DATA_ROOT 등)를 쓰는 시험이 생기면, 뿌리를 임시 디렉터리로 **먼저** 갈고
`super().setUpClass()` 를 부른다 — 순서가 거꾸로면 픽스처가 진짜 뿌리에 쓴다(DiaRUGA P08).
"""
from pathlib import Path

from django.db import connection
from django.test import TestCase


def assert_test_db():
    """지금 열린 DB 가 운영 DB 가 아님을 확인한다. 아니면 무엇이든 돌리기 전에 멈춘다."""
    name = str(connection.settings_dict.get("NAME") or "")
    ok = (name == ":memory:"
          or name.startswith("file:memorydb")
          or "test" in Path(name).name.lower())
    if not ok:
        raise AssertionError(
            f"시험이 운영 DB 를 열었다: {name}\n"
            f"`manage.py test` 로 돌렸는지, DATABASES 를 누가 덮어쓰지 않았는지 볼 것.")


class SafeTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        assert_test_db()
