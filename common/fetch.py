"""Polite cached HTTP layer shared by the job-ad and the professor scrapers: per-day page cache (cache/YYYY-MM-DD/, never cleared), >= DELAY seconds between two
requests to the same host (HOST_DELAY for robots.txt Crawl-delays; different hosts run in parallel), robots.txt check, retries for transient network errors,
a thread-pool runner for the sources and the Vaadin Flow session helper (Hohenheim, Erlangen)."""
import concurrent.futures
import contextlib
import datetime
import gzip
import hashlib
import http.cookiejar
import json
import os
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.parse as up
import urllib.request
import urllib.robotparser


CACHE = pathlib.Path("cache") / datetime.date.today().isoformat()


UA = "Mozilla/5.0 (research script; one small cached fetch per day)"


DELAY = 2.0


HOST_DELAY = {"gjb.hhu.de": 10.0, "www.cs.hhu.de": 10.0, "jobs.aau.at": 4.0, "boku.ac.at": 10.0}  # robots.txt Crawl-delay per host (seconds)


_hosts = {}  # netloc -> [lock, time of the last request]


_lock = threading.Lock()  # guards _hosts, STATS and index.tsv


STATS = {"web": 0, "cached": 0}


@contextlib.contextmanager
def throttle(url):
    """Hold the host's lock and wait until its delay since the previous request has passed; requests to other hosts are not blocked."""
    host = up.urlsplit(url).netloc
    with _lock:
        entry = _hosts.setdefault(host, [threading.Lock(), 0.0])
    with entry[0]:
        time.sleep(max(0.0, HOST_DELAY.get(host, DELAY) - (time.time() - entry[1])))
        try:
            yield
        finally:
            entry[1] = time.time()


def count(key):
    with _lock:
        STATS[key] += 1


def run_sources(sources, workers=12):
    """Call every source in a thread pool; returns [(source, rows or None, error or None)] in the order of `sources`."""
    def one(src):
        try:
            res = (src, src(), None)
        except Exception as e:
            res = (src, None, e)
        print(f"  done {src.__name__} (web so far: {STATS['web']}, cached: {STATS['cached']})", file=sys.stderr, flush=True)
        return res
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, sources))


def fetch(url, body=None, headers=None):
    """GET url (or POST the JSON-serialisable body) with a per-day cache; `headers` = extra request headers (the URL still identifies the cache entry)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    data = json.dumps(body, sort_keys=True).encode() if body is not None else None
    f = CACHE / hashlib.sha1(url.encode() + (data or b"")).hexdigest()[:16]
    if f.exists():
        count("cached")
        return f.read_text(encoding="utf-8")
    with throttle(url):
        if f.exists():  # another thread fetched it while we waited for the host
            count("cached")
            return f.read_text(encoding="utf-8")
        print(f"    GET {url[:100]}", file=sys.stderr, flush=True)
        req = urllib.request.Request(up.quote(url, safe=":/?#[]@!$&'()*+,;=%~"), data=data,  # percent-encode non-ASCII (e.g. '§' in Krems URLs)
                                      headers={"User-Agent": UA, **({"Content-Type": "application/json"} if data else {}), **(headers or {})})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                break
            except urllib.error.HTTPError:
                raise  # the server answered: 404 etc. are real results (robots_ok relies on this)
            except OSError:  # 'No route to host', timeouts, resets: usually transient, retry after 5/10/20 s
                if attempt == 3:
                    raise
                print(f"    retry {attempt + 1} {url[:100]}", file=sys.stderr, flush=True)
                time.sleep(5 * 2 ** attempt)
        if raw[:2] == b"\x1f\x8b":  # some servers gzip even without Accept-Encoding
            raw = gzip.decompress(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:  # some older CMS (RWTH, Heidelberg) still send latin-1
            text = raw.decode("cp1252", "replace")
    count("web")
    tmp = f.with_name(f.name + f".{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)
    with _lock, open(CACHE / "index.tsv", "a", encoding="utf-8") as idx:
        idx.write(f"{f.name}\t{url}\n")
    return text


def vaadin_home(base, name):
    """UIDL message of the start page of a Vaadin Flow app (the list exists only in a session, JSESSIONID cookie), cached like a page under `name`.
    Handshake: GET /?v-r=init&location=&query= (→ Vaadin-Security-Key), POST /?v-r=uidl&v-uiId=N with an empty rpc list (syncId 0, clientId 0),
    then the 'ui-navigate' event for route '/' (syncId 1, clientId 1) → the page as a list of 'changes'."""
    f = CACHE / hashlib.sha1(name.encode()).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    if f.exists():
        count("cached")
        return json.loads(f.read_text(encoding="utf-8"))
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def call(url, body=None):
        with throttle(url):
            print(f"    {'POST' if body else 'GET'} {url[:100]}", file=sys.stderr, flush=True)
            hdr = {"User-Agent": UA, **({"Content-Type": "application/json; charset=UTF-8"} if body else {})}
            r = op.open(urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=hdr), timeout=30).read().decode("utf-8")
        count("web")
        return json.loads(r)

    init = call(base + "?v-r=init&location=&query=")["appConfig"]
    tok, uid = init["uidl"]["Vaadin-Security-Key"], init["v-uiId"]
    url = f"{base}?v-r=uidl&v-uiId={uid}"
    call(url, {"csrfToken": tok, "rpc": [], "syncId": 0, "clientId": 0})
    msg = call(url, {"csrfToken": tok, "syncId": 1, "clientId": 1, "rpc": [{"type": "event", "node": 1, "event": "ui-navigate", "data": {
        "route": "/", "query": "", "appShellTitle": "", "historyState": {"idx": 0}, "trigger": ""}}]})
    f.write_text(json.dumps(msg), encoding="utf-8")
    with _lock, open(CACHE / "index.tsv", "a", encoding="utf-8") as idx:
        idx.write(f"{f.name}\t{name} ({base})\n")
    return msg


_ROBOTS = {}


def robots_ok(url):
    """True if the host's robots.txt (cached like every page) allows a generic bot to fetch url; a missing robots.txt (404) allows, any other error does not."""
    root = "{0.scheme}://{0.netloc}".format(up.urlsplit(url))
    if root not in _ROBOTS:
        p = urllib.robotparser.RobotFileParser()
        try:
            p.parse(fetch(root + "/robots.txt").splitlines())
            _ROBOTS[root] = p
        except urllib.error.HTTPError as e:
            _ROBOTS[root] = None if e.code in (404, 410) else False
        except Exception:
            _ROBOTS[root] = False
    p = _ROBOTS[root]
    return True if p is None else bool(p) and p.can_fetch("*", url)
