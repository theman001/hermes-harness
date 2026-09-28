#!/usr/bin/env python3
"""보고서용 증거 원문 발췌 생성 — 기존 out/ 증거 파일에서 실제 바이트를 뽑아 마크다운으로 정리.
새 조사/새 판단은 하지 않는다(organize-exploit-artifacts 경계). 발췌·재배열만.
출력: journal/web/testasp-vulnweb-full/증거-원문-발췌.md
"""
import html
import json
import os
import re
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRATCH = os.path.join(PROJ, "scratch")
OUT = os.path.join(PROJ, "증거-원문-발췌.md")

buf = []
W = buf.append


def read(p, enc="latin-1"):
    try:
        with open(p, encoding=enc, errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return None


def body_main(s, n=1600):
    """LFI 응답에서 반복 템플릿(헤더/푸터)을 벗겨내고 알맹이만"""
    if s is None:
        return "(파일 없음)"
    i = s.find("MainContentLeft")
    if i == -1:
        i = s.find("MainContent")
    seg = s[i:] if i != -1 else s
    seg = re.sub(r"(?s)<script.*?</script>", "", seg)
    seg = html.unescape(seg)
    seg = re.sub(r"[ \t]+\n", "\n", seg)
    seg = re.sub(r"\n{3,}", "\n\n", seg)
    return seg[:n].strip()


sect = []


def add(title, text, lang=""):
    sect.append((title, text, lang))


# 1) LFI — 자격증명
d = read(os.path.join(SCRATCH, "round5/out/tpl_db_asp.html"))
m = re.search(r"Provider=[^<\r\n]{0,200}", d or "")
add("1-1. LFI → `db.asp` (DB 연결문자열 평문 노출)", (m.group(0) if m else "(추출 실패)").strip(), "text")

# 2) LFI — Search.asp 소스의 SQLi 쿼리
d = read(os.path.join(SCRATCH, "round5/out/tpl_search_asp.html"))
if d:
    m = re.search(r"(?s)(tfSearch|CHARINDEX).{0,400}", html.unescape(d))
    add("1-2. LFI → `Search.asp` 소스 (SQLi 지점 쿼리 원문)", (m.group(0) if m else body_main(d, 900)).strip(), "vbscript")
else:
    add("1-2. LFI → `Search.asp` 소스", "(파일 없음)", "")

# 3) LFI — ShowThread.asp 의 파괴적 DELETE 분기
d = read(os.path.join(SCRATCH, "round5/out/tpl_showthread_asp.html"))
if d:
    t = html.unescape(d)
    m = re.search(r"(?s)DELETE.{0,420}", t)
    add("1-3. LFI → `ShowThread.asp` 소스 (파괴적 DELETE 분기 존재)", (m.group(0) if m else t[:600]).strip(), "vbscript")
else:
    add("1-3. LFI → `ShowThread.asp` 소스", "(파일 없음)", "")

# 4) LFI — web.config
add("1-4. LFI → `web.config` (200 / 3,138B)", body_main(read(os.path.join(SCRATCH, "round5/out/tpl_web_config.html")), 700), "xml")

# 5) LFI — 웹루트 밖
for label, f, path in [
    ("1-5. LFI → `C:\\Windows\\win.ini` (웹루트 밖)", "round5/out/tpl_dotdot4_winini.html", "C:\\Windows\\win.ini"),
    ("1-6. LFI → `C:\\Windows\\system32\\drivers\\etc\\hosts`", "round5/out/tpl_dotdot4_hosts.html", "hosts"),
]:
    t = body_main(read(os.path.join(SCRATCH, f)), 400)
    add(f"{label}", "\n".join(t.splitlines()[:14]), "text")

# 7) Round 7 — IIS/설정 파일 열거 결과(200/500)
txt = read(os.path.join(SCRATCH, "round7/probe_lfi_iis.txt"), enc="utf-8")
if txt:
    ok = [l for l in txt.splitlines() if re.search(r"\b200\b", l)]
    bad = [l for l in txt.splitlines() if re.search(r"\b500\b", l)]
    add("2-1. Round 7 — IIS·설정·로그 파일 존재 오라클 (200 = 읽힘)",
        "\n".join(ok[:40]) or "(없음)", "")
    add("2-2. 같은 열거에서 차단된 항목 (500 = 없음/권한 없음)",
        "\n".join(bad[:25]) or "(없음)", "")

# 8) search.asp SQLi
txt = read(os.path.join(SCRATCH, "round5/probe_search_sqli2.txt"), enc="utf-8")
if txt:
    add("3-1. `/search.asp` boolean-blind — TRUE/FALSE 응답 분기",
        "\n".join([l for l in txt.splitlines() if l.strip()][:40]), "")

# 9) id SQLi
txt = read(os.path.join(SCRATCH, "round7/probe_b_sqli2.txt"), enc="utf-8")
if txt:
    add("3-2. `/showforum.asp`·`/showthread.asp` id 파라미터 — TRUE=200/FALSE=500",
        "\n".join([l for l in txt.splitlines() if l.strip()][:40]), "")

# 10) POST 주입 무효 시도(-G 411) 기록
txt = read(os.path.join(SCRATCH, "round7/probe_b_post_inj.txt"), enc="utf-8")
if txt:
    add("3-3. 무효화된 시도 — `curl -X POST -G` 로 본문 소실 → IIS 411",
        "\n".join([l for l in txt.splitlines() if l.strip()][:18]), "")

# 11) 저장형 XSS 렌더 문맥
s = read(os.path.join(SCRATCH, "round6/out/r6b_after_anon.html"))
if s:
    i = s.find("RT6-STORED-XSS-PROOF")
    add("4-1. 저장형 XSS — 미인증 조회 응답의 렌더 문맥",
        s[max(0, i - 320):i + 220].replace("\r", "") if i != -1 else "(마커 없음)", "html")

# 12) CDP 실행 증거
js = read(os.path.join(SCRATCH, "round6/out/xss_exec_proof.txt"), enc="utf-8") or \
     read(os.path.join(SCRATCH, "round6/xss_exec_proof.txt"), enc="utf-8")
if js:
    add("4-2. 브라우저 실제 실행 증거 (CDP json)", js.strip(), "json")
else:
    add("4-2. 브라우저 실제 실행 증거 (CDP json)", "(파일 없음)", "")

# 13) Round 8/9/10 JSON 요약
for label, f in [
    ("5-1. Round 8 — DB·권한 사실 (`out/db_facts.json`)", "round8/out/db_facts.json"),
    ("5-2. Round 8 — 스키마·계정 (`out/db_facts2.json`)", "round8/out/db_facts2.json"),
    ("5-3. Round 8 — 비밀번호 형식·교차 DB (`out/db_facts3.json`)", "round8/out/db_facts3.json"),
    ("5-4. Round 9 — 교차 앱 스키마·행 (`out/db_facts4.json`)", "round9/out/db_facts4.json"),
]:
    j = read(os.path.join(SCRATCH, f), enc="utf-8")
    if j:
        try:
            o = json.loads(j)
            add(label, json.dumps(o, ensure_ascii=False, indent=2)[:2600], "json")
        except Exception:
            add(label, j[:1200], "json")

# 14) Round 10 — LFI 도달 판정
j = read(os.path.join(SCRATCH, "round10/out/backup_paths3.json"), enc="utf-8")
if j:
    add("6-1. Round 10 — 백업/DB 파일 LFI 도달 판정 (대조군 통과 후 음성)", j.strip()[:2600], "json")
j = read(os.path.join(SCRATCH, "round10/out/backup_paths.json"), enc="utf-8")
if j:
    add("6-2. Round 10 — 백업 이력·인스턴스 경로 (요약)", j.strip()[:1800], "json")

# 15) Round 13 — Register.asp INSERT SQLi 실증
j = read(os.path.join(SCRATCH, "round13/out/register_sqli.json"), enc="utf-8")
if j:
    add("7-1. Round 13 — Register.asp INSERT SQLi 검증 결과(JSON 요약)", j.strip()[:3200], "json")
t = read(os.path.join(SCRATCH, "round13/probe_register_sqli.txt"), enc="utf-8")
if t:
    add("7-2. Round 13 — 실행 로그 전문(기준선→주입→교차검증→대조군)", t.strip()[:3200], "")
t = read(os.path.join(SCRATCH, "round13/verify_extra.txt"), enc="utf-8")
if t:
    add("7-3. Round 13 — 주입 행 속성·무결성 재확인(읽기 전용 오라클)", t.strip()[:2200], "")
t = read(os.path.join(SCRATCH, "round13/verify_reset.txt"), enc="utf-8")
if t:
    add("7-4. Round 13 — ★ 데모 DB 리셋 확인(Round 6·7 산출물이 서버에서 사라짐)", t.strip()[:2400], "")

# 16) Round 14 — 정합성 점검·재현성 이력
j = read(os.path.join(SCRATCH, "round14/out/consistency.json"), enc="utf-8")
if j:
    add("8-1. Round 14 — 헤드라인 PoC 재현 + 리다이렉트 매트릭스(JSON)", j.strip()[:3200], "json")
t = read(os.path.join(SCRATCH, "round14/verify_ids.txt"), enc="utf-8")
if t:
    add("8-2. Round 14 — 현존 id 발견 + id SQLi 재확인 + 오라클 기준값", t.strip()[:2400], "")
t = read(os.path.join(SCRATCH, "round14/fix_artifacts.txt"), enc="utf-8")
if t:
    add("8-3. Round 14 — 산출물 수선 이력(백업 후 11곳 치환)", t.strip()[:1400], "")

# ---- 조립 ----
W("# 증거 원문 발췌 — testasp.vulnweb.com\n")
W("기존 라운드에서 저장해 둔 **원시 응답 파일에서 그대로 발췌**한 자료다(재조사 없음).")
W("원본 파일 경로를 각 항목에 병기했으므로 보고서 작성 시 그대로 인용하거나 재확인할 수 있다.")
W("전체 원문은 `scratch/round4~round10/out/` 에 있다.\n")
for t, text, lang in sect:
    W(f"\n## {t}\n")
    W("```" + lang)
    W(text)
    W("```")
W("")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf))
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes, {len(sect)} sections)")
