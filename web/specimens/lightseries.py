"""카탈로그 빛 묶음을 읽어 Stack(kind=series)·Frame 테이블을 맞춘다 (wetherilli 003).

카탈로그 사진은 `SP-2022-131-1.JPG … -6.JPG` 처럼 **표본 이름 뒤 번호가 빛을 달리해 찍은 컷**이다(사용자 2026-10-25).
흔한 꼴은 1~3 번이 고른 빛(1 번에 자), 4 번부터 낮은 빛을 여러 방향에서. 빛 방향 값은 없다.
2026-10-25 조사(9,054 이름)로 절반 남짓은 미리보기 정밀도에서 구도가 그대로였고, 나머지는 조금씩 어긋나거나
딴 구도 컷이 섞여 있다 — 맞춤은 다음 단계이고, 여기서는 묶음을 있는 그대로 넣는다.

**정본 고르기** — 같은 이름·같은 처리의 묶음이 여러 폴더에 있다(구간 폴더 안의 같은 이름 하위 폴더, `알씨원본`,
`2016.12.25 USB백업`, `6D 외/2016-B&S&A` …). 이름이 같아도 바이트가 다른 것이 많아 어느 쪽이 원본인지 파일로는
가릴 수 없다. 그래서 규칙으로 하나를 고르고 나머지 수를 `other_copies` 에 남긴다:
컷이 많은 쪽 → 사본 표시 폴더(`알씨원본`·`USB백업`)가 아닌 쪽 → 얕은 경로 → 경로 글자순.
**정본 고르기는 전체를 훑을 때만 뜻이 있다** — `--under` 로 일부만 훑으면 고르기도 그 안에서만 하고, 사라진 묶음을 지우지 않는다.

**원본은 읽기만 한다.** 몇 번을 돌려도 같다. EXIF 는 테이블에 없는 컷만 읽는다(다시 돌릴 때 NAS 를 덜 읽는다).
"""
import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .lightstacks import SKIP_DIRS, _exif
from .models import Frame, Slab, Specimen, Stack
from .names import parse_stem

# SP-<연도>-<번호><글자 0~2>-<컷 번호>.JPG. 이름과 번호 사이·확장자 앞의 빈칸을 견딘다(`SP-2016-47A-1 .JPG`).
# `(dorsal)`·`(vent)`(슬랩 전경), `(ethanol)`·`(water)`(액침), `(Cutting)` 이 붙은 것은 빛 묶음이 아니라 걸리지 않는다
SHOT = re.compile(r"^(?P<name>SP-\d{4}-\d+[A-Za-z]{0,2})\s*-\s*(?P<no>\d+)\s*\.jpe?g$", re.IGNORECASE)

# 줄인 사본(`output/`)은 원본의 사본이다 — 읽지 않는다
SKIP_SERIES_DIRS = SKIP_DIRS | {"output"}
# 이 낱말이 경로에 있으면 사본 쪽으로 본다 (정본 고르기의 둘째 기준)
COPY_MARKS = ("알씨원본", "usb백업")
MIN_FRAMES = 2          # 한 장짜리는 묶음이 아니다


@dataclass
class SeriesStats:
    names: int = 0          # 찾은 이름 묶음(폴더 포함)
    chosen: int = 0         # 정본으로 고른 묶음
    single: int = 0         # 한 장뿐이라 뺀 것
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    exif_read: int = 0
    errors: list = field(default_factory=list)


def preparation_of(rel_dir):
    low = rel_dir.lower()
    if "white coated" in low:
        return Stack.Preparation.WHITE_COATED
    if "mg" in low and ("코팅" in low or "coat" in low):
        return Stack.Preparation.MG_COATED
    return Stack.Preparation.NONE


def find_shots(root, start):
    """{(폴더 상대경로, 이름): [(번호, 파일 이름), …]}"""
    groups = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(start):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_SERIES_DIRS)
        rel = str(Path(dirpath).relative_to(root))
        for f in filenames:
            m = SHOT.match(f)
            if m:
                groups[(rel, m["name"])].append((int(m["no"]), f))
    return groups


def _rank(rel_dir, n):
    low = rel_dir.lower()
    is_copy = any(mark in low for mark in COPY_MARKS)
    return (-n, is_copy, rel_dir.count("/"), rel_dir)


def choose(groups):
    """같은 대상(슬랩·글자·소문자·처리)의 묶음 중 정본 하나씩. → [(폴더, 이름, 컷들, 다른 사본 수)]"""
    by_target = defaultdict(list)
    for (rel, name), shots in groups.items():
        p = parse_stem(name)
        if not p:
            continue
        by_target[(p["slab"], p["letter"], p["lower"], preparation_of(rel))].append((rel, name, shots))
    out = []
    for cands in by_target.values():
        cands.sort(key=lambda c: _rank(c[0], len(c[2])))
        rel, name, shots = cands[0]
        out.append((rel, name, sorted(shots), len(cands) - 1))
    return out


def _frame_key(fr):
    return (fr["seq"], fr["path"], fr["shot_no"])


@transaction.atomic
def save_series(rel, name, shots, copies, exif):
    p = parse_stem(name)
    slab, _ = Slab.objects.get_or_create(slab_no=p["slab"], defaults={"year": p["year"]})
    specimen = None
    if p["letter"]:
        specimen, _ = Specimen.objects.get_or_create(slab=slab, letter=p["letter"])

    frames = []
    for seq, (no, fname) in enumerate(shots):
        path = f"{rel}/{fname}"
        w, h, _, at = exif[path]
        frames.append({"seq": seq, "path": path, "shot_no": no, "width": w, "height": h, "captured_at": at})
    w, h = Counter((f["width"], f["height"]) for f in frames).most_common(1)[0][0]
    first = exif[frames[0]["path"]]
    values = {
        "slab": slab, "kind": Stack.Kind.SERIES, "preparation": preparation_of(rel),
        "view": Stack.View.WHOLE, "label": name, "source_dir": rel, "other_copies": copies,
        "n_frames": len(frames), "width": w, "height": h, "camera": first[2], "captured_at": first[3],
    }
    stack = Stack.objects.filter(source_dir=rel, kind=Stack.Kind.SERIES, label=name).first()
    if stack is None:
        stack = Stack.objects.create(specimen=specimen, **values)
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in frames)
        return "created", stack.id

    changed = False
    for k, v in values.items():
        if getattr(stack, k) != v:
            setattr(stack, k, v)
            changed = True
    if specimen and stack.specimen_id is None:
        stack.specimen = specimen
        changed = True
    if changed:
        stack.save()
    old = [(f.seq, f.path, f.shot_no) for f in stack.frames.all()]
    if old != [_frame_key(fr) for fr in frames]:
        # 컷에 사람이 붙인 것이 아직 없다 — 맞춤 값이 컷에 붙기 시작하면 path 별로 맞추게 바꾼다
        stack.frames.all().delete()
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in frames)
        changed = True
    return ("updated" if changed else "unchanged"), stack.id


def scan(root=None, under=None, workers=16, log=None):
    root = Path(root or settings.SOURCE_ROOT)
    start = root / under if under else root
    st = SeriesStats()
    if not start.is_dir():
        # NAS 가 안 붙었을 때 「아무것도 없다」로 읽으면 아래에서 모든 묶음을 지운다
        st.errors.append(f"폴더가 없다: {start}")
        return st
    groups = find_shots(root, start)
    st.names = len(groups)
    if not groups:
        st.errors.append(f"빛 묶음을 하나도 못 찾았다: {start} — 지우지 않고 멈춘다")
        return st
    picked = choose(groups)
    st.single = sum(1 for c in picked if len(c[2]) < MIN_FRAMES)
    picked = [c for c in picked if len(c[2]) >= MIN_FRAMES]
    st.chosen = len(picked)
    if log:
        log(f"이름 묶음 {st.names} → 정본 {st.chosen} (한 장뿐 {st.single})")

    # EXIF: 테이블에 이미 있는 컷은 그 값을 쓴다 (카메라는 묶음에만 적혀 있다)
    exif = {path: (w, h, cam, at) for path, w, h, cam, at in
            Frame.objects.filter(stack__kind=Stack.Kind.SERIES)
            .values_list("path", "width", "height", "stack__camera", "captured_at")}
    need = [f"{rel}/{fname}" for rel, _, shots, _ in picked for _, fname in shots
            if f"{rel}/{fname}" not in exif]

    def read(path):
        try:
            return path, _exif(root / path), None
        except OSError as e:
            return path, None, str(e)

    with ThreadPoolExecutor(workers) as ex:
        for k, (path, val, err) in enumerate(ex.map(read, need)):
            if err:
                st.errors.append(f"{path}: {err}")
            else:
                exif[path] = val
                st.exif_read += 1
            if log and k and k % 5000 == 0:
                log(f"EXIF {k}/{len(need)}")

    for rel, name, shots, copies in picked:
        if any(f"{rel}/{f}" not in exif for _, f in shots):
            # 테이블의 것은 그대로 둔다 — 한 번 못 읽었다고 지우지 않는다
            st.errors.append(f"{rel}/{name}: 못 읽은 컷이 있어 건너뜀")
            continue
        result, _ = save_series(rel, name, shots, copies, exif)
        setattr(st, result, getattr(st, result) + 1)

    if not under:
        # 전체를 훑었을 때만: 정본에서 빠진 묶음(폴더가 사라졌거나 더 나은 사본이 생긴 것)을 지운다.
        # 못 읽어 건너뛴 묶음도 정본 목록에 있으니 지워지지 않는다
        picked_keys = {(rel, name) for rel, name, _, _ in picked}
        gone_ids = [sid for sid, rel, name in Stack.objects.filter(kind=Stack.Kind.SERIES)
                    .values_list("id", "source_dir", "label") if (rel, name) not in picked_keys]
        gone = Stack.objects.filter(id__in=gone_ids)
        st.removed = gone.count()
        gone.delete()
    return st
