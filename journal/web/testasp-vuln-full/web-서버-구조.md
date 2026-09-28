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
