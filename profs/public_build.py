"""Render the public pages that go to GitHub Pages next to professors.html: output/changes.html (history/changes.tsv, newest first) and output/index.html (links only, no job pages).
Usage (from the project root): python3 -I profs/public_build.py"""
import csv
import html
import os

e = html.escape
rows = []
if os.path.exists("history/changes.tsv"):
    with open("history/changes.tsv", newline="", encoding="utf-8") as f:
        rows = sorted(csv.DictReader(f, delimiter="\t"), key=lambda r: r["date"], reverse=True)  # stable: keeps the order within a day

STYLE = """<style>
  :root { --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#ddd; --head:#f3f3f3; --link:#0645ad; }
  @media (prefers-color-scheme: dark) { :root { --bg:#151515; --fg:#e6e6e6; --muted:#999; --line:#333; --head:#202020; --link:#7ab0ff; } }
  body { margin:0; padding:1rem; background:var(--bg); color:var(--fg); font:14px/1.4 system-ui,sans-serif; }
  h1 { font-size:1.2rem; margin:0 0 .5rem; } .muted { color:var(--muted); } a { color:var(--link); }
  input,select { font:inherit; padding:.25rem .4rem; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:4px; }
  .wrap { overflow-x:auto; margin-top:.75rem; } table { border-collapse:collapse; width:100%; }
  th,td { text-align:left; padding:.35rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; } th { background:var(--head); white-space:nowrap; }
  tr.hide { display:none; } .new { color:#1a7f37; } .ended { color:#b42318; }
</style>"""


def cells(r):
    detail = f'{e(r["field"])}: {e(r["old"])} → {e(r["new"])}' if r["event"] == "changed" else e(r["topic"])
    return f'<tr><td>{e(r["date"])}</td><td class="{e(r["event"])}">{e(r["event"])}</td><td><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["name"])}</a></td><td>{e(r["university"])}</td><td>{detail}</td></tr>'


changes = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Professor changes</title>
{STYLE}</head><body>
<h1>Professor changes</h1>
<p class="muted"><a href="index.html">back</a> · <a href="changes.tsv">changes.tsv</a> · new / ended / changed professors found by the weekly scrape; a professor who moved shows up as ended and new. {len(rows)} entries.</p>
<input id="q" type="search" placeholder="search name, university …" size="28">
<select id="k"><option value="">all events</option><option>new</option><option>ended</option><option>changed</option></select> <span id="n" class="muted"></span>
<div class="wrap"><table><thead><tr><th>Date</th><th>Event</th><th>Name</th><th>University</th><th>Details</th></tr></thead>
<tbody>
{chr(10).join(cells(r) for r in rows)}
</tbody></table></div>
<script>
const q = document.getElementById("q"), k = document.getElementById("k"), rs = [...document.querySelectorAll("tbody tr")];
function f() {{
  const s = q.value.toLowerCase(); let n = 0;
  for (const r of rs) {{ const hide = (k.value && r.cells[1].textContent !== k.value) || (s && !r.textContent.toLowerCase().includes(s)); r.classList.toggle("hide", hide); n += !hide; }}
  document.getElementById("n").textContent = `${{n}} of ${{rs.length}}`;
}}
q.oninput = f; k.onchange = f; f();
</script></body></html>"""

index = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Professors</title>
{STYLE}</head><body>
<h1>Professors in Germany, Austria and Switzerland</h1>
<ul><li><a href="professors.html">Professors</a>: current professors of the scraped faculties, searchable and sortable</li>
<li><a href="changes.html">Changes</a>: new, ended and changed professors, updated weekly ({len(rows)} entries; raw data: <a href="changes.tsv">changes.tsv</a>)</li>
<li><a href="status_profs.html">Source status</a>: which universities were scraped successfully and which failed or are missing</li></ul>
</body></html>"""

os.makedirs("output", exist_ok=True)
open("output/changes.html", "w", encoding="utf-8").write(changes)
open("output/index_public.html", "w", encoding="utf-8").write(index)  # not index.html: that name belongs to the full landing page (site/build_index.py)
print(len(rows), "changes written to output/changes.html")
