import re
from dataclasses import dataclass, asdict
from datetime import date, datetime

from . import opening_hours as ohlib
from .schema import (FIELDS, MINIMUM, DICTS, DICT_FALLBACK, BOOL_FIELDS, DATE_FIELDS,
                     LAT_RANGE, LON_RANGE, LICENSES, CITY_CENTROIDS, STATUS_REKORDU)

BLAD, NAPRAWA, OSTRZEZENIE, INFO = "blad", "naprawa", "ostrzezenie", "info"

RULES = {
    1: (OSTRZEZENIE, "Brak źródła rekordu – przypisano „inne”"),
    2: (OSTRZEZENIE, "Brak współrzędnych"),
    3: (OSTRZEZENIE, "Współrzędne poza Polską lub nieliczbowe – rekord do sprawdzenia, nie usunięty"),
    4: (NAPRAWA, "Zduplikowany identyfikator – rekordy scalono"),
    5: (NAPRAWA, "Telefon po normalizacji nie ma 9 cyfr – usunięto"),
    6: (NAPRAWA, "Kod pocztowy w złym formacie – usunięto"),
    7: (NAPRAWA, "Wartość spoza słownika – zastąpiono wartością domyślną"),
    8: (INFO, "Niepoprawna data – traktowana jako brak danych"),
    9: (NAPRAWA, "Prywatny kontakt (RODO) – usunięto"),
    10: (OSTRZEZENIE, "calodobowo=true, ale godziny_dostepu są zawężone"),
    11: (OSTRZEZENIE, "Dostęp prywatny lub brak dostępu przy calodobowo=true"),
    12: (OSTRZEZENIE, "Elektrody lub bateria po terminie – AED do weryfikacji"),
    13: (OSTRZEZENIE, "Data przeglądu lub weryfikacji z przyszłości – usunięto"),
    14: (OSTRZEZENIE, "umiejscowienie=w_pojezdzie przy stacjonarny=true"),
    15: (OSTRZEZENIE, "Współrzędne mało precyzyjne (mniej niż 3 miejsca po przecinku lub środek miejscowości)"),
    16: (OSTRZEZENIE, "Kandydat na duplikat: inny AED bliżej niż 25 m"),
    17: (OSTRZEZENIE, "Brak data_weryfikacji lub starsza niż 12 miesięcy"),
    18: (NAPRAWA, "Wartość logiczna znormalizowana do true/false"),
    19: (NAPRAWA, "Niepoprawny lub nieszyfrowany adres zdjęcia"),
    20: (OSTRZEZENIE, "calodobowo=false i brak godzin dostępu"),
    21: (OSTRZEZENIE, "AED w budynku bez piętra lub opisu dojścia"),
    22: (OSTRZEZENIE, "Godziny dostępu nieczytelne dla systemu"),
    23: (OSTRZEZENIE, "Brak pola z poziomu minimum"),
    24: (NAPRAWA, "Poprawiono zapis współrzędnych"),
    25: (NAPRAWA, "Niepoprawne piętro – usunięto"),
    26: (NAPRAWA, "Godziny zamieniono na format opening_hours"),
    27: (NAPRAWA, "Data zamieniona na format rrrr-mm-dd"),
    28: (NAPRAWA, "Współrzędne uzupełnione z miejscowości (geokodowanie)"),
}

FREE_MAIL = {"gmail.com", "wp.pl", "o2.pl", "onet.pl", "onet.eu", "interia.pl", "interia.eu",
             "op.pl", "yahoo.com", "outlook.com", "hotmail.com", "poczta.fm", "tlen.pl",
             "gazeta.pl", "icloud.com", "proton.me", "protonmail.com", "vp.pl", "buziaczek.pl"}
FUNCTIONAL_LOCAL = re.compile(r"^(kontakt|biuro|sekretariat|info|recepcja|office|admin|szkola|urzad|"
                              r"gmina|ug|um|osp|psp|zarzad|obsluga|dyrekcja|portiernia)", re.I)
MOBILE = re.compile(r"^(45|5[0137]|6[069]|7[2389]|88)\d{7}$")
TRUE_VALS = {"true", "tak", "yes", "1", "t", "y", "prawda", "x"}
FALSE_VALS = {"false", "nie", "no", "0", "f", "n", "falsz", "fałsz"}
EMAIL = re.compile(r"^[^@\s]+@([^@\s]+\.[a-z]{2,})$", re.I)
DMS = re.compile(r"^\s*(-)?(\d{1,3})[°º\s]\s*(?:(\d{1,2})['′\s]\s*)?(?:(\d{1,2}(?:[.,]\d+)?)[\"″]?\s*)?([NSEW])?\s*$", re.I)
DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%y"]


@dataclass
class Issue:
    rule: int
    level: str
    field: str
    message: str
    value: str = ""

    def as_dict(self):
        return asdict(self)


def _blank(v) -> bool:
    return v is None or str(v).strip() == ""


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)


def _issue(issues, rule, field, value="", note="", level=None):
    lvl, msg = RULES[rule]
    issues.append(Issue(rule, level or lvl, field, msg + (f" ({note})" if note else ""), str(value)[:200]))


def parse_coord(v: str) -> tuple[float, bool, int]:
    """Return (value, repaired, decimals). Accepts 52.1, 52,1, -52.1, 52°24'23\"N."""
    s = str(v).strip()
    m = DMS.match(s) if ("°" in s or "º" in s or "'" in s or re.search(r"\d\s+\d", s)) else None
    if m:
        deg = int(m[2]) + int(m[3] or 0) / 60 + float((m[4] or "0").replace(",", ".")) / 3600
        return deg, True, 6
    t = s.replace(" ", "")
    repaired = False
    if t.count(",") == 1 and "." not in t:
        t, repaired = t.replace(",", "."), True
    val = float(t)
    if val < 0:
        val, repaired = -val, True
    dec = len(t.split(".")[1]) if "." in t else 0
    return val, repaired, dec


def parse_date(v: str) -> date | None:
    s = v.strip()[:19].replace("T", " ").split(" ")[0]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def in_poland(lat: float, lon: float) -> bool:
    return LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]


def validate_record(raw: dict, today: date, strict: bool = False) -> tuple[dict, list[Issue]]:
    """Normalize one record. Never drops an AED: problems lower quality or set status_rekordu.
    strict=True (dysponent form/upload) turns blocking problems into errors to fix before publishing."""
    r = {k: ("" if _blank(raw.get(k)) else str(raw.get(k)).strip()) for k in FIELDS}
    issues: list[Issue] = []
    needs_check = False

    if not r["zrodlo"]:
        r["zrodlo"] = "inne"
        _issue(issues, 1, "zrodlo")

    coords_ok = False
    if r["lat"] and r["lon"]:
        try:
            lat, f1, d1 = parse_coord(r["lat"])
            lon, f2, d2 = parse_coord(r["lon"])
            if not in_poland(lat, lon) and in_poland(lon, lat):
                lat, lon, d1, d2, f1 = lon, lat, d2, d1, True
            if in_poland(lat, lon) and (lat, lon) != (0, 0):
                coords_ok = True
                if f1 or f2:
                    _issue(issues, 24, "lat/lon", f"{r['lat']},{r['lon']}")
                if min(d1, d2) < 3:
                    _issue(issues, 15, "lat/lon", f"{r['lat']},{r['lon']}")
                r["lat"], r["lon"] = round(lat, 7), round(lon, 7)
            else:
                _issue(issues, 3, "lat/lon", f"{r['lat']},{r['lon']}", level=BLAD if strict else None)
        except ValueError:
            _issue(issues, 3, "lat/lon", f"{r['lat']},{r['lon']}", level=BLAD if strict else None)
    else:
        _issue(issues, 2, "lat/lon", level=BLAD if strict else None)
    if not coords_ok:
        city = CITY_CENTROIDS.get(r["miejscowosc"].lower())
        if city and not strict:
            r["lat"], r["lon"] = city
            r["sposob_geokodowania"] = "miejscowosc"
            _issue(issues, 28, "lat/lon", r["miejscowosc"])
            _issue(issues, 15, "lat/lon", r["miejscowosc"], "środek miejscowości")
        else:
            r["lat"] = r["lon"] = ""
        needs_check = True
    elif not r["sposob_geokodowania"]:
        r["sposob_geokodowania"] = "wspolrzedne_zrodla"

    for k in BOOL_FIELDS:
        v = r[k].lower()
        if not v or v in ("true", "false"):
            r[k] = v
        elif v in TRUE_VALS:
            r[k] = "true"; _issue(issues, 18, k, raw.get(k))
        elif v in FALSE_VALS:
            r[k] = "false"; _issue(issues, 18, k, raw.get(k))
        else:
            r[k] = ""; _issue(issues, 18, k, raw.get(k), "nierozpoznana wartość, usunięto")

    for k, allowed in DICTS.items():
        v = r[k]
        if not v:
            continue
        norm = v.lower().strip() if k == "cecha_adresu" else v.lower().strip().replace(" ", "_").replace("-", "_")
        norm = {"dla_klientów": "dla_klientow", "na_zewnątrz_budynku": "na_zewnatrz_budynku", "na_zewnatrz": "na_zewnatrz_budynku", "na_zewnątrz": "na_zewnatrz_budynku", "w_środku": "w_budynku"}.get(norm, norm)
        if norm in allowed:
            r[k] = norm
        else:
            fb = DICT_FALLBACK[k]
            r[k] = fb or ""
            _issue(issues, 7, k, v, f"→ {fb or 'puste'}")

    if r["kontakt_telefon"]:
        digits = re.sub(r"\D", "", r["kontakt_telefon"])
        if digits.startswith("0048") and len(digits) == 13:
            digits = digits[4:]
        elif digits.startswith("48") and len(digits) == 11:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 10:
            digits = digits[1:]
        if len(digits) != 9:
            _issue(issues, 5, "kontakt_telefon", r["kontakt_telefon"]); r["kontakt_telefon"] = ""
        elif MOBILE.match(digits) and not strict and r["zrodlo"] != "dysponent":
            _issue(issues, 9, "kontakt_telefon", "<usunięto>", "numer komórkowy z nieznanego źródła"); r["kontakt_telefon"] = ""
        else:
            r["kontakt_telefon"] = digits

    if r["kod_pocztowy"]:
        pc = re.sub(r"[\s–—]", "", r["kod_pocztowy"])
        if re.fullmatch(r"\d{5}", pc):
            pc = f"{pc[:2]}-{pc[2:]}"
        if re.fullmatch(r"\d{2}-\d{3}", pc):
            r["kod_pocztowy"] = pc
        else:
            _issue(issues, 6, "kod_pocztowy", r["kod_pocztowy"]); r["kod_pocztowy"] = ""

    if r["kontakt_email"]:
        m = EMAIL.match(r["kontakt_email"])
        if not m:
            _issue(issues, 9, "kontakt_email", "", "niepoprawny format"); r["kontakt_email"] = ""
        elif m[1].lower() in FREE_MAIL and not FUNCTIONAL_LOCAL.match(r["kontakt_email"].split("@")[0]):
            _issue(issues, 9, "kontakt_email", "<usunięto>"); r["kontakt_email"] = ""

    if r["zdjecie_url"]:
        u = r["zdjecie_url"]
        if u.startswith("http://"):
            r["zdjecie_url"] = "https://" + u[7:]; _issue(issues, 19, "zdjecie_url", u, "zamieniono na https")
        elif not u.startswith("https://"):
            r["zdjecie_url"] = ""; _issue(issues, 19, "zdjecie_url", u, "usunięto")

    if r["poziom_pietro"] != "":
        named = {"parter": "0", "p": "0", "piwnica": "-1", "suterena": "-1", "antresola": "0"}
        r["poziom_pietro"] = named.get(r["poziom_pietro"].lower().strip(" ."), r["poziom_pietro"])
        try:
            lvl = float(r["poziom_pietro"].replace(",", "."))
            if lvl != int(lvl) or not -5 <= lvl <= 100:
                raise ValueError
            r["poziom_pietro"] = int(lvl)
        except ValueError:
            _issue(issues, 25, "poziom_pietro", r["poziom_pietro"]); r["poziom_pietro"] = ""

    dates = {}
    for k in DATE_FIELDS + ["data_dodania_w_zrodle"]:
        v = r[k]
        if not v:
            continue
        d = parse_date(v)
        if d is None:
            _issue(issues, 8, k, v); r[k] = ""; continue
        if d.isoformat() != v[:10]:
            _issue(issues, 27, k, v)
        r[k] = d.isoformat(); dates[k] = d

    for k in ("data_przegladu", "data_weryfikacji"):
        if k in dates and dates[k] > today:
            _issue(issues, 13, k, r[k]); r[k] = ""; del dates[k]

    for k in ("data_waznosci_elektrod", "data_waznosci_baterii"):
        if k in dates and dates[k] < today:
            _issue(issues, 12, k, r[k]); needs_check = True

    if "data_weryfikacji" not in dates or _months_between(dates["data_weryfikacji"], today) >= 12:
        _issue(issues, 17, "data_weryfikacji", r["data_weryfikacji"])

    if r["godziny_dostepu"]:
        try:
            norm = ohlib.normalize(r["godziny_dostepu"])
            if norm != r["godziny_dostepu"]:
                _issue(issues, 26, "godziny_dostepu", r["godziny_dostepu"], f"→ {norm}")
                r["godziny_dostepu"] = norm
        except (ohlib.OHParseError, ValueError):
            pass
        if r["godziny_dostepu"] == "24/7":
            r["calodobowo"], r["godziny_dostepu"] = "true", ""
        else:
            wm = ohlib.weekly_minutes(r["godziny_dostepu"])
            if wm is None:
                _issue(issues, 22, "godziny_dostepu", r["godziny_dostepu"])
            elif r["calodobowo"] == "true" and wm < 7 * 1440:
                _issue(issues, 10, "godziny_dostepu", r["godziny_dostepu"])
            elif wm == 7 * 1440:
                r["calodobowo"] = "true"
            if r["calodobowo"] == "" and wm is not None:
                r["calodobowo"] = "false"
    if r["calodobowo"] == "false" and not r["godziny_dostepu"]:
        _issue(issues, 20, "godziny_dostepu", level=BLAD if strict else None)

    if r["calodobowo"] == "true" and r["kategoria_dostepu"] in ("prywatny", "brak_dostepu"):
        _issue(issues, 11, "kategoria_dostepu", r["kategoria_dostepu"])
    if r["umiejscowienie"] == "w_pojezdzie" and r["stacjonarny"] == "true":
        _issue(issues, 14, "stacjonarny")
    if r["umiejscowienie"] == "w_budynku" and (r["poziom_pietro"] == "" or not r["opis_dojscia"]):
        _issue(issues, 21, "poziom_pietro/opis_dojscia", level=BLAD if strict else None)

    for k in MINIMUM:
        if k not in ("id_aed", "lat", "lon") and r[k] == "":
            _issue(issues, 23, k, level=BLAD if strict else None)

    r["licencja_zrodla"] = r["licencja_zrodla"] or LICENSES.get(r["zrodlo"], "do_ustalenia")
    r["status_rekordu"] = record_status(r, dates, today, needs_check)
    return r, issues


def record_status(r: dict, dates: dict, today: date, needs_check: bool) -> str:
    given = r["status_rekordu"].lower()
    if given == "usuniety":
        return "usuniety"
    if needs_check or r["status_sprawnosci"] == "niesprawny":
        return "wymaga_sprawdzenia"
    fresh = "data_weryfikacji" in dates and _months_between(dates["data_weryfikacji"], today) < 12
    trusted = r["sposob_weryfikacji"] in ("kontrola_dysponenta", "potwierdzenie_qr") or r["zrodlo"] == "dysponent"
    if given == "zweryfikowany" or (fresh and trusted):
        return "zweryfikowany" if fresh or given == "zweryfikowany" else "zgloszony"
    return given if given in STATUS_REKORDU else "zgloszony"


def has_error(issues: list[Issue]) -> bool:
    return any(i.level == BLAD for i in issues)
