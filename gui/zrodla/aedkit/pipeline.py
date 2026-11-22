import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from .rules import RULES, BLAD, Issue, validate_record, has_error, _months_between
from .schema import FIELDS, MINIMUM, RECOMMENDED

DUP_METERS = 25.0


def haversine(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def stable_id(zrodlo: str, id_zrodla: str, used: set) -> str:
    n = int(hashlib.sha1(f"{zrodlo}|{id_zrodla}".encode()).hexdigest(), 16) % 10**8
    while f"PL-AED-{n:08d}" in used:
        n = (n + 1) % 10**8
    out = f"PL-AED-{n:08d}"
    used.add(out)
    return out


def etykieta(r: dict) -> str:
    addr = " ".join(x for x in [r["cecha_adresu"] if r["cecha_adresu"] != "brak" else "", r["ulica"], r["numer_budynku"]] if x)
    parts = [r["nazwa_obiektu"] or r["dysponent_nazwa"], addr or r["miejscowosc"]]
    label = ", ".join(p for p in parts if p) or (r["opis_dojscia"] or f"AED {r['miejscowosc']}".strip())
    return label[:100] or "AED"


def quality(r: dict, issues: list[Issue], today: date, sources: int = 1) -> int:
    mins = [k for k in MINIMUM if k != "id_aed"]
    score = 40 * sum(r[k] != "" for k in mins) / len(mins)
    score += 20 * sum(r[k] != "" for k in RECOMMENDED) / len(RECOMMENDED)
    if r["data_weryfikacji"]:
        age = _months_between(date.fromisoformat(r["data_weryfikacji"]), today)
        score += 25 if age < 6 else 15 if age < 12 else 5 if age < 24 else 0
    score += 10 if sources >= 2 else 5
    warn = sum(1 for i in issues if i.level == "ostrzezenie" and i.rule not in (23,))
    score += max(0, 5 - warn)
    if r["kategoria_dostepu"] == "nieznany":
        score -= 5
    if r["sposob_geokodowania"] == "miejscowosc":
        score -= 15
    return max(0, min(100, round(score)))


def _grid(records):
    g = defaultdict(list)
    for idx, r in records:
        g[(int(r["lat"] / 0.0003), int(r["lon"] / 0.0005))].append(idx)
    return g


def _similar(a: dict, b: dict) -> bool:
    na = (a["nazwa_obiektu"] or a["opis_dojscia"]).lower()
    nb = (b["nazwa_obiektu"] or b["opis_dojscia"]).lower()
    if not na or not nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.6


def run(rows: list[dict], today: date | None = None, strict: bool = False, groups: list[str] | None = None) -> dict:
    today = today or date.today()
    results = []
    for n, raw in enumerate(rows, start=2):
        rec, issues = validate_record(raw, today, strict)
        results.append({"line": n, "record": rec, "issues": issues, "raw": raw})

    seen_src, seen_id = {}, {}
    dup_of = {}
    for idx, res in enumerate(results):
        r = res["record"]
        if r["zrodlo"] and r["id_zrodla"]:
            key = (r["zrodlo"], r["id_zrodla"])
            if key in seen_src:
                dup_of[idx] = seen_src[key]
                res["issues"].append(Issue(4, RULES[4][0], "id_zrodla", RULES[4][1], r["id_zrodla"]))
                continue
            seen_src[key] = idx
        if r["id_aed"]:
            if r["id_aed"] in seen_id:
                res["issues"].append(Issue(4, RULES[4][0], "id_aed", "Zduplikowany id_aed – nadano nowy", r["id_aed"]))
                r["id_aed"] = ""
            else:
                seen_id[r["id_aed"]] = idx

    valid = [(i, res["record"]) for i, res in enumerate(results) if i not in dup_of and res["record"]["lat"] != "" and not has_error(res["issues"])]
    grid = _grid(valid)
    by_idx = dict(valid)
    sources = defaultdict(set)
    merged_into = {}
    grp = {i: (groups[i] if groups else r["zrodlo"]) for i, r in valid}
    for i, r in valid:
        sources[i].add(grp[i])
    for i, r in valid:
        cx, cy = int(r["lat"] / 0.0003), int(r["lon"] / 0.0005)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j <= i:
                        continue
                    o = by_idx[j]
                    d = haversine((r["lat"], r["lon"]), (o["lat"], o["lon"]))
                    if d >= DUP_METERS or not _similar(r, o):
                        continue
                    if grp[i] != grp[j] and j not in merged_into and i not in merged_into:
                        merged_into[j] = i
                        sources[i] |= sources[j]
                    else:
                        note = f"{d:.0f} m od wiersza {results[j]['line']}"
                        results[i]["issues"].append(Issue(16, RULES[16][0], "lat/lon", f"{RULES[16][1]} ({note})"))

    used = set(seen_id)
    accepted, rejected, review = [], [], []
    for i, res in enumerate(results):
        r = res["record"]
        if i in dup_of:
            res["merged_into"] = dup_of[i]; continue
        if has_error(res["issues"]):
            rejected.append(res); continue
        if i in merged_into:
            res["merged_into"] = merged_into[i]; continue
        if not r["id_aed"]:
            r["id_aed"] = stable_id(r["zrodlo"], r["id_zrodla"] or f"line{res['line']}", used)
        r["etykieta"] = r["etykieta"] or etykieta(r)
        r["data_aktualizacji"] = today.isoformat()
        r["wskaznik_jakosci"] = quality(r, res["issues"], today, len(sources[i]))
        res["sources"] = sorted(sources[i])
        if r["lat"] == "" or r["status_rekordu"] == "usuniety":
            review.append(res)
        else:
            accepted.append(res)
            if r["status_rekordu"] == "wymaga_sprawdzenia":
                review.append(res)

    return {"today": today.isoformat(), "strict": strict, "results": results, "review": review,
            "accepted": accepted, "rejected": rejected, "merged": len(merged_into) + len(dup_of),
            "merged_into": merged_into, "dup_of": dup_of}


def summarize(out: dict) -> dict:
    per_rule = Counter()
    for res in out["results"]:
        for i in {(x.rule, x.level) for x in res["issues"]}:
            per_rule[i] += 1
    n = len(out["results"])
    acc = out["accepted"]
    return {
        "data": out["today"],
        "tryb": "dysponent (ścisły)" if out["strict"] else "import",
        "rekordy_wejsciowe": n,
        "przyjete": len(acc),
        "odrzucone_tryb_scisly": len(out["rejected"]),
        "do_sprawdzenia": len(out["review"]),
        "bez_wspolrzednych": sum(1 for r in out["review"] if r["record"]["lat"] == ""),
        "statusy": dict(Counter(r["record"]["status_rekordu"] for r in acc)),
        "scalone_duplikaty_miedzy_zrodlami": out["merged"],
        "sredni_wskaznik_jakosci": round(sum(r["record"]["wskaznik_jakosci"] for r in acc) / len(acc), 1) if acc else 0,
        "calodobowe": sum(r["record"]["calodobowo"] == "true" for r in acc),
        "publiczne": sum(r["record"]["kategoria_dostepu"] == "publiczny" for r in acc),
        "z_opisem_dojscia": sum(bool(r["record"]["opis_dojscia"]) for r in acc),
        "zweryfikowane_12m": sum(not any(x.rule == 17 for x in r["issues"]) for r in acc),
        "reguly": [
            {"nr": rule, "poziom": level, "opis": RULES[rule][1], "rekordy": c, "procent": round(100 * c / n, 1) if n else 0}
            for (rule, level), c in sorted(per_rule.items())
        ],
    }


def write_outputs(out: dict, outdir: str | Path) -> dict:
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "aed_dane.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\r\n")
        w.writeheader()
        for res in out["accepted"]:
            w.writerow(res["record"])
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [res["record"]["lon"], res["record"]["lat"]]},
        "properties": {k: v for k, v in res["record"].items() if k not in ("lat", "lon")},
    } for res in out["accepted"]]
    (outdir / "aed_dane.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    with open(outdir / "do_sprawdzenia.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\r\n")
        w.writeheader()
        for res in out["review"]:
            w.writerow(res["record"])
    with open(outdir / "problemy.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["wiersz", "id_zrodla", "regula", "poziom", "pole", "komunikat", "wartosc"])
        for res in out["results"]:
            for i in res["issues"]:
                w.writerow([res["line"], res["record"]["id_zrodla"], i.rule, i.level, i.field, i.message, i.value])
    summary = summarize(out)
    (outdir / "raport.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "raport.html").write_text(render_html(summary), encoding="utf-8")
    return summary


def render_html(s: dict) -> str:
    color = {"blad": "#b3261e", "naprawa": "#8a5a00", "ostrzezenie": "#1f3864", "info": "#555"}
    label = {"blad": "Błąd", "naprawa": "Naprawa", "ostrzezenie": "Ostrzeżenie", "info": "Informacja"}
    rows = "".join(
        f"<tr><td>{r['nr']}</td><td style='color:{color[r['poziom']]};font-weight:600'>{label[r['poziom']]}</td>"
        f"<td>{r['opis']}</td><td class=n>{r['rekordy']}</td><td class=n>{r['procent']}%</td></tr>"
        for r in s["reguly"])
    kpi = [("Rekordy", s["rekordy_wejsciowe"]), ("Opublikowane", s["przyjete"]), ("Do sprawdzenia", s["do_sprawdzenia"]),
           ("Scalone duplikaty", s["scalone_duplikaty_miedzy_zrodlami"]),
           ("Śr. wskaźnik jakości", s["sredni_wskaznik_jakosci"]), ("Całodobowe", s["calodobowe"]),
           ("Z opisem dojścia", s["z_opisem_dojscia"]), ("Zweryfikowane ≤12 mies.", s["zweryfikowane_12m"])]
    tiles = "".join(f"<div class=t><div class=v>{v}</div><div class=l>{k}</div></div>" for k, v in kpi)
    return f"""<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raport walidacji danych AED</title><style>
body{{font-family:system-ui,Arial,sans-serif;margin:2rem auto;max-width:1000px;padding:0 1rem;color:#1a1a1a}}
h1{{font-size:1.5rem}}.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.75rem;margin:1.5rem 0}}
.t{{border:1px solid #d0d0d0;border-radius:8px;padding:.75rem}}.v{{font-size:1.6rem;font-weight:700}}.l{{font-size:.85rem;color:#444}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #e0e0e0;padding:.5rem;text-align:left;vertical-align:top}}
th{{background:#1f3864;color:#fff}}.n{{text-align:right;font-variant-numeric:tabular-nums}}
</style></head><body><h1>Raport walidacji danych AED</h1>
<p>Data: {s['data']} · Tryb: {s['tryb']}</p><div class=g>{tiles}</div>
<h2>Reguły</h2><table><caption class=l>Liczba rekordów, w których zadziałała reguła</caption>
<thead><tr><th scope=col>Nr</th><th scope=col>Poziom</th><th scope=col>Reguła</th><th scope=col class=n>Rekordy</th><th scope=col class=n>%</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
