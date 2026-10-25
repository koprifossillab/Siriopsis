# HANDOFF

**2026-10-25** · 판 없음 · 반입 끝, **뷰어 첫 판**([005](devlog/20261025_wetherilli_005_viewer.md)) — 카탈로그 빛 묶음 8,876 과 PTM 22 벌을 화면에서 넘겨 본다
([wetherilli 002](devlog/20261025_wetherilli_002_light_stacks_to_tables.md), [003](devlog/20261025_wetherilli_003_catalog_light_series.md), [004](devlog/20261025_wetherilli_004_keep_copies.md) — 사본도 넣었다).
**자료가 맞는지 확인을 기다리며 멈추지 않는다** — 사용자는 데이터가 옳다고 보고 틀을 짜는 중이다. 아래 §0 은 막는 일이 아니다.
다음은 **paleolab 에 길**(`v0.1.0`, P01 3단계) 또는 **정밀 맞춤**(GPU) 또는 **묶음 고치기** — 사용자가 화면을 보고 고른다.

## 0. 사람이 정할 것

- **PTM 더미의 표본** — 이름에 글자가 없는 PTM 21 벌(002 §결과): `52`(셋) = `52A` 와 같은 A? · `494`(넷) = A? · `601`(둘) = A(목록에 하나뿐)? ·
  `0577a`·`0577b` 의 소문자는 표본 글자인가 마주 조각인가 · SP-2011 두 슬랩은 phyloserver 에 없다 — 분류군은 어디서
- **phyloserver 에 없는 슬랩 393** — NAS `Siriopsis/survey/20261025_not_in_phyloserver.csv`. 목록에 더할 것인가
- **사본 폴더의 정본 규칙**(003 §한 것) — 컷 수 → 사본 표시 폴더 아님 → 얕은 경로. 사본도 들어가 있어(004) 뷰어에서 보고 정하면 된다
- Docker Hub `koprifossillab/siriopsis` 와 secret — 첫 `v*` 태그 전에(이 서버에서만 굽는다면 없어도 된다)

## 1. 지금 있는 것

| | 지금 |
|---|---|
| 웹 | Django 5.2 · `core`(`/healthz` — 더미·컷 수, 컷 0 이면 degraded) · `specimens`(테이블·반입 · 화면 `/`·`/slab/<번호>/`·`/stack/<id>/` · 컷 `/frame/<id>.jpg?w=`) |
| 화면 | DiaRUGA 모양(006) — 목록은 연도 탭 → 백 번 구간 → NAS 열 개 폴더(또는 층준 구간), 설정 `/system/`(판 이력은 CHANGELOG), 대기 화면, 로고 `docs/assets/logo/` |
| 뷰어 | PTM 은 빛 방향 판, 빛 묶음은 번호 줄. 저해상도(1600, 기본)·고해상도(2560 + 확대하면 지금 컷만 원본), `h` 키. 축소본 캐시 `THUMB_CACHE` |
| 반입 | `scan_light_stacks`(PTM, `.lp`) · `scan_light_series`(카탈로그 빛 묶음, 정본 고르기) · `import_catalog`(phyloserver 목록) — 모두 원본은 읽기만 |
| 테이블 | 개발 DB: 슬랩 4,304 · 표본 6,700(분류군 6,653) · 묶음 10,522(`series` 정본 8,876 + 사본 1,624 · `ptm` 22) · 컷 71,867 |
| 시험 | 37 (`python web/manage.py test core specimens`) |
| 이미지·CI | `deploy/Dockerfile` · `.github/workflows/test.yml`(시험 → 굽기, `v*` 태그만 push) |
| 환경 | venv `~/venv/Siriopsis`, `workon sp`, `.guides` 링크, 개발 DB `Siriopsis.db`(gitignore — 반입 세 명령으로 7 분이면 다시 만든다) |
| 자료 | NAS `/nfs/temp-share/Sirius Passet Catalog/`(읽기만). 작업 공간 `/nfs/temp-share/Siriopsis/` — 조사 표는 `survey/`, paleoadmin 요청은 `temp/` |
| GPU | RTX 3060 Ti 8 GB — 무거운 분석(맞춤)은 여기서(사용자) |
| 라이선스 | AGPL-3.0 |
| 운영 | **없다.** 자리만 — `/srv/Siriopsis`, nginx `/Siriopsis/`, 포트 8100·8101 |

## 2. 다음

`TODOs.md`.
