# Siriopsis

북그린란드 **시리우스 파셋**(Sirius Passet) 화석을 **한 표본, 여러 방법으로** 보는 이미지 뷰어.
극지연구소(KOPRI) 고생물 연구실의 사내망 웹 앱으로, paleo-server 의 `http://paleolab/Siriopsis/` 에 얹힌다(예정).

첫 이미지 유형은 **빛 방향 더미** — 표본과 카메라를 고정하고 빛만 50 방향에서 비춰 찍은 묶음(RTI 촬영)을,
DiaRUGA 가 한 시야를 여러 초점으로 넘겨 보듯 빛 방향을 바꿔 가며 본다. 단계는 [P01](devlog/20261025_wetherilli_P01_stages.md).

> 지금은 뼈대(Django · `/healthz` · 시험 · 이미지 · CI)만 있다.

## 시작

```bash
python3 -m venv ~/venv/Siriopsis && . ~/venv/Siriopsis/bin/activate
pip install -r requirements.txt
python web/manage.py test core
python web/manage.py migrate && python web/manage.py runserver 0.0.0.0:8051
```

작업 규칙은 [CLAUDE.md](CLAUDE.md), 지금 상태는 [HANDOFF.md](HANDOFF.md).
