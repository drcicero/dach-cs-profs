import os, re, sys, urllib.parse as up
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profs_scrape import prof, need, plain   # prof(uni, faculty, name, topic="", unit="", url="") ; need(url) = cached, polite, robots-checked fetch


def stgallen():
    """School of Computer Science 'lecturers' page: one schema.org JSON-LD ItemList of Person entries (email/phone in it are ignored).
    Kept: honorificPrefix starting 'Prof' (Dr.-only persons = lecturers/PD skipped). Topic not available; url = public HSG person page."""
    import json
    url = "https://www.unisg.ch/en/university/schools/school-of-computer-science/lecturers/"
    out = []
    page = need(url)
    pos = {plain(n): plain(r) for n, r in re.findall(r'(?s)<h4[^>]*>([^<]*)</h4><div class="headings-regular[^>]*>[^<]*</div><div class="headings-small[^>]*>(.*?)</div>', page)}  # position text under each name
    for s in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', page):
        if '"Person"' not in s:
            continue
        for p in json.loads(s).get("itemListElement", []):
            p = p.get("item", p)
            if p.get("@type") == "Person" and (p.get("honorificPrefix") or "").startswith("Prof"):
                out.append(prof("Universität St. Gallen", "School of Computer Science", p["name"], "", "", p.get("url", url), pos.get(p["name"], "")))
    return out


def geneva():
    """Genève blocks www.unige.ch/informatique with a bot challenge (F5 TSPD, not bypassed). The CUI professors list (cui.unige.ch, allowed) is an
    iframe page listing all professors/MER of Faculté des sciences; kept = 'Prof.' with role Professeur(e) and unit 'Département d'informatique'.
    Skipped: honoraire/émérite/titulaire/invité, MER (Dr.), other departments (e.g. GSI-only). Topic = research group name; email/phone ignored."""
    url = "https://cui.unige.ch/static/listeProfs.php?ordre=nom"
    out = []
    for row in re.findall(r"(?s)<tr class=\"(?:pair|impair)\">(.*?)</tr>", need(url)):
        m = re.search(r'(?s)<td valign="top">(Prof\.)\s*<a [^>]*><strong>(.*?)</strong>\s*(.*?)</a><br/>(.*?)<br/>(.*?)<br>(.*?)(?:<br/>Bâtiment|<br/>Tél|</td>)', row)
        if not m:
            continue
        role, dept = plain(m.group(4)), plain(m.group(5)) + " " + plain(m.group(6))
        if not re.match(r"Professeure?( ordinaire| associé| assistant)?e?$", role, re.I) or "Département d'informatique" not in dept.replace("\xa0", " "):
            continue
        g = re.search(r'(?s)<a href="([^"]*)" target="_blank"[^>]*>(.*?)</a>', row)
        out.append(prof("Université de Genève", "Département d'informatique", f"{plain(m.group(3))} {plain(m.group(2)).title()}",
                        plain(g.group(2)) if g else "", "", g.group(1) if g else url, role))
    return out


def neuchatel():
    """Institut d'informatique (unine.ch/iiun) team page loads its 'Professeures et professeurs' grid via a public block endpoint (tag Institut d'informatique,
    category faculte-des-sciences). Emeriti are a separate block (not fetched). Topic = research field shown on the card."""
    import json
    atts = json.dumps({"order": "lastname,asc", "category": "faculte-des-sciences", "tag": "Institut d'informatique", "spacers": "", "search_only": False})
    url = "https://www.unine.ch/iiun/vc-block/unine-biography-grid?" + up.urlencode({"atts": atts, "lang": "fr", "cache": "false"})
    out = []
    for m in re.finditer(r'(?s)unine-biography-grid__full-link[^>]*href="([^"]*)".*?<h3[^>]*>(.*?)</h3>\s*<h4[^>]*>(.*?)</h4>', need(url)):
        out.append(prof("Université de Neuchâtel", "Institut d'informatique", plain(m.group(2)), plain(m.group(3)), "", m.group(1), "Professeur"))
    return out


SOURCES_CH3 = [stgallen, geneva, neuchatel]
