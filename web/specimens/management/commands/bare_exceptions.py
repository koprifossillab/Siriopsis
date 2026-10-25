"""글자 없는 더미가 있는데 A 가 아닌 표본도 알려진 슬랩 — A 에 붙이지 않은 것을 표로 낸다 (`specimens/bare.py`, wetherilli 012).

    python web/manage.py bare_exceptions                        # 화면에
    python web/manage.py bare_exceptions --csv /nfs/temp-share/Siriopsis/survey/20261025_bare_not_a.csv
"""
import csv
import sys

from django.core.management.base import BaseCommand

from specimens import bare

FIELDS = ("slab", "bare_stacks", "labels", "phyloserver_letters", "nas_letters", "in_phyloserver")


class Command(BaseCommand):
    help = "글자 없는 이름을 A 에 붙이지 않은 슬랩(A 가 아닌 표본이 따로 있다)을 낸다 (읽기만)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", help="이 파일에 쓴다 (UTF-8 BOM — 윈도 엑셀이 한글을 읽게)")

    def handle(self, *args, **opts):
        rows = bare.exceptions()
        path = opts.get("csv")
        out = open(path, "w", newline="", encoding="utf-8-sig") if path else sys.stdout
        try:
            w = csv.DictWriter(out, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        finally:
            if path:
                out.close()
        self.stderr.write(f"예외 슬랩 {len(rows)}" + (f" → {path}" if path else ""))
