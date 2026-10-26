"""phyloserver 의 EPMA 세션·맵·채널을 테이블에 맞춘다 (`specimens/epma.py`, wetherilli 018).

    python web/manage.py import_epma                     # phyloserver `epma.json`
    python web/manage.py import_epma --dump <폴더>        # 내보낸 `models/SpEpma*.json` (epma.json 이 서기 전·시험)
    docker compose run --rm -T manage import_epma

몇 번을 돌려도 같다. 받은 것에 없는 행은 지운다(phyloserver 에서 지운 것). 받은 것이 비었거나 못 받으면 아무것도 고치지 않는다.
파일(`EPMA_ROOT`)은 읽지 않는다 — 화면이 열 때 읽는다.
"""
from django.core.management.base import BaseCommand, CommandError

from specimens import epma


class Command(BaseCommand):
    help = "phyloserver 의 EPMA 메타(epma.json 또는 내보낸 SpEpma*.json)를 테이블에 맞춘다"

    def add_arguments(self, parser):
        parser.add_argument("--dump", help="phyloserver 내보내기 폴더(models/SpEpma*.json)")
        parser.add_argument("--base", help="phyloserver siriuspasset 뿌리 (기본 SIRIOPSIS_CATALOG_URL)")

    def handle(self, *args, dump=None, base=None, **opts):
        try:
            data = epma.load_dump(dump) if dump else epma.fetch(base)
        except (OSError, ValueError) as e:
            raise CommandError(f"못 읽었다 — 고치지 않는다: {e}")
        st = epma.sync(data)
        for line in st.no_slab[:20]:
            self.stdout.write(f"슬랩 없음: {line}")
        for line in st.errors[:20]:
            self.stderr.write(line)
        self.stdout.write(self.style.SUCCESS(str(st)))
        if st.errors and not st.sessions:
            raise CommandError("반입하지 않았다")
