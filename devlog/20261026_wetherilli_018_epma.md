# 018 — EPMA 를 붙인다: phyloserver 메타 + `/data3/epma` 읽기 전용 (`v0.4.0`)

2026-10-26 · `work/20261025-wetherilli` · wetherilli

## 정한 것 (사용자 · paleoadmin, NAS `temp/20261026_proposal_epma_attach.md`)

- **EPMA 를 가져오는 쪽은 phyloserver 그대로**(`import_epma_sessions`·`convert_epma_binary`). Siriopsis 는 읽기만 한다
- 메타는 phyloserver 0.110.0 의 `GET /siriuspasset/epma.json`(세션 176 · 맵 201 · 채널 4,855, 칸 값 그대로)
- 파일은 `/data3/epma` 를 그 자리에서 `:ro` 로 — 같은 서버라 새로 가져온 세션이 바로 보이고 사본이 어긋날 일이 없다.
  NAS 의 두 벌(`phyloserver-export/20261025/media/epma` · `DatabaseBackup/phyloserver/epma`)은 **백업이라 읽지 않는다**

## 한 것

- 테이블 `EpmaSession`·`EpmaMap`·`EpmaChannel` (0009). 행마다 phyloserver id(`catalog_id`)가 열쇠. 슬랩·표본은 phyloserver id 로 잇고(`Slab.catalog_id`),
  테이블에 없는 슬랩이면 비워 두고 id 를 남긴다 — `import_catalog` 가 끝에 다시 잇는다(`epma.relink`)
- `import_epma` — `epma.json` 을 읽어 통째로 맞춘다(없어진 행은 지운다, 빈 것을 받으면 멈춘다). `--dump <폴더>` 는 내보낸 `models/SpEpma*.json`(dumpdata 꼴) — 칸이 같아 둘 다 받는다
- 화면
  - 슬랩 화면 오른쪽, 짝 칸 아래에 **EPMA** — 세션마다 카드(대표 채널 썸네일 · 측정일 · 맵·채널 수 · 장비·kV · 표본 글자)
  - `/epma/<id>/` — 왼쪽 큰 캔버스, 오른쪽 맵마다 채널 줄. 강도 뷰어는 phyloserver `static/js/epma_interactive.js` 에서 옮겼다
    (gzip 을 브라우저가 풀고 `<HH` 가로·세로 + uint16 LE 를 LUT 로 칠한다). 더한 것: 최솟값 슬라이더, ↑↓ 로 채널 넘기기, 고른 채널을 주소에(`?c=`), LUT 를 브라우저에 기억
  - 강도 파일이 없고 이미지만 있으면 이미지를, 둘 다 없으면 「만들지 않았다 — 원자료 경로」를 보인다
- 파일 서빙 `/epma/channel/<id>.jpg[?thumb=1]`·`.bin` — 테이블의 상대경로만, `EPMA_ROOT` 밖이면 404. `.bin` 은 `Content-Encoding` 없이 보낸다(브라우저가 먼저 풀면 뷰어가 두 번 푼다)
- compose 공통 마운트에 `/data3/epma:/data3/epma:ro`

## 버린 것

- 파일을 NAS 내보내기에서 읽기 — 얼려 둔 10-25 판이라 새 세션이 안 보이고, paleoadmin 이 백업이라고 못 박았다
- 원자료 CSV(채널마다 수십 MB)를 직접 읽기 — phyloserver 가 이미 `.bin.gz`(1/10)로 바꿔 둔다. 바꾸지 않은 채널은 phyloserver 에서 바꾸는 것이 맞다(원천이 하나)
- 뷰어를 `static/` 파일로 — 이 저장소는 화면 스크립트를 템플릿 안에 둔다(정적 파일 수집이 없다)

## 자료에서 본 것 (phyloserver 쪽에 알림)

- 슬랩이 테이블에 없는 세션 18 — 라벨이 `SP-2017-1357_0001_MAP_0001_csv` 처럼 슬랩 번호가 아닌 것이 phyloserver 에 슬랩으로 들어가 있다
- `Samsung_EPMA/SP-2016-1236&1237` 세션의 채널 383 개는 원소가 아니라 **광학 사진**이고 원소 칸이 `SP-2016-12` 로 읽혀 있다(`SP-2017-37(holotype)Images` 도 5 개)
- 채널 842 개는 이미지도 강도 파일도 없다(원자료 CSV 만) — 화면은 「파일 없음」으로 흐리게

## 시험

124 (+8) — 두 꼴(epma.json·dumpdata)이 같은 테이블, 테이블에 없는 슬랩은 id 만, 다시 반입하면 없어진 것을 지움, 빈 것은 안 지움, `relink`,
대표 채널(phyloserver 의 것 → 특수 채널 먼저), 파일 서빙(썸네일·이미지·`.bin` 머리), 뿌리 밖 경로 404, 화면. 뿌리 검사·`relink`·지우기를 빼면 실패하는 것을 보았다.
