"""Render professors.json to a static output/professors.html (search + university filter, sortable). Usage (from the project root): python3 -I profs/professors_build.py"""
import html
import json
import math
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]  # python -I does not add the script's folder; common/ lives in the project root
from common.cs import CS, bold
from roles import ROLES, RANK
from cs_filter import cs_hit

data = json.load(open("professors.json", encoding="utf-8"))


def tidy(ps):
    """Display-only clean-up of the unit column (professors.json stays as scraped): blank a faculty that is just the institute's own name (MPI, CISPA); drop a unit that only repeats the role ('Faculty') or the topic,
    turn Constructor's job titles ('Assistant Professor of Computer Science') into the field, and unify spellings of one unit within a university."""
    norm = lambda t: re.sub(r"\W+", " ", t.lower()).strip()
    spell = {}
    for p in ps:
        u = p["unit"].replace("Institute for Machine Learning", "Institut für Machine Learning").replace("It-Sicherheit", "IT-Sicherheit")
        if re.match(r"Max Planck Institute|CISPA Helmholtz Center", p["faculty"]):  # the institute's own name, already the first column
            p["faculty"] = ""
        p["unit"] = re.sub(r"^(?:Assistant |Associate )?Professor of ", "", u)
        if p["unit"] and norm(p["unit"]) in (norm(p.get("role", "")), norm(p["topic"])):
            p["unit"] = ""
        spell.setdefault((p["university"], norm(p["unit"])), []).append(p["unit"])
    for p in ps:  # 'Institut für IT-Sicherheit' / 'It-Sicherheit': the commonest, then the spelling with more capitals
        c = spell[(p["university"], norm(p["unit"]))]
        p["unit"] = max(set(c), key=lambda x: (c.count(x), sum(ch.isupper() for ch in x))) if p["unit"] else ""


INSTITUTES = {"CISPA": r"CISPA", "MPI-INF": r"MPI.INF|Institute for Informatics", "MPI-SP": r"MPI.SP|Security and Privacy", "MPI-SWS": r"MPI.SWS|Software Systems"}


def merge_joint(ps):
    """Someone listed by an institute (CISPA, MPI) and by a university (joint appointment) is one row: the university's, with 'also <institute>' in the unit
    unless the university page already names the institute. Only institute/university pairs are merged: a name shared by two universities may be two people."""
    name = lambda p: re.sub(r"\W+", " ", re.sub(r"\b(?:prof|dr|apl|pd|ing|habil|dipl)\b\.?", "", p["name"].lower())).strip()
    uni = {}
    for p in ps:
        if p["university"] not in INSTITUTES:
            uni.setdefault(name(p), []).append(p)
    out = []
    for p in ps:
        m = uni.get(name(p)) if p["university"] in INSTITUTES else None
        if m and len(m) == 1:
            if not re.search(INSTITUTES[p["university"]], m[0]["unit"]):
                m[0]["unit"] += ("; " if m[0]["unit"] else "") + "also " + p["university"]
            continue
        out.append(p)
    return out


tidy(data["professors"])
data["professors"] = merge_joint(data["professors"])
profs = sorted((p for p in data["professors"] if cs_hit(p)), key=lambda p: (p["university"], p["faculty"], p["unit"], p["name"].split()[-1] if p["name"] else ""))
PL = {(r["university"], r["name"]): r for r in json.load(open("professors_pl.json", encoding="utf-8"))["professors"]} if os.path.exists("professors_pl.json") else {}  # from dblp_pl.py
CSR = {(r["university"], r["name"]): r for r in json.load(open("professors_csr.json", encoding="utf-8"))["professors"]} if os.path.exists("professors_csr.json") else {}  # from csr_papers.py
unis = sorted({p["university"] for p in profs})
e = html.escape
def pl_attrs(p):
    r = PL.get((p["university"], p["name"]))
    return f' data-years="{e(json.dumps(r["years"]))}" data-amb="{int(r["ambiguous"])}" data-tip="{e(" | ".join(r["sample"]))}"' if r else ""


def csr_attrs(p):
    r = CSR.get((p["university"], p["name"]))
    return f' data-cyears="{e(json.dumps(r["years"]))}" data-camb="{int(r["ambiguous"])}" data-ctip="{e("CSranked venues: " + ", ".join(r["sample"]))}"' if r else ""


def pl_cell(p):
    r = PL.get((p["university"], p["name"]))
    if not r:
        return ""
    tip = e(" | ".join(r["sample"]) + (" (name shared by several DBLP people: check)" if r["ambiguous"] else ""))
    return f'{r["papers"]}{"?" if r["ambiguous"] else ""}'

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jobs"))
from status_lib import dots_map, inst_cell, assign_regions
import profs_status  # the institutions of the status page: one dot each, at the same place
INST = {uni: i for i, r in enumerate(profs_status.rows) for uni in [profs_status.SRC.get(r["name"], ("", ""))[0]] if uni}  # university as in professors.json -> dot index
for u in unis:
    if u not in INST:
        print("no dot for", u, file=sys.stderr)


assign_regions(profs_status.rows)
def ucell(u):
    return inst_cell(profs_status.rows[INST[u]]) if u in INST else (u, "zz||" + u.lower())


def hl(text):
    return bold(text, CS)


rows = "\n".join(
    f'<tr data-cs="{int(cs_hit(p))}" data-pl="{int((p["university"], p["name"]) in PL)}"{pl_attrs(p)}{csr_attrs(p)} data-u="{e(p["university"])}" data-i="{INST.get(p["university"], "")}"><td data-sort="{e(ucell(p["university"])[1])}">{e(ucell(p["university"])[0])}</td><td>{e(p["faculty"])}</td><td>{hl(p["unit"])}</td>'
    f'<td><a href="{e(p["url"])}" target="_blank" rel="noopener">{e(p["name"])}</a></td><td data-rk="{RANK[p["role"]] if p.get("role") else len(ROLES)}">{e(p.get("role", ""))}</td><td>{hl(p["topic"])}</td><td>{pl_cell(p)}</td><td></td></tr>' for p in profs)
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
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; align-items:start; }} .left {{ position:sticky; top:1rem; }} .right {{ min-width:0; }} .cols .map {{ max-width:none; margin:0; max-height:calc(100vh - 2rem); }} @media (max-width:900px) {{ .cols {{ display:block; }} .left {{ position:static; }} }}
  .map {{ display:block; max-width:26rem; width:100%; margin:.6rem 0 0; }} .map .t {{ fill:var(--head); stroke:var(--line); stroke-width:1; }}
  .map .d {{ fill:#000; stroke:none; cursor:pointer; }} .map .d.on {{ stroke:var(--fg); stroke-width:2; }}
  th,td {{ text-align:left; padding:.35rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:var(--head); white-space:nowrap; cursor:pointer; }} th.s::after {{ content:" ▲"; }} th.s.r::after {{ content:" ▼"; }} tr.hide {{ display:none; }}
</style></head><body>
<div class="cols"><div class="left">{dots_map(profs_status.rows)}</div><div class="right">
<h1>Professors at selected German universities</h1>
<div class="bar"><input id="q" type="search" placeholder="search name, topic, unit …" size="28">
<span class="seg"><label><input type="radio" name="m" value="cs" checked>CS-related</label><label><input type="radio" name="m" value="pl">PL-related</label></span>
<span class="muted">papers, last</span><span class="seg"><label><input type="radio" name="y" value="5">5</label><label><input type="radio" name="y" value="10">10</label><label><input type="radio" name="y" value="15">15</label><label><input type="radio" name="y" value="0" checked>all</label></span><span class="muted">years</span>
<select id="u"><option value="">all universities</option>{options}</select><span id="dot" class="muted" hidden></span><span id="n" class="muted"></span></div>
<div class="wrap"><table>
<thead><tr title="click a header to sort"><th>Institution (city, state)</th><th>Faculty</th><th>Unit</th><th>Name</th><th data-rk title="position, sorted by seniority: director, professor / faculty, associate, assistant / junior, group leader, honorary / visiting / secondary">Position</th><th>Topic / chair</th><th data-num title="papers in PACMPL, ESOP, ECOOP or TOPLAS (DBLP)">PL papers</th><th data-num title="DBLP papers (at least 6 pages) in the venues CSrankings counts; the selected window applies">CSranked papers</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
<p class="muted">Scraped {e(data["scraped"])} from the universities' public staff pages; {len(profs)} professors. Only computer-science people are listed, because the scrapers read the CS departments properly and other faculties only by chance; some pages give no topic or unit (shown empty). CS-related = the faculty or unit name says Informatik / computer / software (computer-science institutes count completely); electrical engineering, business and plain mathematics faculties do not, and the topic is not used. Position = taken from the page's section or role label where it gives one (e.g. assistant professorships, honorary professorships, group leaders), otherwise guessed from the title before the name (Jun.-Prof., Assoc. Prof., Hon.-Prof., apl. ...), "Professor" means a Prof. title without a more precise rank; "Faculty" is the tenured / tenure-track faculty of a research institute (MPI, CISPA), ranked like a professor, while its research group leaders are "Group leader"; and an empty cell means the page does not say (sorted last); the column sorts by seniority. Bold keywords in topic and unit are only a hint. PL-related = at least two papers (within the selected years) in PACMPL, ESOP, ECOOP or TOPLAS according to the DBLP dump, matched by name (a "?" marks names DBLP lists for several people; hover for titles). CSranked papers = DBLP papers of at least 6 pages in the conferences and journals counted by <a href="https://csrankings.org">CSrankings</a> (all its areas, whole counts, same year window), matched by name like the PL papers; hover for the venues. A 0 means the name was found in DBLP but has no counted paper in the window; an empty cell means no DBLP author of that name was found. <a href="index.html">&larr; overview</a>{'' if os.environ.get('PUBLIC') else ' &middot; <a href="jobs.html">professorship ads</a>'}</p>
</div></div>
<script>
const PL_MIN = 2;  // "PL-related" = at least this many PL papers inside the selected window
let dot = "";  // dot picked by a click (also dots of institutions without professors)
const dots = [...document.querySelectorAll(".map .d")], dl = document.getElementById("dot");
const tb = document.querySelector("tbody"), rows = [...tb.rows], ths = [...document.querySelectorAll("th")];
function f() {{
  const q = document.getElementById("q").value.toLowerCase(), cnt = {{}}, u = document.getElementById("u").value, m = document.querySelector('input[name=m]:checked').value, w = +document.querySelector('input[name=y]:checked').value, cur = new Date().getFullYear(); let n = 0;
  for (const r of rows) {{
    const win = (j) => Object.entries(JSON.parse(j)).reduce((s, [y, c]) => s + (!w || +y > cur - w ? c : 0), 0);  // papers inside the window: the last w years including this one (0 = all)
    if (r.dataset.years) {{
      const k = win(r.dataset.years), c = r.cells[6];
      r.dataset.k = k; c.textContent = k ? k + (r.dataset.amb === "1" ? "?" : "") : ""; c.title = r.dataset.tip + (r.dataset.amb === "1" ? " (name shared by several DBLP people: check)" : "");
    }} else r.dataset.k = 0;
    if (r.dataset.cyears) {{
      const k = win(r.dataset.cyears), c = r.cells[7];
      c.textContent = k + (r.dataset.camb === "1" ? "?" : "");  // linked to DBLP: 0 is shown; unlinked rows stay empty c.title = r.dataset.ctip + (r.dataset.camb === "1" ? " (name shared by several CSrankings people: check)" : "");
    }}
    const hide = (m === "cs" && r.dataset.cs === "0") || (m === "pl" && +r.dataset.k < PL_MIN) || (u && r.dataset.u !== u) || (dot && r.dataset.i !== dot) || (q && !r.textContent.toLowerCase().includes(q)); r.classList.toggle("hide", hide); if (!hide) {{ n++; cnt[r.dataset.i] = (cnt[r.dataset.i] || 0) + 1; }} }}
  const mx = Math.max(1, ...Object.values(cnt));  // colour: from the fewest hits (blue) to the busiest (red)
  for (const d of dots) {{
    const c = cnt[d.dataset.i] || 0;
    d.style.fill = c ? `color-mix(in srgb, #e03030 ${{mx > 1 ? 100 * (c - 1) / (mx - 1) : 0}}%, #1a5fb4)` : "#000";  // 0: black; 1 hit: blue, the busiest: red
    d.style.opacity = c ? "" : ".25";  // no hit: mostly transparent
    d.classList.toggle("on", dot === d.dataset.i);
    d.firstChild.textContent = `${{d.firstChild.textContent.split(": ")[0]}}: ${{c}} shown`;
  }}
  const sd = dots.find(d => d.dataset.i === dot); dl.hidden = !dot; dl.textContent = sd ? sd.firstChild.textContent.split(": ")[0] + " \u2715" : "";
  document.getElementById("n").textContent = `${{n}} of ${{rows.length}}`;
  sortRows();
}}
function sortRows() {{  // sort by the header marked "s" (class "r" = descending); re-run after the radios change the PL counts
  const th = document.querySelector("th.s"); if (!th) return;
  const i = ths.indexOf(th), rev = th.classList.contains("r"), num = x => th.hasAttribute("data-rk") ? +x.cells[i].dataset.rk : (isNaN(parseFloat(x.cells[i].textContent)) ? -1 : parseFloat(x.cells[i].textContent));  // empty cell (not found in DBLP) sorts below a 0; "5?" = 5
  rows.sort((a, b) => (th.hasAttribute("data-num") || th.hasAttribute("data-rk") ? num(a) - num(b) : (a.cells[i].dataset.sort || a.cells[i].textContent).localeCompare(b.cells[i].dataset.sort || b.cells[i].textContent)) * (rev ? -1 : 1)).forEach(r => tb.appendChild(r));
}}
ths.forEach(th => th.onclick = () => {{
  const rev = th.classList.contains("s") && !th.classList.contains("r");
  ths.forEach(x => x.classList.remove("s", "r")); th.classList.add("s"); if (rev) th.classList.add("r");
  sortRows();
}});
dots.forEach(d => d.onclick = () => {{ dot = dot === d.dataset.i ? "" : d.dataset.i; f(); }}); dl.style.cursor = "pointer"; dl.onclick = () => {{ dot = ""; f(); }};
document.getElementById("q").oninput = f; document.getElementById("u").onchange = f; document.querySelectorAll("input[name=m], input[name=y]").forEach(x => x.onchange = f); f();
</script></body></html>"""
os.makedirs("output", exist_ok=True)
open("output/professors.html", "w", encoding="utf-8").write(page)
print(len(profs), "professors written to output/professors.html")
