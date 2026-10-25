#!/bin/bash
# 웹 컨테이너 시작. 이주는 기동 때 돈다 (.guides/web/deployment.md §7).
set -e

cd /app/web

python manage.py migrate --noinput

# collectstatic 은 아직 하지 않는다 — 템플릿이 CSS 를 인라인으로 들고 있다.

exec gunicorn siriopsisweb.wsgi:application \
    --bind 0.0.0.0:9090 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
