"""글자 없는 이름은 A 표본 (wetherilli 012)."""
import tempfile
from pathlib import Path

from django.utils import timezone

from core.tests.base import SafeTestCase
from specimens import bare, catalog
from specimens.lightseries import scan as scan_series
from specimens.lightstacks import scan as scan_ptm
from specimens.models import Slab, Specimen, Stack

from .fixtures import make_stack
from .test_lightseries import MAIN, shots


def listing(slab_no, letters, cid=100):
    """phyloserver 목록 한 슬랩 — parse_list 가 내는 꼴."""
    return {"id": cid, "horizon": "5.9", "specimens": {
        f"{slab_no}-{x}": {"id": cid + i, "taxon_name": f"taxon {x}", "phylum": "", "remarks": ""}
        for i, x in enumerate(letters)}}


class BareTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def sync(self, data):
        return catalog.sync(fetch=data.get)

    def test_is_bare(self):
        self.assertTrue(bare.is_bare("SP-2016-494"))
        self.assertFalse(bare.is_bare("SP-2016-494B"))
        self.assertFalse(bare.is_bare("SP-2011-0577a"))       # 소문자는 글자가 있는 것 — 규칙 밖
        self.assertFalse(bare.is_bare("SP-2016-64&65"))

    def test_catalog_sync_attaches_a_and_fills_it(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2, 3])
        scan_series(root=self.root)
        st = Stack.objects.get(label="SP-2016-47")
        self.assertIsNone(st.specimen)                      # phyloserver 를 읽기 전에는 모른다
        self.sync({"SP-2016-0047": listing("SP-2016-0047", "A")})
        st.refresh_from_db()
        self.assertEqual(st.specimen.specimen_no, "SP-2016-0047-A")
        self.assertEqual(st.specimen.taxon_name, "taxon A")  # 새로 생긴 A 도 같은 걸음에 채운다
        self.assertEqual(Slab.objects.get().catalog_letters, "A")

    def test_slab_not_in_catalog_is_a(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2])
        scan_series(root=self.root)
        self.sync({})
        self.assertEqual(Stack.objects.get().specimen.letter, "A")

    def test_other_letter_in_catalog_is_exception(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2])
        scan_series(root=self.root)
        self.sync({"SP-2016-0047": listing("SP-2016-0047", "AB")})
        self.assertIsNone(Stack.objects.get().specimen)
        self.assertEqual([r["slab"] for r in bare.exceptions()], ["SP-2016-0047"])
        self.assertFalse(Specimen.objects.filter(letter="A").exists())

    def test_other_letter_on_nas_is_exception(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2])
        shots(self.root, MAIN, "SP-2016-47K", [1, 2])
        scan_series(root=self.root)
        self.sync({})
        self.assertIsNone(Stack.objects.get(label="SP-2016-47").specimen)
        self.assertEqual(bare.exceptions()[0]["nas_letters"], "K")

    def test_rescan_after_sync_keeps_a_and_new_exception_detaches(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2])
        scan_series(root=self.root)
        self.sync({"SP-2016-0047": listing("SP-2016-0047", "A")})
        scan_series(root=self.root)
        self.assertEqual(Stack.objects.get().specimen.letter, "A")
        # 목록에 B 가 더해지면 「한 장」이 아니다 — 다시 읽을 때 뗀다
        self.sync({"SP-2016-0047": listing("SP-2016-0047", "AB")})
        self.assertIsNone(Stack.objects.get().specimen)

    def test_ptm_bare_name_goes_to_a(self):
        make_stack(self.root, "SP-2016 샘플별/6D 외/PTM/SP-2016-601Z", "SP-2016-601Z")
        scan_ptm(root=self.root)
        Slab.objects.update(catalog_synced_at=timezone.now())
        st = scan_ptm(root=self.root)                       # 다시 돌리기만으로 붙는다
        self.assertEqual(Stack.objects.get().specimen.specimen_no, "SP-2016-0601-A")
        self.assertEqual(st.bare["attached"], 1)

    def test_edited_stack_is_left_alone(self):
        shots(self.root, MAIN, "SP-2016-47", [1, 2])
        scan_series(root=self.root)
        Stack.objects.update(edited_at=timezone.now())
        self.sync({})
        self.assertIsNone(Stack.objects.get().specimen)

    def test_slab_view_is_not_a_specimen(self):
        slab = Slab.objects.create(slab_no="SP-2016-0047", year=2016, catalog_synced_at=timezone.now())
        Stack.objects.create(slab=slab, kind=Stack.Kind.SLAB, preparation="none", view="whole",
                             label="SP-2016-47", source_dir="x")
        bare.assign()
        self.assertIsNone(Stack.objects.get().specimen)
