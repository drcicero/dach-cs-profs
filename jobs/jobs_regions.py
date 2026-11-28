"""One-off: turn geoBoundaries ADM1 GeoJSON (DEU, AUT, CHE; simplified files) into regions.json
{code: svg path} for the map in jobs.html. Usage (from the project root): python3 jobs/jobs_regions.py DEU.geojson AUT.geojson CHE.geojson
Luxembourg (one region, ADM0 file LUX): python3 jobs/jobs_regions.py --add LUX.geojson  (adds / replaces it in the existing regions.json)
Source: https://www.geoboundaries.org (gbOpen; DEU attribution, AUT CC BY-SA 2.0, CHE swisstopo, LUX)."""
import json, math, sys

CODE = {"Baden-Württemberg": "BW", "Bayern": "BY", "Berlin": "BE", "Brandenburg": "BB", "Bremen": "HB", "Hamburg": "HH", "Hessen": "HE",
        "Mecklenburg-Vorpommern": "MV", "Niedersachsen": "NI", "Nordrhein-Westfalen": "NRW", "Rheinland-Pfalz": "RP", "Saarland": "SL",
        "Sachsen": "SN", "Sachsen-Anhalt": "ST", "Schleswig-Holstein": "SH", "Thüringen": "TH",
        "Burgenland": "AT-B", "Kärnten": "AT-K", "Niederösterreich": "AT-NÖ", "Oberösterreich": "AT-OÖ", "Salzburg": "AT-S", "Steiermark": "AT-ST",
        "Tirol": "AT-T", "Vorarlberg": "AT-V", "Wien": "AT-W",
        "Aargau": "CH-AG", "Appenzell Ausserrhoden": "CH-AR", "Appenzell Innerrhoden": "CH-AI", "Basel-Landschaft": "CH-BL", "Basel-Stadt": "CH-BS",
        "Bern": "CH-BE", "Fribourg": "CH-FR", "Genève": "CH-GE", "Glarus": "CH-GL", "Graubünden": "CH-GR", "Jura": "CH-JU", "Luzern": "CH-LU",
        "Neuchâtel": "CH-NE", "Nidwalden": "CH-NW", "Obwalden": "CH-OW", "Schaffhausen": "CH-SH", "Schwyz": "CH-SZ", "Solothurn": "CH-SO",
        "St. Gallen": "CH-SG", "Thurgau": "CH-TG", "Ticino": "CH-TI", "Uri": "CH-UR", "Valais": "CH-VS", "Vaud": "CH-VD", "Zug": "CH-ZG", "Zürich": "CH-ZH", "Luxembourg": "LU"}
TOL = 0.012  # degrees


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-12
    i, dmax = max(((i, abs(dy * (p[0] - x1) - dx * (p[1] - y1)) / n) for i, p in enumerate(pts[1:-1], 1)), key=lambda t: t[1])
    return dp(pts[:i + 1], tol)[:-1] + dp(pts[i:], tol) if dmax > tol else [pts[0], pts[-1]]


ADD = sys.argv[1] == "--add"
feats = [f for p in sys.argv[2 if ADD else 1:] for f in json.load(open(p, encoding="utf-8"))["features"]]
polys = {}
for f in feats:
    g = f["geometry"]
    polys[CODE[f["properties"]["shapeName"]]] = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
lon0, lat0 = 5.8, 55.1
k = math.cos(math.radians(48.5))
out = {}
for code, mp in polys.items():
    d = ""
    for poly in mp:
        for ring in poly:
            ring = [tuple(p[:2]) for p in ring]
            m = max(range(len(ring)), key=lambda i: math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1]))  # closed ring: split at the far point
            r = dp(ring[:m + 1], TOL)[:-1] + dp(ring[m:], TOL)
            if len(r) < 4 or abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:]))) / 2 < TOL * TOL * 4:
                continue  # tiny islands
            d += "M" + "L".join(f"{(x - lon0) * k * 100:.0f},{(lat0 - y) * 100:.0f}" for x, y in r) + "Z"
    out[code] = d
if ADD:
    out = {**json.load(open("regions.json", encoding="utf-8")), **out}
open("regions.json", "w", encoding="utf-8").write("{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in out.items()) + "\n}\n")  # one line per region, so a diff shows which region changed
print(len(out), "regions,", sum(map(len, out.values())), "bytes")
