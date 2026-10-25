"""이름에 표본 글자가 없는 더미를 A 표본에 붙인다 (wetherilli 012).

실무자 전달(2026-10-25): **표본 번호 뒤에 알파벳이 없으면 그 슬랩의 표본은 한 장이고, 그것이 A 다.**
phyloserver 도 그렇게 적는다 — 엑셀에서 글자 칸이 빈 슬랩(`SP-2022-49`)이 목록에는 `SP-2022-0049-A` 로 있다.

예외: 그 슬랩에 A 가 아닌 표본이 따로 알려져 있으면(phyloserver 목록의 `B` …, 또는 NAS 의 `SP-2016-494B` 같은 이름)
「표본이 한 장」이라는 앞의 말이 맞지 않는다 — 그 슬랩은 붙이지 않고 비워 둔다(사람이 본다, `exceptions`).
소문자(`0577a`)는 글자가 있는 이름이라 이 규칙 밖이다. 슬랩 전경(`slab`)은 표본이 아니라 슬랩 사진이라 밖이다.

**한 함수가 다시 정한다** — 글자 없는 이름의 더미는 이 규칙만으로 표본이 정해지므로, 반입 셋(`scan_light_stacks`·
`scan_light_series`·`import_catalog`)이 끝에 이것을 불러 지금 아는 것으로 다시 맞춘다. 몇 번을 돌려도 같다.
phyloserver 를 아직 안 읽은 슬랩(`catalog_synced_at` 없음)은 붙이지 않는다 — 예외인지 모르기 때문이다. 처음 세우는 DB 는
반입 다음 `import_catalog` 가 붙인다.
**사람이 손댄 묶음(`edited_at`)은 건드리지 않는다**(008).
"""
from django.db import transaction

from .models import Slab, Specimen, Stack
from .names import parse_stem

BARE_KINDS = (Stack.Kind.SERIES, Stack.Kind.PTM)
LETTER = "A"


def is_bare(label):
    """글자도 소문자도 없는 이름인가 (`SP-2016-494` 는 그렇다, `SP-2016-494B`·`SP-2011-0577a` 는 아니다)."""
    p = parse_stem(label)
    return bool(p) and not p["letter"] and not p["lower"]


def other_letters(slab):
    """A 가 아닌 표본 글자 — phyloserver 목록(`catalog_letters`)과 테이블의 표본(NAS 이름에서 온 것)."""
    known = set(slab.catalog_letters.split()) | set(slab.specimens.values_list("letter", flat=True))
    return sorted(known - {LETTER})


def _bare_stacks(slab_ids=None):
    qs = Stack.objects.filter(kind__in=BARE_KINDS, edited_at__isnull=True)
    if slab_ids is not None:
        qs = qs.filter(slab_id__in=slab_ids)
    return [st for st in qs.only("id", "slab_id", "label", "specimen_id") if is_bare(st.label)]


@transaction.atomic
def assign(slab_ids=None):
    """글자 없는 더미의 표본을 다시 정한다. `slab_ids` 가 없으면 전체. → {"attached", "detached", "skipped": [슬랩 번호…]}"""
    stacks = _bare_stacks(slab_ids)
    by_slab = {}
    for st in stacks:
        by_slab.setdefault(st.slab_id, []).append(st)
    out = {"attached": 0, "detached": 0, "skipped": [], "unsynced": 0}
    for slab in Slab.objects.filter(id__in=by_slab).order_by("slab_no"):
        mine = by_slab[slab.id]
        if slab.catalog_synced_at is None:
            out["unsynced"] += 1
            continue
        if other_letters(slab):
            out["skipped"].append(slab.slab_no)
            target = None
        else:
            target, _ = Specimen.objects.get_or_create(slab=slab, letter=LETTER)
        tid = target.id if target else None
        change = [st.id for st in mine if st.specimen_id != tid]
        if change:
            Stack.objects.filter(id__in=change).update(specimen_id=tid)
            out["attached" if tid else "detached"] += len(change)
    return out


def exceptions():
    """글자 없는 더미가 있는데 A 가 아닌 표본도 알려진 슬랩 — 붙이지 않은 것. 사람에게 보일 표의 줄."""
    by_slab = {}
    for st in _bare_stacks():
        by_slab.setdefault(st.slab_id, []).append(st)
    rows = []
    for slab in Slab.objects.filter(id__in=by_slab).order_by("slab_no"):
        others = other_letters(slab)
        if not others:
            continue
        mine = by_slab[slab.id]
        nas = sorted(set(slab.specimens.exclude(letter=LETTER).values_list("letter", flat=True)))
        rows.append({
            "slab": slab.slab_no,
            "bare_stacks": len(mine),
            "labels": " ".join(sorted({st.label for st in mine})),
            "phyloserver_letters": slab.catalog_letters,
            "nas_letters": " ".join(nas),
            "in_phyloserver": slab.catalog_id is not None,
        })
    return rows


def summary():
    """지금 상태를 한 줄로 — 반입 명령이 끝에 찍는다."""
    stacks = _bare_stacks()
    on_a = sum(1 for st in stacks if st.specimen_id is not None)
    slabs = Slab.objects.filter(id__in={st.slab_id for st in stacks})
    unsynced = slabs.filter(catalog_synced_at__isnull=True).count()
    return (f"글자 없는 더미 {len(stacks)} — A 에 붙음 {on_a} · 예외 슬랩 {len(exceptions())} · "
            f"phyloserver 안 읽은 슬랩 {unsynced}")
