import csv
import io
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import HTTP
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from . import engine, exif

MAX_BODY = 12 * 1024 * 1024
SCHEMA = """
create table if not exists aed(id text primary key, lat real, lon real, nazwa text, zrodlo text,
  status text default 'niezweryfikowany', liczba_potwierdzen int default 0, data_weryfikacji text,
  sposob_weryfikacji text, proponowana_lat real, proponowana_lon real, dane text);
create table if not exists weryfikacje(id text primary key, aed_id text, ts text, urzadzenie text, typ text,
  lat real, lon real, accuracy real, werdykt text, wynik int, odleglosc_m real, hash text,
  proponowana_lat real, proponowana_lon real, raport text, plik text, decyzja_admin text);
create index if not exists w_aed on weryfikacje(aed_id);
"""


class Store:
    def __init__(self, path, foto_dir):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.foto = foto_dir
        os.makedirs(foto_dir, exist_ok=True)
        self.lock = threading.Lock()

    def import_rows(self, rows, zrodlo):
        n = 0
        with self.lock, self.db:
            for r in rows:
                i = r.get("id_aed") or r.get("id")
                try:
                    lat, lon = float(r["lat"]), float(r["lon"])
                except (KeyError, TypeError, ValueError):
                    continue
                self.db.execute("insert into aed(id,lat,lon,nazwa,zrodlo,dane) values(?,?,?,?,?,?) on conflict(id) do update set lat=excluded.lat,lon=excluded.lon,nazwa=excluded.nazwa,zrodlo=excluded.zrodlo,dane=excluded.dane",
                                (i, lat, lon, r.get("nazwa_obiektu") or r.get("nazwa") or "AED", zrodlo, json.dumps(r, ensure_ascii=False)))
                n += 1
        return n

    def aed(self, i):
        r = self.db.execute("select * from aed where id=?", (i,)).fetchone()
        return dict(r) if r else None

    def near(self, lat, lon, n=10, tylko_niezw=False):
        dl = 0.03
        q = "select id,lat,lon,nazwa,status,liczba_potwierdzen from aed where lat between ? and ? and lon between ? and ?"
        if tylko_niezw:
            q += " and status not in ('potwierdzony')"
        rows = [dict(r) for r in self.db.execute(q, (lat - dl, lat + dl, lon - dl * 1.6, lon + dl * 1.6))]
        for r in rows:
            r["odleglosc_m"] = round(engine.haversine(lat, lon, r["lat"], r["lon"]))
        return sorted(rows, key=lambda r: r["odleglosc_m"])[:n]

    def hashes(self, aed_id):
        return [r[0] for r in self.db.execute("select hash from weryfikacje where hash!=''")]

    def recompute(self, aed_id):
        wsz = [dict(r) for r in self.db.execute("select * from weryfikacje where aed_id=?", (aed_id,))]
        ws = [w for w in wsz if w["typ"] != "zgloszenie" or w["decyzja_admin"]]
        if not ws and wsz:
            self.db.execute("update aed set status='zgloszony' where id=?", (aed_id,))
            return {"status": "zgloszony", "liczba_potwierdzen": 0}
        for w in ws:
            w["proponowana_pozycja"] = (w["proponowana_lat"], w["proponowana_lon"]) if w["proponowana_lat"] else None
        s = engine.status(ws)
        p = s.get("proponowana_pozycja") or (None, None)
        self.db.execute("update aed set status=?,liczba_potwierdzen=?,data_weryfikacji=coalesce(?,data_weryfikacji),sposob_weryfikacji=coalesce(?,sposob_weryfikacji),proponowana_lat=?,proponowana_lon=? where id=?",
                        (s["status"], s.get("liczba_potwierdzen", 0), s.get("data_weryfikacji"), s.get("sposob"), p[0], p[1], aed_id))
        return s

    def add(self, aed_id, foto, gps, urzadzenie, typ):
        a = self.aed(aed_id)
        if not a:
            return None, None
        with self.lock:
            w = engine.verify(foto, gps, a, znane_hashe=self.hashes(aed_id), typ="jest" if typ == "zgloszenie" else typ)
            wid = uuid.uuid4().hex
            plik = ""
            if foto and w.werdykt != engine.ODRZUCONY:
                plik = wid + ".jpg"
                with open(os.path.join(self.foto, plik), "wb") as f:
                    f.write(exif.strip(foto))
            pp = w.proponowana_pozycja or (None, None)
            ts = engine._utc(gps.get("ts")) or datetime.now(timezone.utc)
            with self.db:
                self.db.execute("insert into weryfikacje values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (wid, aed_id, ts.isoformat(), urzadzenie, typ, gps.get("lat"), gps.get("lon"), gps.get("accuracy"),
                                 w.werdykt, w.wynik, w.odleglosc_m, w.hash, pp[0], pp[1], json.dumps(w.dict(), ensure_ascii=False), plik, None))
                s = self.recompute(aed_id)
        return wid, {**w.dict(), "status_aed": s}

    def add_new(self, f, foto, gps, urzadzenie):
        try:
            lat, lon = float(f.get("aed_lat") or gps["lat"]), float(f.get("aed_lon") or gps["lon"])
        except (TypeError, ValueError, KeyError):
            return None, {"blad": "brak położenia AED"}
        nazwa = (f.get("nazwa") or "").strip()[:120]
        if not nazwa or not foto:
            return None, {"blad": "wymagane: nazwa i zdjęcie AED"}
        aid = "PL-AED-Z" + uuid.uuid4().hex[:8].upper()
        dane = {k: (f.get(k) or "")[:300] for k in ("nazwa", "miejscowosc", "kod_pocztowy", "ulica", "numer_budynku", "opis_dojscia", "godziny_dostepu", "kategoria_dostepu")}
        with self.lock, self.db:
            self.db.execute("insert into aed(id,lat,lon,nazwa,zrodlo,status,dane) values(?,?,?,?,?,?,?)",
                            (aid, lat, lon, nazwa, "zgloszenie_mieszkanca", "zgloszony", json.dumps(dane, ensure_ascii=False)))
        wid, res = self.add(aid, foto, gps, urzadzenie, "zgloszenie")
        return aid, {"id_aed": aid, **res}

    def decide(self, wid, decyzja):
        r = self.db.execute("select aed_id,proponowana_lat,proponowana_lon from weryfikacje where id=?", (wid,)).fetchone()
        if not r:
            return None
        with self.lock, self.db:
            if decyzja == "korekta" and r["proponowana_lat"]:
                self.db.execute("update aed set lat=?,lon=? where id=?", (r["proponowana_lat"], r["proponowana_lon"], r["aed_id"]))
                decyzja = "potwierdzony"
            self.db.execute("update weryfikacje set decyzja_admin=? where id=?", (decyzja, wid))
            return self.recompute(r["aed_id"])

    def queue(self):
        q = "select w.id,w.typ,w.aed_id,w.ts,w.werdykt,w.wynik,w.odleglosc_m,w.lat,w.lon,w.accuracy,w.plik,w.raport,a.nazwa,a.lat aed_lat,a.lon aed_lon from weryfikacje w join aed a on a.id=w.aed_id where w.decyzja_admin is null and (w.werdykt in (?,?,?) or w.typ='zgloszenie') order by w.ts desc limit 200"
        out = []
        for r in self.db.execute(q, (engine.RECZNIE, engine.KOREKTA, engine.BRAK_AED)):
            d = dict(r)
            d["raport"] = json.loads(d["raport"])
            out.append(d)
        return out

    def export(self):
        cols = ["id", "lat", "lon", "nazwa", "zrodlo", "status", "liczba_potwierdzen", "data_weryfikacji", "sposob_weryfikacji"]
        return cols, [[r[c] for c in cols] for r in self.db.execute("select * from aed order by id")]


def make_handler(store, static_dir, admin_token):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=static_dir, **k)

        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _admin(self):
            if admin_token and self.headers.get("Authorization") != f"Bearer {admin_token}":
                self._json({"blad": "brak uprawnień"}, 401)
                return False
            return True

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            p = u.path
            if p == "/api/aed/najblizsze":
                try:
                    return self._json(store.near(float(q["lat"]), float(q["lon"]), int(q.get("n", 10)), q.get("niezweryfikowane") == "1"))
                except (KeyError, ValueError):
                    return self._json({"blad": "podaj lat i lon"}, 400)
            if p.startswith("/api/aed/"):
                a = store.aed(p.rsplit("/", 1)[1])
                return self._json(a) if a else self._json({"blad": "nie ma"}, 404)
            if p == "/api/kolejka":
                return self._admin() and self._json(store.queue())
            if p.startswith("/api/zdjecie/"):
                if not self._admin():
                    return
                f = os.path.join(store.foto, os.path.basename(p))
                if not os.path.isfile(f):
                    return self._json({"blad": "nie ma"}, 404)
                b = open(f, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                return self.wfile.write(b)
            if p in ("/api/eksport.csv", "/api/eksport.json"):
                cols, rows = store.export()
                if p.endswith(".json"):
                    return self._json([dict(zip(cols, r)) for r in rows])
                s = io.StringIO()
                w = csv.writer(s)
                w.writerow(cols)
                w.writerows(rows)
                b = s.getvalue().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                return self.wfile.write(b)
            return super().do_GET()

        def do_POST(self):
            try:
                return self._post()
            except Exception as e:
                import traceback
                traceback.print_exc()
                try:
                    return self._json({"blad": "błąd serwera: " + type(e).__name__}, 500)
                except Exception:
                    pass

        def _post(self):
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._json({"blad": "plik za duży (max 12 MB)"}, 413)
            body = self.rfile.read(n)
            if u.path in ("/api/weryfikacje", "/api/zgloszenia"):
                ct = self.headers.get("Content-Type", "")
                msg = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + ct.encode() + b"\r\n\r\n" + body)
                f, foto = {}, b""
                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if name == "zdjecie":
                        foto = part.get_payload(decode=True) or b""
                    elif name:
                        f[name] = part.get_content().strip()
                try:
                    gps = {"lat": float(f["lat"]), "lon": float(f["lon"]), "accuracy": float(f.get("accuracy") or 999), "ts": f.get("ts")}
                except (KeyError, ValueError):
                    gps = {"lat": None, "lon": None}
                if u.path == "/api/zgloszenia":
                    aid, res = store.add_new(f, foto, gps, f.get("urzadzenie", self.client_address[0]))
                    return self._json(res, 201 if aid else 400)
                typ = f.get("typ", "jest")
                if typ == "jest" and not foto:
                    return self._json({"blad": "brak zdjęcia"}, 400)
                wid, res = store.add(f.get("aed_id", ""), foto, gps, f.get("urzadzenie", self.client_address[0]), typ)
                if not wid:
                    return self._json({"blad": "nieznany AED"}, 404)
                return self._json({"id": wid, **res}, 201)
            if u.path.startswith("/api/kolejka/"):
                if not self._admin():
                    return
                try:
                    d = json.loads(body or b"{}").get("decyzja")
                except ValueError:
                    d = None
                if d not in ("potwierdzony", "korekta", "odrzucony", "prawdopodobnie_brak"):
                    return self._json({"blad": "decyzja: potwierdzony|korekta|odrzucony|prawdopodobnie_brak"}, 400)
                s = store.decide(u.path.rsplit("/", 1)[1], d)
                return self._json(s) if s else self._json({"blad": "nie ma"}, 404)
            self._json({"blad": "nie ma"}, 404)

    return H


def serve(db, foto_dir, static_dir, host="127.0.0.1", port=8090, admin_token=None):
    store = Store(db, foto_dir)
    srv = ThreadingHTTPServer((host, port), make_handler(store, static_dir, admin_token))
    print(f"aedverify: http://{host}:{port}/weryfikuj.html  (panel: /panel.html)")
    srv.serve_forever()
