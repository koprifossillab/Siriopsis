"""NAS 의 엑셀 목록에서 별표(☆)와 counterpart 짝을 읽어 Star·Counterpart 테이블을 다시 만든다 (`specimens/workbook.py`, wetherilli 013).

    python web/manage.py import_workbooks            # SOURCE_ROOT 바로 아래의 SP-*.xlsx, 연도마다 가장 늦게 고친 것
    python web/manage.py import_workbooks --verbose  # 못 읽은 counterpart 글을 모두 찍는다

엑셀은 읽기만 한다. 몇 번을 돌려도 같다.
"""
from django.core.management.base import BaseCommand

from specimens.workbook import sync


class Command(BaseCommand):
    help = "엑셀 목록의 별표·counterpart 를 읽는다 (원본은 읽기만)"

    def add_arguments(self, parser):
        parser.add_argument("--root", help="SOURCE_ROOT 대신 볼 폴더")
        parser.add_argument("--verbose", action="store_true", help="못 읽은 글을 모두 찍는다")

    def handle(self, *args, root=None, verbose=False, **opts):
        st = sync(root)
        self.stdout.write(f"읽은 파일: {', '.join(st.files) or '없음'}")
        for e in st.errors:
            self.stderr.write(f"못 읽음: {e}")
        for title, rows in (("번호 없는 counterpart", st.no_target), ("not counterpart", st.negated),
                            ("제 자신을 가리킴", st.self_ref)):
            if rows:
                self.stdout.write(f"{title} {len(rows)}")
                for r in rows if verbose else rows[:5]:
                    self.stdout.write(f"  {r}")
        self.stdout.write(self.style.SUCCESS(
            f"행 {st.rows} · 별표 {st.stars} · counterpart 글 {st.mentions} → 짝 {st.pairs}(불확실 {st.uncertain}) · "
            f"번호 없음 {len(st.no_target)} · not {len(st.negated)} · 제 자신 {len(st.self_ref)} · 못 읽음 {len(st.errors)}"))
