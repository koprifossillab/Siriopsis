from core.tests.base import SafeTestCase
from specimens import catalog
from specimens.catalog import parse_list, sync
from specimens.models import Slab, Specimen

# phyloserver siriuspasset `specimen_list/?filter1=SP-2016-0052` 의 표 부분 (2026-10-25 화면에서 줄임).
# 이 꼴(칸 클래스·rowspan·슬랩 칸 안의 단추)이 바뀌면 catalog.py 도 고친다.
LIST_HTML = """
<table><tbody>
<tr><th class="col-slab"><div>Slab no.</div></th><th class="col-specimen"><div>Specimen no.</div></th></tr>
<tr class="specimen-row-even">
  <td class="slab-cell col-slab" rowspan="2">
    <a href="/siriuspasset/slab_detail/3242/">SP-2016-0052</a>
    <span class="badge badge-image-count" title="Slab-only images">2</span>
    <div class="mt-1"><a href="/siriuspasset/add_specimen/?slab_id=3242" class="btn">+ Add Specimen</a></div>
  </td>
  <td class="slab-cell col-horizon" rowspan="2">
      5.9-6.0
  </td>
  <td class="col-specimen"><a href="/siriuspasset/specimen_detail/7259/">SP-2016-0052-A</a></td>
  <td class="col-taxon">Kerygmachela</td>
  <td class="col-phylum">Stem arthropod</td>
  <td class="col-images"><span class="badge badge-image-count">176</span></td>
  <td class="slab-cell col-epma" rowspan="2"></td>
  <td class="col-remarks">eye recognizable</td>
</tr>
<tr class="specimen-row-odd">
  <td class="col-specimen"><a href="/siriuspasset/specimen_detail/7260/">SP-2016-0052-B</a></td>
  <td class="col-taxon">new vetulicolian</td>
  <td class="col-phylum">Stem deuterostome</td>
  <td class="col-images"><span class="badge badge-image-count">21</span></td>
  <td class="col-remarks"></td>
</tr>
</tbody></table>
"""


class ParseListTest(SafeTestCase):
    def test_rowspan_rows_belong_to_slab(self):
        slabs = parse_list(LIST_HTML)
        s = slabs["SP-2016-0052"]
        self.assertEqual((s["id"], s["horizon"]), (3242, "5.9-6.0"))
        self.assertEqual(set(s["specimens"]), {"SP-2016-0052-A", "SP-2016-0052-B"})
        a = s["specimens"]["SP-2016-0052-A"]
        self.assertEqual((a["id"], a["taxon_name"], a["phylum"], a["remarks"]),
                         (7259, "Kerygmachela", "Stem arthropod", "eye recognizable"))


class SyncTest(SafeTestCase):
    def test_fills_only_specimens_we_have(self):
        slab = Slab.objects.create(slab_no="SP-2016-0052", year=2016)
        Specimen.objects.create(slab=slab, letter="A")
        other = Slab.objects.create(slab_no="SP-2011-0203", year=2011)

        def fetch(no):
            return parse_list(LIST_HTML).get(no)

        found, missing, filled, errors = sync(fetch=fetch)
        self.assertEqual((found, missing, filled, errors), (1, 1, 1, []))
        a = Specimen.objects.get(letter="A")
        self.assertEqual((a.taxon_name, a.catalog_id), ("Kerygmachela", 7259))
        self.assertFalse(Specimen.objects.filter(letter="B").exists())   # 목록에만 있는 표본은 만들지 않는다
        slab.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((slab.catalog_id, slab.horizon), (3242, "5.9-6.0"))
        self.assertIsNone(other.catalog_id)
        self.assertIsNotNone(other.catalog_synced_at)

    def test_network_error_is_reported_not_raised(self):
        Slab.objects.create(slab_no="SP-2016-0052", year=2016)

        def fetch(no):
            raise OSError("연결 거부")

        found, missing, filled, errors = sync(fetch=fetch)
        self.assertEqual((found, len(errors)), (0, 1))

    def test_many_slabs_read_whole_list_once(self):
        for n in range(catalog.PAGE_WALK_OVER + 1):
            Slab.objects.create(slab_no=f"SP-2017-{n:04d}", year=2017)
        Slab.objects.create(slab_no="SP-2016-0052", year=2016)
        calls = []

        def everything(log=None):
            calls.append(1)
            return parse_list(LIST_HTML)

        found, missing, filled, errors = sync(fetch_everything=everything)
        self.assertEqual(len(calls), 1)
        self.assertEqual((found, missing), (1, catalog.PAGE_WALK_OVER + 1))

