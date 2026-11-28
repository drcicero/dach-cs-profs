"""Scientific leaders of non-university research institutes (MPI-SWS, MPI-SP, MPI-INF, CISPA) -> same rows as profs_scrape.py (field 'university' = institute).
Public staff pages only, no contact data; every request goes through need() (cache, delay, robots.txt)."""
import os, re, sys, urllib.parse as up
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain   # prof(uni, faculty, name, topic="", unit="", url="") ; need(url) = cached, polite, robots-checked fetch

SWS = "Max Planck Institute for Software Systems"
SP = "Max Planck Institute for Security and Privacy"
INF = "Max Planck Institute for Informatics"
CISPA = "CISPA Helmholtz Center for Information Security"


def mpi_sws():
    """mpi-sws.org/people: sections 'Faculty' (directors + tenure-track faculty) and 'Research Group Leaders' (h3 headings), person cards h4.person__name; later sections (affiliated, postdocs, ...) skipped."""
    url = "https://www.mpi-sws.org/people/"
    out, unit = [], ""
    for part in re.split(r'(?=<h[23] class="page__section-ttl"|<h2 class="page__section-ttl")|(?=<h[23] class="section__ttl")', need(url)):
        m = re.match(r'<h[23] class="(?:page__section-ttl|section__ttl)">(.*?)</h', part, re.S)
        if m and plain(m.group(1)):
            unit = plain(m.group(1))
        if unit not in ("Faculty", "Research Group Leaders"):
            continue
        for a in re.finditer(r'(?s)<a href="([^"]+)" class="people__ct people__lnk">.*?<h4 class="person__name">(.*?)</h4>', part):
            out.append(prof("MPI-SWS", SWS, plain(a.group(2)), "", unit, up.urljoin(url, a.group(1)), "Faculty" if unit == "Faculty" else "Group leader"))
    return out


def mpi_sp():
    """mpi-sp.org/4245/faculty: one h2 per person under 'Faculty' (directors, tenure-track) and 'Research Group Leaders'; Max Planck Fellows, visiting research group leaders and adjunct faculty are read as 'Honorary / visiting / secondary' (a university's position for the same name wins).
    Page text is a free-form bio, so no topic."""
    url = "https://www.mpi-sp.org/4245/faculty"
    t = re.sub(r"data-picture='[^']*'", "", need(url))
    out, unit = [], "Faculty"
    for part in re.split(r"(?=<h2[ >])", t):
        h = re.match(r"<h2[^>]*>(.*?)</h2>", part, re.S)
        if not h:
            continue
        name = plain(h.group(1)).replace("\xa0", " ")
        if name in ("Faculty", "Research Group Leaders"):
            unit = name
            continue
        if name in ("Max Planck Fellows", "Visiting Research Group Leaders", "Adjunct Faculty Members"):
            unit = name  # external members: position 'Honorary / visiting / secondary' unless a university lists them with a position
            continue
        if name == "Former Faculty":
            unit = ""
        if unit and "<h2" not in part[4:]:
            link = re.search(r'<strong><a [^>]*href="([^"]+)"', part)
            out.append(prof("MPI-SP", SP, name, "", unit, link.group(1) if link else url, {"Faculty": "Faculty", "Research Group Leaders": "Group leader"}.get(unit, "Honorary / visiting / secondary")))
    return out


def mpi_inf():
    """mpi-inf.mpg.de/departments: header blocks 'D1..D6' (department directors) and 'RG1..RG3' (research group leaders); topic = department / group title.
    Historic entries (AG2, BIO: emeriti) have a linked number and are skipped. Every department section also has a table 'research group | leader' (senior researchers with a Prof. title,
    others with Dr./PhD): all those leaders are read too (role Professor when the title says Prof., else Group leader)."""
    url = "https://www.mpi-inf.mpg.de/departments/"
    t = need(url)
    out = []
    for m in re.finditer(r'(?s)department-header__number">\s*(D\d|RG\d)\s*</div><h2 class="department-header__title">\s*(.*?)\s*</h2><div class="department-header__director">\s*(.*?)\s*</div>', t):
        code, title, name = m.group(1), plain(m.group(2)), plain(m.group(3))
        href = re.search(r'href="(/departments/[^"]+)"[^>]*>\s*Go to %s\b' % code, t)
        out.append(prof("MPI-INF", INF, name, title, f"{'Department' if code[0] == 'D' else 'Research Group'} {code}", up.urljoin(url, href.group(1)) if href else url, "Director"))
    for row in re.findall(r"(?s)<tr>(.*?)</tr>", t):  # research group | leader
        cells = re.findall(r"(?s)<td[^>]*>(.*?)</td>", row)
        link = re.search(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', cells[1]) if len(cells) == 2 else None
        if link:
            name = plain(link.group(2)).replace("\xa0", " ")
            out.append(prof("MPI-INF", INF, name, plain(cells[0]).rstrip(","), "Research group", up.urljoin(url, link.group(1)), "" if name.startswith("Prof") else "Group leader"))
    return out


def cispa():
    """cispa.de/en/people: one page, contact cards grouped by headline; the 'Faculty' block (tenured / tenure-track faculty) and the
    'Senior Researcher & Research Group Leader' block (role Group leader); research areas are empty on the list page, so no topic."""
    url = "https://cispa.de/en/people"
    t = need(url)
    blk = re.split(r'id="faculty">Faculty</h3>', t, maxsplit=1)[-1]
    blk = re.split(r'<div class="people-headline"', blk, 1)[0]
    out = []
    for m in re.finditer(r'(?s)<a class="contact-contact" href="([^"]+)"\s+title="([^"]+)"', blk):
        out.append(prof("CISPA", CISPA, plain(m.group(2)), "", "Faculty", up.urljoin(url, m.group(1)), "Faculty"))
    blk = re.split(r'id="seniorResearcher_researchGroupLeader"', t, maxsplit=1)[-1]
    blk = re.split(r'<div class="people-headline"', blk, 1)[0]
    for m in re.finditer(r'(?s)<a class="contact-contact" href="([^"]+)"\s+title="([^"]+)"', blk):
        out.append(prof("CISPA", CISPA, plain(m.group(2)), "", "Senior Researcher & Research Group Leader", up.urljoin(url, m.group(1)), "Group leader"))
    return out


SOURCES_INST = [mpi_sws, mpi_sp, mpi_inf, cispa]
