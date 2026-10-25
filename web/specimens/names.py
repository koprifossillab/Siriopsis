"""NAS 의 이름을 phyloserver 목록의 이름 꼴로 바꾼다 (wetherilli 002).

phyloserver `siriuspasset` 은 슬랩을 `SP-2016-0052`(번호 네 자리), 표본을 `SP-2016-0052-A` 로 적는다.
NAS 의 파일·폴더는 `SP-2016-52A`, `SP-2016-52Z`, `SP-2011-0577aZ` 처럼 적는다.
**이 저장소의 이름은 phyloserver 꼴이다** — 사람이 고쳐 가는 목록이 그쪽이라, 거기와 같은 글자로 찾을 수 있어야 한다.
"""
import re

# SP-<연도>-<번호><글자?><Z?> — 끝의 대문자 Z 는 확대 촬영 표시(사용자 확인 2026-10-25), 표본 글자가 아니다.
# 표본 글자는 Z 를 뺀 영문 한 자다. 소문자(`0577a`)는 표본 글자인지 마주 조각(a/b) 표시인지 모른다 —
# 그래서 `letter` 와 따로 `lower` 로 돌려주고, 표본에 붙이지 않는다.
_NAME = re.compile(r"^SP-(?P<year>\d{4})-(?P<num>\d+)(?P<letter>[A-Y])?(?P<lower>[a-z])?(?P<zoom>Z)?$")


def slab_no(year, num):
    return f"SP-{int(year):04d}-{int(num):04d}"


def parse_stem(stem):
    """`SP-2016-52AZ` → dict(slab='SP-2016-0052', letter='A', lower='', zoom=True). 꼴이 아니면 None."""
    m = _NAME.match(stem.strip())
    if not m:
        return None
    return {
        "slab": slab_no(m["year"], m["num"]),
        "year": int(m["year"]),
        "letter": m["letter"] or "",
        "lower": m["lower"] or "",
        "zoom": bool(m["zoom"]),
    }


def label_of(stem):
    """확대 표시 Z 를 뗀 이름 — 같은 대상을 찍은 더미들(무처리·코팅·전체·확대)이 같은 값을 갖는다."""
    p = parse_stem(stem)
    return stem[:-1] if p and p["zoom"] else stem
