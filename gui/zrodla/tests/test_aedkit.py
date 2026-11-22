import csv
import io
from datetime import date, datetime

import pytest

from aedkit import opening_hours as oh
from aedkit.osm import to_schema, read_csv_text
from aedkit.pipeline import run
from aedkit.rules import validate_record, has_error, parse_coord
from aedkit.schema import FIELDS

TODAY = date(2026, 11, 21)

BASE = {
    "lat": "52.40640", "lon": "16.92520", "miejscowosc": "Poznań", "kod_pocztowy": "61-001",
    "cecha_adresu": "ul.", "ulica": "Główna", "numer_budynku": "1", "stacjonarny": "true",
    "umiejscowienie": "w_budynku", "poziom_pietro": "0", "opis_dojscia": "Parter, przy recepcji",
    "kategoria_dostepu": "publiczny", "calodobowo": "true", "sposob_otwarcia": "swobodny",
    "status_sprawnosci": "sprawny", "dysponent_nazwa": "Urząd Gminy", "data_weryfikacji": "2026-10-01",
    "sposob_weryfikacji": "kontrola_dysponenta", "zrodlo": "dysponent", "id_zrodla": "d-1",
    "kontakt_telefon": "610000000",
}

GOLDEN = {
    "parter_slownie": {"poziom_pietro": "parter"},
    "piwnica": {"poziom_pietro": "-2", "opis_dojscia": "Poziom -2, parking"},
    "wies_bez_ulicy": {"cecha_adresu": "brak", "ulica": "", "numer_budynku": "17", "miejscowosc": "Wólka"},
    "bez_numeru": {"numer_budynku": "", "ulica": "Leśna"},
    "numer_z_litera": {"numer_budynku": "12A"},
    "numer_z_ukosnikiem": {"numer_budynku": "12/14"},
    "godziny_przez_polnoc": {"calodobowo": "false", "godziny_dostepu": "Mo-Su 22:00-06:00"},
    "kod_z_zerem": {"kod_pocztowy": "00-950"},
    "telefon_z_zerem": {"kontakt_telefon": "052 123 45 67"},
    "telefon_z_prefiksem": {"kontakt_telefon": "+48 61 000 00 00"},
    "jastrzebia_gora_polnoc": {"lat": "54.8300", "lon": "18.3000"},
    "opolonek_poludnie": {"lat": "49.0030", "lon": "22.8580"},
    "osinow_zachod": {"lat": "52.8500", "lon": "14.1250"},
    "zosin_wschod": {"lat": "50.8650", "lon": "24.1450"},
    "na_zewnatrz_bez_pietra": {"umiejscowienie": "na_zewnatrz_budynku", "poziom_pietro": "", "opis_dojscia": ""},
    "pojazd": {"umiejscowienie": "w_pojezdzie", "stacjonarny": "false", "poziom_pietro": "", "opis_dojscia": ""},
    "email_funkcyjny_gmail": {"kontakt_email": "sekretariat.sp3@gmail.com"},
    "polskie_znaki_i_cudzyslowy": {"opis_dojscia": "Żółta szafka „przy wejściu”, obok \"Biedronki\", 2. piętro"},
    "rok_przestepny": {"data_przegladu": "2024-02-29"},
}


@pytest.mark.parametrize("name", GOLDEN)
def test_golden_records_pass_untouched(name):
    rec, issues = validate_record({**BASE, **GOLDEN[name]}, TODAY, strict=True)
    assert not has_error(issues), [i.as_dict() for i in issues]
    damaging = {1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 19, 22, 25, 28}
    assert not [i.as_dict() for i in issues if i.rule in damaging]
    assert rec["status_rekordu"] == "zweryfikowany" and rec["lat"] != ""
    for k, v in GOLDEN[name].items():
        if k in ("opis_dojscia", "numer_budynku", "ulica", "kod_pocztowy"):
            assert rec[k] == v


MUTATIONS = [
    ({"lat": "48.1", "lon": "16.3"}, 3),
    ({"lat": "54.95", "lon": "18.3"}, 3),
    ({"lat": "abc"}, 3),
    ({"lat": ""}, 2),
    ({"zrodlo": ""}, 1),
    ({"kontakt_telefon": "61 000 00"}, 5),
    ({"kod_pocztowy": "6100"}, 6),
    ({"kategoria_dostepu": "dla wszystkich"}, 7),
    ({"data_przegladu": "2026-02-30"}, 8),
    ({"kontakt_email": "jan.kowalski@gmail.com"}, 9),
    ({"godziny_dostepu": "Mo-Fr 08:00-16:00"}, 10),
    ({"kategoria_dostepu": "prywatny"}, 11),
    ({"data_waznosci_elektrod": "2026-01-01"}, 12),
    ({"data_przegladu": "2027-01-01"}, 13),
    ({"umiejscowienie": "w_pojezdzie", "poziom_pietro": "", "opis_dojscia": ""}, 14),
    ({"lat": "52.41", "lon": "16.93"}, 15),
    ({"data_weryfikacji": "2025-06-01"}, 17),
    ({"calodobowo": "TAK"}, 18),
    ({"calodobowo": "1"}, 18),
    ({"zdjecie_url": "http://x.pl/a.jpg"}, 19),
    ({"calodobowo": "false"}, 20),
    ({"opis_dojscia": ""}, 21),
    ({"calodobowo": "false", "godziny_dostepu": "w dni robocze rano"}, 22),
    ({"lat": "16.92520", "lon": "52.40640"}, 24),
    ({"lat": "52,40640"}, 24),
    ({"lon": "-16.92520"}, 24),
    ({"lat": "52°24'23\"N", "lon": "16°55'31\"E"}, 24),
    ({"poziom_pietro": "wysoko"}, 25),
    ({"calodobowo": "false", "godziny_dostepu": "pn-pt 8-16"}, 26),
    ({"data_weryfikacji": "01.10.2026"}, 27),
]
CASCADE = {25: {21}, 2: {28, 15}, 3: {28, 15}, 9: set(), 22: set()}
ALLOWED = {23, 17, 15, 20}


@pytest.mark.parametrize("mut,rule", MUTATIONS, ids=[f"{r}-{list(m.values())[0]}" for m, r in MUTATIONS])
def test_single_mutation_fires_expected_rule(mut, rule):
    _, base_issues = validate_record(BASE, TODAY)
    assert base_issues == [], [i.as_dict() for i in base_issues]
    rec, issues = validate_record({**BASE, **mut}, TODAY)
    fired = {i.rule for i in issues}
    assert rule in fired, (mut, fired)
    extra = fired - {rule} - ALLOWED - CASCADE.get(rule, set())
    assert not extra, (mut, fired)


def test_bad_coordinates_never_delete_record():
    rec, issues = validate_record({**BASE, "lat": "99", "lon": "99", "miejscowosc": "Wólka"}, TODAY)
    assert rec["status_rekordu"] == "wymaga_sprawdzenia"
    out = run([{**BASE, "lat": "99", "lon": "99", "miejscowosc": "Wólka"}], TODAY)
    assert len(out["review"]) == 1 and not out["rejected"]


def test_geocode_from_city_lowers_quality():
    out = run([{**BASE, "lat": "", "lon": ""}, BASE | {"id_zrodla": "d-2", "lat": "52.30000", "lon": "16.80000"}], TODAY)
    geo = next(r for r in out["accepted"] if r["record"]["sposob_geokodowania"] == "miejscowosc")
    exact = next(r for r in out["accepted"] if r["record"]["sposob_geokodowania"] == "wspolrzedne_zrodla")
    assert geo["record"]["status_rekordu"] == "wymaga_sprawdzenia"
    assert geo["record"]["wskaznik_jakosci"] < exact["record"]["wskaznik_jakosci"]


def test_invalid_calendar_date_is_just_missing():
    rec, issues = validate_record({**BASE, "data_przegladu": "2025-02-29"}, TODAY)
    assert rec["data_przegladu"] == ""
    assert {i.level for i in issues if i.rule == 8} == {"info"}


def test_expired_pads_mark_for_check_but_keep():
    rec, _ = validate_record({**BASE, "data_waznosci_elektrod": "2025-12-31"}, TODAY)
    assert rec["status_rekordu"] == "wymaga_sprawdzenia" and rec["lat"] != ""


def test_status_verified_and_reported():
    assert validate_record(BASE, TODAY)[0]["status_rekordu"] == "zweryfikowany"
    osm = {**BASE, "zrodlo": "osm", "sposob_weryfikacji": "zgloszenie_spolecznosci", "data_weryfikacji": "2024-01-01"}
    assert validate_record(osm, TODAY)[0]["status_rekordu"] == "zgloszony"


def test_license_per_source():
    assert validate_record({**BASE, "zrodlo": "osm"}, TODAY)[0]["licencja_zrodla"] == "ODbL-1.0"
    assert validate_record(BASE, TODAY)[0]["licencja_zrodla"] == "CC0-1.0"


def test_private_email_not_in_output_or_log():
    rec, issues = validate_record({**BASE, "kontakt_email": "jan.kowalski@wp.pl"}, TODAY)
    assert rec["kontakt_email"] == ""
    assert "kowalski" not in " ".join(i.value + i.message for i in issues)


def test_mobile_from_unknown_source_removed_but_kept_from_dysponent():
    osm = validate_record({**BASE, "zrodlo": "osm", "kontakt_telefon": "601 234 567"}, TODAY)[0]
    dys = validate_record({**BASE, "kontakt_telefon": "601 234 567"}, TODAY)[0]
    assert osm["kontakt_telefon"] == "" and dys["kontakt_telefon"] == "601234567"


def test_duplicate_source_id_merged_not_rejected():
    out = run([BASE, dict(BASE)], TODAY)
    assert len(out["accepted"]) == 1 and out["merged"] == 1 and not out["rejected"]


def test_cross_source_merge():
    c = {**BASE, "zrodlo": "osm", "id_zrodla": "node/1", "lat": "52.40645", "lon": "16.92525"}
    out = run([BASE, c], TODAY)
    assert out["merged"] == 1 and out["accepted"][0]["sources"] == ["dysponent", "osm"]


def test_same_source_nearby_is_warning_not_merge():
    out = run([BASE, {**BASE, "id_zrodla": "d-2", "lat": "52.40645"}], TODAY)
    assert out["merged"] == 0 and len(out["accepted"]) == 2
    assert any(i.rule == 16 for r in out["accepted"] for i in r["issues"])


def test_csv_with_bom_quotes_newlines_semicolon():
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, delimiter=";")
    w.writeheader()
    w.writerow({**{k: "" for k in FIELDS}, **BASE, "opis_dojscia": "Hol, przy „recepcji”;\nza \"drzwiami\""})
    rows = read_csv_text("﻿" + buf.getvalue())
    assert len(rows) == 1 and "id_aed" in rows[0]
    assert rows[0]["opis_dojscia"] == "Hol, przy „recepcji”;\nza \"drzwiami\""
    rec, issues = validate_record(rows[0], TODAY)
    assert rec["opis_dojscia"].startswith("Hol, przy")


@pytest.mark.parametrize("raw,expected", [
    ("pn-pt 8-16", "Mo-Fr 08:00-16:00"),
    ("Pon.-Pt. 8:00–16:00, sob. 9-13", "Mo-Fr 08:00-16:00; Sa 09:00-13:00"),
    ("Mo-Fr 8AM-1PM", "Mo-Fr 08:00-13:00"),
    ("Mo-Fr 1-5PM", "Mo-Fr 13:00-17:00"),
    ("całodobowo", "24/7"),
    ("0-24", "24/7"),
    ("Mo-Su 22:00-06:00", "Mo-Su 22:00-06:00"),
    ("pn-sob 10-22, ndz zamknięte", "Mo-Sa 10:00-22:00; Su off"),
])
def test_hours_normalization(raw, expected):
    assert oh.normalize(raw) == expected


@pytest.mark.parametrize("spec,at,expected", [
    ("24/7", datetime(2026, 11, 22, 3, 0), True),
    ("Mo-Fr 08:00-18:00; Sa 09:00-14:00", datetime(2026, 11, 21, 13, 0), True),
    ("Mo-Fr 08:00-18:00; Sa 09:00-14:00", datetime(2026, 11, 21, 15, 0), False),
    ("Mo-Su 22:00-06:00", datetime(2026, 11, 24, 1, 30), True),
    ("Mo-Su 22:00-06:00", datetime(2026, 11, 24, 12, 0), False),
    ("Fr 22:00-06:00", datetime(2026, 11, 21, 5, 0), True),
    ("Mo-Fr 07:00-15:00,16:00-20:00", datetime(2026, 11, 23, 15, 30), False),
    ("sunrise-sunset", datetime(2026, 11, 22, 10, 0), None),
])
def test_opening_hours(spec, at, expected):
    assert oh.is_open(spec, at) is expected


@pytest.mark.parametrize("v,expected", [("52.1234", 52.1234), ("52,1234", 52.1234), ("-24,09", 24.09),
                                       ("54°50'N", 54 + 50 / 60), ("52°24'23.5\"N", 52 + 24 / 60 + 23.5 / 3600)])
def test_coordinate_formats(v, expected):
    assert parse_coord(v)[0] == pytest.approx(expected)


def test_osm_mapping():
    row = {"@id": "123", "lat": "52.1", "lon": "21.0", "access": "customers", "indoor": "yes",
           "level": "1", "defibrillator:location": "1 piętro, klucz w recepcji",
           "opening_hours": "24/7", "operator": "Szkoła Podstawowa nr 5", "addr:street": "Aleja Róż",
           "addr:housenumber": "5", "addr:city": "Warszawa"}
    r = to_schema(row)
    assert r["kategoria_dostepu"] == "dla_klientow" and r["umiejscowienie"] == "w_budynku"
    assert r["calodobowo"] == "true" and r["sposob_otwarcia"] == "klucz_u_pracownika"
    assert r["dysponent_typ"] == "oswiata" and (r["cecha_adresu"], r["ulica"]) == ("al.", "Róż")
    assert r["id_zrodla"] == "node/123"


def test_osm_vehicle_detection():
    r = to_schema({"@id": "9", "lat": "52.1", "lon": "21.0", "defibrillator:location": "Samochód GBA OSP Wólka"})
    assert r["umiejscowienie"] == "w_pojezdzie" and r["stacjonarny"] == "false"


def test_aggregate_two_providers(tmp_path):
    from aedkit.aggregate import aggregate
    a = tmp_path / "gmina.csv"; b = tmp_path / "psp.csv"
    for path, rows in ((a, [BASE, {**BASE, "id_zrodla": "d-2", "lat": "52.50000", "lon": "16.95000", "nazwa_obiektu": "Hala"}]),
                       (b, [{**BASE, "id_zrodla": "psp-9", "lat": "52.40645", "lon": "16.92525"}])):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
            for r in rows:
                w.writerow({**{k: "" for k in FIELDS}, **r})
    rep = aggregate([f"gmina-poznan={a}", f"psp-poznan={b}"], tmp_path / "out", TODAY)
    assert rep["rekordy_wejsciowe"] == 3 and rep["rekordy_po_scaleniu"] == 2
    assert rep["potwierdzone_przez_2_lub_wiecej_dostawcow"] == 1
    rows = list(csv.DictReader(open(tmp_path / "out" / "krajowa_lista_aed.csv", encoding="utf-8")))
    both = next(r for r in rows if r["liczba_dostawcow"] == "2")
    assert both["dostawcy"] == "gmina-poznan;psp-poznan" and "psp-poznan:psp-9" in both["identyfikatory_zrodlowe"]
    assert (tmp_path / "out" / "metadane_dcat.jsonld").exists()
