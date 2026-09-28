#!/usr/bin/env python3
"""Read-only SQLi probe harness for testasp.vulnweb.com (GET only, no redirect follow)."""
import json, os, ssl, sys, time, urllib.error, urllib.parse, urllib.request

BASE = "http://testasp.vulnweb.com"
OUT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(OUT, "requests.jsonl")
_CNT = os.path.join(OUT, ".counter")
_counter = [int(open(_CNT).read()) if os.path.exists(_CNT) else 0]


def _bump():
    _counter[0] += 1
    with open(_CNT, "w") as f:
        f.write(str(_counter[0]))
    return _counter[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def get(path, params=None, tag="", save=True):
    """params: dict of raw (already-unencoded) values; we encode exactly once."""
    n = _bump()
    qs = ""
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    url = f"{BASE}{path}" + (("?" + qs) if qs else "")
    t0 = time.time()
    try:
        with OPENER.open(url, timeout=25) as r:
            code, body, hdrs = r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        code, body, hdrs = e.code, e.read(), dict(e.headers)
    except Exception as e:  # noqa
        code, body, hdrs = -1, b"", {"error": repr(e)}
    dt = time.time() - t0
    fn = ""
    if save:
        fn = os.path.join(OUT, f"r{n:04d}_{tag or 'req'}.body")
        with open(fn, "wb") as f:
            f.write(body)
    rec = {"n": n, "url": url, "path": path, "code": code, "size": len(body),
           "time": round(dt, 3), "file": os.path.basename(fn), "tag": tag,
           "loc": hdrs.get("Location", "")}
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec, body.decode("iso-8859-1", "replace")


def count_posts(html):
    return html.count("class='posttext'") + html.count('class="posttext"')


def count_threads(html):
    return html.count("class='threadtitle'")


def count_rows(html):
    return html.count("<tr bgcolor=")


if __name__ == "__main__":
    print("harness ready", OUT)
