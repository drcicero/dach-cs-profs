"""Position of a person, shown as a sortable column on the professors page. ROLES is ordered by seniority (index = sort rank).
A scraper that knows the position (a section heading such as 'Assistenzprofessuren', a role label) passes `role=`; otherwise it is guessed from the title printed before the name
(Jun.-Prof., Assoc. Prof., Hon.-Prof., apl. Prof. ...) and from the topic text, a printed 'Prof.' / 'Professor' counts as 'Professor', and when nothing says more the position is left empty ('')."""
import re

ROLES = ["Director", "Professor", "Faculty", "Associate professor", "Assistant / junior professor", "Group leader", "Honorary / visiting / secondary"]
RANK = {r: i for i, r in enumerate(ROLES)}
RANK["Faculty"] = RANK["Professor"]  # tenured / tenure-track faculty of a research institute: ranked like a professor
GUESS = [
    ("Director", re.compile(r"Scientific Director|Wissenschaftliche[rs] (?:Direktor|Mitglied)", re.I)),
    ("Assistant / junior professor", re.compile(r"\bJ(?:un(?:ior)?)?\.?-?\s?Prof|Juniorprofessur|Assistenzprof|Professeure? assistant|Professeure? boursier|Assistant Prof|Assistenzprofessor|Tenure[- ]Track|\bAss\.?\s?Prof|\bAssistenz-?Prof", re.I)),
    ("Associate professor", re.compile(r"Assoziiert|Professeure? associ|Assoc(?:iate|\.)? ?(?:-)?Prof|Assoz\.? ?(?:-)?Prof|Associate Professor", re.I)),
    ("Honorary / visiting / secondary", re.compile(r"\bHon\.?-?\s?Prof|Honorarprof|\bapl\.|au(?:ß|ss)erplan|\bGastprof|Visiting Prof|Vertretungsprof|Professor(?:en)?vertretung|Professurvertretung|Adjunct|Zweitmitglied|Affiliate", re.I)),
]


def role_of(raw_name, topic="", role=""):
    """Normalised role: `role` if it is one of ROLES; else guessed from the raw name (with its title) and the topic; 'Professor' if only a Prof. title shows; else '' (unknown)."""
    if role in ROLES:
        return role
    for label, rx in GUESS:  # `role` may also be the raw position text of the page ('Assistant Professor', 'Associate Professor of ...')
        if rx.search(role) or rx.search(raw_name) or rx.search(topic):
            return label
    if re.search(r"prof(?:\.|ess(?:or|ur|eur))", f"{role} {raw_name} {topic}", re.I):  # a printed professor title, no more precise position
        return "Professor"
    return ""  # nothing says what the position is: left empty, not guessed
