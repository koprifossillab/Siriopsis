# TODOs

단계는 [P01](devlog/20261025_wetherilli_P01_stages.md), 003 에서 카탈로그 빛 묶음이 본체가 되었다.

## 반입 남은 것

- PTM 더미에 표본 붙이기 — 사람의 답을 기다린다(HANDOFF §0). 붙인 값은 반입으로 다시 만들 수 없다 → 백업 대상
- `(dorsal)`·`(vent)`(슬랩 전경)·`(ethanol)`·`(water)`(액침)·한 장짜리 — 다른 「방법」으로 표본 화면에 붙인다(종류를 더한다)

## 정밀 맞춤 (GPU)

- 빛 묶음마다 컷의 이동·회전·배율을 구해 `Frame` 에 값으로 둔다 — 맞춘 그림을 만들지 않고 뷰어가 겹쳐 그린다
- 낮은 빛 컷은 밝기 모양이 달라 밝기가 아니라 윤곽(기울기)으로 맞춘다. 딴 구도 컷(확대 등)은 「맞춤 안 됨」으로 표시
- 별도 requirements(`-pipeline`) — GPU 라이브러리는 웹 이미지에 넣지 않는다

## 뷰어 (005 첫 판 다음)

- PTM 빛 벡터 좌표 방향을 그림자로 맞춘다 — 지금 판은 +x 오른쪽·+y 위로 그리고 그렇게 적었다
- 맞춤 값이 생기면 빛 묶음 컷을 겹쳐 그릴 때 바로잡는다
- 브라우저 시험(playwright)을 저장소에 — 판을 누르면 그림이 바뀐다, ←/→ 차례, 해상도 바꾸기
- 목록 대표 컷(400 폭, 4천 장)만 미리 굽기(`warm_thumbs`)는 운영에서 처음 뜨는 속도를 보고
- 슬랩 전경(`dorsal`·`vent`)·액침·한 장짜리를 표본 화면의 다른 칸으로

## 묶음 고치기 (뷰어에서, 004)

- DiaRUGA `web/viewer/regroup.py` 와 시야 화면의 가르기·합치기·삭제를 옮긴다 — 컷을 다른 묶음으로, 묶음 둘을 하나로, 묶음·컷 지우기(숨김)
- **반입이 사람의 손을 덮지 않게** — 손댄 묶음 표시, 반입은 그 묶음을 건너뛰고 새 컷은 「묶이지 않은 컷」으로. 같은 커밋에서 `save_series`·지우기를 바꾼다
- 그때부터 백업이 계약 — 운영 전에

## paleolab 에 길 (`v0.1.0`)

- Cropobite 에서 `deploy/srv/docker-compose.yml`(127.0.0.1:8100, NAS 읽기 전용 마운트)·`deploy/nginx/Siriopsis-subpath.conf`·`deploy/host/{install,deploy,smoke}.sh`
- paleoadmin 요청 md(`N:\Siriopsis\temp`): `/srv/Siriopsis` · nginx · paleolab 첫 화면 한 줄
- 반입을 cron 으로(새 사진) · 백업 + `/healthz` 백업 나이 · 소개 화면 최소판

## 그 밖

- kopri-devdocs 대상 저장소 — `pull-repos.sh` 가 origin 소유자로 고르므로 paleoadmin 클론만 있으면 된다
