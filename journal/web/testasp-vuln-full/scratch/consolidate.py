#!/usr/bin/env python3
"""Consolidate all ffuf/gobuster results for testasp.vulnweb.com into one dataset."""
import json, os, glob, re
from collections import defaultdict, Counter

BASE = "/tmp/full/sub5"

def load_ffuf(path, tool):
    if not os.path.exists(path):
        return []
    try:
        d = json.load(open(path))
    except Exception as e:
        print("skip", path, e); return []
    out = []
    for r in d.get("results", []):
        out.append({
            "tool": tool,
            "url": r["url"],
            "status": r["status"],
            "length": r["length"],
            "words": r.get("words"),
            "src": os.path.basename(path),
        })
    return out

rows = []
rows += load_ffuf(f"{BASE}/ffuf_dirs.json", "ffuf#1 raft(no-ext,proxy)")
rows += load_ffuf(f"{BASE}/ffuf_ext.json",  "ffuf#2 raft+10ext(direct)")
rows += load_ffuf(f"{BASE}/probe.json",      "ffuf#3 quickhits+2ext/images(probe)")
rows += load_ffuf(f"{BASE}/subdirs/.json",   "ffuf#3 quickhits+9ext/cgi-bin(oldrun)")

# gobuster text parsing
gb = f"{BASE}/gobuster.txt"
if os.path.exists(gb):
    for line in open(gb, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        m = re.match(r"^(\S+)\s+\(Status:\s*(\d+)\)\s*\[Size:\s*(\d+)\](?:\s*\[-->\s*(\S+)\])?", line)
        if m:
            p, st, sz, loc = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            rows.append({"tool": "gobuster common+asp,txt,bak,inc(proxy)",
                         "url": f"http://testasp.vulnweb.com/{p}",
                         "status": st, "length": sz, "words": None,
                         "src": "gobuster.txt", "location": loc})

# subdir runs
for f in sorted(glob.glob(f"{BASE}/subdirs/*.json")):
    d = os.path.basename(f).replace(".json", "")
    rows += load_ffuf(f, f"ffuf#4 quickhits+9ext/{d}(direct)")

# ---- dedupe identical tool+url+status+length ----
seen, uniq = set(), []
for r in rows:
    k = (r["tool"], r["url"], r["status"], r["length"])
    if k in seen:
        continue
    seen.add(k); uniq.append(r)

# ---- normalize path, collapse IIS case-variants ----
def norm(r):
    u = r["url"]
    p = u.split("testasp.vulnweb.com", 1)[1] or "/"
    return p

byloc = defaultdict(lambda: {"statuses": set(), "lengths": set(), "tools": set(), "paths": set()})
for r in uniq:
    key = (r["status"], r["length"], norm(r).lower().rstrip("/") or "/")
    bylocc = key
    bylocc = key
    bylocc = key
    e = byloc[bylocc]
    e["statuses"].add(r["status"]); e["lengths"].add(r["length"])
    e["tools"].add(r["tool"].split()[0]); e["paths"].add(norm(r))

print("=" * 100)
print(f"RAW rows: {len(rows)}  |  after exact-dedupe: {len(uniq)}  |  unique case-insensitive locations: {len(byloc)}")
print("=" * 100)
print(f"{'status':>6} {'len':>7}  {'srcs':<12} path")
for (st, ln, lp), e in sorted(byloc.items(), key=lambda kv: (kv[0][0], kv[0][2])):
    real = sorted(e["paths"])[0]
    npaths = len(e["paths"])
    print(f"{st:>6} {ln:>7}  {npaths:>2} variants  {real}")

# ---- set difference: scan2 vs scan1 (file-level) ----
s1 = {norm(r).lower().rstrip("/") for r in uniq if r["src"] == "ffuf_dirs.json"}
s2 = {norm(r).lower().rstrip("/") for r in uniq if r["src"] == "ffuf_ext.json"}
print("\n" + "=" * 100)
print("scan#1 (raft, no ext) locations:", len(s1))
print("scan#2 (raft + 10 ext) locations:", len(s2))
new = sorted(x for x in s2 - s1 if not x.endswith("/") and "." in x.rsplit("/", 1)[-1])
print(f"NEW file paths only found by scan#2 (-e): {len(new)}")
for n in new:
    print("   +", n)
only1 = sorted(s1 - s2)
print("only in scan#1:", only1)

# ---- gobuster vs ffuf ----
gset = {norm(r).lower().rstrip("/") for r in uniq if r["tool"].startswith("gobuster")}
fset = {norm(r).lower().rstrip("/") for r in uniq if r["tool"].startswith("ffuf")}
print("\n" + "=" * 100)
print("gobuster-only:", sorted(gset - fset))
print("ffuf-only (root-level files):", sorted(x for x in fset - gset if x.count("/") == 1 and "." in x))
print("both agree on:", sorted(gset & fset))

# ---- status histogram ----
print("\n" + "=" * 100)
print("status histogram (deduped rows):", dict(Counter(r["status"] for r in uniq)))
print("tool row counts:", dict(Counter(r["tool"].split()[0] for r in uniq)))

json.dump(uniq, open(f"{BASE}/merged.json", "w"), indent=1)
print("\nwrote", f"{BASE}/merged.json")
