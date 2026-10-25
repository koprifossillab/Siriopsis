# TODOs

단계는 [P01](devlog/20261025_wetherilli_P01_stages.md), 003 에서 카탈로그 빛 묶음이 본체가 되었다.

## 반입 남은 것

- PTM 더미에 표본 붙이기 — 사람의 답을 기다린다(HANDOFF §0). 붙인 값은 반입으로 다시 만들 수 없다 → 백업 대상
- `(dorsal)`·`(vent)`(슬랩 전경)·`(ethanol)`·`(water)`(액침)·한 장짜리 — 다른 「방법」으로 표본 화면에 붙인다(종류를 더한다)

## 정밀 맞춤 (GPU)

- 빛 묶음마다 컷의 이동·회전·배율을 구해 `Frame` 에 값으로 둔다 — 맞춘 그림을 만들지 않고 뷰어가 겹쳐 그린다
- 낮은 빛 컷은 밝기 모양이 달라 밝기가 아니라 윤곽(기울기)으로 맞춘다. 딴 구도 컷(확대 등)은 「맞춤 안 됨」으로 표시
- 별도 requirements(`-pipeline`) — GPU 라이브러리는 웹 이미지에 넣지 않는다

## 뷰어

- DiaRUGA `/img` 축소본 서빙·`thumb`/`full` 태그·`_atlasview.html` 확대·이동을 옮긴다(머리에 출처)
- 표본 목록 → 표본(묶음 칸: 종류·처리·배율) → 묶음 화면. **PTM 은 빛 방향 판, 빛 묶음은 번호 줄** — 다르게 건다
- PTM 빛 벡터 좌표 방향을 그림자로 맞춘다
- 슬랩·표본에서 phyloserver 상세 화면으로 가는 링크(`catalog_id`)
- 축소본 캐시 `/data/Siriopsis/thumbcache` + `warm_thumbs`(컷 6만 — 화면 폭 축소본만 미리) · 브라우저 시험

## paleolab 에 길 (`v0.1.0`)

- Cropobite 에서 `deploy/srv/docker-compose.yml`(127.0.0.1:8100, NAS 읽기 전용 마운트)·`deploy/nginx/Siriopsis-subpath.conf`·`deploy/host/{install,deploy,smoke}.sh`
- paleoadmin 요청 md(`N:\Siriopsis\temp`): `/srv/Siriopsis` · nginx · paleolab 첫 화면 한 줄
- 반입을 cron 으로(새 사진) · 백업 + `/healthz` 백업 나이 · 소개 화면 최소판

## 그 밖

- kopri-devdocs 대상 저장소 — `pull-repos.sh` 가 origin 소유자로 고르므로 paleoadmin 클론만 있으면 된다
