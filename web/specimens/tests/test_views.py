"""뷰어 화면과 컷 서빙 (wetherilli 005). 원본·캐시 뿌리를 임시 디렉터리로 갈고 시험한다 — NAS 를 읽지 않는다."""
import io
import tempfile
from pathlib import Path

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from core.tests.base import SafeTestCase
from specimens import browse, thumbs
from specimens.models import Frame, Slab, Specimen, Stack

from .fixtures import make_jpg


class BandTest(SafeTestCase):
    def test_horizon_bands(self):
        # phyloserver 의 층준은 손으로 적은 글자다 — 고치지 않고 묶기만
        self.assertEqual(browse.band_of("6.15-6.2")[1], "6.1–6.2 m")
        self.assertEqual(browse.band_of("6.2~6.3")[1], "6.2–6.3 m")
        self.assertEqual(browse.band_of("~7.3")[1], "7.3–7.4 m")
        self.assertEqual(browse.band_of("scree")[0], browse.band_of("SCREE")[0])
        self.assertEqual(browse.band_of("")[0], browse.BLANK)
        self.assertEqual(browse.band_of("?")[0], browse.UNKNOWN)
        self.assertLess(browse.band_of("5.9")[0], browse.band_of("6.0")[0])

    def test_folder_names_follow_nas(self):
        s = Slab(slab_no="SP-2016-0110", year=2016)
        self.assertEqual(browse.folder_of(s), "SP-2016(101~110)")
        self.assertEqual(browse.block_of(s)[1], "101~200")


class ViewerTest(SafeTestCase):
    @classmethod
    def setUpClass(cls):
        # 뿌리를 먼저 간다 (core/tests/base.py 머리말)
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.src, cls.cache = root / "src", root / "cache"
        cls._over = override_settings(SOURCE_ROOT=cls.src, THUMB_CACHE=cls.cache)
        cls._over.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._over.disable()
        cls._tmp.cleanup()

    def setUp(self):
        (self.src / "a").mkdir(parents=True, exist_ok=True)
        for i in (1, 2):
            make_jpg(self.src / "a" / f"SP-2022-131A-{i}.JPG", size=(800, 600))
        self.slab = Slab.objects.create(slab_no="SP-2022-0131", year=2022, catalog_id=77)
        sp = Specimen.objects.create(slab=self.slab, letter="A", taxon_name="Halkieria evangelista",
                                     phylum="Mollusca", catalog_id=88)
        self.series = Stack.objects.create(slab=self.slab, specimen=sp, kind="series", preparation="none",
                                           view="whole", label="SP-2022-131A", source_dir="a", n_frames=2,
                                           other_copies=1)
        self.f1 = Frame.objects.create(stack=self.series, seq=0, shot_no=1, path="a/SP-2022-131A-1.JPG")
        Frame.objects.create(stack=self.series, seq=1, shot_no=2, path="a/SP-2022-131A-2.JPG")
        self.copy = Stack.objects.create(slab=self.slab, specimen=sp, kind="series", preparation="none",
                                         view="whole", label="SP-2022-131A", source_dir="b",
                                         copy_of=self.series, n_frames=2)
        self.ptm = Stack.objects.create(slab=self.slab, kind="ptm", preparation="white_coated", view="whole",
                                        label="SP-2022-131", source_dir="p", n_frames=1)
        Frame.objects.create(stack=self.ptm, seq=0, path="p/IMG_1.JPG", light_x=-0.73, light_y=-0.44, light_z=0.52)

    def test_home_lists_slab_once_and_finds_taxon(self):
        r = self.client.get(reverse("home"))
        self.assertContains(r, 'class="row" data-in', count=1)       # 표본·더미가 여럿이어도 슬랩은 한 줄
        self.assertContains(r, "SP-2022(131~140)")                    # NAS 의 열 개 폴더 이름 꼴
        self.assertEqual(r.context["sums"]["series"], 1)              # 사본은 묶음 수에 넣지 않는다
        self.assertEqual(r.context["sums"]["copies"], 1)
        self.assertContains(self.client.get(reverse("home"), {"q": "halkieria"}), "SP-2022-0131")
        self.assertNotContains(self.client.get(reverse("home"), {"q": "Anomalocaris"}), "SP-2022-0131")
        self.assertContains(self.client.get(reverse("home"), {"kind": "ptm"}), "SP-2022-0131")
        self.assertContains(self.client.get(reverse("home"), {"view": "grid"}), 'class="tile"', count=1)
        self.assertContains(self.client.get(reverse("home"), {"y": "2022"}), "SP-2022-0131")

    def test_slab_groups_by_specimen_and_loose(self):
        r = self.client.get(reverse("slab", args=["SP-2022-0131"]))
        self.assertContains(r, "Halkieria evangelista")
        self.assertContains(r, "specimen_detail/88/")
        self.assertContains(r, "slab_detail/77/")
        self.assertContains(r, "표본 글자 없음")                   # 글자 없는 PTM
        self.assertNotContains(r, reverse("stack", args=[self.copy.id]))   # 사본은 정본 화면에서

    def test_stack_pages_differ_by_kind(self):
        r = self.client.get(reverse("stack", args=[self.ptm.id]))
        self.assertContains(r, 'id="pad"')
        r = self.client.get(reverse("stack", args=[self.series.id]))
        self.assertNotContains(r, 'id="pad"')
        self.assertContains(r, "2벌")
        self.assertContains(r, reverse("stack", args=[self.copy.id]))
        # 사본에서 열어도 같은 줄이 정본을 가리킨다
        r = self.client.get(reverse("stack", args=[self.copy.id]))
        self.assertContains(r, reverse("stack", args=[self.series.id]))

    def test_frame_thumbnail_snaps_width_and_caches(self):
        r = self.client.get(reverse("frame_image", args=[self.f1.id]), {"w": "150"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        im = Image.open(io.BytesIO(b"".join(r.streaming_content)))
        self.assertEqual(im.size, (200, 150))                       # 150 → 200
        self.assertEqual(len(list(self.cache.glob("*.jpg"))), 1)
        self.client.get(reverse("frame_image", args=[self.f1.id]), {"w": "200"})
        self.assertEqual(len(list(self.cache.glob("*.jpg"))), 1)    # 같은 폭은 같은 파일

    def test_frame_original_and_narrow_source(self):
        r = self.client.get(reverse("frame_image", args=[self.f1.id]))
        self.assertEqual(Image.open(io.BytesIO(b"".join(r.streaming_content))).size, (800, 600))
        # 원본이 그 폭보다 좁으면 늘리지 않고 원본을 낸다
        r = self.client.get(reverse("frame_image", args=[self.f1.id]), {"w": "2560"})
        self.assertEqual(Image.open(io.BytesIO(b"".join(r.streaming_content))).size, (800, 600))

    def test_frame_refuses_missing_outside_and_bad_width(self):
        self.assertEqual(self.client.get(reverse("frame_image", args=[999])).status_code, 404)
        gone = Frame.objects.get(stack=self.ptm)                      # 파일이 없다
        self.assertEqual(self.client.get(reverse("frame_image", args=[gone.id])).status_code, 404)
        outside = Path(self._tmp.name) / "secret.jpg"
        make_jpg(outside)
        gone.path = "../secret.jpg"
        gone.save()
        self.assertEqual(self.client.get(reverse("frame_image", args=[gone.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("frame_image", args=[self.f1.id]), {"w": "x"}).status_code, 404)

    def test_snap_width(self):
        self.assertEqual(thumbs.snap_width("1"), thumbs.WIDTHS[0])
        self.assertEqual(thumbs.snap_width("1600"), 1600)
        self.assertEqual(thumbs.snap_width("99999"), thumbs.WIDTHS[-1])
