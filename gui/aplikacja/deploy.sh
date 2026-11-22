#!/usr/bin/env bash
set -euo pipefail
IP="${1:-20.215.200.98}"
DOMAIN="${IP//./-}.sslip.io"
SRC="$(cd "$(dirname "$0")" && pwd)"
WEB=/var/www/punktzycia
if [ -f "$SRC/model.env" ]; then
  sudo mkdir -p /etc/punktzycia; sudo touch /etc/punktzycia/env
  for k in AED_MODEL_URL AED_MODEL_KEY AED_MODEL_CLASSES; do sudo sed -i "/^$k=/d" /etc/punktzycia/env; done
  tr -d '\r' < "$SRC/model.env" | grep -E '^(AED_MODEL_URL|AED_MODEL_KEY|AED_MODEL_CLASSES)=' | sudo tee -a /etc/punktzycia/env >/dev/null
  rm -f "$SRC/model.env"
  echo "Model AI: konfiguracja zapisana w /etc/punktzycia/env"
fi

if sudo ss -ltnp | grep -E ':(80|443)\s' | grep -vq caddy; then
  echo "Porty 80/443 zajmuje inny program:"; sudo ss -ltnp | grep -E ':(80|443)\s'; exit 1
fi

if ! command -v caddy >/dev/null; then
  sudo apt-get update -y
  if ! sudo apt-get install -y caddy; then
    sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gpg
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update -y && sudo apt-get install -y caddy
  fi
fi

# osobne repo git tylko dla tej strony (nie rusza innych repozytoriow na VM)
command -v git >/dev/null || sudo apt-get install -y git
cd "$SRC"
[ -d .git ] || { git init -q -b main 2>/dev/null || git init -q; git config user.name "Punkt Zycia deploy"; git config user.email "deploy@punktzycia.local"; }
git add -A && git commit -qm "Wdrozenie $(date '+%Y-%m-%d %H:%M')" && echo "Git: zapisano wersje w $SRC ($(git rev-parse --short HEAD))" || echo "Git: brak zmian"
cd - >/dev/null

sudo mkdir -p "$WEB"
sudo cp "$SRC"/index.html "$SRC"/sw.js "$SRC"/manifest.webmanifest "$SRC"/icon-*.png "$WEB"/
sudo cp "$SRC"/aedverify/static/weryfikuj.html "$SRC"/aedverify/static/panel.html "$SRC"/aedverify/static/foto.js "$WEB"/
sudo chmod -R a+rX "$WEB"; sudo chown -R caddy:caddy "$WEB" 2>/dev/null || true

API=/opt/punktzycia-api
DATA=/var/lib/punktzycia
python3 -c "import PIL" 2>/dev/null || sudo apt-get install -y python3-pil || true
id punktzycia >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin punktzycia
sudo mkdir -p "$API" "$DATA/zdjecia" /etc/punktzycia
sudo rm -rf "$API/aedverify" && sudo cp -r "$SRC/aedverify" "$API/" && sudo rm -rf "$API/aedverify/__pycache__" && sudo chmod -R a+rX "$API/aedverify"
[ -s /etc/punktzycia/admin_token ] || head -c 18 /dev/urandom | base64 | tr -d '/+=' | sudo tee /etc/punktzycia/admin_token >/dev/null
sudo touch /etc/punktzycia/env
sudo sed -i '/^AED_ADMIN_TOKEN=/d' /etc/punktzycia/env
echo "AED_ADMIN_TOKEN=$(sudo cat /etc/punktzycia/admin_token)" | sudo tee -a /etc/punktzycia/env >/dev/null
sudo chmod 600 /etc/punktzycia/admin_token /etc/punktzycia/env
sudo chown -R punktzycia:punktzycia "$DATA"
sudo tee /etc/systemd/system/punktzycia-api.service >/dev/null <<UNIT
[Unit]
Description=Punkt Zycia - weryfikacja AED
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
sudo systemctl daemon-reload
sudo systemctl enable punktzycia-api
sudo systemctl restart punktzycia-api

sudo mkdir -p /etc/caddy/sites
sudo tee /etc/caddy/sites/punktzycia.caddy >/dev/null <<CADDY
$DOMAIN {
	root * $WEB
	encode zstd gzip
	header Cache-Control "no-cache"
	header /api/* Access-Control-Allow-Origin "*"
	header /api4life/* Access-Control-Allow-Origin "*"
	handle_path /api4life/* {
		reverse_proxy https://127.0.0.1:7231 {
			header_up Host localhost
			transport http {
				tls_insecure_skip_verify
			}
		}
	}
	handle /api/* {
		request_body {
			max_size 12MB
		}
		reverse_proxy 127.0.0.1:8090
	}
	redir / /start
	rewrite /start /index.html
	handle {
		file_server
	}
}
CADDY
[ -f /etc/caddy/Caddyfile ] || echo "" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo grep -q 'import sites/\*.caddy' /etc/caddy/Caddyfile || echo 'import sites/*.caddy' | sudo tee -a /etc/caddy/Caddyfile >/dev/null
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then sudo ufw allow 80/tcp; sudo ufw allow 443/tcp; fi
sudo systemctl enable --now caddy
sudo systemctl reload caddy || sudo systemctl restart caddy
sleep 5
echo
curl -fsS "http://127.0.0.1:8090/api/aed/najblizsze?lat=52.23&lon=21.01&n=1" >/dev/null && echo "API weryfikacji: OK" || { echo "API weryfikacji NIE dziala:"; sudo journalctl -u punktzycia-api -n 20 --no-pager; }
echo "Gotowe. Otworz na telefonie:  https://$DOMAIN/start"
echo "Potwierdzanie AED:            https://$DOMAIN/weryfikuj.html"
echo "Panel weryfikacji:            https://$DOMAIN/panel.html?token=$(sudo cat /etc/punktzycia/admin_token)"
echo "Jesli sie nie otwiera: w Azure dodaj regule ruchu przychodzacego dla portow 80 i 443."
