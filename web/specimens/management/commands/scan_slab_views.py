"""슬랩 전경(`SP-2016-694(dorsal).JPG`)을 읽어 Stack(kind=slab)·Frame 테이블을 맞춘다 (`specimens/slabviews.py`).

    python web/manage.py scan_slab_views                          # SOURCE_ROOT 전체 — 정본 고르기·지우기는 이때만
    python web/manage.py scan_slab_views --under "SP-2022-샘플별"   # 일부만 (지우지 않는다)
"""
from django.core.management.base import BaseCommand

from specimens.slabviews import scan


class Command(BaseCommand):
    help = "SOURCE_ROOT 아래의 슬랩 전경(dorsal)을 읽어 테이블을 맞춘다 (원본은 읽기만)"

    def add_arguments(self, parser):
        parser.add_argument("--root", help="SOURCE_ROOT 대신 볼 폴더")
        parser.add_argument("--under", help="SOURCE_ROOT 안의 이 폴더 아래만 (지우지 않는다)")
        parser.add_argument("--workers", type=int, default=16, help="EXIF 를 같이 읽는 수 (NAS 지연을 메운다)")

    def handle(self, *args, root=None, under=None, workers=16, **opts):
        st = scan(root=root, under=under, workers=workers, log=self.stdout.write)
        for e in st.errors[:30]:
            self.stderr.write(f"못 읽음: {e}")
        if len(st.errors) > 30:
            self.stderr.write(f"… {len(st.errors) - 30} 건 더")
        self.stdout.write(self.style.SUCCESS(
            f"사진 {st.files} · 이름 묶음 {st.names} · 정본 {st.chosen} · 사본 {st.copies} · 새로 {st.created} · "
            f"바뀜 {st.updated} · 그대로 {st.unchanged} · 지움 {st.removed} · EXIF 읽음 {st.exif_read} · 못 읽음 {len(st.errors)}"))
