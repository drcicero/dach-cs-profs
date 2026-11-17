"""Swiss CS departments, part 1: ETH Zürich D-INFK, EPFL IC, Universität Zürich IfI. Same row format and fetching as profs_scrape.py."""
import json
import os
import re
import sys
import urllib.parse as up

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain

ETH_AREAS = ["computer-systems", "data-management-machine-learning", "information-system-security",
             "intelligent-interactive-systems-and-physical-computing", "programming-languages-software-engineering",
             "theory-algorithms", "visual-computing"]


def _eth_cards(url):
    """Yield (name, role, link, areas text) for each professor card (<p><b>Name</b>Role</p> + 'More details' link + keywords) of an ETH D-INFK page."""
    for chunk in need(url).split("<p><b>")[1:]:
        name, rest = chunk.split("</b>", 1)
        role = plain(rest.split("</p>", 1)[0])
        if not re.search(r"Professor", role):
            continue
        link = re.search(r'href="([^"]*)"[^>]*>(?:\s*<[^>]+>)*\s*(?:external page\s*)?(?:More details|Website)', chunk)
        topic = plain(re.split(r"(?:More details|Website)</a>", chunk, 1)[-1].split("</p>", 1)[0]) if link else ""
        yield plain(name).replace("\u200b", ""), role, (up.urljoin(url, link.group(1)) if link else url), topic


def eth():
    """D-INFK faculty page (inf.ethz.ch/people/faculty/faculty.html): one card per professor with title and research keywords; Adjunct professors skipped.
    The unit is the research area (Computer Systems, Visual Computing, ...) taken from the seven research-area pages (the first area a professor appears on); the institutes are not listed on any public list page."""
    base = "https://inf.ethz.ch/people/faculty/faculty.html"
    area = {}
    for a in ETH_AREAS:
        url = f"https://inf.ethz.ch/research/{a}.html"
        title = plain(re.search(r"(?s)<h1[^>]*>(.*?)</h1>", need(url)).group(1))
        for name, role, link, topic in _eth_cards(url):
            area.setdefault(name, title)
    out = []
    for name, role, link, topic in _eth_cards(base):
        if "Adjunct" in role:
            continue
        out.append(prof("ETH Zürich", "Department of Computer Science", name, topic, area.get(name, ""), link))
    return out


def epfl():
    """IC 'Professors' page (epfl.ch/schools/ic/about/faculty-members/): list rows with name, job title and people.epfl.ch link. Only the first block is read (stops before External faculty / Courtesy / Emeriti / visiting) and only Full / Associate / (Tenure Track) Assistant Professors are kept; the e-mail and office entries of the page are ignored. No lab or topic is listed there."""
    url = "https://www.epfl.ch/schools/ic/about/faculty-members/"
    page = need(url).split(">External faculty members<", 1)[0]
    out = []
    for link, name, title in re.findall(r'(?s)href="(https://people\.epfl\.ch/[^"]*)"\s+itemprop="name"\s*>(.*?)</a\s*>.*?itemprop="jobTitle">\s*(.*?)\s*</p>', page):
        if re.fullmatch(r"(?:Full|Associate|Assistant|Tenure Track Assistant) Professor", plain(title)):
            out.append(prof("EPFL Lausanne", "School of Computer and Communication Sciences", plain(name), "", "", link))
    return out


def uzh():
    """IfI people page loads capuana.ifi.uzh.ch/people/persons.json (the JSON behind the page); only the category 'Professors' is used (no affiliated/adjunct/guest professors, instructors or former faculty). Topic is the research group's full name."""
    data = json.loads(need("https://capuana.ifi.uzh.ch/people/persons.json"))
    key = next(k for k in data if k.startswith("Professors"))
    out = []
    for p in data[key]:
        group = (p.get("Group_Full") or p.get("Group") or "").split(" / ")[0]
        out.append(prof("Universität Zürich", "Department of Informatics", f"{p['Firstname']} {p['Lastname']}", group, "", p.get("Personalpage") or p.get("Group_URL") or ""))
    return out


SOURCES_CH1 = [eth, epfl, uzh]
