"""Current professors of some German universities -> professors.json (separate from the job ads).
Same polite fetching as the job-ad scraper (common/fetch.py) (per-day cache, >= 2 s between requests, robots.txt checked for every host).
Public staff pages only; stored per professor: name, topic (chair / Fachgebiet), unit (institute / department), faculty, link. No contact data.
Usage (from the project root): python3 -I profs/profs_scrape.py"""
import datetime
import html
import json
import os
import re
import sys
import urllib.parse as up

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]  # python -I does not add the script's folder; common/ lives in the project root
from common.fetch import fetch, robots_ok, run_sources, STATS
from common.text import plain
from cs_filter import cs_hit
from roles import role_of

TITLE = re.compile(r"\b(?:Prof\.\s?in|T\.-T\.-Prof\.?|T\.-T\.-|Univ\.?-?\s?Prof\.?|Jun\.?-?\s?Prof\.?|Prof\.?|Professor(?:in)?|apl\.|PD|Dr\.?|habil\.?|(?:rer|nat|sc|techn|oec|pol|agr|forest|paed|jur|dent|vet|hum|soc|publ|disc|theol|troph|math|soc)\.?(?=\s)|Ing\.?|-Ing\.?|ir\.|nat\.?|iur\.?|phil\.?|med\.?|h\. ?c\.?|mult\.?|M\.?\s?Sc\.?|LL\.?\s?M\.?(?:\s?\([^)]*\))?|MBA|Dipl\.-\w+\.?|Dr\.-Ing\.?|PhD|Ph\.? ?D\.?|DPhil)(?=[\s,.]|$)", re.I)


def clean_name(s):
    """'Univ.-Prof. Dr.-Ing. Rolf Findeisen' / 'Beckmann, Roland Michael, Dr. iur.' / 'Abetz, Univ.-Prof. Dr. Volker' -> 'Rolf Findeisen' / 'Roland Michael Beckmann' / 'Volker Abetz'."""
    s = html.unescape(re.sub(r"\s+", " ", s)).strip()
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)  # '(gemeinsam mit Hereon)'
    last = ""
    if "," in s:
        last, s = (x.strip() for x in s.split(",", 1))
        if not TITLE.sub(" ", s).replace(",", " ").strip(" .-"):  # 'Martin Butz, Ph.D.': the part after the comma is only a degree, not the first name
            s, last = last, ""
    s = TITLE.sub(" ", s).replace(",", " ")
    s = re.sub(r"(?<=\s)[-.]+(?=\s|$)|^[-.]+\s", " ", s)
    first = " ".join(s.split())
    return f"{first} {last}".strip()


def prof(uni, faculty, name, topic="", unit="", url="", role=""):
    """`role`: the position if the page says it (see roles.py); otherwise it is guessed from the title printed before the name and from the topic."""
    topic = re.sub(r"\s+", " ", html.unescape(topic).replace("\u200b", "")).strip(" ,;")
    raw = html.unescape(name)
    return dict(university=uni, faculty=faculty, unit=unit, name=clean_name(re.sub(r"^Professor(?:en)?vertretung:\s*|^Professurvertretung:\s*", "", raw)), topic=topic, url=url, role=role_of(raw, topic, role))


def need(url):
    if not robots_ok(url):
        raise RuntimeError(f"robots.txt disallows {url}")
    return fetch(url)


CHEMNITZ = {"nw": "Fakultät für Naturwissenschaften", "ma": "Fakultät für Mathematik", "mb": "Fakultät für Maschinenbau",
            "et": "Fakultät für Elektrotechnik und Informationstechnik", "if": "Fakultät für Informatik", "ww": "Fakultät für Wirtschaftswissenschaften",
            "pf": "Philosophische Fakultät", "hs": "Fakultät für Human- und Sozialwissenschaften"}


def chemnitz():
    out = []
    for code, fak in CHEMNITZ.items():
        t = need(f"https://www.tu-chemnitz.de/urz/www/php/examples/ldap4.php?fak={code}")
        for li in re.findall(r"(?s)<li>(.*?)</li>", t.split("tucal-proflist", 1)[-1]):
            m = re.search(r'(?s)<strong><a href="([^"]*)">(.*?)</a></strong>\s*<span>(.*?)</span>', li)
            if m:
                topic = re.sub(r"^(?:Juniorprofessur|Professur|Stiftungsprofessur)\s+(?:für\s+)?", "", plain(m.group(2)))
                out.append(prof("TU Chemnitz", fak, plain(m.group(3)), topic, "", m.group(1)))
    return out


DARMSTADT = [("https://www.informatik.tu-darmstadt.de/fb20/professuren_und_gruppenleitungen/index.de.jsp", "Fachbereich Informatik"),  # first: people listed on both pages (joint members such as Hollick, Koch) count as Informatik
             ("https://www.etit.tu-darmstadt.de/fachbereich/professuren_etit/index.de.jsp", "Fachbereich Elektrotechnik und Informationstechnik")]


DARMSTADT_ROLES = [(r"Assistenzprofessur", "Assistant / junior professor"), (r"Vertretungs|Gastprofessur|Zweitmitglieder|Honorarprofessur", "Honorary / visiting / secondary"), (r"Nachwuchsgruppe|Young Investigator", "Group leader")]


def darmstadt():
    """Same CMS on every Fachbereich host: schema.org Person rows; topic = jobTitle (ETIT) or the 'Fachgebiete' cell (Informatik)."""
    out = []
    for url, fak in DARMSTADT:
        page = need(url)
        chunks = page.split('itemtype="https://schema.org/Person"')
        section = ""
        for prev, row in zip(chunks, chunks[1:]):
            sec = re.findall(r'(?s)<th colspan="\d">(.*?)</th>', prev)
            if sec:  # the Informatik page groups its rows: Professuren, Assistenzprofessuren, … Emeriti (often deceased), Privatdozent*innen
                section = plain(sec[-1])
            if re.search(r"Emeriti|Privatdozent", section):
                continue
            role = next((r for rx, r in DARMSTADT_ROLES if re.search(rx, section)), "")
            pre = re.search(r'(?s)itemprop="honorificPrefix">(.*?)</span>', row)
            name = re.search(r'itemprop="name">(.*?)</span>', row)
            job = re.search(r'(?s)itemprop="jobTitle"[^>]*>(.*?)</div>', row) or re.search(r'(?s)class="working-areas [^"]*">(.*?)</td>', row)
            href = re.search(r'itemprop="url" href="([^"]+)"', row)
            if name and pre and ("Prof" in pre.group(1) or role == "Group leader"):  # group leaders (IRG, Athene) have a Dr. title
                out.append(prof("TU Darmstadt", fak, name.group(1), plain(job.group(1)) if job else "", "", up.urljoin(url, href.group(1)) if href else url, role or plain(pre.group(1))))  # the printed title (Prof. ...) when the section gives no position
    return out


def heidelberg_mathinf():
    """informatik.uni-heidelberg.de people list: Institut fuer Informatik, Institut fuer Technische Informatik (ZITI), IWR, Computerlinguistik, DKFZ. PD/Dr. rows skipped."""
    url = "https://www.informatik.uni-heidelberg.de/about/personen"
    out = []
    for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", need(url)):
        c = [plain(x) for x in re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)]
        if len(c) >= 2 and re.search(r",\s*Prof\.", c[0]) and "PD" not in c[0]:
            out.append(prof("Universität Heidelberg", "Fakultät für Mathematik und Informatik", c[0], "", c[1], url))
    return out


def frankfurt():
    """Institut für Informatik (FB 12) professor page; the page repeats every card (mobile + desktop), so dedupe by name.
    Seniorprof. rows (retired) and the 'Zweitmitgliedschaften' (professors of other Fachbereiche) are skipped."""
    url = "https://www.uni-frankfurt.de/f7/professorinnen-und-professoren-103454214"
    page = need(url).split("Zweitmitgliedschaften", 1)[0]
    out, seen = [], set()
    for m in re.finditer(r'(?s)<strong>(Prof\.[^<]*)</strong>(.*?)</div>\s*</div>\s*</div>', page):
        name = plain(m.group(1))
        if name in seen:
            continue
        seen.add(name)
        rest = m.group(2)
        link = re.search(r'<a href="([^"]+)"', rest)
        topic = plain(re.sub(r"gefördert durch.*", "", rest, flags=re.S))
        out.append(prof("Goethe-Universität Frankfurt", "Fachbereich Informatik und Mathematik", name, topic, "Institut für Informatik", up.urljoin(url, link.group(1)) if link else url))
    return out


def bamberg():
    """Fakultät WIAI, 'Die Fachgruppen im Überblick': one card per Fachgruppe (chair) with the professor as first list link; 'N.N.' chairs are vacant."""
    url = "https://www.uni-bamberg.de/wiai/faecher/faecher/"
    page = need(url).split('id="content-main"', 1)[1]
    out, unit = [], ""
    for m in re.finditer(r'<div class="ce-bodytext"><h2>.*?<strong>(.*?)</strong>|class="heading__link">\s*(.*?)\s*</a>.*?<ul><li><a href="([^"]*)">(.*?)</a>', page, re.S):
        if m.group(1):
            unit = plain(m.group(1))
            continue
        name = plain(m.group(4))
        if "Prof" not in name:
            continue
        out.append(prof("Universität Bamberg", "Fakultät Wirtschaftsinformatik und Angewandte Informatik", name, plain(m.group(2)), unit, up.urljoin(url, m.group(3))))
    return out


def hannover():
    url = "https://www.fei.uni-hannover.de/fakultaet/institute-fachgebiete"
    out = []
    for card in need(url).split('class="c-card__title')[1:]:
        inst = plain(card.split("</h3>", 1)[0].split(">", 1)[-1])
        for m in re.finditer(r'(?s)<a href="([^"]+)"[^>]*class="c-list__link[^"]*">(.*?)</a>.*?c-list__subline">(.*?)</div>', card.split("c-card__button-wrap")[0]):
            for person in re.split(r",\s*(?=(?:Jun\.-)?Prof\.|PD |Dr\. )", plain(m.group(3)).strip()):  # one Fachgebiet can have several professors
                out.append(prof("Leibniz Universität Hannover", "Fakultät für Elektrotechnik und Informatik", person, re.sub(r"^Fachgebiet ", "", plain(m.group(2))), inst, m.group(1)))
    return out


def hamburg():
    """Fachbereich Informatik own professor list (Fiona): 'Ordentliche Professor:innen' + 'nach Par. 17 HmbHG'. Replaces the whole-MIN scrape (246 rows, mostly Physik/Chemie/...).
    Second members (Moeller, Nuettgens, Voss ...), Vertretung, PD, guests, retired are excluded."""
    url = "https://www2.informatik.uni-hamburg.de/fiona/pers.php?lang=de&ltype=ordner&group=PROF"
    out = []
    for m in re.finditer(r'(?s)<div class="mitarbeiterin" data-initial="([^"]*)" data-institute="([^"]*)".*?<h4><a href="([^"]*)">(.*?)</a></h4>(.*?)(?=<a name=|$)', need(url)):
        if m.group(1) not in ("ordentliche professor:innen", "professor:innen nach § 17 hmbhg"):
            continue
        topics = "; ".join(plain(x) for x in re.findall(r"(?s)<li>(.*?)</li>", m.group(5))[:3])
        out.append(prof("Universität Hamburg", "Fachbereich Informatik (MIN-Fakultät)", plain(m.group(4)), topics, m.group(2), m.group(3)))
    return out


def ulm():
    """Fakultät IngInf-Psych, Institut für Informatik: table of Abteilungen (institute link) with their professors below the link."""
    url = "https://www.uni-ulm.de/in/fakultaet/institute/informatik/"
    out = []
    for row in re.findall(r"(?s)<tr><td[^>]*>(.*?)</td></tr>", need(url).split("contenttable", 1)[1]):
        head, *people = re.split(r"<br\s*/?>", row)
        a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', head)
        if not a:
            continue
        abbr, _, topic = plain(a.group(2)).partition("–")
        for p in people:
            if re.search(r"Prof", p):
                out.append(prof("Universität Ulm", "Fakultät für Ingenieurwissenschaften, Informatik und Psychologie", plain(p), topic.strip(), "Institut für Informatik", up.urljoin(url, a.group(1))))
    return out


def greifswald():
    """Institut für Mathematik und Informatik (research page: 'Topic - Prof. Name' links; 'Dr.' rows are not professors) + Institute of Data Science (heads of groups, listed under 'Professors')."""
    out = []
    url = "https://math-inf.uni-greifswald.de/forschung/"
    for href, txt in re.findall(r'<a href="(/forschung/[^"]+)"[^>]*class="internal-link">([^<]*- Prof\.[^<]*)</a>', need(url)):
        topic, name = plain(txt).rsplit(" - ", 1)
        out.append(prof("Universität Greifswald", "Mathematisch-Naturwissenschaftliche Fakultät", name, re.sub(r"^Juniorprofessur\s+", "", topic), "Institut für Mathematik und Informatik", up.urljoin(url, href)))
    url = "https://datascience.uni-greifswald.de/team/"
    for head, href, name in re.findall(r'(?s)<h2 class="">\s*Head of ([^<]*?)\s*</h2>.*?<a href="(/team/[^"]+)"[^>]*>([^<]+)</a>', need(url)):
        out.append(prof("Universität Greifswald", "Mathematisch-Naturwissenschaftliche Fakultät", name, re.sub(r"\s+[Gg]roup$", "", head), "Institute of Data Science", up.urljoin(url, href)))
    return out


def dresden():
    url = "https://tu-dresden.de/ing/informatik/die-fakultaet/institute-und-professuren-1"
    out = []
    for sec in need(url).split("<h3>")[1:]:
        unit = plain(sec.split("</h3>", 1)[0])
        for li in re.findall(r"(?s)<li>(.*?)</li>", sec):
            em = re.findall(r"(?s)<em>(.*?)</em>", li)  # "Gumhold, " and "Prof. Dr. Stefan" can be two <em>
            if not em or "Prof" not in "".join(em) or "Vertretung" in "".join(em):  # acting professors are not listed
                continue
            chair = plain(re.split(r"<br\s*/?>", li, 1)[0])
            out.append(prof("TU Dresden", "Fakultät Informatik", plain(" ".join(em)), re.sub(r"^(?:Juniorprofessur|Professur) (?:für )?", "", chair), unit, url))
    return out


def kit():
    url = "https://www.informatik.kit.edu/english/5097.php"
    out = []
    for sec in re.split(r"(?=<h[34][ >])", need(url))[1:]:
        head = plain(sec.split("</h", 1)[0])
        if re.search(r"Emeriti|retired|Affiliated", head):
            continue
        for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", sec):
            c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
            if len(c) >= 2 and "Prof" in plain(c[1]):
                href = re.search(r'href="([^"]*)"', c[1])
                out.append(prof("KIT", "KIT-Fakultät für Informatik", plain(c[1]), plain(c[0]), re.sub(r"\s*\(\w+\)$", "", head), up.urljoin(url, href.group(1)) if href else url))
    return out


def tuebingen():
    url = "https://uni-tuebingen.de/en/faculties/faculty-of-science/departments/computer-science/research-groups/"
    out = []
    for m in re.finditer(r'(?s)<p><strong>((?:Jun\.-|Univ\.-)?Prof[^<]*)</strong><br>\s*(?:<a [^>]*?href="([^"]*)"[^>]*>(.*?)</a>|([^<]+))(.*?)</p>', need(url)):
        name = plain(m.group(1))
        if re.search(r"coopted|honorary|apl\.", name, re.I):
            continue
        out.append(prof("Universität Tübingen", "Fachbereich Informatik", name, plain(m.group(3) or m.group(4)), " / ".join(plain(x) for x in re.findall(r"<i>(.*?)</i>", m.group(5)) if plain(x) != "|"), up.urljoin(url, m.group(2) or url)))
    return out


def saarland_cs():
    """Job title = <br>-separated lines: positions and affiliations first, the research topic last
    ('Scientific Director, MPI SWS<br>Professor, Saarland University<br>Distributed Systems'). Topic = last line; other institutions go to the unit."""
    url = "https://saarland-informatics-campus.de/en/forschung-research/advisors/"
    sec = need(url).split("Professors of Saarbrücken Computer Science", 1)[1].split("<h2", 1)[0]
    out = []
    for m in re.finditer(r'CS_person_name">(.*?)</div><div class="CS_person_jobtitle">(.*?)</div>', sec):
        lines = [plain(x) for x in re.split(r"<br\s*/?>", m.group(2))]
        lines = [x for x in lines if x]
        if len(lines) > 1:
            topic = lines[-1]
            others = [re.sub(r"^(?:Scientific Director|Co-opted Professor|Seniorprofessor|Professor),?\s*", "", x) for x in lines[:-1]]
            unit = "; ".join(x for x in others if x and not re.fullmatch(r"Saarland University|Department of Computer Science", x))
        else:
            topic, unit = re.sub(r"^Professor,? (?:Saarland University)?\s*", "", lines[0] if lines else ""), ""
        out.append(prof("Universität des Saarlandes", "Fakultät für Mathematik und Informatik", plain(m.group(1)), topic, unit, url, " ".join(lines)))
    return out


def rwth():
    url = "https://www.informatik.rwth-aachen.de/cms/informatik/forschung/Forschungsbereiche/~bnrzti/Liste-der-Forschungsgruppen2/lidx/1/"
    out = []
    for sec in need(url).split("<h2>")[1:]:
        unit = plain(sec.split("</h2>", 1)[0])
        for th, row in re.findall(r"(?s)<th[^>]*>.*?</th>\s*<th[^>]*>(.*?)</th>.*?<tbody>(.*?)</tbody>", sec):
            cells = re.findall(r"(?s)<td[^>]*>(.*?)</td>", row)
            txt = plain(cells[1]) if len(cells) > 1 else ""
            m = re.match(r"((?:Univ\.-)?Prof\..*?)\s*(?:Tel\.|$)", txt)
            if m and not re.search(r"i\. ?R\.|Priv|Apl|apl", m.group(1)):
                out.append(prof("RWTH Aachen", "Fakultät für Mathematik, Informatik und Naturwissenschaften", m.group(1), plain(th), unit, url))
    return out


FREIBURG = {"iif": "Institut für Informatik", "imtek": "IMTEK", "inatech": "INATECH"}


def freiburg():
    url = "https://uni-freiburg.de/tf/forschung/professuren/"
    out = []
    for tab_id, body in re.findall(r'(?s)<section[^>]*?\bid="(\w+)"[^>]*>(.*?)</section>', need(url)):
        for tr in re.findall(r"(?s)<tr>(.*?)</tr>", body):
            c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
            if len(c) >= 3:
                out.append(prof("Universität Freiburg", "Technische Fakultät", f"{plain(c[1])} {plain(c[0])}", plain(c[2]), FREIBURG.get(tab_id, tab_id), url, "Professur"))  # the page is the list of the Technische Fakultät Professuren
    return out


def tum():
    """Topic = research-area slug of the link target (the page shows names only)."""
    url = "https://www.cs.cit.tum.de/en/cs/people/professors/"
    out = []
    for m in re.finditer(r'(?s)c-tummemberlist__name">\s*<a href="([^"]*)"[^>]*>\s*<span class="title">(.*?)</span>\s*(.*?)</a>', need(url)):
        area = re.search(r"/research/areas/([^/]+)/", m.group(1))
        out.append(prof("TU München", "School of Computation, Information and Technology", plain(m.group(3)), area.group(1).replace("-", " ") if area else "", "Department of Computer Science", up.urljoin(url, m.group(1)), plain(m.group(2))))
    return out


def tum_cit():
    """A-Z list of all chairs of the CIT school (Mathematics, Computer Science, Computer Engineering, Electrical Engineering); department from the link host."""
    url = "https://www.cit.tum.de/en/cit/school/organization/chairs-professorships/"
    dep = {"cs.cit": "Department of Computer Science", "in": "Department of Computer Science", "ce.cit": "Department of Computer Engineering",
           "ee.cit": "Department of Electrical Engineering", "math.cit": "Department of Mathematics"}
    out = []
    for m in re.finditer(r'<li><a href="([^"]*)"[^>]*>(.*?)</a>(?:&nbsp;|\s)*\((Prof[^)]*)\)</li>', need(url)):
        host = (up.urlparse(m.group(1)).hostname or "").removeprefix("www.").removesuffix(".tum.de")
        host = "in" if host.endswith(".in") else host
        out.append(prof("TU München", "School of Computation, Information and Technology", plain(m.group(3)), plain(m.group(2)), dep.get(host, ""), m.group(1), m.group(3)))
    return out


def stuttgart():
    url = "https://www.f05.uni-stuttgart.de/informatik/fachbereich/professorinnen-und-professoren/"
    out = []
    for sec in need(url).split("<h2")[1:]:
        head = plain(sec.split("</h2>", 1)[0].split(">", 1)[-1])
        if not re.match(r"Professorinnen und Professoren|Juniorprofessor", head):
            continue
        for m in re.finditer(r'class="FirstLastName" href="([^"]*)"[^>]*>(.*?)</a>', sec):
            out.append(prof("Universität Stuttgart", "Fakultät 5, Fachbereich Informatik", plain(m.group(2)), "", "", m.group(1), head))
    return out


def goettingen():
    url = "https://uni-goettingen.de/de/628113.html"
    sec = need(url).split("Professor*innen:</h3>", 1)[1].split("<h3>", 1)[0]
    return [prof("Universität Göttingen", "Institut für Informatik", plain(m.group(2)), "", "", m.group(1)) for m in re.finditer(r'<li><a href="([^"]*)"[^>]*>(.*?)</a>', sec)]


TUB_CS = ("Softwaretechnik und Theoretische Informatik", "Technische Informatik und Mikroelektronik", "Wirtschaftsinformatik und Quantitative Methoden", "Telekommunikationssysteme")


def tu_berlin():
    """Fakultät IV table (main table only: honorary, apl., second-member and former sections come after the first h2); CS institutes only."""
    url = "https://www.tu.berlin/eecs/einrichtungen/professuren-fachgebiete"
    page = need(url)
    body = page.split("Fakultät IV: Professuren", 1)[-1].split("<h2", 1)[0] if "Fakultät IV: Professuren" in page else page
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", body):
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 4 and plain(c[0]) not in ("", "N.N.", "N. N.") and any(x in plain(c[3]) for x in TUB_CS):
            href = re.search(r'href="([^"]+)"', c[0])
            out.append(prof("TU Berlin", "Fakultät IV Elektrotechnik und Informatik", plain(c[0]), plain(c[2]), plain(c[3]), up.urljoin(url, href.group(1)) if href else url, "Professur"))  # the table is the Fakultät IV Professuren list
    return out


def hpi_profs():
    url = "https://hpi.de/en/research/professorships/"
    out = []
    for blk in need(url).split("cs-image-text__text")[1:]:
        h = re.search(r"(?s)<h4[^>]*>(.*?)</h4>", blk)
        p = re.search(r"(?s)</h4>.*?<p>(.*?)</p>", blk)
        href = re.search(r'href="([^"]+)"', blk)
        if h and "Prof" in plain(h.group(1)):
            out.append(prof("Hasso-Plattner-Institut", "Digital-Engineering-Fakultät (HPI / Universität Potsdam)", plain(h.group(1)), plain(p.group(1)) if p else "", "", up.urljoin(url, href.group(1)) if href else url))
    return out


def dortmund():
    """Same as now but Jun.-Prof. rows (Feurer, Rehs) were skipped by startswith('Prof')."""
    from profs_scrape import need as _need
    url = "https://cs.tu-dortmund.de/lehrstuehle/professuren/"
    out, area = [], ""
    for part in re.split(r"(?=<h[24][ >])", _need(url).split('<h1 class="">Professuren', 1)[-1]):
        h2 = re.match(r"<h2[^>]*>(.*?)</h2>", part, re.S)
        if h2:
            area = plain(h2.group(1))
        if re.search(r"Kooptation|Honorar|Pensioniert|emeritiert", area):
            continue
        for m in re.finditer(r'(?s)class="tile-title">(.*?)</h4>', part):
            name = plain(m.group(1))
            href = re.findall(r'<a [^>]*href="([^"]+)"', part[:m.start()])
            if name.startswith(("Prof", "Jun.-Prof")) and "apl" not in name:
                out.append(prof("TU Dortmund", "Fakultät für Informatik", name, "", area, href[-1] if href else url))
    return out


def fu_berlin():
    url = "https://www.mi.fu-berlin.de/inf/groups/index.html"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", need(url).split("Ehemals aktive Gruppen", 1)[0]):
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 2:
            for m in re.finditer(r'<a [^>]*href="([^"]+)"[^>]*>(Prof[^<]*)</a>([^<]*)', c[1]):
                if not re.search(r"ausgeschieden|Ruhestand", m.group(3)):
                    out.append(prof("FU Berlin", "Fachbereich Mathematik und Informatik", m.group(2), plain(c[0]), "Informatik", up.urljoin(url, m.group(1))))
    return out


def osnabrueck():
    """University-wide table of all professorships (Stand on the page): title, first name, surname, Fachbereich, Lehreinheit, Professur."""
    url = "https://www.uni-osnabrueck.de/lehren/unsere-professuren"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", need(url)):
        c = [plain(x) for x in re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)]
        if len(c) >= 6 and c[0].startswith("Prof") and c[2] and "N.N" not in c[2]:
            out.append(prof("Universität Osnabrück", c[3], f"{c[1]} {c[2]}", re.sub(r"\s*FIS-Profil.*", "", c[5]), c[4], url, "Professur"))  # page "Unsere Professuren"
    return out


def paderborn():
    url = "https://cs.uni-paderborn.de/forschung/professoren-und-ihre-fachgebiete"
    out = []
    for blk in need(url).split('class="person-item"')[1:]:
        n = re.search(r'(?s)class="person-name" href="([^"]+)">(.*?)</a>', blk)
        a = re.search(r'(?s)class="area">(.*?)</p>', blk)
        if n and plain(n.group(2)).startswith(("Prof", "Jun")):
            out.append(prof("Universität Paderborn", "Institut für Informatik", plain(n.group(2)), re.sub(r"^[>\s]+", "", plain(a.group(1))) if a else "", "", n.group(1)))
    return out


def kassel():
    url = "https://www.uni-kassel.de/eecs/fachgebiete.html"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", need(url)):
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 2 and re.match(r"Prof", plain(c[1])):
            href = re.search(r'href="([^"]+)"', c[0])
            out.append(prof("Universität Kassel", "Fachbereich Elektrotechnik / Informatik", plain(c[1]), plain(c[0]), "", up.urljoin(url, href.group(1)) if href else url))
    return out


def wuerzburg():
    """Informatik chairs page: one frame per professor (name in the header h3, chair in the bodytext h3); stops before Seniorprofessor / Honorarprofessor / Dozent."""
    url = "https://www.informatik.uni-wuerzburg.de/lehrstuehle-professuren/"
    page = need(url)
    cut = re.search(r"<h3[^>]*>\s*(?:Seniorprofessor|Honorarprofessor|Dozent)", page)
    out = []
    for frame in (page[:cut.start()] if cut else page).split('class="frame frame-default frame-type-textpic')[1:]:
        n = re.search(r'(?s)<header>.*?<h3[^>]*>\s*<a href="([^"]+)">(.*?)</a>', frame)
        c = re.search(r'(?s)class="ce-bodytext">.*?<h3[^>]*>(.*?)</h3>', frame)
        if n and plain(n.group(2)).startswith("Prof"):
            out.append(prof("Universität Würzburg", "Institut für Informatik", plain(n.group(2)), re.sub(r"\s*\(Informatik [IVX]+\)", "", plain(c.group(1))) if c else "", "", up.urljoin(url, n.group(1))))
    return out


def marburg():
    """FB 12 Mathematik und Informatik, current working groups (mathematics and computer science mixed; the working group is the unit)."""
    url = "https://www.uni-marburg.de/de/fb12/arbeitsgruppen"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", need(url)):
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 3:
            n = re.search(r"(?s)<strong>(.*?)</strong><br />\s*(Prof[^<]*)", c[1])
            ag = re.search(r'(?s)<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', c[2])
            topics = "; ".join(plain(x) for x in re.findall(r"(?s)<li>(.*?)</li>", c[2])[:4])
            if n:
                out.append(prof("Universität Marburg", "Fachbereich 12 Mathematik und Informatik", plain(n.group(1)), topics, plain(ag.group(2)) if ag else "", ag.group(1) if ag else url, plain(n.group(2))))
    return out


def jena():
    """FMI employee list; only 'Univ.-Prof.' rows (plain 'Prof.' are mostly emeriti, 'apl.' are not professors). Mathematics and computer science mixed."""
    url = "https://www.fmi.uni-jena.de/180/beschaeftigte"
    out = []
    for li in re.findall(r"(?s)<li data-filter=.*?</li>\s*(?=<li data-filter|</ul>)", need(url)):
        n = re.search(r'(?s)<h2 class="name">(.*?)</h2>', li)
        inst = re.search(r'(?s)class="institution[^"]*">\s*<span>(.*?)</span>', li)
        if n and "Univ.-Prof" in n.group(1):
            out.append(prof("Universität Jena", "Fakultät für Mathematik und Informatik", plain(n.group(1)), plain(inst.group(1)) if inst else "", "", url))
    return out


OVGU_BASE = "https://www.ovgu.de/Universit%C3%A4t/Forschungsprofil/Professoren+und+Professorinnen/"
OVGU = ["Fakult%C3%A4t+f%C3%BCr+Informatik.html"]  # computer science only (the other faculties have pages of the same layout: Mathematik, Naturwissenschaften, Medizin, Humanwissenschaften, Wirtschaft, ETIT)


def magdeburg():
    """Fakultät für Informatik, professor page (same layout on every faculty page; only this one is read); institute = h3, no topic. apl. professors skipped."""
    out = []
    for page in OVGU:
        url = OVGU_BASE + page
        t = need(url)
        fak = plain(re.search(r"(?s)<h1[^>]*>(.*?)</h1>", t).group(1))
        for sec in t.split("<h3")[1:]:
            unit = plain(sec.split("</h3>", 1)[0].split(">", 1)[-1])
            for m in re.finditer(r'(?s)class="person_name">\s*<a href="([^"]+)"[^>]*>\s*<strong>(.*?)</strong>', sec):
                name = plain(m.group(2))
                if re.match(r"(?:Jun\.-)?Prof", name) and "apl." not in name:
                    out.append(prof("Universität Magdeburg", fak, name, "", unit, up.urljoin(url, m.group(1))))
    return out


def mannheim():
    """Business Informatics and Mathematics: keep only the computer-science chairs (drop Institut fuer Mathematik). Tiles without a link (Keuper) are matched too;
    name taken from uma-address-name only (it was polluted for Moerkotte/Slowik)."""
    url = "https://www.wim.uni-mannheim.de/en/about/chairs-and-professors/"
    out = []
    for sec in need(url).split("<h3")[1:]:
        unit = plain(sec.split("</h3>", 1)[0].split(">", 1)[-1])
        if re.search(r"Dean|Mathemati", unit):
            continue
        for m in re.finditer(r'(?s)(?:<a href="([^"]*)"[^>]*>)?\s*<div class="uma-address-picture">.*?uma-address-name">(.*?)</div>\s*<div class="uma-address-position">(.*?)</div>', sec):
            if re.match(r"(?:Jun\.-)?Prof", plain(m.group(2))):
                out.append(prof("Universität Mannheim", "School of Business Informatics and Mathematics", re.sub(r'\s+(?:Lehrstuhl|Chair).*$|^M\. ', '', plain(m.group(2))), plain(m.group(3)), unit, m.group(1) or url))
    return out


def luebeck():
    url = "https://www.uni-luebeck.de/structure/sektionen/informatiktechnik/professorinnen-und-professoren.html"
    out, unit = [], ""
    for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", need(url)):
        h = re.search(r"(?s)<h4[^>]*>(.*?)</h4>", tr)
        if h:
            unit = plain(h.group(1)).title().replace(" Für ", " für ").replace(" Und ", " und ").replace(" Der ", " der ")
            continue
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 2:
            a = re.search(r'(?s)<a href="([^"]*)"[^>]*>(.*?)</a>', c[0])
            if a and "Prof" in plain(a.group(2)):
                out.append(prof("Universität zu Lübeck", "Sektion Informatik/Technik", re.sub(r"\s*\(Direktor(?:in)?\)", "", plain(a.group(2))), plain(c[1]), unit, a.group(1)))
    return out


def augsburg():
    url = "https://www.uni-augsburg.de/de/fakultaet/fai/informatik/prof/"
    out = []
    for box in need(url).split("linkColumns-columnTitle")[1:]:
        area = plain(box.split("</div>", 1)[0].split(">", 1)[-1])
        for m in re.finditer(r'(?s)<a class="linkColumns-columnLink[^"]*" href="([^"]+)">(.*?)</a>', box.split("linkColumns-columnTitle")[0]):
            name = plain(m.group(2))
            if re.match(r"(?:Jun\.-)?Prof\.", name) and "i. R." not in name:
                out.append(prof("Universität Augsburg", "Institut für Informatik", name, area, "", up.urljoin(url, m.group(1))))
    return out


def rptu():
    url = "https://www.cs.rptu.de/en/organisation/ags/"
    page = need(url).split("otherfaculty", 1)[0]
    out = []
    for m in re.finditer(r'(?s)<h3><a href="([^"]*)"[^>]*>(.*?)</a></h3>\s*</div>\s*<div class="description">(.*?)<div', page):
        if "Prof" in plain(m.group(2)):
            out.append(prof("RPTU Kaiserslautern-Landau", "Fachbereich Informatik", plain(m.group(2)), plain(m.group(3)), "", m.group(1)))
    return out


def regensburg():
    """Fakultät INF + Data Science: five Fachbereiche (incl. Wirtschaftsinformatik); each <h2>Fachbereich | X</h2> is followed by <li><a>Lehrstuhl (Prof. Dr. Name)</a>. Vertretungen skipped."""
    url = "https://www.uni-regensburg.de/informatik-data-science/fakultaet/fakultaetstruktur"
    out = []
    for sec in re.split(r"(?=<h2[^>]*>\s*Fachbereich\s*\|)", need(url))[1:]:
        head, body = sec.split("</h2>", 1)
        unit = re.sub(r"^Fachbereich\s*\|\s*", "", plain(head))
        body = re.split(r"<h2", body, 1)[0]
        for m in re.finditer(r'(?s)<li[^>]*>(.*?)</li>', body):  # some entries (e.g. Klier) have no <a>
            t = plain(m.group(1))
            link = re.search(r'href="([^"]*)"', m.group(1))
            n = re.match(r"(.*?)\s*\((Prof[^)]*)\)$", t)
            if n and "Vertretung" not in t:
                out.append(prof("Universität Regensburg", "Fakultät für Informatik und Data Science", n.group(2), n.group(1), unit, up.urljoin(url, link.group(1)) if link else url))
    return out


def passau():
    url = "https://www.fim.uni-passau.de/forschung-und-professuren/lehrstuehle-professuren-und-fachgebiete"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", need(url)):
        c = re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)
        if len(c) >= 2 and re.match(r"Professor", plain(c[0])):
            out.append(prof("Universität Passau", "Fakultät für Informatik und Mathematik", plain(c[0]), plain(c[1]), "", url))
    return out


def potsdam():
    url = "https://www.uni-potsdam.de/de/cs/research/index"
    page = need(url)
    sec = page.split("Professuren am Institut", 1)[-1].split("<h2", 1)[0] if "Professuren am Institut" in page else ""
    out = []
    for m in re.finditer(r'(?s)upce-linkcard__link">\s*<a href="([^"]*)"[^>]*>(.*?)</a>\s*</div>\s*<div class="upce-linkcard__description">(.*?)</div>', sec):
        d = plain(m.group(3)).lstrip("- ").strip()
        if d.startswith("Prof"):
            out.append(prof("Universität Potsdam", "Institut für Informatik und Computational Science", d, plain(m.group(2)), "", m.group(1)))
    return out


def hhu():
    """robots.txt: Crawl-delay 10. The 'quick-links' list (<a href=...>Chair (Prof. Dr. Name)</a>) is the full list; the nav menu in the page only shows a part."""
    url = "https://www.cs.hhu.de/lehrstuehle-und-arbeitsgruppen"
    page = need(url)
    out, seen = [], set()
    for m in re.finditer(r'(?s)<li>\s*<a href="([^"]+)"[^>]*>\s*([^<]*?)\s*\(((?:Jun\.-)?Prof[^)]*)\)\s*<i class="fa', page):
        n = prof("Universität Düsseldorf", "Institut für Informatik", m.group(3).replace("Dr.S", "Dr. S"), plain(m.group(2)), "", up.urljoin(url, m.group(1)))
        if (n["name"], n["topic"]) not in seen:
            seen.add((n["name"], n["topic"]))
            out.append(n)
    return out


def rostock():
    """Fakultät IEF: the Informatik institutes are two: 'Institut für Informatik' and 'Institut für Visual and Analytic Computing' (both CS)."""
    base = "https://www.ief.uni-rostock.de/fakultaet/institute-und-lehrstuehle/lehrende/institute/"
    out = []
    for slug, unit in (("informatik", "Institut für Informatik"), ("visual-and-analytic-computing", "Institut für Visual and Analytic Computing")):
        url = base + slug + "/"
        for m in re.finditer(r'(?s)csc-header"><h3[^>]*>(.*?)</h3><h4[^>]*>(.*?)</h4>', need(url)):
            n, chair = plain(m.group(1)), plain(m.group(2))
            if re.match(r"(?:Jun\.-)?Prof", n) and not re.search(r"i\.\s?R\.|außerplanmäßig|apl|Gast", n + " " + chair):
                out.append(prof("Universität Rostock", "Fakultät für Informatik und Elektrotechnik", n, re.sub(r"^(?:Lehrstuhl|Juniorprofessur) ", "", chair.split(" (ehemals")[0]), unit, url))
    return out


def bochum():
    """Elementor cards: a title span ('Prof. Dr.'), the person link (first / last name widgets) and, in the next terms-list-item, the chair."""
    url = "https://informatik.rub.de/en/faculty/professorships/"
    page = re.split(r">\s*(?:Co-opted professorships|Former&nbsp;members)", need(url))[0]
    chunks = page.split('elementor-post-info__terms-list-item">')[1:]
    out = []
    for i, chunk in enumerate(chunks):
        title = plain(chunk.split("</span>", 1)[0])
        if not re.match(r"Prof", title):  # 'Apl. Prof.' and chair terms are skipped
            continue
        link = re.search(r'(?s)<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', chunk)
        names = [plain(x) for x in re.findall(r'(?s)elementor-widget-container">\s*([^<]+?)\s*</div>', link.group(2))] if link else []
        nxt = plain(chunks[i + 1].split("</span>", 1)[0]) if i + 1 < len(chunks) else ""
        if len(names) >= 2:
            out.append(prof("Ruhr-Universität Bochum", "Fakultät für Informatik", f"{title} {names[0]} {names[1]}", "" if re.match(r"(?:Apl\. )?Prof", nxt) else nxt, "", link.group(1)))
    return out


def cottbus():
    """Fakultät 1 MINT 'Institute & Fachgebiete': one table per Institut (h2.categoryHeading); only the 'Institut für Informatik' block, first table (Fachgebiete).
    N.N. chairs, Gastprofessor and Honorarprofessur (second 'Arbeitsgebiet' table) are skipped."""
    url = "https://www.b-tu.de/fakultaet1/fakultaet/institute-fachgebiete"
    page = need(url)
    block = page.split('<a href="/institut-informatik">Institut für Informatik</a></h2>', 1)[1].split("<h2", 1)[0]
    block = block.split("</table>", 1)[0]
    out = []
    for m in re.finditer(r'(?s)<td class="title">(.*?)</td><td class="sub_title">(.*?)</td>', block):
        name = plain(m.group(2)).replace("Dr.rer.", "Dr. rer. ")
        if not name.startswith("Prof"):
            continue
        a = re.search(r'<a href="([^"]*)"', m.group(1))
        topic = re.sub(r"\s*\((?:gemeinsame Berufung)[^)]*\)", "", plain(m.group(1)))
        out.append(prof("BTU Cottbus-Senftenberg", "Fakultät 1 MINT - Mathematik, Informatik, Physik, Elektro- und Informationstechnik", name, topic, "Institut für Informatik", up.urljoin(url, a.group(1)) if a else url))
    return out


def duisburg_essen():
    """Fakultät für Informatik (formerly Abteilung in the Fakultät für Ingenieurwissenschaften): 'Fachgebiete' page, one card per Abteilung (AI, HCCS, SE, WiInf)
    with a first table of Fachgebiete/Leitung. Seniorprofessuren/Emeriti tables, 'Kooptierte Professor:innen' and N.N. chairs are skipped."""
    url = "https://www.uni-due.de/informatik/fachgebiete.php"
    page = need(url)
    out = []
    for card in re.split(r'<span class="card-title">', page)[1:]:
        unit = plain(card.split("</span>", 1)[0])
        if not unit.startswith("Abteilung"):
            continue
        unit = re.sub(r"\s*\([A-Za-z]+\)$", "", unit)
        table = card.split("</table>", 1)[0]
        for m in re.finditer(r"(?s)<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>", table):
            name = plain(m.group(2))
            name = re.sub(r"\s*\(.*\)$", "", name)  # '(Research Center ...)'
            if not name.startswith("Prof"):
                continue
            a = re.search(r'<a href="([^"]*)"', m.group(2))
            out.append(prof("Universität Duisburg-Essen", "Fakultät für Informatik", name, plain(m.group(1)), unit, up.urljoin(url, a.group(1)) if a else url))
    return out


def giessen():
    """Institut für Informatik (FB 07), 'Personen' page: h3 (name) + first <p> (Professur) for the sections Institutsleitung and Professorinnen und Professoren (before Sekretariat)."""
    url = "https://www.uni-giessen.de/de/fbz/fb07/fachgebiete/informatik/informatik-institut-personen"
    page = need(url)
    page = page.split("<h2>Institutsleitung</h2>", 1)[1].split("<h2>Sekretariat", 1)[0]
    out = []
    for m in re.finditer(r'(?s)<h3 id="[^"]*"><a href="([^"]*)">(.*?)</a></h3>\s*<p>(.*?)</p>', page):
        name = plain(m.group(2))
        if not re.match(r"Prof", name):
            continue
        topic = re.sub(r"(?s)^.*?(?:Professor(?:in)?\s+für\s+|Professor(?:in)?\s+)", "", re.sub(r"\s*&\s*(?:Stellvertretender|Informationssicherheits).*$", "", plain(m.group(3))))
        out.append(prof("Universität Gießen", "Fachbereich 07 Mathematik, Informatik, Physik, Geographie", name, topic, "Institut für Informatik", m.group(1)))
    return out


def koeln():
    """Abteilung für Informatik (MNF): /abteilung lists all Professor:innen (+ assoziierte Mitglieder, joint with Med. Fakultät); topic = Forschungsgruppe on /forschung/gruppen
    (that page only gives 'Prof: A. Surname', so groups are matched by surname). Dozent:innen, Vertretungsprofessuren and former members are skipped."""
    base = "https://cs.uni-koeln.de"
    page = need(base + "/abteilung")
    page = page[page.find("<main"):]
    groups = []
    for b in need(base + "/forschung/gruppen").split("<h2")[1:]:
        groups.append((re.sub(r"^class=\"\">\s*", "", plain(b.split("</h2>")[0])).strip(), plain(b.split("</h2>", 1)[1])))
    out = []
    sections = re.split(r"(?s)<h2[^>]*>", page)[1:]
    for sec in sections:
        title = plain(sec.split("</h2>")[0])
        if title.startswith("Professor:innen"):
            unit_note = "Abteilung für Informatik"
        elif title.startswith("Assoziierte"):
            unit_note = "Abteilung für Informatik (assoziiert)"
        else:
            continue
        for m in re.finditer(r"(?s)<h6>(?:<a [^>]*href=\"([^\"]+)\"[^>]*>)?(.*?)(?:</a>)?</h6>|<p>(.*?)</p>", sec):
            txt = plain(m.group(2) or m.group(3) or "")
            if not txt.startswith("Prof"):
                continue
            extra = re.search(r"\((.*)\)", txt)
            name = re.sub(r"\s*\(.*", "", txt)
            sur = name.split()[-1]
            topic = ""
            for g, body in groups:
                if re.search(r"Prof[.:]+.{0,60}?" + re.escape(sur), body):
                    topic = g
            if not topic:  # e.g. QIC: group text names the professor without the 'Prof:' marker
                topic = next((g for g, body in groups if sur in body), "")
            if not topic and extra:
                topic = extra.group(1).split(";")[0].replace("Global Faculty in KPA", "").strip(' "')
            url = up.urljoin(base, m.group(1)) if m.group(1) else base + "/abteilung"
            out.append(prof("Universität Köln", "Mathematisch-Naturwissenschaftliche Fakultät", name, topic, unit_note, url))
    return out


def bonn():
    """Institut für Informatik (MNF): the 8 Abteilung pages under /de/forschung/ each show the Arbeitsgruppenleiter*innen as cards 'Prof. Dr. Name Group Raum|Mail …'
    (there is no whole-institute staff list). Topic = research group on the card, unit = Abteilung."""
    base = "https://www.informatik.uni-bonn.de/de/forschung/"
    areas = [("algorithmen-und-komplexitaet", "Algorithmen und Komplexität"), ("computational-analytics", "Computational Analytics"),
             ("computational-life-health", "Computational Life & Health"), ("informationssysteme-und-kuenstliche-intelligenz", "Informationssysteme und KI"),
             ("intelligente-systeme-und-robotik", "Intelligente Systeme und Robotik"), ("language-technologies", "Language Technologies"),
             ("sicherheit-und-vernetzte-systeme", "Sicherheit und vernetzte Systeme"), ("visual-computing", "Visual Computing")]
    N = (r"((?:J?Prof(?:essorin|essor)?\.?|Juniorprofessor(?:in)?)\s+(?:Dr\.(?:-Ing\.)?\s+)*"
         r"(?:[A-ZÄÖÜ][\wäöüß]+|[A-Z]\.)(?:\s+(?:[A-Z]\.|von|van|de))*\s+[A-ZÄÖÜ][\wäöüß\-]+)\s+(.{0,90}?)\s+(?:Raum:|Telefon|Mail\b|Gruppe Mail|Profil)")
    out, seen = [], set()
    for slug, unit in areas:
        last = "informationssysteme-und-ki" if slug.startswith("informationssysteme") else slug
        url = base + slug + "/" + last
        p = plain(re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", need(url)))
        for m in re.finditer(N, p):
            n = prof("Universität Bonn", "Mathematisch-Naturwissenschaftliche Fakultät", m.group(1).replace("Juniorprofessorin", "Jun.-Prof.").replace("Juniorprofessor", "Jun.-Prof."), m.group(2), "Institut für Informatik, Abt. " + unit, url)
            if n["name"] not in seen:
                seen.add(n["name"])
                out.append(n)
    return out


def braunschweig():
    """Department Informatik (Carl-Friedrich-Gauss-Fakultaet) 'Uebersicht der Institute': one accordion per institute with 'Leiter:' and, where the
    institute has several Abteilungen, 'Abteilung X / Leiter: Prof. ...'. The faculty-wide list (/fk1/forschung/hochschullehrerinnen) mixes Math/WiWi/Sozialwiss.
    and has no unit, so it is not used. Hannover Abteilungen of the PLRI (MHH) are skipped. Covers institute/Abteilung heads only (not every professor)."""
    url = "https://www.tu-braunschweig.de/informatik/research/institutes"
    page = need(url)
    fak = "Carl-Friedrich-Gauß-Fakultät (Department Informatik)"
    out, seen = [], set()
    for chunk in page.split('class="accordion__header"')[1:]:
        head, body = chunk.split("</a>", 1)
        unit = plain(head.split(">", 1)[1])
        if unit.startswith("Bildnachweise"):
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", body))
        text = re.sub(r"(\|\s*)+", "|", text)
        link = re.findall(r'href="([^"#]+)"', body)
        iurl = up.urljoin(url, link[-1]) if link else url
        found = re.findall(r"(Abteilung [^|]+)\|Leiter(?:in)?: (Prof\.[^|]+)|(?<![\w ])Leiter(?:in)?:\|?\s*(Prof\.[^|]+)", text)
        for abt, n1, n2 in found:
            if "(Hannover)" in abt:
                continue
            name = n1 or n2
            topic = re.sub(r"^Abteilung (?:für )?", "", abt) if abt else unit
            if name not in seen:
                seen.add(name)
                out.append(prof("TU Braunschweig", fak, name, topic, unit, iurl))
    return out


def ilmenau():
    """Fakultaet Informatik und Automatisierung, page 'Institute und Fachgebiete': 5 institute columns, each Fachgebiet as '<a>Name</a><br>(Prof. ...)'.
    Includes the Automatisierungs-/Biomedizinische-Technik institutes of the same Fakultaet (unit tells them apart). N.N. chairs, Lehrgruppe leader (Dr.) and
    Honorar-/Zweitmitgliedschaften are excluded."""
    url = "https://www.tu-ilmenau.de/universitaet/fakultaeten/fakultaet-informatik-und-automatisierung/profil/institute-und-fachgebiete"
    page = need(url)
    page = page.split("Honorarprofessuren und Zweitmitgliedschaften", 1)[0]
    out = []
    for col in page.split('<h4')[1:]:
        unit = plain(col.split("</h4>", 1)[0].split(">", 1)[1])
        for seg in col.split("</p>"):
            m = re.search(r'(?s)<p>(.*?)\((Prof[^)]*)\)', seg)
            if not m:
                continue
            link = re.search(r'href="([^"]+)"', m.group(1))
            out.append(prof("TU Ilmenau", "Fakultät für Informatik und Automatisierung", m.group(2), plain(m.group(1)), unit,
                            up.urljoin(url, link.group(1)) if link else url))
    return out


TUHH = [  # (unit, team/people page, who to take)
    ("Institut für Softwaresysteme (E-16)", "https://www.tuhh.de/sts/institute/people"),
    ("Institut für Secure Cyber-Physical Systems (E-15)", "https://www.tuhh.de/scps/team"),
    ("Institut für Software Security (E-22)", "https://www.tuhh.de/softsec/homepage.html"),
    ("Institut für Eingebettete Systeme (E-13)", "https://www.tuhh.de/es/home/people"),
    ("Institut für Networked Cyber-Physical Systems (E-17)", "https://www.tuhh.de/ncps/team"),
    ("Institut für Autonomous Cyber-Physical Systems (E-24)", "https://www.tuhh.de/acps/team"),
    ("Institut für Data Science Foundations (E-21)", "https://www.tuhh.de/dsf/team"),
    ("Institut für Data Engineering (E-19)", "https://www.tuhh.de/ide/team"),
    ("Forschungsgruppe Human-Centric Machine Learning (E-EXK7)", "https://www.tuhh.de/human-ai/staff"),
    ("Forschungsgruppe Theoretische Informatik (E-EXK6)", "https://www.tuhh.de/tcs/staff"),
    ("Institut für Algorithmen und Komplexität (E-11)", "https://www.tuhh.de/algo/people"),
    ("Institut für Quantum Inspired and Quantum Optimization (E-25)", "https://www.tuhh.de/quantum/team"),
    ("Institut für Kommunikationsnetze (E-4)", "https://www.tuhh.de/et6/homepage.html"),
]


def tuhh():
    """No whole-unit professor list exists (Studiendekanat EIM page only lists institutes and a count of 34 Professor*innen, no names), so every CS institute's
    own team page is read: 'Prof. ...' tokens before the first 'Former/Ehemalige/Guests' heading ('Prof. (ret.)' skipped). Institutes whose head is N.N./acting
    (E-19 Data Engineering) give no row. Other EIM institutes (ET, Mathematik, Medizintechnik) are not included."""
    out = []
    for unit, url in TUHH:
        text = re.sub(r"<(script|style).*?</\1>", "", need(url), flags=re.S)
        toks = [re.sub(r"\s+", " ", html_t).strip() for html_t in re.sub(r"<[^>]+>", "|", text).split("|")]
        toks = [t for t in toks if t]
        first = next((i for i, t in enumerate(toks) if t.startswith("Prof.")), len(toks))
        end = next((i for i, t in enumerate(toks) if i > first and re.match(r"(?:Former|Ehemalige|Guests|Gäste|Alumni)", t)), len(toks))
        seen = set()
        head = ""  # heading of the person block before the name ('Assistant Professor' ...)
        for i, t in enumerate(toks[:end]):
            if re.fullmatch(r"(?:Full |Assistant |Associate |Junior )?Professors?|Juniorprofessor(?:in|en)?", t):
                head = t
            if i < first:
                continue
            m = re.fullmatch(r"(Prof\.(?: (?:Dr\.|Dr\.-Ing\.|rer\.|nat\.|pol\.|habil\.))*) ([A-ZÄÖÜ][\w\-.]+(?: [A-ZÄÖÜ][\w\-.]+){1,3})", t)
            if m and m.group(2) not in seen:
                seen.add(m.group(2))
                out.append(prof("TU Hamburg", "Studiendekanat Elektrotechnik, Informatik und Mathematik", t, "", unit, url, head))
    return out


def erlangen_ds():
    """Department Data Science (Naturwissenschaftliche Fakultät): collegial board page, tokens 'Prof. Dr.|First|Last|[(|Interim Professor|)|]chair|Professors'.
    Interim professors, Adjunct professors and non-professors (research associates) are skipped. The Department Informatik (Technische Fakultät) has no page with names (cs.fau.de lists chairs only; FAUdir is disallowed)."""
    url = "https://www.datascience.nat.fau.eu/start/collegial-board/"
    toks = [html.unescape(t).strip() for t in re.sub(r"<[^>]+>", "|", re.sub(r"(?s)<(script|style).*?</\1>", "", need(url))).split("|")]
    toks = [t for t in toks if t]
    out = []
    for i, t in enumerate(toks):
        if t.startswith("Prof. Dr."):
            j = i + 1
            first, last = toks[j], toks[j + 1]
            j += 2
            if toks[j] == "(":
                continue  # (Interim Professor)
            topic, cat = toks[j], toks[j + 1]
            if cat != "Professors":
                continue  # 'Adjunct professors'
            out.append(prof("Universität Erlangen-Nürnberg", "Naturwissenschaftliche Fakultät", f"{t} {first} {last}", "" if topic.startswith("Department of") else re.sub(r"^(?:Professorship|Chair) (?:for|of) ", "", topic), "Department Data Science", url))
    if not out:
        raise RuntimeError("no professors found (the site now serves an Anubis anti-bot challenge)")
    return out


def mainz():
    """Institut für Informatik (FB 08): the page /personenverzeichnis/ builds its list in the browser from the public JGU directory API
    (jgudir.webapi.jgu.net, organization 807 = Institut für Informatik, recursive; robots.txt of that host allows it). Professors = members with role 'Professor*' or a 'Prof.' title
    (Jun.-Prof. sit under the staff role). Only name, group and unit are kept (the API also carries phone/e-mail, which is not stored). This list is current;
    the /arbeitsgruppen/ prose still names people who have left (Erdweg, Brinkmann)."""
    import json
    page = "https://www.informatik.uni-mainz.de/personenverzeichnis/"
    root = json.loads(need("https://jgudir.webapi.jgu.net/v1/jgu-mz/organization/807/people/recursive"))
    out = {}

    def walk(node, parent, depth):
        org = node["organization"]["displayName"]
        for rm in node["roleMembers"]:
            for m in rm["members"]:
                n = m["displayName"]
                if (rm["role"]["displayName"].startswith("Professor") or re.search(r"Prof\.", n)) and not re.search(r"apl\.|Hon\.|Honorar|Emerit|i\. ?R\.", n):
                    row = prof("Universität Mainz", "Fachbereich 08 Physik, Mathematik und Informatik", n, org if depth else "", "Institut für Informatik" + (", " + parent if depth > 1 else ""), page, rm["role"]["displayName"])
                    if row["name"] not in out or (depth and not out[row["name"]]["topic"]):  # a member can also be listed at institute level: keep the entry with a group
                        out[row["name"]] = row
        for c in node["childOrganizationMembers"]:
            walk(c, org, depth + 1)

    walk(root, "", 0)
    return list(out.values())


SOURCES = [chemnitz, darmstadt, heidelberg_mathinf, frankfurt, bamberg, hannover, hamburg, ulm, greifswald, dresden, kit, tuebingen, saarland_cs, rwth, freiburg, tum_cit, tum, stuttgart, goettingen, tu_berlin, hpi_profs, dortmund, fu_berlin, osnabrueck, paderborn, kassel, wuerzburg, marburg, jena, magdeburg, mannheim, luebeck, augsburg, rptu, regensburg, passau, potsdam, hhu, rostock, bochum, cottbus, duisburg_essen, giessen, koeln, bonn, braunschweig, ilmenau, tuhh, erlangen_ds, mainz]

def merge(rows):
    """One row per (university, name), in order of first appearance. A person listed several times (e.g. under Informatik and under Electrical Engineering, or on the TUM chairs list
    and the CS page) keeps the first row, unless a later one is CS-related and the first is not: then the CS row wins."""
    out = {}
    for r in rows:
        k = (r["university"], r["name"])
        if k not in out or (cs_hit(r) and not cs_hit(out[k])):
            out[k] = r
    return list(out.values())


if __name__ == "__main__":
    # Swiss / Austrian universities, non-university institutes and more German universities live in their own modules (they import this one, hence the import here)
    from profs_scrape_ch1 import SOURCES_CH1
    from profs_scrape_ch2 import SOURCES_CH2
    from profs_scrape_ch3 import SOURCES_CH3
    from profs_scrape_at import SOURCES_AT
    from profs_scrape_inst import SOURCES_INST
    from profs_scrape_de2 import SOURCES_DE2
    SOURCES = SOURCES + SOURCES_DE2 + SOURCES_CH1 + SOURCES_CH2 + SOURCES_CH3 + SOURCES_AT + SOURCES_INST
    profs, status = [], {}
    for src, res, err in run_sources(SOURCES):  # parallel across hosts, merged in SOURCES order
        if err:
            status[src.__name__] = f"FAILED: {err}"
            continue
        rows = merge(r for r in res if not re.fullmatch(r"N\. ?N\.?", r["name"]) and "†" not in r["name"] and r["name"])  # N. N. = vacant chair; † = deceased
        profs = merge(profs + rows)  # first source wins (e.g. TUM chairs list before the CS page), except that a CS row beats a non-CS one
        status[src.__name__] = f"{len(rows)} professors"
    # Institute people: 'Faculty' / 'Group leader' by the page's section; a more precise position that a university lists for the same name (Director, Associate ...) wins
    INSTITUTES = {"CISPA", "MPI-SWS", "MPI-SP"}
    uni_role = {}
    for p in profs:
        if p["university"] not in INSTITUTES and p["role"] not in ("", "Group leader"):
            uni_role.setdefault(p["name"], p["role"])
    for p in profs:
        if p["university"] in INSTITUTES and p["role"] and p["name"] in uni_role and not (p["role"] == "Faculty" and uni_role[p["name"]] == "Professor"):
            p["role"] = uni_role[p["name"]]  # the position at a real university is preferred (Faculty stays when the university only says Professor)
    for k, v in status.items():
        print(f"{k:12} {v}")
    json.dump(dict(scraped=datetime.date.today().isoformat(), status=status, professors=profs), open("professors.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(profs), "professors written to professors.json;", f"requests: {STATS['web']} web, {STATS['cached']} from cache")
