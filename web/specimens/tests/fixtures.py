"""시험용 빛 더미 폴더를 임시 디렉터리에 세운다 — **시험은 NAS 원본을 읽지 않는다** (CLAUDE.md)."""
from pathlib import Path

from PIL import Image

# 실제 .lp 의 첫 세 줄(SP-2016-52Z)과 같은 꼴: 윈도 경로, 소문자 .jpg, 빛 단위 벡터
VECTORS = [
    (-0.7347357813929454, -0.44147379642946366, 0.5150380749100542),
    (-0.703022299549211, -0.6555789002208297, 0.27563735581699916),
    (-0.41145512515461136, -0.807526151172377, 0.42261826174069944),
]


def make_jpg(path, size=(40, 30), when="2016:04:30 14:16:26"):
    im = Image.new("RGB", size, (90, 90, 90))
    ex = Image.Exif()
    ex[272] = "Canon EOS 60D"
    ex[306] = when
    im.save(path, exif=ex)


def make_stack(root, rel_dir, stem, first=10095, vectors=VECTORS, skip=()):
    """root/rel_dir 에 컷 len(vectors) 장과 <stem>.lp 를 만든다. skip 의 번째 컷은 파일을 만들지 않는다."""
    d = Path(root) / rel_dir
    d.mkdir(parents=True, exist_ok=True)
    lines = [str(len(vectors))]
    for i, (x, y, z) in enumerate(vectors):
        name = f"IMG_{first + i}"
        if i not in skip:
            make_jpg(d / f"{name}.JPG")
        lines.append(f"C:\\Users\\MY\\Desktop\\{stem}\\{name}.jpg {x} {y} {z}")
    (d / f"{stem}.lp").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d
