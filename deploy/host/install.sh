#!/bin/bash
# Siriopsis 를 http://paleolab/Siriopsis/ 에 처음 얹는다. **sudo 로 한 번** 돌린다 (몇 번 돌려도 같다).
# Cropobite deploy/host/install.sh 에서 왔다 — 자동 반입 cron 은 아직 없다(사진이 새로 들어오는 일이 드물다).
# 백업 cron(/etc/cron.d/Siriopsis)은 v0.2.0 부터 (wetherilli 008 — 묶음 고치기로 DB 에 다시 만들 수 없는 것이 생겼다).
#
#   sudo bash deploy/host/install.sh
#
# sudo 가 필요한 일만 여기 모았다 — /srv 아래 자리, nginx 조각, paleolab 첫 화면 카드.
# 컨테이너를 띄우고 반입하는 일은 이것이 끝난 뒤 docker 그룹 사용자가 한다 (끝에 적힌 명령).
#
# 고치는 파일은 모두 먼저 사본을 뜬다. nginx 설정이 깨지면 사본으로 되돌리고 멈춘다.
# 사본은 /etc/nginx/sites-enabled/ 에 두지 않는다 — 거기 둔 파일은 nginx 가 전부 읽는다.
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "sudo 로 돌릴 것: sudo bash $0" >&2; exit 1; }
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SRV=/srv/Siriopsis
SITE=/etc/nginx/sites-enabled/phyloserver
LANDING=/srv/paleolab/index.html
STAMP=$(date +%Y%m%d_%H%M%S)
OWNER=paleoadmin:paleoadmin

echo "== 1. $SRV"
install -d -o paleoadmin -g paleoadmin -m 2775 "$SRV" "$SRV/db" "$SRV/www" "$SRV/backup"
install -o paleoadmin -g paleoadmin -m 664 "$REPO/deploy/srv/docker-compose.yml" "$SRV/docker-compose.yml"
install -o paleoadmin -g paleoadmin -m 664 "$REPO/deploy/www/Siriopsis-unavailable.html" "$SRV/www/"
if [ ! -f "$SRV/.env" ]; then
    # 처음 한 번만 만든다. 있으면 건드리지 않는다 — 통째로 덮으면 비밀키가 날아간다
    key=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    sed "s|^SIRIOPSIS_SECRET_KEY=.*|SIRIOPSIS_SECRET_KEY=$key|" "$REPO/deploy/srv/env.template" > "$SRV/.env"
    chown $OWNER "$SRV/.env"; chmod 660 "$SRV/.env"
    echo "   .env 를 만들었다"
else
    echo "   .env 는 이미 있다 — 그대로 둔다"
    # 판이 오르며 견본에 생긴 열쇠만 끝에 더한다 (있는 줄은 건드리지 않는다)
    while IFS= read -r line; do
        key="${line%%=*}"
        if ! grep -q "^$key=" "$SRV/.env"; then
            echo "$line" >> "$SRV/.env"; echo "   .env 에 더했다: $key"
        fi
    done < <(grep -E '^SIRIOPSIS_BACKUP|^SIRIOPSIS_OFFSITE' "$REPO/deploy/srv/env.template")
fi
install -d -o paleoadmin -g paleoadmin -m 2775 /data/Siriopsis /data/Siriopsis/thumbcache
# 일별 오프사이트 사본 자리 (backup 문이 붙인다 — 없으면 docker 가 root 로 만든다)
install -d -o paleoadmin -g paleoadmin -m 2775 /nfs/temp-share/Siriopsis/backup

echo "== 2. nginx"
install -m 644 "$REPO/deploy/nginx/Siriopsis-subpath.conf" /etc/nginx/snippets/Siriopsis-subpath.conf
if ! grep -q "snippets/Siriopsis-subpath.conf" "$SITE"; then
    cp -p "$SITE" "/etc/nginx/phyloserver.bak-siriopsis-$STAMP"
    # 형제 조각들 바로 아래, `location /` 보다 앞에 넣는다
    python3 - "$SITE" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
anchor = "    include snippets/Cropobite-subpath.conf;\n"
line = "    # Siriopsis 시리우스 파셋 표본 뷰어 (/Siriopsis/). 실체는 Siriopsis 저장소의 deploy/nginx/Siriopsis-subpath.conf\n" \
       "    include snippets/Siriopsis-subpath.conf;\n"
if anchor in s:
    s = s.replace(anchor, anchor + line, 1)
else:
    i = s.index("    location / {")
    s = s[:i] + line + "\n" + s[i:]
open(p, "w").write(s)
PY
    echo "   include 한 줄을 넣었다 (사본 /etc/nginx/phyloserver.bak-siriopsis-$STAMP)"
fi
if ! nginx -t 2>&1; then
    echo "!! nginx -t 실패 — 되돌린다" >&2
    [ -f "/etc/nginx/phyloserver.bak-siriopsis-$STAMP" ] && cp -p "/etc/nginx/phyloserver.bak-siriopsis-$STAMP" "$SITE"
    rm -f /etc/nginx/snippets/Siriopsis-subpath.conf
    exit 1
fi
systemctl reload nginx
echo "   다시 읽혔다"

echo "== 3. paleolab 첫 화면 카드"
install -o paleoadmin -g paleoadmin -m 664 "$REPO/docs/assets/logo/icons/siriopsis-icon-tile-96.png" /srv/paleolab/img/siriopsis-96.png
if ! grep -q 'href="/Siriopsis/"' "$LANDING"; then
    cp -p "$LANDING" "$LANDING.bak-$STAMP"
    python3 - "$LANDING" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
card = '''      <a class="item" href="/Siriopsis/">
        <span class="item-icon"><img src="img/siriopsis-96.png?v=20261025" alt="" style="width:1.4rem;height:1.4rem;border-radius:22%;display:block"></span>
        <span class="item-title">Siriopsis</span>
        <span class="item-desc">Sirius Passet fossils under many lights. 시리우스 파셋 표본 뷰어.</span>
      </a>
'''
# Sirius Passet Catalog 카드 바로 뒤 — 같은 표본을 보는 두 화면이 나란히 선다
i = s.index('href="/siriuspasset"')
j = s.index("</a>\n", i) + len("</a>\n")
s = s[:j] + card + s[j:]
open(p, "w").write(s)
PY
    echo "   카드를 넣었다 (사본 $LANDING.bak-$STAMP)"
else
    echo "   카드는 이미 있다"
fi

echo "== 4. 백업 cron"
install -o root -g root -m 644 "$REPO/deploy/cron.d/Siriopsis" /etc/cron.d/Siriopsis
echo "   /etc/cron.d/Siriopsis — 시간별 :50, NAS 05:40. 다음 날 /healthz 의 backup 을 본다"

cat <<EOF

== 끝. 이제 docker 그룹 사용자로 (sudo 없이):
   cd $SRV && docker compose up -d web
   docker compose run --rm manage scan_light_stacks --under "SP-2016 샘플별/6D 외"
   docker compose run --rm manage scan_light_series
   docker compose run --rm manage import_catalog
   curl -s http://localhost/Siriopsis/healthz
EOF
