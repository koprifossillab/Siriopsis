# TODOs

단계는 [P01](devlog/20261025_wetherilli_P01_stages.md).

## 1단계 — 빛 더미를 테이블로

- 모델 `Slab`·`Specimen`·`Stack`(종류·처리·배율)·`Frame`(seq·빛 벡터)
- `scan_light_stacks`(`.lp` → Stack/Frame, NAS 읽기만, 몇 번을 돌려도 같게) · `import_catalog`(엑셀 → 분류군·문·층준)
- `/healthz` 에 Frame ≠ 0

## 2단계 — 빛 더미 뷰어

- DiaRUGA `/img` 축소본 서빙·`thumb`/`full` 태그·`_atlasview.html` 확대·이동을 옮긴다(머리에 출처)
- 표본 목록 → 표본(더미 칸) → 더미(그림 + 빛 방향 판 + 컷 줄, 50 컷 미리 받기, ←/→·↑/↓)
- 빛 벡터 좌표 방향을 그림자로 맞춘다
- 축소본 캐시 `/data/Siriopsis/thumbcache` + `warm_thumbs` · 브라우저 시험

## 3단계 — paleolab 에 길 (`v0.1.0`)

- Cropobite 에서 `deploy/srv/docker-compose.yml`(127.0.0.1:8100)·`deploy/nginx/Siriopsis-subpath.conf`·`deploy/host/{install,deploy,smoke}.sh`
- paleoadmin 요청 md(`N:\Siriopsis\temp`): `/srv/Siriopsis` · nginx · paleolab 첫 화면 한 줄
- 백업 + `/healthz` 백업 나이 · 소개 화면 최소판

## 그 밖

- kopri-devdocs 대상 저장소 목록에 Siriopsis — `pull-repos.sh` 가 origin 소유자로 고르므로 paleoadmin 클론만 있으면 된다
