"""NAS 의 빛 더미(RTI 촬영 폴더)를 읽어 Stack·Frame 테이블을 맞춘다 (P01 1단계, wetherilli 002).

빛 더미 폴더는 이렇게 생겼다 (`SP-2016 샘플별/6D 외/PTM{, white coated}/<이름>/`):

    IMG_10095.JPG … IMG_10144.JPG   50 컷 — 삼각대 고정이라 픽셀이 맞아 있다
    SP-2016-52Z.lp                  첫 줄 컷 수, 다음 줄마다 `<윈도 경로> x y z`
    SP-2016-52Z.ptm                 RTIBuilder 가 만든 PTM (있으면)

`.lp` 의 경로는 촬영 PC 의 것(`C:\\Users\\MY\\Desktop\\…\\IMG_10095.jpg`)이라 **파일 이름만** 쓰고,
대소문자는 가리지 않고 찾는다(`.lp` 는 `.jpg`, 파일은 `.JPG`).

**원본은 읽기만 한다.** 몇 번을 돌려도 같다 — 같은 폴더는 같은 Stack 행이다(`source_dir`).
컷이 하나라도 없으면 그 더미는 통째로 건너뛰고 알린다 — 빠진 컷이 있는 빛 판은 방향이 비어 보인다.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import bare
from .models import Frame, Slab, Specimen, Stack
from .names import label_of, parse_stem

# NAS(Synology)가 만든 것 — 읽지 않는다
SKIP_DIRS = {"@eaDir", "#recycle"}


@dataclass
class ScanStats:
    found: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    bare: dict = field(default_factory=dict)    # 글자 없는 이름을 A 에 붙인 결과 (`bare.assign`, 012)
    errors: list = field(default_factory=list)


def parse_lp(path):
    """`.lp` → [(파일 이름, x, y, z), …]. 첫 줄의 컷 수와 줄 수가 다르면 ValueError."""
    lines = [ln.strip() for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        raise ValueError("빈 파일")
    n = int(lines[0])
    rows = []
    for ln in lines[1:]:
        # 경로에 빈칸이 있을 수 있다 — 끝의 세 수를 먼저 떼어 낸다
        name, x, y, z = ln.rsplit(None, 3)
        rows.append((name.replace("\\", "/").rsplit("/", 1)[-1], float(x), float(y), float(z)))
    if len(rows) != n:
        raise ValueError(f"첫 줄은 {n} 컷인데 {len(rows)} 줄이다")
    return rows


def find_lp_files(root):
    """root 아래의 `.lp` 를 모두 찾는다 (NAS 가 만든 폴더는 건너뛴다)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            if f.lower().endswith(".lp"):
                yield Path(dirpath) / f


def _preparation(rel_dir):
    return (Stack.Preparation.WHITE_COATED if "white coated" in rel_dir.lower()
            else Stack.Preparation.NONE)


def _exif(path):
    """(폭, 높이, 카메라, 촬영 시각) — 머리만 읽는다."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
        ex = im.getexif()
        model = (ex.get(272) or "").strip()
        when = ex.get_ifd(0x8769).get(36867) or ex.get(306)
    at = None
    if when:
        try:
            at = timezone.make_aware(datetime.strptime(str(when).strip(), "%Y:%m:%d %H:%M:%S"))
        except ValueError:
            pass
    return w, h, model, at


def read_stack(lp_path, root):
    """`.lp` 하나 → 테이블에 넣을 값. 넣지는 않는다. 문제가 있으면 ValueError."""
    lp_path = Path(lp_path)
    folder = lp_path.parent
    stem = lp_path.stem
    name = parse_stem(stem) or parse_stem(folder.name)
    if not name:
        raise ValueError(f"이름을 못 읽는다: {stem}")
    rows = parse_lp(lp_path)
    by_lower = {f.lower(): f for f in os.listdir(folder)}
    missing = [r[0] for r in rows if r[0].lower() not in by_lower]
    if missing:
        raise ValueError(f"컷 {len(missing)} 장이 없다 (첫째 {missing[0]})")

    rel_dir = str(folder.relative_to(root))
    frames = []
    for seq, (fname, x, y, z) in enumerate(rows):
        actual = by_lower[fname.lower()]
        frames.append({"seq": seq, "path": f"{rel_dir}/{actual}", "light_x": x, "light_y": y, "light_z": z})

    # 폭·높이는 첫 컷에서 — 삼각대 더미라 모두 같다. 다르면 2단계 뷰어가 겹쳐 그리지 못한다
    w, h, camera, at = _exif(folder / Path(frames[0]["path"]).name)
    for fr in frames:
        fr["width"], fr["height"] = w, h

    ptm = by_lower.get(f"{stem.lower()}.ptm", "")
    return {
        "name": name,
        "stack": {
            "kind": Stack.Kind.PTM,
            "preparation": _preparation(rel_dir),
            "view": Stack.View.ZOOM if name["zoom"] else Stack.View.WHOLE,
            "label": label_of(stem),
            "source_dir": rel_dir,
            "lp_file": lp_path.name,
            "ptm_file": ptm,
            "n_frames": len(frames),
            "width": w, "height": h,
            "camera": camera,
            "captured_at": at,
        },
        "frames": frames,
    }


def _frame_key(fr):
    return (fr["seq"], fr["path"], round(fr["light_x"], 6), round(fr["light_y"], 6), round(fr["light_z"], 6))


@transaction.atomic
def save_stack(info):
    """read_stack 의 값을 테이블에 맞춘다. 돌려주는 값: 'created' | 'updated' | 'unchanged'."""
    name = info["name"]
    slab, _ = Slab.objects.get_or_create(slab_no=name["slab"], defaults={"year": name["year"]})
    # 표본은 대문자 글자가 있을 때만 여기서 붙인다 (names.py). 글자 없는 이름은 scan 끝의 bare.assign 이 A 에 붙인다(012)
    specimen = None
    if name["letter"]:
        specimen, _ = Specimen.objects.get_or_create(slab=slab, letter=name["letter"])

    values = dict(info["stack"], slab=slab)
    stack = Stack.objects.filter(source_dir=values["source_dir"], kind=values["kind"],
                                 label=values["label"]).first()
    if stack is None:
        stack = Stack.objects.create(specimen=specimen, **values)
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in info["frames"])
        return "created"

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

    old = [_frame_key({"seq": f.seq, "path": f.path, "light_x": f.light_x, "light_y": f.light_y,
                       "light_z": f.light_z}) for f in stack.frames.all()]
    if old != [_frame_key(fr) for fr in info["frames"]]:
        # 컷에는 아직 사람이 붙인 것이 없어 통째로 바꿔도 잃을 것이 없다.
        # 컷에 메모·표시가 붙기 시작하면 여기를 seq 별 맞추기로 바꿔야 한다
        stack.frames.all().delete()
        Frame.objects.bulk_create(Frame(stack=stack, **fr) for fr in info["frames"])
        changed = True
    return "updated" if changed else "unchanged"


def scan(root=None, under=None, log=None):
    root = Path(root or settings.SOURCE_ROOT)
    start = root / under if under else root
    st = ScanStats()
    for lp in find_lp_files(start):
        st.found += 1
        try:
            result = save_stack(read_stack(lp, root))
        except (ValueError, OSError) as e:
            st.errors.append(f"{lp.relative_to(root)}: {e}")
            continue
        setattr(st, result, getattr(st, result) + 1)
        if log and result != "unchanged":
            log(f"{result}: {lp.relative_to(root).parent}")
    # 글자 없는 이름(`SP-2016-494`)은 A 표본에 — 예외 슬랩은 비워 둔다 (012)
    st.bare = bare.assign()
    return st
