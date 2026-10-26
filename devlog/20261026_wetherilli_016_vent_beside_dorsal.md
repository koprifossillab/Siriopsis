# 016 — vent 를 dorsal 옆에, phyloserver export.json 반입 (`v0.3.1`)

2026-10-26 · `work/20261025-wetherilli` · wetherilli

## 한 것

- **슬랩 화면 왼쪽에 dorsal 과 vent 를 나란히** (사용자 2026-10-26 「vent 는 dorsal 하고 병렬적으로 보여줘」).
  vent 가 있으면 왼쪽 칸을 넓혀(`.slabv.pair`, 420 → 760 px) 두 장을 반씩, 아래에 「슬랩 전경 · dorsal / vent」. 좁은 창(1100 px 아래)은 한 칸으로 내린다
- 짝은 대표가 dorsal 일 때만 짓는다. vent 만 있는 슬랩은 지금처럼 vent 가 혼자 대표다(나란히 둘 상대가 없다)
- 화면에서 본 vent(`SP-2016-0101`)는 슬랩을 뒤집어 찍은 아랫면으로 보인다 — 뜻은 사용자가 정한다(HANDOFF §0)

## 버린 것

- vent 를 대표 아래 작은 그림(`herothumbs`)에 두기 — 지금까지 그 자리였고, 사용자가 「병렬」을 말했다. 두 면을 같은 크기로 놓아야 비교할 수 있다
- 오른쪽 더미 카드 칸에 vent 를 줄로 넣기 — 슬랩 자체를 찍은 사진이라 표본 칸에 넣지 않는다(009)

## 운영

- paleoadmin 이 아침에 cron v0.3.0 조각을 깔고 NAS 사본을 한 번 메웠다(`Siriopsis_20261026.2.db`) — `/healthz` ok
- phyloserver 0.109.0 이 운영에 올라 `export.json` 이 200 — `import_catalog` 한 번: 슬랩 4,332 찾음 · **목록에 없음 393 → 27** ·
  표본 채움 8,287 · A 2,339 · 예외 66. counterpart 는 phyloserver 652 행이 새로 들었고(그 슬랩은 엑셀의 짝을 안 쓴다), ☆ 60
- 시험 115 (+ 짝·vent 혼자의 단언, 짝을 빼면 실패하는 것을 보았다)
