from django.test import SimpleTestCase

from specimens.names import label_of, parse_stem


class ParseStemTest(SimpleTestCase):
    def test_letter_and_padding(self):
        p = parse_stem("SP-2016-52A")
        self.assertEqual((p["slab"], p["letter"], p["zoom"]), ("SP-2016-0052", "A", False))

    def test_trailing_z_is_zoom_not_letter(self):
        # Z 는 확대 촬영 표시다 (사용자 확인 2026-10-25) — 표본 글자로 읽으면 안 된다
        p = parse_stem("SP-2016-52Z")
        self.assertEqual((p["letter"], p["zoom"]), ("", True))
        p = parse_stem("SP-2016-494AZ")
        self.assertEqual((p["letter"], p["zoom"]), ("A", True))

    def test_lowercase_is_not_a_specimen_letter(self):
        p = parse_stem("SP-2011-0577aZ")
        self.assertEqual((p["slab"], p["letter"], p["lower"], p["zoom"]),
                         ("SP-2011-0577", "", "a", True))

    def test_not_a_name(self):
        self.assertIsNone(parse_stem("IMG_10095"))

    def test_label_drops_zoom(self):
        self.assertEqual(label_of("SP-2011-0577aZ"), "SP-2011-0577a")
        self.assertEqual(label_of("SP-2016-52A"), "SP-2016-52A")
