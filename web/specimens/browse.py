"""목록 화면의 묶음 — 채집 연도 → 번호 구간(또는 층준 구간) → 슬랩 (wetherilli 005).

DiaRUGA 목록이 지역 → 코어 → 층준(슬라이드)으로 묶듯(사용자 2026-10-25), 여기서는 **연도 탭 → 구간 → 슬랩**이다.
연도는 슬랩 이름의 `SP-<연도>`(채집한 해).

**번호 구간이 기본이다** — NAS 가 슬랩을 열 개씩 폴더로 나눠 두었다(`SP-2016(101~110)`, 사용자 2026-10-25). 사람이 자료를
그 폴더로 찾아 왔으니 목록도 같은 열 개 단위를 쓰고, 그 위를 백 개 단위로 접는다. 열 개 이름은 폴더 이름과 같은 꼴로 **번호에서 계산한다**
(폴더를 읽지 않는다 — 사본·PTM 폴더가 따로 있어 슬랩 하나에 폴더가 여럿이다).

층준 구간으로도 묶는다(`by=horizon`) — 층준은 phyloserver 목록의 `horizon` 이다.

**층준은 사람이 손으로 적은 글자다** — `6.1-6.2`·`6.2~6.3`·`~7.3`·`SCREE`/`scree`·`?`·빈칸이 섞여 있다(2026-10-25 조사:
연도마다 구간 글자가 100 가지 남짓, 빈칸이 절반). 그래서 **글자를 고치지 않고 묶기만 한다** — 첫 수를 0.1 m 구간으로
내리고(`6.15-6.2` → 6.1 구간), 굴러 내린 돌(scree)과 미기록·읽을 수 없음을 따로 둔다. 원래 글자는 슬랩 줄에 그대로 보인다.
"""
import math
import re
from collections import defaultdict

from django.db.models import Count, Min, Q, Sum

from .models import Slab, Specimen, Stack

_NUM = re.compile(r"\d+(?:\.\d+)?")

# 구간 열쇠 — 정렬 차례가 곧 화면 차례다. 수 구간이 먼저, 그다음 scree·미상·미기록
SCREE = (1, "scree")
UNKNOWN = (2, "unknown")
BLANK = (3, "blank")


def band_of(horizon):
    """층준 글자 → (정렬 열쇠, 이름)."""
    h = (horizon or "").strip()
    if not h:
        return BLANK, "층준 미기록"
    if "scree" in h.lower():
        return SCREE, "Scree — 굴러 내린 돌"
    m = _NUM.search(h)
    if not m:
        return UNKNOWN, "층준 미상"
    lo = math.floor(float(m.group()) * 10 + 1e-9) / 10
    return (0, lo), f"{lo:.1f}–{lo + 0.1:.1f} m"


def slab_rows(slabs):
    """슬랩마다 화면 한 줄의 값. 사본은 묶음 수·컷 수에 넣지 않는다(따로 센다)."""
    ids = [s.id for s in slabs]
    agg = {r["slab_id"]: r for r in Stack.objects.filter(slab_id__in=ids).values("slab_id").annotate(
        series=Count("id", filter=Q(kind=Stack.Kind.SERIES, copy_of__isnull=True)),
        ptm=Count("id", filter=Q(kind=Stack.Kind.PTM, copy_of__isnull=True)),
        copies=Count("id", filter=Q(copy_of__isnull=False)),
        frames=Sum("n_frames", filter=Q(copy_of__isnull=True)),
        first=Min("captured_at"),
    )}
    specs = defaultdict(list)
    for sp in Specimen.objects.filter(slab_id__in=ids).only("slab_id", "letter", "taxon_name", "phylum"):
        specs[sp.slab_id].append(sp)
    rows = []
    for s in slabs:
        a = agg.get(s.id, {})
        sp = specs.get(s.id, [])
        rows.append({
            "slab": s,
            "n_specimens": len(sp),
            "taxa": sorted({x.taxon_name for x in sp if x.taxon_name}),
            "phyla": sorted({x.phylum for x in sp if x.phylum}),
            "series": a.get("series", 0), "ptm": a.get("ptm", 0), "copies": a.get("copies", 0),
            "frames": a.get("frames") or 0, "first": a.get("first"),
        })
    return rows


def number_of(slab_no):
    """`SP-2016-0052` → 52."""
    return int(slab_no.rsplit("-", 1)[-1])


def block_of(slab):
    """백 개 단위 구간 → (정렬 열쇠, 이름). 안의 열 개 단위 이름은 `folder_of`."""
    lo = (number_of(slab.slab_no) - 1) // 100 * 100 + 1
    return (0, lo), f"{lo}~{lo + 99}"


def folder_of(slab):
    """NAS 의 열 개 단위 폴더 이름 꼴 — `SP-2016(101~110)`."""
    lo = (number_of(slab.slab_no) - 1) // 10 * 10 + 1
    return f"SP-{slab.year}({lo}~{lo + 9})"


def tree(rows, by="no"):
    """줄들 → 구간 묶음 [{key, name, rows, 합계…}], 구간 차례로.

    번호로 묶으면 줄마다 `folder`(열 개 단위 폴더 이름)를 붙이고, 그 폴더의 첫 줄에만 `folder_head` 를 켠다 — 화면이 거기에 가름줄을 넣는다.
    """
    groups = {}
    for r in rows:
        if by == "no":
            # 연도 탭이 「전체」면 같은 번호가 해마다 있다 — 연도를 열쇠에 넣는다
            (k, lo), name = block_of(r["slab"])
            key, name = (k, (r["slab"].year, lo)), f"SP-{r['slab'].year}  {name}"
            r["folder"] = folder_of(r["slab"])
        else:
            key, name = band_of(r["slab"].horizon)
        g = groups.setdefault(key, {"key": key, "name": name, "rows": []})
        g["rows"].append(r)
    out = []
    for key in sorted(groups):
        g = groups[key]
        g["id"] = "b" + re.sub(r"[^0-9a-z]", "", str(key[1]).lower())
        if by == "no":
            prev = None
            for r in g["rows"]:
                r["folder_head"] = r["folder"] != prev
                prev = r["folder"]
        for f in ("n_specimens", "series", "ptm", "copies", "frames"):
            g[f] = sum(r[f] for r in g["rows"])
        out.append(g)
    return out


def years():
    """[(연도, 슬랩 수)] — 더미가 있는 슬랩만."""
    return list(Slab.objects.filter(stacks__isnull=False).values_list("year")
                .annotate(n=Count("id", distinct=True)).order_by("year"))
