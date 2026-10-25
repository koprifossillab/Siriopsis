# HANDOFF

**2026-10-25** · http://paleolab/Siriopsis/ ([007](devlog/20261025_wetherilli_007_paleolab_route.md)). 반입 끝, 뷰어는 DiaRUGA 모양([006](devlog/20261025_wetherilli_006_diaruga_look.md)).
**`v0.2.0` 운영 중** — 묶음 고치기 + 백업([008](devlog/20261025_wetherilli_008_regroup_and_backup.md)). 21:23 배포 전 사본(`backup/pre_deploy/`) 뒤에 올렸고, 첫 시간별·NAS 사본을 손으로 떠 `/healthz` ok.
([wetherilli 002](devlog/20261025_wetherilli_002_light_stacks_to_tables.md), [003](devlog/20261025_wetherilli_003_catalog_light_series.md), [004](devlog/20261025_wetherilli_004_keep_copies.md) — 사본도 넣었다).
**자료가 맞는지 확인을 기다리며 멈추지 않는다** — 사용자는 데이터가 옳다고 보고 틀을 짜는 중이다. 아래 §0 은 막는 일이 아니다.
다음은 사용자가 말해 줄 일들(TODOs 에 받는다), 그다음 **정밀 맞춤**(GPU).


**이어 할 것 (2026-10-25 22:40, 사용량 한도로 멈춤)** — 운영은 아직 v0.2.0. v0.3.0 에 넣을 것:
- 이 브랜치 `work/20261025-wetherilli`(`ae83368`): 슬랩 전경·vent(009), 슬랩 화면, catalog 3·5·6(012·013, 시험 89)
- viewer 브랜치 `work/20261025-wetherilli-viewer`(worktree `../Siriopsis-wt-viewer`): `3cc1052`(010 배율·스케일바·길이) · `ffe7af9`(011 테두리), 시험 94.
  **커밋 안 된 것**: devlog 010·011 초안, `devlog/README.md`·`TODOs.md`·`pipeline/ruler_scale.py` 고침 — 확인해 커밋. 배율 전체 실행(약 10,500 줄)은 끝나지 않았다 — `pipeline/ruler_scale.py --targets … --out …` 다시
- 순서: viewer 를 이 브랜치 위로 rebase → `makemigrations --merge`(0006_catalog·0007_catalog 와 0006_viewer·0007_viewer) → 시험 → main push → 배포 전 사본 → v0.3.0 → 운영 반입
  (`scan_slab_views` · `import_catalog` · `import_workbooks` · `import_scales <CSV — /srv/Siriopsis/backup/import/ 로 복사>`) → cron 조각 재설치 요청(timeout·offsite 문)
- paleoadmin: phyloserver 0.109.0 `export.json` 은 내일 아침 운영 배포 예정, 내보내기는 NAS `phyloserver-export/20261025.part/`(끝나면 `.part` 가 빠진다). 22:50 첫 자동 백업 확인

## 0. 사람이 정할 것

- **백업 cron** — paleoadmin 요청을 NAS `temp/20261025_request_backup_cron.md` 에 두었다(`/etc/cron.d/Siriopsis`). 깔리면 다음 :50 뒤 `/healthz` 의 `backup.age_h` 를 본다.
  깔리기 전에는 2 시간 뒤부터 `/healthz` 가 degraded 다(백업이 낡았다) — 그것이 맞는 경보다
- **PTM 더미의 표본** — 이름에 글자가 없는 PTM 21 벌(002 §결과): `52`(셋) = `52A` 와 같은 A? · `494`(넷) = A? · `601`(둘) = A(목록에 하나뿐)? ·
  `0577a`·`0577b` 의 소문자는 표본 글자인가 마주 조각인가 · SP-2011 두 슬랩은 phyloserver 에 없다 — 분류군은 어디서
- **phyloserver 에 없는 슬랩 393** — NAS `Siriopsis/survey/20261025_not_in_phyloserver.csv`. 목록에 더할 것인가
- **사본 폴더의 정본 규칙**(003 §한 것) — 컷 수 → 사본 표시 폴더 아님 → 얕은 경로. 사본도 들어가 있어(004) 뷰어에서 보고 정하면 된다
- Docker Hub `koprifossillab/siriopsis` 와 secret — git `v*` 태그를 밀기 전에(지금은 태그 없이 이 서버에서 굽는다)

## 1. 지금 있는 것

| | 지금 |
|---|---|
| 웹 | Django 5.2 · `core`(`/healthz` — 더미·컷 수, 컷 0 이면 degraded) · `specimens`(테이블·반입 · 화면 `/`·`/slab/<번호>/`·`/stack/<id>/` · 컷 `/frame/<id>.jpg?w=`) |
| 화면 | DiaRUGA 모양(006) — 목록은 연도 탭 → 백 번 구간 → NAS 열 개 폴더(또는 층준 구간), 설정 `/system/`(판 이력은 CHANGELOG), 대기 화면, 로고 `docs/assets/logo/` |
| 뷰어 | PTM 은 빛 방향 판, 빛 묶음은 번호 줄. 저해상도(1600, 기본)·고해상도(2560 + 확대하면 지금 컷만 원본), `h` 키. 축소본 캐시 `THUMB_CACHE` |
| 반입 | `scan_light_stacks`(PTM, `.lp`) · `scan_light_series`(카탈로그 빛 묶음, 정본 고르기) · `import_catalog`(phyloserver 목록) — 모두 원본은 읽기만 |
| 테이블 | 개발 DB: 슬랩 4,304 · 표본 6,700(분류군 6,653) · 묶음 10,522(`series` 정본 8,876 + 사본 1,624 · `ptm` 22) · 컷 71,867 |
| 시험 | 63 (`python web/manage.py test core specimens`) |
| 묶음 고치기 | 더미 화면 오른쪽 칸 — 가르기·합치기·지우기(두 걸음), 컷 숨기기(한 걸음). 빛 묶음만. 반입은 `edited_at` 묶음을 건너뛴다, 새 컷은 「새로 찾은 컷」 조각 (`regroup.py`) |
| 백업 | `ops/backup_db.py` — 시간별 :50 `--keep 24` · NAS 05:40 · 실패 깃발 `BACKUP_FAIL.*` → `/healthz` degraded. compose `backup` 문. **cron 은 paleoadmin 요청 중** (§0) |
| 이미지·CI | `deploy/Dockerfile` · `.github/workflows/test.yml`(시험 → 굽기, `v*` 태그만 push) |
| 환경 | venv `~/venv/Siriopsis`, `workon sp`, `.guides` 링크, 개발 DB `Siriopsis.db`(gitignore — 반입 세 명령으로 7 분이면 다시 만든다) |
| 자료 | NAS `/nfs/temp-share/Sirius Passet Catalog/`(읽기만). 작업 공간 `/nfs/temp-share/Siriopsis/` — 조사 표는 `survey/`, paleoadmin 요청은 `temp/` |
| GPU | RTX 3060 Ti 8 GB — 무거운 분석(맞춤)은 여기서(사용자) |
| 라이선스 | AGPL-3.0 |
| 운영 | `/srv/Siriopsis`(compose, `127.0.0.1:8100`, 이미지는 이 서버에서 굽는다) · nginx `/Siriopsis/` · 첫 화면 카드. 판 올리기: 굽기 → `.env` 의 `IMAGE_TAG` → `docker compose up -d web`. 반입은 `docker compose run --rm manage <명령>`(약 8 분). 판 올리기 전에 `docker compose run --rm -T backup --note pre-<판> --flat --out /srv/Siriopsis/backup/pre_deploy --keep 20` |

## 2. 다음

`TODOs.md`.
