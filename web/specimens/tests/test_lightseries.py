import shutil
import tempfile
from pathlib import Path

from core.tests.base import SafeTestCase
from specimens.lightseries import scan
from specimens.models import Frame, Stack

from .fixtures import make_jpg

MAIN = "SP-2016 샘플별/SP-2016(41-50)"


def shots(root, rel, name, numbers, sep="-"):
    d = Path(root) / rel
    d.mkdir(parents=True, exist_ok=True)
    for n in numbers:
        make_jpg(d / f"{name}{sep}{n}.JPG")
    return d


class ScanLightSeriesTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_groups_by_name_in_number_order(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2, 9, 10, 11])
        shots(self.root, "SP-2022-샘플별/SP-2022(131~140)", "SP-2022-131", [1, 2, 3])
        st = scan(root=self.root)
        self.assertEqual((st.chosen, st.created, st.errors), (2, 2, []))
        k = Stack.objects.get(label="SP-2016-47K")
        self.assertEqual((k.kind, k.n_frames, k.slab.slab_no, k.specimen.specimen_no),
                         ("series", 5, "SP-2016-0047", "SP-2016-0047-K"))
        self.assertEqual(list(k.frames.values_list("shot_no", flat=True)), [1, 2, 9, 10, 11])   # 10 이 2 앞에 오지 않는다
        self.assertEqual(k.frames.get(seq=3).path, f"{MAIN}/SP-2016-47K-10.JPG")
        s131 = Stack.objects.get(label="SP-2022-131")
        self.assertIsNone(s131.specimen)                # 글자가 없으면 슬랩에만
        self.assertEqual(s131.slab.slab_no, "SP-2022-0131")

        st = scan(root=self.root)
        self.assertEqual((st.created, st.updated, st.unchanged, st.exif_read), (0, 0, 2, 0))   # 다시 읽지 않는다

    def test_other_views_and_copies_are_not_series(self):
        d = shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        for f in ("SP-2016-47(dorsal).JPG", "SP-2016-47A-1(ethanol).JPG", "SP-2017-1 (Cutting)-1.JPG"):
            make_jpg(d / f)
        shots(self.root, f"{MAIN}/output", "SP-2016-48A", [1, 2])     # 줄인 사본
        shots(self.root, MAIN, "SP-2016-49A", [1])                     # 한 장뿐
        st = scan(root=self.root)
        self.assertEqual(st.single, 1)
        self.assertEqual(list(Stack.objects.values_list("label", flat=True)), ["SP-2016-47K"])

    def test_duplicate_folders_pick_one(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2, 3])
        shots(self.root, "SP-2016 샘플별/6D 외/2016-B&S&A/2017 .05. 10 Baguette", "SP-2016-47K", [1, 2, 3])
        shots(self.root, f"{MAIN}/알씨원본", "SP-2016-47K", [1, 2, 3])
        shots(self.root, "SP-2016 샘플별/6D 외/mg코팅/mg 코팅 1", "SP-2016-47K", [1, 2])
        scan(root=self.root)
        plain = Stack.objects.get(preparation="none")
        self.assertEqual((plain.source_dir, plain.other_copies), (MAIN, 2))
        coated = Stack.objects.get(preparation="mg_coated")    # 코팅한 것은 사본이 아니라 다른 묶음
        self.assertEqual(coated.n_frames, 2)

    def test_more_frames_wins_and_old_choice_is_removed(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        scan(root=self.root)
        shots(self.root, f"{MAIN}/SP-2016(41-50)", "SP-2016-47K", [1, 2, 3])
        st = scan(root=self.root)
        self.assertEqual((st.created, st.removed), (1, 1))
        self.assertEqual(Stack.objects.get().source_dir, f"{MAIN}/SP-2016(41-50)")

    def test_missing_root_deletes_nothing(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        scan(root=self.root)
        shutil.rmtree(self.root / "SP-2016 샘플별")
        st = scan(root=self.root)
        self.assertEqual(st.removed, 0)
        self.assertTrue(st.errors)
        self.assertEqual(Frame.objects.count(), 2)
        st = scan(root=self.root / "없는 폴더")
        self.assertEqual(st.removed, 0)

    def test_partial_scan_does_not_delete(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        shots(self.root, "SP-2022-샘플별/x", "SP-2022-131", [1, 2])
        scan(root=self.root)
        st = scan(root=self.root, under="SP-2022-샘플별")
        self.assertEqual(st.removed, 0)
        self.assertEqual(Stack.objects.count(), 2)
