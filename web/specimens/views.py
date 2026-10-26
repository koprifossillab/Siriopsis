"""뷰어 화면 — 목록 → 슬랩 → 더미 (P01 2단계, wetherilli 005).

DiaRUGA 의 데이터셋 → 슬라이드 → 시야 자리다. 더미 화면은 **종류마다 다르게 건다**(사용자 2026-10-25):
PTM 은 빛 방향 판(50 방향을 위에서 내려다본 원), 빛 묶음은 번호 줄. 큰 그림의 확대·이동은 둘이 같다(`_zoomview.html`).
"""
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import browse, epma, outlines, regroup, scales, thumbs, workbook
from .models import EpmaChannel, EpmaSession, Frame, Slab, Stack

PER_PAGE = 48
# 종류 거르기 — 더미의 종류에 EPMA 세션(018)을 나란히 둔다. EPMA 는 Stack 이 아니라 따로 된 테이블이다
EPMA = "epma"
KINDS = Stack.Kind.choices + [(EPMA, "EPMA")]


def _first_frames(stack_ids):
    """{더미 id: 보이는 첫 컷 id}. 빛 묶음의 1 번은 고른 빛에 자가 있는 컷이라 대표로 맞다. 숨긴 컷은 뒤에 있다(`regroup`)."""
    out = {}
    for sid, fid in (Frame.objects.filter(stack_id__in=stack_ids, hidden=False)
                     .order_by("stack_id", "seq").values_list("stack_id", "id")):
        out.setdefault(sid, fid)
    return out


def home(request):
    """슬랩 목록 — 채집 연도 탭 → 번호 구간(NAS 의 열 개 폴더)·층준 구간 → 슬랩 (`browse.py`). DiaRUGA 목록처럼 표(`list`)와 격자(`grid`) 두 모양.

    찾기(`q`)는 슬랩 번호·분류군·문, 거르기는 종류(빛 묶음·PTM·전경·EPMA)·☆ 별표·짝. 표는 한 연도를 통째로 내고(가장 많은 2017 이 2,317 줄), 격자는 쪽으로 나눈다.
    """
    q = (request.GET.get("q") or "").strip()
    kind = (request.GET.get("kind") or "").strip()
    mode = "grid" if request.GET.get("view") == "grid" else "list"
    by = "horizon" if request.GET.get("by") == "horizon" else "no"
    ys = browse.years()
    try:
        year = int(request.GET.get("y") or 0)
    except ValueError:
        year = 0
    if year not in {y for y, _ in ys}:
        year = 0

    slabs = Slab.objects.filter(Q(stacks__hidden=False) | Q(epma_sessions__isnull=False))
    if year:
        slabs = slabs.filter(year=year)
    if q:
        slabs = slabs.filter(Q(slab_no__icontains=q) | Q(specimens__taxon_name__icontains=q)
                             | Q(specimens__phylum__icontains=q))
    if kind == EPMA:
        slabs = slabs.filter(epma_sessions__isnull=False)
    elif kind in Stack.Kind.values:
        slabs = slabs.filter(stacks__kind=kind, stacks__hidden=False)
    # ☆ 별표·짝으로 거르기 (사용자 2026-10-26) — 둘 다 켜면 둘 다 가진 슬랩
    star = request.GET.get("star") == "1"
    pair = request.GET.get("pair") == "1"
    stars, pairs = workbook.slab_marks()
    if star:
        slabs = slabs.filter(slab_no__in=list(stars))
    if pair:
        slabs = slabs.filter(slab_no__in=list(pairs))
    slabs = slabs.distinct().order_by("slab_no")

    keep = {k: v for k, v in (("q", q), ("kind", kind), ("star", "1" if star else ""), ("pair", "1" if pair else ""),
                              ("by", "horizon" if by == "horizon" else "")) if v}
    ctx = {"q": q, "kind": kind, "star": star, "pair": pair, "by": by, "kinds": KINDS, "mode": mode, "year": year,
           "years": ys, "total_slabs": sum(n for _, n in ys), "keep": keep}

    def mark(rows):
        for r in rows:
            r["stars"] = "☆" * stars.get(r["slab"].slab_no, 0)
            r["pairs"] = pairs.get(r["slab"].slab_no, [])
        return rows

    if mode == "list":
        rows = mark(browse.slab_rows(list(slabs)))
        groups = browse.tree(rows, by)
        ctx.update(groups=groups, n_rows=len(rows), sums={
            f: sum(g[f] for g in groups) for f in ("n_specimens", "series", "ptm", "epma", "copies", "frames")})
        return render(request, "specimens/home.html", ctx)

    page = Paginator(slabs, PER_PAGE).get_page(request.GET.get("page"))
    rows = mark(browse.slab_rows(list(page)))
    # 슬랩마다 대표 더미 하나 — 정본 빛 묶음을 먼저(PTM 첫 컷은 낮은 빛이라 어둡다)
    rep = {}
    for st in (Stack.objects.filter(slab_id__in=[r["slab"].id for r in rows], copy_of__isnull=True, hidden=False)
               .order_by("slab_id", "-kind", "label")):        # "series" > "ptm"
        rep.setdefault(st.slab_id, st.id)
    first = _first_frames(rep.values())
    for r in rows:
        r["frame"] = first.get(rep.get(r["slab"].id))
    ctx.update(rows=rows, page=page, n_rows=page.paginator.count)
    return render(request, "specimens/home.html", ctx)


def slab(request, slab_no):
    """슬랩 하나 (사용자 2026-10-25): 왼쪽에 대표 이미지(전경)와 속성 상자, 오른쪽에 더미 카드 줄 — 표본마다 끊고, 글자 없는 것·지운 것은 뒤에."""
    s = get_object_or_404(Slab, slab_no=slab_no)
    stacks = list(s.stacks.filter(copy_of__isnull=True, hidden=False).select_related("specimen")
                  .order_by("kind", "preparation", "view", "label", "piece"))
    hidden = list(s.stacks.filter(hidden=True).order_by("label", "piece", "source_dir"))
    first = _first_frames([st.id for st in stacks])
    for st in stacks:
        st.first_frame = first.get(st.id)

    # 슬랩 전경(009)은 표본 칸이 아니라 맨 위에 — 슬랩 자체를 찍은 사진이다
    overview = [st for st in stacks if st.kind == Stack.Kind.SLAB]
    # 두 슬랩을 한 장에 찍은 전경(`SP-2016-64&65`)은 반입이 앞 번호에 붙인다 — 뒷 슬랩에서도 보이게 더한다 (013)
    shared = workbook.shared_views(s)
    first.update(_first_frames([st.id for st in shared]))
    for st in shared:
        st.first_frame = first.get(st.id)
    overview += shared
    stacks = [st for st in stacks if st.kind != Stack.Kind.SLAB]
    # EPMA 세션(018)은 빛 묶음·PTM 과 나란한 자료 — 같은 표본 칸에 카드로 넣는다. 표본이 안 정해진 세션은 「표본 글자 없음」 칸에
    sessions = _epma_sessions(s)
    groups = []
    for sp in s.specimens.all():
        mine = [st for st in stacks if st.specimen_id == sp.id]
        ep = [e for e in sessions if e.specimen_id == sp.id]
        if mine or ep:
            groups.append({"specimen": sp, "stacks": mine, "epma": ep})
    loose = [st for st in stacks if st.specimen_id is None]
    loose_epma = [e for e in sessions if e.specimen_id is None]
    # 왼쪽 칸 (사용자 2026-10-25): 대표 이미지는 정본 전경의 첫 컷, 없으면 첫 빛 묶음. 아래 상자에 슬랩의 속성
    # vent(뜻을 아직 모른다)는 dorsal 이 없을 때만 대표가 된다
    rep = (next((st for st in overview if not st.copy_of_id and "(vent)" not in st.label), None)
           or next((st for st in overview if not st.copy_of_id), None) or next(iter(stacks), None))
    # vent 는 dorsal 과 나란히 (사용자 2026-10-26 「vent 는 dorsal 하고 병렬적으로」) — 대표가 dorsal 일 때만 짝을 짓는다
    vent = None
    if rep is not None and rep.kind == Stack.Kind.SLAB and "(vent)" not in rep.label:
        vent = next((st for st in overview if not st.copy_of_id and "(vent)" in st.label and st.first_frame), None)
    dates = [st.captured_at for st in stacks + overview if st.captured_at]
    facts = {
        "n_stacks": len(stacks), "n_frames": sum(st.n_frames for st in stacks),
        "n_ptm": sum(st.kind == Stack.Kind.PTM for st in stacks), "n_epma": len(sessions),
        "copies": s.stacks.filter(copy_of__isnull=False, hidden=False).count(),
        "first": min(dates) if dates else None, "last": max(dates) if dates else None,
        "taxa": sorted({sp.taxon_name for sp in s.specimens.all() if sp.taxon_name}),
    }
    first.update(_hidden_first(hidden))
    for st in hidden:
        st.first_frame = first.get(st.id)
    return render(request, "specimens/slab.html", {
        "slab": s, "groups": groups, "loose": loose, "hidden": hidden, "overview": overview,
        "rep": rep, "vent": vent, "heropair": [rep, vent] if vent else [], "facts": facts, "specimens": list(s.specimens.all()),
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
        # counterpart 짝 (013) — `{% include "specimens/_counterpart.html" %}` 가 그린다
        "counterparts": _counterparts(s),
        "loose_epma": loose_epma,
    })


def _epma_sessions(s):
    """이 슬랩의 EPMA 세션 (018) — 대표 채널과 맵·채널 수를 붙인다."""
    from django.db.models import Count
    sessions = list(s.epma_sessions.select_related("specimen")
                    .annotate(n_maps=Count("maps", distinct=True), n_channels=Count("maps__channels")))
    epma.representative(sessions)
    return sessions


def epma_session(request, pk):
    """EPMA 세션 하나 (018) — 맵마다 채널, 고른 채널의 강도를 캔버스에(phyloserver `epma_interactive.js` 를 옮겼다)."""
    s = get_object_or_404(EpmaSession.objects.select_related("slab", "specimen"), pk=pk)
    maps = list(s.maps.prefetch_related("channels"))
    epma.representative([s])
    chans = [c for m in maps for c in m.channels.all()]
    try:
        cur = next(c for c in chans if c.id == int(request.GET.get("c", 0)))
    except (StopIteration, ValueError):
        cur = s.rep or next(iter(chans), None)
    return render(request, "specimens/epma.html", {
        "session": s, "maps": maps, "cur": cur, "n_channels": len(chans),
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
    })


def _epma_file(path, content_type):
    if path is None:
        raise Http404("파일이 없다")
    resp = FileResponse(path.open("rb"), content_type=content_type)
    # 채널 id 는 phyloserver 의 행과 함께 간다 — 파일은 갈아 끼우지 않는다(이름에 덧붙인 꼬리가 다르다)
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


def epma_image(request, pk):
    """`/epma/channel/<id>.jpg[?thumb=1]` — 채널 이미지(phyloserver 가 만든 것), 썸네일은 옆 `.thumbnails/`."""
    c = get_object_or_404(EpmaChannel, pk=pk)
    path = epma.thumb_path(c.image_file) if request.GET.get("thumb") else epma.file_path(c.image_file)
    return _epma_file(path, "image/jpeg")


def epma_data(request, pk):
    """`/epma/channel/<id>.bin` — 강도 값(gzip 째로, 풀기는 브라우저가). Content-Encoding 을 달지 않는다 — 뷰어가 직접 푼다."""
    c = get_object_or_404(EpmaChannel, pk=pk)
    return _epma_file(epma.file_path(c.binary_data_file), "application/octet-stream")


def _counterparts(s):
    """이 슬랩의 짝마다 상대 슬랩의 대표 컷 하나를 붙인다 — 전경 → 빛 묶음 → PTM."""
    pairs = workbook.pairs_for(s.slab_no)
    ids = [g["slab"].id for g in pairs if g["slab"]]
    rank = {Stack.Kind.SLAB: 0, Stack.Kind.SERIES: 1, Stack.Kind.PTM: 2}
    rep = {}
    for st in sorted(Stack.objects.filter(slab_id__in=ids, copy_of__isnull=True, hidden=False).order_by("label", "piece"),
                     key=lambda st: rank.get(st.kind, 9)):
        rep.setdefault(st.slab_id, st.id)
    first = _first_frames(rep.values())
    for g in pairs:
        g["frame"] = first.get(rep.get(g["slab"].id)) if g["slab"] else None
    return pairs


def starred(request):
    """별표 표본 (013) — 엑셀 목록과 phyloserver remarks 의 ☆. 사진이 없는 표본도 줄에 낸다(슬랩이 테이블에 없음)."""
    rows = workbook.starred()
    mode = "grid" if request.GET.get("view") == "grid" else "list"
    return render(request, "specimens/starred.html", {
        "rows": rows, "mode": mode, "n_with": sum(1 for r in rows if r["slab"]),
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
    })


def _hidden_first(stacks):
    """지운 묶음의 대표 컷 — 합쳐 비었으면 없다. 숨긴 컷이라도 낸다."""
    out = {}
    for sid, fid in (Frame.objects.filter(stack_id__in=[s.id for s in stacks])
                     .order_by("stack_id", "seq").values_list("stack_id", "id")):
        out.setdefault(sid, fid)
    return out


def stack(request, pk):
    st = get_object_or_404(Stack.objects.select_related("slab", "specimen", "copy_of"), pk=pk)
    frames = list(st.frames.filter(hidden=False))
    hidden_frames = list(st.frames.filter(hidden=True))
    primary = st.copy_of or st
    # 같은 묶음의 정본과 사본 — 어느 쪽을 보고 있든 같은 줄을 낸다
    family = [primary] + list(primary.copies.filter(hidden=False).order_by("source_dir"))
    # 이 슬랩의 다른 더미 — 왼쪽 칸의 격자(DiaRUGA 시야 격자 자리)와 PageUp/Down
    siblings = list(st.slab.stacks.filter(copy_of__isnull=True, hidden=False).select_related("specimen")
                    .order_by("kind", "preparation", "view", "label", "piece"))
    first = _first_frames([x.id for x in siblings])
    for x in siblings:
        x.first_frame = first.get(x.id)
    ids = [x.id for x in siblings]
    i = ids.index(primary.id) if primary.id in ids else -1
    prev_id = ids[i - 1] if i > 0 else None
    next_id = ids[i + 1] if 0 <= i < len(ids) - 1 else None

    # 배율 (wetherilli 010) — 잰 컷과 크기가 같은 컷에만. 없으면 화면은 스케일바를 안 그리고 길이를 px 로 적는다
    scale = scales.of(st)
    # 표본 테두리 (wetherilli 011) — 그린 컷과 크기가 같은 컷에만 얹는다
    outline = outlines.of(st)
    payload = [{"id": f.id, "seq": f.seq, "no": f.shot_no, "name": f.path.rsplit("/", 1)[-1],
                "w": f.width, "h": f.height, "mmpp": scale.mm_per_px if scale and scale.fits(f.width, f.height) else None,
                "ol": bool(outline and outline.fits(f.width, f.height)),
                "drawn": bool(outline and f.path == outline.frame_path),
                "x": f.light_x, "y": f.light_y, "z": f.light_z,
                "az": None if f.light_x is None else round(f.azimuth, 1),
                "el": None if f.light_z is None else round(f.elevation, 1)} for f in frames]
    return render(request, "specimens/stack.html", {
        "stack": st, "frames": frames, "payload": payload, "family": family if len(family) > 1 else [],
        "prev_id": prev_id, "next_id": next_id, "siblings": siblings, "primary_id": primary.id,
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
        "hidden_frames": hidden_frames, "scale": scale,
        "outline": outline, "outline_numbers": outlines.numbers(outline, st) if outline else None,
        "outline_data": {"points": outline.points, "w": outline.width, "h": outline.height} if outline else None,
        "drawable": not outlines._check(st),
        "scale_misfit": sum(1 for p in payload if p["mmpp"] is None) if scale and scale.mm_per_px else 0,
        # 묶음 고치기 칸 (008) — 빛 묶음만. 합칠 상대는 같은 슬랩의 빛 묶음(사본 포함)
        "editable": st.kind == Stack.Kind.SERIES and not st.hidden,
        "merge_targets": list(st.slab.stacks.filter(kind=Stack.Kind.SERIES, hidden=False)
                              .exclude(id=st.id).order_by("label", "piece", "source_dir")),
    })


# ── 묶음 고치기 (wetherilli 008) ────────────────────────────
# 묶음을 바꾸는 셋(가르기·합치기·지우기)은 **두 걸음이다 — 미리보기 다음에 확인**(DiaRUGA `split_group` 과 같다).
# 첫 POST 는 무엇이 어떻게 되는지 보여 주기만 하고, `confirm=1` 이 실린 두 번째 POST 만 고친다.
# 숨기기·되살리기는 되돌릴 수 있어 한 걸음이다. 고칠 수 없는 묶음(PTM·지운 것)은 화면이 아니라 **서버가** 막는다(`regroup._check`).

def _regroup_page(request, st, action, preview, extra=None):
    ctx = {"stack": st, "action": action, "preview": preview, "back_url": reverse("stack", args=[st.id])}
    ctx.update(extra or {})
    return render(request, "specimens/regroup_confirm.html", ctx, status=200 if preview["ok"] else 400)


def _bad(request, st, action, e):
    return _regroup_page(request, st, action, {"ok": False, "errors": [str(e)]})


@require_POST
def split_stack(request, pk):
    st = get_object_or_404(Stack, pk=pk)
    after = [a for a in request.POST.getlist("after") if a.strip()]
    if request.POST.get("confirm") == "1":
        try:
            regroup.apply_split(st, after)
        except ValueError as e:
            return _bad(request, st, "split", e)
        return redirect("stack", pk=st.id)
    return _regroup_page(request, st, "split", regroup.split_preview(st, after), {"after": after})


@require_POST
def merge_stack(request, pk):
    st = get_object_or_404(Stack, pk=pk)
    other = (request.POST.get("with") or "").strip()
    if request.POST.get("confirm") == "1":
        try:
            regroup.apply_merge(st, other)
        except ValueError as e:
            return _bad(request, st, "merge", e)
        return redirect("stack", pk=st.id)
    return _regroup_page(request, st, "merge", regroup.merge_preview(st, other), {"other": other})


@require_POST
def delete_stack(request, pk):
    st = get_object_or_404(Stack, pk=pk)
    if request.POST.get("confirm") == "1":
        try:
            slab_no = regroup.apply_delete(st)
        except ValueError as e:
            return _bad(request, st, "delete", e)
        return redirect("slab", slab_no=slab_no)
    return _regroup_page(request, st, "delete", regroup.delete_preview(st))


@require_POST
def restore_stack(request, pk):
    st = get_object_or_404(Stack, pk=pk)
    try:
        regroup.restore(st)
    except ValueError as e:
        return _bad(request, st, "restore", e)
    return redirect("stack", pk=st.id)


@require_POST
def frame_visibility(request, pk):
    """컷 숨기기(`hide=1`)·되살리기(`hide=0`). 한 걸음 — 되살릴 수 있다."""
    f = get_object_or_404(Frame.objects.select_related("stack"), pk=pk)
    try:
        if request.POST.get("hide") == "1":
            regroup.hide_frame(f)
        else:
            regroup.show_frame(f)
    except ValueError as e:
        return _bad(request, f.stack, "frame", e)
    return redirect("stack", pk=f.stack_id)


@require_POST
def outline(request, pk):
    """표본 테두리 저장(`frame`·`points`)·지우기(`delete=1`) (wetherilli 011). 한 걸음 — 다시 그리거나 고칠 수 있다."""
    st = get_object_or_404(Stack, pk=pk)
    try:
        if request.POST.get("delete") == "1":
            outlines.delete(st)
        else:
            outlines.save(st, request.POST.get("frame", ""), request.POST.get("points", ""))
    except ValueError as e:
        return _bad(request, st, "outline", e)
    return redirect("stack", pk=st.id)


def frame_image(request, pk):
    """`/frame/<id>.jpg?w=<폭>` — 컷 한 장. `w` 가 없으면 원본(확대해 들어갈 때만).

    파일 이름을 주소로 받지 않는다 — 컷 id 를 받아 테이블의 경로를 쓴다. 폴더 이름의 한글·빈칸·`&` 를 주소에 싣지 않는다.
    """
    f = get_object_or_404(Frame, pk=pk)
    path = thumbs.source_path(f.path)
    if path is None:
        raise Http404("원본이 없다")
    raw = request.GET.get("w")
    if raw:
        try:
            width = thumbs.snap_width(raw)
        except ValueError:
            raise Http404("w 가 수가 아니다")
        path = thumbs.thumbnail(path, width) or path
    resp = FileResponse(path.open("rb"), content_type="image/jpeg")
    # 컷 id 는 반입이 컷을 바꾸면 새로 난다 — 하루 캐시로 충분하다(같은 이름의 파일을 갈아 끼운 경우만 늦는다)
    resp["Cache-Control"] = "public, max-age=86400"
    return resp
