"""배율을 잴 컷 — 보이는 빛 묶음마다 보이는 첫 컷 — 을 CSV 로 낸다 (`specimens/scales.py`, wetherilli 010).

    python web/manage.py scale_targets --out targets.csv
    docker compose run --rm -T manage scale_targets > targets.csv      # 운영 (호스트는 운영 DB 를 열지 않는다)

그 파일을 호스트의 `pipeline/ruler_scale.py --targets` 가 읽는다.
"""
import sys

from django.core.management.base import BaseCommand

from specimens.scales import write_targets


class Command(BaseCommand):
    help = "배율을 잴 컷(빛 묶음의 보이는 첫 컷)을 CSV 로 낸다"

    def add_arguments(self, parser):
        parser.add_argument("--out", help="쓸 파일 (없으면 표준 출력)")
        parser.add_argument("--no-copies", action="store_true", help="사본 묶음은 빼고 정본만")

    def handle(self, *args, out=None, no_copies=False, **opts):
        copies = not no_copies
        if out:
            with open(out, "w", newline="", encoding="utf-8") as fh:
                n = write_targets(fh, copies)
            self.stderr.write(f"컷 {n} → {out}")
        else:
            n = write_targets(sys.stdout, copies)
            self.stderr.write(f"컷 {n}")
