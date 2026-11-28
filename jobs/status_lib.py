"""Shared by the two status pages (jobs/jobs_status.py: ad sources, profs/profs_status.py: professor sources): locations, SVG map and the page template.
A row is a dict(country, region, name, key, st, n, note, reg); `st` is one of the statuses of the page's LABEL, rows are listed in the order of RANK."""
import html
import json
import math
import re
import sys

# Where each institution sits: first matching substring of the name wins (so "Frankfurt (Oder)" must come before "Frankfurt").
PLACE = [  # research institutes: headquarters (or the site the scraper looks at)
         ("Max-Planck-Institut für Informatik", 49.26, 7.05), ("MPI-INF", 49.26, 7.05), ("MPI-SWS", 49.26, 7.05), ("MPI-SP", 51.45, 7.27),
         ("MPI-IS", 48.53, 9.06), ("Max-Planck-Gesellschaft", 48.15, 11.58), ("CISPA", 49.26, 7.05), ("Hasso-Plattner", 52.39, 13.13),
         ("Fraunhofer", 48.15, 11.58), ("Leibniz", 52.52, 13.37), ("Paul Scherrer", 47.54, 8.22), ("Empa", 47.40, 8.61), ("DFKI", 49.43, 7.75),
         ("DESY", 53.58, 9.88), ("Helmholtz", 52.52, 13.37), ("Jülich", 50.91, 6.41), ("Weizenbaum", 52.52, 13.33), ("ISTA", 48.31, 16.26),
         ("Halle-Wittenberg", 51.50, 11.97), ("Frankfurt (Oder)", 52.34, 14.55), ("Freiburg (Fribourg)", 46.79, 7.16), ("Fribourg", 46.79, 7.16), ("Bundeswehr München", 48.08, 11.64),
         ("Lausitz", 51.77, 14.33), ("Cottbus", 51.77, 14.33), ("Frankfurt", 50.13, 8.67), ("Freiburg", 48.00, 7.85), ("Hohenheim", 48.71, 9.21),
         ("Karlsruhe", 49.01, 8.40), ("KIT", 49.01, 8.40), ("Konstanz", 47.69, 9.19), ("Heidelberg", 49.42, 8.67), ("Mannheim", 49.49, 8.49),
         ("Stuttgart", 48.75, 9.11), ("Tübingen", 48.52, 9.06), ("Ulm", 48.42, 9.95), ("Augsburg", 48.33, 10.90), ("Bamberg", 49.89, 10.89),
         ("Bayreuth", 49.93, 11.58), ("Eichstätt", 48.89, 11.18), ("Erlangen", 49.60, 11.01), ("München", 48.15, 11.58), ("Passau", 48.57, 13.45),
         ("Regensburg", 49.00, 12.10), ("Würzburg", 49.79, 9.93), ("Berlin", 52.51, 13.33), ("Potsdam", 52.40, 13.07), ("Bremen", 53.11, 8.85),
         ("Hamburg", 53.55, 9.99), ("Darmstadt", 49.88, 8.66), ("Gießen", 50.59, 8.68), ("Kassel", 51.31, 9.48), ("Marburg", 50.81, 8.77),
         ("Greifswald", 54.09, 13.37), ("Rostock", 54.09, 12.11), ("Braunschweig", 52.27, 10.53), ("Clausthal", 51.81, 10.34), ("Göttingen", 51.54, 9.94),
         ("Hannover", 52.38, 9.72), ("Hildesheim", 52.15, 9.95), ("Lüneburg", 53.23, 10.41), ("Oldenburg", 53.15, 8.18), ("Osnabrück", 52.28, 8.03),
         ("Vechta", 52.73, 8.29), ("Aachen", 50.78, 6.07), ("Bielefeld", 52.04, 8.50), ("Bochum", 51.45, 7.26), ("Bonn", 50.73, 7.09),
         ("Dortmund", 51.49, 7.41), ("Duisburg-Essen", 51.46, 7.01), ("Düsseldorf", 51.19, 6.79), ("Hagen", 51.36, 7.47), ("Köln", 50.93, 6.93),
         ("Münster", 51.96, 7.61), ("Paderborn", 51.71, 8.77), ("Siegen", 50.91, 8.02), ("Witten", 51.44, 7.35), ("Wuppertal", 51.26, 7.15),
         ("Kaiserslautern", 49.43, 7.75), ("Koblenz", 50.36, 7.59), ("Mainz", 49.99, 8.24), ("Speyer", 49.32, 8.43), ("Trier", 49.75, 6.69),
         ("Saarlandes", 49.26, 7.05), ("Chemnitz", 50.81, 12.93), ("Dresden", 51.03, 13.73), ("Freiberg", 50.92, 13.34), ("Leipzig", 51.34, 12.37),
         ("Halle", 51.50, 11.97), ("Magdeburg", 52.14, 11.64), ("Flensburg", 54.78, 9.45), ("Kiel", 54.35, 10.12), ("Lübeck", 53.83, 10.71),
         ("Erfurt", 50.98, 11.03), ("Ilmenau", 50.68, 10.93), ("Jena", 50.93, 11.59), ("Weimar", 50.98, 11.33),
         ("Luxembourg", 49.50, 5.95), ("Wien", 48.21, 16.37), ("Graz", 47.07, 15.45), ("Innsbruck", 47.26, 11.39), ("Salzburg", 47.79, 13.05), ("Leoben", 47.38, 15.09),
         ("Linz", 48.34, 14.32), ("Klagenfurt", 46.62, 14.27), ("Krems", 48.41, 15.61), ("Zürich", 47.38, 8.54), ("Lausanne", 46.52, 6.57),
         ("Basel", 47.56, 7.59), ("Bern", 46.95, 7.44), ("St. Gallen", 47.43, 9.38), ("Genève", 46.20, 6.14), ("Neuchâtel", 46.99, 6.94),
         ("Luzern", 47.05, 8.31), ("Lugano", 46.01, 8.96), ("Svizzera italiana", 46.01, 8.96)]


R = 5  # dot radius (no outline: the colour is the information)
MIN_DIST = 12  # smallest distance between two dot centres
# research institutes shown on both status pages (same dots, only the colours differ); each page gives them its own source and status
INSTITUTES = ["MPI für Informatik (MPI-INF)", "MPI für Softwaresysteme (MPI-SWS)", "MPI für Sicherheit und Privatsphäre (MPI-SP)", "MPI für Intelligente Systeme (MPI-IS)",
              "Max-Planck-Gesellschaft", "CISPA Helmholtz-Zentrum", "Hasso-Plattner-Institut (HPI)", "Fraunhofer-Gesellschaft", "Leibniz-Gemeinschaft",
              "Helmholtz-Gemeinschaft", "Forschungszentrum Jülich", "DESY", "DFKI", "Weizenbaum-Institut", "Paul Scherrer Institut (CH)", "Empa, WSL, Eawag (CH)", "ISTA (AT)"]


def locate(name):
    return next(((la, lo) for key, la, lo in PLACE if key in name), None)


STATE_CODE = {"Baden-Württemberg": "BW", "Bayern": "BY", "Berlin": "BE", "Brandenburg": "BB", "Bremen": "HB", "Hamburg": "HH", "Hessen": "HE",
              "Mecklenburg-Vorpommern": "MV", "Niedersachsen": "NI", "Nordrhein-Westfalen": "NRW", "Rheinland-Pfalz": "RP", "Saarland": "SL",
              "Sachsen": "SN", "Sachsen-Anhalt": "ST", "Schleswig-Holstein": "SH", "Thüringen": "TH"}
K = math.cos(math.radians(48.5))
xy = lambda lat, lon: ((lon - 5.8) * K * 100, (55.1 - lat) * 100)  # same projection as regions.json


def group(code):
    """Map region of a state code: every German state on its own, Austria, Switzerland and Luxembourg as one region each."""
    return code[:2] if code[:3] in ("AT-", "CH-") else code


def inside(pt, d):
    """Ray casting over the subpaths of an SVG path made only of M/L/Z with integer points."""
    x, y = pt
    hit = False
    for sub in re.split(r"[MZ]", d):
        p = [tuple(map(int, q.split(","))) for q in re.findall(r"-?\d+,-?\d+", sub)]
        for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
    return hit


def assign_regions(rows):
    """r["reg"]: German universities by their state heading, AT / CH by country, research institutes by the state their headquarters lies in."""
    regions = json.load(open("regions.json", encoding="utf-8"))
    for r in rows:
        if r["country"] != "DE":
            r["reg"] = r["country"]
        elif r["region"] != "research institute":
            r["reg"] = STATE_CODE.get(r["region"], "")
        else:
            pos = locate(r["name"])
            r["reg"] = next((c for c, d in regions.items() if c in STATE_CODE.values() and pos and inside(xy(*pos), d)), "")
            if not r["reg"]:
                print("no state for", r["name"], file=sys.stderr)


def inst_cell(r):
    """First table column of every page: (label 'Institution (state)', sort key country - state - institution)."""
    label = r["name"] if not r.get("reg") or r["name"].endswith(f'({r["reg"]})') else f'{r["name"]} ({r["reg"]})'  # "ISTA (AT)" already says it
    return label, f'{r["country"]}|{r.get("reg", "")}|{r["name"]}'.lower()


def dot(rows, pos, i, title, cls=""):
    """One dot: a circle, or a square of the same size for a research institute."""
    x, y = pos[i]
    if rows[i]["region"] == "research institute":
        return f'<rect class="d i{cls}" data-i="{i}" x="{x - R:.1f}" y="{y - R:.1f}" width="{2 * R}" height="{2 * R}" rx="2"><title>{html.escape(title)}</title></rect>'
    return f'<circle class="d{cls}" data-i="{i}" cx="{x:.1f}" cy="{y:.1f}" r="{R}"><title>{html.escape(title)}</title></circle>'


def layout(rows):
    """State borders (regions.json, neutral) and a position per institution: (viewBox, land paths, {row index: [x, y]}).
    Several institutions in one city are spread on a small ring."""
    regions = json.load(open("regions.json", encoding="utf-8"))
    pts = [tuple(map(int, q.split(","))) for d in regions.values() for q in re.findall(r"-?\d+,-?\d+", d)]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    vb = f"{min(xs) - 5} {min(ys) - 5} {max(xs) - min(xs) + 10} {max(ys) - min(ys) + 10}"
    merged = {}
    for c, d in regions.items():
        merged[group(c)] = merged.get(group(c), "") + d
    land = "".join(f'<path class="t" data-reg="{c}" d="{d}"><title></title></path>' for c, d in merged.items())
    groups = {}
    for i, r in enumerate(rows):
        pos = locate(r["name"])
        if pos:
            groups.setdefault(pos, []).append(i)
        else:
            print("no location for", r["name"], file=sys.stderr)
    pos = {}  # row index -> [x, y]; start on a small ring around the city, then push apart until every pair is at least MIN_DIST away
    for p, idx in groups.items():
        cx, cy = xy(*p)
        for j, i in enumerate(idx):
            a = 2 * math.pi * j / len(idx) - math.pi / 2
            off = 0 if len(idx) == 1 else 5 + len(idx)
            pos[i] = [cx + off * math.cos(a), cy + off * math.sin(a)]
    ids = sorted(pos)
    for _ in range(300):
        moved = False
        for n, i in enumerate(ids):
            for j in ids[n + 1:]:
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy)
                if d < MIN_DIST:
                    dx, dy, d = (dx, dy, d) if d > 1e-6 else (1.0, 0.0, 1.0)
                    push = (MIN_DIST - d) / 2 + 0.05
                    pos[i][0] -= dx / d * push; pos[i][1] -= dy / d * push
                    pos[j][0] += dx / d * push; pos[j][1] += dy / d * push
                    moved = True
        if not moved:
            break
    return vb, land, pos


def map_html(rows, label):
    """Land plus one dot per institution, coloured by status. Research institutes sit at their headquarters and are drawn as squares."""
    vb, land, pos = layout(rows)
    dots = [dot(rows, pos, i, f'{rows[i]["name"]}: {label[rows[i]["st"]]}', " " + rows[i]["st"]) for i in sorted(pos)]
    return f'<svg class="map" viewBox="{vb}" xmlns="http://www.w3.org/2000/svg">{land}{"".join(dots)}</svg>'


def dots_map(rows):
    """Same land and dot positions as map_html, but colourless: the page colours the dots itself (class d, data-i = row index)."""
    vb, land, pos = layout(rows)
    dots = "".join(dot(rows, pos, i, rows[i]["name"]) for i in sorted(pos))
    return f'<svg class="map" viewBox="{vb}" xmlns="http://www.w3.org/2000/svg">{land}{dots}</svg>'


BLOCK = re.compile(r"robots\.txt|anti-bot|anubis|captcha|challenge", re.I)  # the site asks not to be scraped: shown black instead of red


def render(title, rows, label, rank, scraped, intro, map_note, num_head, links, groups=("DE", "AT", "CH", "LU")):
    """Whole page. `label`/`rank`: status -> text / sort position; `links`: html for the navigation line."""
    assign_regions(rows)
    for r in rows:
        if "blocked" in label and r["st"] in ("failing", "none", "zero") and BLOCK.search(r["note"]):
            r["st"] = "blocked"
    count = {c: {k: sum(1 for r in rows if r["country"] == c and r["st"] == k) for k in label} for c in groups}
    summary = "".join(f"<li><b>{c}</b>: {sum(v.values())} listed &ndash; " + ", ".join(f"{v[k]} {label[k]}" for k in label) + "</li>" for c, v in count.items())
    body = "\n".join(
        f'<tr class="{r["st"]}" data-i="{i}" data-st="{r["st"]}" data-reg="{r["reg"]}" data-cc="{r["country"]}" data-rank="{rank[r["st"]]}"><td data-sort="{html.escape(inst_cell(r)[1])}">{html.escape(inst_cell(r)[0])}</td>'
        f'<td>{html.escape(r["key"])}</td><td>{label[r["st"]]}</td><td class="num">{r["n"]}</td><td>{html.escape(r["note"])}</td></tr>' for i, r in enumerate(rows))
    problems = [k for k in label if rank[k] >= 2]
    ok = [k for k in label if rank[k] < 2]
    css = """<style>
  :root { --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#ddd; --head:#f3f3f3; --link:#0645ad; --ok:#e6f4ea; --zero:#fff8e1; --bad:#fdecea; }
  @media (prefers-color-scheme: dark) { :root { --bg:#151515; --fg:#e6e6e6; --muted:#999; --line:#333; --head:#202020; --link:#7ab0ff; --ok:#16301f; --zero:#33290f; --bad:#3a1a18; } }
  body { background:var(--bg); color:var(--fg); font:14px/1.4 system-ui,sans-serif; margin:1rem; } a { color:var(--link); }
  table { border-collapse:collapse; width:100%; } th,td { border-bottom:1px solid var(--line); padding:.3rem .5rem; text-align:left; vertical-align:top; }
  th { background:var(--head); cursor:pointer; } td.num { text-align:right; } .muted { color:var(--muted); } label { margin-right:1rem; }
  .cols { display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; align-items:start; } .left { position:sticky; top:1rem; } .right { min-width:0; } .cols .map { max-width:none; margin:0; max-height:calc(100vh - 2rem); } @media (max-width:900px) { .cols { display:block; } .left { position:static; } }
  .map { display:block; max-width:34rem; width:100%; margin:.5rem 0; }
  .t { fill:var(--head); stroke:var(--bg); stroke-width:1.5; } .d { stroke:none; } .d.ads { fill:#2e9d4f; } .d.zero, .d.partial { fill:#e0a526; } .d.failing, .d.none { fill:#d64545; } .d.blocked { fill:#000; stroke:#888; stroke-width:1; } .t { cursor:pointer; } .t:hover { fill:color-mix(in srgb, var(--link) 25%, var(--head)); } .t.sel { fill:color-mix(in srgb, var(--link) 45%, var(--head)); }
  #sel { margin-left:1rem; }
  tr.ads td:nth-child(3) { background:var(--ok); } tr.zero td:nth-child(3), tr.partial td:nth-child(3) { background:var(--zero); } tr.failing td:nth-child(3), tr.none td:nth-child(3) { background:var(--bad); } tr.blocked td:nth-child(3) { background:#000; color:#fff; }
</style>"""
    script = """<script>
  const f = () => { const p = document.getElementById("prob").checked, c = document.getElementById("cc").value;
    document.querySelectorAll("#t tbody tr").forEach(r => { r.hidden = (p && !PROBLEMS.includes(r.dataset.st)) || (c && r.dataset.cc !== c) || (sel && r.dataset.reg !== sel); });
    document.querySelectorAll("#t tbody tr").forEach(r => { const d = document.querySelector(`.d[data-i="${r.dataset.i}"]`); if (d) d.style.display = r.hidden ? "none" : ""; }); };
  let sel = "";
  const tot = {};
  document.querySelectorAll("#t tbody tr").forEach(r => tot[r.dataset.reg] = (tot[r.dataset.reg] || 0) + 1);
  document.querySelectorAll(".t").forEach(t => {
    t.firstChild.textContent = `${t.dataset.reg}: ${tot[t.dataset.reg] || 0} institutions (click to filter)`;
    t.onclick = () => { sel = sel === t.dataset.reg ? "" : t.dataset.reg; mark(); };
  });
  const mark = () => { document.querySelectorAll(".t").forEach(t => t.classList.toggle("sel", t.dataset.reg === sel));
    document.getElementById("sel").innerHTML = sel ? `region ${sel} &ndash; <a href="#" id="clr">show all</a>` : "";
    if (sel) document.getElementById("clr").onclick = e => { e.preventDefault(); sel = ""; mark(); };
    f(); };
  mark();
  const body = document.querySelector("#t tbody"); let col = -1, asc = true;
  document.querySelectorAll("#t th").forEach((th, i) => th.onclick = () => {
    asc = col === i ? !asc : true; col = i;
    const key = r => i === 2 ? +r.dataset.rank : i === 3 ? (r.cells[3].textContent === "" ? -1 : +r.cells[3].textContent) : (r.cells[i].dataset.sort || r.cells[i].textContent.toLowerCase());
    [...body.rows].sort((a, b) => (key(a) > key(b) ? 1 : key(a) < key(b) ? -1 : 0) * (asc ? 1 : -1)).forEach(r => body.appendChild(r));
    document.querySelectorAll("#t th").forEach(h => h.textContent = h.textContent.replace(/ [▲▼]$/, "")); th.textContent += asc ? " ▲" : " ▼";
  });
  document.getElementById("prob").onchange = f; document.getElementById("cc").onchange = f;
</script>"""
    countries = "".join(f"<option>{c}</option>" for c in groups)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{css}
<div class="cols"><div class="left">{map_html(rows, label)}</div><div class="right">
<h1>{title}</h1>
<p>{links} &middot; scraped {html.escape(scraped)}</p>
<ul>{summary}</ul>
{intro}
<p class="muted">{map_note}</p>
<div><label><input type="checkbox" id="prob"> only show problems ({" / ".join(label[k] for k in problems)})</label>
<select id="cc"><option value="">all countries</option>{countries}</select><span id="sel"></span></div>
<table id="t"><thead><tr title="click a header to sort"><th>Institution (city, state)</th><th>Source</th><th>Status</th><th>{num_head}</th><th>Note</th></tr></thead>
<tbody>
{body}
</tbody></table>
</div></div>
{script.replace("PROBLEMS", json.dumps(problems))}</html>
""", count
