import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from statistics import median

from . import exif as _exif
from . import vision

POTWIERDZONY = "potwierdzony_auto"
KOREKTA = "korekta_lokalizacji"
RECZNIE = "do_sprawdzenia"
ODRZUCONY = "odrzucony"
BRAK_AED = "brak_aed"

MAX_ACC = 100
TOL_MIN, TOL_MAX = 25, 75
KOREKTA_MAX = 150
EXIF_GPS_MAX = 100
EXIF_CZAS_MAX = timedelta(hours=24)
SWIEZOSC = timedelta(minutes=15)
DUP_BITS = 6
PROG_WNIOSKU = 50


def haversine(a, b, c, d):
    r = 6371008.8
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


@dataclass
class Wynik:
    werdykt: str
    wynik: int
    odleglosc_m: float | None
    tolerancja_m: float | None
    powody: list = field(default_factory=list)
    flagi: list = field(default_factory=list)
    exif: dict = field(default_factory=dict)
    ai: dict = field(default_factory=dict)
    hash: str = ""
    proponowana_pozycja: tuple | None = None

    def dict(self):
        d = asdict(self)
        for k in ("czas", "gps_czas"):
            if d["exif"].get(k):
                d["exif"][k] = d["exif"][k].isoformat()
        return d


def _utc(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, timezone.utc)
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def verify(zdjecie, gps, aed, teraz=None, znane_hashe=(), typ="jest"):
    teraz = _utc(teraz) or datetime.now(timezone.utc)
    pow, flagi, pkt = [], [], 50
    lat, lon, acc = gps.get("lat"), gps.get("lon"), gps.get("accuracy")
    ts = _utc(gps.get("ts"))
    h = vision.phash(zdjecie) if zdjecie else ""
    ex = _exif.read(zdjecie) if zdjecie else {}
    ex_out = {k: ex.get(k) for k in ("lat", "lon", "czas", "model", "jest_exif")}

    def koniec(w, p, d=None, tol=None, poz=None, ai=None):
        p = max(0, min(100, round(p)))
        if p < PROG_WNIOSKU and w != ODRZUCONY:
            pow.append(f"wynik {p}/100 poniżej progu {PROG_WNIOSKU} – zgłoszenie odrzucone")
            flagi.append("ponizej_progu")
            w, poz = ODRZUCONY, None
        return Wynik(w, p, None if d is None else round(d, 1),
                     None if tol is None else round(tol, 1), pow, flagi, ex_out, ai or {}, h, poz)

    if lat is None or lon is None:
        pow.append("brak lokalizacji z urządzenia")
        return koniec(RECZNIE, 0)
    if acc is None or acc > MAX_ACC:
        pow.append(f"zbyt niska dokładność GPS ({acc} m)")
        flagi.append("slaby_gps")
        pkt -= 25

    if ts:
        if ts - teraz > timedelta(minutes=2):
            pow.append("czas zdjęcia z przyszłości")
            flagi.append("czas")
            return koniec(ODRZUCONY, 0)
        if teraz - ts > SWIEZOSC:
            pow.append("lokalizacja nieświeża (>15 min)")
            flagi.append("czas")
            pkt -= 20

    for k in znane_hashe:
        if h and vision.hash_distance(h, k) <= DUP_BITS:
            pow.append("to samo zdjęcie było już wysłane")
            flagi.append("duplikat")
            return koniec(ODRZUCONY, 0)

    d = haversine(lat, lon, aed["lat"], aed["lon"])
    tol = min(TOL_MAX, max(TOL_MIN, 1.5 * (acc or MAX_ACC)))

    if ex.get("lat") is not None:
        de = haversine(lat, lon, ex["lat"], ex["lon"])
        ex_out["odleglosc_od_gps_m"] = round(de, 1)
        if de > EXIF_GPS_MAX:
            pow.append(f"GPS w zdjęciu różni się o {de:.0f} m od lokalizacji urządzenia")
            flagi.append("exif_gps")
            pkt -= 35
        else:
            pow.append("GPS w zdjęciu zgodny z urządzeniem")
            pkt += 15
    elif ex.get("jest_exif"):
        pow.append("zdjęcie bez GPS w EXIF (typowe dla przeglądarek)")
    if ex.get("czas") and ts:
        dc = abs(ex["czas"] - ts.replace(tzinfo=None))
        if dc > EXIF_CZAS_MAX + timedelta(hours=14):
            pow.append("zdjęcie zrobione dawno temu (wg EXIF)")
            flagi.append("exif_czas")
            pkt -= 30

    ai, ai_info = vision.aed_score(zdjecie) if zdjecie else (None, {})
    ai_out = {"pewnosc": ai, **ai_info}
    if typ == "jest" and ai is not None:
        if ai >= 0.6:
            pow.append(f"{'model AI wykrył AED' if ai_info.get('metoda') == 'model_yolo' else 'na zdjęciu wykryto oznaczenie AED'} ({ai:.0%})")
            pkt += 15
        elif ai < 0.15:
            pow.append("model AI nie wykrył AED na zdjęciu" if ai_info.get("metoda") == "model_yolo" else "nie wykryto oznaczenia AED na zdjęciu")
            flagi.append("ai_brak_aed")
            pkt -= 20

    if typ == "nie_ma":
        if d <= tol:
            pow.append(f"zgłoszenie braku AED z miejsca ({d:.0f} m)")
            return koniec(BRAK_AED, pkt + 20, d, tol, ai=ai_out)
        pow.append(f"zgłaszający jest {d:.0f} m od AED")
        return koniec(RECZNIE, pkt - 30, d, tol, ai=ai_out)

    twarde = {"exif_gps", "exif_czas", "duplikat", "czas", "slaby_gps"}
    if d <= tol:
        pow.append(f"zgodność położenia: {d:.0f} m (tolerancja {tol:.0f} m)")
        pkt += 25
        w = POTWIERDZONY if pkt >= 70 and not twarde & set(flagi) else RECZNIE
        return koniec(w, pkt, d, tol, ai=ai_out)
    if d <= KOREKTA_MAX:
        pow.append(f"AED {d:.0f} m od pozycji w bazie – propozycja korekty")
        w = KOREKTA if pkt >= 50 and not twarde & set(flagi) else RECZNIE
        return koniec(w, pkt, d, tol, (round(lat, 6), round(lon, 6)), ai_out)
    pow.append(f"zdjęcie zrobione {d:.0f} m od AED z bazy")
    flagi.append("daleko")
    return koniec(ODRZUCONY if d > 1000 else RECZNIE, pkt - 40, d, tol, ai=ai_out)


def status(weryfikacje, teraz=None, waznosc_dni=365, ludzie=2):
    teraz = _utc(teraz) or datetime.now(timezone.utc)
    swieze = [w for w in weryfikacje if teraz - _utc(w["ts"]) <= timedelta(days=waznosc_dni)]
    if not swieze:
        return {"status": "wygasly" if weryfikacje else "niezweryfikowany", "liczba_potwierdzen": 0}
    reczne = sorted((w for w in swieze if w.get("decyzja_admin")), key=lambda w: _utc(w["ts"]))
    if reczne:
        ost = reczne[-1]
        return {"status": ost["decyzja_admin"], "liczba_potwierdzen": 1, "data_weryfikacji": _utc(ost["ts"]).date().isoformat(), "sposob": "recznie"}

    def urz(werdykt):
        return {w["urzadzenie"]: w for w in swieze if w["werdykt"] == werdykt}

    ok, kor, brak = urz(POTWIERDZONY), urz(KOREKTA), urz(BRAK_AED)
    ost_ok = max((_utc(w["ts"]) for w in ok.values()), default=None)
    ost_brak = max((_utc(w["ts"]) for w in brak.values()), default=None)
    if len(brak) >= ludzie and (ost_ok is None or ost_brak > ost_ok):
        return {"status": "prawdopodobnie_brak", "liczba_potwierdzen": 0, "liczba_zgloszen_braku": len(brak)}
    if len(kor) >= ludzie:
        pts = [w["proponowana_pozycja"] for w in kor.values()]
        m = (median(p[0] for p in pts), median(p[1] for p in pts))
        if all(haversine(*p, *m) <= 40 for p in pts):
            return {"status": "do_korekty", "proponowana_pozycja": [round(m[0], 6), round(m[1], 6)], "liczba_potwierdzen": len(kor)}
    if len(ok) >= ludzie:
        return {"status": "potwierdzony", "liczba_potwierdzen": len(ok), "data_weryfikacji": ost_ok.date().isoformat(), "sposob": "foto_gps"}
    if ok:
        return {"status": "wstepnie_potwierdzony", "liczba_potwierdzen": 1, "data_weryfikacji": ost_ok.date().isoformat(), "sposob": "foto_gps"}
    if any(w["werdykt"] in (RECZNIE, KOREKTA, BRAK_AED) for w in swieze):
        return {"status": "do_sprawdzenia", "liczba_potwierdzen": 0}
    return {"status": "niezweryfikowany", "liczba_potwierdzen": 0}
