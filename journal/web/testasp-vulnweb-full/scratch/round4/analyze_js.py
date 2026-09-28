#!/usr/bin/env python3
"""Static analysis of downloaded JS/CSS for testasp.vulnweb.com round4."""
import re, json, os, collections, sys

BASE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(BASE, "..", "js")
PAGES = os.path.join(BASE, "..", "pages")

def read(p):
    with open(p, "rb") as f:
        return f.read().decode("latin-1")

out = {}

for name in ("tiny_mce.js", "tiny_mce_src.js"):
    src = read(os.path.join(JS, name))
    d = {}
    d["bytes"] = len(src)
    d["lines"] = src.count("\n") + 1
    # version
    vers = set()
    for pat in [r"majorVersion\s*[:=]\s*['\"](\d+)", r"minorVersion\s*[:=]\s*['\"](\d+)",
                r"releaseDate\s*[:=]\s*['\"]([\d\-]+)",
                r"Version:\s*([\d\.a-z]+)", r"tiny_mce[^\n]{0,40}?([23]\.\d+\.?\d*\.?\d*)",
                r"\$Rev\s*[:=]\s*['\"]?([^'\"\s]+)"]:
        vers.update(re.findall(pat, src, re.I))
    d["version_candidates"] = sorted(vers)[:20]
    # first 3 lines comment banner
    d["banner"] = src[:300].replace("\n", "\\n")[:300]
    # URLs / paths
    urls = sorted(set(re.findall(r"https?://[^\s'\"\)<>]+", src)))
    d["http_urls"] = urls[:60]
    d["http_url_count"] = len(urls)
    paths = sorted(set(re.findall(r"['\"](/[A-Za-z0-9_\-/\.]+\.(?:js|htm|html|php|asp|gif|png|css))['\"]", src)))
    d["abs_paths"] = paths[:80]
    d["abs_path_count"] = len(paths)
    # plugin/theme/lang references
    plugs = sorted(set(re.findall(r"plugins?/([a-z0-9_]+)", src, re.I)))
    d["plugin_dirs"] = plugs
    langs = sorted(set(re.findall(r"langs?/([a-z_\-]+)\.js", src, re.I)))
    d["lang_files"] = langs[:60]
    d["lang_file_count"] = len(langs)
    themes = sorted(set(re.findall(r"themes/([a-z0-9_]+)", src, re.I)))
    d["themes"] = themes
    skins = sorted(set(re.findall(r"skins/([a-z0-9_]+)", src, re.I)))
    d["skins"] = skins
    # dangerous APIs
    danger = {}
    for api, pat in {
        "document.write": r"document\.write\s*\(",
        "innerHTML": r"\.innerHTML",
        "outerHTML": r"\.outerHTML",
        "eval(": r"\beval\s*\(",
        "new Function": r"new\s+Function\s*\(",
        "setTimeout(str)": r"setTimeout\s*\(\s*['\"]",
        "execScript": r"execScript",
        "ActiveXObject": r"ActiveXObject",
        "document.cookie": r"document\.cookie",
        "window.location": r"window\.location",
        "location.href": r"location\.href",
        "XMLHttpRequest": r"XMLHttpRequest",
        "createElement(script)": r"createElement\s*\(\s*['\"]script",
        "insertAdjacentHTML": r"insertAdjacentHTML",
        "atob/unescape": r"\bunescape\s*\(",
    }.items():
        danger[api] = len(re.findall(pat, src))
    d["dangerous_api_counts"] = danger
    # request paths: url params, .asp/.php fetch
    d["asp_php_refs"] = sorted(set(re.findall(r"[A-Za-z0-9_\-/\.]+\.(?:asp|aspx|php|cgi)", src, re.I)))[:40]
    out[name] = d

# line numbers for dangerous APIs in each file (first N occurrences)
for name in ("tiny_mce.js", "tiny_mce_src.js"):
    src = read(os.path.join(JS, name))
    lines = src.split("\n")
    loc = collections.defaultdict(list)
    pats = {"document.write": r"document\.write\s*\(", "eval(": r"\beval\s*\(",
            "innerHTML": r"\.innerHTML", "new Function": r"new\s+Function\s*\(",
            "ActiveXObject": r"ActiveXObject", "document.cookie": r"document\.cookie"}
    for i, l in enumerate(lines, 1):
        for k, p in pats.items():
            if re.search(p, l):
                loc[k].append(i)
    out[name]["dangerous_line_numbers"] = {k: v[:40] for k, v in loc.items()}
    # snippets for eval/document.write
    snips = {}
    for k, p in (("document.write", r"document\.write\s*\("), ("eval(", r"\beval\s*\(")):
        for i, l in enumerate(lines, 1):
            if re.search(p, l):
                snips.setdefault(k, []).append(f"L{i}: {l.strip()[:200]}")
    out[name]["dangerous_snippets"] = {k: v[:12] for k, v in snips.items()}

print(json.dumps(out, indent=2, ensure_ascii=False))
