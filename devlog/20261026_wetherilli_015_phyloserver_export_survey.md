# 015 — phyloserver `siriuspasset` 통째 내보내기 조사

2026-10-26 · `work/20261025-wetherilli` · wetherilli

사용자 요청 8번(「다 털어와도 된다. 우리 뷰어가 그 DB 기능을 완전히 대체할 수도 있다」). paleoadmin 이 phyloserver 0.109.0 의 `export_siriuspasset` 으로
NAS `/nfs/temp-share/Siriopsis/phyloserver-export/20261025/` 에 내보냈다(2025-10-25 22:14 → 23:00, phyloserver devlog 069). 무엇이 들었는지 적는다 — 옮기기는 아직 안 했다.

## 들어 있는 것

| | 행 | 메모 |
|---|---|---|
| `SpSlab` | 4,583 | Siriopsis 테이블의 슬랩은 4,304(사진이 있는 것) |
| `SpFossilSpecimen` | 9,505 | remarks ☆ 43 · counterpart 2,198(표본) / 890(슬랩) |
| `SpFossilImage` | 83,375 | 모두 `PHOTO`. 슬랩에만 28,147 · 표본에 55,228. **파일은 복사 안 함** — 모두 `original_path` 로 NAS `Sirius Passet Catalog` 를 가리킨다(166,749 파일·466 GB, `media_index.json` 에 경로·크기·md5). Siriopsis 가 이미 읽는 원본이다 |
| `SpEpmaSession`·`Map`·`Channel` | 176 · 201 · 4,855 | **파일까지 복사됨** — `media/epma/`, 15,728 파일 · 167 GB. 원래 자리 `/data3/epma` 는 열화 중인 디스크라 이것이 사본 노릇도 한다. 세션이 걸린 슬랩 93, 그 가운데 81 이 Siriopsis 테이블에 있다 |
| 이력(simple_history) | 슬랩 14,086 · 표본 18,789 · EPMA 457 | 표본 이력: 생성 14,144 · 삭제 4,639 · 고침 **6**. 사람이 화면에서 고친 일은 거의 없고, 반입을 다시 돌린 흔적이 대부분이다. `users.json` 이 비어 있다 — 이력의 `history_user` 가 모두 null 이다. phyloserver 화면이 simple_history 에 사용자를 넘기지 않았다(paleoadmin DONE). 누가 고쳤는지는 이력 행의 `modified_by` 글자로 본다 |
| `DirectoryScan`·`SpImageProcessingRecord` | 0 · 0 | |
| `missing_files.txt` | 0 | DB 가 가리키는데 없는 파일 없음 |

## 읽은 것

- **분류 정보 쪽은 Siriopsis 가 이미 다 받는다** — `export.json`(운영 배포는 paleoadmin 이 2026-10-26 아침)을 `import_catalog` 가 먼저 읽는다. 시험 서버(:8082)의 것으로 `parse_export` 가 4,583 슬랩을 읽는 것을 봤다
- **사진**은 옮길 것이 없다 — 같은 NAS 원본이다. 다만 phyloserver 가 사진을 **표본에** 붙여 둔 짝(55,228)은 Siriopsis 의 이름 규칙(`SP-…-52A-3`)과 대조할 거리다 — 다르면 phyloserver 쪽에 사람이 고친 것이 있다는 뜻
- **EPMA 는 Siriopsis 에 없는 새 「방법」이다** — 한 표본을 원소 지도로 본다. 「한 표본을 여러 방법으로」에 맞는다. 옮긴다면 `Stack.kind` 하나(`epma`)와 채널 이미지 뷰어
- **권한**: 내보낸 폴더·파일이 0777 이다(NAS 는 누구나 읽는다). 비밀은 없다(사용자 이름 칸만) — 지우기를 막으려면 paleoadmin 쪽에서 좁힌다

## 남은 것

- 사용자와 정할 것: Siriopsis 가 siriuspasset 을 대신한다면 (1) 슬랩·표본 편집 화면(지금은 phyloserver 에서 고친다) (2) EPMA 뷰어 (3) 사진-표본 짝 대조 — 차례
