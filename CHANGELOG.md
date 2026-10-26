# CHANGELOG

판 하나에 한 줄. 근거 devlog 번호와 함께. `v0.1.0` 앞의 「—」 줄은 판 없이 쌓인 작업이다.

| 판 | 날짜 | 무엇 |
|---|---|---|
| — | 2026-10-25 | 작업 환경. Django 뼈대 · `/healthz` · 시험 4 · 이미지 · CI · 문서 관례 ([wetherilli 001](devlog/20261025_wetherilli_001_bootstrap.md)), 단계 계획 ([P01](devlog/20261025_wetherilli_P01_stages.md)) |
| — | 2026-10-25 | 빛 더미 22 벌을 테이블로 — `scan_light_stacks` · `import_catalog`(phyloserver) · `/healthz` 행 수 · 시험 18 · AGPL-3.0 ([wetherilli 002](devlog/20261025_wetherilli_002_light_stacks_to_tables.md)) |
| — | 2026-10-25 | 카탈로그 빛 묶음 8,876 · 컷 59,774 — `scan_light_series`, 종류 `ptm`·`series`, phyloserver 목록 쪽 넘기기 · 시험 25 ([wetherilli 003](devlog/20261025_wetherilli_003_catalog_light_series.md)) |
| — | 2026-10-25 | 사본 묶음 1,624 도 넣어 정본에 잇는다(`copy_of`) · 시험 26 ([wetherilli 004](devlog/20261025_wetherilli_004_keep_copies.md)) |
| — | 2026-10-25 | 뷰어 첫 판 — 목록·슬랩·더미 화면, PTM 빛 방향 판, `/frame/<id>.jpg` 축소본, 저해상도·고해상도 · 시험 33 ([wetherilli 005](devlog/20261025_wetherilli_005_viewer.md)) |
| — | 2026-10-25 | DiaRUGA 모양 — 연도·번호 묶음 목록, 시야 화면 구성, 로고·대기 화면·설정(판 이력·출처·만든이) · 시험 37 ([wetherilli 006](devlog/20261025_wetherilli_006_diaruga_look.md)) |
| v0.1.0 | 2026-10-25 | 첫 판 — http://paleolab/Siriopsis/ . compose(127.0.0.1:8100, NAS 읽기 전용)·nginx 조각·`install.sh`·첫 화면 카드 ([wetherilli 007](devlog/20261025_wetherilli_007_paleolab_route.md)) |
| v0.2.0 | 2026-10-25 | 묶음 고치기 — 가르기·합치기·지우기(숨김)·컷 숨기기, 반입이 손댄 묶음을 덮지 않는다 · 백업(시간별 :50 · NAS 05:40 · `/healthz` 깃발) · CSRF · 시험 63 ([wetherilli 008](devlog/20261025_wetherilli_008_regroup_and_backup.md)) |
| v0.3.0 | 2026-10-26 | 슬랩 전경(dorsal·vent) · 슬랩 화면(전경·속성 / 더미 카드) · 배율·스케일바·길이 재기 · 표본 테두리 · 글자 없음=A · ☆ 별표 표본 · counterpart 짝 · 백업 문 가르기 · 시험 115 ([009](devlog/20261025_wetherilli_009_slab_views_and_slab_page.md) · [010](devlog/20261025_wetherilli_010_ruler_scale.md) · [011](devlog/20261025_wetherilli_011_specimen_outline.md) · [012](devlog/20261025_wetherilli_012_bare_name_is_a.md) · [013](devlog/20261025_wetherilli_013_stars_and_counterparts.md) · [014](devlog/20261026_wetherilli_014_release_v030.md)) |
| v0.3.1 | 2026-10-26 | 슬랩 화면에 vent 를 dorsal 옆에 나란히 · phyloserver `export.json` 반입(목록에 없음 393 → 27, counterpart 652) ([016](devlog/20261026_wetherilli_016_vent_beside_dorsal.md)) |
| v0.3.2 | 2026-10-26 | 목록 열 너비 고정 · 목록·격자에 ☆·짝 표시, 찾기 줄에 ☆·짝 거르기 · 시험 116 ([017](devlog/20261026_wetherilli_017_list_fixed_columns_and_marks.md)) |
| v0.3.3 | 2026-10-26 | 목록 칸이 줄을 바꾸지 않는다(넘치면 …, 전체는 title) · 번호 열을 넓혀 ☆·짝 표시가 한 줄에 ([017](devlog/20261026_wetherilli_017_list_fixed_columns_and_marks.md)) |
