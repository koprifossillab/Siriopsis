"""컷의 축소본 (wetherilli 005). DiaRUGA `viewer/views.py` 의 `_thumbnail`·`_jpeg` 에서 왔다.

원본은 NAS 의 18~20 MP JPEG(장당 5~10 MB)라 목록·줄·큰 그림 모두 축소본을 쓰고, 확대해 들어갈 때만 원본을 보낸다.

- **폭은 정해진 몇 가지뿐이다**(`WIDTHS`) — 주소의 `w=` 를 아무 수나 받으면 캐시가 끝없이 는다. 가까운 위의 폭으로 올린다
- **열쇠에 원본의 mtime 이 든다** — 원본이 바뀌면 새로 만든다. 캐시는 지워도 된다
- JPEG 는 `draft()` 로 DCT 단계에서 미리 줄여 연다 — 20 MP 를 다 풀지 않아 장당 0.2~0.4 초
- 1600 은 저해상도, **2560 은 고해상도** 보기의 폭이다(005 §해상도). 2560 은 원본(5184·5472)의 절반 아래라
  `draft()` 가 1/2 로 풀어 준다 — 2800·3200 으로 두면 원본을 다 풀어야 해 장당 0.5 초로 두 배가 된다(쟀다)
"""
import hashlib
import os
from pathlib import Path

from django.conf import settings

WIDTHS = (200, 400, 800, 1600, 2560)


def snap_width(raw):
    """`w=` 값 → WIDTHS 중 하나. 숫자가 아니면 ValueError."""
    w = int(raw)
    return next((x for x in WIDTHS if x >= w), WIDTHS[-1])


def source_path(rel):
    """테이블의 상대경로 → SOURCE_ROOT 안의 실제 파일. 바깥을 가리키거나 없으면 None.

    경로는 반입기가 적은 것이지만, 링크(`..`·심볼릭)로 바깥을 가리키는 행이 생겨도 따라가지 않는다.
    """
    root = Path(settings.SOURCE_ROOT).resolve()
    try:
        target = (root / rel).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not target.is_file() or not target.is_relative_to(root):
        return None
    return target


def thumbnail(path, width):
    """축소본 파일 경로. 원본이 이미 그 폭보다 좁으면 원본을, 못 읽으면 None."""
    from PIL import Image

    st = path.stat()
    key = f"{path}|{st.st_mtime_ns}|{width}"
    out = Path(settings.THUMB_CACHE) / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".jpg")
    if out.exists():
        return out
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(path) as im:
            if im.width <= width:
                return path
            height = round(im.height * width / im.width)
            im.draft("RGB", (width, height))
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, height), Image.LANCZOS)
            # 일꾼 여럿이 같은 축소본을 동시에 만들 수 있다 — 저마다의 임시 파일에 쓰고 바꿔 끼운다
            tmp = out.with_suffix(f".{os.getpid()}.tmp")
            im.save(tmp, "JPEG", quality=84)
            tmp.replace(out)
    except OSError:
        return None
    return out
