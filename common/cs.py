"""Computer-science keyword rules shared by the job-ad page and the professors page (CS-related filter, bold keyword highlighting)."""
import html
import re

# Matched on title + topic only (not the description, which names the whole department).
# Strong words always make an ad CS; weak ones only count when no (named) unit says otherwise.
CS_STRONG = re.compile(r"informatik|informatics|computer|software", re.I)
CS_WEAK = re.compile(r"security|machine learning|artificial intelligence|\bAI\b|\bKI\b|künstliche|data science|datenbank|algorithm|robot|chip|"
                     r"network|netz|cyber|kryptograph|logic|verification|programming|quantum comput|it-sicherheit|informationssicherheit|"
                     r"maschinelles lernen|deep learning|rechnerarchitektur|betriebssystem|verteilte system|eingebettete|embedded", re.I)
CS = re.compile(CS_STRONG.pattern + "|" + CS_WEAK.pattern, re.I)  # kept for quick keyword checks


def bold(text, rx):
    """HTML-escaped text with the regex matches in <b>."""
    out, pos = [], 0
    for m in rx.finditer(text):
        out.append(html.escape(text[pos:m.start()]) + "<b>" + html.escape(m.group()) + "</b>")
        pos = m.end()
    return "".join(out) + html.escape(text[pos:])
