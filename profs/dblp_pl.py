"""Professors with at least one paper in the given DBLP venues (default PACMPL, ESOP, ECOOP, TOPLAS) -> professors_pl.json / professors_pl.csv.
Step 1 (once, ~minutes): stream dblp/dblp.xml.gz and keep only papers whose DBLP key starts with the venue prefixes -> dblp/venue_papers.json.
Step 2 (seconds): match the authors to professors.json by name (first + last token, accents/ß folded, DBLP homonym numbers like '0001' dropped).
Usage (from the project root): python3 -I profs/dblp_pl.py [--venues pacmpl,esop,ecoop,toplas] [--since 2015] [--reindex]
dblp.xml.gz and dblp.dtd come from https://dblp.org/xml/ (put both into ./dblp/; the DTD must sit next to the cwd for the entities)."""
import argparse
import csv
import gzip
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I does not add the script's folder
from cs_filter import cs_hit

PREFIX = {"pacmpl": "journals/pacmpl/", "toplas": "journals/toplas/", "esop": "conf/esop/", "ecoop": "conf/ecoop/", "popl": "conf/popl/", "pldi": "conf/pldi/", "icfp": "conf/icfp/",
          "oopsla": "conf/oopsla/", "tacas": "conf/tacas/", "cav": "conf/cav/"}
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root: dblp/, professors.json and the outputs live there
DUMP = os.path.join(HERE, "dblp", "dblp.xml.gz")
INDEX = os.path.join(HERE, "dblp", "venue_papers.json")


def build_index(venues):
    from lxml import etree
    prefixes = tuple(PREFIX[v] for v in venues)
    papers, n = [], 0
    os.chdir(os.path.join(HERE, "dblp"))  # dblp.dtd is resolved relative to the cwd
    with gzip.open(DUMP, "rb") as f:
        for _, el in etree.iterparse(f, events=("end",), tag=("article", "inproceedings"), load_dtd=True, resolve_entities=True, huge_tree=True):
            n += 1
            key = el.get("key", "")
            if key.startswith(prefixes):
                papers.append(dict(key=key, venue=next(v for v in venues if key.startswith(PREFIX[v])), year=(el.findtext("year") or ""), title="".join(el.find("title").itertext()) if el.find("title") is not None else "",
                                   authors=[dict(name=a.text or "", orcid=a.get("orcid", "")) for a in el.findall("author")], ee=el.findtext("ee") or ""))
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    with open(INDEX, "w", encoding="utf-8") as f:  # one paper per line, so git diffs of a refreshed index stay readable
        f.write(json.dumps(dict(venues=list(venues), records_seen=n), ensure_ascii=False)[:-1] + ', "papers": [\n')
        f.write(",\n".join(json.dumps(x, ensure_ascii=False) for x in papers) + "\n]}\n")
    print(f"index: {len(papers)} papers of {n} records")


def fold(s):
    s = unicodedata.normalize("NFKD", s.replace("ß", "ss")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s.replace("-", " ")).split()


def name_key(name):
    t = fold(re.sub(r"\s\d{4}$", "", name))  # 'Wei Zhang 0001' -> homonym number dropped
    return (t[0], t[-1]) if len(t) > 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default="pacmpl,esop,ecoop,toplas")
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--reindex", action="store_true")
    a = ap.parse_args()
    venues = [v.strip().lower() for v in a.venues.split(",")]
    idx = json.load(open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) and not a.reindex else None
    if idx is None or not set(venues) <= set(idx["venues"]):
        build_index(sorted(set(venues) | set(idx["venues"] if idx else [])))
        idx = json.load(open(INDEX, encoding="utf-8"))
    by_author = defaultdict(list)
    homonyms = defaultdict(set)  # name key -> distinct DBLP person names (a numbered suffix means DBLP knows several people of that name)
    for p in idx["papers"]:
        if p["venue"] not in venues or (p["year"] and int(p["year"]) < a.since):
            continue
        for au in p["authors"]:
            k = name_key(au["name"])
            if k:
                by_author[k].append(p)
                homonyms[k].add(au["name"])
    out = []
    for pr in json.load(open(os.path.join(HERE, "professors.json"), encoding="utf-8"))["professors"]:
        k = name_key(pr["name"])
        ps = by_author.get(k, []) if cs_hit(pr) else []  # name match is only first+last token: a law professor must not get a namesake's papers
        if not ps:
            continue
        ps = list({p["key"]: p for p in ps}.values())
        counts = {v: sum(1 for p in ps if p["venue"] == v) for v in venues}
        out.append(dict(university=pr["university"], faculty=pr["faculty"], unit=pr["unit"], name=pr["name"], topic=pr["topic"], url=pr["url"],
                        papers=len(ps), counts=counts, latest=max(p["year"] for p in ps), years=dict(sorted({y: sum(1 for p in ps if p["year"] == y) for y in {p["year"] for p in ps}}.items())), ambiguous=any(re.search(r"\s\d{4}$", n) for n in homonyms[k]),
                        sample=[f'{p["year"]} {p["venue"].upper()}: {p["title"]}' for p in sorted(ps, key=lambda p: p["year"], reverse=True)[:3]]))
    out.sort(key=lambda r: (-r["papers"], r["university"], r["name"]))
    json.dump(dict(venues=venues, since=a.since, professors=out), open(os.path.join(HERE, "professors_pl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "professors_pl.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["university", "name", "unit", "topic", "papers", *venues, "latest", "name_ambiguous_in_dblp", "url"])
        for r in out:
            w.writerow([r["university"], r["name"], r["unit"], r["topic"], r["papers"], *(r["counts"][v] for v in venues), r["latest"], int(r["ambiguous"]), r["url"]])
    print(f"{len(out)} professors with >=1 paper in {'/'.join(v.upper() for v in venues)}" + (f" since {a.since}" if a.since else "") + f"; {sum(r['ambiguous'] for r in out)} with a name that DBLP lists for several people (check by hand)")


if __name__ == "__main__":
    main()
