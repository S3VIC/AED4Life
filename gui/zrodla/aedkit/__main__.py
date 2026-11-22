import argparse
import json
from datetime import date

from . import osm
from .pipeline import run, write_outputs


def main():
    p = argparse.ArgumentParser(prog="aedkit", description="Normalizacja i walidacja danych AED do publikacji w dane.gov.pl")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, help_ in (("osm", "importuj aed_poland.csv/.geojson z OpenStreetMap"),
                        ("validate", "sprawdź plik dysponenta w formacie wzorcowym")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("input")
        s.add_argument("-o", "--out", default="wynik")
        s.add_argument("--today", type=date.fromisoformat, default=date.today())
    ag = sub.add_parser("aggregate", help="zbierz zbiory wielu dostawców w krajową listę AED")
    ag.add_argument("providers", nargs="+", help="dostawca=plik.csv (dla OSM: osm=aed_poland.csv)")
    ag.add_argument("-o", "--out", default="wynik_krajowy")
    ag.add_argument("--today", type=date.fromisoformat, default=date.today())
    a = p.parse_args()
    if a.cmd == "aggregate":
        from .aggregate import aggregate
        print(json.dumps(aggregate(a.providers, a.out, a.today), ensure_ascii=False, indent=2))
        return
    rows = osm.load_rows(a.input)
    if a.cmd == "osm":
        rows = [osm.to_schema(r) for r in rows]
    out = run(rows, a.today, strict=a.cmd == "validate")
    summary = write_outputs(out, a.out)
    print(json.dumps({k: v for k, v in summary.items() if k != "reguly"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
