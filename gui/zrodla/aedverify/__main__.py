import argparse
import csv
import json
import os
import sys

from . import engine, server


def _rows(path):
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        if isinstance(d, dict) and "h" in d:
            return [dict(zip(d["h"], r)) for r in d["d"]]
        return d
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def main(argv=None):
    p = argparse.ArgumentParser(prog="aedverify")
    s = p.add_subparsers(dest="cmd", required=True)
    i = s.add_parser("import")
    i.add_argument("plik")
    i.add_argument("--zrodlo", default="import")
    i.add_argument("--db", default="aedverify.db")
    v = s.add_parser("check")
    v.add_argument("zdjecie")
    v.add_argument("--aed", required=True)
    v.add_argument("--gps", required=True)
    r = s.add_parser("serve")
    r.add_argument("--db", default="aedverify.db")
    r.add_argument("--foto", default="zdjecia")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8090)
    a = p.parse_args(argv)
    if a.cmd == "import":
        n = server.Store(a.db, os.path.join(os.path.dirname(os.path.abspath(a.db)), "zdjecia")).import_rows(_rows(a.plik), a.zrodlo)
        print(f"{n} AED zaimportowanych jako niezweryfikowane")
    elif a.cmd == "check":
        la, lo = map(float, a.aed.split(","))
        g = [float(x) for x in a.gps.split(",")]
        w = engine.verify(open(a.zdjecie, "rb").read(), {"lat": g[0], "lon": g[1], "accuracy": g[2] if len(g) > 2 else 15}, {"lat": la, "lon": lo})
        json.dump(w.dict(), sys.stdout, ensure_ascii=False, indent=1, default=str)
        print()
    else:
        static = os.path.join(os.path.dirname(__file__), "static")
        server.serve(a.db, a.foto, static, a.host, a.port, os.environ.get("AED_ADMIN_TOKEN"))


main()
