"""슬랩 전경(dorsal) 반입 (wetherilli 009). 시험은 NAS 를 읽지 않는다 — 픽스처 사진을 스스로 만든다."""
import shutil
import tempfile
from pathlib import Path

from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import regroup
from specimens.lightseries import scan as scan_series
from specimens.models import Stack
from specimens.slabviews import parse, scan

from .fixtures import make_jpg

MAIN = "SP-2016 샘플별/SP-2016(61~70)"


def put(root, rel, *names):
    d = Path(root) / rel
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        make_jpg(d / n)


class ParseTest(SafeTestCase):
    def test_names(self):
        self.assertEqual(parse("SP-2016-694(dorsal).JPG")[:2], ("SP-2016-694", "SP-2016-0694"))
        self.assertEqual(parse("SP-2016-892 (dorsal).jpg")[1], "SP-2016-0892")
        self.assertEqual(parse("SP-2016-1316A(dorsal).JPG")[1], "SP-2016-1316")         # 글자가 있어도 슬랩 사진
        self.assertEqual(parse("SP-2016-64&65(dorsal).jpg")[:2], ("SP-2016-64&65", "SP-2016-0064"))
        self.assertEqual(parse("SP-2017-2SP-2017-2237(dorsal).JPG")[1], "SP-2017-2237")  # 겹쳐 적은 이름
        self.assertEqual(parse("SP-2016-1155-(dorsal).JPG")[1], "SP-2016-1155")
        self.assertEqual(parse("SP-2016-816(dorsal(.JPG")[1], "SP-2016-0816")
        self.assertEqual(parse("724(dorsal).JPG", "SP-2017(721~730)")[1], "SP-2017-0724")
        self.assertIsNone(parse("724(dorsal).JPG", "SP-2017(731~740)"))                  # 구간 밖이면 모른다
        self.assertEqual(parse("SP-2016-47 (vent).JPG")[:2], ("SP-2016-47(vent)", "SP-2016-0047"))   # dorsal 과 다른 묶음
        self.assertEqual(parse("731(vent).JPG", "SP-2017(731~740)")[0], "SP-2017-731(vent)")
        for bad in ("JC-SPIDER-8(dorsal).JPG", "SP-2016-47A-1.JPG", "SP-2016-47vent).JPG", "SP-2016-47A-1(ethanol).JPG"):
            self.assertIsNone(parse(bad), bad)
        # 차례: 번호 없는 것 → 번호 순 → 변형
        keys = sorted(["SP-2018-215 (dorsal) (2).JPG", "SP-2018-215 (dorsal-DSLR).JPG", "SP-2018-215 (dorsal) (1).JPG"],
                      key=lambda n: parse(n)[3])
        self.assertEqual(keys[-1], "SP-2018-215 (dorsal-DSLR).JPG")


class ScanSlabViewsTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_slab_only_and_copies(self):
        put(self.root, MAIN, "SP-2016-64(dorsal).JPG", "SP-2016-65A(dorsal).JPG", "SP-2016-64&65(dorsal).jpg",
            "SP-2016-64A-1.JPG", "SP-2016-64A-2.JPG")
        put(self.root, "SP-2016 샘플별/6D 외/2016.12.25 USB백업/SP-2016 샘플별/SP-2016(61~70)", "SP-2016-64(dorsal).JPG")
        st = scan(root=self.root)
        self.assertEqual((st.chosen, st.copies, st.created, st.errors), (3, 1, 4, []))
        s64 = Stack.objects.get(kind="slab", label="SP-2016-64", copy_of=None)
        self.assertEqual((s64.source_dir, s64.other_copies, s64.specimen, s64.n_frames), (MAIN, 1, None, 1))
        self.assertIsNone(Stack.objects.get(label="SP-2016-65A").specimen)     # 표본에 안 붙는다
        self.assertEqual(Stack.objects.get(label="SP-2016-64&65").slab.slab_no, "SP-2016-0064")
        # 빛 묶음 반입은 dorsal 을 안 읽고, 이쪽은 빛 묶음을 안 읽는다
        scan_series(root=self.root)
        self.assertEqual(Stack.objects.filter(kind="series").count(), 1)
        self.assertEqual(Stack.objects.filter(kind="slab").count(), 4)
        st = scan(root=self.root)
        self.assertEqual((st.created, st.updated, st.unchanged, st.exif_read), (0, 0, 4, 0))

    def test_numbered_shots_are_one_stack(self):
        put(self.root, "SP-2018-샘플별/SP-2018-(211~220)", "SP-2018-215 (dorsal) (2).JPG", "SP-2018-215 (dorsal) (1).JPG")
        scan(root=self.root)
        st = Stack.objects.get(kind="slab")
        self.assertEqual(st.n_frames, 2)
        self.assertEqual(st.frames.get(seq=0).path.rsplit("/", 1)[1], "SP-2018-215 (dorsal) (1).JPG")

    def test_vanished_and_missing_root(self):
        put(self.root, MAIN, "SP-2016-64(dorsal).JPG", "SP-2016-66(dorsal).JPG")
        scan(root=self.root)
        (self.root / MAIN / "SP-2016-66(dorsal).JPG").unlink()
        self.assertEqual(scan(root=self.root).removed, 1)
        put(self.root, "SP-2017-샘플별/SP-2017(1~10)", "SP-2017-1(dorsal).JPG")
        scan(root=self.root)
        self.assertEqual(scan(root=self.root, under="SP-2017-샘플별").removed, 0)   # 일부만 훑으면 지우지 않는다
        self.assertEqual(Stack.objects.filter(kind="slab").count(), 2)
        st = scan(root=self.root / "붙지 않은 NAS")
        self.assertEqual((st.removed, bool(st.errors)), (0, True))
        shutil.rmtree(self.root / "SP-2016 샘플별")
        shutil.rmtree(self.root / "SP-2017-샘플별")
        st = scan(root=self.root)
        self.assertEqual((st.removed, bool(st.errors)), (0, True))
        self.assertEqual(Stack.objects.filter(kind="slab").count(), 2)

    def test_slab_page_and_not_editable(self):
        put(self.root, MAIN, "SP-2016-64(dorsal).JPG", "SP-2016-64A-1.JPG", "SP-2016-64A-2.JPG")
        scan(root=self.root)
        scan_series(root=self.root)
        put(self.root, MAIN, "SP-2016-64(vent).JPG")
        scan(root=self.root)
        r = self.client.get(reverse("slab", args=["SP-2016-0064"]))
        self.assertEqual(r.context["rep"].label, "SP-2016-64")                  # 대표는 dorsal
        self.assertEqual(r.context["vent"].label, "SP-2016-64(vent)")           # vent 는 dorsal 과 나란히
        self.assertContains(r, 'class="heropair"')
        # vent 가 차례상 앞에 와도(dorsal 이 흰 코팅 폴더에만 있을 때) 대표는 dorsal
        put(self.root, "SP-2016 샘플별/SP-2016(71~80)", "SP-2016-77(vent).JPG", "SP-2016-77A-1.JPG", "SP-2016-77A-2.JPG")
        put(self.root, "SP-2016 샘플별/SP-2016-white coated", "SP-2016-77(dorsal).JPG")
        scan(root=self.root)
        r77 = self.client.get(reverse("slab", args=["SP-2016-0077"]))
        self.assertEqual(r77.context["rep"].label, "SP-2016-77")
        self.assertEqual(r77.context["vent"].label, "SP-2016-77(vent)")
        # vent 만 있으면 그것이 대표이고 짝은 없다
        put(self.root, MAIN, "SP-2016-66(vent).JPG", "SP-2016-66A-1.JPG", "SP-2016-66A-2.JPG")
        scan(root=self.root)
        r66 = self.client.get(reverse("slab", args=["SP-2016-0066"]))
        self.assertEqual((r66.context["rep"].label, r66.context["vent"]), ("SP-2016-66(vent)", None))
        self.assertNotContains(r66, 'class="heropair"')
        self.assertContains(r, "슬랩 전경")
        self.assertEqual([g["specimen"].letter for g in r.context["groups"]], ["A"])
        self.assertEqual(len(r.context["overview"]), 2)
        self.assertEqual(r.context["loose"], [])                               # 「표본 글자 없음」 칸에 섞이지 않는다
        self.assertFalse(regroup.delete_preview(Stack.objects.get(kind="slab", label="SP-2016-64"))["ok"])
