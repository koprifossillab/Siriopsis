"""표본 테두리 — 계측·저장·지우기·묶음 고치기·화면 (wetherilli 011). NAS 를 읽지 않는다."""
import json
import math
import re
import tempfile
from pathlib import Path

from django.test import Client, override_settings
from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import outlines, regroup, scales, shape
from specimens.lightseries import scan
from specimens.lightstacks import scan as scan_ptm
from specimens.models import EditLog, Outline, Stack

from .fixtures import make_jpg, make_stack
from .test_lightseries import MAIN, shots

SQUARE = [[10, 5], [30, 5], [30, 25], [10, 25]]          # 20 × 20 px


class ShapeTest(SafeTestCase):
    def test_square(self):
        m = shape.measure([tuple(p) for p in SQUARE])
        self.assertAlmostEqual(m["area_px"], 400)
        self.assertAlmostEqual(m["perimeter_px"], 80)
        self.assertAlmostEqual(m["long_px"], 20)
        self.assertAlmostEqual(m["short_px"], 20)
        # 넓이가 같은 정사각형의 모멘트 타원: λ = 20²/12 → 지름 4√λ
        self.assertAlmostEqual(m["major_px"], 4 * math.sqrt(400 / 12))

    def test_rotated_rectangle_long_and_short(self):
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
        rect = [(x * c - y * s, x * s + y * c) for x, y in [(0, 0), (40, 0), (40, 10), (0, 10)]]
        m = shape.measure(rect)
        self.assertAlmostEqual(m["long_px"], 40, places=6)
        self.assertAlmostEqual(m["short_px"], 10, places=6)
        self.assertAlmostEqual(m["area_px"], 400, places=6)

    def test_degenerate(self):
        self.assertIsNone(shape.measure([(0, 0), (1, 1)])["area_px"])
        self.assertIsNone(shape.measure([(0, 0), (1, 1), (2, 2)])["area_px"])


class OutlineTest(SafeTestCase):
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

    def f(self, stack, no):
        return stack.frames.get(shot_no=no)

    def test_save_measures_on_server_and_marks_edited(self):
        o = outlines.save(self.k, self.f(self.k, 2).id, json.dumps(SQUARE))
        self.assertEqual((o.frame_path, o.width, o.height, o.area_px), (self.f(self.k, 2).path, 40, 30, 400))
        self.k.refresh_from_db()
        self.assertIsNotNone(self.k.edited_at)
        self.assertEqual(EditLog.objects.get(action="outline").detail["points"], 4)
        # 다시 그리면 한 줄을 고쳐 쓴다 — 한 더미에 하나
        outlines.save(self.k, self.f(self.k, 1).id, [[0, 0], [40, 0], [40, 30]])
        self.assertEqual(Outline.objects.count(), 1)
        self.assertEqual(Outline.objects.get().area_px, 600)

    def test_rescan_keeps_the_outline(self):
        outlines.save(self.k, self.f(self.k, 1).id, SQUARE)
        shots(self.root, MAIN, "SP-2016-47K", [5])        # 새 컷 — 손댄 묶음은 반입이 덮지 않는다
        scan(root=self.root)
        self.k.refresh_from_db()
        self.assertEqual((self.k.n_frames, Outline.objects.get().stack_id), (4, self.k.id))

    def test_refuses_bad_input(self):
        fid = self.f(self.k, 1).id
        for frame, pts in ((fid, "[[0,0],[1,1]]"), (fid, "x"), (fid, [[0, 0], [10, 10], [20, 20]]),
                           (fid, [[0, 0], [400, 0], [0, 30]]), (self.f(self.a, 1).id, SQUARE), ("x", SQUARE)):
            with self.assertRaises(ValueError, msg=(frame, pts)):
                outlines.save(self.k, frame, pts)
        self.assertFalse(Outline.objects.exists())
        self.k.refresh_from_db()
        self.assertIsNone(self.k.edited_at)

    def test_points_just_outside_are_pulled_to_the_edge(self):
        o = outlines.save(self.k, self.f(self.k, 1).id, [[-0.5, -0.5], [40.4, 0], [40, 30.3]])
        self.assertEqual(o.points, [[0.0, 0.0], [40.0, 0.0], [40.0, 30.0]])

    def test_hidden_frame_and_hidden_stack_refused(self):
        f1 = self.f(self.k, 1)
        regroup.hide_frame(f1)
        with self.assertRaises(ValueError):
            outlines.save(self.k, f1.id, SQUARE)
        regroup.apply_delete(self.a)
        self.a.refresh_from_db()
        with self.assertRaises(ValueError):
            outlines.save(self.a, self.f(self.a, 1).id, SQUARE)

    def test_delete(self):
        outlines.save(self.k, self.f(self.k, 1).id, SQUARE)
        outlines.delete(self.k)
        self.assertFalse(Outline.objects.exists())
        self.assertTrue(EditLog.objects.filter(action="outline_delete").exists())
        with self.assertRaises(ValueError):
            outlines.delete(self.k)

    def test_split_moves_outline_with_its_frame(self):
        outlines.save(self.k, self.f(self.k, 4).id, SQUARE)
        (new_id,) = regroup.apply_split(self.k, [self.f(self.k, 2).id])
        self.assertEqual(Outline.objects.get().stack_id, new_id)

    def test_merge_keeps_receivers_outline(self):
        outlines.save(self.k, self.f(self.k, 1).id, SQUARE)
        outlines.save(self.a, self.f(self.a, 1).id, [[0, 0], [40, 0], [40, 30]])
        regroup.apply_merge(self.k, self.a.id)
        self.assertEqual(Outline.objects.get(stack=self.k).area_px, 400)

    def test_merge_takes_others_outline_when_receiver_has_none(self):
        path = self.f(self.a, 1).path
        outlines.save(self.a, self.f(self.a, 1).id, SQUARE)
        regroup.apply_merge(self.k, self.a.id)
        self.assertEqual(Outline.objects.get(stack=self.k).frame_path, path)

    def test_numbers_in_mm_when_scale_fits(self):
        o = outlines.save(self.k, self.f(self.k, 1).id, SQUARE)
        self.assertEqual(dict(outlines.numbers(o, self.k)["rows"])["넓이"], "400 px²")
        scales.import_rows([{"path": self.f(self.k, 1).path, "status": "ok", "mm_per_px": "0.1",
                             "width": "40", "height": "30"}])
        self.k = Stack.objects.get(id=self.k.id)
        n = outlines.numbers(o, self.k)
        self.assertTrue(n["mm"])
        self.assertEqual(dict(n["rows"])["넓이"], "4.00 mm²")
        self.assertEqual(dict(n["rows"])["둘레"], "8.00 mm")


class OutlinePtmTest(SafeTestCase):
    def test_ptm_stack_takes_an_outline_and_rescan_keeps_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_stack(tmp, "SP-2016 샘플별/6D 외/PTM/SP-2016-52Z", "SP-2016-52Z")
            scan_ptm(root=tmp)
            st = Stack.objects.get(kind="ptm")
            outlines.save(st, st.frames.first().id, SQUARE)
            scan_ptm(root=tmp)
            self.assertEqual(Outline.objects.get().stack_id, st.id)


class OutlineViewTest(SafeTestCase):
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

    def test_post_saves_and_page_lays_it_only_on_same_size_frames(self):
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        make_jpg(self.root / MAIN / "SP-2016-47K-3.JPG", size=(60, 30))
        scan(root=self.root)
        k = Stack.objects.get(label="SP-2016-47K")
        url = reverse("outline", args=[k.id])
        r = self.client.post(url, {"frame": k.frames.get(shot_no=2).id, "points": json.dumps(SQUARE)})
        self.assertRedirects(r, reverse("stack", args=[k.id]), fetch_redirect_response=False)
        page = self.client.get(reverse("stack", args=[k.id]))
        self.assertEqual([(f["ol"], f["drawn"]) for f in self.payload(page)], [(True, False), (True, True), (False, False)])
        self.assertContains(page, "400 px²")
        self.assertContains(page, "맞춤 전이라 어긋날 수 있다")
        bad = self.client.post(url, {"frame": k.frames.get(shot_no=1).id, "points": "[[0,0]]"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(Outline.objects.get().frame_path.rsplit("/", 1)[-1], "SP-2016-47K-2.JPG")
        self.client.post(url, {"delete": "1"})
        self.assertFalse(Outline.objects.exists())

    def test_post_needs_csrf(self):
        shots(self.root, MAIN, "SP-2016-47A", [1, 2])
        scan(root=self.root)
        a = Stack.objects.get(label="SP-2016-47A")
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("outline", args=[a.id]), {"frame": a.frames.first().id, "points": json.dumps(SQUARE)})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Outline.objects.exists())
