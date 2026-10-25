#!/bin/bash
# 웹 컨테이너 시작. 이주는 기동 때 돈다 (.guides/web/deployment.md §7).
set -e

cd /app/web

python manage.py migrate --noinput

# collectstatic 은 아직 하지 않는다 — 템플릿이 CSS 를 인라인으로 들고 있다.

# 컷 축소본을 처음 만드는 요청이 0.2~0.5 초씩 걸리고, 화면 하나가 컷 수십 장을 한꺼번에 묻는다(미리 받기).
# 일꾼 셋이 한 요청씩만 받으면 줄이 선다 — 일꾼마다 실 넷(Pillow 는 풀고 줄이는 동안 GIL 을 놓는다).
exec gunicorn siriopsisweb.wsgi:application \
    --bind 0.0.0.0:9090 \
    --workers 3 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
