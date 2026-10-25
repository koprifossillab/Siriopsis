import os
import time

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def healthz(request):
    """판·DB·안전망 상태를 한 번에 낸다 (DiaRUGA·ForGIA `/healthz` 와 같은 모양).

    | 상태 | 코드 | 뜻 |
    |---|---|---|
    | `ok` | 200 | 정상 |
    | `degraded` | **200** | 서비스는 되는데 손상이 감지됐다 (백업이 낡았다) |
    | `unhealthy` | 503 | DB 를 못 연다 |

    **`degraded` 를 503 으로 두지 않는다** — 배포의 기동 게이트가 200 을 기다린다.
    배포를 막는 일은 smoke 가 `status != ok` 로 한다 (.guides/web/operations.md §4).

    도메인 테이블이 생기면 **핵심 행 수 ≠ 0** 검사를 여기 더한다 — 마운트가 어긋나
    빈 DB 가 새로 만들어져도 "DB 가 열린다" 는 통과하기 때문이다.
    """
    info = {"status": "ok", "version": os.environ.get("IMAGE_TAG", "")}
    notes = []

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        info["db"] = "ok"
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

    info["notes"] = notes
    code = 503 if info["status"] == "unhealthy" else 200
    resp = JsonResponse(info, status=code, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "no-store"
    return resp
