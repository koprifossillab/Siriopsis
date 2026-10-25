"""Siriopsis 산출물:  python build.py  → ./out/

  out/icons/   favicon.ico · favicon-16/32 · siriopsis-icon.svg · siriopsis-icon-512.png (투명 배경)
               siriopsis-icon-tile-512.png (둥근 타일 배경판) · 가로형 로고(라이트/다크)
  out/siriopsis_build_animation.gif    빌드 애니메이션 (어두운 배경 #080a0e)
  out/siriopsis_build_animation_onlight.webp  투명 배경 · 진한 글자 (밝은 페이지용)
  out/siriopsis_build_animation_ondark.webp   투명 배경 · 흰 글자 (어두운 페이지용)
"""
import io, os, sys
import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from logo import P, draw_icon, icon_svg, logo_svg, ease  # noqa: E402

OUT = os.path.join(HERE, "out")
W, H = 800, 300
CANVAS = "#080a0e"     # 아이콘 타일보다 어둡게 → 타일 경계가 보이게


def png(svg, w, h=None, path=None, mode="RGBA"):
    data = cairosvg.svg2png(bytestring=svg.encode(), output_width=w, output_height=h or w)
    if path:
        open(path, "wb").write(data)
    return Image.open(io.BytesIO(data)).convert(mode)


INK_ON = {"dark": (P["ink"], P["steel"]), "light": ("#151a22", "#6f8199")}


def frame(st, transparent=False, on="dark"):
    ink, sub = INK_ON[on]
    svg = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    if not transparent:
        svg.append(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')
    svg.append(f'<g transform="translate(50,50) scale({200/512:.5f})">{draw_icon(st)}</g>')
    tx, sb = ease(st["text"]), ease(st["sub"])
    if tx > 0:
        svg.append(f'<g opacity="{tx:.3f}" transform="translate({(1-tx)*-24:.2f},0)">'
                   f'<text x="290" y="160" font-family="Montserrat ExtraBold, sans-serif" font-weight="800" '
                   f'font-size="78" letter-spacing="-1" fill="{ink}">Siriopsis</text></g>')
    if sb > 0:
        svg.append(f'<g opacity="{sb:.3f}" transform="translate(0,{(1-sb)*10:.2f})">'
                   f'<text x="294" y="204" font-family="Noto Sans CJK KR, sans-serif" font-size="21" '
                   f'letter-spacing="3" fill="{sub}">SIRIUS PASSET FOSSIL VIEWER</text></g>')
    svg.append('</svg>')
    return "".join(svg)


def timeline():
    st = dict(halo=0, longs=0, shorts=0, spin=0, core=0, twinkle=0, text=0, sub=0)
    F = []

    def add(ms, **kw):
        st.update(kw); F.append((dict(st), ms))

    def tween(n, ms, **to):
        for i in range(1, n + 1):
            add(ms, **{k: v * i / n for k, v in to.items()})

    for _ in range(3): add(60)                    # 잠깐 빈 화면
    tween(10, 45, halo=1)                         # 2 빛무리
    tween(6, 40, core=1)                          # 3 별의 중심
    # 4·5 골편이 돋는 동안 회전은 한 번의 연속 동작으로 (구간을 나누면 속도가 끊긴다)
    N = 30
    for i in range(1, N + 1):
        t = i / N
        add(38, spin=t,
            longs=min(1.0, t / 0.6),               # 앞 60% 동안 긴 골편 4장
            shorts=max(0.0, (t - 0.4) / 0.6))      # 뒤 60% 동안 짧은 골편 4장 (겹쳐서 이어짐)
    for v in (0.25, 0.5, 0.75, 1.0):              # 6 반짝
        add(45, twinkle=v)
    add(60, twinkle=0)
    tween(12, 45, text=1)                         # 7 이름
    tween(8, 45, sub=1)                           #   부제
    add(2600)                                     # 8 완성 화면 유지
    return F


if __name__ == "__main__":
    icons = os.path.join(OUT, "icons"); os.makedirs(icons, exist_ok=True)
    r = icon_svg()
    open(os.path.join(icons, "siriopsis-icon.svg"), "w").write(r)
    png(icon_svg(tile=True), 512, path=os.path.join(icons, "siriopsis-icon-tile-512.png"))
    png(r, 512, path=os.path.join(icons, "siriopsis-icon-512.png"))
    png(r, 32, path=os.path.join(icons, "favicon-32.png"))
    png(r, 16, path=os.path.join(icons, "favicon-16.png"))
    Image.open(os.path.join(icons, "siriopsis-icon-512.png")).save(
        os.path.join(icons, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    for dark in (False, True):
        tag = "dark" if dark else "light"
        s = logo_svg(dark)
        open(os.path.join(icons, f"siriopsis-logo-{tag}.svg"), "w").write(s)
        png(s, 1600, 480, path=os.path.join(icons, f"siriopsis-logo-{tag}.png"))

    F = timeline()
    durs = [d for _, d in F]
    imgs = [png(frame(st), W, H, mode="RGB") for st, _ in F]
    gif = os.path.join(OUT, "siriopsis_build_animation.gif")
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=durs, loop=0, optimize=True)
    sizes = {}
    for on in ("light", "dark"):
        rgba = [png(frame(st, transparent=True, on=on), W, H) for st, _ in F]
        webp = os.path.join(OUT, f"siriopsis_build_animation_on{on}.webp")
        rgba[0].save(webp, save_all=True, append_images=rgba[1:], duration=durs, loop=0, lossless=False, quality=90, method=4)
        sizes[on] = os.path.getsize(webp)
    print(len(F), "frames", sum(durs), "ms | gif", os.path.getsize(gif), "| webp", sizes)
