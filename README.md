# Siriopsis

북그린란드 **시리우스 파셋**(Sirius Passet) 화석을 **한 표본, 여러 방법으로** 보는 이미지 뷰어.
극지연구소(KOPRI) 고생물 연구실의 사내망 웹 앱으로, paleo-server 의 `http://paleolab/Siriopsis/` 에 얹힌다(예정).

첫 이미지 유형은 **빛을 달리해 찍은 묶음**이다 — 카탈로그 사진(`SP-2022-131-1 … -6`, 약 9천 묶음)과 PTM 촬영(돔 50 방향, 22 벌)을,
DiaRUGA 가 한 시야를 여러 초점으로 넘겨 보듯 빛을 바꿔 가며 본다. 단계는 [P01](devlog/20261025_wetherilli_P01_stages.md).

> 지금은 빛 묶음 8,876 과 PTM 22 벌(슬랩 4,304 · 컷 6만)이 테이블에 들어가 있고, 화면은 아직 없다.

## 시작

```bash
python3 -m venv ~/venv/Siriopsis && . ~/venv/Siriopsis/bin/activate
pip install -r requirements.txt
python web/manage.py test core specimens
python web/manage.py migrate && python web/manage.py runserver 0.0.0.0:8051
```

작업 규칙은 [CLAUDE.md](CLAUDE.md), 지금 상태는 [HANDOFF.md](HANDOFF.md).

## 라이선스

[AGPL-3.0](LICENSE). 화석 사진은 이 저장소에 들어 있지 않다 — 연구실 NAS 에서 읽는다.
