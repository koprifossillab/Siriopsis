# Siriopsis 웹 이미지 (ForGIA deploy/Dockerfile.base 에서 왔다).
#
# 자료·DB 는 굽지 않는다. 전부 마운트해서 본다 (.guides/web/data-safety.md §8).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성을 코드보다 먼저 깐다 — 코드만 고쳤을 때 이 층을 다시 받지 않는다
COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt

COPY . .

# 컨테이너는 1000:1000 으로 돈다 (compose 의 user:). root 로 돌면 DB 소유자가 바뀐다.
# 이름 있는 사용자가 없으므로 캐시 위치를 적어 둔다.
ENV HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

EXPOSE 9090
ENTRYPOINT ["/app/deploy/entrypoint-web.sh"]
