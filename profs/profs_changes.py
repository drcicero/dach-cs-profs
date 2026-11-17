"""Diff professors.json against the last committed snapshot -> history/changes.tsv (append-only events, one row per event; a 'changed' event gets one row per changed field).
Snapshot = history/professors.jsonl (sorted, no timestamps, so git diffs show only real changes).
Events: new, ended (missing MISSING_RUNS runs in a row), changed (faculty/unit/topic/url).
Guards against broken scrapes: a university whose count collapses (or drops to 0) is carried over unchanged, and 'ended' needs MISSING_RUNS consecutive misses.
Usage (from the project root): python3 -I profs/profs_changes.py"""
import collections
import csv
import json
import os
import sys
import unicodedata

HIST = "history"
SNAP, EVENTS = f"{HIST}/professors.jsonl", f"{HIST}/changes.tsv"
COLS = ("date", "event", "name", "university", "faculty", "unit", "topic", "url", "field", "old", "new")
MISSING_RUNS = 2  # consecutive scrapes a professor must be absent before we call it 'ended'
COLLAPSE = 0.7  # a university that keeps < 70% of its professors (and loses >= 3) is treated as a failed scrape
FIELDS = ("faculty", "unit", "topic", "url")


def norm(name):
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def load_snapshot():
    if not os.path.exists(SNAP):
        return None
    return {(r["university"], norm(r["name"])): r for r in map(json.loads, open(SNAP, encoding="utf-8"))}


def main():
    data = json.load(open("professors.json", encoding="utf-8"))
    day = data["scraped"]
    new = {}
    for p in data["professors"]:
        if p["name"]:
            new.setdefault((p["university"], norm(p["name"])), dict(p))  # first wins on duplicates
    old = load_snapshot()
    os.makedirs(HIST, exist_ok=True)
    events, warnings = [], []

    if old is None:
        print(f"no snapshot yet: baseline of {len(new)} professors, no events")
        write_snapshot(new)
        return

    old_n, new_n = collections.Counter(k[0] for k in old), collections.Counter(k[0] for k in new)
    broken = {u for u, n in old_n.items() if new_n[u] < COLLAPSE * n and n - new_n[u] >= 3 or new_n[u] == 0}
    for u in sorted(broken):
        warnings.append(f"{u}: {old_n[u]} -> {new_n[u]} professors, treated as failed scrape (kept previous data)")

    merged = {}
    for k, r in new.items():
        if k[0] in broken:
            continue
        merged[k] = r
    for k, r in old.items():  # carry over: broken universities untouched, others count their misses
        if k[0] in broken:
            merged[k] = r
        elif k not in new:
            merged[k] = dict(r, missing=r.get("missing", 0) + 1)

    gone = {k for k in old if k not in new and k[0] not in broken}  # absent this run (not yet necessarily ended)
    appeared = [k for k in new if k not in old and k[0] not in broken]
    for k in sorted(appeared):
        events.append(dict(date=day, event="new", name=new[k]["name"], university=k[0], faculty=new[k]["faculty"], unit=new[k]["unit"], topic=new[k]["topic"], url=new[k]["url"]))
    for k in sorted(gone):
        if merged[k]["missing"] >= MISSING_RUNS:
            r = old[k]
            events.append(dict(date=day, event="ended", name=r["name"], university=k[0], faculty=r["faculty"], unit=r["unit"], topic=r["topic"], url=r["url"]))
            del merged[k]
    for k in sorted(set(new) & set(old)):
        if k[0] in broken:
            continue
        diff = {f: [old[k][f], new[k][f]] for f in FIELDS if old[k][f] != new[k][f]}
        if diff:
            events += [dict(date=day, event="changed", name=new[k]["name"], university=k[0], url=new[k]["url"], field=f, old=a, new=b) for f, (a, b) in diff.items()]

    if events:
        fresh = not os.path.exists(EVENTS)
        with open(EVENTS, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, COLS, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            if fresh:
                w.writeheader()
            w.writerows(events)
    write_snapshot(merged)
    c = collections.Counter(e["event"] for e in events)
    print(f"{day}: {len(new)} professors scraped; " + (", ".join(f"{n} {k}" for k, n in sorted(c.items())) or "no changes"))
    for w in warnings:
        print("WARNING:", w, file=sys.stderr)


def write_snapshot(recs):
    with open(SNAP, "w", encoding="utf-8") as f:
        for k in sorted(recs):
            f.write(json.dumps(recs[k], ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
