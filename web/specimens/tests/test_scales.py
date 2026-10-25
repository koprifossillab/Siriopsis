"""더미의 배율 — 잴 컷 내보내기·잰 값 넣기·화면·묶음 고치기 (wetherilli 010). NAS 를 읽지 않는다."""
import csv
import io
import json
import re
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import regroup, scales
from specimens.lightseries import scan
from specimens.models import Scale, Stack

from .fixtures import make_jpg
from .test_lightseries import MAIN, shots


def row(path, status="ok", mmpp="0.0125", **kw):
    r = {"path": path, "width": "40", "height": "30", "status": status, "mm_per_px": mmpp, "ticks": "30", "note": ""}
    r.update(kw)
    return r


class ScaleTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shots(self.root, MAIN, "SP-2016-47K", [1, 2, 3, 4])
        shots(self.root, MAIN, "SP-2016-47A", [1, 2])
        scan(root=self.root)
        self.k = Stack.objects.get(label="SP-2016-47K")
        self.a = Stack.objects.get(label="SP-2016-47A")

    def tearDown(self):
        self._tmp.cleanup()

    def first(self, stack):
        return stack.frames.filter(hidden=False).order_by("seq").first()

    def test_targets_are_first_visible_frames(self):
        t = scales.targets()
        self.assertEqual({r["path"] for r in t}, {f"{MAIN}/SP-2016-47K-1.JPG", f"{MAIN}/SP-2016-47A-1.JPG"})
        regroup.hide_frame(self.first(self.k))           # 1 번을 숨기면 2 번이 잴 컷이다
        self.assertIn(f"{MAIN}/SP-2016-47K-2.JPG", {r["path"] for r in scales.targets()})
        out = io.StringIO()
        scales.write_targets(out)
        self.assertEqual(next(csv.reader(io.StringIO(out.getvalue()))), scales.TARGET_FIELDS)

    def test_import_keeps_only_trusted_values_and_is_repeatable(self):
        rows = [row(self.first(self.k).path),
                row(self.first(self.a).path, status="doubt", mmpp="0.02", note="눈금 8 개뿐"),
                row("없는/컷.JPG"), {"path": "x", "status": "몰라"}]
        st = scales.import_rows(rows)
        self.assertEqual((st.ok, st.doubt, st.no_frame, len(st.bad)), (1, 1, 1, 1))
        k, a = Scale.objects.get(stack=self.k), Scale.objects.get(stack=self.a)
        self.assertEqual((k.status, k.mm_per_px, k.width, k.height), ("ok", 0.0125, 40, 30))
        # 믿기 어려운 값은 넣지 않고 까닭에 어림값을 남긴다
        self.assertEqual((a.status, a.mm_per_px), ("doubt", None))
        self.assertIn("0.02000", a.note)
        self.assertIn("눈금 8 개뿐", a.note)
        scales.import_rows(rows)
        self.assertEqual(Scale.objects.count(), 2)
        # 사람의 손이 아니다 — 반입이 묶음을 그대로 다시 맞춘다
        self.k.refresh_from_db()
        self.assertIsNone(self.k.edited_at)

    def test_ok_without_value_is_refused(self):
        st = scales.import_rows([row(self.first(self.k).path, mmpp="")])
        self.assertEqual((st.ok, len(st.bad)), (0, 1))
        self.assertFalse(Scale.objects.exists())

    def test_command_reads_csv(self):
        p = self.root / "scales.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, list(row("x")))
            w.writeheader()
            w.writerow(row(self.first(self.k).path))
        out = io.StringIO()
        call_command("import_scales", str(p), stdout=out)
        self.assertIn("잼 1", out.getvalue())
        self.assertTrue(Scale.objects.filter(stack=self.k, status="ok").exists())

    def test_fits_only_same_size(self):
        scales.import_rows([row(self.first(self.k).path)])
        sc = Scale.objects.get(stack=self.k)
        self.assertTrue(sc.fits(40, 30))
        self.assertFalse(sc.fits(30, 40))

    def test_split_moves_scale_with_its_frame(self):
        scales.import_rows([row(self.first(self.k).path)])
        # 잰 컷(1 번)이 남는 쪽: 그대로
        (new_id,) = regroup.apply_split(self.k, [self.k.frames.get(shot_no=2).id])
        self.assertEqual(Scale.objects.get().stack_id, self.k.id)
        # 잰 컷이 숨어 1 번이 아닌 묶음을 다시 가르면 — 잰 컷을 가진 조각으로 간다
        Scale.objects.all().delete()
        new = Stack.objects.get(id=new_id)
        scales.import_rows([row(new.frames.get(shot_no=4).path)])
        (newer,) = regroup.apply_split(new, [new.frames.get(shot_no=3).id])
        self.assertEqual(Scale.objects.get().stack_id, newer)

    def test_merge_keeps_receivers_scale(self):
        scales.import_rows([row(self.first(self.k).path, mmpp="0.01"), row(self.first(self.a).path, mmpp="0.02")])
        regroup.apply_merge(self.k, self.a.id)
        self.assertEqual(Scale.objects.get(stack=self.k).mm_per_px, 0.01)

    def test_merge_takes_others_scale_when_receiver_has_none(self):
        scales.import_rows([row(self.first(self.a).path, mmpp="0.02")])
        regroup.apply_merge(self.k, self.a.id)
        self.assertEqual(Scale.objects.get(stack=self.k).mm_per_px, 0.02)


class ScaleViewTest(SafeTestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls._over = override_settings(SOURCE_ROOT=cls.root, THUMB_CACHE=cls.root / "cache")
        cls._over.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._over.disable()
        cls._tmp.cleanup()

    def payload(self, resp):
        m = re.search(r'<script type="application/json" id="frames-data">(.*?)</script>', resp.content.decode(), re.S)
        return json.loads(m.group(1))

    def test_scale_reaches_only_frames_of_the_measured_size(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        make_jpg(self.root / MAIN / "SP-2016-47K-3.JPG", size=(60, 30))     # 딴 카메라·확대 — 크기가 다르다
        scan(root=self.root)
        k = Stack.objects.get(label="SP-2016-47K")
        url = reverse("stack", args=[k.id])
        r = self.client.get(url)
        self.assertEqual([f["mmpp"] for f in self.payload(r)], [None, None, None])
        self.assertContains(r, "아직 재지 않음")
        scales.import_rows([row(k.frames.get(shot_no=1).path)])
        r = self.client.get(url)
        self.assertEqual([f["mmpp"] for f in self.payload(r)], [0.0125, 0.0125, None])
        self.assertContains(r, "0.01250 mm/px")
        self.assertContains(r, "1 mm = 80 px")
        self.assertContains(r, "크기가 다른 컷 1")

    def test_untrusted_scale_says_why(self):
        shots(self.root, MAIN, "SP-2016-47A", [1, 2])
        scan(root=self.root)
        a = Stack.objects.get(label="SP-2016-47A")
        scales.import_rows([row(a.frames.get(shot_no=1).path, status="none", mmpp="", note="자를 못 찾음")])
        r = self.client.get(reverse("stack", args=[a.id]))
        self.assertEqual({f["mmpp"] for f in self.payload(r)}, {None})
        self.assertContains(r, "자를 못 찾음")
