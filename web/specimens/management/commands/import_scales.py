"""`pipeline/ruler_scale.py` 가 낸 배율 CSV 를 테이블(Scale)에 넣는다 (`specimens/scales.py`, wetherilli 010).

    python web/manage.py import_scales scales.csv
    # 운영 — 파일을 /srv/Siriopsis/backup/import/ 에 두면 manage 컨테이너에 같은 자리로(읽기만) 붙어 있다
    docker compose run --rm -T manage import_scales /srv/Siriopsis/backup/import/<파일>.csv

몇 번을 넣어도 같다. `ok` 만 값을 넣고, 믿기 어려운 것·자를 못 찾은 것은 까닭만 남긴다.
"""
from django.core.management.base import BaseCommand

from specimens.scales import import_file


class Command(BaseCommand):
    help = "배율 CSV(열쇠는 컷 경로)를 Scale 테이블에 넣는다"

    def add_arguments(self, parser):
        parser.add_argument("csv")

    def handle(self, *args, csv=None, **opts):
        st = import_file(csv)
        for b in st.bad[:20]:
            self.stderr.write(f"건너뜀: {b}")
        self.stdout.write(self.style.SUCCESS(str(st)))
