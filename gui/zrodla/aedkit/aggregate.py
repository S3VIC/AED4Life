import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from . import osm
from .pipeline import run, summarize

AGG_FIELDS = [
    "id_aed", "etykieta", "lat", "lon", "miejscowosc", "kod_teryt_gminy", "adres",
    "umiejscowienie", "poziom_pietro", "opis_dojscia", "kategoria_dostepu", "calodobowo",
    "godziny_dostepu", "sposob_otwarcia", "status_sprawnosci", "status_rekordu",
    "data_weryfikacji", "wskaznik_jakosci", "liczba_dostawcow", "dostawcy", "identyfikatory_zrodlowe",
    "licencje_zrodel", "data_aktualizacji",
]


def load_provider(spec: str) -> tuple[str, str, list[dict]]:
    """spec: provider_id=path[:osm]  e.g. gmina-bydgoszcz=bydgoszcz.csv  or  osm=aed_poland.csv:osm"""
    pid, _, rest = spec.partition("=")
    path, _, kind = rest.partition(":")
    rows = osm.load_rows(path)
    if kind == "osm" or pid == "osm":
        rows = [osm.to_schema(r) for r in rows]
    return pid, path, rows


def aggregate(specs: list[str], outdir: str | Path, today: date | None = None) -> dict:
    today = today or date.today()
    rows, groups, prov_meta = [], [], {}
    for spec in specs:
        pid, path, prov_rows = load_provider(spec)
        prov_meta[pid] = {"plik": path, "rekordy": len(prov_rows)}
        rows += prov_rows
        groups += [pid] * len(prov_rows)
    out = run(rows, today, strict=False, groups=groups)
    providers = defaultdict(set)
    ids = defaultdict(set)
    for i, res in enumerate(out["results"]):
        target = out["dup_of"].get(i, out["merged_into"].get(i, i))
        while target in out["merged_into"] or target in out["dup_of"]:
            target = out["dup_of"].get(target, out["merged_into"].get(target))
        providers[target].add(groups[i])
        if res["record"]["id_zrodla"]:
            ids[target].add(f'{groups[i]}:{res["record"]["id_zrodla"]}')
    index = {id(res): i for i, res in enumerate(out["results"])}
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    agg_rows = []
    for res in out["accepted"]:
        i = index[id(res)]
        r = res["record"]
        lic = sorted({("ODbL-1.0" if p == "osm" else r["licencja_zrodla"]) for p in providers[i]})
        agg_rows.append({
            **{k: r.get(k, "") for k in AGG_FIELDS},
            "adres": " ".join(x for x in [r["cecha_adresu"] if r["cecha_adresu"] != "brak" else "", r["ulica"], r["numer_budynku"]] if x),
            "liczba_dostawcow": len(providers[i]),
            "dostawcy": ";".join(sorted(providers[i])),
            "identyfikatory_zrodlowe": ";".join(sorted(ids[i])),
            "licencje_zrodel": ";".join(lic),
        })
    with open(outdir / "krajowa_lista_aed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AGG_FIELDS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(agg_rows)
    features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]},
                 "properties": {k: v for k, v in a.items() if k not in ("lat", "lon")}} for a in agg_rows]
    (outdir / "krajowa_lista_aed.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")

    per_prov = Counter()
    for i, res in enumerate(out["results"]):
        per_prov[(groups[i], "problemy")] += sum(1 for x in res["issues"] if x.level in ("ostrzezenie", "blad"))
    report = {
        "data": today.isoformat(),
        "dostawcy": {pid: {**m, "problemy": per_prov[(pid, "problemy")],
                           "rekordy_w_liscie_krajowej": sum(1 for a in agg_rows if pid in a["dostawcy"].split(";"))}
                     for pid, m in prov_meta.items()},
        "rekordy_wejsciowe": len(rows),
        "rekordy_po_scaleniu": len(agg_rows),
        "scalone_duplikaty": out["merged"],
        "potwierdzone_przez_2_lub_wiecej_dostawcow": sum(1 for a in agg_rows if a["liczba_dostawcow"] >= 2),
        "do_sprawdzenia": len(out["review"]),
    }
    (outdir / "raport_agregacji.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    any_odbl = any("ODbL-1.0" in a["licencje_zrodel"] for a in agg_rows)
    dcat = {
        "@context": {"dct": "http://purl.org/dc/terms/", "dcat": "http://www.w3.org/ns/dcat#"},
        "@type": "dcat:Dataset",
        "dct:title": {"pl": "Krajowa lista defibrylatorów AED", "en": "National list of AED defibrillators"},
        "dct:description": {"pl": "Zagregowana lista AED z zbiorów wielu dostawców publikowanych w dane.gov.pl, "
                                  "ujednolicona do wzorcowego schematu, odduplikowana, z pochodzeniem i licencją każdego rekordu."},
        "dct:publisher": "Ministerstwo Cyfryzacji (koordynator)",
        "dcat:theme": ["HEAL", "REGI"],
        "dcat:keyword": ["AED", "defibrylator", "ratownictwo"],
        "dct:accrualPeriodicity": "WEEKLY",
        "dct:language": "pl",
        "dct:spatial": "Polska",
        "dct:modified": today.isoformat(),
        "dct:license": "ODbL-1.0" if any_odbl else "CC0-1.0",
        "dct:source": [{"dostawca": pid, "zasob": m["plik"]} for pid, m in prov_meta.items()],
        "dcat:distribution": [
            {"dct:format": "CSV", "dcat:downloadURL": "krajowa_lista_aed.csv", "dct:conformsTo": "RFC 4180"},
            {"dct:format": "GeoJSON", "dcat:downloadURL": "krajowa_lista_aed.geojson"},
        ],
        "uwaga": "Szkic metadanych w duchu DCAT-AP-PL. Nazwy i wymagane pola zweryfikować z Przewodnikiem dla dostawców danych dane.gov.pl.",
    }
    (outdir / "metadane_dcat.jsonld").write_text(json.dumps(dcat, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
