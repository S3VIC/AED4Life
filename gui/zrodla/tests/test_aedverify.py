import io
import json
import threading
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from aedverify import engine, exif, vision
from aedverify.server import Store, make_handler
from http.server import ThreadingHTTPServer

AED = {"lat": 52.406374, "lon": 16.925168}
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def jpg(color=(0, 150, 70), gps=None, when=None, seed=0):
    im = Image.new("RGB", (400, 300), color)
    import random
    rnd = random.Random(seed)
    for _ in range(40):
        x, y = rnd.randrange(360), rnd.randrange(260)
        c = (255, 255, 255) if rnd.random() < 0.5 else tuple(max(0, v - 90) for v in color)
        for dx in range(40):
            for dy in range(40):
                im.putpixel((x + dx, y + dy), c)
    ex = Image.Exif()
    ex[0x0110] = "TestPhone"
    if when:
        ex.get_ifd(0x8769)[0x9003] = when.strftime("%Y:%m:%d %H:%M:%S")
    if gps:
        def dms(v):
            v = abs(v)
            d = int(v); m = int((v - d) * 60); s = (v - d - m / 60) * 3600
            return (d, m, round(s, 4))
        g = ex.get_ifd(0x8825)
        g[1] = "N" if gps[0] >= 0 else "S"
        g[2] = dms(gps[0])
        g[3] = "E" if gps[1] >= 0 else "W"
        g[4] = dms(gps[1])
    b = io.BytesIO()
    im.save(b, "JPEG", exif=ex)
    return b.getvalue()


def g(dlat=0.0, acc=10, ts=NOW):
    return {"lat": AED["lat"] + dlat, "lon": AED["lon"], "accuracy": acc, "ts": ts.isoformat()}


def test_exif_read_and_strip():
    b = jpg(gps=(52.4, 16.9), when=datetime(2026, 11, 22, 13, 0))
    e = exif.read(b)
    assert e["jest_exif"] and abs(e["lat"] - 52.4) < 1e-4 and abs(e["lon"] - 16.9) < 1e-4
    assert e["czas"].hour == 13 and e["model"] == "TestPhone"
    s = exif.strip(b)
    assert exif.read(s)["lat"] is None and Image.open(io.BytesIO(s)).size == (400, 300)


def test_ai_heuristic_green_vs_grey():
    assert vision.aed_score(jpg())[0] >= 0.6
    assert vision.aed_score(jpg(color=(120, 120, 120)))[0] < 0.15


def test_confirm_close():
    w = engine.verify(jpg(), g(0.0001), AED, NOW)
    assert w.werdykt == engine.POTWIERDZONY and w.wynik >= 70


def test_exif_gps_mismatch_goes_manual():
    w = engine.verify(jpg(gps=(52.2, 21.0)), g(), AED, NOW)
    assert w.werdykt == engine.RECZNIE and "exif_gps" in w.flagi


def test_correction_and_far():
    assert engine.verify(jpg(), g(0.0009), AED, NOW).werdykt == engine.KOREKTA
    assert engine.verify(jpg(), g(0.05), AED, NOW).werdykt == engine.ODRZUCONY


def test_stale_future_dup_weakgps_noai():
    assert engine.verify(jpg(), g(ts=NOW + timedelta(hours=1)), AED, NOW).werdykt == engine.ODRZUCONY
    assert engine.verify(jpg(), g(ts=NOW - timedelta(hours=2)), AED, NOW).werdykt == engine.RECZNIE
    b = jpg()
    assert engine.verify(b, g(), AED, NOW, znane_hashe=[vision.phash(b)]).werdykt == engine.ODRZUCONY
    assert engine.verify(jpg(), g(acc=300), AED, NOW).werdykt == engine.RECZNIE
    assert engine.verify(jpg(color=(120, 120, 120)), g(), AED, NOW).werdykt == engine.RECZNIE


def test_status_consensus():
    t = NOW.isoformat()
    ok = lambda d: {"ts": t, "urzadzenie": d, "werdykt": engine.POTWIERDZONY}
    assert engine.status([], NOW)["status"] == "niezweryfikowany"
    assert engine.status([ok("a")], NOW)["status"] == "wstepnie_potwierdzony"
    assert engine.status([ok("a"), ok("a")], NOW)["status"] == "wstepnie_potwierdzony"
    assert engine.status([ok("a"), ok("b")], NOW)["status"] == "potwierdzony"
    old = {"ts": (NOW - timedelta(days=400)).isoformat(), "urzadzenie": "a", "werdykt": engine.POTWIERDZONY}
    assert engine.status([old], NOW)["status"] == "wygasly"
    k = lambda d, p: {"ts": t, "urzadzenie": d, "werdykt": engine.KOREKTA, "proponowana_pozycja": p}
    s = engine.status([k("a", (52.4072, 16.9252)), k("b", (52.4073, 16.9251))], NOW)
    assert s["status"] == "do_korekty"
    br = {"ts": (NOW + timedelta(minutes=1)).isoformat(), "werdykt": engine.BRAK_AED}
    assert engine.status([ok("a"), {**br, "urzadzenie": "x"}, {**br, "urzadzenie": "y"}], NOW + timedelta(minutes=2))["status"] == "prawdopodobnie_brak"


def _post(url, fields, foto=None, headers=None):
    bnd = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    if foto:
        body += f'--{bnd}\r\nContent-Disposition: form-data; name="zdjecie"; filename="a.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + foto + b"\r\n"
    body += f"--{bnd}--\r\n".encode()
    r = urllib.request.Request(url, body, {"Content-Type": f"multipart/form-data; boundary={bnd}", **(headers or {})})
    return json.load(urllib.request.urlopen(r))


def test_server_end_to_end(tmp_path):
    st = Store(str(tmp_path / "d.db"), str(tmp_path / "f"))
    assert st.import_rows([{"id_aed": "PL-AED-1", **AED, "nazwa_obiektu": "Rektorat"}], "gov") == 1
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(st, str(tmp_path), "sekret"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}/api"
    try:
        near = json.load(urllib.request.urlopen(f"{base}/aed/najblizsze?lat={AED['lat']}&lon={AED['lon']}"))
        assert near[0]["status"] == "niezweryfikowany"
        now = datetime.now(timezone.utc).isoformat()
        f = {"aed_id": "PL-AED-1", "lat": AED["lat"], "lon": AED["lon"], "accuracy": 8, "ts": now}
        r1 = _post(f"{base}/weryfikacje", {**f, "urzadzenie": "a"}, jpg(gps=(AED["lat"], AED["lon"]), seed=1))
        assert r1["werdykt"] == engine.POTWIERDZONY and r1["status_aed"]["status"] == "wstepnie_potwierdzony"
        r2 = _post(f"{base}/weryfikacje", {**f, "urzadzenie": "b"}, jpg(seed=7, color=(0, 140, 60)))
        assert r2["status_aed"]["status"] == "potwierdzony"
        stored = list((tmp_path / "f").iterdir())
        assert stored and all(exif.read(p.read_bytes())["lat"] is None for p in stored)
        r3 = _post(f"{base}/weryfikacje", {**f, "lat": 52.2, "urzadzenie": "c"}, jpg(seed=13))
        assert r3["werdykt"] == engine.ODRZUCONY
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{base}/kolejka")
        nz = _post(f"{base}/zgloszenia", {"nazwa": "Sklep", "aed_lat": 52.41, "aed_lon": 16.93, "lat": 52.41, "lon": 16.93, "accuracy": 9, "ts": now, "urzadzenie": "z"}, jpg(seed=21))
        assert nz["id_aed"].startswith("PL-AED-Z") and nz["status_aed"]["status"] == "zgloszony"
        with pytest.raises(urllib.error.HTTPError):
            _post(f"{base}/zgloszenia", {"nazwa": "Bez zdjecia", "lat": 52.41, "lon": 16.93})
        q = json.load(urllib.request.urlopen(urllib.request.Request(f"{base}/kolejka", headers={"Authorization": "Bearer sekret"})))
        zq = [x for x in q if x["aed_id"] == nz["id_aed"]][0]
        dec = json.load(urllib.request.urlopen(urllib.request.Request(f"{base}/kolejka/{zq['id']}", json.dumps({"decyzja": "potwierdzony"}).encode(), {"Authorization": "Bearer sekret"})))
        assert dec["status"] == "potwierdzony"
        csv = urllib.request.urlopen(f"{base}/eksport.csv").read().decode()
        assert "PL-AED-1" in csv and "potwierdzony" in csv
    finally:
        srv.shutdown()


def test_model_api(monkeypatch):
    from http.server import BaseHTTPRequestHandler
    seen = {}

    class M(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            seen["q"] = self.path
            self.rfile.read(int(self.headers["Content-Length"]))
            b = json.dumps({"predictions": [{"class": "AED", "confidence": 0.93}, {"class": "door", "confidence": 0.99}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    s = ThreadingHTTPServer(("127.0.0.1", 0), M)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    monkeypatch.setattr(vision, "API_URL", f"http://127.0.0.1:{s.server_port}/aed-x/8")
    monkeypatch.setattr(vision, "API_KEY", "k123")
    try:
        sc, info = vision.aed_score(jpg(color=(120, 120, 120)))
        assert sc == 0.93 and info["metoda"] == "model_yolo" and "api_key=k123" in seen["q"]
        w = engine.verify(jpg(color=(120, 120, 120)), g(), AED, NOW)
        assert w.werdykt == engine.POTWIERDZONY and any("model AI" in p for p in w.powody)
        monkeypatch.setattr(vision, "API_URL", "http://127.0.0.1:9/x")
        sc, info = vision.aed_score(jpg())
        assert info["metoda"] == "heurystyka_znaku_ilcor" and "blad_modelu" in info
    finally:
        s.shutdown()
