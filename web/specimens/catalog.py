"""phyloserver `siriuspasset` 의 슬랩·표본 목록에서 분류 정보를 읽어 온다 (wetherilli 002).

**분류 정보의 원천은 phyloserver 다** — 연구실이 그쪽 화면에서 분류군·비고를 고쳐 가고(엑셀은 그 옛 사본),
사진 수·EPMA 도 거기 붙어 있다. 사용자가 「같이 참고」하라고 했다(2026-10-25).
JSON API 가 없어 목록 화면(`specimen_list/?filter1=<슬랩>`)의 표를 읽는다. 칸마다 `col-slab`·`col-specimen`·
`col-taxon` … 클래스가 붙어 있어 그것으로 가른다 — **그 화면의 칸 이름이 바뀌면 여기가 깨진다**
(시험 `test_catalog` 가 그 꼴을 픽스처로 들고 있다).

읽기만 한다. **지금 테이블에 있는 슬랩만** 묻는다 — 4천 슬랩을 다 가져오지 않는다.
"""
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Slab, Specimen

_COLS = ("col-slab", "col-horizon", "col-specimen", "col-taxon", "col-phylum", "col-remarks")


class _ListParser(HTMLParser):
    """목록 화면의 <td class="… col-xxx"> 를 행마다 모은다. 링크 href 도 같이."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._col = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self._row = {}
        elif tag == "td" and self._row is not None:
            classes = (a.get("class") or "").split()
            self._col = next((c for c in classes if c in _COLS), None)
            self._text = []
        elif tag == "a" and self._col and "href" in a and f"{self._col}_href" not in self._row:
            self._row[f"{self._col}_href"] = a["href"]

    def handle_endtag(self, tag):
        if tag == "td" and self._col:
            # 슬랩 칸에는 「+ Add Specimen」 단추와 사진 수 표시가 같이 들어 있다 — 첫 낱말만
            text = " ".join("".join(self._text).split())
            self._row[self._col] = text.split()[0] if self._col == "col-slab" and text else text
            self._col = None
        elif tag == "tr" and self._row is not None:
            if "col-specimen" in self._row or "col-slab" in self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._col:
            self._text.append(data)


def _id_from(href):
    """`/siriuspasset/specimen_detail/7259/` → 7259."""
    try:
        return int(href.rstrip("/").rsplit("/", 1)[-1])
    except (AttributeError, ValueError):
        return None


def parse_list(html):
    """목록 화면 HTML → {슬랩: {"id", "horizon", "specimens": {표본 번호: {...}}}}.

    슬랩 칸은 rowspan 으로 첫 행에만 있다 — 다음 행들은 앞 슬랩의 것이다.
    """
    p = _ListParser()
    p.feed(html)
    slabs = {}
    cur = None
    for r in p.rows:
        if r.get("col-slab"):
            cur = slabs.setdefault(r["col-slab"], {
                "id": _id_from(r.get("col-slab_href")),
                "horizon": r.get("col-horizon", ""),
                "specimens": {},
            })
        if cur is not None and r.get("col-specimen"):
            cur["specimens"][r["col-specimen"]] = {
                "id": _id_from(r.get("col-specimen_href")),
                "taxon_name": r.get("col-taxon", ""),
                "phylum": r.get("col-phylum", ""),
                "remarks": r.get("col-remarks", ""),
            }
    return slabs


def fetch_slab(slab_no, base=None, timeout=20):
    base = (base or settings.CATALOG_URL).rstrip("/") + "/"
    url = base + "specimen_list/?" + urllib.parse.urlencode({"filter1": slab_no})
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    return parse_list(html).get(slab_no)


def fetch_all(base=None, timeout=20, delay=0.3, log=None, max_pages=1000):
    """목록을 쪽마다 넘기며 모두 읽는다 (쪽마다 슬랩 20). 슬랩이 많을 때 슬랩마다 묻는 것보다 요청이 스무 배 적다.

    마지막 쪽 뒤를 물으면 phyloserver(Django Paginator.get_page)는 마지막 쪽을 다시 준다 —
    새 슬랩이 없는 쪽이 나오면 끝이다. 남의 운영 서비스라 요청 사이를 띄운다.
    """
    import time
    base = (base or settings.CATALOG_URL).rstrip("/") + "/"
    out = {}
    for page in range(1, max_pages + 1):
        url = base + "specimen_list/?" + urllib.parse.urlencode({"page": page})
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            got = parse_list(resp.read().decode("utf-8", errors="replace"))
        new = set(got) - set(out)
        if not new:
            break
        out.update(got)
        if log and page % 50 == 0:
            log(f"목록 {page} 쪽 · 슬랩 {len(out)}")
        time.sleep(delay)
    return out


@transaction.atomic
def apply_slab(slab, data, now=None):
    """한 슬랩의 목록 값을 테이블에 옮긴다. 목록에 없는 표본은 만들지 않는다 — 우리가 가진 표본만 채운다.

    목록에 슬랩이 없으면(`data` None) 아무것도 지우지 않고 catalog_id 만 비운다.
    돌려주는 값: 채운 표본 수.
    """
    slab.catalog_synced_at = now or timezone.now()
    if not data:
        slab.catalog_id = None
        slab.save()
        return 0
    slab.catalog_id = data["id"]
    slab.horizon = data["horizon"]
    slab.save()
    n = 0
    for sp in slab.specimens.all():
        row = data["specimens"].get(sp.specimen_no)
        if not row:
            continue
        sp.catalog_id = row["id"]
        sp.taxon_name = row["taxon_name"]
        sp.phylum = row["phylum"]
        sp.remarks = row["remarks"]
        sp.save()
        n += 1
    return n


# 슬랩이 이보다 많으면 목록 전체를 쪽마다 읽는다 (fetch_all)
PAGE_WALK_OVER = 30


def sync(slabs=None, fetch=None, log=None, fetch_everything=fetch_all):
    """테이블의 슬랩마다 목록 값을 채운다. 돌려주는 값: (찾은 슬랩, 못 찾은 슬랩, 채운 표본, 오류 목록).

    슬랩이 적으면 슬랩마다 묻고(fetch_slab), 많으면 목록 전체를 한 번 읽는다(fetch_all).
    """
    slabs = list(slabs if slabs is not None else Slab.objects.all())
    found = missing = filled = 0
    errors = []
    if fetch is None:
        if len(slabs) > PAGE_WALK_OVER:
            try:
                everything = fetch_everything(log=log)
            except OSError as e:
                return 0, 0, 0, [f"목록 전체: {e}"]
            fetch = everything.get
        else:
            fetch = fetch_slab
    for slab in slabs:
        try:
            data = fetch(slab.slab_no)
        except OSError as e:
            errors.append(f"{slab.slab_no}: {e}")
            continue
        filled += apply_slab(slab, data)
        if data:
            found += 1
        else:
            missing += 1
            if log:
                log(f"목록에 없음: {slab.slab_no}")
    return found, missing, filled, errors
