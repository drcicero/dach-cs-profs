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
        out.append(prof("Universität Halle", "Naturwissenschaftliche Fakultät III", name, topic, "Institut für Informatik", up.urljoin(base + "mitarbeiter/", m.group(1)), title))
    return out


def leipzig():
    """Fakultät für Mathematik und Informatik, faculty start page (the old institute sites informatik.uni-leipzig.de/ifi/... and mathcs.uni-leipzig.de/ifi/... are gone):
    its last 'Institut für Informatik' heading lists the Informatik professors as 'Professor(in) Dr. Name (Topic):' up to the page footer. 'Dr. ... (Vertretungsprofessur)' is skipped,
    JProf. kept. The page also lists the mathematics institute's professors under an earlier heading; those are not read."""
    url = "https://www.uni-leipzig.de/fakultaet-fuer-mathematik-und-informatik/"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    start = max((i for i, t in enumerate(toks) if t == "Institut für Informatik"), default=None)
    if start is None:
        raise RuntimeError("heading 'Institut für Informatik' not found (page layout changed)")
    out = []
    for t in toks[start + 1:]:
        if t.startswith("Universität Leipzig"):
            break
        m = re.match(r"(Professor(?:in)?|JProf\.) (Dr\. [^(:]+?)\s*(?:\(([^)]*)\))?:?\s*$", t)
        if m:
            out.append(prof("Universität Leipzig", "Fakultät für Mathematik und Informatik", "Prof. " + m.group(2), m.group(3) or "", "Institut für Informatik", url))
    return out


def siegen():
    """Department Elektrotechnik und Informatik (NT-Fakultät) start page (the old eti.uni-siegen.de/dekanat/institute page now redirects to the university home page):
    h2 'Schwerpunkt ...' sections, each chair an h3 followed by its professor(s) ('Prof. Dr. A und Prof. Dr. B'). Only the computer-science Schwerpunkte
    (Embedded System, Visual Computing) are read; Dr. entries are skipped, chairs without a named professor (vacant) give no row."""
    url = "https://www.uni-siegen.de/department-elektrotechnik-und-informatik"
    page = need(url)
    out = []
    for sec in re.split(r"(?=<h2[^>]*>\s*Schwerpunkt)", page)[1:]:
        head = plain(sec.split("</h2>", 1)[0])
        if not re.search(r"Embedded System|Visual Computing", head):
            continue
        sec = re.split(r"<h2", sec[5:], 1)[0]  # up to the next h2
        for card in re.split(r"(?=<h3)", sec)[1:]:
            chair = plain(card.split("</h3>", 1)[0])
            m = re.search(r">\s*((?:(?:Jun|Univ)\.-)?Prof\.[^<>]*?)\s*<", card.split("</h3>", 1)[1]) if "</h3>" in card else None  # the professor line is a text node of its own
            for nm in re.split(r"\s+(?:und|&)\s+(?=(?:(?:Jun|Univ)\.-)?Prof)", plain(m.group(1)) if m else ""):
                if re.match(r"(?:(?:Jun|Univ)\.-)?Prof", nm):
                    out.append(prof("Universität Siegen", "Naturwissenschaftlich-Technische Fakultät", nm, chair, "Department Elektrotechnik und Informatik", url))
    return out


def wuppertal():
    """Informatik (cs.uni-wuppertal.de) 'Professors and Instructors': 'Professors' block of 'Prof. Dr. Name' / chair pairs, up to 'Lecturers'. The page mixes in the applied-mathematics
    and electrical-engineering professors who belong to the programme; all of them are taken (the list is the computer-science department's own). Apl. Prof. is skipped."""
    url = "https://cs.uni-wuppertal.de/en/computer-science/professors-and-instructors/"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t == "Professors" and i + 1 < len(toks) and toks[i + 1].startswith("Prof.")), None)
    if start is None:
        raise RuntimeError("block 'Professors' not found (page layout changed)")
    out = []
    for i in range(start + 1, len(toks) - 1):
        if toks[i] in ("Lecturers", "Lecturer"):
            break
        if re.match(r"Prof\.? ", toks[i]):
            out.append(prof("Universität Wuppertal", "Informatik", toks[i], toks[i + 1], "", url))
    return out


def freiberg():
    """Institute of Computer Science (Fakultät für Mathematik und Informatik), start page block 'Professorships': per professorship an image (with photographer credit), the chair title,
    'Prof. Dr. Name' and the chair title again; the line after the name is the topic. The mathematics institutes of the faculty are not read."""
    url = "https://tu-freiberg.de/en/faculty1/institute-for-computer-science"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t == "Professorships"), None)
    if start is None:
        raise RuntimeError("heading 'Professorships' not found (page layout changed)")
    out, seen = [], set()
    for i in range(start + 1, len(toks) - 1):
        if toks[i].startswith("Visitor address"):
            break
        if re.match(r"Prof\.? ", toks[i]) and toks[i] not in seen:
            seen.add(toks[i])
            out.append(prof("TU Bergakademie Freiberg", "Fakultät für Mathematik und Informatik", toks[i], toks[i + 1], "Institut für Informatik", url))
    return out


def bayreuth():
    """Institut für Informatik (Fakultät für Mathematik, Physik und Informatik), 'Lehrstühle | Professuren': one collapsible heading per chair 'Angewandte Informatik IV - Prof. Dr. Name - Topic'.
    Retired professors are listed in a separate block without such a heading and are not read."""
    url = "https://www.ai.uni-bayreuth.de/de/professoren/index.html"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    out, seen = [], set()
    for t in (t.replace("\xa0", " ") for t in toks):
        m = re.match(r"Angewandte Informatik [IVX]+ - (Prof\..*?)\s+- (.+)$", t)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(prof("Universität Bayreuth", "Fakultät für Mathematik, Physik und Informatik", m.group(1), m.group(2), "Institut für Informatik", url))
    if not out:
        raise RuntimeError("no 'Angewandte Informatik N - Prof. ...' headings found (page layout changed)")
    return out


def hagen():
    """Fakultät für Mathematik und Informatik, 'Lehrende': block 'Lehrstühle und ihre Professorinnen und Professoren' = pairs 'Prof. Dr. Name' / 'Lehrstuhl für ...' (soft hyphens removed), up to the
    'Arbeitsgebiete' block. Mathematics chairs are in the same list and are kept (mixed Mathematik + Informatik faculty, like Jena or Marburg); honorary, apl. and former professors are not read."""
    url = "https://www.fernuni-hagen.de/mi/fakultaet/lehrgebiete.shtml"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).replace("\xad", "").split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t.startswith("Lehrstühle und ihre Professor")), None)
    if start is None:
        raise RuntimeError("block 'Lehrstühle und ihre Professorinnen und Professoren' not found (page layout changed)")
    out = []
    for i in range(start + 1, len(toks) - 1):
        if toks[i].startswith("Arbeitsgebiete und ihre"):
            break
        if re.match(r"(?:Jun\.-)?Prof\. ", toks[i]):
            out.append(prof("FernUniversität in Hagen", "Fakultät für Mathematik und Informatik", toks[i], re.sub(r"^Lehrstuhl für ", "", toks[i + 1]), "", url))
    return out


def unibw():
    """Fakultät für Informatik, 'Professuren der Fakultät für Informatik': per institute heading 'Institut INFn - ...' the entries 'Univ.-Professor(in) Dr. Name' followed by
    '(Professur für ...)' (the brackets sometimes sit in separate text nodes). Name as written on the page (one entry has no first name)."""
    url = "https://www.unibw.de/inf/professuren"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t.startswith("Professuren der Fakultät für Informatik")), None)
    if start is None:
        raise RuntimeError("heading 'Professuren der Fakultät für Informatik' not found (page layout changed)")
    out, unit = [], ""
    for i in range(start + 1, len(toks)):
        t = toks[i]
        if t == "Kontakt":
            break
        if t.startswith("Institut INF"):
            unit = t
        elif t.startswith("Univ.-Professor"):
            topic = []
            for u in toks[i + 1:i + 4]:
                if u.startswith(("Univ.-Professor", "Institut INF", "Kontakt")):
                    break
                topic.append(u)
            topic = re.sub(r"^\(?\s*(?:Professur\s+(?:für\s+)?)?|\s*\)$", "", " ".join(topic).strip("() "))
            name = re.sub(r"^Univ\.-Professor(?:in)? ", "Prof. ", t)
            name = re.sub(r",\s*Ph\.?D\..*$", "", name)  # 'Klaus Buchenrieder, Ph.D. M.S. (OSU)'
            out.append(prof("Universität der Bundeswehr München", "Fakultät für Informatik", name, topic, unit, url))
    return out


def hildesheim():
    """Fachbereich 4, overview 'Forschungsgruppen im Bereich Informatik' (the page is still marked ENTWURF = draft): per institute a heading, then one line per group
    'Group (ABBR), Prof. Dr. Name'. Only institutes whose name says Informatik are read (Institut für Informatik, Betriebswirtschaft und Wirtschaftsinformatik, Mathematik und
    Angewandte Informatik); the Institut für Informationswissenschaft und Sprachtechnologie is not. Lines with 'vertreten durch', PD or Dr. only (no professor) give no row."""
    url = "https://www.uni-hildesheim.de/fb4/institutsverbund-informatik/"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t.startswith("Die Forschungsgruppen im Bereich Informatik sind")), None)
    if start is None:
        raise RuntimeError("list 'Die Forschungsgruppen im Bereich Informatik sind ...' not found (page layout changed)")
    out, unit = [], ""
    for t in toks[start + 1:]:
        if t.startswith("Professor "):  # the contact cards below the list
            break
        if t.startswith("Institut für") and "," not in t:
            unit = t
            continue
        m = re.match(r"(.*?)\s*(?:\([^)]*\))?,\s*(Prof\.? ?Dr\.? .*)$", t)
        if m and re.search(r"informatik", unit, re.I):
            out.append(prof("Universität Hildesheim", "Fachbereich 4", m.group(2), re.sub(r"\s*\(.*", "", m.group(1)), unit, url))
    return out


def constructor():
    """Constructor University Bremen, faculty directory: entries 'Name / Title' followed by 'Read more'. Kept: Professor / Associate / Assistant Professor whose title field says computer, informatics or
    software ('Professor of Computer Science', 'Assistant Professor of Computer Science and Engineering'); adjunct professors and lecturers are skipped. The title field serves as unit."""
    url = "https://constructor.university/directory/faculty"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url)))).split("\n") if t.strip()]
    out, cur = [], []
    for t in toks:
        if t == "Read more":
            if len(cur) >= 2 and re.match(r"(?:Assistant |Associate )?Professor (?:of|for|in) ", cur[-1]) and re.search(r"computer|informatik|informatics|software", cur[-1], re.I):
                out.append(prof("Constructor University Bremen", "School of Computer Science & Engineering", "Prof. " + re.sub(r"\s+", " ", cur[-2]), "", cur[-1], url, cur[-1]))
            cur = []
        else:
            cur.append(t)
    if not out:
        raise RuntimeError("no 'Professor of Computer Science' entries found (page layout changed)")
    return out


def _lu_name(t):
    """'Prof. Jean-Sébastien CORON' / 'Assoc. Prof Marko RANCIC' / 'Leon VAN DER TORRE' -> 'Prof. Jean-Sébastien Coron' (upper-case words get normal case, particles stay lower case)."""
    t = re.sub(r"^(?:Assist\.|Assoc\.)?\s*Prof\.?\s+(?:Dr\.?\s+)?", "", t.strip())
    t = " ".join((w if w == "van" else w.capitalize() if w.isupper() and len(w) > 1 else w) if w.lower() not in ("van", "der", "de", "von") else w.lower() for w in t.split())
    return "Prof. " + t


def luxembourg():
    """University of Luxembourg, Department of Computer Science (FSTM). Only the static pages are read, so the list is PARTIAL: from the people page the head of department and the 'Professors'
    accordion as far as it is shown without its 'Load more' button (6 of them, found by JavaScript from an internal people API that is not called here), plus the 'Head of Group' of every research
    group of the department whose title says professor. DCS professors who neither head a group nor are among the first six are not found."""
    base = "https://www.uni.lu/fstm-en/research-departments/department-of-computer-science/"
    toks = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(base + "people/")))).split("\n") if t.strip()]
    start = next((i for i, t in enumerate(toks) if t == "Our people"), None)
    if start is None:
        raise RuntimeError("heading 'Our people' not found (page layout changed)")
    found = {}
    section = ""
    for i in range(start + 1, len(toks) - 2):
        t = toks[i]
        if t in ("Researchers", "Administrative Staff", "Technical Staff", "Share this"):
            break
        if t in ("Head of Department", "Professors"):
            section = t
        elif section and toks[i + 2] in ("Learn more",) and re.match(r"(?:Prof |Prof\. )", t) or section == "Professors" and toks[i + 1:i + 2] and toks[i + 3:i + 4] == ["Learn more"]:
            found.setdefault(_lu_name(t).casefold(), prof("University of Luxembourg", "Faculty of Science, Technology and Medicine", _lu_name(t), "", "Department of Computer Science", base + "people/"))
    page = need(base + "research/")
    i = page.find('id="our-research-groups"')
    urls = list(dict.fromkeys(re.findall(r'href="(https://www\.uni\.lu/fstm-en/research-groups/[^"]+)"', page[i:page.find("Publications", i) + 200])))
    for u in urls:
        g = [t.strip() for t in html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"(?s)<(script|style).*?</\1>", "", need(u)))).split("\n") if t.strip()]
        group = g[g.index("View breadcrumb") + 4] if "View breadcrumb" in g else u
        for n, t in enumerate(g):
            if re.match(r"Heads? of (?:the )?Group|Group (?:leader|head)|Principal Investigator", t, re.I) and n + 2 < len(g):
                for name, title in ((g[n + 1], g[n + 2]), ) + (((g[n + 3], g[n + 4]), ) if n + 4 < len(g) and re.search(r"professor", g[n + 4], re.I) else ()):
                    if re.search(r"professor", title, re.I) and not re.match(r"Dr\.", name):
                        found.setdefault(_lu_name(name).casefold(), prof("University of Luxembourg", "Faculty of Science, Technology and Medicine", _lu_name(name), group, "Department of Computer Science", u, title))
    return list(found.values())


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
        out.append(prof("Universität Trier", "Fachbereich IV", f"{' '.join(first.split())} {last}", topic, "Informatikwissenschaften", up.urljoin(base, link.group(1)) if link and link.group(1) != "#" else base + "team/professuren", rest))
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
            out.append(prof("Universität Koblenz", "Fachbereich 4 Informatik", re.sub(r"^J(?:un\.?-?)?Prof\.\s*", "", p["Title"]), topic, KOBLENZ.get(path[3] if len(path) > 3 else "", ""), up.urljoin(url, p["@id"]), p["Title"] + " " + desc))
    if not out:
        raise RuntimeError("layout changed")
    return out


SOURCES_DE2 = [wuppertal, freiberg, bayreuth, hagen, unibw, hildesheim, constructor, luxembourg, lmu, koblenz, erlangen_cs, bremen, konstanz, kiel, muenster, bielefeld, oldenburg, halle, leipzig, siegen, trier, clausthal]
