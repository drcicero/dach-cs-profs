"""DBLP papers of each professor in the venues CSrankings counts -> professors_csr.json ("CSranked papers" column of the professors page).
Venue lists: the exact DBLP booktitles / journal names of CSrankings' own filter (util/filter-dblp.py of github.com/emeryberger/CSrankings, gh-pages), kept in csrankings/venues.json
(--venues refreshes it; read with ast, never executed). Like CSrankings, only papers of at least 6 pages count (page ranges that cannot be read count as well).
Step 1 (--reindex, minutes): stream dblp/dblp.xml.gz and record every author whose name matches a professor in professors.json (linked to DBLP, even with no counted paper) and count the papers per year and venue -> csrankings/dblp_index.json.
Step 2 (seconds): match professors.json against that index (same name matching as dblp_pl.py; professors that are new since the index was built get no count until the next --reindex).
Usage (from the project root): python3 -I profs/csr_papers.py [--venues] [--reindex]"""
import ast
import gzip
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I does not add the script's folder
from cs_filter import cs_hit
from dblp_pl import name_key

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.path.join(HERE, "dblp", "dblp.xml.gz")
VENUES = os.path.join(HERE, "csrankings", "venues.json")
INDEX = os.path.join(HERE, "csrankings", "dblp_index.json")
URL = "https://raw.githubusercontent.com/emeryberger/CSrankings/gh-pages/util/filter-dblp.py"
MIN_PAGES = 6
SAFE = (ast.Expression, ast.Call, ast.Name, ast.List, ast.ListComp, ast.comprehension, ast.Constant, ast.JoinedStr, ast.FormattedValue, ast.Starred, ast.Load, ast.Store)


def fetch_venues():
    """BOOKTITLES / JOURNALS out of CSrankings' filter script; the two assignments are evaluated only after checking that they hold nothing but literals, f-strings and range()."""
    tree = ast.parse(urllib.request.urlopen(URL, timeout=60).read().decode("utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("BOOKTITLES", "JOURNALS"):
            expr = node.value.args[0]  # frozenset([...])
            for n in ast.walk(expr):
                assert isinstance(n, SAFE) and (not isinstance(n, ast.Name) or n.id in ("i", "range")) and (not isinstance(n, ast.Call) or n.func.id == "range"), ast.dump(n)
            out[node.targets[0].id] = sorted(eval(compile(ast.Expression(expr), "venues", "eval"), {"__builtins__": {}, "range": range}))
    os.makedirs(os.path.dirname(VENUES), exist_ok=True)
    json.dump(out, open(VENUES, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"venues: {len(out['BOOKTITLES'])} booktitles, {len(out['JOURNALS'])} journals")


def pages(text):
    """Number of pages, or None when the range cannot be read ('10-17', '12:140-12:150')."""
    m = re.match(r"(\d+)-(\d+)$", text or "") or re.match(r"\d+:(\d+)-\d+:(\d+)$", text or "")
    return int(m.group(2)) - int(m.group(1)) + 1 if m else None


def build_index():
    from lxml import etree
    v = json.load(open(VENUES, encoding="utf-8"))
    books, journals = set(v["BOOKTITLES"]), set(v["JOURNALS"])
    wanted = {name_key(p["name"]) for p in json.load(open(os.path.join(HERE, "professors.json"), encoding="utf-8"))["professors"] if p["name"]} - {None}
    people = defaultdict(lambda: dict(names=set(), years=defaultdict(int), venues=defaultdict(int)))
    os.chdir(os.path.join(HERE, "dblp"))  # dblp.dtd is resolved relative to the cwd
    n = kept = 0
    with gzip.open(DUMP, "rb") as f:
        for _, el in etree.iterparse(f, events=("end",), tag=("article", "inproceedings"), load_dtd=True, resolve_entities=True, huge_tree=True):
            n += 1
            venue = el.findtext("booktitle" if el.tag == "inproceedings" else "journal")
            counts = venue in (books if el.tag == "inproceedings" else journals) and (pages(el.findtext("pages")) or MIN_PAGES) >= MIN_PAGES
            kept += counts
            year, label = el.findtext("year") or "", re.sub(r" \(\d+\)$", "", venue or "")
            for a in el.findall("author"):  # every author record links the person to DBLP (so a CSranked count of 0 can be told from 'not found in DBLP'); only counting papers add to the numbers
                k = name_key(a.text or "")
                if k in wanted:
                    p = people[" ".join(k)]
                    p["names"].add(a.text)
                    if counts:
                        p["years"][year] += 1
                        p["venues"][label] += 1
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    with open(INDEX, "w", encoding="utf-8") as f:  # one author per line, so git diffs stay readable
        f.write("{\n" + ",\n".join(json.dumps(k, ensure_ascii=False) + ": " + json.dumps(dict(names=sorted(x["names"]), years=dict(sorted(x["years"].items())), venues=dict(sorted(x["venues"].items()))), ensure_ascii=False, separators=(",", ":"))
                                   for k, x in sorted(people.items())) + "\n}\n")
    print(f"index: {kept} CSranked papers of {n} records; {len(people)} of {len(wanted)} professor names found")


def main():
    if "--venues" in sys.argv or not os.path.exists(VENUES):
        fetch_venues()
    if "--reindex" in sys.argv or not os.path.exists(INDEX):
        build_index()
    idx = json.load(open(INDEX, encoding="utf-8"))
    out = []
    for pr in json.load(open(os.path.join(HERE, "professors.json"), encoding="utf-8"))["professors"]:
        k = name_key(pr["name"])
        e = idx.get(" ".join(k)) if k else None
        if not e or not cs_hit(pr):  # name match is only first + last token: a law professor must not get a namesake's papers
            continue
        top = sorted(e["venues"].items(), key=lambda a: -a[1])[:4]
        out.append(dict(university=pr["university"], name=pr["name"], papers=sum(e["years"].values()), years=e["years"],
                        ambiguous=any(re.search(r"\s\d{4}$", x) for x in e["names"]) or len(e["names"]) > 1, sample=[f"{a} {n}" for a, n in top]))
    json.dump(dict(professors=out), open(os.path.join(HERE, "professors_csr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out)} professors linked to DBLP, {sum(r['papers'] > 0 for r in out)} with CSranked papers; {sum(r['ambiguous'] for r in out)} with a name DBLP lists for several people (check by hand)")


main()
