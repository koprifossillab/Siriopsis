"""Siriopsis 로고 — 할키에리아 골편 8장이 시리우스의 반짝임을 이룬다.

draw_icon(state): state 의 각 값은 진행도(0~1). 모두 1 이면 완성된 정지 아이콘.
정지 아이콘과 빌드 애니메이션이 이 함수 하나를 같이 쓴다.
"""
import math

P = dict(bg0="#1b2028", bg1="#0d1015", ink="#eef4ff", ice="#bcd3f0", steel="#6f8199",
         dim="#3a4555", acc="#8fd8ff", edge="#46566c")

DONE = dict(halo=1, longs=1, shorts=1, spin=1, core=1, twinkle=0)


def clamp(t):
    return max(0.0, min(1.0, t))


def ease(t):
    t = clamp(t); return t * t * (3 - 2 * t)


def back(t, s=1.7):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1


def ease_out(t):
    """빠르게 출발해서 점점 느려지며 멈춤 (회전 감속용, cubic)."""
    t = clamp(t); return 1 - (1 - t) ** 3


def stagger(t, i, n):
    return clamp(t * n - i)


def blade(L, W, fill, rib=None, curve=0.0, edge=None):
    """골편 모양 잎날: (0,0)에서 위(-y)로 길이 L, 최대 폭 W, curve 만큼 끝이 휜다."""
    c = curve * L
    d = (f'M 0 0 C {W*0.9:.1f} {-L*0.25:.1f} {W*0.7+c:.1f} {-L*0.7:.1f} {c:.1f} {-L:.1f} '
         f'C {-W*0.5+c:.1f} {-L*0.72:.1f} {-W*0.9:.1f} {-L*0.3:.1f} 0 0 Z')
    stroke = f' stroke="{edge}" stroke-width="5" stroke-linejoin="round"' if edge else ""
    s = f'<path d="{d}" fill="{fill}"{stroke}/>'
    if rib:
        s += (f'<path d="M 0 {-L*0.08:.1f} Q {c*0.4:.1f} {-L*0.55:.1f} {c*0.92:.1f} {-L*0.92:.1f}" fill="none" '
              f'stroke="{rib}" stroke-width="{max(2, W*0.09):.1f}" stroke-linecap="round" opacity="0.55"/>')
    return s


def defs(uid="", square=False):
    rx = 0 if square else 112
    return (f'<defs><clipPath id="r{uid}"><rect width="512" height="512" rx="{rx}"/></clipPath>'
            f'<radialGradient id="bg{uid}" cx="0.5" cy="0.38" r="0.75"><stop offset="0" stop-color="{P["bg0"]}"/>'
            f'<stop offset="1" stop-color="{P["bg1"]}"/></radialGradient>'
            f'<linearGradient id="blade{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["ink"]}"/>'
            f'<stop offset="1" stop-color="{P["ice"]}"/></linearGradient>'
            f'<radialGradient id="halo{uid}"><stop offset="0" stop-color="{P["acc"]}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{P["acc"]}" stop-opacity="0"/></radialGradient></defs>')


def draw_icon(st=DONE, uid="", square=False, tile=False):
    """512×512 좌표계 아이콘 조각(<svg> 태그 없이).

    tile=False(기본): 배경 없이 별만 — 어떤 배경 위에서도 비쳐 보이도록 골편에 테두리를 두른다.
    tile=True: 둥근 사각 타일 배경 포함(앱 아이콘용).
    """
    b = [defs(uid, square)]
    if tile:
        b.append(f'<g clip-path="url(#r{uid})"><rect width="512" height="512" fill="url(#bg{uid})"/>')
    else:
        b.append('<g>')
    edge = None if tile else P["edge"]
    tw = math.sin(math.pi * clamp(st["twinkle"]))          # 0→1→0 반짝
    h = ease(st["halo"]) * (1 + 0.6 * tw)
    if h > 0:
        b.append(f'<circle cx="256" cy="256" r="{230 * (0.7 + 0.3 * ease(st["halo"])):.1f}" fill="url(#halo{uid})" opacity="{min(1, h):.3f}"/>')
    spin = -80 * (1 - ease_out(st["spin"]))                 # 바람개비가 돌다가 감속하며 멈춤
    scale = 1 + 0.06 * tw
    b.append(f'<g transform="translate(256,256) rotate({spin:.2f}) scale({scale:.4f})">')
    for k in range(8):
        long_ = k % 2 == 0
        lt = stagger(st["longs"] if long_ else st["shorts"], k // 2, 4)
        if lt <= 0:
            continue
        g = (blade(206, 34, f"url(#blade{uid})", rib=P["steel"], curve=0.10, edge=edge) if long_
             else blade(104, 20, P["steel"], curve=0.14, edge=edge))
        b.append(f'<g transform="rotate({k*45}) scale({0.25 + 0.75 * back(lt):.4f})" opacity="{ease(lt):.3f}">{g}</g>')
    co = st["core"]
    if co > 0:
        b.append(f'<circle r="{11 * back(co) * (1 + 0.5 * tw):.2f}" fill="{P["acc"]}"/>')
    b.append('</g></g>')
    return "".join(b)


def icon_svg(tile=False):
    return ('<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">'
            + draw_icon(DONE, tile=tile) + '</svg>')


def logo_svg(dark=False):
    """가로형 헤더 로고: 아이콘(200px) + 워드마크."""
    bg = P["bg1"] if dark else "#ffffff"
    ink = P["ink"] if dark else "#151a22"
    sub = P["steel"] if dark else "#6f8199"
    return ('<svg width="800" height="240" viewBox="0 0 800 240" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="800" height="240" fill="{bg}"/>'
            f'<g transform="translate(40,40) scale(0.390625)">{draw_icon()}</g>'
            f'<text x="276" y="132" font-family="Montserrat ExtraBold, sans-serif" font-weight="800" font-size="80" '
            f'letter-spacing="-1" fill="{ink}">Siriopsis</text>'
            f'<text x="280" y="174" font-family="Noto Sans CJK KR, sans-serif" font-size="22" letter-spacing="3" '
            f'fill="{sub}">SIRIUS PASSET FOSSIL VIEWER</text></svg>')
