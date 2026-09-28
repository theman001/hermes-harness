#!/usr/bin/env python3
"""Analyse every downloaded .js / .css asset (round4)."""
import os, re, json, glob, collections

BASE = os.path.dirname(os.path.abspath(__file__))
JSD = os.path.join(BASE, "..", "js")

PATTERNS = {
    "document.write": r"document\.write\s*\(",
    "innerHTML": r"\.innerHTML",
    "outerHTML": r"\.outerHTML",
    "eval(": r"\beval\s*\(",
    "new Function": r"new\s+Function\s*\(",
    "setTimeout(string)": r"setTimeout\s*\(\s*['\"]",
    "document.cookie": r"document\.cookie",
    "XMLHttpRequest": r"XMLHttpRequest",
    "ActiveXObject": r"ActiveXObject",
    "createElement('script')": r"createElement\s*\(\s*['\"]script",
    "location.href=": r"location\.href\s*=",
    "top.window.opener": r"window\.opener",
    "execCommand": r"execCommand\s*\(",
}

out = {}
for f in sorted(glob.glob(os.path.join(JSD, "*"))):
    if f.endswith(".headers.txt") or f.endswith(".map"):
        continue
    src = open(f, "rb").read().decode("latin-1")
    n = os.path.basename(f)
    if not (n.endswith(".js") or n.endswith(".css")):
        continue
    lines = src.split("\n")
    loc = {}
    for k, p in PATTERNS.items():
        hits = [i for i, l in enumerate(lines, 1) if re.search(p, l)]
        if hits:
            loc[k] = {"count": len(re.findall(p, src)), "lines": hits[:25]}
    vers = re.findall(r"(?:majorVersion|minorVersion|releaseDate)\s*[:=]\s*['\"]([^'\"]+)", src)
    rcs = re.findall(r"\$RCSfile: ([^,]+),v \$|\$Revision: ([\d\.]+) \$|\$Date: ([\d/: ]+)\$", src)
    out[n] = {
        "bytes": len(src), "lines": len(lines),
        "version_fields": vers,
        "rcs": [x for x in rcs][:4],
        "dangerous": loc,
        "urls": sorted(set(re.findall(r"https?://[^\s'\"\)<>]+", src)))[:15],
        "path_templates": sorted(set(re.findall(r"['\"](/(?:themes|plugins|langs|images|css)/[^'\"]*)['\"]", src)))[:20],
        "server_endpoints": sorted(set(re.findall(r"[\w/\.\-]*\.(?:php|asp|aspx|cgi)", src, re.I)))[:20],
    }
json.dump(out, open(os.path.join(BASE, "js_analysis_all.json"), "w"), indent=1)
for n, d in out.items():
    print("=" * 60)
    print(f"{n}: {d['bytes']}b / {d['lines']} lines  version={d['version_fields']}  rcs={d['rcs']}")
    for k, v in d["dangerous"].items():
        print(f"   {k}: count={v['count']} lines(first25)={v['lines']}")
    print("   urls:", d["urls"])
    print("   path_templates:", d["path_templates"])
    print("   endpoints:", d["server_endpoints"])
