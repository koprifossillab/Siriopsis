# HANDOFF

**2026-10-25** · 판 없음 · 1단계 끝 — 빛 더미 22 벌이 테이블에 있다([wetherilli 002](devlog/20261025_wetherilli_002_light_stacks_to_tables.md)).
다음은 **2단계 — 빛 더미 뷰어**([P01](devlog/20261025_wetherilli_P01_stages.md)).

## 0. 사람이 정할 것

- **이름에 표본 글자가 없는 더미의 표본** — 지금 표본이 붙은 것은 `SP-2016-52A`(무처리 전체) 하나뿐이다(002 §결과)
  - `SP-2016-52`(무처리 확대 · 흰 코팅 전체·확대) — `52A` 와 같은 A(*Kerygmachela*)인가
  - `SP-2016-494`(넷) — A(*Kerygmachela*)인가 (B·C 는 *Isoxys*)
  - `SP-2016-601`(둘) — phyloserver 에 A 하나뿐이다
  - `SP-2011-0577a`·`0577b` — 소문자 a/b 는 표본 글자인가, 마주 조각(part/counterpart)인가
  - `SP-2011-0203`·`0577` 은 phyloserver 목록에 없다 — 분류군을 어디서 얻나
- Docker Hub `koprifossillab/siriopsis` 와 secret — 첫 `v*` 태그 전에(이 서버에서만 굽는다면 없어도 된다)

## 1. 지금 있는 것

| | 지금 |
|---|---|
| 웹 | Django 5.2 · `core`(첫 화면 · `/healthz` — 더미·컷 수, 컷 0 이면 degraded) · `specimens`(테이블·반입, 화면 없음) |
| 반입 | `scan_light_stacks`(NAS `.lp` → Stack·Frame, 읽기만) · `import_catalog`(phyloserver 목록 → 층준·분류군) |
| 시험 | 18 (`python web/manage.py test core specimens`) |
| 이미지·CI | `deploy/Dockerfile` · `.github/workflows/test.yml`(시험 → 굽기, `v*` 태그만 push) |
| 환경 | venv `~/venv/Siriopsis`, `workon sp`, `.guides` → `../kopri-devdocs/guides`, 개발 DB `Siriopsis.db`(gitignore — 반입 두 명령으로 다시 만든다) |
| 자료 | NAS `/nfs/temp-share/Sirius Passet Catalog/`(읽기만). NAS 작업 공간 `/nfs/temp-share/Siriopsis/` — paleoadmin 요청은 `temp/` 에 md |
| 라이선스 | AGPL-3.0 |
| 운영 | **없다.** 자리만 정했다 — `/srv/Siriopsis`, nginx `/Siriopsis/`, 포트 8100(운영)·8101(시험) |

## 2. 다음

`TODOs.md`.
