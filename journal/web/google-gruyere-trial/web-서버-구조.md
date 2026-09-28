# 서버 구조 — google-gruyere-trial

## 대상 개요
- Google 공식 취약 웹앱 코드랩 "Gruyere" (Web Application Exploits and Defenses).
- **호스팅판** = App Engine. 방문자마다 고유 인스턴스(GID)를 받고 `/<gid>/` 경로로만 동작.
  `_unique_id` 가 경로 첫 세그먼트로 강제되며(소스 `DoGetOrPost` 의 "DO NOT CHANGE" 블록),
  경로에 GID 가 없으면 `/` 로 리다이렉트되고 그 외에는 요청이 거부된다.
- GID 획득: `GET /start` → `Set-Cookie: GRUYERE_ID=<29자리>` + HTML 안에 인스턴스 id.
  이후 `GET /<gid>` → `302 Location: /<gid>/`.

## 인증 방식
- **세션 쿠키 1개**, 이름 `GRUYERE`. 값은 `hash|uid|is_admin|is_author` 형태의 평문 플래그 묶음.
  - 예: 로그인 성공 시 `Set-Cookie: GRUYERE=74315992|brie||author; path=/<gid>`
  - `hash` = `str(hash(cookie_secret + '%s|%s|%s' % (uid, is_admin, is_author)) & 0x7FFFFFF)`
    (소스 `_CreateCookie`/`_ParseCookie`). 서명 공간 27비트, `cookie_secret` 은 서버 파일 `secret.txt` 첫 줄.
  - `is_admin` 필드는 값이 `'admin'` 이면 True, `is_author` 는 `'author'` 이면 True.
- **쿠키 플래그 없음** — HttpOnly/Secure/SameSite 전부 미설정(실측). `path=/<gid>` 만 지정.
- 로그인은 **GET + 쿼리스트링** (`?uid=&pw=`). 비밀번호가 URL 에 실린다.
- 서버는 계정을 서버측 세션에 보관하지 않는다 — 쿠키가 곧 신원(서명만 맞으면 신뢰).

### 재현 가능한 로그인 curl (project 레벨 영속 — phase 넘어 재사용)
```bash
cd /home/taeuk/projects/llm-abliteration/hermes-harness/journal/web/google-gruyere-trial/scratch
GID=$(cut -d= -f2 gid.txt)          # 확보한 샌드박스 id (아래 "GID 확보" 참고)
PX=(-x http://127.0.0.1:8080 --cacert /home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem)
B="https://google-gruyere.appspot.com/$GID"

# 0) GID 없으면 새로 확보 (새 샌드박스가 발급됨 — 기존 데이터는 사라짐)
curl -s "${PX[@]}" -c gruyere.cookies -b gruyere.cookies \
  "https://google-gruyere.appspot.com/start" -o start.html
GID=$(grep -oE 'Gruyere instance id is [0-9]+' start.html | grep -oE '[0-9]+')

# 1) 시드 계정 로그인 (계정 신규 생성 불필요)
curl -s "${PX[@]}" -c gruyere.cookies -b gruyere.cookies -D - \
  "$B/login?uid=brie&pw=briebrie"
# 기대: 200 + Set-Cookie: GRUYERE=<hash>|brie||author; path=/<gid>

# 2) 로그인 상태 확인
curl -s "${PX[@]}" -c gruyere.cookies -b gruyere.cookies "$B/dump.gtl"
# 기대: _cookie 에 {'uid': 'brie', ...} 가 채워져 나옴
```
- 프록시(`-x`)는 mitmproxy 캡처용. 캡처 불필요하면 `-x`/`--cacert` 를 빼면 된다.
- 쿠키 jar 는 `scratch/gruyere.cookies` (project 레벨 아님 — phase 넘어 보존 안 됨.
  GID 쿠키 `GRUYERE_ID` 와 로그인 쿠키 `GRUYERE` 를 모두 여기 담음).

## 계정/데이터
- 기본 시드 데이터(소스 `data.py` 의 `DEFAULT_DATA`, 호스팅판도 동일함을 실측 확인):
  - `administrator` / `secret` — **is_admin = True**
  - `cheddar` / `orange` — is_author True
  - `sardo` / `odras` — is_author True
  - `brie` / `briebrie` — is_author True
- 즉 관리자 계정이 기본 비밀번호로 존재한다(추정 아님 — `/dump.gtl` 로 실측 확인).
- 별도 계정을 새로 만들 필요 없이 위 시드 계정으로 인증 영역 정찰 가능.

## API 패턴
- REST 아님. 경로 → 메서드명 매핑: `_GetHandlerFunction` 이 `'_Do' + path[1:].capitalize()` 로
  `GruyereRequestHandler` 의 메서드를 찾아 호출. 못 찾으면 `resources/` 아래 정적 파일 서빙.
- 이 때문에 **핸들러가 없는 `.gtl` 템플릿은 그대로 렌더된다**(`_SendFileResponse` 경로) —
  `dump.gtl`, `manage.gtl` 이 그렇게 무인증 노출된다.
- `do_GET`/`do_POST` 모두 같은 `DoGetOrPost` 로 들어간다 → **모든 핸들러가 GET 으로도 호출 가능**.
- AJAX: `/<gid>/feed.gtl` 이 `_feed(( <JS 리터럴> ))` 를 `content-type: text/html` 로 반환.
  클라이언트 `lib.js` 의 `_refresh()` 는 `eval('(' + responseText + ')')` 로 파싱한다.

## 응답 헤더 특성
- `server: Google Frontend`, `x-cloud-trace-context: ...`
- `x-xss-protection: 0` (XSS Auditor 명시적 비활성)
- CSP / X-Frame-Options / X-Content-Type-Options / Strict-Transport-Security **없음**
- 정적 리소스는 `Cache-control: public, max-age=7200`

## tech_stack 근거 (3개 신호 일치 → 확정)
1. `Server: Google Frontend` + `x-cloud-trace-context` → Google App Engine.
2. 공개 배포 소스(`/gruyere-code.zip`)가 **Python 2.7** (`#!/usr/bin/env python2.7`,
   `BaseHTTPServer`/`cgi`/`cPickle`/`urlparse` — py2 전용 모듈).
3. 템플릿 확장자 `.gtl` + 자체 템플릿 엔진 `gtl.py`(GTL), 쿠키명 `GRUYERE`.
- 로컬판과 호스팅판 차이: 로컬판은 단일 인스턴스 + `127.0.0.1` 제한 + 경로에 랜덤 id.
  호스팅판은 `GRUYERE_ID` 쿠키로 방문자별 인스턴스를 분리한다. 취약 로직 자체는 동일 계열로 보이며
  각 항목은 실측으로 확인한다(소스 추정만으로 확정하지 않음).

## 저장소 경로 (로컬 분석용)
- 소스: `journal/web/google-gruyere-trial/scratch/src/` (gruyere.py, gtl.py, sanitize.py, data.py, resources/*.gtl)
- 원본 zip: `journal/web/google-gruyere-trial/scratch/gruyere-code.zip`

## 실측으로 확정된 서버 동작 (Round 2~5)
- **정적 파일 서빙 경로에 정규화가 없다.** 경로는 `urllib.unquote` 후 `resources/` 기준으로
  그대로 `open()` 된다. 평문 `../` 는 **Google Frontend 가 302 로 정규화 차단**하지만
  `%2e%2e%2f`(슬래시까지 인코딩)와 `..%2f` 는 통과한다 → 경로이탈 성립.
- **파일 확장자 화이트리스트가 있다**(`RESOURCE_CONTENT_TYPES`). `.css/.gif/.htm/.html/.js/
  .jpeg/.jpg/.png/.ico/.text/.txt` 만 서빙되고 그 외는 `Unrecognized file type (…)` 로
  열기 전 차단된다. 확장자 없는 파일은 `content_type='text/plain'` 으로 허용된다.
  널바이트 우회(`data.py%00.txt`)는 실패한다.
- **미처리 예외가 클라이언트에 그대로 반환된다.** 널바이트 경로 입력 시
  `<H1>Gruyere System Alert</H1><TT>Exception: file() argument 1 must be encoded string
  without null bytes, not str</TT>` 를 200 으로 응답(내부 구현/API 노출).
- **쿠키 서명 알고리즘 확정**: `서명 = py2_hash(cookie_secret + cookie_data) & 0x7FFFFFF`.
  - `cookie_secret` 은 서버의 `secret.txt` 첫 줄이며 **내용은 `Cookie!\n`** (경로이탈로 확인)
  - `cookie_data = "<uid>|<is_admin>|<is_author>"` (`is_admin` 자리에 `admin`, `is_author`
    자리에 `author` 가 들어가면 True)
  - py2 str hash 재구현: `x = ord(s[0])<<7; for c in s: x = (1000003*x) ^ ord(c) (64bit wrap);
    x ^= len(s)`
  - 실측 4쌍 4/4 일치: `brie||author`→74315992, `administrator|admin|`→31131337,
    `cheddar||author`→40461140, `sardo||author`→22005508
  - **서명은 인스턴스 무관 전역값**(GID 3개에서 동일) → 임의 uid 로 쿠키 위조 가능
- **`_PROTECTED_URLS = ['/quit', '/reset']`** 이지만 실제 핸들러명은 `/quitserver` 이다
  → `_GetHandlerFunction` 매핑상 `/quitserver` 는 보호 목록에 없어 **인증 없이 호출 가능**
  (미실행 — 승인 대상).
- 핸들러가 없는 `.gtl` 템플릿은 `_SendFileResponse` 로 렌더된다 → `dump.gtl`/`manage.gtl`/
  `showprofile.gtl` 이 그렇게 무인증 노출된다.
- `do_GET` 과 `do_POST` 가 같은 `DoGetOrPost` 로 진입 → **모든 핸들러가 GET 으로 호출 가능**.

## 실측으로 확정된 인증/권한 동작 (Round 3)
- 쿠키의 `is_admin`/`is_author` 플래그는 **로그인 시점에 프로필에서 샘플링**된다.
  세션 중 프로필을 바꿔도 그 세션 쿠키에는 반영되지 않고 **재로그인해야** 반영된다.
- `_DoSaveprofile` 은 `uid`/`is_admin`/`is_author` 를 **요청 파라미터에서 그대로** 프로필에
  기록한다(매스어사인먼트). `action=update` + `is_admin=True` 로 자기 계정을 관리자로 승격 가능.
  `_AddParameter` 는 파라미터가 truthy 일 때만 값을 넣으므로 `name` 을 주지 않으면 uid 로 덮어써진다.

## XSS 관련 실측 (Round 4~5)
- 스니펫/프로필은 서버측 `sanitize.SanitizeHtml()`(허용 태그 화이트리스트 + 이벤트핸들러
  블랙리스트)을 거치지만, **블랙리스트에 `onerror` 가 없다** → `<img src=x onerror=...>` 통과.
- 템플릿의 `{{값:html}}` = SanitizeHtml, `{{값:text}}` = `cgi.escape(str(v))`.
  **`cgi.escape` 는 py2 에서 기본 quote=False** 라 따옴표를 이스케이프하지 않는다 →
  `src='{{icon:text}}'` 같은 단일인용부호 속성에서 속성 탈출 가능.
- `{{uid.0}}` / `{{_message}}` 처럼 **escaper 없는 치환 지점**이 여러 곳 있다:
  `error.gtl` 의 `Invalid request: <path>`, `feed.gtl` 의 uid(JS 문자열), `snippets.gtl` 의
  uid(h2 HTML 문맥 + Refresh 링크 `onclick` 속성). 즉 uid 하나에 3개 문맥의 반사 지점이 있다.
- `feed.gtl` 응답은 `content-type: text/html` 이고 본문은 `_feed(( … ))` 형태의 JS 다.
  **URL 을 직접 열면 HTML 로 파싱되어 실행되지 않는다** — 실행은 `lib.js _refresh()` 의
  `eval('(' + responseText + ')')` 경로를 통해서만 일어난다.
- 응답 헤더에 CSP/X-Frame-Options/X-Content-Type-Options/HSTS 없음, `x-xss-protection: 0`.
  GRUYERE 쿠키에 HttpOnly/Secure/SameSite 없음 → XSS 시 `document.cookie` 로 세션 탈취 가능.

## 업로드 경로 실측 (Round 6, phase 2)
- `_DoUpload2` → `_ExtractFileFromRequest()` 가 `form['upload_file'].filename` 을 **그대로**
  반환(정규화·basename 절단 없음) → `_MakeUserDirectory(uid)` =
  `RESOURCE_PATH + os.sep + str(uid) + os.sep` = `resources/<uid>/` →
  `_Open(directory, filename, 'wb')` = `open('resources/<uid>/' + filename, 'wb')`.
- 따라서 `filename` 의 `../` 가 그대로 해석된다: `../../x` → 앱 루트의 `x` 에 쓴다.
  실측: `filename=../../p5r6uniq.txt` 업로드 후 `GET /<gid>/%2e%2e%2fp5r6uniq.txt` 로
  그 내용이 읽힘(쓰기 위치가 `resources/<uid>/` 밖임을 확인).
- **주의(샌드박스 경계 판단)**: `secret.txt` 와 쿠키 서명은 GID 인스턴스 간에 동일했다
  (phase 1 Round 2). 즉 이 파일은 전 GID 공용이며, 덮어쓰면 다른 사용자에게 영향이 간다
  → own_system 경계 밖. `resources/<uid>/` 안쪽과 같은 GID 내 계정 디렉터리는 내 샌드박스.
- 업로드본 서빙: `_SendFileResponse` 가 `RESOURCE_CONTENT_TYPES` 확장자 맵으로
  Content-type 을 정한다 — `.html`/`.htm` → `text/html`, `.js` → `application/javascript`.
  별도 nosniff 없음(`X-Content-Type-Options` 부재) → 업로드한 HTML 이 그대로 실행된다.
- GTL escaper 실측(`gtl.py` 205~219행): `{{x:text}}` = `cgi.escape`, `{{x:html}}` =
  `SanitizeHtml`, `{{x:pprint}}` = 디버그. **escaper 미지정 `{{x}}` 는 무이스케이프** —
  `upload2.gtl` 의 `{{url}}`/`{{_message}}`, `error.gtl` 의 메시지, `feed.gtl`/`snippets.gtl`
  의 `{{uid.0}}` 가 전부 이 범주다(반사 XSS 계열의 공통 원인).
- 경로이탈 쓰기 시 미존재 디렉터리를 지정해도 "File uploaded!" 가 반환되는 관찰이 있었다
  (원인 미규명). 이 때문에 "실패를 기대한 비파괴 판별"이 성립하지 않았다 — 다음부터 쓰기
  경로의 능력 판정은 소스로만 하고, 실행은 승인 후 1회로 한다.

### 승인 후 실행으로 확정한 쓰기 범위 (Round 6 후속)
- `filename=../../r6_root_proof.txt` → `resources/<uid>/../../` = **앱 루트**. 쓰기 후
  `GET /<gid>/%2e%2e%2fr6_root_proof.txt` 로 내용 확인(읽기 경로이탈도 동일 깊이에서 동작).
- `filename=../cheddar/r6_probe.txt` → **같은 GID 내 형제 계정 디렉터리**. 쓰기 후
  `GET /<gid>/cheddar/r6_probe.txt` 가 내가 쓴 문자열 반환 → 계정 경계 침범 확정.
- **존재 오라클 주의**: 없는 정적 파일도 `200` + `Error` 페이지를 준다(예:
  `/cheddar/zzz_absent.txt`). 정적 파일 존재 판정은 **상태코드가 아니라 본문**으로 한다.

## 템플릿 엔진(gtl.py) 실측 (Round 7)
- 문법: `{{field.sub:escaper}}`, `[[if:x]]…[[/if:x]]`, `[[for:x]]…[[/for:x]]`,
  `[[include:file]][[/include:file]]`(닫는 태그 필수 — 없으면 확장 안 됨).
- escaper: `:text`=cgi.escape, `:html`=SanitizeHtml, `:pprint`=디버그 덤프. **미지정은 무이스케이프**.
- `_ExpandValue` 의 `*name` 은 `specials['_params']` 에서 값을 읽어 **요청 파라미터로 필드명을
  지정**한다 → `{{_db.*uid.name}}` 는 `?uid=` 로 임의 사용자를 고른다(인증 검사 없음).
- `_ExpandInclude`: `fname = os.sep + filename.replace('/', os.sep)` →
  `_Open(RESOURCE_PATH, fname)` = `open('resources' + fname)`. **경로 정규화 없음** →
  `../secret.txt`, `../data.py`, `../../../../etc/passwd` 전부 읽힌다. 파일이 없으면
  include 블록 본문을 그대로 출력(오류 아님).
- **정적 서빙의 확장자 화이트리스트는 템플릿 include 를 전혀 막지 못한다** — 같은 파일이
  두 경로로 읽히는데 하나만 차단된다(대조군: `/%2e%2e%2fdata.py` → `Unrecognized file type`).
- specials 로 노출되는 것: `_cookie`(파싱된 쿠키), `_profile`(로그인 사용자 프로필), `_db`(전체 DB),
  `_params`, `_unique_id`. 템플릿 하나로 전부 덤프 가능.

## 인증 경계 실측 (Round 8, phase 2)
- `_DoSaveprofile` 의 `action=update` 는 **`pw` 파라미터가 있을 때만** `oldpw`/admin 검사를 한다.
  `pw` 를 주지 않으면 조건 `(newpw and ...)` 이 거짓이라 검사 자체가 실행되지 않고
  `database[uid].update(profile_data)` 로 직행한다 → **무인증 상태변경**.
- `uid = self._GetParameter(params, 'uid', cookie[COOKIE_UID])` — uid 는 **요청 파라미터 우선**,
  쿠키는 폴백일 뿐이다. 즉 쿠키 없이도 임의 계정을 지정할 수 있다.
- 무조건 프로필에 반영되는 필드: `name`, `pw`, `is_author`, `is_admin`, `private_snippet`,
  `icon`, `web_site`, `color` (전부 `_AddParameter`).
- 실측: 쿠키 없이 `/saveprofile?action=update&uid=brie&private_snippet=...` → 302 + 값 변경 확인.
- **CSRF 논의보다 "인증 부재" 를 먼저 확인할 것** — 쿠키가 불필요하면 SameSite Lax 여부는
  무관해진다.

## 쿠키 직렬화 / 서명 (Round 9 실측, phase 2)
- 발급: `_CreateCookie(cookie_name, uid)` → `c_data = '%s|%s|%s' % (uid, is_admin, is_author)`
  (**uid 를 검증 없이 이어붙임**) → `h_data = str(hash(cookie_secret + c_data) & 0x7FFFFFF)`
  → `Set-Cookie: GRUYERE=<h_data>|<c_data>; path=/<gid>`
- 검증/파싱: `_ParseCookie` → `cookie.split('|', 1)` 로 해시 분리 → 서명 재계산 비교 →
  `values = cookie_data.split('|')` → `uid=values[0]`, `is_admin = values[1]=='admin'`,
  `is_author = values[2]=='author'`.
- **uid 에 `|` 가 들어가면 서명은 그 uid 포함 전체 데이터로 정상 계산되므로 검증을 통과하면서
  필드가 추가된다** → 서버가 스스로 관리자 쿠키를 발급. 위조도 시크릿 지식도 불필요.
- 실측: `uid=r9poc|admin|author` 로 가입 → `GRUYERE=<sig>|r9poc|admin|author||` 발급 →
  서버 파싱 `{'is_admin': True, 'is_author': True, 'uid': u'r9poc'}` → 관리자 메뉴 렌더.
  같은 계정은 DB 상 `is_admin=None`(권한 없음) — **쿠키와 DB 의 권한 불일치**가 핵심.
- 재현용: `curl -s -D - "$B/saveprofile?action=new&uid=r9poc%7Cadmin%7Cauthor&pw=<8자>"` (가입 폼 하나)
- 쿠키 속성: HttpOnly/Secure/SameSite 전무(phase 1 확인) → XSS 탈취·Lax 논의와 결합 가능.

## XSS 방어선 실측 — sanitize.py (Round 10, phase 2)
- `gtl.py:217` 의 `:html` escaper 만 `sanitize.SanitizeHtml()` 을 호출한다(`:text` 는 cgi.escape,
  미지정은 무이스케이프). 사용 지점: `home.gtl:29`(private_snippet), `home.gtl:44`(snippets.0),
  `feed.gtl:24,27`.
- 살균 로직: 태그 단위로 잘라 태그명이 `allowed_tags`(`a,b,big,br,center,code,em,h1..h6,hr,i,img,
  li,ol,p,s,small,span,strong,table,td,tr,u,ul`)에 없으면 이름을 `blocked` 로 바꾸고,
  `disallowed_attributes` 목록을 `t.replace(a,'blocked')` 로 치환. `</` 로 시작하는 닫는 태그는 무검사.
- **실측 실패 모드 3종**:
  1. 목록 누락 — `onerror`(및 oninput/ontoggle/onanimationstart 등)가 `disallowed_attributes` 에 없음.
  2. 치환 대소문자 구분 — `OnLoad`/`OnClick` 등은 `t.replace('onload',...)` 에 걸리지 않음
     (HTML 속성명은 대소문자 무시 → 브라우저는 실행).
  3. 허용 태그의 URL 스킴 미검증 — `a` 허용인데 `href="javascript:..."` 를 막지 않음.
- 재현: `python3 -c "import sys;sys.path.insert(0,'src');import sanitize;print(sanitize.SanitizeHtml('<img src=x OnLoad=alert(1)>'))"`
- 결과: 살균기를 통과한 `OnLoad` 페이로드가 저장형으로 남아 **비인증 방문자** 브라우저에서 실행됨.
