"""템플릿이 늘 쓰는 값 — 판 번호와 자리 이름 (ForGIA `viewer/context.py` 에서 왔다).

**판을 화면에 띄우는 이유**: 배포가 실제로 갈렸는지, 지금 보는 화면이 어느 판인지를
눈으로 확인할 수 있어야 한다 (.guides/branding.md §2). 값은 `.env` 의 `IMAGE_TAG` —
배포 스크립트가 그 한 줄을 고치므로 배포한 것과 화면에 뜨는 것이 같은 값이다.

**자리 이름**(`SIRIOPSIS_ENV_LABEL`)은 운영이 아닌 자리를 화면 전체 워터마크로 알린다.
운영과 시험이 같은 오리진에 같은 모양으로 뜨면 주소창 말고는 구분할 것이 없다.
`DEBUG` 가 켜져 있고 이름이 없으면 `DEFAULT_DEV_LABEL` 로 뜬다 — 개발 서버에서
켜는 것을 기억에 맡기지 않는다. 운영 `.env` 는 `SIRIOPSIS_DEBUG=0` 이고 이 줄이 없다.
"""
import os

from django.conf import settings

DEFAULT_DEV_LABEL = "Test Server"


def version(request):
    return {
        "image_tag": os.environ.get("IMAGE_TAG", ""),
        "env_label": (os.environ.get("SIRIOPSIS_ENV_LABEL", "").strip()
                      or (DEFAULT_DEV_LABEL if settings.DEBUG else "")),
    }
