#!/usr/bin/env bash
# Punkt Zycia (AED4Life GUI) - one-shot startup script for a Debian/Ubuntu VM.
#
# Usage (from the copied/cloned gui folder, nothing else required):
#     bash start.sh
#
# Optional overrides (environment variables):
#     PUBLIC_IP     public IP of this VM        (default: auto-detected)
#     DOMAIN        host name for HTTPS         (default: <ip-with-dashes>.sslip.io)
#     API_UPSTREAM  AED4Life .NET API address   (default: https://20.215.200.98:7231)
#
# What it does: installs Caddy, publishes the static GUI from ./aplikacja,
# proxies /api4life/* to the AED4Life API (so the browser never sees the API's
# self-signed certificate), obtains a Let's Encrypt certificate for the
# sslip.io name, and (if ./zrodla/aedverify is present) runs the verification
# backend as a systemd service. Safe to re-run.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || exec sudo -E bash "$0" "$@"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if   [ -f "$HERE/aplikacja/index.html" ]; then APP="$HERE/aplikacja"; VERIFY="$HERE/zrodla/aedverify"
elif [ -f "$HERE/index.html" ];           then APP="$HERE";           VERIFY="$HERE/../zrodla/aedverify"
else echo "index.html not found next to this script (expected ./aplikacja/index.html)"; exit 1; fi
[ -d "$VERIFY" ] || VERIFY="$APP/aedverify"

API_UPSTREAM="${API_UPSTREAM:-https://20.215.200.98:7231}"
WEB=/var/www/punktzycia
export DEBIAN_FRONTEND=noninteractive

say() { printf '\n==> %s\n' "$*"; }

say "Detecting public IP / domain"
detect_ip() {
  curl -fsS -m 3 -H Metadata:true \
    "http://169.254.169.254/metadata/instance/network/interface/0/ipv4/ipAddress/0/publicIpAddress?api-version=2021-02-01&format=text" 2>/dev/null ||
  curl -4fsS -m 5 https://api.ipify.org 2>/dev/null ||
  curl -4fsS -m 5 https://ifconfig.me 2>/dev/null || true
}
PUBLIC_IP="${PUBLIC_IP:-$(detect_ip)}"
if [ -z "${DOMAIN:-}" ]; then
  [[ "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Cannot detect public IP. Run: PUBLIC_IP=<ip> bash start.sh"; exit 1; }
  DOMAIN="${PUBLIC_IP//./-}.sslip.io"
fi
echo "Domain: $DOMAIN"

say "Checking ports 80/443"
if ss -ltnp | grep -E ':(80|443)\s' | grep -vq caddy; then
  echo "Ports 80/443 are used by another program:"; ss -ltnp | grep -E ':(80|443)\s'; exit 1
fi

say "Installing Caddy"
if ! command -v caddy >/dev/null; then
  apt-get update -y
  if ! apt-get install -y caddy; then
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gpg
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -y && apt-get install -y caddy
  fi
fi

say "Publishing GUI to $WEB"
mkdir -p "$WEB"
cp "$APP"/index.html "$APP"/sw.js "$APP"/manifest.webmanifest "$APP"/icon-*.png "$WEB"/
for f in weryfikuj.html panel.html foto.js; do
  [ -f "$VERIFY/static/$f" ] && cp "$VERIFY/static/$f" "$WEB"/
done
chmod -R a+rX "$WEB"; chown -R caddy:caddy "$WEB" 2>/dev/null || true

HAVE_VERIFY=0
if [ -d "$VERIFY" ] && [ -f "$VERIFY/__main__.py" ]; then
  HAVE_VERIFY=1
  say "Installing verification backend (aedverify)"
  command -v python3 >/dev/null || apt-get install -y python3
  python3 -c "import PIL" 2>/dev/null || apt-get install -y python3-pil || true
  API=/opt/punktzycia-api; DATA=/var/lib/punktzycia
  id punktzycia >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin punktzycia
  mkdir -p "$API" "$DATA/zdjecia" /etc/punktzycia
  rm -rf "$API/aedverify"; cp -r "$VERIFY" "$API/aedverify"
  find "$API/aedverify" -name __pycache__ -prune -exec rm -rf {} + ; chmod -R a+rX "$API/aedverify"
  [ -s /etc/punktzycia/admin_token ] || head -c 18 /dev/urandom | base64 | tr -d '/+=' > /etc/punktzycia/admin_token
  touch /etc/punktzycia/env
  [ -f "$APP/model.env" ] && tr -d '\r' < "$APP/model.env" | grep -E '^(AED_MODEL_URL|AED_MODEL_KEY|AED_MODEL_CLASSES)=' >> /etc/punktzycia/env || true
  sed -i '/^AED_ADMIN_TOKEN=/d' /etc/punktzycia/env
  echo "AED_ADMIN_TOKEN=$(cat /etc/punktzycia/admin_token)" >> /etc/punktzycia/env
  chmod 600 /etc/punktzycia/admin_token /etc/punktzycia/env
  chown -R punktzycia:punktzycia "$DATA"
  cat > /etc/systemd/system/punktzycia-api.service <<UNIT
[Unit]
Description=Punkt Zycia - AED verification
After=network.target
[Service]
User=punktzycia
WorkingDirectory=$API
EnvironmentFile=/etc/punktzycia/env
ExecStart=/usr/bin/python3 -u -m aedverify serve --db $DATA/aedverify.db --foto $DATA/zdjecia --host 127.0.0.1 --port 8090
Restart=always
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$DATA
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable punktzycia-api
  systemctl restart punktzycia-api
fi

say "Configuring Caddy (HTTPS + /api4life proxy to $API_UPSTREAM)"
mkdir -p /etc/caddy/sites
{
cat <<CADDY
$DOMAIN {
	root * $WEB
	encode zstd gzip
	header Cache-Control "no-cache"
	header /api/* Access-Control-Allow-Origin "*"
	header /api4life/* Access-Control-Allow-Origin "*"
	handle_path /api4life/* {
		reverse_proxy $API_UPSTREAM {
			header_up Host localhost
			transport http {
				tls_insecure_skip_verify
			}
		}
	}
CADDY
if [ "$HAVE_VERIFY" -eq 1 ]; then cat <<CADDY
	handle /api/* {
		request_body {
			max_size 12MB
		}
		reverse_proxy 127.0.0.1:8090
	}
CADDY
fi
cat <<CADDY
	redir / /start
	rewrite /start /index.html
	handle {
		file_server
	}
}
CADDY
} > /etc/caddy/sites/punktzycia.caddy
[ -f /etc/caddy/Caddyfile ] || : > /etc/caddy/Caddyfile
grep -q 'import sites/\*.caddy' /etc/caddy/Caddyfile || echo 'import sites/*.caddy' >> /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 80/tcp; ufw allow 443/tcp; fi
systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy

say "Smoke test"
sleep 5
if curl -fsS -m 15 "http://127.0.0.1:8090/api/aed/najblizsze?lat=52.23&lon=21.01&n=1" >/dev/null 2>&1; then echo "verification API: OK"; else
  [ "$HAVE_VERIFY" -eq 1 ] && { echo "verification API NOT responding:"; journalctl -u punktzycia-api -n 15 --no-pager; } || echo "verification backend not installed (aedverify not found) - skipped"; fi
if curl -sk -m 15 "https://127.0.0.1/api4life/api/aed/nearest?latitude=52.23&longitude=21.01" -H "Host: $DOMAIN" | grep -q latitude; then
  echo "AED4Life API via proxy: OK"; else echo "WARNING: AED4Life API not reachable via $API_UPSTREAM (the map will stay empty)"; fi

echo
echo "Done. Open on your phone:  https://$DOMAIN/start"
[ "$HAVE_VERIFY" -eq 1 ] && echo "Verification panel:        https://$DOMAIN/panel.html?token=$(cat /etc/punktzycia/admin_token)"
echo "If it does not open: allow inbound TCP 80 and 443 in the cloud firewall (Azure NSG)."
