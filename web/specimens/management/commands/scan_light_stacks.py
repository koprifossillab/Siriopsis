"""NAS 의 빛 더미(`.lp` 가 있는 폴더)를 읽어 Stack·Frame 테이블을 맞춘다 (`specimens/lightstacks.py`).

    python web/manage.py scan_light_stacks                       # SOURCE_ROOT 전체 (NAS 를 다 훑어 몇 분 걸린다)
    python web/manage.py scan_light_stacks --under "SP-2016 샘플별/6D 외"
"""
from django.core.management.base import BaseCommand

from specimens.lightstacks import scan


class Command(BaseCommand):
    help = "SOURCE_ROOT 아래의 빛 더미를 읽어 테이블을 맞춘다 (원본은 읽기만)"

    def add_arguments(self, parser):
        parser.add_argument("--root", help="SOURCE_ROOT 대신 볼 폴더")
        parser.add_argument("--under", help="SOURCE_ROOT 안의 이 폴더 아래만 훑는다")

    def handle(self, *args, root=None, under=None, **opts):
        st = scan(root=root, under=under, log=self.stdout.write)
        for e in st.errors:
            self.stderr.write(f"못 읽음: {e}")
        self.stdout.write(self.style.SUCCESS(
            f".lp {st.found} · 새로 {st.created} · 바뀜 {st.updated} · 그대로 {st.unchanged} · "
            f"못 읽음 {len(st.errors)}"))
