"""더미의 배율 — 잴 컷을 내보내고, 잰 값을 받아 넣는다 (wetherilli 010).

재는 일(`pipeline/ruler_scale.py`)은 호스트에서 NAS 원본을 읽어 돈다 — 무거운 영상 처리는 웹 이미지에 넣지 않는다(CLAUDE.md 「환경」).
**운영 DB 는 호스트가 열 수 없다**(data-safety §14). 그래서 둘 사이는 파일이다 — 열쇠는 **컷 경로**(SOURCE_ROOT 기준):

    manage scale_targets --out targets.csv        # 컨테이너 안: 빛 묶음마다 보이는 첫 컷
    python pipeline/ruler_scale.py --targets targets.csv --out scales.csv   # 호스트
    manage import_scales scales.csv               # 컨테이너 안: 테이블에

**배율은 잰 컷을 가진 묶음에 붙는다.** 묶음을 가르거나 합쳐 잰 컷이 다른 묶음으로 가면 배율도 따라간다(`regroup.py`).
잰 컷이 이제 첫 컷이 아니어도(합쳐 온 컷 뒤로 밀린 것) 그 묶음에 붙인다 — 한 묶음에 잰 컷이 여럿이면 앞 컷의 것을.
"""
import csv

from django.db import transaction

from .models import Frame, Scale, Stack

TARGET_FIELDS = ["path", "width", "height", "stack", "label"]


def targets(copies=True):
    """잴 컷 — 보이는 빛 묶음마다 보이는 첫 컷 (seq 가 가장 작은 것). → [dict]"""
    stacks = Stack.objects.filter(kind=Stack.Kind.SERIES, hidden=False)
    if not copies:
        stacks = stacks.filter(copy_of__isnull=True)
    first = {}
    for f in (Frame.objects.filter(stack__in=stacks, hidden=False).order_by("stack_id", "seq")
              .values("stack_id", "path", "width", "height", "stack__label")):
        first.setdefault(f["stack_id"], f)
    return [{"path": f["path"], "width": f["width"], "height": f["height"], "stack": sid, "label": f["stack__label"]}
            for sid, f in sorted(first.items(), key=lambda t: t[1]["path"])]


def write_targets(fh, copies=True):
    rows = targets(copies)
    w = csv.DictWriter(fh, TARGET_FIELDS)
    w.writeheader()
    w.writerows(rows)
    return len(rows)


def _num(v, cast=float):
    try:
        return cast(v) if v not in (None, "") else None
    except ValueError:
        return None


class ImportStats:
    def __init__(self):
        self.rows = 0
        self.ok = self.doubt = self.none = 0
        self.no_frame = 0
        self.bad = []

    def __str__(self):
        return (f"줄 {self.rows} · 잼 {self.ok} · 믿기 어려움 {self.doubt} · 자 없음 {self.none} · "
                f"테이블에 없는 컷 {self.no_frame} · 이상한 줄 {len(self.bad)}")


@transaction.atomic
def import_rows(rows):
    """`ruler_scale.py` 의 결과 줄들 → Scale 테이블. 몇 번을 넣어도 같다(묶음마다 한 줄을 고쳐 쓴다).

    `ok` 가 아닌 값은 넣지 않는다 — `doubt` 는 어림값을 `note` 에만 남긴다(믿기 어려운 값으로 그은 스케일바는 없느니만 못하다).
    """
    st = ImportStats()
    by_path = {}
    for r in rows:
        st.rows += 1
        path = (r.get("path") or "").strip()
        status = (r.get("status") or "").strip()
        if not path or status not in Scale.Status.values:
            st.bad.append(f"{st.rows}: {path or '(경로 없음)'} · status={status!r}")
            continue
        mmpp = _num(r.get("mm_per_px"))
        if status == Scale.Status.OK and not (mmpp and mmpp > 0):
            st.bad.append(f"{st.rows}: {path} · ok 인데 mm_per_px 가 없다")
            continue
        by_path[path] = r
    # 경로 → 그 컷을 가진 빛 묶음들(사본은 경로가 다르다). 한 묶음에 잰 컷이 여럿이면 앞 컷
    chosen = {}
    found = set()
    for f in (Frame.objects.filter(path__in=list(by_path), stack__kind=Stack.Kind.SERIES)
              .order_by("stack_id", "hidden", "seq")):
        found.add(f.path)
        chosen.setdefault(f.stack_id, f)
    st.no_frame = len(set(by_path) - found)
    for sid, f in chosen.items():
        r = by_path[f.path]
        status = r["status"].strip()
        note = (r.get("note") or "").strip()
        mmpp = _num(r.get("mm_per_px"))
        if status == Scale.Status.DOUBT and mmpp:
            note = f"어림 {mmpp:.5f} mm/px — {note}" if note else f"어림 {mmpp:.5f} mm/px"
        Scale.objects.update_or_create(stack_id=sid, defaults={
            "status": status,
            "mm_per_px": mmpp if status == Scale.Status.OK else None,
            "frame_path": f.path,
            "width": _num(r.get("width"), int) or f.width,
            "height": _num(r.get("height"), int) or f.height,
            "ticks": _num(r.get("ticks"), int) or 0,
            "note": note[:300],
        })
        setattr(st, status, getattr(st, status) + 1)
    return st


def import_file(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return import_rows(csv.DictReader(fh))


def of(stack):
    """묶음의 Scale 행 — 없으면 None."""
    try:
        return stack.scale
    except Scale.DoesNotExist:
        return None
