"""빛 묶음을 사람이 고친다 — 가르기·합치기·지우기, 컷 숨기기 (wetherilli 008).

DiaRUGA `web/viewer/regroup.py`(v0.37.1)의 모양을 옮겼다: **미리보기(`*_preview`, 테이블을 건드리지 않는다)
다음에 확인(`apply_*`, 한 트랜잭션)**, 이상한 것이 하나라도 있으면 아무것도 하지 않는다. 화면도 이 모듈만 부른다.

DiaRUGA 와 다른 것:
- **지우는 것이 없다 — 숨긴다.** 묶음 행을 지우면 다음 반입이 같은 폴더·이름에서 도로 만든다. 그래서 묶음은
  `hidden`, 컷도 `hidden` 이고, 둘 다 되살릴 수 있다. DiaRUGA 는 시야 아래 검출·교정이 딸려 가 「진짜로 지워진다」를
  경고했지만, 여기는 묶음 아래 사람이 단 것이 아직 없다
- **이웃만 합치는 규칙이 없다.** 시야는 촬영 순서로 늘어놓지만, 더미는 슬랩 안에서 이름·종류 차례일 뿐이다.
  같은 슬랩의 빛 묶음이면 합친다 — 합친 컷은 고른 묶음 뒤에 붙는다
- **고친 묶음은 `edited_at` 을 단다** — 반입(`lightseries.py`)이 그 묶음을 건너뛴다. 사본도 묶음이라 고칠 수 있다
- **PTM 은 고치지 않는다.** 50 방향과 `.lp` 가 짝이라 가르거나 합칠 까닭이 없다

**정본을 지우거나 다른 묶음에 합치면 그 사본도 숨는다** — 사본은 정본의 「같은 묶음」 줄에서만 보이므로(`views.stack`),
정본이 숨으면 사본은 길을 잃는다. 미리보기가 그것을 먼저 보인다.
"""
from collections import Counter

from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from .models import EditLog, Frame, Stack

# seq 를 다시 매기는 동안 (stack, seq) 유일 제약에 걸리지 않게 잠깐 치워 두는 자리 — 한 묶음의 컷 수보다 훨씬 크면 된다
SEQ_PARK = 10000


def visible_frames(stack):
    return list(stack.frames.filter(hidden=False).order_by("seq"))


def _check(stack):
    """고칠 수 있는 묶음인가. → 문제 목록"""
    if stack.kind != Stack.Kind.SERIES:
        return [f"{stack.get_kind_display()} 묶음은 고치지 않는다 — 빛 묶음만"]
    if stack.hidden:
        return ["지운 묶음이다 — 되살린 뒤에 고친다"]
    return []


def _copies(stack):
    """함께 숨을 사본 — 이 묶음이 정본일 때만."""
    return list(stack.copies.filter(hidden=False).order_by("source_dir"))


def _refresh(stack, now):
    """보이는 컷으로 묶음의 값을 다시 적고 손댄 표시를 단다."""
    frames = visible_frames(stack)
    stack.n_frames = len(frames)
    if frames:
        stack.width, stack.height = Counter((f.width, f.height) for f in frames).most_common(1)[0][0]
        stack.captured_at = frames[0].captured_at
    stack.edited_at = now
    stack.save()


def _renumber(stack, frames):
    """`frames` 를 이 묶음으로 옮기며 그 차례대로 seq 를 0부터. 이 묶음에 남은 다른 컷(가를 조각)도 함께 치워 둔다."""
    ids = [f.id for f in frames]
    Frame.objects.filter(Q(id__in=ids) | Q(stack=stack)).update(seq=F("seq") + SEQ_PARK)
    for i, fid in enumerate(ids):
        Frame.objects.filter(id=fid).update(stack=stack, seq=i)


def _ordered(frames):
    return [f for f in frames if not f.hidden] + [f for f in frames if f.hidden]


def _row(f):
    return {"id": f.id, "no": f.shot_no, "name": f.path.rsplit("/", 1)[-1]}


def _log(action, stack, **detail):
    EditLog.objects.create(action=action, stack=stack, detail=detail)


# ── 가르기 ────────────────────────────────────────────────

def _cuts(stack, after):
    """자를 자리(이 컷 **뒤**에서 가른다) → (보이는 컷을 나눈 조각들, 문제 목록)"""
    bad = _check(stack)
    if bad:
        return [], bad
    frames = visible_frames(stack)
    by_id = {f.id: f for f in frames}
    want = set()
    for raw in after:
        try:
            fid = int(str(raw).strip())
        except ValueError:
            bad.append(f"{raw}: 컷 번호가 아니다")
            continue
        if fid not in by_id:
            bad.append(f"{fid}: 이 묶음의 보이는 컷이 아니다")
        elif frames and fid == frames[-1].id:
            bad.append(f"{by_id[fid].path.rsplit('/', 1)[-1]}: 마지막 컷이다 — 그 뒤에서 가를 것이 없다")
        else:
            want.add(fid)
    if not bad and not want:
        bad.append("자를 자리를 하나도 고르지 않았다")
    if bad:
        return [], bad
    pieces, cur = [], []
    for f in frames:
        cur.append(f)
        if f.id in want:
            pieces.append(cur)
            cur = []
    pieces.append(cur)
    return pieces, []


def split_preview(stack, after):
    pieces, bad = _cuts(stack, after)
    if bad:
        return {"ok": False, "errors": bad}
    return {"ok": True, "errors": [], "pieces": [[_row(f) for f in p] for p in pieces],
            "hidden": stack.frames.filter(hidden=True).count()}


@transaction.atomic
def apply_split(stack, after):
    """첫 조각은 이 묶음에 남고(숨긴 컷도 여기에), 나머지는 같은 이름의 새 조각 묶음이 된다. → 새 묶음 id 들"""
    pieces, bad = _cuts(stack, after)
    if bad:
        raise ValueError(" · ".join(bad))
    now = timezone.now()
    top = (Stack.objects.filter(source_dir=stack.source_dir, kind=stack.kind, label=stack.label)
           .aggregate(m=Max("piece"))["m"] or 0)
    hidden = list(stack.frames.filter(hidden=True).order_by("seq"))
    _renumber(stack, pieces[0] + hidden)
    made = []
    for k, piece in enumerate(pieces[1:], 1):
        new = Stack.objects.create(
            slab=stack.slab, specimen=stack.specimen, kind=stack.kind, preparation=stack.preparation,
            view=stack.view, label=stack.label, source_dir=stack.source_dir, piece=top + k,
            camera=stack.camera)
        _renumber(new, piece)
        _refresh(new, now)
        made.append(new.id)
    _refresh(stack, now)            # 조각을 다 옮긴 뒤에 — 그 전에는 남은 컷이 아직 이 묶음에 있다
    _log("split", stack, pieces=[[f.path for f in p] for p in pieces], new_stacks=made)
    return made


# ── 합치기 ────────────────────────────────────────────────

def _merge_pair(stack, other_id):
    bad = _check(stack)
    try:
        other = Stack.objects.get(id=int(str(other_id).strip()))
    except (ValueError, Stack.DoesNotExist):
        return None, bad + [f"{other_id}: 그런 묶음이 없다"]
    if other.id == stack.id:
        bad.append("자기 자신과는 합치지 않는다")
    elif other.slab_id != stack.slab_id:
        bad.append(f"다른 슬랩의 묶음이다 ({other.slab.slab_no})")
    else:
        bad += [f"{other.label}: {e}" for e in _check(other)]
    return other, bad


def merge_preview(stack, other_id):
    other, bad = _merge_pair(stack, other_id)
    if bad:
        return {"ok": False, "errors": bad}
    notes = []
    if other.preparation != stack.preparation:
        notes.append(f"처리가 다르다 — {stack.get_preparation_display()} 와 {other.get_preparation_display()}. "
                     f"합친 묶음은 {stack.get_preparation_display()} 로 남는다")
    return {"ok": True, "errors": [], "other": other, "notes": notes,
            "rows": [_row(f) for f in visible_frames(stack)],
            "other_rows": [_row(f) for f in visible_frames(other)],
            "copies": _copies(other)}


@transaction.atomic
def apply_merge(stack, other_id):
    """`other` 의 컷을 이 묶음 뒤에 붙이고 `other` 는 숨긴다(행은 남는다 — 반입이 도로 만들지 않게)."""
    other, bad = _merge_pair(stack, other_id)
    if bad:
        raise ValueError(" · ".join(bad))
    now = timezone.now()
    moved = [f.path for f in other.frames.order_by("seq")]
    _renumber(stack, _ordered(list(stack.frames.order_by("seq")) + list(other.frames.order_by("seq"))))
    _refresh(stack, now)
    copies = _hide(other, now)
    _log("merge", stack, merged=other.id, frames=moved, copies_hidden=copies)
    return stack.id


# ── 지우기 · 되살리기 ─────────────────────────────────────

def _hide(stack, now):
    """묶음과 그 사본을 숨긴다. → 숨긴 사본 id 들"""
    copies = [c.id for c in _copies(stack)]
    Stack.objects.filter(id__in=copies).update(hidden=True, edited_at=now)
    stack.hidden = True
    _refresh(stack, now)
    return copies


def delete_preview(stack):
    bad = _check(stack)
    if bad:
        return {"ok": False, "errors": bad}
    return {"ok": True, "errors": [], "rows": [_row(f) for f in visible_frames(stack)],
            "copies": _copies(stack)}


@transaction.atomic
def apply_delete(stack):
    bad = _check(stack)
    if bad:
        raise ValueError(" · ".join(bad))
    copies = _hide(stack, timezone.now())
    _log("delete", stack, copies_hidden=copies)
    # 슬랩 화면으로 돌아간다 — 숨긴 묶음은 거기 「지운 묶음」 칸에 있다
    return stack.slab.slab_no


@transaction.atomic
def restore(stack):
    """지운 묶음을 되살린다. 함께 숨은 사본은 따로 되살린다(슬랩 화면의 「지운 묶음」 칸)."""
    if not stack.hidden:
        raise ValueError("지운 묶음이 아니다")
    stack.hidden = False
    _refresh(stack, timezone.now())
    _log("restore", stack)


# ── 컷 숨기기 ─────────────────────────────────────────────

@transaction.atomic
def hide_frame(frame):
    """컷 하나를 숨긴다 — 딴 구도 컷이 섞였을 때. 되살릴 수 있어 확인을 거치지 않는다."""
    stack = frame.stack
    bad = _check(stack)
    if frame.hidden:
        bad.append("이미 숨긴 컷이다")
    elif stack.frames.filter(hidden=False).count() < 2:
        bad.append("마지막 컷이다 — 묶음을 지운다")
    if bad:
        raise ValueError(" · ".join(bad))
    frame.hidden = True
    frame.save(update_fields=["hidden"])
    _renumber(stack, _ordered(list(stack.frames.order_by("seq"))))
    _refresh(stack, timezone.now())
    _log("hide_frame", stack, frame=frame.path)


@transaction.atomic
def show_frame(frame):
    """숨긴 컷을 되살린다 — 원래 컷 번호 차례의 자리로."""
    stack = frame.stack
    bad = _check(stack)
    if not frame.hidden:
        bad.append("숨긴 컷이 아니다")
    if bad:
        raise ValueError(" · ".join(bad))
    frame.hidden = False
    frame.save(update_fields=["hidden"])
    frames = list(stack.frames.order_by("seq"))
    # 되살린 컷만 번호 차례의 자리로 끼운다 — 나머지는 사람이 만든 차례(합친 차례)를 그대로.
    # 자리는 같은 폴더에서 번호가 그보다 큰 첫 컷의 앞(폴더가 다르면 번호를 비교하지 않는다)
    shown = [f for f in frames if not f.hidden and f.id != frame.id]
    folder = frame.path.rsplit("/", 1)[0]
    at = next((i for i, f in enumerate(shown) if f.path.rsplit("/", 1)[0] == folder and f.shot_no is not None
               and frame.shot_no is not None and f.shot_no > frame.shot_no), len(shown))
    shown.insert(at, frame)
    _renumber(stack, shown + [f for f in frames if f.hidden])
    _refresh(stack, timezone.now())
    _log("show_frame", stack, frame=frame.path)
