"""자에서 배율 재기 — 그린 자로 시험한다 (wetherilli 010). **NAS 원본을 읽지 않는다.**

    python -m unittest discover -s pipeline/tests -t .
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from pipeline import ruler_scale as rs


def photo(px_per_mm, size=(3000, 2000), ruler=True, at="top", tick_w=None, seed=0, rock=110):
    """돌 바탕에 흰 종이 자(1 mm 눈금, 5 mm·10 mm 는 길게)를 그린 사진 → PIL 그림."""
    rng = np.random.default_rng(seed)
    w, h = size
    base = rng.normal(rock, 22, (h, w)).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(np.stack([base, base, (base * 0.92).astype(np.uint8)], -1)).filter(ImageFilter.GaussianBlur(1.2))
    if not ruler:
        return im
    d = ImageDraw.Draw(im)
    tw = tick_w or max(2, round(px_per_mm * 0.12))
    if at == "top":
        # 크게 찍은 사진에는 자의 띠 일부만 든다 — 띠의 높이를 사진에 맞춰 줄인다
        x0, y0, x1, y1 = 300, 40, w - 300, 40 + min(int(px_per_mm * 9), 420)
        d.rectangle([x0, y0, x1, y1], fill=(238, 236, 228))
        k, x = 0, x0 + px_per_mm * 0.7
        while x < x1 - 4:
            L = min(px_per_mm * (5 if k % 10 == 0 else 3.6 if k % 5 == 0 else 2.4), (y1 - y0) * (0.8 if k % 5 else 0.95))
            d.rectangle([round(x - tw / 2), y1 - L, round(x + tw / 2), y1 - 1], fill=(25, 25, 25))
            x += px_per_mm
            k += 1
    else:      # 왼쪽 가장자리에 세운 자
        x0, y0, x1, y1 = 0, 200, int(px_per_mm * 8), h - 200
        d.rectangle([x0, y0, x1, y1], fill=(240, 240, 236))
        k, y = 0, y0 + px_per_mm * 0.7
        while y < y1 - 4:
            L = px_per_mm * (5 if k % 10 == 0 else 3.6 if k % 5 == 0 else 2.4)
            d.rectangle([x1 - L, round(y - tw / 2), x1 - 1, round(y + tw / 2)], fill=(25, 25, 25))
            y += px_per_mm
            k += 1
    return im


class RulerScaleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def measure(self, im, name="a.jpg"):
        p = self.dir / name
        im.save(p, quality=90)
        rs.SOURCE_ROOT = str(self.dir)
        return rs.measure(name)

    def test_horizontal_ruler(self):
        for ppm in (21.7, 48.3, 96.1):
            r = self.measure(photo(ppm))
            self.assertEqual(r["status"], "ok", (ppm, r))
            self.assertAlmostEqual(r["px_per_mm"] / ppm, 1, delta=0.004, msg=(ppm, r))
            self.assertAlmostEqual(r["mm_per_px"] * ppm, 1, delta=0.004)

    def test_vertical_ruler(self):
        r = self.measure(photo(63.4, at="left"))
        self.assertEqual(r["status"], "ok", r)
        self.assertAlmostEqual(r["px_per_mm"] / 63.4, 1, delta=0.004, msg=r)

    def test_thin_ticks_are_not_read_as_half_millimetres(self):
        # 가는 눈금은 FFT 의 둘째 배음이 바탕보다 세다 — 반 주기로 읽으면 두 배 값이 나온다
        r = self.measure(photo(150.0, tick_w=4))
        self.assertAlmostEqual(r["px_per_mm"] / 150.0, 1, delta=0.004, msg=r)

    def test_no_ruler_is_none_or_doubt_never_ok(self):
        for seed in range(3):
            r = self.measure(photo(50, ruler=False, seed=seed), f"n{seed}.jpg")
            self.assertNotEqual(r["status"], "ok", r)

    def test_unreadable_file(self):
        (self.dir / "bad.jpg").write_bytes(b"not a jpeg")
        rs.SOURCE_ROOT = str(self.dir)
        r = rs.measure("bad.jpg")
        self.assertEqual(r["status"], "none")
        self.assertIn("못 읽음", r["note"])


if __name__ == "__main__":
    unittest.main()
