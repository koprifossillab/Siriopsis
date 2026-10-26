"""NAS 의 엑셀 목록(`SP-*_Catalog*.xlsx`)에서 별표와 counterpart 짝을 읽는다 (wetherilli 013).

**원천은 phyloserver 다**(CLAUDE.md). 엑셀은 **phyloserver 에서 얻지 못한 곳만 메운다** — 화면이 고른다:
- **별표(☆)** — 연구에 쓰기 좋은 표본(사용자). phyloserver 목록의 remarks(`Specimen.remarks`)가 먼저다.
  엑셀의 ☆ 는 phyloserver 목록에 없는 슬랩만 쓴다(`starred`). 2026-10-25: phyloserver 43, 엑셀 62 — phyloserver 의 것은 모두 엑셀에도 있고,
  엑셀에만 있는 19 가운데 17 은 목록에 슬랩이 없다(SP-2022-0165 …). 나머지 둘(`SP-2022-0120-C`·`0129-A`)은 phyloserver 를 따라 별표가 아니다
- **counterpart** — phyloserver 는 목록 화면에 이 칸을 내지 않는다. `export.json`(`catalog.fetch_export`)이 생기면 `import_catalog` 가 거기서 읽고
  그 슬랩에 `counterpart_synced_at` 을 적는다. 그 표시가 없는 슬랩만 엑셀의 짝을 쓴다(`pairs_for`). 행마다 출처(`origin`)가 남는다

엑셀은 연도마다 한 파일 — 이름의 `SP-<연도>` 가 같은 것이 여럿이면 고친 날짜가 가장 늦은 것(`pick_files`).
칸은 머리줄의 이름(`slab no.`·`specimen no.`·…)으로 찾는다 — 연도마다 칸 자리가 다르다. 슬랩 칸은 `SP-2016-1` 글자이거나 `1` 수다.
**원본은 읽기만 한다**(read_only). `Star` 와 엑셀에서 온 `Counterpart` 는 읽은 것으로 통째로 다시 만든다 — 사람이 고치는 값이 없다.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Counterpart, Slab, Specimen, Star, Stack
from .names import slab_no as fmt_slab

STAR_CHARS = "☆★"
_YEAR = re.compile(r"SP-(\d{4})")

# counterpart 낱말 — 손으로 적어 꼴이 여럿이다: Counterpart · counter part · counterpar · Counter par · conterpart · Conter part
_WORD = re.compile(r"co(?:u)?nter\s*-?\s*par(?:t)?(?:\s+piece)?", re.IGNORECASE)
# 낱말 뒤의 연결(of · ot · to)과 대상들. 대상은 `(SP-2016-)185`·`1318A`·`1496 A`, 사이는 `,`·`&`·`+`·`and`
_TARGET = r"(?:SP-(?P<y{i}>\d{{4}})-)?(?P<n{i}>\d+)(?:\s?(?P<l{i}>[A-Z])(?![A-Za-z]))?(?![A-Za-z\d])"
_ONE = re.compile(_TARGET.format(i=""))
_LEAD = re.compile(r"^\s*(?:of|ot|to)?\s*", re.IGNORECASE)
_SEP = re.compile(r"^\s*(?:,|&|\+|and\b)\s*", re.IGNORECASE)
# 불확실 — 번호 바로 뒤의 「?」(`of 37?`)·maybe·probable·CHECK. 괄호 안 분류군의 「?」(`(?Chalazoscolex TF)`)는 짝의 것이 아니다
_UNSURE = re.compile(r"\d\s?[A-Z]?\s*\?|maybe|probabl|check", re.IGNORECASE)
_NOT = re.compile(r"\bnot\s+$", re.IGNORECASE)


@dataclass
class WorkbookStats:
    files: list = field(default_factory=list)
    rows: int = 0
    stars: int = 0
    mentions: int = 0           # counterpart 낱말이 든 칸
    pairs: int = 0              # 읽은 짝 (한 칸에 여럿일 수 있다)
    no_target: list = field(default_factory=list)     # 낱말은 있는데 번호가 없다 (「level from counterpart」·「Counterpart of」)
    negated: list = field(default_factory=list)       # 「not counterpart of」
    self_ref: list = field(default_factory=list)      # 제 슬랩·제 글자를 가리킨다 (적은 이의 잘못)
    uncertain: int = 0
    errors: list = field(default_factory=list)


def pick_files(root):
    """{연도: 경로} — 연도마다 고친 날짜가 가장 늦은 엑셀 하나. 엑셀이 열려 있을 때의 잠금 파일(`~$…`)은 뺀다."""
    best = {}
    for p in sorted(Path(root).glob("*.xlsx")):
        m = _YEAR.search(p.name)
        if p.name.startswith("~$") or not m:
            continue
        y = int(m[1])
        if y not in best or p.stat().st_mtime > best[y].stat().st_mtime:
            best[y] = p
    return dict(sorted(best.items()))


def parse_counterpart(text, year):
    """칸의 글 → ([(슬랩, 글자), …], 상태). 상태는 'ok' · 'no_target' · 'negated' · None(낱말 없음)."""
    m = _WORD.search(text)
    if not m:
        return [], None
    if _NOT.search(text[:m.start()]):
        return [], "negated"
    rest = _LEAD.sub("", text[m.end():], count=1)
    out = []
    while True:
        t = _ONE.match(rest)
        if not t:
            break
        y = int(t["y"]) if t["y"] else year
        out.append((fmt_slab(y, t["n"]), t["l"] or ""))
        rest = rest[t.end():]
        s = _SEP.match(rest)
        if not s:
            break
        rest = rest[s.end():]
    return out, ("ok" if out else "no_target")


def _rows(path):
    """엑셀 첫 장 → [(행 번호, {머리 이름: 값})]. 머리줄은 `slab no.` 가 든 첫 줄."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        it = wb.worksheets[0].iter_rows(values_only=True)
        head = None
        for i, r in enumerate(it, start=1):
            if head is None:
                names = [str(v).strip().lower() if v is not None else "" for v in r]
                if "slab no." in names:
                    head = names
                continue
            yield i, dict(zip(head, r))
    finally:
        wb.close()


def _slab_of(value, year):
    """`SP-2016-1` · `1` · `1.0` → `SP-2016-0001`. 못 읽으면 None."""
    if value is None:
        return None
    s = str(value).strip()
    m = re.fullmatch(r"(?:SP-(\d{4})-)?(\d+)(?:\.0)?", s)
    if not m:
        return None
    return fmt_slab(int(m[1]) if m[1] else year, m[2])


def _letter_of(value):
    s = str(value or "").strip()
    return s if re.fullmatch(r"[A-Z]", s) else ""


def read(root=None):
    """엑셀을 읽어 (별표 행, 짝 행, 통계). 테이블에 넣지 않는다."""
    root = Path(root or settings.SOURCE_ROOT)
    st = WorkbookStats()
    stars, pairs = [], []
    for year, path in pick_files(root).items():
        st.files.append(path.name)
        try:
            rows = list(_rows(path))
        except Exception as e:          # 깨진 파일 하나가 나머지를 막지 않게
            st.errors.append(f"{path.name}: {e}")
            continue
        for i, r in rows:
            slab = _slab_of(r.get("slab no."), year)
            if not slab:
                continue
            st.rows += 1
            letter = _letter_of(r.get("specimen no."))
            where = f"{path.name}:{i}"
            n_star, star_text = 0, ""
            for k, v in r.items():
                if not isinstance(v, str) or k in ("taxon name", "phylum"):
                    continue
                c = sum(v.count(ch) for ch in STAR_CHARS)
                if c > n_star:
                    n_star, star_text = c, v.strip()
                found, state = parse_counterpart(v, year)
                if state is None:
                    continue
                st.mentions += 1
                if state == "no_target":
                    st.no_target.append(f"{where} {slab} {v!r}")
                    continue
                if state == "negated":
                    st.negated.append(f"{where} {slab} {v!r}")
                    continue
                unsure = bool(_UNSURE.search(v))
                for o_slab, o_letter in found:
                    if o_slab == slab and o_letter == letter:
                        st.self_ref.append(f"{where} {slab}{letter} {v!r}")
                        continue
                    pairs.append(Counterpart(origin=Counterpart.Origin.EXCEL, slab_no=slab, letter=letter, other_slab_no=o_slab, other_letter=o_letter,
                                             uncertain=unsure, text=v.strip()[:300], source=path.name, row=i))
                    st.uncertain += unsure
            if n_star:
                stars.append(Star(slab_no=slab, letter=letter or "A", stars=n_star, text=star_text[:300],
                                  taxon_name=str(r.get("taxon name") or "").strip()[:100],
                                  horizon=str(r.get("horizon") or "").strip()[:100], source=path.name, row=i))
    st.stars, st.pairs = len(stars), len(pairs)
    return stars, pairs, st


@transaction.atomic
def save(stars, pairs):
    """엑셀에서 온 것만 다시 만든다 — phyloserver 의 짝(`import_catalog`)은 건드리지 않는다."""
    Star.objects.all().delete()
    Counterpart.objects.filter(origin=Counterpart.Origin.EXCEL).delete()
    Star.objects.bulk_create(stars)
    Counterpart.objects.bulk_create(pairs)


def sync(root=None):
    stars, pairs, st = read(root)
    if not st.files:
        # NAS 가 안 붙었을 때 「아무것도 없다」로 읽으면 테이블을 비운다
        st.errors.append(f"엑셀을 하나도 못 찾았다: {root or settings.SOURCE_ROOT} — 지우지 않고 멈춘다")
        return st
    if st.errors:
        st.errors.append("못 읽은 파일이 있어 테이블을 그대로 둔다")
        return st
    save(stars, pairs)
    return st


# ── 화면에 내는 값 ─────────────────────────────────────

def starred():
    """별표 표본 — phyloserver remarks 의 ☆, 그리고 phyloserver 목록에 없는 슬랩은 엑셀(`Star`)의 것. 표본 번호 차례의 dict 목록.

    `sources` 에 어디서 왔는지를 적는다. 둘 다 있으면 둘 다 — 엑셀의 ☆ 는 목록에 없는 슬랩만 읽으므로 지금은 겹치지 않는다.
    """
    out = {}
    # phyloserver 목록에 있는 슬랩은 그쪽 remarks 의 ☆ 가 원천이다 — 엑셀의 것은 목록에 없는 슬랩만 메운다
    in_catalog = set(Slab.objects.filter(catalog_id__isnull=False).values_list("slab_no", flat=True))
    for s in Star.objects.exclude(slab_no__in=in_catalog):
        out[s.specimen_no] = {"specimen_no": s.specimen_no, "slab_no": s.slab_no, "letter": s.letter,
                              "stars": s.stars, "sources": ["엑셀"], "text": s.text,
                              "taxon_name": s.taxon_name, "horizon": s.horizon, "specimen": None}
    q = Specimen.objects.select_related("slab").filter(remarks__regex=f"[{STAR_CHARS}]")
    for sp in q:
        n = sum(sp.remarks.count(ch) for ch in STAR_CHARS)
        row = out.setdefault(sp.specimen_no, {"specimen_no": sp.specimen_no, "slab_no": sp.slab.slab_no,
                                              "letter": sp.letter, "stars": 0, "sources": [], "text": sp.remarks,
                                              "taxon_name": "", "horizon": "", "specimen": None})
        row["stars"] = max(row["stars"], n)
        row["sources"].append("phyloserver")
    # 테이블의 표본·슬랩을 붙인다 — 분류군·층준은 phyloserver 의 것이 앞선다
    slabs = {s.slab_no: s for s in Slab.objects.filter(slab_no__in={r["slab_no"] for r in out.values()})}
    specs = {(sp.slab_id, sp.letter): sp for sp in Specimen.objects.filter(slab__in=slabs.values())}
    for r in out.values():
        slab = slabs.get(r["slab_no"])
        r["slab"] = slab
        sp = specs.get((slab.id, r["letter"])) if slab else None
        r["specimen"] = sp
        if sp and sp.taxon_name:
            r["taxon_name"] = sp.taxon_name
        r["phylum"] = sp.phylum if sp else ""
        if slab and slab.horizon:
            r["horizon"] = slab.horizon
    for r in out.values():
        r["marks"] = "☆" * r["stars"]
    _attach_frames(out.values())
    return sorted(out.values(), key=lambda r: r["specimen_no"])


def _attach_frames(rows):
    """대표 컷 — 그 표본의 정본 빛 묶음 → PTM → 슬랩의 아무 더미(전경 먼저 아님: 표본을 보이려는 것이다)."""
    from .views import _first_frames
    slab_ids = [r["slab"].id for r in rows if r["slab"]]
    stacks = list(Stack.objects.filter(slab_id__in=slab_ids, copy_of__isnull=True, hidden=False)
                  .order_by("slab_id", "-kind", "label", "piece"))   # series > slab > ptm
    first = _first_frames([s.id for s in stacks])
    by_slab = defaultdict(list)
    for s in stacks:
        by_slab[s.slab_id].append(s)
    rank = {Stack.Kind.SERIES: 0, Stack.Kind.PTM: 1, Stack.Kind.SLAB: 2}
    for r in rows:
        r["frame"] = r["stack"] = None
        r["n_stacks"] = 0
        if not r["slab"]:
            continue
        mine = by_slab[r["slab"].id]
        sp = r["specimen"]
        own = [s for s in mine if sp and s.specimen_id == sp.id]
        r["n_stacks"] = len(own)
        pick = sorted(own, key=lambda s: rank.get(s.kind, 9)) or sorted(mine, key=lambda s: rank.get(s.kind, 9))
        for s in pick:
            if first.get(s.id):
                r["stack"], r["frame"] = s, first[s.id]
                break


def slab_marks():
    """목록 화면의 표시·거르기 (사용자 2026-10-26) — ({슬랩: ☆ 의 수}, {슬랩: [짝 슬랩 …]}).

    `starred`·`pairs_for` 와 같은 원천 규칙을 따른다 — ☆ 는 phyloserver remarks, 목록에 없는 슬랩만 엑셀.
    짝은 phyloserver 에서 읽은 슬랩은 그쪽 것만, 아니면 엑셀의 것. 두 방향을 합친다. 한 장에 같이 찍힌 전경(`64&65`)은 짝으로 치지 않는다 — 적힌 counterpart 만.
    """
    stars = defaultdict(int)
    in_catalog = set(Slab.objects.filter(catalog_id__isnull=False).values_list("slab_no", flat=True))
    for no, n in Star.objects.exclude(slab_no__in=in_catalog).values_list("slab_no", "stars"):
        stars[no] = max(stars[no], n)
    for no, remarks in Specimen.objects.filter(remarks__regex=f"[{STAR_CHARS}]").values_list("slab__slab_no", "remarks"):
        stars[no] = max(stars[no], sum(remarks.count(ch) for ch in STAR_CHARS))
    read = set(Slab.objects.filter(counterpart_synced_at__isnull=False).values_list("slab_no", flat=True))
    pairs = defaultdict(set)
    for origin, a, b in Counterpart.objects.values_list("origin", "slab_no", "other_slab_no"):
        if (origin == Counterpart.Origin.PHYLOSERVER or a not in read) and a != b:
            pairs[a].add(b)
            pairs[b].add(a)
    return dict(stars), {k: sorted(v) for k, v in pairs.items()}


def pairs_for(slab_no):
    """이 슬랩의 짝 — 적힌 방향 둘을 합쳐 상대 슬랩마다 하나. → [{"other", "slab", "lines": [...], "uncertain"}]

    `lines` 는 (이쪽 글자, 저쪽 글자, 원문, 출처) — 같은 짝이 양쪽 행에 적혀 있으면 둘 다 낸다(적은 것을 그대로 보인다).
    전경 사진 한 장에 두 슬랩이 같이 찍힌 것(`SP-2016-64&65(dorsal)`)도 짝으로 낸다(`shared_views`).
    """
    out = {}
    # phyloserver 에서 짝을 읽은 슬랩(`counterpart_synced_at`, export.json)은 그쪽 것만 — 엑셀의 짝은 읽지 못한 슬랩의 행만 쓴다
    read = set(Slab.objects.filter(counterpart_synced_at__isnull=False).values_list("slab_no", flat=True))

    def use(c):
        return c.origin == Counterpart.Origin.PHYLOSERVER or c.slab_no not in read

    def add(other, mine_l, other_l, text, src, unsure, origin):
        g = out.setdefault(other, {"other": other, "lines": [], "uncertain": True, "views": []})
        g["lines"].append({"mine": mine_l, "theirs": other_l, "text": text, "source": src, "uncertain": unsure,
                           "origin": origin})
        g["uncertain"] = g["uncertain"] and unsure

    for c in Counterpart.objects.filter(slab_no=slab_no):
        if use(c):
            add(c.other_slab_no, c.letter, c.other_letter, c.text, _where(c), c.uncertain, c.get_origin_display())
    for c in Counterpart.objects.filter(other_slab_no=slab_no).exclude(slab_no=slab_no):
        if use(c):
            add(c.slab_no, c.other_letter, c.letter, c.text, _where(c), c.uncertain, c.get_origin_display())
    for st, others in _together(slab_no):
        for o in others:
            g = out.setdefault(o, {"other": o, "lines": [], "uncertain": False, "views": []})
            g["views"].append(st)
            g["uncertain"] = False if not g["lines"] else g["uncertain"]
    slabs = {s.slab_no: s for s in Slab.objects.filter(slab_no__in=out)}
    for g in out.values():
        g["slab"] = slabs.get(g["other"])
    return sorted(out.values(), key=lambda g: g["other"])


def _where(c):
    """출처 한 마디 — 엑셀은 `파일:행`, phyloserver 는 그 표본(슬랩) 번호."""
    return c.source if c.origin == Counterpart.Origin.PHYLOSERVER else f"{c.source}:{c.row}"


# 두 슬랩을 한 장에 찍은 전경의 이름 — `SP-2016-64&65`, `SP-2016-64&SP-2016-65` 도 받는다.
# 반대 면 전경은 꼬리에 `(vent)` 가 붙는다(`SP-2016-64&65(vent)`) — 같은 규칙이다
_TOGETHER = re.compile(r"^SP-(?P<y>\d{4})-(?P<n>\d+)[A-Z]?(?P<rest>(?:\s*&\s*(?:SP-\d{4}-)?\d+[A-Z]?)+)\s*(?:\([^)]*\))?$")


def together_slabs(label):
    """`SP-2016-64&65` → ['SP-2016-0064', 'SP-2016-0065']. 꼴이 아니면 []."""
    m = _TOGETHER.match(label.strip())
    if not m:
        return []
    y = int(m["y"])
    out = [fmt_slab(y, m["n"])]
    for part in re.findall(r"&\s*(?:SP-(\d{4})-)?(\d+)", m["rest"]):
        out.append(fmt_slab(int(part[0]) if part[0] else y, part[1]))
    return out


def _together(slab_no):
    """[(전경 더미, [이 슬랩이 아닌 슬랩…])] — 이 슬랩이 이름에 든 두 슬랩 전경(정본, 숨기지 않은 것)."""
    out = []
    for st in (Stack.objects.filter(kind=Stack.Kind.SLAB, label__contains="&", copy_of__isnull=True, hidden=False)
               .select_related("slab")):
        names = together_slabs(st.label)
        if slab_no in names:
            out.append((st, [n for n in names if n != slab_no]))
    return out


def shared_views(slab):
    """다른 슬랩에 붙은 전경 가운데 이 슬랩도 찍힌 것 — 슬랩 화면의 전경 칸에 더한다 (지금 반입은 앞 번호에만 붙인다)."""
    return [st for st, _ in _together(slab.slab_no) if st.slab_id != slab.id]
