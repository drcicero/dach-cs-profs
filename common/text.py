"""Small text helpers shared by the scrapers."""
import html
import re


def plain(s):
    s = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
