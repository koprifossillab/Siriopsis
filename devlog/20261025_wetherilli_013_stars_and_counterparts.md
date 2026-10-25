# 013 — 별표 표본과 counterpart 짝

2026-10-25 · `work/20261025-wetherilli-catalog` · wetherilli

TODOs 사용자 요청 5(별표 표본 모아 보기)와 6(counterpart 짝 슬랩). 둘 다 NAS `Sirius Passet Catalog` 의 엑셀 목록에서 시작한 말인데,
**원천은 phyloserver 다**(CLAUDE.md) — 그래서 먼저 두 곳을 비교했고, 엑셀은 phyloserver 가 비운 곳만 메운다.

## 비교 (2026-10-25)

| | phyloserver | 엑셀 |
|---|---|---|
| ☆ (remarks) | 목록 화면의 remarks 에 **43** | **62** (2016 1 · 2017 27 · 2022 34, `☆☆` 둘) |
| counterpart | 목록 화면에 없다. 슬랩·표본 **상세 화면**에만(`SpSlab.counterpart` · `SpFossilSpecimen.counterpart`) | 「Counterpart?」 칸과 remarks — 글 706 |

- ☆: phyloserver 의 43 은 모두 엑셀에도 있다. 엑셀에만 있는 19 가운데 17 은 phyloserver 목록에 슬랩이 없고(SP-2022-0165 …), 둘(`SP-2022-0120-C`·`0129-A`)은 목록에 있는데 ☆ 가 없다
- counterpart: phyloserver 의 값은 같은 엑셀에서 `import_specimens.py` 가 넣었고(슬랩 칸은 그 슬랩 **첫 행**의 값), 그 뒤로는 phyloserver 화면에서 사람이 고친다(이력이 남는다).
  상세 화면을 읽는 길(표본 9.5천 장, 한 장에 0.03 초 + 쉼 0.2 초 → 약 37 분)은 재 보고 버렸다 — 사용자가 phyloserver 에 `export.json` 을 만들기로 했다
  (요청서 NAS `Siriopsis/temp/20261025_request_phyloserver_json_export.md`)
- 엑셀 판: 한 연도에 파일이 둘인 때가 있다(2016 `compiled`/`+Updated2025`, 2022 `2025version`/`2026version`). 연도마다 고친 날짜가 가장 늦은 것 하나를 읽는다.
  **옛 파일에만 있는 행**은 2016 이 0, 2022 가 1(`SP-2022-289 FAKE`) — ☆·counterpart 가 있는 것은 0 이라 옛 파일은 읽지 않는다

## 한 것

- `specimens/workbook.py` + `import_workbooks` — 엑셀을 읽어(openpyxl `read_only`, 머리줄의 칸 이름으로) `Star`·`Counterpart` 테이블을 만든다(마이그레이션 `0007_catalog_workbook`).
  엑셀에서 온 것만 통째로 다시 만든다. 슬랩이 테이블에 없을 수 있어(사진이 없는 표본) 이름을 글자로 둔다. 글자 칸이 비면 별표는 A(012)
- counterpart 글 읽기(`parse_counterpart`) — 손으로 적어 꼴이 여럿이다: `Counterpart of 790` · `Counter part of 1496 A` · `conterpart of 548` · `counterpart ot 965` ·
  `Counterpart to 2325A` · `Counterpart of SP-2016-185, JV` · `counterpart 570 + 575 & 576 JV` · `Counter part of 1561D,2ea`. 번호만 있으면 그 행의 연도
- `catalog.sync` 가 **`export.json` 을 먼저 읽는다** — 404·연결 실패·꼴이 틀리면 지금처럼 목록 화면. export 를 읽은 슬랩은 표본·슬랩 칸의 counterpart 로
  phyloserver 의 짝(`origin=phyloserver`)을 다시 만들고 `Slab.counterpart_synced_at` 을 적는다. 슬랩 칸의 짝은 표본 칸에 없는 상대만 더한다(첫 행의 사본이라)
- **어느 쪽을 쓰나**(화면이 고른다, `workbook.starred`·`pairs_for`):
  ☆ — phyloserver 목록에 있는 슬랩은 그쪽 remarks, 없는 슬랩은 엑셀. counterpart — `counterpart_synced_at` 이 있는 슬랩은 phyloserver 의 것만, 없으면 엑셀. 행마다 출처를 보인다
- 화면: `/starred/`(표·격자, 대표 컷·표본·☆·분류군·문·층준·더미 수·출처·원문), 머리줄에 「☆ 별표」 링크 하나(`base.html`).
  슬랩 화면은 고치지 않고(7번이 다시 짠다) 조각 `specimens/_counterpart.html` 과 context `counterparts` 를 냈다 — 상대 슬랩의 대표 컷·링크·적힌 원문·출처
- 두 슬랩을 한 장에 찍은 전경(`SP-2016-64&65`, 꼬리 `(vent)` 도)을 **뒷 슬랩의 전경 칸에도** 더한다(`views.slab` 의 `overview`), 짝 목록에도 「같이 찍힘」으로
- `openpyxl` 을 `requirements-web.txt` 에 — 운영에서 `manage import_workbooks` 로 돈다. 가볍다(순수 파이썬)
- 시험 77 → 89(`test_workbook` 12). 고침을 하나씩 빼 보고 실패하는 것을 봤다 — 역방향 짝, 뒷 슬랩 전경, 가장 늦은 파일 고르기(픽스처 이름 차례가 같아 처음엔 못 잡아 고쳤다),
  `(vent)` 꼬리, phyloserver ☆ 합치기, `not counterpart`, 엑셀 비키기, 엑셀 ☆ 거르기, export 짝 반입, export 먼저 읽기, 엑셀 반입이 phyloserver 짝을 안 지우기

## 결과 (개발 DB 사본)

| | |
|---|---|
| 엑셀 행 | 8,362 (네 파일) |
| counterpart 글 | 706 → **번호를 읽음 694** · 짝 691 (한 글에 여럿이 있고 제 슬랩을 가리킨 7 을 뺐다, 불확실 3 — `CHECK: … 37?`·`probable … 802`) |
| 못 읽음 | 번호 없음 11 (`level from counterpart` 4 · 2018 의 빈 `Counterpart of` 7) · `not counterpart of 564` 1 · 제 슬랩을 가리킴 7 (`484 → 484` 처럼 적은 이의 잘못) |
| 슬랩 짝 | 243 — 둘 다 테이블에 있음 227 · 하나만 12 · 둘 다 없음 4 |
| 「Counterpart?」 칸의 짝이 아닌 값 | `JV`·`HM`·`NO PHOTO` … 1,526 — 짝이 아니라 읽지 않는다 |
| 두 슬랩 전경 | 이름 12 가지 가운데 11 이 엑셀의 짝과 같다(`1354&1355` 만 엑셀에 없다) |
| `/starred/` | 60 줄 — phyloserver 41 · 엑셀 19, 사진 있는 슬랩 45 |

`SP-2017-0389-B`·`SP-2022-0067-A` 는 phyloserver 에 ☆ 가 있지만 우리 테이블에 슬랩이 없어(사진 없음) 목록에 있는지 모른다 — 「엑셀」로 나온다. export.json 이 생기면 바로잡힌다.

## 왜 이렇게

- **엑셀은 버리지 않고 빈 곳 메우기로.** phyloserver 에 슬랩이 없는 SP-2022 후반은 엑셀에만 있다. 지금 운영에는 export.json 이 없어 counterpart 는 엑셀이 실제로 채운다
- **고르는 것은 반입이 아니라 화면.** 두 반입(`import_catalog`·`import_workbooks`)을 어느 차례로 돌려도 같은 화면이 되게 — 둘은 저마다 제 출처의 행만 다시 만든다
- **짝은 적힌 방향 그대로 둔다.** 양쪽에 같은 짝이 적힌 것이 많지만 글자가 다르기도 하다(`1404E → 1405F`, `1405E → 1404E`). 합치지 않고 화면에서 양쪽을 다 보인다
- **슬랩 화면은 조각으로.** 7번(지휘 세션)이 슬랩 화면을 다시 짠다 — 끼울 자리는 그쪽이 정한다
- 버린 것: 상세 화면 9.5천 장 읽기(위), 별표 칸을 `Specimen` 에 두기(사진 없는 표본이 표본 행으로 생겨 목록의 표본 수가 늘어난다)

## 남은 것

- phyloserver `export.json`·통째 내보내기 — 요청서가 NAS `temp/` 에 있다. 올라오면 `import_catalog` 가 저절로 그것을 먼저 읽는다
- 표본 화면이 생기면 짝을 표본 단위로(지금은 슬랩 단위로 묶고 글자는 줄마다 적는다)
