"""EPMA — phyloserver 메타 반입과 파일 서빙, 화면 (wetherilli 018)."""
import gzip
import shutil
import struct
import tempfile
from pathlib import Path

from django.test import override_settings
from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import epma
from specimens.models import EpmaChannel, EpmaMap, EpmaSession, Slab, Specimen, Stack

REL = "SP/2017/2301-2400/SP-2017-2398/session_001/map_003"


def doc(json_form=True, sessions=None):
    """epma.json 꼴(`slab_id`…) 또는 dumpdata 꼴(`{"pk", "fields"}`)."""
    s = [{"id": 3, "slab_id": 11369, "specimen_id": 501, "session_number": 1, "session_label": "SP-2017-2398_0001_MAP_0003_csv",
          "source_directory": "SP-2017-2398_0001_MAP_0003_csv", "data_format": "csv", "instrument": "JXA8530",
          "accel_voltage": 15.0, "probe_current": None, "acquisition_date": "2024-11-24", "analyst": "", "description": "",
          "representative_channel_id": 23},
         {"id": 4, "slab_id": 99999, "specimen_id": None, "session_number": 2, "session_label": "elsewhere",
          "acquisition_date": None, "representative_channel_id": None}] if sessions is None else sessions
    m = [{"id": 3, "session_id": 3, "map_number": 3, "map_label": "m3", "pixel_width": 3, "pixel_height": 2},
         {"id": 5, "session_id": 4, "map_number": 1, "map_label": "m1"}]
    c = [{"id": 22, "epma_map_id": 3, "element": "Cl", "line": "Ka", "method": "EDS", "channel_number": 8,
          "image_file": f"{REL}/images/Cl.jpg", "binary_data_file": f"{REL}/data/Cl.bin.gz", "is_special": False},
         {"id": 23, "epma_map_id": 3, "element": "SEI", "line": "", "method": "", "image_file": f"{REL}/images/SEI.jpg",
          "binary_data_file": "", "is_special": True},
         {"id": 24, "epma_map_id": 5, "element": "Fe", "image_file": "", "binary_data_file": ""}]
    if json_form:
        return {"sessions": s, "maps": m, "channels": c}

    def dump(rows, refs):
        out = []
        for r in rows:
            f = {(k[:-3] if k in refs else k): v for k, v in r.items() if k != "id"}
            out.append({"model": "x", "pk": r["id"], "fields": f})
        return out
    return {"sessions": dump(s, {"slab_id", "specimen_id", "representative_channel_id"}),
            "maps": dump(m, {"session_id"}), "channels": dump(c, {"epma_map_id"})}


class SyncTest(SafeTestCase):
    def setUp(self):
        self.slab = Slab.objects.create(slab_no="SP-2017-2398", year=2017, catalog_id=11369)
        self.sp = Specimen.objects.create(slab=self.slab, letter="A", catalog_id=501)

    def test_both_forms_same(self):
        for form in (True, False):
            st = epma.sync(epma.parse(doc(form)))
            self.assertEqual((st.sessions, st.maps, st.channels, st.linked, len(st.no_slab)), (2, 2, 3, 1, 1), form)
            s = EpmaSession.objects.get(catalog_id=3)
            self.assertEqual((s.slab, s.specimen, s.representative_catalog_id, str(s.acquisition_date)),
                             (self.slab, self.sp, 23, "2024-11-24"))
            self.assertEqual(EpmaChannel.objects.get(catalog_id=22).map.session, s)
            self.assertIsNone(EpmaSession.objects.get(catalog_id=4).slab)     # 테이블에 없는 슬랩 — id 만 남긴다
            self.assertEqual(EpmaSession.objects.get(catalog_id=4).slab_catalog_id, 99999)

    def test_resync_removes_gone_and_empty_keeps(self):
        epma.sync(epma.parse(doc()))
        d = doc()
        d["sessions"] = d["sessions"][:1]
        d["maps"] = d["maps"][:1]
        d["channels"] = d["channels"][:1]
        st = epma.sync(epma.parse(d))
        self.assertEqual(st.removed, 4)                                       # 채널 23·24 · 맵 5 · 세션 4
        self.assertEqual(sorted(EpmaChannel.objects.values_list("catalog_id", flat=True)), [22])
        st = epma.sync(epma.parse({"sessions": [], "maps": [], "channels": []}))
        self.assertTrue(st.errors)
        self.assertEqual(EpmaSession.objects.count(), 1)                      # 빈 것을 받으면 지우지 않는다

    def test_relink_after_catalog(self):
        epma.sync(epma.parse(doc()))
        other = Slab.objects.create(slab_no="SP-2018-0001", year=2018)
        self.assertEqual(epma.relink(), 0)
        other.catalog_id = 99999
        other.save()
        self.assertEqual(epma.relink(), 1)
        self.assertEqual(EpmaSession.objects.get(catalog_id=4).slab, other)

    def test_load_dump(self):
        import json
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "models").mkdir()
        d = doc(False)
        for key, name in (("sessions", "SpEpmaSession"), ("maps", "SpEpmaMap"), ("channels", "SpEpmaChannel")):
            (tmp / "models" / f"{name}.json").write_text(json.dumps(d[key]))
        self.assertEqual(epma.sync(epma.load_dump(tmp)).channels, 3)


class ScreenTest(SafeTestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / REL / "images" / ".thumbnails").mkdir(parents=True)
        (self.root / REL / "data").mkdir(parents=True)
        (self.root / REL / "images" / "Cl.jpg").write_bytes(b"\xff\xd8full")
        (self.root / REL / "images" / ".thumbnails" / "Cl.jpg").write_bytes(b"\xff\xd8thumb")
        (self.root / REL / "images" / "SEI.jpg").write_bytes(b"\xff\xd8sei")      # 썸네일 없음 → 이미지 그대로
        raw = struct.pack("<HH", 3, 2) + struct.pack("<6H", 0, 1, 2, 3, 4, 500)
        (self.root / REL / "data" / "Cl.bin.gz").write_bytes(gzip.compress(raw))
        (self.root.parent / "outside.jpg").write_bytes(b"secret")
        self.addCleanup((self.root.parent / "outside.jpg").unlink)
        self.slab = Slab.objects.create(slab_no="SP-2017-2398", year=2017, catalog_id=11369)
        Specimen.objects.create(slab=self.slab, letter="A", catalog_id=501)
        epma.sync(epma.parse(doc()))
        self.cl = EpmaChannel.objects.get(catalog_id=22)
        self.sei = EpmaChannel.objects.get(catalog_id=23)
        self.enterContext(override_settings(EPMA_ROOT=str(self.root)))

    def test_files(self):
        r = self.client.get(reverse("epma_data", args=[self.cl.id]))
        self.assertEqual(r["Content-Type"], "application/octet-stream")
        self.assertFalse(r.has_header("Content-Encoding"))                   # 브라우저가 스스로 풀지 않게 — 뷰어가 푼다
        body = b"".join(r.streaming_content)
        self.assertEqual(struct.unpack("<HH", gzip.decompress(body)[:4]), (3, 2))
        thumb = self.client.get(reverse("epma_image", args=[self.cl.id]) + "?thumb=1")
        self.assertEqual(b"".join(thumb.streaming_content), b"\xff\xd8thumb")
        full = self.client.get(reverse("epma_image", args=[self.cl.id]))
        self.assertEqual(b"".join(full.streaming_content), b"\xff\xd8full")
        sei = self.client.get(reverse("epma_image", args=[self.sei.id]) + "?thumb=1")
        self.assertEqual(b"".join(sei.streaming_content), b"\xff\xd8sei")
        self.assertEqual(self.client.get(reverse("epma_data", args=[self.sei.id])).status_code, 404)   # 강도 파일 없음

    def test_outside_root_refused(self):
        EpmaChannel.objects.filter(pk=self.cl.pk).update(image_file="../outside.jpg")
        self.assertEqual(self.client.get(reverse("epma_image", args=[self.cl.id])).status_code, 404)
        EpmaChannel.objects.filter(pk=self.cl.pk).update(image_file=str(self.root.parent / "outside.jpg"))
        self.assertEqual(self.client.get(reverse("epma_image", args=[self.cl.id])).status_code, 404)

    def test_slab_and_session_pages(self):
        r = self.client.get(reverse("slab", args=["SP-2017-2398"]))
        s = EpmaSession.objects.get(catalog_id=3)
        # 빛 묶음·PTM 과 나란히 — 표본 칸 안의 카드 (사용자 2026-10-26). 더미가 없는 표본이라도 칸이 선다
        [g] = r.context["groups"]
        self.assertEqual((g["specimen"].letter, g["stacks"], [e.id for e in g["epma"]]), ("A", [], [s.id]))
        self.assertEqual(g["epma"][0].rep, self.sei)                          # phyloserver 의 대표 채널
        self.assertEqual((g["epma"][0].n_maps, g["epma"][0].n_channels), (1, 2))
        self.assertEqual(r.context["loose_epma"], [])
        self.assertEqual(r.context["facts"]["n_epma"], 1)
        self.assertContains(r, reverse("epma_session", args=[s.id]))
        EpmaSession.objects.filter(pk=s.pk).update(specimen=None)              # 표본이 안 정해지면 「표본 글자 없음」 칸
        r = self.client.get(reverse("slab", args=["SP-2017-2398"]))
        self.assertEqual((r.context["groups"], [e.id for e in r.context["loose_epma"]]), ([], [s.id]))
        self.assertContains(r, "표본 글자 없음")
        EpmaSession.objects.filter(pk=s.pk).update(specimen=Specimen.objects.get(catalog_id=501))
        r = self.client.get(reverse("epma_session", args=[s.id]))
        self.assertEqual(r.context["cur"], self.sei)                          # 대표부터
        self.assertNotContains(r, 'id="cv"')                                  # 강도 파일이 없으면 이미지로
        r = self.client.get(reverse("epma_session", args=[s.id]) + f"?c={self.cl.id}")
        self.assertEqual(r.context["cur"], self.cl)
        self.assertContains(r, reverse("epma_data", args=[self.cl.id]))
        other = EpmaChannel.objects.get(catalog_id=24)                       # 다른 세션의 채널은 고를 수 없다
        self.assertEqual(self.client.get(reverse("epma_session", args=[s.id]) + f"?c={other.id}").context["cur"], self.sei)
        lone = EpmaSession.objects.get(catalog_id=4)
        self.assertContains(self.client.get(reverse("epma_session", args=[lone.id])), "테이블에 없음")

    def test_no_representative_falls_back(self):
        EpmaSession.objects.filter(catalog_id=3).update(representative_catalog_id=None)
        s = EpmaSession.objects.get(catalog_id=3)
        epma.representative([s])
        self.assertEqual(s.rep, self.sei)                                     # 특수 채널(SEI) 먼저

    def test_list_column_and_kind(self):
        """목록의 EPMA 열과 종류 거르기 — 더미가 없는 슬랩도 EPMA 가 있으면 목록에 든다."""
        Slab.objects.create(slab_no="SP-2017-0001", year=2017)                # 아무것도 없는 슬랩 — 목록에 안 든다
        lit = Slab.objects.create(slab_no="SP-2017-0002", year=2017)          # 빛 묶음만 있는 슬랩
        Stack.objects.create(slab=lit, kind=Stack.Kind.SERIES, preparation="none", view="whole", label="x", source_dir="x", n_frames=2)
        r = self.client.get(reverse("home") + "?y=2017")
        rows = {x["slab"].slab_no: x for g in r.context["groups"] for x in g["rows"]}
        self.assertEqual(list(rows), ["SP-2017-0002", "SP-2017-2398"])
        self.assertEqual((rows["SP-2017-2398"]["epma"], r.context["sums"]["epma"]), (1, 1))
        self.assertContains(r, '<th class="n">EPMA</th>')
        self.assertIn((2017, 2), r.context["years"])
        r = self.client.get(reverse("home") + "?y=2017&kind=epma")
        self.assertEqual([x["slab"].slab_no for g in r.context["groups"] for x in g["rows"]], ["SP-2017-2398"])
        r = self.client.get(reverse("home") + "?y=2017&kind=series")
        self.assertEqual([x["slab"].slab_no for g in r.context["groups"] for x in g["rows"]], ["SP-2017-0002"])
        r = self.client.get(reverse("home") + "?y=2017&view=grid")
        self.assertContains(r, "EPMA 1")
