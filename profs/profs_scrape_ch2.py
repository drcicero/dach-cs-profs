import os, re, sys, urllib.parse as up
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain   # prof(uni, faculty, name, topic="", unit="", url="") ; need(url) = cached, polite, robots-checked fetch


def basel():
    """Departement Mathematik und Informatik people page: the personlist plugin embeds all persons as JSON (data-data attribute, no extra request).
    Kept: persons with title Prof., an OU under 'Fachbereich Informatik' and a professorship / head-of-department / dean function. Skipped: emeriti, lecturers, mathematics, staff, students."""
    import html, json
    url = "https://dmi.unibas.ch/en/department/people/"
    m = re.search(r'data-data="([^"]*MX_LASTNAME[^"]*)"', need(url))
    out, seen = [], set()
    for p in json.loads(html.unescape(m.group(1)))["data"]["items"]:
        if not (p.get("titelPrefix") or p.get("MX_TITLE") or "").startswith("Prof") or "em." in p.get("MX_TITLE", ""):
            continue
        for b in p["DISPLAYBLOCKS"]:
            path = b.get("OU", {}).get("VISIBLE_DISPLAYNAME_PATH", [])
            fn = b.get("FUNKTION", {}).get("plural_neutral_en", "")
            if "Fachbereich Informatik" in path and fn in ("Professorships", "Heads of the department", "Deans") and p["_id"] not in seen:
                seen.add(p["_id"])
                group = re.sub(r"^FG\s+", "", path[-1]) if path[-1].startswith("FG ") else ""
                out.append(prof("Universität Basel", "Department Mathematik und Informatik", f'{p["MX_TITLE"]} {p["MX_FIRSTNAME"]} {p["MX_LASTNAME"]}',
                                f"Forschungsgruppe {group}" if group else "", "Fachbereich Informatik", up.urljoin(url, p["link"])))
    return out


def bern():
    """Institut für Informatik team page (ZMS article.team-box cards): kept = name starting 'Prof.' (research group leaders); topic = research group taken from the profile URL.
    Skipped: 'Prof. em.', PD, lecturers, secretaries, admins, doctoral staff."""
    url = "https://www.inf.unibe.ch/ueber_uns/team/index_ger.html"
    out = []
    for a in re.findall(r'(?s)<article class="team-box".*?</article>', need(url)):
        m = re.search(r'<dd>\s*<a href="([^"]*)">(.*?)</a>', a)
        if not m or not plain(m.group(2)).startswith("Prof.") or "em." in plain(m.group(2)).split()[:2]:
            continue
        g = re.search(r"/forschungsgruppen/([^/]+)/", m.group(1))
        topic = re.sub(r"_[a-z]{2,5}$", "", g.group(1)).replace("_", " ").title() if g else ""
        out.append(prof("Universität Bern", "Institut für Informatik", plain(m.group(2)), topic, "", m.group(1)))
    return out


def usi():
    """USI search.usi.ch faculty people page (sections by rank): kept = Dean, Full / Associate / Assistant Professor ('Last, First' rows).
    Skipped: Adjunct Professor, Professor emeritus, lecturers, researchers, PhD students, staff. No topic available."""
    url = "https://search.usi.ch/en/faculties/3/faculty-of-informatics/people"
    out, seen = [], set()
    for rank, body in re.findall(r"(?s)<h3>([^<]*)</h3>(.*?)(?=<h3>|$)", need(url)):
        if rank not in ("Dean", "Full Professor", "Associate Professor", "Assistant Professor"):
            continue
        for href, name in re.findall(r'<li>\s*<a href="(https://search\.usi\.ch/en/people/[^"]*)">([^<]*)</a>', body):
            if href not in seen:
                seen.add(href)
                out.append(prof("Università della Svizzera italiana (Lugano)", "Faculty of Informatics", plain(name), "", "", href))
    return out


def fribourg():
    """Department of Informatics 'Professors' page (people cards <h5>name</h5><p>role</p>): all listed professors; topic = role is not a topic, so left empty.
    Skipped: emeriti, teaching staff, assistants (separate pages)."""
    url = "https://www.unifr.ch/inf/en/prof.html"
    out = []
    for art in re.findall(r"(?s)<article.*?</article>", need(url)):
        m = re.search(r'(?s)<a href="([^"]*)" class="box--link".*?<h5>(.*?)</h5>\s*<p>(.*?)</p>', art)
        if m and "Professor" in m.group(3) and "emerit" not in m.group(3).lower():
            out.append(prof("Universität Freiburg (Fribourg)", "Department of Informatics", plain(m.group(2)), "", "", m.group(1)))
    return out


SOURCES_CH2 = [basel, bern, usi, fribourg]
