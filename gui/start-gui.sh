#!/usr/bin/env bash
# Starts the Punkt Zycia GUI (gui/aplikacja) on a local web server. No arguments needed.
# Picks the first free port in 8000-8020 and opens the browser if a desktop is available.
# The GUI fetches AED data from the AED4Life WebAPI by itself.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/aplikacja" && pwd)"
[ -f "$ROOT/index.html" ] || { echo "index.html not found in $ROOT" >&2; exit 1; }

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ] && ! command -v node >/dev/null 2>&1; then
    echo "Python 3 (or Node.js) is required to serve the GUI. On Debian/Ubuntu:  sudo apt-get install -y python3" >&2
    exit 1
fi

PORT=""
for p in $(seq 8000 8020); do
    if ! (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null; then PORT="$p"; break; fi
done
[ -n "$PORT" ] || { echo "Ports 8000-8020 are all in use." >&2; exit 1; }

URL="http://localhost:$PORT/"
printf '\n  Punkt Zycia is running at: %s\n  Press Ctrl+C to stop.\n\n' "$URL"
if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 & fi
if [ "$(uname)" = "Darwin" ]; then open "$URL" >/dev/null 2>&1 & fi

if [ -n "$PY" ]; then
    exec "$PY" - "$ROOT" "$PORT" <<'PYEOF'
import http.server, sys, functools
root, port = sys.argv[1], int(sys.argv[2])
class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.webmanifest': 'application/manifest+json', '.js': 'text/javascript'}
    def translate_path(self, path):
        if path.split('?')[0] in ('/', '/start'):
            path = '/index.html'
        return super().translate_path(path)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()
http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=root)).serve_forever()
PYEOF
else
    exec node - "$ROOT" "$PORT" <<'JSEOF'
const http = require('http'), fs = require('fs'), path = require('path');
const [root, port] = [process.argv[2], +process.argv[3]];
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.json':'application/json','.webmanifest':'application/manifest+json','.ico':'image/x-icon'};
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/' || p === '/start') p = '/index.html';
  const f = path.normalize(path.join(root, p));
  if (!f.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404).end(); return; }
    res.writeHead(200, {'Content-Type': types[path.extname(f).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store'}).end(d);
  });
}).listen(port, '127.0.0.1');
JSEOF
fi
