# CLAUDE.md

**Siriopsis** — 북그린란드 시리우스 파셋(Sirius Passet, 캄브리아기 제3세) 화석의 이미지 뷰어.
**한 표본을 여러 방법으로 본다** — DiaRUGA 가 한 시야를 여러 초점으로 보듯, 여기서는 한 표본을
여러 빛 방향·여러 처리(무처리·흰 코팅·에탄올·물 …)로 찍은 이미지를 한 자리에서 넘겨 본다.
첫 이미지 유형은 **빛 방향 더미**(RTI 촬영 — 표본과 카메라를 고정하고 빛만 50 방향으로 바꿔 찍은 묶음).
paleo-server 에서 도는 웹 앱(Django + Docker + SQLite + gunicorn + nginx 서브경로).
**NAS 원본은 읽기만 한다.** 문서는 한국어로 쓴다 — 커밋 메시지, devlog, 주석 모두.

## 공통 규약

작업 체제·배포·데이터 안전·운영 규약은 `.guides/` 에 있다 — **이 저장소는 그것을 따른다.**

- 작업 체제(브랜치·devlog·말): `.guides/workflow.md`
- 웹 앱(배포·데이터 안전·운영): `.guides/web/README.md`
- 소속·라이선스·출처: `.guides/branding.md`

없으면 kopri-devdocs 클론이 안 걸린 것 — `../kopri-devdocs` 를 형제로 두고
`ln -s ../kopri-devdocs/guides .guides`. **이 저장소에는 커밋하지 않는다**(kopri-devdocs 는 private,
**이 저장소는 public** 이다 — 비밀번호·키·내부 메모를 커밋하지 않는다).
뷰어의 기준 구현은 DiaRUGA(초점 더미 뷰어), 이 저장소의 뼈대는 Cropobite 001(그 뿌리는 ForGIA)에서 왔다 —
배포 스크립트·nginx 조각·백업 스크립트는 다시 짜지 말고 거기서 옮긴다. **옮긴 파일은 머리에 출처를 적는다.**

## 이름

**표기는 `Siriopsis` 하나** — 저장소·경로(`/srv/Siriopsis`·`~/venv/Siriopsis`)·URL(`/Siriopsis/`)·
DB(`Siriopsis.db`). **기술이 소문자를 강제하는 자리만 `siriopsis`** — Docker Hub 이미지
(`koprifossillab/siriopsis`), 파이썬 패키지(`siriopsisweb`), `localStorage` 키.
환경변수는 `SIRIOPSIS_*`. 앱은 `core`(첫 화면·`/healthz`)와 `specimens`(슬랩·표본·더미·컷, 반입).
**슬랩·표본 이름은 phyloserver 꼴** — `SP-2016-0052`(번호 네 자리)·`SP-2016-0052-A`. NAS 의 `SP-2016-52A`·`52Z` 는 `specimens/names.py` 가 바꾼다
(끝의 대문자 `Z` 는 확대 촬영, 표본 글자가 아니다 — 사용자 확인).

**말** (자료의 엑셀 목록을 따른다 — P01 에서 정했다):
슬랩(Slab = `SP-2016-47`, 암석 한 덩이) · 표본(Specimen = 슬랩 안의 글자 `A`·`K` …, 화석 하나) ·
컷(사진 한 장) · **더미**(Stack = 한 표본을 같은 자리에서 한 가지 축만 바꿔 찍은 정렬된 컷들 — 빛 더미, 나중에 초점 더미) ·
처리(Preparation = 무처리·흰 코팅·마그네슘 코팅·에탄올·물). DiaRUGA 의 「시야」 자리가 여기서는 「더미」다.

## 작업 방식

- **브랜치: 하루치 브랜치** `work/<YYYYMMDD>-<계정>` → 로컬 `merge --ff-only` 로 main (현미경·연구실 서버 계열과 같다,
  `.guides/workflow.md` §2). 문서만 고치는 커밋은 main 에 바로.
- 작업 전 `git pull --rebase`. **`git add -A`·`.`·`commit -a` 금지** — 고친 파일만
  `git commit -F <메시지 파일> -- <파일…>`. 커밋 메시지는 한국어, 끝에 devlog 번호 `(wetherilli 001)`.
- 원격은 HTTPS(`https://github.com/koprifossillab/Siriopsis.git`) — 이 서버의 SSH 키는 `jikhanjung` 계정이고,
  초대는 `wetherilli` 가 받았다. `gh` credential helper 로 민다.
- **paleoadmin 권한이 필요한 일**(sudo · `/srv/Siriopsis` · nginx · `/srv/paleolab` 첫 화면 · `/etc/cron.d`)은
  요청을 md 로 써서 NAS `/nfs/temp-share/Siriopsis/temp/`(사용자 PC `N:\Siriopsis\temp`)에 둔다 —
  paleoadmin 쪽이 주기적으로 읽고 처리한다. 파일 이름은 **영문**(`YYYYMMDD_request_<일>.md`, 한글 이름은 윈도에서 안 보인다).
  처리됐는지는 결과(경로·응답)로 확인한다.

## devlog

`devlog/YYYYMMDD_{계정}_{nnn}_{title}.md`, 계획은 `_P{nn}_`, 제목은 영어 snake_case, **번호는 글쓴이마다**.
머리줄 아래 `날짜 · \`브랜치\` · 글쓴이`. 새 파일은 `devlog/README.md` 색인에 한 줄.
**무엇을 했는지보다 왜 그렇게 했고 무엇을 버렸는지**를 쓴다. 검토는 `docs/`, 정한 계획은 P 문서,
**HANDOFF 는 지금만** 말한다. 비밀번호·키를 적지 않는다.

## 말

**낱말 하나에 뜻 하나, 비유를 쓰지 않는다** (`.guides/workflow.md` §6). DiaRUGA·ForGIA 의
정해 둔 말을 물려받는다 — 비교하다(견주다 ✗) · DB 의 것은 **테이블**(화면의 것은 "표") ·
시험·CI 의 **레이어** · 늘어놓는 것은 **정렬한다**. 그래서 컷을 서로 맞추는 일은 「정렬」이 아니라 **「맞춤」**(registration)이다.

## 자료

원본은 NAS `/nfs/temp-share/Sirius Passet Catalog/`(사용자 PC `N:\Sirius Passet Catalog`, 510 GB, 이름은 UTF-8 한글).
**읽기만 한다** — 지우기·옮기기·이름 바꾸기를 하지 않는다.
**이 프로젝트의 NAS 작업 공간은 `/nfs/temp-share/Siriopsis/`**(사용자 PC `N:\Siriopsis`) — 사람에게 보일 자료(밀착 인화지·점검표)·
paleoadmin 요청(`temp/`)·사람이 넘겨줄 자료를 여기에 둔다. 만드는 파일·폴더 이름은 영문. 사정은 [P01](devlog/20261025_wetherilli_P01_stages.md) §자료.

- `SP-<연도> 샘플별/SP-<연도>(<번호 구간>)/SP-<연도>-<슬랩><표본>-<컷>.JPG` — 카탈로그 사진(약 8만 장). 컷끼리 구도가 달라 그대로는 더미가 아니다
- `SP-2016 샘플별/6D 외/PTM{, white coated}/<표본>/IMG_*.JPG + <표본>.lp + <표본>.ptm` — **빛 더미 22 벌**(벌마다 50 컷 + 빛 벡터). 1단계 자료
- 목록 엑셀(`SP-*_Catalog*.xlsx`) — 옛 사본. **분류 정보는 phyloserver 에서 읽는다**(아래)
- `@eaDir`·`Thumbs.db`·`*@SynoEAStream` 은 NAS 가 만든 것 — 읽지 않는다

**분류 정보의 원천은 phyloserver `siriuspasset`**(`http://paleolab/siriuspasset/specimen_list/`, 연구실이 고쳐 가는 목록).
JSON API 가 없어 `import_catalog` 가 목록 화면의 표를 읽는다(`specimens/catalog.py`) — 읽기만, 테이블에 있는 슬랩만.
서버 안에서는 `paleolab` 이름이 안 풀려 `http://172.16.116.98/siriuspasset/`(`SIRIOPSIS_CATALOG_URL`)로 부른다.

## 환경

```bash
workon sp                 # ~/venv/Siriopsis + ~/projects/Siriopsis
pip install -r requirements.txt
python web/manage.py test core specimens   # 시험 — 고치고 나면 이것부터
```

requirements 는 `-web`(이미지에 들어가는 것) · `-dev`(시험만) · 둘을 묶는 `requirements.txt`.
무거운 분석 라이브러리(맞춤·PTM 계산)가 들어오면 `-web` 에 넣지 말고 갈래 파일을 따로 만든다(ForGIA 의 web/pipeline 경계).

**자료도 DB 도 저장소 안에 없다.** 위치는 `.env`(`.env.template` 참고). 운영 자리는 정해 두었다:

```
/srv/Siriopsis/   db/  www/  docker-compose.yml  .env     ← 운영 (deploy/host/install.sh 가 세운다, paleoadmin)
/data/Siriopsis/                                         ← 축소본·타일 캐시 (큰 디스크)
nginx 80 의 /Siriopsis/ → 127.0.0.1:8100 (운영) · 8101 (시험)
```

**포트**: 컨테이너는 **8100**(운영)·**8101**(시험). 8090~8099 는 형제 앱 자리다.
개발 서버는 `8051`~`8059` 중 빈 것을 `ss -ltn` 으로 골라 `0.0.0.0` 에 붙인다(형제와 같은 대역을 나눠 쓴다).

```bash
export SIRIOPSIS_DB=$PWD/Siriopsis.db      # 운영 /srv/Siriopsis/db 를 가리키지 않는다
export IMAGE_TAG="dev $(git rev-parse --short HEAD)"
python web/manage.py migrate
python web/manage.py scan_light_stacks --under "SP-2016 샘플별/6D 외"   # 빛 더미 (NAS 읽기만, 몇 번을 돌려도 같다. 전체는 30초)
python web/manage.py import_catalog          # phyloserver 에서 층준·분류군
PORT=$(for p in $(seq 8051 8059); do ss -ltn | grep -q ":$p " || { echo $p; break; }; done)
setsid nohup python web/manage.py runserver 0.0.0.0:$PORT > /tmp/siriopsis-runserver.log 2>&1 < /dev/null &
echo "http://172.16.116.98:$PORT/"
```

- `DEBUG` 면 `Test Server` 워터마크가 저절로 뜬다(`core/context.py`). **끄지 않는다.**
- **`pkill -f "runserver …"` 는 자기 명령줄까지 잡아 셸을 죽인다** — `pkill -f "runserver 0.0.0.0:805[1]"` 처럼 패턴을 비껴 쓴다.
- **테스트로 띄울 때 DB 는 언제나 사본** — 운영 DB 를 붙이지도, `cp` 로 뜨지도 않는다(WAL).
  **호스트는 살아 있는 운영 DB 를 열지 않는다 — 읽기도** (`.guides/web/data-safety.md` §14).

## 시험

호스트 venv 로 돈다 — 시험은 자기 DB 를 새로 만들고 끝나면 버린다. 그것을 `core/tests/base.py` 가
확인한다(운영 DB 를 열면 멈춘다). 새 시험은 `SafeTestCase` 를 딛는다. **시험은 NAS 원본을 읽지 않는다** — 픽스처 이미지를 스스로 만든다.
**되살려서 실패하는 것을 본 뒤에야 시험이 있다고 말한다** — 고침을 빼 보고 실패하는지 확인한다.
GitHub Actions 가 push 마다 시험을 돌리고, 통과한 것만 이미지로 굽는다(`v*` 태그만 Docker Hub 로).
