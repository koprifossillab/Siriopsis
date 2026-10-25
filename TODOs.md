# TODOs

단계는 [P01](devlog/20261025_wetherilli_P01_stages.md).

## 1단계 남은 것

- 표본이 비어 있는 더미에 표본 붙이기 — 사람의 답을 기다린다(HANDOFF §0). 붙인 값은 반입으로 다시 만들 수 없는 자료다 → 3단계 백업 대상

## 2단계 — 빛 더미 뷰어

- DiaRUGA `/img` 축소본 서빙·`thumb`/`full` 태그·`_atlasview.html` 확대·이동을 옮긴다(머리에 출처)
- 표본 목록 → 표본(더미 칸) → 더미(그림 + 빛 방향 판 + 컷 줄, 50 컷 미리 받기, ←/→·↑/↓)
- 빛 벡터 좌표 방향을 그림자로 맞춘다
- 표본 화면은 같은 대상의 더미를 모은다 — 표본이 비어 있으면 슬랩·이름(`label`)으로. `52A` 와 `52` 처럼 이름이 갈린 것은 표본이 붙어야 모인다
- 슬랩·표본에서 phyloserver 상세 화면으로 가는 링크(`catalog_id`)
- 축소본 캐시 `/data/Siriopsis/thumbcache` + `warm_thumbs` · 브라우저 시험

## 3단계 — paleolab 에 길 (`v0.1.0`)

- Cropobite 에서 `deploy/srv/docker-compose.yml`(127.0.0.1:8100)·`deploy/nginx/Siriopsis-subpath.conf`·`deploy/host/{install,deploy,smoke}.sh`
- paleoadmin 요청 md(`N:\Siriopsis\temp`): `/srv/Siriopsis` · nginx · paleolab 첫 화면 한 줄
- 백업 + `/healthz` 백업 나이 · 소개 화면 최소판

## 그 밖

- kopri-devdocs 대상 저장소 목록에 Siriopsis — `pull-repos.sh` 가 origin 소유자로 고르므로 paleoadmin 클론만 있으면 된다
