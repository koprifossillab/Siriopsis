import html
import json
import os
import re
import time

from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe


def healthz(request):
    """판·DB·안전망 상태를 한 번에 낸다 (DiaRUGA·ForGIA `/healthz` 와 같은 모양).

    | 상태 | 코드 | 뜻 |
    |---|---|---|
    | `ok` | 200 | 정상 |
    | `degraded` | **200** | 서비스는 되는데 손상이 감지됐다 (백업이 낡았다) |
    | `unhealthy` | 503 | DB 를 못 연다 |

    **`degraded` 를 503 으로 두지 않는다** — 배포의 기동 게이트가 200 을 기다린다.
    배포를 막는 일은 smoke 가 `status != ok` 로 한다 (.guides/web/operations.md §4).

    **핵심 행 수 ≠ 0** — 컷(Frame)이 하나도 없으면 degraded. 마운트가 어긋나 빈 DB 가 새로
    만들어져도 "DB 가 열린다" 는 통과하기 때문이다.
    """
    info = {"status": "ok", "version": os.environ.get("IMAGE_TAG", "")}
    notes = []

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        info["db"] = "ok"
        from specimens.models import Frame, Stack
        info["stacks"] = Stack.objects.count()
        info["frames"] = Frame.objects.count()
        if info["frames"] == 0:
            info["status"] = "degraded"
            notes.append("컷이 하나도 없다 — DB 가 비었거나 반입(scan_light_stacks)을 안 했다")
    except Exception as e:                       # noqa: BLE001 — 무엇이 나오든 죽지 않는다
        info["status"] = "unhealthy"
        info["db"] = None
        notes.append(f"DB 를 읽지 못했다: {e}")

    age_h = None
    try:
        snaps = list(settings.BACKUP_DIR.glob("Siriopsis_*.db"))
        if snaps:
            newest = max(snaps, key=lambda p: p.stat().st_mtime)
            age_h = round((time.time() - newest.stat().st_mtime) / 3600, 1)
    except OSError:
        pass
    info["backup"] = {"age_h": age_h, "max_age_h": settings.BACKUP_MAX_AGE_H}
    if settings.BACKUP_MAX_AGE_H and (age_h is None or age_h > settings.BACKUP_MAX_AGE_H):
        if info["status"] == "ok":
            info["status"] = "degraded"
        notes.append("백업 사본이 없다" if age_h is None else
                     f"백업이 낡았다 — 가장 새 사본이 {age_h} 시간 전 "
                     f"(문턱 {settings.BACKUP_MAX_AGE_H})")

    # 백업 스크립트가 세운 실패 깃발 (`ops/backup_db.py` — BACKUP_FAIL.backup · BACKUP_FAIL.offsite). 문턱과 상관없이 본다
    try:
        flags = sorted(settings.BACKUP_DIR.glob("BACKUP_FAIL.*"))
    except OSError:
        flags = []
    for f in flags:
        info["status"] = "degraded" if info["status"] == "ok" else info["status"]
        try:
            notes.append(f"백업 실패 ({f.suffix[1:]}): {f.read_text(encoding='utf-8').strip()}")
        except OSError:
            notes.append(f"백업 실패 ({f.suffix[1:]})")

    off_h = None
    try:
        at = json.loads((settings.BACKUP_DIR / "offsite_status.json").read_text(encoding="utf-8"))["at"]
        off_h = round((time.time() - at) / 3600, 1)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    info["backup"]["offsite_age_h"] = off_h
    if settings.OFFSITE_MAX_AGE_H and (off_h is None or off_h > settings.OFFSITE_MAX_AGE_H):
        info["status"] = "degraded" if info["status"] == "ok" else info["status"]
        notes.append("NAS 로 간 사본이 없다" if off_h is None else
                     f"NAS 사본이 낡았다 — {off_h} 시간 전 (문턱 {settings.OFFSITE_MAX_AGE_H})")

    info["notes"] = notes
    code = 503 if info["status"] == "unhealthy" else 200
    resp = JsonResponse(info, status=code, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "no-store"
    return resp


# 이름 넷만 받는다 — 경로를 받지 않는다
SPLASH_ASSETS = {"ondark.webp": "image/webp", "onlight.webp": "image/webp",
                 "ondark.png": "image/png", "onlight.png": "image/png"}


def splash_asset(request, name):
    """대기 화면 로고 (DiaRUGA `splash_asset` 에서 왔다). 정적 파일을 내보내는 길이 없어 뷰가 낸다.

    밝은·어두운 테마마다 한 벌 — 투명 배경 webp 라 테마 바탕 위에 그대로 얹힌다(DiaRUGA 의 GIF 는 바탕색을 박아 구웠다).
    """
    ctype = SPLASH_ASSETS.get(name)
    if not ctype:
        raise Http404(name)
    from .context import SPLASH_DIR
    resp = FileResponse((SPLASH_DIR / name).open("rb"), content_type=ctype)
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


REPO_URL = "https://github.com/koprifossillab/Siriopsis"
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_CODE = re.compile(r"`([^`]+)`")


def _md_inline(text):
    """CHANGELOG 한 칸의 마크다운 → HTML. 링크·`코드`·**굵게**만 — 그 밖은 글자로 둔다.

    devlog 링크는 상대경로라 이미지 안에서 열 곳이 없다(문서는 이미지에 안 넣는다) — GitHub 의 그 파일로 바꾼다.
    """
    out = html.escape(text, quote=False)
    out = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)

    def link(m):
        href = m.group(2)
        if not re.match(r"^https?://", href):
            href = f"{REPO_URL}/blob/main/{href.lstrip('./')}"
        return f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{m.group(1)}</a>'
    return mark_safe(_LINK.sub(link, out))


def changelog(path=None):
    """CHANGELOG.md 의 표 → [{"ver", "date", "what"}], 새것부터. 파일이 없으면 빈 목록."""
    path = path or settings.PROJECT_ROOT / "CHANGELOG.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # 머리줄과 가름줄(`|---|`)은 건너뛴다
        if len(cells) < 3 or cells[0] == "판" or re.fullmatch(r"[-: ]+", cells[0]):
            continue
        rows.append({"ver": cells[0], "date": cells[1], "what": _md_inline("|".join(cells[2:]))})
    return rows[::-1]


def system(request):
    """설정 화면 — 오른쪽 위 톱니 (사용자 2026-10-25). 지금 판·판 이력·자료 현황·자리.

    DiaRUGA `/system/` 의 자리지만 **읽기만 한다** — 바꿀 설정이 아직 없다. 판 이력은 CHANGELOG.md 를 그대로 읽는다(적는 곳은 하나).
    """
    from django.db.models import Count, Max, Q
    from specimens.models import Frame, Slab, Specimen, Stack

    stacks = Stack.objects.aggregate(
        series=Count("id", filter=Q(kind=Stack.Kind.SERIES, copy_of__isnull=True)),
        ptm=Count("id", filter=Q(kind=Stack.Kind.PTM)),
        slabview=Count("id", filter=Q(kind=Stack.Kind.SLAB, copy_of__isnull=True)),
        copies=Count("id", filter=Q(copy_of__isnull=False)))
    stats = {
        "slabs": Slab.objects.count(),
        "slabs_catalog": Slab.objects.filter(catalog_id__isnull=False).count(),
        "specimens": Specimen.objects.count(),
        "taxa": Specimen.objects.exclude(taxon_name="").count(),
        "frames": Frame.objects.count(),
        "synced": Slab.objects.aggregate(t=Max("catalog_synced_at"))["t"],
        **stacks,
    }
    years = list(Slab.objects.values_list("year").annotate(n=Count("id")).order_by("year"))
    return render(request, "core/system.html", {
        "log": changelog(), "stats": stats, "years": years, "repo": REPO_URL,
        "places": [
            ("원본 (읽기만)", settings.SOURCE_ROOT),
            ("DB", settings.SIRIOPSIS_DB),
            ("축소본 캐시", settings.THUMB_CACHE),
            ("분류 정보", settings.CATALOG_LINK_URL),
        ],
    })
