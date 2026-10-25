# 014 — `v0.3.0` 운영에

2026-10-26 · `work/20261025-wetherilli` · wetherilli

사용자 요청 1~7(TODOs 「사용자 요청 (2026-10-25)」)을 tmux 세션 둘과 지휘 세션이 나눠 했고([009](20261025_wetherilli_009_slab_views_and_slab_page.md) ·
[010](20261025_wetherilli_010_ruler_scale.md) · [011](20261025_wetherilli_011_specimen_outline.md) · [012](20261025_wetherilli_012_bare_name_is_a.md) ·
[013](20261025_wetherilli_013_stars_and_counterparts.md)), 지휘 세션이 모아 판을 올렸다(사용자: 「네가 모아서 판 올리도록 해」).

## 한 차례

1. viewer 세션이 사용량 한도로 22:36 에 멈췄다 — 커밋 둘(010·011)은 들어가 있었고, devlog 결과 절·색인은 지휘 세션이 채워 커밋했다(배율 전체 실행은 그 전에 끝나 있었다: 10,500 줄)
2. viewer 브랜치를 지휘 브랜치 위로 rebase — 충돌은 모두 둘 다 더한 것(모델 Star·Counterpart 와 Scale, `views` import 줄, devlog 색인). `0008_merge_…` 로 catalog(0006·0007)와 viewer(0006·0007) 갈래를 이었다. 시험 115 + pipeline 5
3. 개발 DB 사본에 migrate·`import_workbooks`·`import_scales` → 화면 확인(스케일바 20 mm 가 사진 속 자의 눈금과 맞다 — 54 px/mm × 18 % ≈ 화면 10 px/mm)
4. main push → 배포 전 사본(`pre_deploy/…_004337_pre-v0.3.0.db`) → 굽기(openpyxl 3.1.5 포함) → 시험 포트 8101(마이그레이션 다섯·화면 200) → 운영 00:45
5. 운영 반입(00:44~00:48, 4 분):
   - `scan_slab_views` — 사진 5,794 → 정본 4,829 · 사본 928
   - `import_catalog` — 슬랩 3,966 · 목록에 없음 393 · 글자 없는 더미 2,450 중 A 2,340 · 예외 66 (export.json 은 아직 404 → 목록 211 쪽)
   - `import_workbooks` — ☆ 62 · 짝 691
   - `import_scales` — ok 8,885 · doubt 1,611 · none 4, 어긋난 줄 0
   - 끝에 `manual/…_post-v0.3.0-import.db`(슬랩 4,359 · 묶음 16,279 · 컷 77,661)
6. cron 조각 다시 깔기 요청 — NAS `temp/20261026_request_backup_cron_v030.md`(새 compose 의 `offsite` 문이 선 뒤에 두었다)

## 그 밖에 밤사이

- 시간별 백업 cron 이 22:50·23:50 에 돌았다(integrity ok) — paleoadmin 확인과 같다
- phyloserver 내보내기가 끝났다 — 조사는 [015](20261026_wetherilli_015_phyloserver_export_survey.md)

## 걸린 것

- 일꾼 세션이 사용량 한도로 끊기면 REPORT 없이 끝난다 — 지휘 세션은 `tj status`·`git log` 로 어디까지 왔는지 읽고 이어야 한다. 커밋을 잘게 한 것이 살렸다
- 지휘 세션도 한도에 걸려 00:40 까지 멈췄다. 그 사이 HANDOFF 맨 위에 「이어 할 것」을 적어 둔 것으로 이어 갔다
