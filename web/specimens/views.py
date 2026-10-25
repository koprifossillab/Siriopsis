"""뷰어 화면 — 목록 → 슬랩 → 더미 (P01 2단계, wetherilli 005).

DiaRUGA 의 데이터셋 → 슬라이드 → 시야 자리다. 더미 화면은 **종류마다 다르게 건다**(사용자 2026-10-25):
PTM 은 빛 방향 판(50 방향을 위에서 내려다본 원), 빛 묶음은 번호 줄. 큰 그림의 확대·이동은 둘이 같다(`_zoomview.html`).
"""
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from . import browse, thumbs
from .models import Frame, Slab, Stack

PER_PAGE = 48


def _first_frames(stack_ids):
    """{더미 id: 첫 컷 id}. 빛 묶음의 1 번은 고른 빛에 자가 있는 컷이라 대표로 맞다."""
    return dict(Frame.objects.filter(stack_id__in=stack_ids, seq=0).values_list("stack_id", "id"))


def home(request):
    """슬랩 목록 — 채집 연도 탭 → 번호 구간(NAS 의 열 개 폴더)·층준 구간 → 슬랩 (`browse.py`). DiaRUGA 목록처럼 표(`list`)와 격자(`grid`) 두 모양.

    찾기(`q`)는 슬랩 번호·분류군·문, 거르기는 종류. 표는 한 연도를 통째로 내고(가장 많은 2017 이 2,317 줄), 격자는 쪽으로 나눈다.
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

    slabs = Slab.objects.filter(stacks__isnull=False)
    if year:
        slabs = slabs.filter(year=year)
    if q:
        slabs = slabs.filter(Q(slab_no__icontains=q) | Q(specimens__taxon_name__icontains=q)
                             | Q(specimens__phylum__icontains=q))
    if kind in Stack.Kind.values:
        slabs = slabs.filter(stacks__kind=kind)
    slabs = slabs.distinct().order_by("slab_no")

    keep = {k: v for k, v in (("q", q), ("kind", kind), ("by", "horizon" if by == "horizon" else "")) if v}
    ctx = {"q": q, "kind": kind, "by": by, "kinds": Stack.Kind.choices, "mode": mode, "year": year,
           "years": ys, "total_slabs": sum(n for _, n in ys), "keep": keep}

    if mode == "list":
        rows = browse.slab_rows(list(slabs))
        groups = browse.tree(rows, by)
        ctx.update(groups=groups, n_rows=len(rows), sums={
            f: sum(g[f] for g in groups) for f in ("n_specimens", "series", "ptm", "copies", "frames")})
        return render(request, "specimens/home.html", ctx)

    page = Paginator(slabs, PER_PAGE).get_page(request.GET.get("page"))
    rows = browse.slab_rows(list(page))
    # 슬랩마다 대표 더미 하나 — 정본 빛 묶음을 먼저(PTM 첫 컷은 낮은 빛이라 어둡다)
    rep = {}
    for st in (Stack.objects.filter(slab_id__in=[r["slab"].id for r in rows], copy_of__isnull=True)
               .order_by("slab_id", "-kind", "label")):        # "series" > "ptm"
        rep.setdefault(st.slab_id, st.id)
    first = _first_frames(rep.values())
    for r in rows:
        r["frame"] = first.get(rep.get(r["slab"].id))
    ctx.update(rows=rows, page=page, n_rows=page.paginator.count)
    return render(request, "specimens/home.html", ctx)


def slab(request, slab_no):
    """슬랩 하나 — 표본마다 더미를 {처리 × 배율} 칸으로. 표본 글자 없는 더미는 따로."""
    s = get_object_or_404(Slab, slab_no=slab_no)
    stacks = list(s.stacks.filter(copy_of__isnull=True).select_related("specimen")
                  .order_by("kind", "preparation", "view", "label"))
    first = _first_frames([st.id for st in stacks])
    for st in stacks:
        st.first_frame = first.get(st.id)

    groups = []
    for sp in s.specimens.all():
        mine = [st for st in stacks if st.specimen_id == sp.id]
        if mine:
            groups.append({"specimen": sp, "stacks": mine})
    loose = [st for st in stacks if st.specimen_id is None]
    return render(request, "specimens/slab.html", {
        "slab": s, "groups": groups, "loose": loose,
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
    })


def stack(request, pk):
    st = get_object_or_404(Stack.objects.select_related("slab", "specimen", "copy_of"), pk=pk)
    frames = list(st.frames.all())
    primary = st.copy_of or st
    # 같은 묶음의 정본과 사본 — 어느 쪽을 보고 있든 같은 줄을 낸다
    family = [primary] + list(primary.copies.order_by("source_dir"))
    # 이 슬랩의 다른 더미 — 왼쪽 칸의 격자(DiaRUGA 시야 격자 자리)와 PageUp/Down
    siblings = list(st.slab.stacks.filter(copy_of__isnull=True).select_related("specimen")
                    .order_by("kind", "preparation", "view", "label"))
    first = _first_frames([x.id for x in siblings])
    for x in siblings:
        x.first_frame = first.get(x.id)
    ids = [x.id for x in siblings]
    i = ids.index(primary.id) if primary.id in ids else -1
    prev_id = ids[i - 1] if i > 0 else None
    next_id = ids[i + 1] if 0 <= i < len(ids) - 1 else None

    payload = [{"id": f.id, "seq": f.seq, "no": f.shot_no, "name": f.path.rsplit("/", 1)[-1],
                "x": f.light_x, "y": f.light_y, "z": f.light_z,
                "az": None if f.light_x is None else round(f.azimuth, 1),
                "el": None if f.light_z is None else round(f.elevation, 1)} for f in frames]
    return render(request, "specimens/stack.html", {
        "stack": st, "frames": frames, "payload": payload, "family": family if len(family) > 1 else [],
        "prev_id": prev_id, "next_id": next_id, "siblings": siblings, "primary_id": primary.id,
        "catalog": settings.CATALOG_LINK_URL.rstrip("/") + "/",
    })


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
