"""Current professors of Austrian computer-science units (TU Wien, TU Graz, JKU, Uni Wien, Innsbruck, ISTA, Salzburg, Klagenfurt).
Same conventions as profs_scrape.py (need() = cached, polite, robots-checked fetch; prof() rows; no contact data stored).
Usage: from profs_scrape_at import SOURCES_AT"""
import html
import os
import re
import sys
import urllib.parse as up

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain

# words that make up Austrian academic titles; a token is dropped if all its '.'/'-'-separated parts are in this set
_TITLE_WORDS = set("""univ uni prof ao a o assoz assoc assist ass priv doz dr dipl ing mag mmag di ddipl dott ssa techn rer nat phil habil inform math phys
volksw msc bsc ma ba mba bakk phd ph d med meng msci bed med ll m in fh hon h c mult oec soc iur jur mas sc""".split())


def at_name(s):
    """'Univ.-Prof.in Dr.in Martina Seidl, MSc' / 'Prof.Dipl.-Ing. Mag. Dr. Markus Zanker' / 'Assoz. Prof. Priv.-Doz. Dr. Stefan Resmerita' -> name without Austrian titles."""
    s = re.sub(r"\(.*?\)", " ", html.unescape(re.sub(r"\s+", " ", s)))
    keep = []
    for tok in re.split(r"[\s,]+", s):
        parts = [p for p in re.split(r"[.\-]", tok) if p]
        if tok and parts and all(p.lower() in _TITLE_WORDS for p in parts):
            continue
        keep.append(tok)
    return " ".join(keep).strip(" ,.-")


def _last_first(s):
    """'Böhme Rainer' (Innsbruck: surname first) -> 'Böhme, Rainer' so that clean_name puts the first name first."""
    w = s.split()
    return f"{' '.join(w[:-1])}, {w[-1]}" if len(w) > 1 else s


def tuwien():
    """Faculty of Informatics: /people/professors (cards: name in the first <span>, topic = 'card-subtitle' text, role in its 'text-muted' span; the section
    'Emeriti and Retired' at the end is skipped, as are Honorary/Visiting roles). Unit = institute, read from the 24 research-unit pages (nav links /orgs/eNNN-NN):
    their 'Professors' section lists the slugs, 'A research unit of the Institute of X' names the institute. Raises when no card matches (layout change)."""
    base = "https://informatics.tuwien.ac.at"
    page = need(base + "/people/professors")
    units = {}
    for href, label in dict.fromkeys(re.findall(r'(?s)href="(?:https://informatics\.tuwien\.ac\.at)?(/orgs/e\d+-\d+)/?"[^>]*>\s*(.*?)\s*</a>', page)):
        t = need(base + href)
        m = re.search(r'research unit of the (Institute of [^"<]*)', t)
        unit = plain(m.group(1)) if m else re.sub(r"\s*\(Research Unit\)", "", plain(label))
        sec = re.search(r"(?s)<h1[^>]*>\s*Professors\s*</h1>(.*?)<h1[^>]*>", t)
        for slug in re.findall(r'/people/([^"/]+)/?"', sec.group(1) if sec else ""):
            units.setdefault(slug, unit)
    cut = [m.start() for m in re.finditer(r"<h1[^>]*>\s*Emeriti and Retired\s*</h1>", page)]
    body = page[:cut[-1]] if cut else page
    out = []
    for href, name, rest in re.findall(r'(?s)class="stretched-link" href="(?:https://informatics\.tuwien\.ac\.at)?(/people/[^"]*)">\s*<span[^>]*>(.*?)</span>.*?card-subtitle[^>]*>(.*?)</p>', body):
        topic, _, role = rest.partition('<span class="text-muted">')
        if re.search(r"Retired|Emerit|Honorary|Visiting", plain(role)):
            continue
        out.append(prof("TU Wien", "Fakultät für Informatik", plain(name), plain(topic), units.get(href.strip("/").rsplit("/", 1)[-1], ""), base + href, plain(role)))
    if not out:
        raise RuntimeError("layout changed")
    return out


# TU Graz: institute from the host/path of the personal web page; None = biomedical / non-CS (skipped). Unlisted people: unit "" and kept.
_TUG_UNIT = [("isec", "Institute of Information Security"), ("ivc", "Institute of Visual Computing"), ("icg", "Institute of Visual Computing"),
             ("iml", "Institute of Machine Learning and Neural Computation"), ("sai", "Institute of Software Engineering and Artificial Intelligence"),
             ("ist.tugraz", "Institute of Algorithms and Theory"), ("alexander-lex", "Institute of Visual Computing"), ("isds", "Institute of Human-Centred Computing"), ("hcc", "Institute of Human-Centred Computing"),
             ("atcs", "Institute of Algorithms and Theory")]
_TUG_SKIP = ("biomech", "hce", "ibi", "ine", "bioinfo", "sts", "bci.tugraz")
_TUG_NAME = {"Denis Kalkofen": "Institute of Visual Computing", "Alexander Lex": "Institute of Visual Computing", "Elisabeth Lex": "Institute of Human-Centred Computing",
             "Denis Helic": "Institute of Human-Centred Computing", "Johanna Pirker": "Institute of Human-Centred Computing", "Fariba Karimi": "Institute of Human-Centred Computing",
             "Roman Kern": "Institute of Machine Learning and Neural Computation", "Alexander Plopski": "Institute of Human-Centred Computing", "Christian Gütl": "Institute of Human-Centred Computing",
             "Wolfgang Slany": "Institute of Software Engineering and Artificial Intelligence", "Daniel Gruß": "Institute of Information Security", "Daniel Gruss": "Institute of Information Security",
             "Viktoria Pammer-Schindler": "Institute of Human-Centred Computing", "Dieter Schmalstieg": "Institute of Visual Computing", "Yannic Maus": "Institute of Algorithms and Theory",
             "Oswin Aichholzer": "Institute of Algorithms and Theory", "Birgit Vogtenhuber": "Institute of Algorithms and Theory", "Markus Steinberger": "Institute of Visual Computing"}
_TUG_NOT_CS = {"Lenk", "Watzenig", "Müller-Putz", "Wriessnegger", "Rienmüller", "Wächter", "Wieser", "Scharfetter", "Uecker", "Sommer", "Holzapfel", "Baumgartner", "Schröttner"}


def tugraz():
    """CSBME faculty team page (/faculty/team/faculty, one div.person per member: first/last name, title, role_* classes, personal web page).
    Kept: role UP/AP/UA/UD/VP (full/associate/assistant/ao. professors). Skipped: Priv.-Doz., staff without professor role, and members of the biomedical-engineering institutes
    (decided by the host of their web page or a small name list, because the page itself names no institute); the unit is inferred the same way (blank if unknown)."""
    url = "https://www.tugraz.at/fakultaeten/faculty-of-computer-science-and-biomedical-engineering/faculty/team/faculty"
    out = []
    for blk in re.split(r'(?=<div class="person listEntry)', need(url))[1:]:
        roles = re.search(r'class="person listEntry([^"]*)"', blk).group(1)
        n = re.search(r'firstName">(.*?)</span>\s*<span class="lastName">(.*?)</span>.*?class="title">(.*?)</span>', blk, re.S)
        if not n or not re.search(r"Prof", n.group(3)) or re.search(r"Priv|\bem\.|i\.\s?R\.", n.group(3)):
            continue
        first, last = plain(n.group(1)), plain(n.group(2))
        if last in _TUG_NOT_CS:
            continue
        w = re.search(r'website"><a[^>]*href="([^"]*)"', blk)
        web = w.group(1) if w else ""
        host = re.sub(r"^https?://(?:www\.)?", "", web).lower()
        if any(re.match(rf"{k}\.|tugraz\.at/(?:institute|arbeitsgruppen)/{k}/", host) or f"/{k}/" in host for k in _TUG_SKIP):
            continue
        unit = _TUG_NAME.get(f"{first} {last}") or next((u for k, u in _TUG_UNIT if re.search(rf"(?:^|\.|/){re.escape(k)}(?:\.|/)", host)), "")
        out.append(prof("TU Graz", "Fakultät für Informatik und Biomedizinische Technik", f"{first} {last}", "", unit, web or url, plain(n.group(3))))
    return out


def jku():
    """informatik.jku.at/research/faculty.phtml (Fachbereich Informatik, name + position + link to the personal/institute page). Kept: positions containing 'Professor'
    (skipped: Senior Lecturer/Scientist) and non-CS institutes (Integriert Studieren, School of Education, Robopsychology Lab, Signal Processing, Integrated Circuits). Unit = institute guessed from the link (blank if the
    link is a private homepage). The page is hand-maintained and can lag behind (e.g. still lists people who moved)."""
    url = "https://informatik.jku.at/research/faculty.phtml"
    hosts = {"ics.jku": "Institut für Complex Systems", "cis.jku": "Abteilung für Kooperative Informationssysteme", "cp.jku": "Institut für Computational Perception",
             "ssw.": "Institut für Systemsoftware", "fmv.jku": "Institut für Formale Modelle und Verifikation", "iic.jku": "Institut für Integrierte Schaltungen und Quantum Computing",
             "ins.jku": "Institut für Netzwerke und Sicherheit"}
    out = []
    for href, name, role in re.findall(r'(?s)<a href="([^"]*)"[^>]*>\s*<em>(.*?)</em><br />\s*</a>\s*(.*?)<br', need(url)):
        if "Professor" not in role or re.search(r"integriert-studieren|school-of-education|linz-school|robopsychology|didaktik|integrated-circuits|iic\.jku|signal-processing", href):
            continue
        unit = next((v for k, v in hosts.items() if k in href), "")
        m = re.search(r"jku\.at/(?:en/)?((?:institut|institute|abteilung)[^/]*)/", href)
        if not unit and m:
            unit = re.sub(r"^institut-fuer-", "institut für ", m.group(1)).replace("-", " ")
            unit = re.sub(r"^(institute) (of|for) ", lambda x: f"Institute {x.group(2)} ", unit).title().replace(" Fuer ", " für ").replace(" Of ", " of ").replace(" For ", " for ").replace(" Und ", " und ").replace(" Für ", " für ")
        out.append(prof("JKU Linz", "Technisch-Naturwissenschaftliche Fakultät", at_name(plain(name)), "", unit, href, plain(role)))
    return out


def univie():
    """Fakultät für Informatik: /ueber-uns/professuren (table: Person, Titel, ...; e-mail/room columns ignored). Titles already separate; no unit given on that page.
    Skipped: nobody (the list contains only professors; ao. Univ.-Prof. are kept since the page does not mark retirement)."""
    base = "https://informatik.univie.ac.at"
    out = []
    for tr in re.findall(r'(?s)<tr class="univiepersonal-entry-table">(.*?)</tr>', need(base + "/ueber-uns/professuren")):
        a = re.search(r'<a href="([^"]*)"><span class="pers-search">(.*?)</span>', tr)
        if a:
            out.append(prof("Universität Wien", "Fakultät für Informatik", plain(a.group(2)), "", "", up.urljoin(base, html.unescape(a.group(1)).split("?")[0]), plain(tr)[:150]))
    return out


def innsbruck():
    """Institut für Informatik: tab 'Professors' on /en/informatik/research/ ('Title Lastname Firstname (research group) Research areas: ...'). Name order is surname first.
    Skipped: nothing (tab lists current professors only). Unit = research group, topic = research areas."""
    url = "https://www.uibk.ac.at/en/informatik/research/"
    page = need(url)
    sec = page.split('id="prof"', 1)[1].split("cmsplugin_", 1)[0]
    out = []
    for card in sec.split('<div class="col-12 col-md-6 col-lg-6">')[1:]:
        n = re.search(r'<a href="[^"]*people\.vcard[^"]*">(.*?)</a>', card)
        if not n or re.search(r"Emerit|i\.\s?R\.|Hon\.", plain(card)):
            continue
        group = re.search(r"\(\s*(?:</strong>)?\s*(?:<a[^>]*>)?([^<)]*?)(?:</a>)?\s*\)", card)
        topic = re.search(r"Research areas:</strong>\s*(.*?)</span>", card, re.S)
        out.append(prof("Universität Innsbruck", "Institut für Informatik", _last_first(plain(n.group(1))), plain(topic.group(1)) if topic else "", plain(group.group(1)) if group else "", url, plain(card)[:80]))
    return out


def ista():
    """Research overview /en/research/ (all ISTA faculty as person boxes with group name and field tags). Kept: tag 'Computer Science' (Henzinger, Kolmogorov, Lampert, Locatello ...);
    skipped: biology, physics, neuroscience, earth science, pure-mathematics and data-science-only groups (e.g. Vogels, Tkacik, Barton)."""
    url = "https://ista.ac.at/en/research/"
    out = []
    for b in need(url).split("person-box")[1:]:
        n = re.search(r'class="pname">(.*?)<', b)
        tags = re.findall(r'<span class="field_designator">(.*?)</span>', b)
        if n and "Computer Science" in tags:
            g = re.search(r'pspecialization">(.*?)<', b)
            link = re.search(r'<a href="([^"]*)"', b)
            out.append(prof("ISTA", "Computer Science and Mathematics", plain(n.group(1)), (g.group(1).capitalize() if g else ""), "", link.group(1) if link else url))
    return out


def salzburg():
    """Fachbereich Informatik: /fachbereich-informatik/mitarbeiter/ (headed lists; Fachbereichsleitung + Universitäts-Professor*innen, Assoziierte & Außerordentliche, Assistenzprofessor*innen).
    Skipped: Postdocs, doctoral staff, administration, Professoren im Ruhestand (own page, not read). Duplicates across lists are merged. No unit (department names are on /abteilungen/)."""
    base = "https://www.plus.ac.at/fachbereich-informatik/mitarbeiter/"
    seen, out = set(), []
    for head, body in re.findall(r'(?s)<h2 class="columns small-12">(.*?)</h2>\s*</div>\s*(<ul>.*?</ul>)', need(base)):
        h = plain(head)
        if not re.match(r"Universit|Assoziierte|Assistenzprofessor", h):
            continue
        for href, txt in re.findall(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', body):
            name = at_name(plain(txt))
            if name and name not in seen:
                seen.add(name)
                out.append(prof("Universität Salzburg", "Fachbereich Informatik", name, "", "", html.unescape(href), h))
    return out


def klagenfurt():
    """Computer-science institutes of the Fakultät für Technische Wissenschaften: Informatik-Systeme (/isys/team/, table sections Universitäts- / Assoziierte Professoren; rows marked 'i.R.' skipped),
    Information Technology (itec.aau.at/team/, person cards with position), Artificial Intelligence and Cybersecurity (/en/aics/team/, text list by research group). Kept: names with a
    Prof. title or professor position; skipped: Priv.-Doz., assistants, postdocs, administration. Informatikdidaktik / Smart Systems / Networked Embedded Systems are not covered."""
    out = []
    t = need("https://www.aau.at/isys/team/")
    sec = None
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", t):
        h = re.search(r"<strong>(.*?)</strong></td>", tr)
        if h:
            sec = plain(h.group(1))
            continue
        a = re.search(r'<td width="125"><a href="([^"]*)"[^>]*>(.*?)</a>(.*?)</td>', tr)
        if a and sec and re.match(r"Universitätsprof|Assoziierte Prof", sec) and "i.R." not in a.group(3):
            out.append(prof("Universität Klagenfurt", "Institut für Informatik", plain(a.group(2)), "", "Institut für Informatik-Systeme", html.unescape(a.group(1)), sec))
    url = "https://itec.aau.at/team/"
    for name, pos in re.findall(r'(?s)lhea-member-name">(.*?)</h2>\s*(?:<!--.*?-->\s*)?<h4 class="lhea-member-position">(.*?)</h4>', need(url)):
        if re.search(r"(?:Full|Associate|Assistant) Professor", pos) and "Priv" not in name:
            out.append(prof("Universität Klagenfurt", "Institut für Informatik", at_name(plain(name)), "", "Institut für Informationstechnologie (ITEC)", url, pos))
    url = "https://www.aau.at/en/aics/team/"
    t = need(url).split("Research Groups", 1)[-1]
    group = ""
    for tok in re.split(r"<[^>]+>", t):
        tok = html.unescape(tok).strip()
        g = re.match(r"Research Group:\s*(.*)", tok)
        if g:
            group = g.group(1)
        elif re.match(r"(?:O\.|Ao\.)?(?:Univ\.-|Assoc\.|Ass\.-)?\s?Prof\.", tok) and "Priv" not in tok and "Head of" not in tok and "[at]" not in tok:
            out.append(prof("Universität Klagenfurt", "Institut für Informatik", at_name(tok), "", "Institut für Artificial Intelligence und Cybersecurity" + (f" ({group})" if group else ""), url, tok))
    return out


SOURCES_AT = [tuwien, tugraz, jku, univie, innsbruck, ista, salzburg, klagenfurt]
