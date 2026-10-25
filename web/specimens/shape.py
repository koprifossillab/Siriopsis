"""폴리곤 하나에서 계측값을 낸다 — **순수 파이썬, 임포트는 `math` 뿐** (wetherilli 011).

**옮겨 온 것이다** — DiaRUGA v0.37.1 `web/viewer/shape.py` 의 `area`(신발끈)·`perimeter`·`_centroid_moments`·`fit_ellipse`·
`_rotated_wh`. 웹 이미지에는 numpy·cv2 가 없다(그 경계를 지킨다) — 폴리곤의 지표는 화소가 필요 없다.
DiaRUGA 의 판정용 지표(타원 IoU·볼록성·텍스처 …)는 가져오지 않았다 — 표본 테두리에는 판정이 없다.

좌표는 `[[x, y], …]`, 원본 화소. 화면 좌표는 y 가 아래로 커지지만 면적·모멘트는 부호만 뒤집혀 절댓값으로 받는다.
"""
import math

MIN_POINTS = 3


def area(pts):
    """신발끈 공식. **절댓값이다** — 점의 방향(시계/반시계)에 안 매인다."""
    if len(pts) < MIN_POINTS:
        return 0.0
    s = 0.0
    for i, (x0, y0) in enumerate(pts):
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def perimeter(pts):
    if len(pts) < 2:
        return 0.0
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def _centroid_moments(pts):
    """면적 모멘트에서 `(cx, cy, m20, m02, m11)`. 없으면 None."""
    n = len(pts)
    if n < MIN_POINTS:
        return None
    a2 = sxx = syy = sxy = cx = cy = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
        sxx += cross * (x0 * x0 + x0 * x1 + x1 * x1)
        syy += cross * (y0 * y0 + y0 * y1 + y1 * y1)
        sxy += cross * (2 * x0 * y0 + x0 * y1 + x1 * y0 + 2 * x1 * y1)
    ar = a2 / 2.0
    if abs(ar) < 1e-9:
        return None
    cx /= 6.0 * ar
    cy /= 6.0 * ar
    return (cx, cy, sxx / (12.0 * ar) - cx * cx, syy / (12.0 * ar) - cy * cy, sxy / (24.0 * ar) - cx * cy)


def fit_ellipse(pts):
    """면적 모멘트가 같은 타원 `(cx, cy, a, b, deg)` — `a` 가 장반경. 균일 밀도 타원의 모멘트가 `a²/4` 라 `a = 2√λ₁`."""
    m = _centroid_moments(pts)
    if m is None:
        return None
    cx, cy, m20, m02, m11 = m
    diff = math.hypot(m20 - m02, 2.0 * m11)
    l1 = (m20 + m02 + diff) / 2.0
    l2 = (m20 + m02 - diff) / 2.0
    if l1 <= 1e-9:
        return None
    return cx, cy, 2.0 * math.sqrt(l1), 2.0 * math.sqrt(max(l2, 0.0)), math.degrees(0.5 * math.atan2(2.0 * m11, m20 - m02))


def _rotated_wh(pts, deg):
    r = math.radians(deg)
    cos, sin = math.cos(r), math.sin(r)
    rx = [x * cos - y * sin for x, y in pts]
    ry = [x * sin + y * cos for x, y in pts]
    return max(rx) - min(rx), max(ry) - min(ry)


def measure(pts):
    """원본 화소의 계측값 → dict. 못 재는 것은 None.

    - `major_px`·`minor_px` — 면적 모멘트가 같은 타원의 장축·단축(지름)
    - `long_px`·`short_px` — 그 타원의 축으로 돌린 바깥 상자의 긴 변·짧은 변(화석의 「길이」·「폭」에 가깝다)
    """
    out = {"area_px": None, "perimeter_px": None, "major_px": None, "minor_px": None, "long_px": None, "short_px": None}
    if len(pts) < MIN_POINTS:
        return out
    a = area(pts)
    if a <= 0:
        return out
    out["area_px"] = a
    out["perimeter_px"] = perimeter(pts)
    ell = fit_ellipse(pts)
    if ell:
        _, _, ea, eb, deg = ell
        out["major_px"], out["minor_px"] = 2.0 * ea, 2.0 * eb
        w, h = _rotated_wh(pts, -deg)
        out["short_px"], out["long_px"] = sorted((w, h))
    return out
