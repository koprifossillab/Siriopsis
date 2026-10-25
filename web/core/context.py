"""템플릿이 늘 쓰는 값 — 판 번호와 자리 이름 (ForGIA `viewer/context.py` 에서 왔다).

**판을 화면에 띄우는 이유**: 배포가 실제로 갈렸는지, 지금 보는 화면이 어느 판인지를
눈으로 확인할 수 있어야 한다 (.guides/branding.md §2). 값은 `.env` 의 `IMAGE_TAG` —
배포 스크립트가 그 한 줄을 고치므로 배포한 것과 화면에 뜨는 것이 같은 값이다.

**자리 이름**(`SIRIOPSIS_ENV_LABEL`)은 운영이 아닌 자리를 화면 전체 워터마크로 알린다.
운영과 시험이 같은 오리진에 같은 모양으로 뜨면 주소창 말고는 구분할 것이 없다.
`DEBUG` 가 켜져 있고 이름이 없으면 `DEFAULT_DEV_LABEL` 로 뜬다 — 개발 서버에서
켜는 것을 기억에 맡기지 않는다. 운영 `.env` 는 `SIRIOPSIS_DEBUG=0` 이고 이 줄이 없다.
"""
import json
import os
from pathlib import Path

from django.conf import settings

DEFAULT_DEV_LABEL = "Test Server"

# 대기 화면(첫 화면 로고) — DiaRUGA `viewer/context.py`(235)에서 왔다. 로고 애니메이션이 끝 장면에 닿는 시각을
# 함께 적어 두고(`logo.json`), 화면은 그때 정지 그림으로 바꾼다(애니메이션은 되풀이된다). 못 읽으면 0 — 정지 그림만 잠깐.
SPLASH_DIR = Path(__file__).resolve().parent / "assets" / "splash"
try:
    SPLASH_MS = int(json.loads((SPLASH_DIR / "logo.json").read_text(encoding="utf-8"))["build_ms"])
except (OSError, ValueError, KeyError):
    SPLASH_MS = 0


def version(request):
    return {
        "image_tag": os.environ.get("IMAGE_TAG", ""),
        "env_label": (os.environ.get("SIRIOPSIS_ENV_LABEL", "").strip()
                      or (DEFAULT_DEV_LABEL if settings.DEBUG else "")),
        "splash_ms": SPLASH_MS,
    }
