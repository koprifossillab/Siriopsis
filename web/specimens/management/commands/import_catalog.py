"""phyloserver siriuspasset 목록에서 지금 테이블에 있는 슬랩·표본의 분류 정보를 채운다 (`specimens/catalog.py`).

    python web/manage.py import_catalog
    python web/manage.py import_catalog --slab SP-2016-0052
"""
from django.core.management.base import BaseCommand

from specimens import bare, epma
from specimens.catalog import sync
from specimens.models import Slab


class Command(BaseCommand):
    help = "phyloserver 목록에서 분류군·문·층준·비고를 읽어 온다 (읽기만)"

    def add_arguments(self, parser):
        parser.add_argument("--slab", action="append", help="이 슬랩만 (여러 번 줄 수 있다)")

    def handle(self, *args, slab=None, **opts):
        slabs = Slab.objects.filter(slab_no__in=slab) if slab else None
        found, missing, filled, errors = sync(slabs, log=self.stdout.write)
        for e in errors:
            self.stderr.write(f"못 읽음: {e}")
        self.stdout.write(self.style.SUCCESS(
            f"슬랩 찾음 {found} · 목록에 없음 {missing} · 표본 채움 {filled} · 못 읽음 {len(errors)}"))
        self.stdout.write(bare.summary())
        # EPMA 세션은 phyloserver 슬랩 id 로 붙는다 — 새로 찾은 슬랩·표본에 다시 잇는다 (018)
        n = epma.relink()
        if n:
            self.stdout.write(f"EPMA 세션 다시 이음 {n}")
