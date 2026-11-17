"""Render professors.json to a static output/professors.html (search + university filter, sortable). Usage (from the project root): python3 -I profs/professors_build.py"""
import html
import json
import math
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]  # python -I does not add the script's folder; common/ lives in the project root
from common.cs import CS, bold
from cs_filter import cs_hit

data = json.load(open("professors.json", encoding="utf-8"))
profs = sorted(data["professors"], key=lambda p: (p["university"], p["faculty"], p["unit"], p["name"].split()[-1] if p["name"] else ""))
PL = {(r["university"], r["name"]): r for r in json.load(open("professors_pl.json", encoding="utf-8"))["professors"]} if os.path.exists("professors_pl.json") else {}  # from dblp_pl.py
unis = sorted({p["university"] for p in profs})
e = html.escape
def pl_attrs(p):
    r = PL.get((p["university"], p["name"]))
    return f' data-years="{e(json.dumps(r["years"]))}" data-amb="{int(r["ambiguous"])}" data-tip="{e(" | ".join(r["sample"]))}"' if r else ""


def pl_cell(p):
    r = PL.get((p["university"], p["name"]))
    if not r:
        return ""
    tip = e(" | ".join(r["sample"]) + (" (name shared by several DBLP people: check)" if r["ambiguous"] else ""))
    return f'{r["papers"]}{"?" if r["ambiguous"] else ""}'

# university -> city; CITY holds (lat, lon) used for the map dots (one dot per city; same projection as jobs/jobs_regions.py)
CITY = {"Aachen": (50.779, 6.065), "Augsburg": (48.333, 10.898), "Bamberg": (49.892, 10.885), "Basel": (47.559, 7.588), "Berlin": (52.513, 13.327),
        "Bern": (46.950, 7.439), "Bielefeld": (52.038, 8.495), "Bochum": (51.445, 7.262), "Bonn": (50.727, 7.088), "Braunschweig": (52.274, 10.526),
        "Bremen": (53.107, 8.853), "Chemnitz": (50.813, 12.929), "Clausthal": (51.808, 10.340), "Cottbus": (51.767, 14.327), "Darmstadt": (49.877, 8.656),
        "Dortmund": (51.493, 7.414), "Dresden": (51.027, 13.726), "Düsseldorf": (51.190, 6.794), "Essen": (51.464, 7.005), "Frankfurt": (50.128, 8.667),
        "Freiburg": (48.000, 7.848), "Fribourg": (46.793, 7.156), "Genève": (46.195, 6.144), "Gießen": (50.587, 8.678), "Göttingen": (51.540, 9.938),
        "Graz": (47.069, 15.450), "Greifswald": (54.093, 13.374), "Halle": (51.495, 11.970), "Hamburg": (53.567, 9.985), "Hannover": (52.382, 9.718),
        "Heidelberg": (49.417, 8.670), "Ilmenau": (50.683, 10.933), "Innsbruck": (47.264, 11.385), "Jena": (50.933, 11.588), "Kaiserslautern": (49.425, 7.750),
        "Karlsruhe": (49.007, 8.404), "Kassel": (51.313, 9.480), "Kiel": (54.347, 10.122), "Klosterneuburg": (48.309, 16.257), "Koblenz": (50.360, 7.590),
        "Köln": (50.928, 6.929), "Lausanne": (46.519, 6.566), "Linz": (48.337, 14.319), "Lugano": (46.011, 8.958), "Lübeck": (53.834, 10.708),
        "Mainz": (49.993, 8.239), "Mannheim": (49.484, 8.463), "Marburg": (50.810, 8.774), "München": (48.200, 11.620), "Münster": (51.963, 7.610),
        "Neuchâtel": (46.993, 6.938), "Oldenburg": (53.147, 8.177), "Osnabrück": (52.283, 8.025), "Paderborn": (51.708, 8.770), "Passau": (48.567, 13.451),
        "Potsdam": (52.400, 13.070), "Regensburg": (49.000, 12.096), "Rostock": (54.088, 12.107), "Saarbrücken": (49.258, 7.046), "Salzburg": (47.794, 13.046),
        "St. Gallen": (47.433, 9.375), "Stuttgart": (48.745, 9.105), "Trier": (49.747, 6.689), "Tübingen": (48.524, 9.056), "Ulm": (48.422, 9.950),
        "Wien": (48.205, 16.365), "Würzburg": (49.787, 9.934), "Zürich": (47.375, 8.545)}
UNI_CITY = {"BTU Cottbus-Senftenberg": "Cottbus", "CISPA": "Saarbrücken", "EPFL Lausanne": "Lausanne", "ETH Zürich": "Zürich", "FU Berlin": "Berlin",
            "Goethe-Universität Frankfurt": "Frankfurt", "Hasso-Plattner-Institut": "Potsdam", "ISTA": "Klosterneuburg", "JKU Linz": "Linz", "KIT": "Karlsruhe",
            "LMU München": "München", "Leibniz Universität Hannover": "Hannover", "MPI-INF": "Saarbrücken", "MPI-SP": "Bochum", "MPI-SWS": "Saarbrücken",  # MPI-SWS also has a Kaiserslautern site
            "RPTU Kaiserslautern-Landau": "Kaiserslautern", "RWTH Aachen": "Aachen", "Ruhr-Universität Bochum": "Bochum", "TU Berlin": "Berlin",
            "TU Braunschweig": "Braunschweig", "TU Chemnitz": "Chemnitz", "TU Clausthal": "Clausthal", "TU Darmstadt": "Darmstadt", "TU Dortmund": "Dortmund",
            "TU Dresden": "Dresden", "TU Graz": "Graz", "TU Hamburg": "Hamburg", "TU Ilmenau": "Ilmenau", "TU München": "München", "TU Wien": "Wien",
            "Università della Svizzera italiana (Lugano)": "Lugano", "Universität Augsburg": "Augsburg", "Universität Bamberg": "Bamberg", "Universität Basel": "Basel",
            "Universität Bern": "Bern", "Universität Bielefeld": "Bielefeld", "Universität Bonn": "Bonn", "Universität Bremen": "Bremen",
            "Universität Duisburg-Essen": "Essen", "Universität Düsseldorf": "Düsseldorf", "Universität Freiburg": "Freiburg", "Universität Freiburg (Fribourg)": "Fribourg",
            "Universität Gießen": "Gießen", "Universität Greifswald": "Greifswald", "Universität Göttingen": "Göttingen", "Universität Halle": "Halle",
            "Universität Hamburg": "Hamburg", "Universität Heidelberg": "Heidelberg", "Universität Innsbruck": "Innsbruck", "Universität Jena": "Jena",
            "Universität Kassel": "Kassel", "Universität Kiel": "Kiel", "Universität Koblenz": "Koblenz", "Universität Köln": "Köln", "Universität Mainz": "Mainz",
            "Universität Mannheim": "Mannheim", "Universität Marburg": "Marburg", "Universität Münster": "Münster", "Universität Oldenburg": "Oldenburg",
            "Universität Osnabrück": "Osnabrück", "Universität Paderborn": "Paderborn", "Universität Passau": "Passau", "Universität Potsdam": "Potsdam",
            "Universität Regensburg": "Regensburg", "Universität Rostock": "Rostock", "Universität Salzburg": "Salzburg", "Universität St. Gallen": "St. Gallen",
            "Universität Stuttgart": "Stuttgart", "Universität Trier": "Trier", "Universität Tübingen": "Tübingen", "Universität Ulm": "Ulm", "Universität Wien": "Wien",
            "Universität Würzburg": "Würzburg", "Universität Zürich": "Zürich", "Universität des Saarlandes": "Saarbrücken", "Universität zu Lübeck": "Lübeck",
            "Université de Genève": "Genève", "Université de Neuchâtel": "Neuchâtel"}
for u in unis:
    if u not in UNI_CITY:
        print("no city for", u, "(not shown on the map)", file=sys.stderr)


def map_html():
    """State borders from regions.json (jobs/jobs_regions.py) plus one dot per city; the JS sizes the dots by the professors passing the filters."""
    k = math.cos(math.radians(48.5))
    xy = lambda lat, lon: ((lon - 5.8) * k * 100, (55.1 - lat) * 100)  # same projection as regions.json
    regions = json.load(open("regions.json", encoding="utf-8"))
    pts = [tuple(map(int, q.split(","))) for d in regions.values() for q in re.findall(r"-?\d+,-?\d+", d)]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    vb = f"{min(xs) - 5} {min(ys) - 5} {max(xs) - min(xs) + 10} {max(ys) - min(ys) + 10}"
    land = "".join(f'<path class="t" d="{d}"/>' for d in regions.values())
    dots = "".join(f'<circle class="d" data-c="{e(c)}" cx="{xy(*CITY[c])[0]:.0f}" cy="{xy(*CITY[c])[1]:.0f}" r="0"><title></title></circle>' for c in sorted(set(UNI_CITY.values())))
    return f'<svg class="map" viewBox="{vb}" xmlns="http://www.w3.org/2000/svg">{land}{dots}</svg>'


def hl(text):
    return bold(text, CS)


rows = "\n".join(
    f'<tr data-cs="{int(cs_hit(p))}" data-pl="{int((p["university"], p["name"]) in PL)}"{pl_attrs(p)} data-u="{e(p["university"])}" data-c="{e(UNI_CITY.get(p["university"], ""))}"><td>{e(p["university"])}</td><td>{e(p["faculty"])}</td><td>{hl(p["unit"])}</td>'
    f'<td><a href="{e(p["url"])}" target="_blank" rel="noopener">{e(p["name"])}</a></td><td>{hl(p["topic"])}</td><td>{pl_cell(p)}</td></tr>' for p in profs)
options = "".join(f"<option>{e(u)}</option>" for u in unis)
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Professors</title>
<style>
  :root {{ --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#ddd; --head:#f3f3f3; --link:#0645ad; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#151515; --fg:#e6e6e6; --muted:#999; --line:#333; --head:#202020; --link:#7ab0ff; }} }}
  body {{ margin:0; padding:1rem; background:var(--bg); color:var(--fg); font:14px/1.4 system-ui,sans-serif; }}
  h1 {{ font-size:1.2rem; margin:0 0 .5rem; }} .muted {{ color:var(--muted); }} a {{ color:var(--link); }}
  input,select {{ font:inherit; padding:.25rem .4rem; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:4px; margin:0; }}
  .bar {{ display:flex; flex-wrap:wrap; align-items:center; gap:.4rem .9rem; }}
  .seg {{ display:inline-flex; border:1px solid var(--line); border-radius:6px; overflow:hidden; }}  /* radio group as joined pills; the inputs stay for the JS but are hidden */
  .seg label {{ position:relative; padding:.25rem .65rem; cursor:pointer; border-left:1px solid var(--line); user-select:none; }}
  .seg label:first-child {{ border-left:0; }} .seg label:hover {{ background:var(--head); }}
  .seg input {{ position:absolute; opacity:0; pointer-events:none; }}
  .seg label:has(input:checked) {{ background:var(--link); color:var(--bg); }} .seg label:has(input:focus-visible) {{ outline:2px solid var(--link); outline-offset:-2px; }}
  .wrap {{ overflow-x:auto; margin-top:.75rem; }} table {{ border-collapse:collapse; width:100%; }}
  .map {{ display:block; max-width:26rem; width:100%; margin:.6rem 0 0; }} .map .t {{ fill:var(--head); stroke:var(--line); stroke-width:1; }}
  .map .d {{ fill:var(--link); fill-opacity:.55; stroke:var(--link); stroke-width:1; cursor:pointer; }} .map .d.on {{ fill-opacity:.9; stroke:var(--fg); stroke-width:2; }}
  th,td {{ text-align:left; padding:.35rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:var(--head); white-space:nowrap; cursor:pointer; }} th.s::after {{ content:" ▲"; }} th.s.r::after {{ content:" ▼"; }} tr.hide {{ display:none; }}
</style></head><body>
<h1>Professors at selected German universities</h1>
<div class="bar"><input id="q" type="search" placeholder="search name, topic, unit …" size="28">
<span class="seg"><label><input type="radio" name="m" value="all">all</label><label><input type="radio" name="m" value="cs" checked>CS-related</label><label><input type="radio" name="m" value="pl">PL-related</label></span>
<span class="muted">PL papers, last</span><span class="seg"><label><input type="radio" name="y" value="5">5</label><label><input type="radio" name="y" value="10">10</label><label><input type="radio" name="y" value="15">15</label><label><input type="radio" name="y" value="0" checked>all</label></span><span class="muted">years</span>
<select id="u"><option value="">all universities</option>{options}</select><span id="city" class="muted" hidden></span><span id="n" class="muted"></span></div>
{map_html()}
<div class="wrap"><table>
<thead><tr title="click a header to sort"><th>University</th><th>Faculty</th><th>Unit</th><th>Name</th><th>Topic / chair</th><th data-num title="papers in PACMPL, ESOP, ECOOP or TOPLAS (DBLP)">PL papers</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
<p class="muted">Scraped {e(data["scraped"])} from the universities' public staff pages; {len(profs)} professors. Coverage is per faculty, not whole universities:
only some faculties are included, and some pages give no topic or unit (shown empty). CS-related = a computer-science faculty, or a CS keyword (bold) in the topic or unit; broad faculties like electrical engineering or Math + CS are judged by topic only. PL-related = at least two papers (within the selected years) in PACMPL, ESOP, ECOOP or TOPLAS according to the DBLP dump, matched by name (a "?" marks names DBLP lists for several people; hover for titles). <a href="index.html">&larr; overview</a>{'' if os.environ.get('PUBLIC') else ' &middot; <a href="jobs.html">professorship ads</a>'}</p>
<script>
const PL_MIN = 2;  // "PL-related" = at least this many PL papers inside the selected window
let city = "";  // set by clicking a map dot
const dots = [...document.querySelectorAll(".map .d")], cl = document.getElementById("city");
const tb = document.querySelector("tbody"), rows = [...tb.rows], ths = [...document.querySelectorAll("th")];
function f() {{
  const q = document.getElementById("q").value.toLowerCase(), cnt = {{}}, u = document.getElementById("u").value, m = document.querySelector('input[name=m]:checked').value, w = +document.querySelector('input[name=y]:checked').value, cur = new Date().getFullYear(); let n = 0;
  for (const r of rows) {{
    if (r.dataset.years) {{  // PL papers inside the window: the last w years including this one (0 = all)
      const k = Object.entries(JSON.parse(r.dataset.years)).reduce((s, [y, c]) => s + (!w || +y > cur - w ? c : 0), 0), c = r.cells[5];
      r.dataset.k = k; c.textContent = k ? k + (r.dataset.amb === "1" ? "?" : "") : ""; c.title = r.dataset.tip + (r.dataset.amb === "1" ? " (name shared by several DBLP people: check)" : "");
    }} else r.dataset.k = 0;
    const hide = (m === "cs" && r.dataset.cs === "0") || (m === "pl" && +r.dataset.k < PL_MIN) || (u && r.dataset.u !== u) || (city && r.dataset.c !== city) || (q && !r.textContent.toLowerCase().includes(q)); r.classList.toggle("hide", hide); if (!hide) {{ n++; const c = cnt[r.dataset.c] ||= {{}}; c[r.dataset.u] = (c[r.dataset.u] || 0) + 1; }} }}
  for (const d of dots) {{  // one dot per city, area ~ number of professors passing the filters
    const t = Object.entries(cnt[d.dataset.c] || {{}}), s = t.reduce((a, [, x]) => a + x, 0);
    d.setAttribute("r", s ? 4 + 3 * Math.sqrt(s) : 0); d.classList.toggle("on", city === d.dataset.c);
    d.firstChild.textContent = d.dataset.c + ": " + s + (t.length > 1 || (t.length && t[0][0] !== d.dataset.c) ? " (" + t.map(([k, x]) => k + " " + x).join(", ") + ")" : "");
  }}
  cl.hidden = !city; cl.textContent = city ? "city: " + city + " ✕" : "";
  document.getElementById("n").textContent = `${{n}} of ${{rows.length}}`;
  sortRows();
}}
function sortRows() {{  // sort by the header marked "s" (class "r" = descending); re-run after the radios change the PL counts
  const th = document.querySelector("th.s"); if (!th) return;
  const i = ths.indexOf(th), rev = th.classList.contains("r"), num = x => parseFloat(x.cells[i].textContent) || 0;  // empty cell = 0; "5?" = 5
  rows.sort((a, b) => (th.hasAttribute("data-num") ? num(a) - num(b) : a.cells[i].textContent.localeCompare(b.cells[i].textContent)) * (rev ? -1 : 1)).forEach(r => tb.appendChild(r));
}}
ths.forEach(th => th.onclick = () => {{
  const rev = th.classList.contains("s") && !th.classList.contains("r");
  ths.forEach(x => x.classList.remove("s", "r")); th.classList.add("s"); if (rev) th.classList.add("r");
  sortRows();
}});
dots.forEach(d => d.onclick = () => {{ city = city === d.dataset.c ? "" : d.dataset.c; f(); }}); cl.style.cursor = "pointer"; cl.onclick = () => {{ city = ""; f(); }};
document.getElementById("q").oninput = f; document.getElementById("u").onchange = f; document.querySelectorAll("input[name=m], input[name=y]").forEach(x => x.onchange = f); f();
</script></body></html>"""
os.makedirs("output", exist_ok=True)
open("output/professors.html", "w", encoding="utf-8").write(page)
print(len(profs), "professors written to output/professors.html")
