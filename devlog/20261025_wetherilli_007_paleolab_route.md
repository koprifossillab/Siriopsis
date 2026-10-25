# 007 — paleolab 에 길: `v0.1.0`

2026-10-25 · `work/20261025-wetherilli` · wetherilli

P01 3단계. 사용자: 「paleolab 에 올리는 거 진행해줘」. Cropobite 의 배포 틀을 옮겼다 — 다시 짜지 않는다(CLAUDE.md).

## 한 것

- `deploy/srv/docker-compose.yml` — `127.0.0.1:8100`, 1000:1000, DB 디렉터리째, **NAS 원본은 읽기 전용**(`Sirius Passet Catalog:ro`), 축소본 캐시 `/data/Siriopsis/thumbcache`.
  반입은 같은 이미지의 `manage` 문(`docker compose run --rm manage scan_light_series` …) — 호스트 venv 로 운영 DB 를 열지 않는다
- `deploy/srv/env.template`(`IMAGE_TAG=v0.1.0`, `SIRIOPSIS_SCRIPT_NAME=/Siriopsis`) · `deploy/nginx/Siriopsis-subpath.conf`(끝 슬래시로 떼어 넘김, 소문자 주소 301,
  멈췄을 때 안내 `deploy/www/Siriopsis-unavailable.html`) · `deploy/host/install.sh`(sudo 한 번: `/srv/Siriopsis`, nginx include, paleolab 첫 화면 카드 — Sirius Passet Catalog 카드 바로 뒤)
- gunicorn 일꾼마다 **실 넷**(`--threads 4`) — 화면 하나가 컷 수십 장을 한꺼번에 묻고(미리 받기), 처음 만드는 축소본은 0.2~0.5 초다
- 이미지는 이 서버에서 굽는다(`docker build -f deploy/Dockerfile -t koprifossillab/siriopsis:v0.1.0 .`, 174 MB) — Cropobite 와 같다.
  **git 태그 `v0.1.0` 은 밀지 않는다** — CI 가 `v*` 태그에서 Docker Hub 로 밀려 하는데 secret 이 없어 실패한다(HANDOFF §0). Cropobite 도 태그 없이 판을 낸다
- 굽고 나서 시험 포트 8101 에 개발 DB **사본**으로 띄워 봤다: `/healthz` ok(v0.1.0, 묶음 10,522 · 컷 71,867), 링크가 `/Siriopsis/` 를 달고 나온다, 축소본·설정·대기 화면 200

## 하지 않은 것

- **백업** — 지금 DB 는 반입 세 명령으로 7 분이면 다시 만든다(사람이 붙인 값이 없다). 묶음 고치기가 들어오면 그 커밋에서 백업과 `/healthz` 백업 나이를 켠다(TODOs)
- **자동 반입 cron** — 카탈로그 사진은 드물게 들어온다. 손으로 `manage` 를 돌린다
- **축소본 미리 굽기** — 처음 보는 화면이 몇 초 걸린다. 운영에서 느리면 목록 대표 컷(400)부터
