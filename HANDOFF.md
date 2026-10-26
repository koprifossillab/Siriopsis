# HANDOFF

**2026-10-26** · **`v0.3.1` 운영 중** — http://paleolab/Siriopsis/ ([014](devlog/20261026_wetherilli_014_release_v030.md) · [016](devlog/20261026_wetherilli_016_vent_beside_dorsal.md) vent 를 dorsal 옆에).
슬랩 전경(dorsal·vent) · 슬랩 화면(왼쪽 전경·속성 / 오른쪽 더미 카드) · 배율·스케일바·길이 재기 · 표본 테두리 · 글자 없음=A · ☆ 별표(`/starred/`) · counterpart 짝 ·
묶음 고치기와 백업(v0.2.0, [008](devlog/20261025_wetherilli_008_regroup_and_backup.md)). 일은 tmux 일꾼 둘 + 지휘 세션으로 나눠 했다(메모리 `parallel_tmux_and_admin_loop`).
**자료가 맞는지 확인을 기다리며 멈추지 않는다** — 사용자는 데이터가 옳다고 보고 틀을 짜는 중이다. 아래 §0 은 막는 일이 아니다.
다음은 사용자가 말해 줄 일들(TODOs 「사용자 요청」에 받는다), 그다음 **정밀 맞춤**(GPU) — 배율·테두리가 그 위에서 바로잡힌다.

## 0. 사람이 정할 것 · 기다리는 것

- **phyloserver** — 0.109.0 `export.json` 운영에 올라 `import_catalog` 가 그것을 읽는다(016: 목록에 없음 27 · counterpart phyloserver 652).
  통째 내보내기 조사는 [015](devlog/20261026_wetherilli_015_phyloserver_export_survey.md). Siriopsis 가 siriuspasset 을 대신할지, 무엇부터(편집 화면·EPMA·사진-표본 짝)는 사용자와 정한다
- **vent 의 뜻** — 슬랩 화면에서 dorsal 옆에 나란히 보인다(016). 슬랩 아랫면으로 보인다 — 사용자가 정한다
- **글자 없음=A 의 예외 66 슬랩** — NAS `survey/20261025_bare_not_a.csv`. `0577a`·`0577b` 의 소문자는 아직 물음
- **배율 doubt 1,611 묶음** — 스케일바를 안 그린다(눈금 부족·원근). 결과 NAS `survey/20261026_ruler_scale.csv`
- **phyloserver 에 없는 슬랩** — export.json 으로 393 → 27(SP-2022 의 163~185 따위). 목록에 더할 것인가
- **사본 폴더의 정본 규칙**(003 §한 것) — 컷 수 → 사본 표시 폴더 아님 → 얕은 경로. 사본도 들어가 있어(004) 뷰어에서 보고 정하면 된다
- Docker Hub `koprifossillab/siriopsis` 와 secret — git `v*` 태그를 밀기 전에(지금은 태그 없이 이 서버에서 굽는다)

## 1. 지금 있는 것

| | 지금 |
|---|---|
| 웹 | Django 5.2 · `core`(`/healthz` — 더미·컷 수, 컷 0 이면 degraded) · `specimens`(테이블·반입 · 화면 `/`·`/slab/<번호>/`·`/stack/<id>/` · 컷 `/frame/<id>.jpg?w=`) |
| 화면 | 슬랩 화면은 왼쪽 전경·속성·짝 / 오른쪽 더미 카드(009) · `/starred/` 별표 표본(013) · DiaRUGA 모양(006) — 목록은 연도 탭 → 백 번 구간 → NAS 열 개 폴더(또는 층준 구간), 설정 `/system/`(판 이력은 CHANGELOG), 대기 화면, 로고 `docs/assets/logo/` |
| 뷰어 | 스케일바(더블클릭 → 모양)·「길이」(m)·「테두리」(d, 더미마다 하나, 서버가 잰다 — 010·011). PTM 은 빛 방향 판, 빛 묶음은 번호 줄. 저해상도(1600, 기본)·고해상도(2560 + 확대하면 지금 컷만 원본), `h` 키. 축소본 캐시 `THUMB_CACHE` |
| 반입 | `scan_light_stacks`(PTM) · `scan_light_series`(빛 묶음) · `scan_slab_views`(전경 dorsal·vent) · `import_catalog`(phyloserver — export.json 먼저, 끝에 글자 없음=A) · `import_workbooks`(엑셀 ☆·counterpart) · `import_scales <CSV>`(배율, `pipeline/ruler_scale.py` 가 호스트에서 만든다) — 모두 원본은 읽기만 |
| 테이블 | 운영(v0.3.1 반입 뒤): 슬랩 4,359 · 묶음 16,279(빛 묶음 10,500 · PTM 22 · 전경 5,757) · 컷 77,661 · 배율 ok 8,885 · ☆ 60 · 짝 엑셀 691 + phyloserver 652 |
| 시험 | 115 (`python web/manage.py test core specimens`) + pipeline 5 (`python -m unittest discover -s pipeline/tests -t .`, `requirements-pipeline.txt`) |
| 묶음 고치기 | 더미 화면 오른쪽 칸 — 가르기·합치기·지우기(두 걸음), 컷 숨기기(한 걸음). 빛 묶음만. 반입은 `edited_at` 묶음을 건너뛴다, 새 컷은 「새로 찾은 컷」 조각 (`regroup.py`) |
| 백업 | `ops/backup_db.py` — 시간별 :50 `--keep 24` · NAS 05:40 · 실패 깃발 `BACKUP_FAIL.*` → `/healthz` degraded. compose `backup`(시간별, NAS 안 붙임)·`offsite`(NAS) 문. cron v0.3.0 조각 깔림(2026-10-26 paleoadmin) |
| 이미지·CI | `deploy/Dockerfile` · `.github/workflows/test.yml`(시험 → 굽기, `v*` 태그만 push) |
| 환경 | venv `~/venv/Siriopsis`, `workon sp`, `.guides` 링크, 개발 DB `Siriopsis.db`(gitignore — 반입 세 명령으로 7 분이면 다시 만든다) |
| 자료 | NAS `/nfs/temp-share/Sirius Passet Catalog/`(읽기만). 작업 공간 `/nfs/temp-share/Siriopsis/` — 조사 표는 `survey/`, paleoadmin 요청은 `temp/` |
| GPU | RTX 3060 Ti 8 GB — 무거운 분석(맞춤)은 여기서(사용자) |
| 라이선스 | AGPL-3.0 |
| 운영 | `/srv/Siriopsis`(compose, `127.0.0.1:8100`, 이미지는 이 서버에서 굽는다) · nginx `/Siriopsis/` · 첫 화면 카드. 판 올리기: 굽기 → `.env` 의 `IMAGE_TAG` → `docker compose up -d web`. 반입은 `docker compose run --rm manage <명령>`. 호스트에서 만든 파일(배율 CSV)은 `/srv/Siriopsis/backup/import/` 에 두면 컨테이너가 읽는다. 판 올리기 전에 `docker compose run --rm -T backup --note pre-<판> --flat --out /srv/Siriopsis/backup/pre_deploy --keep 20` |

## 2. 다음

`TODOs.md`.
