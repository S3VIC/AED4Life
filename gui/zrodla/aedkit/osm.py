import csv
import io
import json
import re
from pathlib import Path

VEHICLE = re.compile(r"\b(samoch[oó]d|w[oó]z|karetk|pojazd|GBA|GCBA|SLRt|SLRR|ambulans)", re.I)
KEY = re.compile(r"\bklucz", re.I)
CODE = re.compile(r"\b(kod|szyfr)", re.I)
STAFF = re.compile(r"\b(recepcj|portier|ochron|obsług|pracownik|sekretariat)", re.I)
STREET_PREFIX = [
    (re.compile(r"^(aleja|aleje|al\.)\s+", re.I), "al."),
    (re.compile(r"^(plac|pl\.)\s+", re.I), "pl."),
    (re.compile(r"^(osiedle|os\.)\s+", re.I), "os."),
    (re.compile(r"^rondo\s+", re.I), "rondo"),
    (re.compile(r"^(ulica|ul\.)\s+", re.I), "ul."),
]
ACCESS = {"yes": "publiczny", "permissive": "publiczny", "public": "publiczny",
          "customers": "dla_klientow", "permit": "za_zgoda", "private": "prywatny",
          "no": "brak_dostepu", "employees": "prywatny", "staff": "prywatny"}
OPERATOR_TYPE = [
    (re.compile(r"\b(gmin|urz[aą]d|starostw|powiat|miast|marsza[łl]k|MOSiR|OSiR|GOK|MOK)", re.I), "jst"),
    (re.compile(r"\b(PSP|OSP|stra[żz]|policj|pogotow|ratownict|WOPR|GOPR|TOPR)", re.I), "sluzby_ratownicze"),
    (re.compile(r"\b(szko[łl]|przedszkol|uniwersytet|politechnik|akademi|liceum|zesp[oó][łl] szk)", re.I), "oswiata"),
    (re.compile(r"\b(szpital|przychodni|aptek|NZOZ|SPZOZ|klinik|medic)", re.I), "ochrona_zdrowia"),
    (re.compile(r"\b(PKP|PKS|lotnisk|metro|dworzec|MPK|ZTM|kolej|tramwaj|airport)", re.I), "transport"),
    (re.compile(r"\b(fundacj|stowarzysz|parafi|ko[śs]ci[oó][łl]|caritas)", re.I), "organizacja_pozarzadowa"),
    (re.compile(r"\b(bank|galeri|centrum handl|hotel|kino|sklep|biedronk|lidl|kaufland|auchan|carrefour|ikea|żabk|zabk|orlen|shell|bp)", re.I), "handel_i_uslugi"),
]


def _first(row: dict, *keys) -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, "") and str(v).strip():
            return str(v).strip()
    return ""


def load_rows(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() in (".geojson", ".json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for f in data.get("features", []):
            p = dict(f.get("properties") or {})
            g = f.get("geometry") or {}
            if g.get("type") == "Point":
                p.setdefault("lon", g["coordinates"][0]); p.setdefault("lat", g["coordinates"][1])
            if "id" in f and not p.get("@id"):
                p["@id"] = f["id"]
            rows.append(p)
        return rows
    return read_csv_text(path.read_bytes().decode("utf-8-sig", errors="replace"))


def read_csv_text(text: str) -> list[dict]:
    text = text.lstrip("\ufeff")
    header = text.split("\n", 1)[0]
    delim = max(",;\t|", key=header.count)
    rows = list(csv.DictReader(io.StringIO(text, newline=""), delimiter=delim))
    return [{(k or "").strip().lstrip("\ufeff"): v for k, v in row.items()} for row in rows if any((v or "").strip() for v in row.values() if isinstance(v, str))]


def split_street(street: str) -> tuple[str, str]:
    for rx, cecha in STREET_PREFIX:
        if rx.match(street):
            return cecha, rx.sub("", street).strip()
    return "ul.", street


def osm_id(row: dict) -> str:
    v = _first(row, "@id", "osm_id", "id", "@osm_id", "node_id")
    t = _first(row, "@type", "osm_type", "type")
    if not v:
        return ""
    if "/" in v:
        return v
    v = re.sub(r"\D", "", v) or v
    return f"{(t or 'node').lower()}/{v}"


def to_schema(row: dict) -> dict:
    loc_text = " ".join(filter(None, [
        _first(row, "defibrillator:location:pl"), _first(row, "defibrillator:location"),
        _first(row, "description:pl"), _first(row, "description"), _first(row, "note")]))
    name = _first(row, "name", "name:pl", "operator")
    out: dict = {
        "nazwa_obiektu": _first(row, "name", "name:pl"),
        "lat": _first(row, "lat", "latitude", "@lat", "y", "Y"),
        "lon": _first(row, "lon", "lng", "longitude", "@lon", "x", "X"),
        "miejscowosc": _first(row, "addr:city", "addr:place", "is_in:city"),
        "kod_pocztowy": _first(row, "addr:postcode"),
        "numer_budynku": _first(row, "addr:housenumber"),
        "poziom_pietro": _first(row, "level", "level:ref").split(";")[0],
        "opis_dojscia": _first(row, "defibrillator:location:pl", "defibrillator:location", "description:pl", "description")[:250],
        "opis_dojscia_en": _first(row, "defibrillator:location:en", "description:en")[:250],
        "zdjecie_url": _first(row, "image", "wikimedia_commons:url"),
        "godziny_dostepu": _first(row, "opening_hours"),
        "producent": _first(row, "manufacturer"),
        "model": _first(row, "model"),
        "dysponent_nazwa": _first(row, "operator", "owner"),
        "kontakt_telefon": _first(row, "phone", "contact:phone", "emergency:phone"),
        "kontakt_email": _first(row, "email", "contact:email"),
        "data_weryfikacji": _first(row, "check_date", "survey:date", "check_date:defibrillator"),
        "zrodlo": "osm",
        "data_dodania_w_zrodle": _first(row, "@timestamp", "timestamp", "start_date"),
        "id_zrodla": osm_id(row),
        "status_sprawnosci": "niesprawny" if _first(row, "disused", "disused:emergency") else "nieznany",
    }

    street = _first(row, "addr:street")
    if street:
        out["cecha_adresu"], out["ulica"] = split_street(street)
    elif out["numer_budynku"]:
        out["cecha_adresu"] = "brak"

    access = _first(row, "access").lower().split(";")[0]
    out["kategoria_dostepu"] = ACCESS.get(access, "nieznany")

    indoor = _first(row, "indoor").lower()
    location = _first(row, "location").lower()
    if location == "vehicle" or (not indoor and VEHICLE.search(loc_text + " " + name)):
        out["umiejscowienie"], out["stacjonarny"] = "w_pojezdzie", "false"
    elif indoor in ("yes", "room", "area", "corridor"):
        out["umiejscowienie"], out["stacjonarny"] = "w_budynku", "true"
    elif indoor == "no" or location in ("outdoor", "outside", "wall"):
        out["umiejscowienie"], out["stacjonarny"] = "na_zewnatrz_budynku", "true"
    else:
        out["umiejscowienie"], out["stacjonarny"] = "inne", "true"

    oh = out["godziny_dostepu"]
    out["calodobowo"] = "true" if oh.replace(" ", "") in ("24/7", "Mo-Su00:00-24:00") else ("false" if oh else "")
    if out["calodobowo"] == "true":
        out["godziny_dostepu"] = ""

    if CODE.search(loc_text):
        out["sposob_otwarcia"] = "kod_od_dyspozytora"
    elif KEY.search(loc_text):
        out["sposob_otwarcia"] = "klucz_u_pracownika"
    elif STAFF.search(loc_text) and out["umiejscowienie"] == "w_budynku":
        out["sposob_otwarcia"] = "pomoc_pracownika"
    else:
        out["sposob_otwarcia"] = "nieznany"

    op = out["dysponent_nazwa"] + " " + out["nazwa_obiektu"]
    out["dysponent_typ"] = next((t for rx, t in OPERATOR_TYPE if rx.search(op)), "")
    out["sposob_weryfikacji"] = "zgloszenie_spolecznosci"
    return out
