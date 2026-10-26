# devlog

이름은 `YYYYMMDD_{계정}_{nnn}_{title}.md`, 계획은 `_P{nn}_`. 번호는 글쓴이마다 센다 — 가리킬 때 `wetherilli 001`.

## 계정

| Linux | GitHub |
|---|---|
| sclee | wetherilli |
| paleoadmin | koprifossillab (운영) |

## 색인

| 글 | 무엇 |
|---|---|
| [20261026_wetherilli_018](20261026_wetherilli_018_epma.md) | EPMA 를 붙인다 — phyloserver `epma.json` + `/data3/epma` 읽기 전용, 빛 묶음·PTM 과 나란한 카드·목록 열, 세션 화면 강도 뷰어 (`v0.4.0`·`v0.4.1`) |
| [20261026_wetherilli_017](20261026_wetherilli_017_list_fixed_columns_and_marks.md) | 목록 열 너비 고정(접고 펼 때 17~23 가지 → 1), ☆·짝 표시와 거르기 (`v0.3.2`) |
| [20261026_wetherilli_016](20261026_wetherilli_016_vent_beside_dorsal.md) | vent 를 dorsal 옆에(`v0.3.1`), export.json 반입 — 목록에 없음 393 → 27 |
| [20261026_wetherilli_015](20261026_wetherilli_015_phyloserver_export_survey.md) | phyloserver siriuspasset 통째 내보내기 조사 — 슬랩 4,583·표본 9,505·사진 83,375(원본은 NAS)·EPMA 167 GB·이력 |
| [20261026_wetherilli_014](20261026_wetherilli_014_release_v030.md) | `v0.3.0` 운영에 — 일꾼 둘과 지휘 세션의 브랜치를 합쳐(merge 마이그레이션) 올리고 반입 넷 |
| [20261025_wetherilli_013](20261025_wetherilli_013_stars_and_counterparts.md) | 별표 표본(`/starred/`)과 counterpart 짝 — phyloserver 가 원천(export.json 을 먼저), 엑셀은 빈 곳만, 두 슬랩 전경은 양쪽에 |
| [20261025_wetherilli_012](20261025_wetherilli_012_bare_name_is_a.md) | 글자 없는 이름은 A 표본 — 반입이 끝에 다시 정한다, phyloserver·NAS 에 다른 글자가 있는 슬랩 66 은 예외 |
| [20261025_wetherilli_011](20261025_wetherilli_011_specimen_outline.md) | 표본 테두리 — 더미마다 하나, 그리기·고치기·지우기, 서버가 다시 잰다, 크기가 같은 컷에만 얹고 「맞춤 전」 |
| [20261025_wetherilli_010](20261025_wetherilli_010_ruler_scale.md) | 자에서 배율(mm/px) — 호스트 pipeline → CSV → `import_scales`, 스케일바(DiaRUGA 모양)·길이 재기, 손으로 잰 30 개와 비교 |
| [20261025_wetherilli_009](20261025_wetherilli_009_slab_views_and_slab_page.md) | 슬랩 전경(dorsal) 반입 — kind `slab` 3,915, 슬랩 화면을 왼쪽 전경·속성 / 오른쪽 더미 카드로 |
| [20261025_wetherilli_008](20261025_wetherilli_008_regroup_and_backup.md) | 묶음 고치기(가르기·합치기·지우기·컷 숨기기, 반입이 덮지 않는다)와 백업(시간별·NAS·`/healthz` 깃발) |
| [20261025_wetherilli_007](20261025_wetherilli_007_paleolab_route.md) | paleolab 에 길 `v0.1.0` — compose(8100, NAS 읽기 전용)·nginx 조각·install.sh, gunicorn 실 넷 |
| [20261025_wetherilli_006](20261025_wetherilli_006_diaruga_look.md) | DiaRUGA 모양으로 — 연도·번호(NAS 열 개 폴더) 묶음 목록, 시야 화면 구성, 로고·대기 화면·설정·판 이력·바닥글 |
| [20261025_wetherilli_005](20261025_wetherilli_005_viewer.md) | 뷰어 첫 판 — 목록·슬랩·더미 화면, PTM 빛 방향 판, 컷 서빙, 저해상도·고해상도(잰 값) |
| [20261025_wetherilli_004](20261025_wetherilli_004_keep_copies.md) | 사본도 넣어 정본에 잇는다(1,624), 앞으로 사람이 묶음을 고친다 — 반입이 덮지 않게 |
| [20261025_wetherilli_003](20261025_wetherilli_003_catalog_light_series.md) | 카탈로그 빛 묶음 8,876 — PTM 과 kind 로 가름, 정본 고르기, phyloserver 목록 전체 반입, P01 정정 |
| [20261025_wetherilli_002](20261025_wetherilli_002_light_stacks_to_tables.md) | 빛 더미를 테이블로 — 22 벌, 이름은 phyloserver 꼴, 분류 정보는 phyloserver 목록에서 |
| [20261025_wetherilli_001](20261025_wetherilli_001_bootstrap.md) | 작업 환경 — Cropobite 001 뼈대, 이름·포트·NAS 작업 공간을 정함 |
| [20261025_wetherilli_P01](20261025_wetherilli_P01_stages.md) | 단계 계획 — 자료 조사, DiaRUGA 에서 가져올 것, 빛 더미 뷰어부터 운영까지 |
