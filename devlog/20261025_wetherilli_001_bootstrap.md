# 001 — 작업 환경

2026-10-25 · `main` · wetherilli

빈 저장소(`koprifossillab/Siriopsis`, **public**)에 작업 환경을 세웠다. 기준은 kopri-devdocs `guides/`,
뼈대는 가장 최근에 같은 일을 한 Cropobite 001(`5bda0f0`)을 그대로 가져와 이름만 바꿨다.

## 한 것

- **Django 뼈대** — Cropobite 001 의 `cropobiteweb` → `siriopsisweb`, 환경변수 `CROPOBITE_*` → `SIRIOPSIS_*`.
  앱은 `core` 하나 — 첫 화면과 `/healthz`(ok/degraded/unhealthy, degraded 는 200, 백업 나이 게이트 기본 꺼짐)
- **시험 4개** + `SafeTestCase`. degraded 를 503 으로 바꿔 `test_stale_backup_is_degraded_not_503` 이 실패하는 것을 보고 되돌렸다
- **이미지**(`deploy/Dockerfile`, 1000:1000, 기동 때 migrate) · **CI**(시험 → 굽기, `v*` 태그만 Docker Hub)
- **문서** — CLAUDE.md · README · HANDOFF · TODOs · CHANGELOG · devlog 색인
- venv `~/venv/Siriopsis`(Python 3.14), `workon sp`, `.guides` 링크
- 자료 조사와 DiaRUGA 뷰어 조사 → [P01](20261025_wetherilli_P01_stages.md)

## 정한 것

- **이름**: 표기 `Siriopsis` 하나, 기술이 강제하는 자리만 `siriopsis`, 환경변수 `SIRIOPSIS_*`
- **포트 8100(운영)·8101(시험)** — 8090~8096·8098 이 쓰이고 8097·8099 는 형제 앱이 잡아 둔 자리라 그 다음 빈 둘
- **NAS 작업 공간 `/nfs/temp-share/Siriopsis/`**(사용자 PC `N:\Siriopsis`) — 사용자가 정했다. paleoadmin 몫의 일은
  `temp/` 에 요청 md 를 두면 paleoadmin 쪽이 주기적으로 읽고 처리한다. 원본 자료는 `Sirius Passet Catalog/` 에 그대로 둔다
- **브랜치는 하루치 브랜치**, devlog 는 글쓴이별 꼴 — Cropobite 와 같다
- **말**: 슬랩 · 표본 · 컷 · 더미 · 처리 — 엑셀 목록의 `slab no.`·`specimen no.` 를 따른다. DiaRUGA 의 「시야」 자리가 「더미」다.
  컷을 서로 맞추는 일은 「맞춤」 — 「정렬」 은 늘어놓기에 이미 쓰인다(DiaRUGA 의 말)

## 버린 것

- **Cropobite 의 지금 판(v0.2.x)에서 가져오기** — 노두·EXIF·지도 코드가 섞여 있다. 뼈대만 있는 001 이 깨끗하다.
  Pillow·whitenoise 는 1단계에서 쓸 때 넣는다
- **배포 스크립트·compose·nginx 를 지금 옮기기** — 운영할 자료가 없으면 smoke 의 도메인 검사·백업 대상이 빈칸으로 굳는다(3단계)
- **`LICENSE`** — 사람이 정할 일. 저장소가 public 이라 HANDOFF 맨 위에 올렸다
