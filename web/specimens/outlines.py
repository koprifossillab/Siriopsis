"""표본 테두리 그리기·고치기·지우기 (wetherilli 011). 화면도 반입도 이 모듈만 부른다.

**한 더미에 테두리 하나**(사용자가 받아들인 TODOs 2번 검토). DiaRUGA 의 판정·개체·대표·번지기(`ObjectReview`·`DiatomObject`·
`_spread_drawn`)는 가져오지 않았다 — 테두리가 더미에 붙으면 「모든 컷에 퍼진다」는 따로 할 일이 없다.

- 좌표는 **그린 컷의 원본 화소**. 그 컷이 이 더미의 보이는 컷인지, 점이 컷 안인지 서버가 본다
- 계측값은 서버가 다시 잰다(`shape.measure`) — 브라우저가 보낸 면적을 믿으면 브라우저마다 다른 값이 앉는다(DiaRUGA P09 5.8)
- 저장·지우기는 사람의 손 → 더미에 `edited_at`(반입이 덮지 않게, 008)과 `EditLog`
- 고칠 수 있는 더미는 빛 묶음과 PTM. 슬랩 전경(`slab`)은 표본이 아니라 슬랩을 찍은 것이라 안 받는다. 지운 더미도 안 받는다

가르기는 테두리가 그린 컷을 따라가고, 합치기는 받는 쪽 것을 남긴다(`regroup.py`).
"""
import json

from django.db import transaction
from django.utils import timezone

from . import scales, shape
from .models import EditLog, Frame, Outline, Stack

MAX_POINTS = 2000
# 컷 가장자리를 살짝 넘는 점은 받아 가장자리로 당긴다(끝을 누를 때 손이 밀린다). 그보다 멀면 잘못 보낸 것이다
EDGE_SLACK = 0.02


def of(stack):
    try:
        return stack.outline
    except Outline.DoesNotExist:
        return None


def _check(stack):
    if stack.kind not in (Stack.Kind.SERIES, Stack.Kind.PTM):
        return [f"{stack.get_kind_display()} 더미에는 테두리를 그리지 않는다 — 빛 묶음과 PTM 만"]
    if stack.hidden:
        return ["지운 묶음이다 — 되살린 뒤에 그린다"]
    return []


def parse_points(raw, width, height):
    """`[[x, y], …]`(JSON 글자 또는 목록) → (점 목록, 문제 목록)"""
    try:
        pts = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return [], ["점이 JSON 이 아니다"]
    if not isinstance(pts, list):
        return [], ["점이 목록이 아니다"]
    if len(pts) < shape.MIN_POINTS:
        return [], [f"점이 {len(pts)} 개 — 셋은 있어야 한다"]
    if len(pts) > MAX_POINTS:
        return [], [f"점이 {len(pts)} 개 — {MAX_POINTS} 개까지"]
    out = []
    sx, sy = width * EDGE_SLACK, height * EDGE_SLACK
    for p in pts:
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            return [], [f"{p!r}: 점이 아니다"]
        if not (-sx <= x <= width + sx and -sy <= y <= height + sy):
            return [], [f"({x:.0f}, {y:.0f}): 컷({width}×{height}) 바깥이다"]
        out.append([round(min(max(x, 0.0), width), 1), round(min(max(y, 0.0), height), 1)])
    if shape.area(out) <= 0:
        return [], ["넓이가 없다 — 점이 한 줄에 있다"]
    return out, []


@transaction.atomic
def save(stack, frame_id, raw_points):
    """그리기·고치기 모두. → Outline. 이상하면 ValueError (아무것도 안 바꾼다)"""
    bad = _check(stack)
    try:
        frame = stack.frames.get(id=int(str(frame_id).strip()), hidden=False)
    except (ValueError, Frame.DoesNotExist):
        bad.append(f"{frame_id}: 이 더미의 보이는 컷이 아니다")
        frame = None
    if bad:
        raise ValueError(" · ".join(bad))
    if not (frame.width and frame.height):
        raise ValueError(f"{frame.path}: 컷의 크기를 모른다")
    pts, bad = parse_points(raw_points, frame.width, frame.height)
    if bad:
        raise ValueError(" · ".join(bad))
    m = shape.measure([tuple(p) for p in pts])
    had = of(stack) is not None
    out, _ = Outline.objects.update_or_create(stack=stack, defaults=dict(
        frame_path=frame.path, width=frame.width, height=frame.height, points=pts, **m))
    stack.edited_at = timezone.now()
    stack.save(update_fields=["edited_at"])
    EditLog.objects.create(action="outline", stack=stack,
                           detail={"frame": frame.path, "points": len(pts), "replaced": had})
    return out


@transaction.atomic
def delete(stack):
    bad = _check(stack)
    if of(stack) is None:
        bad.append("테두리가 없다")
    if bad:
        raise ValueError(" · ".join(bad))
    o = stack.outline
    EditLog.objects.create(action="outline_delete", stack=stack, detail={"frame": o.frame_path, "points": o.points})
    o.delete()
    stack.edited_at = timezone.now()
    stack.save(update_fields=["edited_at"])


def numbers(outline, stack):
    """화면에 적을 값 — 배율이 그린 컷에 맞으면 mm·mm² 도. → [(이름, 값 글자)]"""
    sc = scales.of(stack)
    mmpp = sc.mm_per_px if sc and sc.fits(outline.width, outline.height) else None

    def length(px):
        if px is None:
            return "—"
        return f"{px * mmpp:.2f} mm" if mmpp else f"{px:.0f} px"

    area = (f"{outline.area_px * mmpp * mmpp:.2f} mm²" if mmpp else f"{outline.area_px:.0f} px²")
    return {"mm": bool(mmpp), "rows": [
        ("넓이", area), ("둘레", length(outline.perimeter_px)),
        ("길이 · 폭", f"{length(outline.long_px)} · {length(outline.short_px)}"),
        ("장축 · 단축", f"{length(outline.major_px)} · {length(outline.minor_px)}"),
    ]}
