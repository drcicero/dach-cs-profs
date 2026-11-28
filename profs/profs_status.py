"""Status page: which institutions of DE / AT / CH / LU have a working professor scraper. Reads professors.json, hrk_universities.txt, dach_universities.txt
and writes output/status_profs.html. Usage (from the project root): python3 -I profs/profs_status.py"""
import glob
import json
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jobs")]  # python -I does not add the script's folder
from cs_filter import cs_hit, CS_NAME
from status_lib import render, INSTITUTES

data = json.load(open("professors.json", encoding="utf-8"))
status = data["status"]
count, total = {}, {}  # CS-related professors (faculty / unit rule of cs_filter.py) and all scraped professors per university
for p in data["professors"]:
    total[p["university"]] = total.get(p["university"], 0) + 1
    count[p["university"]] = count.get(p["university"], 0) + cs_hit(p)

UNITS = json.load(open("units.json", encoding="utf-8")) if os.path.exists("units.json") else {}  # units_scrape.py: unit names from the organisation page of the institutions without scraper


def unit_note(name):
    """Evidence for 'no computer-science unit': the unit names the university's own page lists, and those of them whose name looks computer-science (cs_filter.CS_NAME)."""
    u = UNITS.get(name)
    if not u or len(u["units"]) < 3:  # no usable list (navigation links only)
        return ""
    cs = [x for x in u["units"] if CS_NAME.search(x)]
    where = u["url"] if isinstance(u["url"], str) else f"{len(u['url'])} faculty pages ({u['url'][0]}, ...)" + (f", not readable: {' '.join(u['missing'])}" if u.get("missing") else "")
    shown = "; ".join(x for x in u["units"] if x not in cs)[:600]
    return (f"no scraper; {len(u['units'])} units on {where}: computer-science-like: {'; '.join(cs)}; all: " if cs else f"no CS unit: none of the {len(u['units'])} units on {where} is computer science: ") + shown


# institution (name as in hrk_universities.txt / dach_universities.txt) -> (university as in professors.json, scraper functions of profs/profs_scrape*.py)
SRC = {
    "Universität Freiburg im Breisgau": ("Universität Freiburg", "freiburg"), "Universität Heidelberg": ("Universität Heidelberg", "heidelberg_mathinf"),
    "KIT Karlsruhe": ("KIT", "kit"), "Universität Konstanz": ("", "konstanz"), "Universität Mannheim": ("Universität Mannheim", "mannheim"),
    "Universität Stuttgart": ("Universität Stuttgart", "stuttgart"), "Universität Tübingen": ("Universität Tübingen", "tuebingen"),
    "Universität Ulm": ("Universität Ulm", "ulm"), "Universität Augsburg": ("Universität Augsburg", "augsburg"), "Universität Bamberg": ("Universität Bamberg", "bamberg"),
    "Universität Erlangen-Nürnberg": ("", "erlangen_ds erlangen_cs"), "Technische Universität München": ("TU München", "tum_cit tum"),
    "Universität München": ("LMU München", "lmu"), "Universität Passau": ("Universität Passau", "passau"), "Universität Regensburg": ("Universität Regensburg", "regensburg"),
    "Universität Würzburg": ("Universität Würzburg", "wuerzburg"), "Freie Universität Berlin": ("FU Berlin", "fu_berlin"), "Technische Universität Berlin": ("TU Berlin", "tu_berlin"),
    "Brandenburgische Technische Universität Cottbus-Senftenberg": ("BTU Cottbus-Senftenberg", "cottbus"), "Universität Potsdam": ("Universität Potsdam", "potsdam"),
    "Universität Bremen": ("Universität Bremen", "bremen"), "Universität Hamburg": ("Universität Hamburg", "hamburg"), "Technische Universität Hamburg": ("TU Hamburg", "tuhh"),
    "Technische Universität Darmstadt": ("TU Darmstadt", "darmstadt"), "Universität Frankfurt am Main": ("Goethe-Universität Frankfurt", "frankfurt"),
    "Universität Gießen": ("Universität Gießen", "giessen"), "Universität Kassel": ("Universität Kassel", "kassel"), "Universität Marburg": ("Universität Marburg", "marburg"),
    "Universität Greifswald": ("Universität Greifswald", "greifswald"), "Universität Rostock": ("Universität Rostock", "rostock"),
    "Technische Universität Braunschweig": ("TU Braunschweig", "braunschweig"), "Technische Universität Clausthal": ("TU Clausthal", "clausthal"),
    "Universität Göttingen": ("Universität Göttingen", "goettingen"), "Universität Hannover": ("Leibniz Universität Hannover", "hannover"),
    "Universität Oldenburg": ("Universität Oldenburg", "oldenburg"), "Universität Osnabrück": ("Universität Osnabrück", "osnabrueck"),
    "Technische Hochschule Aachen": ("RWTH Aachen", "rwth"), "Universität Bielefeld": ("Universität Bielefeld", "bielefeld"), "Universität Bochum": ("Ruhr-Universität Bochum", "bochum"),
    "Universität Bonn": ("Universität Bonn", "bonn"), "Technische Universität Dortmund": ("TU Dortmund", "dortmund"),
    "Universität Duisburg-Essen": ("Universität Duisburg-Essen", "duisburg_essen"), "Universität Düsseldorf": ("Universität Düsseldorf", "hhu"),
    "Universität zu Köln": ("Universität Köln", "koeln"), "Universität Münster": ("Universität Münster", "muenster"), "Universität Paderborn": ("Universität Paderborn", "paderborn"),
    "Universität Siegen": ("Universität Siegen", "siegen"), "Universität Wuppertal": ("Universität Wuppertal", "wuppertal"), "FernUniversität in Hagen": ("FernUniversität in Hagen", "hagen"),
    "Universität der Bundeswehr München": ("Universität der Bundeswehr München", "unibw"), "Universität Hildesheim": ("Universität Hildesheim", "hildesheim"),
    "Constructor University Bremen": ("Constructor University Bremen", "constructor"),
    "Technische Universität Bergakademie Freiberg": ("TU Bergakademie Freiberg", "freiberg"), "Universität Bayreuth": ("Universität Bayreuth", "bayreuth"), "Technische Universität Kaiserslautern-Landau": ("RPTU Kaiserslautern-Landau", "rptu"), "Universität Koblenz": ("Universität Koblenz", "koblenz"),
    "Universität Mainz": ("Universität Mainz", "mainz"), "Universität Trier": ("Universität Trier", "trier"), "Universität des Saarlandes": ("Universität des Saarlandes", "saarland_cs"),
    "Technische Universität Chemnitz": ("TU Chemnitz", "chemnitz"), "Technische Universität Dresden": ("TU Dresden", "dresden"), "Universität Leipzig": ("Universität Leipzig", "leipzig"),
    "Universität Halle-Wittenberg": ("Universität Halle", "halle"), "Universität Magdeburg": ("Universität Magdeburg", "magdeburg"), "Universität zu Kiel": ("Universität Kiel", "kiel"),
    "Universität zu Lübeck": ("Universität zu Lübeck", "luebeck"), "Technische Universität Ilmenau": ("TU Ilmenau", "ilmenau"), "Universität Jena": ("Universität Jena", "jena"),
    # Austria / Switzerland
    "Universität Wien": ("Universität Wien", "univie"), "Universität Innsbruck": ("Universität Innsbruck", "innsbruck"), "Universität Salzburg": ("Universität Salzburg", "salzburg"),
    "Technische Universität Wien": ("TU Wien", "tuwien"), "Technische Universität Graz": ("TU Graz", "tugraz"), "Johannes Kepler Universität Linz": ("JKU Linz", "jku"),
    "Universität Klagenfurt": ("Universität Klagenfurt", "klagenfurt"), "University of Luxembourg": ("University of Luxembourg", "luxembourg"), "ETH Zürich": ("ETH Zürich", "eth"), "EPFL Lausanne": ("EPFL Lausanne", "epfl"), "Universität Zürich": ("Universität Zürich", "uzh"),
    "Universität Basel": ("Universität Basel", "basel"), "Universität Bern": ("Universität Bern", "bern"), "Universität St. Gallen": ("Universität St. Gallen", "stgallen"),
    "Universität Freiburg (Fribourg)": ("Universität Freiburg (Fribourg)", "fribourg"), "Università della Svizzera italiana (Lugano)": ("Università della Svizzera italiana (Lugano)", "usi"),
    "Université de Genève": ("Université de Genève", "geneva"), "Université de Neuchâtel": ("Université de Neuchâtel", "neuchatel"),
    # research institutes
    "MPI für Informatik (MPI-INF)": ("MPI-INF", "mpi_inf"), "MPI für Softwaresysteme (MPI-SWS)": ("MPI-SWS", "mpi_sws"), "MPI für Sicherheit und Privatsphäre (MPI-SP)": ("MPI-SP", "mpi_sp"),
    "CISPA Helmholtz-Zentrum": ("CISPA", "cispa"), "Hasso-Plattner-Institut (HPI)": ("Hasso-Plattner-Institut", "hpi_profs"), "ISTA (AT)": ("ISTA", "ista"),
    "DFKI": ("", ""), "Weizenbaum-Institut": ("", ""), "MPI für Intelligente Systeme (MPI-IS)": ("", ""),  # the other institutes (MPG, Fraunhofer, ...) have no entry: no scraper
}
INCOMPLETE = {"University of Luxembourg": "partial: head of department, the 6 professors shown without 'Load more' and the research-group heads; the rest of the people list is loaded by an internal people API that is not used"}  # institutions where CS is known to be only partly covered (amber); add more here
NOTE = {"Universität Heidelberg": "only Mathematik / Informatik", "Universität Tübingen": "", "Universität Konstanz": "",
        "Universität Hohenheim": "not scraped: no computer-science department (Wirtschaftsinformatik chairs in the business faculty), no common list page found",
        "Universität Graz": "not scraped: no separate computer-science institute found (Informatik is taught jointly with TU Graz); only the Institut für Informationswissenschaft und Wirtschaftsinformatik",
        "Universität für angewandte Kunst Wien": "not scraped: its institute pages are disallowed by robots.txt, no unit list read",
        "Humboldt-Universität Berlin": "not scraped: informatik.hu-berlin.de serves an Anubis anti-bot challenge, www3.informatik.hu-berlin.de disallows scripts in robots.txt (not bypassed)"}

# first line of each scraper's docstring: the reason a scraper is skipped
doc = {}
for f in glob.glob("profs/profs_scrape*.py"):
    for m in re.finditer(r'^def (\w+)\(\):\n    """(.+)', open(f, encoding="utf-8").read(), re.M):
        doc[m.group(1)] = m.group(2).rstrip('"').strip()


def row(country, region, name):
    uni, keys = SRC.get(name, ("", ""))
    keys = keys.split()
    n = count.get(uni, 0) if uni else 0
    msgs = [status[k] for k in keys if k in status]
    failed = [m for m in msgs if m.startswith("FAILED")]
    note = NOTE.get(name, "")
    if not keys and unit_note(name).startswith("no CS unit"):
        st, num, note = "zero", 0, unit_note(name)
    elif not keys:
        st, num, note = "none", "", note or unit_note(name) or "no scraper"
    elif not msgs:
        st, num, note = "none", "", "scraper not run yet"
    elif n:
        st, num = ("partial" if name in INCOMPLETE else "ads"), n
        note = INCOMPLETE.get(name, note)
        if total[uni] > n:
            note = (note + "; " if note else "") + f"{total[uni]} professors scraped, {n} in CS units"
    elif uni in total and not failed:
        st, num, note = "zero", 0, f"{total[uni]} professors scraped, none in a CS unit"
    elif failed:
        st, num, note = "failing", "", failed[0][8:]
    else:
        st, num, note = "zero", 0, note or doc.get(keys[0], "")[:200]
    return dict(country=country, region=region, name=name, key=" ".join(keys), st=st, n=num, note=note)


rows, state = [], ""
for line in open("hrk_universities.txt", encoding="utf-8"):
    name = line.strip()
    if not name or name.startswith("#"):
        continue
    if not re.search(r"Universit|Hochschule|Sporthochschule|KIT|Constructor", name):
        state = name
        continue
    rows.append(row("DE", state, name))
country = ""
for line in open("dach_universities.txt", encoding="utf-8"):
    if line.startswith("#"):
        country = "AT" if "Austria" in line else "LU" if "Luxembourg" in line else "CH"
    elif line.strip():
        rows.append(row(country, "", line.split("\t")[0].rstrip("\n")))
for name in INSTITUTES:
    rows.append(row("AT" if "(AT)" in name else "CH" if "(CH)" in name else "DE", "research institute", name))

RANK = {"ads": 0, "partial": 1, "zero": 1, "failing": 2, "blocked": 3, "none": 4}
LABEL = {"ads": "CS professors found", "partial": "CS partly covered", "zero": "0 CS professors (checked)", "failing": "failing", "blocked": "blocked by the site", "none": "no scraper"}
intro = """<p class="muted">Coverage of the professor scrapers (professors.html), counted in CS only: a professor counts when the faculty or unit name says Informatik / computer / software
(or the institute is a CS one), see the footer of professors.html. "CS partly covered" marks institutions where a CS unit is known to be missing; "works, 0 CS professors" means the scraper
returned people but none in a CS unit (or nothing at all). Universities without a scraper are not looked at yet or are skipped on purpose (robots.txt, anti-bot challenge, broken site).
A drop of a scraper's count shows up in the change history, not here.</p>"""
map_note = ("Map: one dot per institution &ndash; green = CS professors found, amber = CS only partly covered (or 0 CS professors), red = failing or no scraper, black = the site blocks scripts (robots.txt, anti-bot, captcha; respected, not bypassed); follows the filters below. Hover a state for its count and click it to filter the table (Austria, Switzerland and Luxembourg are one region each). "
            "Research institutes (squares) sit at their headquarters.")
def main():
    page, cnt = render("Source status: professors", rows, LABEL, RANK, data["scraped"], intro, map_note, "CS professors",
                       '<a href="index.html">&larr; overview</a> &middot; <a href="professors.html">professors</a>' + ("" if os.environ.get("PUBLIC") else ' &middot; <a href="status_ads.html">ad sources</a>'))  # PUBLIC: no link to the job pages
    os.makedirs("output", exist_ok=True)
    open("output/status_profs.html", "w", encoding="utf-8").write(page)
    print(f"{len(rows)} institutions listed; " + "; ".join(f"{c}: " + ", ".join(f"{v[k]} {k}" for k in LABEL) for c, v in cnt.items()))


if __name__ == "__main__":
    main()
