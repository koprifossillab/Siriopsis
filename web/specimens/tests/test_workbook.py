"""엑셀 목록의 별표와 counterpart (wetherilli 013). 시험은 NAS 를 읽지 않는다 — 엑셀을 스스로 만든다."""
import os
import tempfile
from pathlib import Path

import openpyxl
from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import workbook
from specimens.models import Counterpart, Frame, Slab, Specimen, Stack, Star
from specimens.workbook import parse_counterpart, pick_files, together_slabs

# 실제 엑셀의 머리줄 꼴 — 2016 은 첫 칸이 비고 슬랩이 글자, 2017 은 슬랩이 수, 2022 는 첫 칸부터
HEAD_2016 = [None, "slab no.", "specimen no.", "taxon name", "phylum", "horizon", "remarks", "EPMA", "Counterpart?"]
HEAD_2017 = [None, "slab no.", "specimen no.", "taxon name", "phylum", "horizon", "remarks", "Counterpart?", "현명메모"]


def make_xlsx(path, head, rows, mtime=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(head)
    for r in rows:
        ws.append(r)
    wb.save(path)
    if mtime:
        os.utime(path, (mtime, mtime))


class ParseTest(SafeTestCase):
    def test_forms(self):
        p = parse_counterpart
        self.assertEqual(p("Counterpart of SP-2016-185, JV", 2016), ([("SP-2016-0185", "")], "ok"))
        self.assertEqual(p("Counterpart of 1318A", 2016), ([("SP-2016-1318", "A")], "ok"))
        self.assertEqual(p("Counter part of 1496 A", 2016), ([("SP-2016-1496", "A")], "ok"))
        self.assertEqual(p("JV conterpart of 548", 2016)[0], [("SP-2016-0548", "")])
        self.assertEqual(p("counterpart ot 965", 2016)[0], [("SP-2016-0965", "")])
        self.assertEqual(p("Counterpart to 2325A", 2017)[0], [("SP-2017-2325", "A")])
        self.assertEqual(p("Counterpart 008, JV", 2016)[0], [("SP-2016-0008", "")])
        self.assertEqual(p("counterpart 570 + 575 & 576 JV", 2016)[0],
                         [("SP-2016-0570", ""), ("SP-2016-0575", ""), ("SP-2016-0576", "")])   # 576 뒤의 JV 는 글자가 아니다
        self.assertEqual(p("Counter part of 1561D,2ea", 2016)[0], [("SP-2016-1561", "D")])
        self.assertEqual(p("Cephalon(Counter part of 441F)", 2016)[0], [("SP-2016-0441", "F")])
        self.assertEqual(p("Counterpart of", 2018), ([], "no_target"))
        self.assertEqual(p("level from counterpart", 2016), ([], "no_target"))
        self.assertEqual(p("enrolled, not counterpart of 564", 2016), ([], "negated"))
        self.assertEqual(p("JV", 2016), ([], None))

    def test_together(self):
        self.assertEqual(together_slabs("SP-2016-64&65"), ["SP-2016-0064", "SP-2016-0065"])
        self.assertEqual(together_slabs("SP-2016-71&70"), ["SP-2016-0071", "SP-2016-0070"])
        self.assertEqual(together_slabs("SP-2016-64&65(vent)"), ["SP-2016-0064", "SP-2016-0065"])
        self.assertEqual(together_slabs("SP-2016-64"), [])


class ReadTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self):
        # 옛 파일 — 이름 차례로는 앞이라, 날짜로 고르지 않으면 이것이 뽑힌다
        make_xlsx(self.root / "+2016_SP-2016_Catalog_compiled.xlsx", HEAD_2016,
                  [[None, "SP-2016-4", "A", "brachiopod", "", "SCREE", "☆", None, "Counterpart of SP-2016-5"]],
                  mtime=1_000_000)
        make_xlsx(self.root / "+Updated2025_SP-2016_Catalog.xlsx", HEAD_2016, [
            [None, "SP-2016-4", "A", "brachiopod", "", "SCREE", None, None, "Counterpart of SP-2016-5"],
            [None, "SP-2016-5", None, "brachiopod", "", "SCREE", "☆☆", None, "Counterpart of SP-2016-4"],
            [None, "SP-2016-3", "A", "Sirilorica", "", "~5.9", None, None, "CHECK: counterpart of 37?"],
            [None, "SP-2016-39", None, "x", "", "", None, None, "Counterpart of SP-2016-39"],
            [None, "SP-2016-6", "B", "Spaghetti", "", "", "much", None, "JV"],
        ], mtime=2_000_000)
        make_xlsx(self.root / "SP-2017_Catalog_editing.xlsx", HEAD_2017, [
            [None, 225, None, "Kerygmachela", "", "", None, "Conter part of 224A", None],
        ])
        (self.root / "~$SP-2017_Catalog_editing.xlsx").write_bytes(b"lock")

    def test_pick_newest_per_year(self):
        self.put()
        self.assertEqual({y: p.name for y, p in pick_files(self.root).items()},
                         {2016: "+Updated2025_SP-2016_Catalog.xlsx", 2017: "SP-2017_Catalog_editing.xlsx"})

    def test_sync_reads_stars_and_pairs(self):
        self.put()
        st = workbook.sync(self.root)
        self.assertEqual(st.errors, [])
        # 옛 파일(compiled)의 ☆ 는 읽지 않는다 — 연도마다 한 파일
        self.assertEqual([(s.specimen_no, s.stars) for s in Star.objects.all()], [("SP-2016-0005-A", 2)])
        got = sorted((c.slab_no, c.letter, c.other_slab_no, c.other_letter, c.uncertain) for c in Counterpart.objects.all())
        self.assertEqual(got, [
            ("SP-2016-0003", "A", "SP-2016-0037", "", True),
            ("SP-2016-0004", "A", "SP-2016-0005", "", False),
            ("SP-2016-0005", "", "SP-2016-0004", "", False),
            ("SP-2017-0225", "", "SP-2017-0224", "A", False),       # 2017 은 슬랩 칸이 수
        ])
        self.assertEqual(len(st.self_ref), 1)
        Counterpart.objects.create(origin="phyloserver", slab_no="SP-2016-0001", other_slab_no="SP-2016-0002",
                                   text="Counterpart of 2", source="SP-2016-0001-A", row=1)
        st = workbook.sync(self.root)                                   # 몇 번을 돌려도 같다
        self.assertEqual(Counterpart.objects.filter(origin="excel").count(), 4)
        self.assertEqual(Counterpart.objects.filter(origin="phyloserver").count(), 1)   # 엑셀 반입은 phyloserver 의 짝을 안 지운다

    def test_no_files_keeps_tables(self):
        Star.objects.create(slab_no="SP-2016-0005", letter="A", source="x", row=1)
        st = workbook.sync(self.root)
        self.assertTrue(st.errors)
        self.assertEqual(Star.objects.count(), 1)


def series(slab, specimen=None, label=None):
    st = Stack.objects.create(slab=slab, specimen=specimen, kind=Stack.Kind.SERIES, preparation="none", view="whole",
                              label=label or slab.slab_no, source_dir="d", n_frames=1)
    Frame.objects.create(stack=st, seq=0, path=f"d/{st.label}-1.JPG")
    return st


class ScreenTest(SafeTestCase):
    def setUp(self):
        self.s64 = Slab.objects.create(slab_no="SP-2016-0064", year=2016, horizon="SCREE")
        self.s65 = Slab.objects.create(slab_no="SP-2016-0065", year=2016)
        a = Specimen.objects.create(slab=self.s64, letter="A", taxon_name="Kerygmachela", remarks="☆")
        series(self.s64, a)
        series(self.s65)
        Counterpart.objects.create(slab_no="SP-2016-0064", letter="A", other_slab_no="SP-2016-0065",
                                   text="Counterpart of 65", source="f.xlsx", row=3)
        Star.objects.create(slab_no="SP-2016-0064", letter="A", stars=1, source="f.xlsx", row=3)
        Star.objects.create(slab_no="SP-2022-0275", letter="A", stars=2, taxon_name="Pauloterminus", source="g.xlsx", row=9)

    def test_starred_merges_sources(self):
        rows = {r["specimen_no"]: r for r in workbook.starred()}
        self.assertEqual(rows["SP-2016-0064-A"]["sources"], ["엑셀", "phyloserver"])
        self.assertEqual(rows["SP-2016-0064-A"]["taxon_name"], "Kerygmachela")
        self.assertIsNotNone(rows["SP-2016-0064-A"]["frame"])
        self.assertIsNone(rows["SP-2022-0275-A"]["slab"])                # 사진 없는 표본도 줄에
        self.assertEqual(rows["SP-2022-0275-A"]["marks"], "☆☆")
        r = self.client.get(reverse("starred"))
        self.assertContains(r, "SP-2022-0275-A")
        self.assertContains(r, reverse("starred"))                        # 머리줄 링크
        self.assertEqual(self.client.get(reverse("starred") + "?view=grid").status_code, 200)

    def test_pairs_seen_from_both_sides(self):
        for me, other in (("SP-2016-0064", "SP-2016-0065"), ("SP-2016-0065", "SP-2016-0064")):
            r = self.client.get(reverse("slab", args=[me]))
            got = r.context["counterparts"]
            self.assertEqual([g["other"] for g in got], [other])
            self.assertIsNotNone(got[0]["frame"])

    def test_two_slab_view_shows_on_both(self):
        for label in ("SP-2016-64&65", "SP-2016-64&65(vent)"):
            st = Stack.objects.create(slab=self.s64, kind=Stack.Kind.SLAB, preparation="none", view="whole",
                                      label=label, source_dir=label, n_frames=1)
            Frame.objects.create(stack=st, seq=0, path=f"{label}/x.JPG")
        r = self.client.get(reverse("slab", args=["SP-2016-0065"]))
        self.assertEqual(sorted(st.label for st in r.context["overview"]), ["SP-2016-64&65", "SP-2016-64&65(vent)"])
        self.assertEqual(len(r.context["counterparts"][0]["views"]), 2)

    def test_fragment_renders(self):
        from django.template.loader import render_to_string
        from specimens.views import _counterparts
        html = render_to_string("specimens/_counterpart.html", {"counterparts": _counterparts(self.s65)})
        self.assertIn(reverse("slab", args=["SP-2016-0064"]), html)
        self.assertIn("f.xlsx:3", html)
        self.assertEqual(render_to_string("specimens/_counterpart.html", {"counterparts": []}).strip(), "")


# phyloserver `export.json` 의 꼴 (요청서 NAS `Siriopsis/temp/20261025_request_phyloserver_json_export.md`). 빈 값은 null
EXPORT = {
    "generated_at": "2026-10-25T21:00:00+09:00",
    "slabs": [
        {"id": 10, "slab_no": "SP-2016-0064", "expedition_year": "2016", "horizon": "SCREE",
         "counterpart": "Counterpart of 65", "modified_on": None},
        {"id": 11, "slab_no": "SP-2016-0065", "expedition_year": "2016", "horizon": None, "counterpart": None, "modified_on": None},
    ],
    "specimens": [
        {"id": 100, "slab_id": 10, "specimen_no": "SP-2016-0064-A", "taxon_name": "Kerygmachela", "phylum": None,
         "remarks": "☆", "counterpart": "Counterpart of 66A", "modified_on": None},
        {"id": 101, "slab_id": 10, "specimen_no": "SP-2016-0064-B", "taxon_name": None, "phylum": None,
         "remarks": None, "counterpart": "JV", "modified_on": None},
    ],
}


class ExportTest(SafeTestCase):
    def setUp(self):
        self.s64 = Slab.objects.create(slab_no="SP-2016-0064", year=2016)
        Slab.objects.create(slab_no="SP-2016-0065", year=2016)
        Specimen.objects.create(slab=self.s64, letter="A")
        # 엑셀의 짝 — export 를 읽기 전에는 이것이 보이고, 읽은 뒤에는 phyloserver 의 것만
        Counterpart.objects.create(origin="excel", slab_no="SP-2016-0064", letter="A", other_slab_no="SP-2016-0065",
                                   text="Counterpart of 65", source="f.xlsx", row=3)
        Star.objects.create(slab_no="SP-2016-0064", letter="B", stars=1, source="f.xlsx", row=4)

    def test_parse_export(self):
        from specimens.catalog import parse_export
        d = parse_export(EXPORT)
        self.assertEqual(d["SP-2016-0064"]["specimens"]["SP-2016-0064-A"]["remarks"], "☆")
        self.assertEqual(d["SP-2016-0065"]["horizon"], "")                 # null → 빈 글자

    def test_export_first_then_excel_steps_aside(self):
        from specimens import catalog
        self.assertEqual([g["lines"][0]["origin"] for g in workbook.pairs_for("SP-2016-0064")], ["엑셀"])
        listing_called = []
        catalog.sync(fetch_whole=lambda log=None: catalog.parse_export(EXPORT),
                     fetch_everything=lambda log=None: listing_called.append(1) or {})
        self.assertEqual(listing_called, [])                                 # export 가 있으면 목록 화면을 안 읽는다
        self.s64.refresh_from_db()
        self.assertIsNotNone(self.s64.counterpart_synced_at)
        got = {g["other"]: [(l["mine"], l["theirs"], l["origin"]) for l in g["lines"]]
               for g in workbook.pairs_for("SP-2016-0064")}
        # 표본 칸의 짝(66A) + 표본 칸에 없는 슬랩 칸의 짝(65). 엑셀의 65 짝은 안 쓴다
        self.assertEqual(got, {"SP-2016-0065": [("", "", "phyloserver")],
                               "SP-2016-0066": [("A", "A", "phyloserver")]})
        # ☆: 목록에 있는 슬랩은 phyloserver remarks 만 — 엑셀의 64-B ☆ 는 안 쓴다
        self.assertEqual([(r["specimen_no"], r["sources"]) for r in workbook.starred()],
                         [("SP-2016-0064-A", ["phyloserver"])])
        catalog.sync(fetch_whole=lambda log=None: catalog.parse_export(EXPORT))   # 다시 돌려도 같다
        self.assertEqual(Counterpart.objects.filter(origin="phyloserver").count(), 2)

    def test_list_pages_keep_excel(self):
        from specimens import catalog

        def no_export(log=None):
            raise OSError("HTTP Error 404: Not Found")
        catalog.sync(fetch_whole=no_export, fetch=lambda no: catalog.parse_export(EXPORT).get(no) | {"from_export": False}
                     if no in ("SP-2016-0064", "SP-2016-0065") else None)
        self.assertEqual([g["lines"][0]["origin"] for g in workbook.pairs_for("SP-2016-0064")], ["엑셀"])
