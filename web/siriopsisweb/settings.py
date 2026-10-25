"""
Siriopsis 설정. Cropobite 001 의 뼈대(그 뿌리는 ForGIA v0.3 `web/forgiaweb/settings.py`)에서 왔다 (wetherilli 001).

도메인 앱이 아직 없다 — `core` 는 첫 화면과 `/healthz` 만 갖는다.
"""
import os
import tempfile
from pathlib import Path

# web/siriopsisweb/settings.py -> web/ -> 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def _load_dotenv(path):
    """프로젝트 루트의 .env 를 환경변수로 올린다 (이미 있는 값은 덮지 않는다).

    컨테이너는 compose 가 환경변수를 직접 주므로 이 파일 없이도 돈다 — 그래서
    없어도 조용히 넘어간다. KEY=VALUE 와 주석뿐, 따옴표·여러 줄·치환은 다루지 않는다.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(PROJECT_ROOT / ".env")

# 사내망 도구. 인증이 없으므로 공개망에 그대로 올릴 물건이 아니다.
SECRET_KEY = os.environ.get("SIRIOPSIS_SECRET_KEY", "dev-only-not-a-secret")
DEBUG = os.environ.get("SIRIOPSIS_DEBUG", "1") == "1"

# 이 서버가 실제로 응답할 이름만 적는다. "*" 로 두면 DEBUG 와 겹칠 때 Host 헤더
# 스푸핑을 그대로 받는다. 다른 이름이 필요하면 SIRIOPSIS_HOSTS 에 콤마로.
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    "172.16.116.98",    # 이 서버의 사내망 주소
    "paleo-server",     # 이 머신의 hostname
    "paleolab",         # nginx 80 블록의 server_name — 형제 앱이 같은 블록에 얹힌다
]
ALLOWED_HOSTS += [h.strip() for h in os.environ.get("SIRIOPSIS_HOSTS", "").split(",") if h.strip()]

# 서브경로 아래에 얹을 때 쓴다 (운영은 "/Siriopsis"). 빈 값이면 뿌리(/)에 붙는다.
# 사내 VPN 이 80 만 통과시키고 80 은 한 server 블록이 잡고 있어서, 형제 앱처럼
# 서브경로로 얹는 것 말고는 길이 없다 (.guides/web/operations.md §1).
# 템플릿에 절대경로를 박지 않는다 — {% url %} 이 이 값을 앞에 붙인다.
FORCE_SCRIPT_NAME = os.environ.get("SIRIOPSIS_SCRIPT_NAME", "").rstrip("/") or None

CSRF_TRUSTED_ORIGINS = [f"http://{h}" for h in ALLOWED_HOSTS if not h.startswith("[")]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "core",
    "specimens",
]

# 인증/세션이 없으므로 미들웨어도 최소한만. 로그인이 생기면 그때 더한다.
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]

ROOT_URLCONF = "siriopsisweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "core.context.version",     # 판 번호·자리 이름을 화면에 띄운다
        ]},
    }
]

WSGI_APPLICATION = "siriopsisweb.wsgi.application"

# 웹이 읽는 동안 다른 프로세스가 쓸 수 있게 WAL 로 연다. 서버를 떠나는 사본은
# journal_mode=DELETE 로 내린다 (.guides/web/data-safety.md §5).
SIRIOPSIS_DB = Path(os.environ.get("SIRIOPSIS_DB", "") or PROJECT_ROOT / "Siriopsis.db")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SIRIOPSIS_DB,
        "OPTIONS": {
            "timeout": 20,
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA foreign_keys=ON;"
            ),
        },
        # **시험 DB 는 파일로 만든다** (DiaRUGA 183) — 공유 캐시 인메모리 DB 는 잠금이
        # 테이블 단위라 브라우저 시험에서 기다려도 안 풀린다. 이름의 `test` 는
        # `core.tests.base.assert_test_db` 가 운영 DB 와 가르는 표식이다.
        "TEST": {
            "NAME": os.environ.get(
                "SIRIOPSIS_TEST_DB",
                str(Path(tempfile.gettempdir()) / f"Siriopsis_test_{os.getpid()}.db")),
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 슬래시로 시작하지 않는다 — 상대경로여야 서브경로 배포에서 SCRIPT_NAME 이 붙는다.
STATIC_URL = "static/"

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# --- 자료 ---------------------------------------------------------------------

# 큰 자료(사진 등)의 뿌리. 컨테이너에서는 /data, 호스트에서는 큰 디스크를 가리킨다.
DATA_ROOT = Path(os.environ.get("SIRIOPSIS_DATA_ROOT", "") or PROJECT_ROOT)

# NAS 의 원본 자료 뿌리. **읽기만 한다** — 컨테이너에는 읽기 전용으로 마운트한다.
# 테이블의 경로(Stack.source_dir·Frame.path)는 모두 이 뿌리 기준 상대경로다.
SOURCE_ROOT = Path(os.environ.get("SIRIOPSIS_SOURCE_ROOT", "")
                   or "/nfs/temp-share/Sirius Passet Catalog")

# 분류 정보를 읽어 올 phyloserver siriuspasset 의 뿌리 (specimens/catalog.py).
# `paleolab` 은 이 서버 안에서 이름이 안 풀린다 — 사내망 주소로 부른다(컨테이너에서도 닿는다).
CATALOG_URL = os.environ.get("SIRIOPSIS_CATALOG_URL", "") or "http://172.16.116.98/siriuspasset/"

# --- 안전망 상태 (/healthz 가 읽는다) -----------------------------------------

# 백업 스크립트와 같은 환경변수를 본다 — 값이 갈리면 /healthz 가 아무도 안 쓰는
# 디렉터리를 보며 "최신" 이라 말하게 된다.
BACKUP_DIR = Path(os.environ.get("SIRIOPSIS_BACKUP_DIR", "") or PROJECT_ROOT / "backup")

# 가장 새 스냅샷이 이보다 오래면 degraded (.guides/web/data-safety.md §16).
# **기본은 꺼 둔다** — cron 이 없는 장비에서 켜면 늘 울리고, 늘 울리는 경보는 안 보게 된다.
try:
    BACKUP_MAX_AGE_H = float(os.environ.get("SIRIOPSIS_BACKUP_MAX_AGE_H", "") or 0) or None
except ValueError:
    BACKUP_MAX_AGE_H = None
