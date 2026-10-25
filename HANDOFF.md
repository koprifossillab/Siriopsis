# HANDOFF

**2026-10-25** · 판 없음 · 작업 환경이 섰고 단계 계획이 있다([wetherilli 001](devlog/20261025_wetherilli_001_bootstrap.md),
[P01](devlog/20261025_wetherilli_P01_stages.md)). 다음은 **1단계 — 빛 더미를 테이블로**.

## 0. 사람이 정할 것

- **라이선스** — `LICENSE` 가 없으면 라이선스가 없다(`.guides/branding.md` §3). **저장소가 public 이다.** 형제 웹 앱은 대부분 AGPL-3.0
- 빛 더미 폴더의 `Z` 꼬리 = 확대 촬영으로 읽었다 — 맞는지
- Docker Hub `koprifossillab/siriopsis` 와 secret — 첫 `v*` 태그 전에(이 서버에서만 굽는다면 없어도 된다)

## 1. 지금 있는 것

| | 지금 |
|---|---|
| 웹 | Django 5.2 · `siriopsisweb`(설정) · `core`(첫 화면 · `/healthz`) · 판 번호·`Test Server` 워터마크 |
| 시험 | 4개 (`python web/manage.py test core`) — `/healthz` 세 상태 · 첫 화면 |
| 이미지 | `deploy/Dockerfile` + `entrypoint-web.sh`(기동 때 migrate · gunicorn :9090) |
| CI | `.github/workflows/test.yml` — 시험 → 이미지 굽기(`v*` 태그만 push) |
| 환경 | venv `~/venv/Siriopsis`, `workon sp`, `.guides` → `../kopri-devdocs/guides` |
| 자료 | NAS `/nfs/temp-share/Sirius Passet Catalog/`(읽기만). 1단계 자료는 `SP-2016 샘플별/6D 외/PTM{, white coated}/` 의 빛 더미 22 벌 |
| NAS 작업 공간 | `/nfs/temp-share/Siriopsis/` — paleoadmin 요청은 `temp/` 에 md |
| 운영 | **없다.** 자리만 정했다 — `/srv/Siriopsis`, nginx `/Siriopsis/`, 포트 8100(운영)·8101(시험) |

## 2. 다음

P01 §단계, `TODOs.md`.
