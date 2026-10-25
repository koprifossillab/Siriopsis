"""슬랩 전경 사진(`SP-2016-694(dorsal).JPG`)을 읽어 Stack(kind=slab)·Frame 테이블을 맞춘다 (wetherilli 009).

**dorsal 은 슬랩 안의 표본이 아니라 슬랩 자체를 찍은 사진이다**(사용자 2026-10-25). 그래서 묶음은 슬랩에만 붙고
표본에는 안 붙는다 — 이름에 글자가 있어도(`SP-2016-1316A(dorsal)`, 12 장) 슬랩 사진이다.

2026-10-25 조사(4,712 장): 거의 모두 `SP-<연도>-<번호>(dorsal).JPG` 한 장이고, 같은 이름이 사본 폴더(`USB백업`·구간 안의 같은 이름
폴더·`알씨원본`)에 또 있다(685 슬랩). 서로 다른 사진 여럿은 `(dorsal) (1)`·`(dorsal)-2` 처럼 뒤에 번호를 단다(19 슬랩) — 한 묶음의 컷이 된다.
- `SP-2016-64&65(dorsal)` — 슬랩 둘을 한 장에. **앞 번호의 슬랩에 붙인다**(묶음 하나는 슬랩 하나에 속한다). 뒷 슬랩은 이 사진을 모른다
- `SP-2017-2SP-2017-2237(dorsal)` — 이름이 겹쳐 적혔다(`할미새사촌`, 10 장). 뒤의 것이 슬랩이다
- `SP-2016-1155-(dorsal)` — 괄호 앞의 `-`(5 장)
- `724(dorsal)` — 번호만(`SP-2017(721~730)` 폴더, 10 장). **폴더 이름의 연도·구간 안에 들 때만** 그 슬랩으로 읽는다
- `JC-SPIDER-*`·`JC-ANO-*` 처럼 SP 가 아닌 것은 안 읽는다

정본과 사본은 빛 묶음과 같은 규칙으로 고른다(`lightseries._rank` — 컷 수 → 사본 표시 폴더가 아님 → 얕은 경로), 사본도 넣어 잇는다.
**한 장짜리도 넣는다** — 빛 묶음과 달리 슬랩 전경은 대개 한 장이다. 사람이 고치는 일(`regroup`)은 빛 묶음만이라 여기는 늘 반입이 맞춘다.
**원본은 읽기만 한다.** 몇 번을 돌려도 같다. `--under` 로 일부만 훑으면 지우지 않는다.
"""
import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .lightseries import SKIP_SERIES_DIRS, _rank, preparation_of
from .lightstacks import _exif
from .models import Frame, Slab, Stack
from .names import slab_no

# <앞 이름 겹침?><SP-연도-번호><나머지(글자·&번호)> (dorsal…) <꼬리 번호?>.jpg — 닫는 괄호 자리의 `(` 오타(`(dorsal(`)도 받는다
SHOT = re.compile(
    r"^(?:SP-\d{4}-\d+(?=SP-))?(?P<name>SP-(?P<year>\d{4})-(?P<num>\d+)[A-Za-z&\d]*?)-?\s*"
    r"\((?P<view>dorsal)(?P<variant>[^)(]*)[)(]\s*(?P<tail>[-\s]*\(?\d+\)?)?\s*\.jpe?g$", re.IGNORECASE)


@dataclass
class SlabViewStats:
    files: int = 0
    names: int = 0          # (폴더, 이름) 묶음
    chosen: int = 0
    copies: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    exif_read: int = 0
    errors: list = field(default_factory=list)


# 번호만 적힌 이름과 그것을 담은 구간 폴더 `SP-2017(721~730)`
BARE = re.compile(r"^(?P<num>\d+)(?=\s*\(dorsal)", re.IGNORECASE)
FOLDER = re.compile(r"^SP-(?P<year>\d{4})-?\((?P<lo>\d+)\s*[~-]\s*(?P<hi>\d+)\)$")


def parse(fname, folder=""):
    """파일 이름 → (묶음 이름, 슬랩 번호, 연도, 컷 차례 열쇠). 꼴이 아니면 None. `folder` 는 담은 폴더의 이름."""
    b, f = BARE.match(fname), FOLDER.match(folder)
    if b and f and int(f["lo"]) <= int(b["num"]) <= int(f["hi"]):
        fname = f"SP-{f['year']}-{fname}"
    m = SHOT.match(fname)
    if not m:
        return None
    tail = re.sub(r"\D", "", m["tail"] or "")
    # 컷 차례: 꼬리 번호 없는 것 → 번호 순 → 변형(`dorsal-DSLR`)은 뒤로
    order = (1 if m["variant"].strip() else 0, int(tail) if tail else 0, fname.lower())
    return m["name"], slab_no(m["year"], m["num"]), int(m["year"]), order


def find(root, start):
    """{(폴더 상대경로, 묶음 이름): [(차례, 파일 이름, 슬랩, 연도), …]}"""
    groups = defaultdict(list)
    n = 0
    for dirpath, dirnames, filenames in os.walk(start):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_SERIES_DIRS)
        rel = str(Path(dirpath).relative_to(root))
        for f in filenames:
            p = parse(f, Path(dirpath).name)
            if p:
                name, slab, year, order = p
                groups[(rel, name)].append((order, f, slab, year))
                n += 1
    return groups, n


def choose(groups):
    """같은 대상(이름·처리)마다 [정본, 사본…]. 이름의 빈칸·대소문자는 가리지 않는다."""
    by_target = defaultdict(list)
    for (rel, name), shots in groups.items():
        by_target[(name.upper(), preparation_of(rel))].append((rel, name, sorted(shots)))
    out = []
    for cands in by_target.values():
        cands.sort(key=lambda c: _rank(c[0], len(c[2])))
        out.append(cands)
    return out


@transaction.atomic
def save(rel, name, shots, exif, copy_of=None, copies=0):
    slab_name, year = shots[0][2], shots[0][3]
    slab, _ = Slab.objects.get_or_create(slab_no=slab_name, defaults={"year": year})
    frames = []
    for seq, (_, fname, _, _) in enumerate(shots):
        path = f"{rel}/{fname}"
        w, h, _, at = exif[path]
        frames.append({"seq": seq, "path": path, "shot_no": None, "width": w, "height": h, "captured_at": at})
    w, h = Counter((f["width"], f["height"]) for f in frames).most_common(1)[0][0]
    first = exif[frames[0]["path"]]
    values = {
        "slab": slab, "kind": Stack.Kind.SLAB, "preparation": preparation_of(rel), "view": Stack.View.WHOLE,
        "label": name, "source_dir": rel, "copy_of": copy_of, "other_copies": copies, "piece": 0,
        "n_frames": len(frames), "width": w, "height": h, "camera": first[2], "captured_at": first[3],
    }
    stack = Stack.objects.filter(source_dir=rel, kind=Stack.Kind.SLAB, label=name, piece=0).first()
    if stack is None:
        stack = Stack.objects.create(**values)
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in frames)
        return "created", stack.id
    changed = False
    for k, v in values.items():
        if getattr(stack, k) != v:
            setattr(stack, k, v)
            changed = True
    if changed:
        stack.save()
    if [(f.seq, f.path) for f in stack.frames.all()] != [(f["seq"], f["path"]) for f in frames]:
        stack.frames.all().delete()
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in frames)
        changed = True
    return ("updated" if changed else "unchanged"), stack.id


def scan(root=None, under=None, workers=16, log=None):
    root = Path(root or settings.SOURCE_ROOT)
    start = root / under if under else root
    st = SlabViewStats()
    if not start.is_dir():
        # NAS 가 안 붙었을 때 「아무것도 없다」로 읽으면 아래에서 모든 묶음을 지운다
        st.errors.append(f"폴더가 없다: {start}")
        return st
    groups, st.files = find(root, start)
    st.names = len(groups)
    if not groups:
        st.errors.append(f"슬랩 전경을 하나도 못 찾았다: {start} — 지우지 않고 멈춘다")
        return st
    targets = choose(groups)
    st.chosen = len(targets)
    st.copies = sum(len(t) - 1 for t in targets)
    picked = [c for t in targets for c in t]
    if log:
        log(f"사진 {st.files} · 이름 묶음 {st.names} → 정본 {st.chosen} · 사본 {st.copies}")

    exif = {path: (w, h, cam, at) for path, w, h, cam, at in
            Frame.objects.filter(stack__kind=Stack.Kind.SLAB)
            .values_list("path", "width", "height", "stack__camera", "captured_at")}
    need = [f"{rel}/{s[1]}" for rel, _, shots in picked for s in shots if f"{rel}/{s[1]}" not in exif]

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
            if log and k and k % 2000 == 0:
                log(f"EXIF {k}/{len(need)}")

    def readable(rel, name, shots):
        if any(f"{rel}/{s[1]}" not in exif for s in shots):
            st.errors.append(f"{rel}/{name}: 못 읽은 사진이 있어 건너뜀")
            return False
        return True

    for target in targets:
        (rel, name, shots), rest = target[0], target[1:]
        if not readable(rel, name, shots):
            continue
        result, primary_id = save(rel, name, shots, exif, copies=len(rest))
        setattr(st, result, getattr(st, result) + 1)
        for c_rel, c_name, c_shots in rest:
            if readable(c_rel, c_name, c_shots):
                result, _ = save(c_rel, c_name, c_shots, exif, copy_of=Stack(id=primary_id))
                setattr(st, result, getattr(st, result) + 1)

    if not under:
        keys = {(rel, name) for rel, name, _ in picked}
        gone = Stack.objects.filter(id__in=[
            sid for sid, rel, name in Stack.objects.filter(kind=Stack.Kind.SLAB)
            .values_list("id", "source_dir", "label") if (rel, name) not in keys])
        st.removed = gone.count()
        gone.delete()
    return st
