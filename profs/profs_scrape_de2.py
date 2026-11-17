"""More German computer-science professor lists (second batch); same conventions as profs_scrape.py (cached, polite, robots-checked via need()).
Usage: from profs_scrape_de2 import SOURCES_DE2"""
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse as up

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain  # prof(uni, faculty, name, topic="", unit="", url="") ; need(url) = cached, polite, robots-checked fetch


def _ascii(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def erlangen_cs():
    """Skipped (returns []): cs.fau.de lists the Department Informatik chairs without names, FAUdir is robots-disallowed, and the ~22 chair websites have no common
    layout (several disallow robots or show emeriti/other professors first), so no reliable, current name list can be scraped."""
    return []


def bremen():
    """FB 03 Mathematik/Informatik, Informatik working groups page: <p>Prof. Dr. X. Surname</p><p>Group</p> pairs (first names abbreviated on the site).
    'N. N.' (vacant) skipped; 'weitere Professuren' are honorary/apl./retired and skipped."""
    url = "https://www.uni-bremen.de/fb3/forschung/informatik/arbeitsgruppen"
    out = []
    for m in re.finditer(r"<p>((?:Prof|N\.)[^<]{0,70})</p>\s*<p>(.*?)</p>", need(url)):
        name = plain(m.group(1))
        if name.startswith("Prof"):
            out.append(prof("Universität Bremen", "Fachbereich 03 Mathematik/Informatik", name, plain(m.group(2)), "Informatik", url))
    return out


def konstanz():
    """Skipped: robots.txt of www.uni-konstanz.de and www.informatik.uni-konstanz.de disallows all crawling ('Disallow: /')."""
    return []


def kiel():
    """Institut für Informatik (Technische Fakultät): buttons 'Arbeitsgruppe' + 'Leitung: Prof. Dr. X'; NN and Vertretung entries skipped."""
    url = "https://www.inf.uni-kiel.de/de/tf/fakultaet/institute/informatik/personen-institut-fuer-informatik"
    out = []
    for m in re.finditer(r'<p class="text-center">(.*?)</p><p>(Leitung[^<]*)</p>', need(url)):
        lead = plain(m.group(2))
        if re.match(r"Leitung:\s*Prof", lead):
            link = re.search(r'href="([^"]*)"', m.group(1))
            out.append(prof("Universität Kiel", "Technische Fakultät", re.sub(r"^Leitung:\s*", "", lead), plain(m.group(1)), "Institut für Informatik", up.urljoin(url, link.group(1)) if link else url))
    return out


def muenster():
    """Institut für Informatik (FB 10 Mathematik und Informatik): research page lists the Arbeitsgruppen as 'Group - Prof. Dr. Name' links."""
    url = "https://www.uni-muenster.de/Informatik/forschung/index.shtml"
    out = []
    for m in re.finditer(r'<li><a [^>]*href="([^"]*)"[^>]*>([^<]*?)\s+-\s+(Prof\.[^<]*)</a></li>', need(url)):
        out.append(prof("Universität Münster", "Fachbereich 10 Mathematik und Informatik", m.group(3), plain(m.group(2)), "Institut für Informatik", up.urljoin(url, m.group(1))))
    return out


def bielefeld():
    """Technische Fakultät, 'Intelligente Systeme' Arbeitsgruppen table: AG link followed by the PEVZ person link; only current 'Prof.' entries (not Dr./former AGs)."""
    url = "https://www.uni-bielefeld.de/fakultaeten/technische-fakultaet/forschung/intelligente-systeme/"
    page = need(url).split("Ehemalige Arbeitsgruppen", 1)[0]
    out = []
    for m in re.finditer(r'(?s)<a [^>]*href="(/fakultaeten/technische-fakultaet/forschung/ag-ueberblick/[^"]*)"[^>]*>(.*?)</a>.{0,300}?<a [^>]*href="([^"]*PersonDetail[^"]*)"[^>]*>(.*?)</a>', page):
        name = plain(m.group(4))
        if name.startswith("Prof"):
            out.append(prof("Universität Bielefeld", "Technische Fakultät", name, plain(m.group(2)), "Informatik", m.group(3)))
    return out


def oldenburg():
    """Department für Informatik (Fakultät II), 'Abteilungen und Einrichtungen' table: <strong>AG</strong><br>abbreviated head ('S. Boll'); the full first name is
    taken from the profile link slug where it contains it. apl. Prof. entries are skipped; Nachwuchsgruppen are not professors."""
    url = "https://uol.de/informatik/department/abteilungen-und-einrichtungen"
    page = need(url).split("Abteilungen und zentrale Einrichtungen", 1)[1].split("Nachwuchsgruppen", 1)[0]
    out = []
    for td in re.findall(r"(?s)<td>(.*?)</td>", page):
        parts = re.split(r"<br>|</p>", td)
        topic = " ".join(plain(p) for p in parts if "<strong>" in p)
        for p in parts:
            if "<strong>" in p or not plain(p):
                continue
            a = re.search(r'<a href="([^"]*)"', p)
            name = plain(p)
            m = re.match(r"((?:[A-ZÄÖÜ][a-zäöü]*\.(?:-[A-Z]\.)?|\w+)\s+)(\S.*)$", name)
            if not m or "apl" in (a.group(1) if a else ""):
                continue
            first, last = m.group(1).strip(), m.group(2).strip()
            if a and len(first) <= 4:  # abbreviated: try the slug ('/ei/mitarbeiter/sebastian-lehnhoff', '/prof-dr-ing-habil-sergej-fatikow')
                w = re.sub(r"^(?:apl-)?(?:prof-)?(?:dr-)?(?:ing-)?(?:habil-)?", "", a.group(1).rstrip("/").split("/")[-1]).split("-")
                n = len(last.split())
                if len(w) > n and _ascii(" ".join(w[-n:])).replace("ae", "a").replace("oe", "o").replace("ue", "u").replace("ss", "s") == _ascii(last).replace("ss", "s").replace("ae", "a").replace("oe", "o").replace("ue", "u") and w[0][:1] == first[:1].lower():
                    first = " ".join(x.capitalize() for x in w[:-n])
            if len(topic) < 3:
                continue
            out.append(prof("Universität Oldenburg", "Fakultät II Informatik, Wirtschafts- und Rechtswissenschaften", f"{first} {last}", re.sub(r"\s*\(WI\)", "", topic), "Department für Informatik", up.urljoin(url, a.group(1)) if a else url))
    return out


def halle():
    """Institut für Informatik (NatFak III), 'Mitarbeiter:innen' page, section 'Professor:innen am Institut' ('Prof. Dr. Last, First' / 'JProf.'); topic = Fachgebiet
    from the Arbeitsgruppen page via the AG folder of the professor's profile link. Kooptierte, iDiv, Ruhestand, PD and apl. skipped."""
    base = "https://www.informatik.uni-halle.de/"
    page = need(base + "mitarbeiter/")
    sec = page.split("Professor:innen am Institut", 1)[1].split("Professor:innen am iDiv", 1)[0]
    ag = need(base + "arbeitsgruppen/")
    def key(href):
        if href.startswith("http"):
            return up.urlsplit(href).netloc.replace("www.", "").split(".")[0] if "uni-halle" in href else ""
        return next((x for x in href.split("/") if x not in ("", "..")), "")

    leaders = {plain(m.group(2)): key(m.group(1)) for m in re.finditer(r'<a href="([^"]*)"[^>]*>([^<]+)</a>', ag.split("Arbeitsgruppenleiter", 1)[1])}
    fach = {}
    for m in re.finditer(r'<a href="([^"]*)"[^>]*>([^<]+)</a>', ag.split("Arbeitsgruppenleiter", 1)[0]):
        fach.setdefault(key(m.group(1)), plain(m.group(2)))
    out = []
    for m in re.finditer(r'<a href="([^"]*)"[^>]*>\s*((?:J?Prof)[^<]*?),\s*([^<]*?)\s*</a>', sec):
        title, last = re.sub(r"^J(?=Prof)", "Jun.-", m.group(2)), ""
        last = re.sub(r"^(?:Jun\.-)?Prof\.?\s*(?:Dr\.\s*)?", "", title)
        first = plain(m.group(3))
        name = f"{first} {last}"
        lead = next((k for k in leaders if _ascii(k.split()[-1].replace("ß", "ss")) == _ascii(last.replace("ß", "ss")) or _ascii(k) == _ascii(name)), None)
        topic = fach.get(leaders.get(lead, ""), "")
        out.append(prof("Universität Halle", "Naturwissenschaftliche Fakultät III", name, topic, "Institut für Informatik", up.urljoin(base + "mitarbeiter/", m.group(1))))
    return out


def leipzig():
    """Skipped: the Institut für Informatik pages (informatik.uni-leipzig.de/ifi/..., mathcs.uni-leipzig.de/ifi/...) currently return 404 (site migration / IT incident);
    the only reachable page (informatik.uni-leipzig.de/profs.html) dates from 2010 and is not a current list."""
    return []


def siegen():
    """Department Elektrotechnik und Informatik (NT-Fakultät): the 'Schwerpunkte' page groups the chairs; only the computer-science Schwerpunkte
    (Embedded System, Visual Computing) are read. Cards: h3 chair + first <p> with the (possibly two) professors; Dr. entries skipped."""
    url = "https://www.eti.uni-siegen.de/dekanat/institute/?lang=de"
    page = need(url)
    out = []
    for sec in re.split(r"(?=<h2[^>]*>\s*Schwerpunkt)", page)[1:]:
        head = plain(sec.split("</h2>", 1)[0])
        if not re.search(r"Embedded System|Visual Computing", head):
            continue
        for m in re.finditer(r'(?s)<h3 class="card-title[^>]*>([^<]*)</h3>\s*<div class="card-text[^>]*>\s*<p[^>]*>(.*?)</p>', sec):
            for nm in re.split(r"\s+(?:und|&)\s+(?=(?:Jun\.-)?Prof)", plain(m.group(2))):
                if re.match(r"(?:Jun\.-)?Prof", nm):
                    out.append(prof("Universität Siegen", "Naturwissenschaftlich-Technische Fakultät", nm, plain(m.group(1)), "Department Elektrotechnik und Informatik", url))
    return out


def trier():
    """Fach Informatikwissenschaften (Fachbereich IV): 'Professuren' tiles give chair topic + surname (image name); the Personenverzeichnis rows ('Näher, Prof. Dr. Stefan')
    give the full names. emeritiert, apl., Honorar and Lehrkraft entries are skipped. Only the name column is used (no contact data)."""
    base = "https://www.uni-trier.de/universitaet/fachbereiche-faecher/fachbereich-iv/faecher/informatikwissenschaften/"
    tiles = {}
    for chunk in need(base + "team/professuren").split("portal-item")[1:]:
        m = re.search(r'csm_(\w+?)_[0-9a-f]+\.png"[^>]*alt="([^"]*)"', chunk)
        slug = re.search(r"/professuren/([\w-]+)/", chunk)
        if m:
            alt = plain(m.group(2))
            tiles[m.group(1)] = alt if len(alt.split()) > 1 or not slug else slug.group(1).replace("-", " ").title()  # tile alt is only a surname for some chairs
    out = []
    for row in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", need(base + "team/informatikwissenschaften/personenverzeichnis")):
        cells = re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", row)
        txt = plain(cells[0]) if cells else ""
        m = re.match(r"([^,]+),\s*(.*)$", txt)
        if not m or re.search(r"apl\.|emerit|Hon", txt):
            continue
        last, rest = m.group(1).strip(), m.group(2)
        key = _ascii(last)
        topic = tiles.get(key) or tiles.get(key.replace("ae", "a").replace("oe", "o").replace("ue", "u"))
        if topic is None or not (re.search(r"Prof", rest) or key == "fernau") or "Lehrkraft" in topic:
            continue
        first = re.sub(r"(?:Univ\.-?\s*|Jun\.-?\s*)?Prof\.?|Dr\.?|\(.*?\)|,", " ", rest)
        link = re.search(r'href="([^"]*)"', cells[0])
        out.append(prof("Universität Trier", "Fachbereich IV", f"{' '.join(first.split())} {last}", topic, "Informatikwissenschaften", up.urljoin(base, link.group(1)) if link and link.group(1) != "#" else base + "team/professuren"))
    return out


def clausthal():
    """Institut für Informatik (host ifi.tu-clausthal.de), 'Personen' page: cards with title 'Prof. Dr. X', role 'Universitätsprofessor' and AG link.
    Only role == Universitätsprofessor (not a.D., apl., Dozent, Lehrstuhlvertretung); e-mail/phone on the cards are ignored."""
    url = "https://www.ifi.tu-clausthal.de/ueber-uns/personen"
    out = []
    for m in re.finditer(r'(?s)<h4 class="card-title">(.*?)</h4>\s*<div class="card-text">\s*<p><strong>(.*?)</strong>(.*?)</p>', need(url)):
        if plain(m.group(2)) != "Universitätsprofessor":
            continue
        ag = re.search(r'(?s)AG\s*<a href="([^"]*)"[^>]*>(.*?)</a>', m.group(3))
        out.append(prof("TU Clausthal", "Fakultät für Mathematik/Informatik und Maschinenbau", plain(m.group(1)), plain(ag.group(2)) if ag else "", "Institut für Informatik", ag.group(1) if ag else url))
    return out


def lmu():
    """Institut für Informatik, 'Lehr- und Forschungseinheiten' page: <h3>/<h4> unit heading, then <p> with 'Prof. Dr. X, Prof. Dr. Y (apl.)' (names split by <br> and
    commas). apl. (außerplanmäßig) professors are skipped, as is everything from 'Assoziierte Gruppen' on (other faculties)."""
    url = "https://www.ifi.lmu.de/institut/index.html"
    page = need(url).split("Assoziierte Gruppen")[0]
    out = []
    for unit, body in re.findall(r"(?s)<h[34]>(.*?)</h[34]>\s*<p>(.*?)</p>", page):
        for name in re.split(r"<br\s*/?>|,\s*(?=Prof)", body):
            name = plain(name)
            if name.startswith("Prof") and "(apl.)" not in name:
                out.append(prof("LMU München", "Fakultät für Mathematik, Informatik und Statistik", name, plain(unit), "Institut für Informatik", url))
    if not out:
        raise RuntimeError("layout changed")
    return out


KOBLENZ = {"icv": "Institut für Computervisualistik", "ifi": "Institut für Informatik", "ifm": "Institut für Management", "iwvi": "Institut für Wirtschafts- und Verwaltungsinformatik",
           "ist": "Institut für Softwaretechnik", "west": "Institute for Web Science and Technologies"}


def koblenz():
    """FB 4 Informatik 'Personenverzeichnis' (Plone/Volto): the page embeds all ~400 people as JSON (window.__data, 'items' with Title and Subject tags).
    Professors carry the tag 'Professor*innen' (honorary professors do not); institute = second path part of the person's @id; old duplicate pages ('…-old') dedupe by name."""
    url = "https://www.uni-koblenz.de/de/informatik/personen-am-fachbereich-informatik"
    page = need(url)
    i = page.find('"@type":"Person"')  # the first 'items' arrays are breadcrumbs and navigation; the people list starts at the array holding the first Person
    k = page.rfind('[{"@id"', 0, i)
    if i < 0 or k < 0:
        raise RuntimeError("layout changed")
    items = json.JSONDecoder().raw_decode(page[k:])[0]
    out, seen = [], set()
    for p in items:
        if "Professor*innen" in p.get("Subject", []) and p.get("Title") and p["Title"] not in seen:
            seen.add(p["Title"])
            path = p["@id"].split("/")
            desc = p.get("Description", "").strip()
            topic = "" if re.fullmatch(r"(?i)universitätsprofessor(?:in)?|professor(?:in)?|head of institute", desc) else desc
            out.append(prof("Universität Koblenz", "Fachbereich 4 Informatik", re.sub(r"^J(?:un\.?-?)?Prof\.\s*", "", p["Title"]), topic, KOBLENZ.get(path[3] if len(path) > 3 else "", ""), up.urljoin(url, p["@id"])))
    if not out:
        raise RuntimeError("layout changed")
    return out


SOURCES_DE2 = [lmu, koblenz, erlangen_cs, bremen, konstanz, kiel, muenster, bielefeld, oldenburg, halle, leipzig, siegen, trier, clausthal]
