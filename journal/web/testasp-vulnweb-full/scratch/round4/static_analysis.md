# testasp.vulnweb.com — 정적 자원 수집·분석 (round4)

- 대상: `http://testasp.vulnweb.com` (단일 호스트, 스코프 내)
- 수집일: 2026-09-23 (UTC)
- 근거: 아래 curl 로 **실제 내려받은 파일만** 근거로 작성. 추측/기억 기반 서술 없음.
- 원시 파일: `scratch/pages/` (HTML 원본 + 응답 헤더), `scratch/js/` (JS/CSS/기타 자원 + 헤더),
  `scratch/vti/` (FrontPage `_vti_cnf` 메타파일), 분석 스크립트는 `scratch/round4/`.

---

## 0. 사용한 정확한 curl 명령

### 0.1 요구된 12개 페이지 (전부 저장: 본문 + 전체 응답 헤더)
`scratch/round4/fetch_pages.sh` — 실제 실행한 스크립트(아래가 골격):

```bash
BASE="http://testasp.vulnweb.com"
OUT="journal/web/testasp-vulnweb-full/scratch/pages"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

curl -sS -m 40 -D "$OUT/<slug>.headers.txt" -o "$OUT/<slug>.body" -A "$UA" "$BASE<path>"
```

대응 표(그대로 실행한 12회):

| slug | path |
|---|---|
| root | `/` |
| Default.asp | `/Default.asp` |
| login.asp | `/login.asp` |
| register.asp | `/register.asp` |
| search.asp | `/search.asp` |
| db.asp | `/db.asp` |
| logInput.asp | `/logInput.asp` |
| showthread.asp | `/showthread.asp` |
| showforum.asp | `/showforum.asp` |
| logout.asp | `/logout.asp` |
| Templatize.asp | `/Templatize.asp` |
| robots.txt | `/robots.txt` |

### 0.2 파라미터가 있는 변형 페이지 (같은 형식으로 추가 수집)
```bash
curl -sS -m 40 -D pages/showthread.asp_id=1.headers.txt -o pages/showthread.asp_id=1.body -A "$UA" "http://testasp.vulnweb.com/showthread.asp?id=1"
curl -sS -m 40 -D pages/showforum.asp_id=0.headers.txt -o pages/showforum.asp_id=0.body -A "$UA" "http://testasp.vulnweb.com/showforum.asp?id=0"
curl -sS -m 40 -D pages/showforum.asp_id=1.headers.txt -o pages/showforum.asp_id=1.body -A "$UA" "http://testasp.vulnweb.com/showforum.asp?id=1"
curl -sS -m 40 -D pages/showforum.asp_id=2.headers.txt -o pages/showforum.asp_id=2.body -A "$UA" "http://testasp.vulnweb.com/showforum.asp?id=2"
curl -sS -m 40 -D pages/login.asp_RetURL=Default.headers.txt -o pages/login.asp_RetURL=Default.body -A "$UA" "http://testasp.vulnweb.com/login.asp?RetURL=%2FDefault%2Easp%3F"
curl -sS -m 40 -D pages/register.asp_RetURL=Default.headers.txt -o pages/register.asp_RetURL=Default.body -A "$UA" "http://testasp.vulnweb.com/register.asp?RetURL=%2FDefault%2Easp%3F"
curl -sS -m 40 -D pages/search.asp_tfSearch=admin.headers.txt -o pages/search.asp_tfSearch=admin.body -A "$UA" "http://testasp.vulnweb.com/search.asp?tfSearch=admin"
```

### 0.3 JS/CSS/기타 정적 자원
```bash
curl -sS -m 60 -D js/tiny_mce.js.headers.txt             -o js/tiny_mce.js             -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/tiny_mce.js"
curl -sS -m 60 -D js/tiny_mce_src.js.headers.txt         -o js/tiny_mce_src.js         -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/tiny_mce_src.js"
curl -sS -m 60 -D js/tiny_mce_popup.js.headers.txt       -o js/tiny_mce_popup.js       -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/tiny_mce_popup.js"
curl -sS -m 60 -D js/langs_en.js.headers.txt             -o js/langs_en.js             -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/langs/en.js"
curl -sS -m 60 -D js/themes_simple_editor_template.js.headers.txt     -o js/themes_simple_editor_template.js     -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/themes/simple/editor_template.js"
curl -sS -m 60 -D js/themes_simple_editor_template_src.js.headers.txt -o js/themes_simple_editor_template_src.js -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/themes/simple/editor_template_src.js"
curl -sS -m 60 -D js/themes_simple_editor_content.css.headers.txt     -o js/themes_simple_editor_content.css     -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/themes/simple/css/editor_content.css"
curl -sS -m 60 -D js/themes_simple_editor_ui.css.headers.txt          -o js/themes_simple_editor_ui.css          -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/themes/simple/css/editor_ui.css"
curl -sS -m 60 -D js/themes_simple_editor_popup.css.headers.txt       -o js/themes_simple_editor_popup.css       -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/themes/simple/css/editor_popup.css"
curl -sS -m 60 -D js/license.txt.headers.txt             -o js/license.txt             -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/license.txt"
curl -sS -m 60 -D js/styles.css.headers.txt              -o js/styles.css              -A "$UA" "http://testasp.vulnweb.com/styles.css"
curl -sS -m 60 -D js/MainTemplate.dwt.asp.headers.txt    -o js/MainTemplate.dwt.asp    -A "$UA" "http://testasp.vulnweb.com/Templates/MainTemplate.dwt.asp"
curl -sS -m 60 -D js/_vti_cnf_Default.asp.headers.txt    -o js/_vti_cnf_Default.asp    -A "$UA" "http://testasp.vulnweb.com/_vti_cnf/Default.asp"
curl -sS -m 60 -D js/avatars_noavatar.gif.headers.txt    -o js/avatars_noavatar.gif    -A "$UA" "http://testasp.vulnweb.com/avatars/noavatar.gif"
curl -sS -m 60 -D js/Templatize.asp_item=html_about.html.headers.txt -o 'js/Templatize.asp_item=html_about.html' -A "$UA" "http://testasp.vulnweb.com/Templatize.asp?item=html/about.html"
# 소스맵 후보(.map) — 존재 확인용
curl -sS -m 60 -D js/tiny_mce.js.map.headers.txt         -o js/tiny_mce.js.map         -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/tiny_mce.js.map"
curl -sS -m 60 -D js/tiny_mce_src.js.map.headers.txt     -o js/tiny_mce_src.js.map     -A "$UA" "http://testasp.vulnweb.com/jscripts/tiny_mce/tiny_mce_src.js.map"
curl -sS -m 60 -D js/styles.css.map.headers.txt          -o js/styles.css.map          -A "$UA" "http://testasp.vulnweb.com/styles.css.map"
```

### 0.4 `_vti_cnf` (FrontPage 메타) 수집
```bash
for f in DB.asp Default.asp Login.asp Search.asp db.asp default.asp login.asp logout.asp \
         register.asp search.asp showthread.asp styles.css Templatize.asp showforum.asp logInput.asp; do
  curl -sS -m 30 -A "$UA" -o "vti/$f" -w "%{http_code} %{size_download}  $f\n" \
       "http://testasp.vulnweb.com/_vti_cnf/$f"
done
```

### 0.5 탐색 보조 (구조 확인용, ffuf)
```bash
ffuf -u http://testasp.vulnweb.com/_vti_cnf/FUZZ -w wordlists/common.txt \
     -e .asp,.html,.css,.js,.gif,.txt -mc 200,201,204,301,302,307,400,401,403,500 -t 60 -s -of json -o round4/vti_cnf.json
ffuf -u http://testasp.vulnweb.com/jscripts/FUZZ -w wordlists/quickhits.txt -e .js,.asp,.php,.txt,.css,.inc,.config ... -o round4/jscripts.json
ffuf -u http://testasp.vulnweb.com/jscripts/tiny_mce/FUZZ -w wordlists/quickhits.txt -e .js,.php,.txt,.html,.css ... -o round4/tiny_mce.json
```
직접 경로 확인은 `scratch/round4/probe_paths.py`, `path_probe2.json` (실제 상태코드 기록).

---

## 1. 수집 결과 요약 (실측)

| 요청 | 상태 | Content-Type | 바이트 | 비고 |
|---|---|---|---|---|
| `/` | 200 | text/html | 3538 | `Default.asp`와 **바이트 동일**(diff IDENTICAL) |
| `/Default.asp` | 200 | text/html | 3538 | 포럼 목록 |
| `/login.asp` | 200 | text/html | 3194 | 로그인 폼 |
| `/register.asp` | 200 | text/html | 3617 | 가입 폼 |
| `/search.asp` | 200 | text/html | 2809 | 검색 폼(GET) |
| `/db.asp` | 200 | text/html | **0** | 본문 없음(include 성격) — `_vti_cnf`상 원본 크기 284 |
| `/logInput.asp` | 200 | text/html | **0** | 본문 없음, `_vti_cnf`에 항목 없음(404) |
| `/showthread.asp` | 302 | text/html | 132 | `Location: Default.asp` (id 파라미터 없음) |
| `/showforum.asp` | 302 | text/html | 132 | `Location: Default.asp` |
| `/logout.asp` | 302 | text/html | 132 | `Location: Default.asp` |
| `/Templatize.asp` | **500** | text/html | 1208 | IIS "500 - Internal server error" (item 파라미터 없음) |
| `/robots.txt` | 200 | text/plain | 13 | 내용 `User-agent: *` 만 |
| `/showthread.asp?id=1` | 200 | text/html | 3031 | 스레드 렌더 |
| `/showforum.asp?id=0` | 200 | text/html | 3969 | 게시판 렌더 |
| `/showforum.asp?id=1` | 200 | text/html | 3077 | "Weather" |
| `/showforum.asp?id=2` | 200 | text/html | 2933 | "Miscellaneous" |
| `/Templatize.asp?item=html/about.html` | 200 | text/html | 4594 | **임의 item 렌더(DreamWeaver 템플릿)** |
| `/search.asp?tfSearch=admin` | **500** | text/html | 1208 | 검색어 비어있지 않으면 500 |

공통 응답 헤더(모든 HTML): `Server: Microsoft-IIS/8.5`, `X-Powered-By: ASP.NET`,
`Cache-Control: private`, `Set-Cookie: ASPSESSIONIDAABTRDTB=<...>; path=/`.
**X-Frame-Options / CSP / X-Content-Type-Options / HSTS / Referrer-Policy 없음**(헤더에 부재 확인).
`styles.css`, `tiny_mce*.js` 등 정적 파일은 `Accept-Ranges`, `ETag`, `Last-Modified` 포함
(tiny_mce.js: `Last-Modified: Thu, 29 May 2008 12:11:36 GMT`, ETag `"7edd7d2485c1c81:0"`).

---

## 2. 폼 · 필드 · 파라미터

### 2.1 폼과 입력 필드 (hidden 필드는 **전 페이지에서 0개**)

| 페이지 | form | method | action | form name | 필드(name / type / value) |
|---|---|---|---|---|---|
| login.asp | 1 | **POST** | `""`(빈값=자기 자신) | (없음) | `tfUName` text, `tfUPass` password, submit(`value=Login`, name 없음) |
| register.asp | 1 | **post** | `""` | `frmRegister` (`enctype="application/x-www-form-urlencoded"`) | `tfUName` text, `tfRName` text, `tfEmail` text, `tfUPass` password, submit(`value=Register me`) |
| search.asp | 1 | **get** | `""` | `frmSearch` | `tfSearch` text, submit(`value=search posts`) |
| Default.asp / root | 0 | — | — | — | — |
| showforum.asp / showthread.asp / logout / db / logInput / Templatize / robots.txt | 0 | — | — | — | — |

- `<input type="hidden">` : **수집한 모든 페이지에서 0건.** (예: login.asp는 `RetURL`을 hidden으로
  넣지 않음 → `RetURL`은 메뉴 링크 생성에만 반영됨, 아래 2.3의 diff로 확인)
- `<textarea>`/`<select>` : 수집된 비로그인 뷰에는 없음. 단 `styles.css`에 `TEXTAREA.postit`,
  `INPUT.postit`, `.userinfo`, `.post`, `.posttitle`, `.path` 클래스가 정의돼 있고
  `_vti_cnf/showthread.asp`·`_vti_cnf/showforum.asp`의 `vti_cachedlinkinfo`에
  `S|./jscripts/tiny_mce/tiny_mce.js`가 기록돼 있음 → **로그인 후 게시/댓글 폼에서
  TinyMCE textarea가 쓰인다는 정적 증거**(비로그인 GET으로는 본문 미노출).

### 2.2 링크(href)와 쿼리 파라미터

| 링크 대상 | 파라미터 | 등장 페이지 |
|---|---|---|
| `Templatize.asp?item=html/about.html` | **item** | 전 페이지 메뉴바 |
| `Default.asp` | — | 전 페이지 |
| `Search.asp` | — | 전 페이지 |
| `Login.asp?RetURL=%2F<현재경로>%3F` | **RetURL** | 전 페이지 (현재 URL을 URL-encode해 반영) |
| `Register.asp?RetURL=%2F<현재경로>%3F` | **RetURL** | 전 페이지 |
| `showforum.asp?id=0/1/2` | **id** | Default.asp/root |
| `showthread.asp?id=0..5` | **id** | showforum.asp?* |
| `showforum.asp?id=0` | **id** | showthread.asp?id=1 (breadcrumb) |
| `avatars/noavatar.gif` (img) | — | showthread.asp?id=1 |
| `Images/logo.gif` (img) | — | 전 페이지 |
| `styles.css` (link) | — | 전 페이지 |
| 외부: `https://www.acunetix.com/`, `/vulnerability-scanner/`, `/vulnerability-scanner/sql-injection/`, `/websitesecurity/sql-injection/` | — | 전 페이지 |

파라미터명 전체 목록(수집 범위 내): `item`, `RetURL`, `id`, `tfSearch` (+ POST 필드 `tfUName`,`tfRName`,`tfEmail`,`tfUPass`).

### 2.3 `RetURL` 반영 확인 (실제 diff)
`login.asp` vs `login.asp?RetURL=%2FDefault%2Easp%3F` → **차이는 1개 hunk뿐**:
```diff
- <a href="./Login.asp?RetURL=%2Flogin%2Easp%3F">login</a> - <a href="./Register.asp?RetURL=%2Flogin%2Easp%3F">register</a>
+ <a href="./Login.asp?RetURL=%2FDefault%2Easp%3F">login</a> - <a href="./Register.asp?RetURL=%2FDefault%2Easp%3F">register</a>
```
폼 태그는 양쪽 모두 `<form action="" method="POST">`로 동일 → hidden 필드 없음.
(`register.asp`도 동일 패턴, `<form action="" method="post" ... name="frmRegister">`)

### 2.4 파라미터 유무에 따른 실측 동작 (SQL 오류 노출 신호)
| 요청 | 결과 |
|---|---|
| `/search.asp` | 200 (2809b) |
| `/search.asp?tfSearch=` | 200 (2831b) |
| `/search.asp?tfSearch=a` / `=1` / `=test` | **500** (1208b) |
| `/search.asp?foo=1` | 200 (2823b, 파라미터 무시) |
| `/showthread.asp?id=x` | **500** |
| `/showforum.asp?id=x` | **500** |
| `/Templatize.asp?item=x` | **500** |
| `/Templatize.asp?item=../db.asp` | **500** |
| `/Templatize.asp?item=html/about.html` | 200 (4594b) |
| `/db.asp`, `/db.asp?id=1`, `/logInput.asp?x=1` | 200, **0바이트** |

---

## 3. HTML 주석 → 템플릿·내부 파일명

수집한 모든 HTML에서 동일하게 나타나는 DreamWeaver 템플릿 주석(원문 그대로):

```
<!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" codeOutsideHTMLIsLocked="false" -->
<!-- InstanceBeginEditable name="doctitle" --> ... <!-- InstanceEndEditable -->
<!-- InstanceBeginEditable name="head" -->     ... <!-- InstanceEndEditable -->
<!-- InstanceBeginEditable name="MainContentLeft" --> ... <!-- InstanceEndEditable -->
<!-- InstanceEnd -->
```

- 템플릿 파일명: **`/Templates/MainTemplate.dwt.asp`** (실제로 GET 200 / 2488 bytes로 내려받음).
- 해당 `.dwt.asp` 내부 주석은 `<!-- TemplateBeginEditable ... -->` /
  `<!-- TemplateEndEditable -->` (인스턴스 주석과 대칭) — 파일 자체가
  `../styles.css`, `../Images/logo.gif`, `../Templatize.asp`, `../Default.asp`, `../Search.asp`를 참조.
- `_vti_cnf/*.asp` (FrontPage 메타, 200으로 노출) 에서 드러난 내부 사실:
  - **가상 디렉터리/앱 이름: `acuforum`** — `vti_cachedsvcrellinks` 값이 전부 `acuforum/...` 형태
    (예: `FQUS|acuforum/styles.css`, `FSUS|acuforum/jscripts/tiny_mce/tiny_mce.js`).
  - `showthread.asp`/`showforum.asp`의 `vti_cachedlinkinfo`에 `S|./jscripts/tiny_mce/tiny_mce.js`.
  - `vti_backlinkinfo`로 확인된 상호링크 집합:
    `acuforum/login.asp, register.asp, search.asp, default.asp, showthread.asp, showforum.asp, templatize.asp`.
  - `vti_extenderversion:SR|4.0.2.8912`, `vti_timelastmodified:TR|05 Oct 2007 10:01:19 -0000`.
  - 원본 파일 크기(서버 캐시 값): `default.asp 3663`, `login.asp 3681`, `register.asp 3888`,
    `search.asp 4303`, `showforum.asp 6897`, `showthread.asp 6250`, `templatize.asp 2510`,
    `db.asp 284`, `logout.asp 225`, `styles.css 3390`.
  - `_vti_cnf/logInput.asp` → 404 (해당 파일은 FrontPage 추적 대상이 아님).
- 그 밖의 HTML 주석: IIS 오류 페이지 내부의 인라인 CSS를 감싼 `<!-- ... -->` (403/404/500 페이지, 정보성 아님).
- 메타태그: 전 페이지 동일 — `<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">`.
  `<meta name="generator">`, 프레임워크 흔적 없음. `<title>`은 `acuforum ...` 패턴.
- 저작권/연도: 푸터 `Copyright 2019 Acunetix Ltd.` (전 페이지), `robots.txt` Last-Modified 2019-05-06.
  **개발자 이메일/주석 내 자격증명은 수집 페이지에서 0건**(정규식 스캔 결과 없음).
- 인라인 `<script>`: **수집한 모든 페이지에서 0개.** 외부 스크립트 참조도 비로그인 뷰에서는 0개
  (유일한 CSS 참조 `styles.css`, 이미지 `Images/logo.gif`).

---

## 4. JavaScript 정적 분석

### 4.1 대상 파일 (실측 크기/헤더)
| 파일 | 바이트 | Content-Type | Last-Modified |
|---|---|---|---|
| `/jscripts/tiny_mce/tiny_mce.js` | 132342 (11줄, minify/난독) | application/javascript | Thu, 29 May 2008 12:11:36 GMT |
| `/jscripts/tiny_mce/tiny_mce_src.js` | 180379 (5817줄, **비압축 원본**) | application/javascript | Thu, 29 May 2008 12:11:37 GMT |
| `/jscripts/tiny_mce/tiny_mce_popup.js` | 6835 (244줄) | application/javascript | — |
| `/jscripts/tiny_mce/themes/simple/editor_template.js` | 5727 | application/javascript | Thu, 29 May 2008 12:11:44 GMT |
| `/jscripts/tiny_mce/themes/simple/editor_template_src.js` | 6010 (71줄) | application/javascript | — |
| `/jscripts/tiny_mce/langs/en.js` | 1650 | application/javascript | — |
| `/jscripts/tiny_mce/themes/simple/css/editor_content.css` / `editor_ui.css` / `editor_popup.css` | 616 / 1912 / 821 | text/css | — |
| `/jscripts/tiny_mce/license.txt` | 23672 | text/plain | — (GNU LGPL v2, June 1991) |
| `/styles.css` | 3390 (190줄) | text/css | Thu, 29 May 2008 12:11:27 GMT |

### 4.2 (a) 버전 문자열 — 실제 파일 내용
`tiny_mce.js` L1 배너(원문):
```
/** $RCSfile: tiny_mce.js,v $  $Revision: 1.301 $  $Date: 2005/10/30 16:06:56 $
 *  @author Moxiecode   @copyright Copyright © 2004, Moxiecode Systems AB, All rights reserved. */
function TinyMCE(){this.majorVersion="2";this.minorVersion="0RC4";this.releaseDate="2005-10-30"; ...
```
`tiny_mce_src.js` L1 배너: `$RCSfile: tiny_mce_src.js,v $ $Revision: 1.249 $ $Date: 2005/10/30 16:06:57 $`,
`this.majorVersion = "2"; this.minorVersion = "0RC4"; this.releaseDate = "2005-10-30";`
→ **TinyMCE 2.0RC4 (2005-10-30, Moxiecode Systems AB)**, 2008-05-29에 서버에 배치된 사본.
`tiny_mce_popup.js`: `$Revision: 1.18 $ $Date: 2005/10/29 19:13:20 $`.
**비압축 원본 `tiny_mce_src.js`가 함께 배포되어 있어 전체 소스가 그대로 노출됨.**

### 4.3 (b) 하드코딩된 URL / 경로 / 플러그인 목록
- 하드코딩 URL(양 파일 동일, 3건):
  - `http://tinymce.moxiecode.cp/mce_temp_url` (L179, `this.uniqueURL` — 오타 도메인 `.cp`가 그대로 남음)
  - `http://www.mozilla.org/editor/midasdemo/securityprefs.html`
  - `http://www.w3.org/1999/xhtml`
- 런타임에 조립되는 경로 템플릿(문자열 리터럴 확인):
  - `/themes/` , `/plugins/` , `/langs/` , `/css/editor_content.css`, `/css/editor_popup.css`,
    `/css/editor_ui.css`, `/images/opacity.png`
  - 실제 조립식(원문):
    - `tinyMCE.baseURL + '/themes/' + theme + '/editor_template' + tinyMCE.srcMode + '.js'` (L254)
    - `tinyMCE.baseURL + '/langs/' + this.settings['language'] + '.js'` (L255)
    - `tinyMCE.baseURL + '/plugins/' + themePlugins[i] + '/editor_plugin' + tinyMCE.srcMode + '.js'` (L262)
    - `.../themes/<theme>/css/editor_content.css|editor_popup.css|editor_ui.css` (L207,218,674)
    - `.../themes/<name>/langs/<lang>.js` (L3092), `.../plugins/<name>/langs/<lang>.js` (L3104)
    - `.../themes/<theme>/images/opacity.png` (L1257)
  - `baseURL`/`srcMode` 결정 로직(L63-80): `document.getElementsByTagName('script')`를 훑어
    `src`에 `tiny_mce.js`/`tiny_mce_src.js`/`tiny_mce_gzip.php`가 들어있는 스크립트를 찾아
    디렉터리를 baseURL로, URL에 `_src`가 있으면 `srcMode='_src'`.
- **플러그인 목록은 하드코딩되어 있지 않음** — 기본값 `plugins = ""`(L94),
  `theme = "advanced"`(L93, 기본값), `language = "en"`(L95), `mode = "none"`(L92). 즉 배포된 플러그인 목록은
  JS에서 알 수 없고, 서버에는 실제로 `plugins/` 하위가 존재하지 않음(아래 4.6).
- 서버에 실제 존재하는 테마는 `simple`(editor_template.js 200) — `advanced`/`default`는 404.

### 4.4 (c) 위험 API 사용 위치·개수
| API | tiny_mce.js | tiny_mce_src.js | tiny_mce_popup.js |
|---|---|---|---|
| `document.write(` | 3 (L9) | 3 (L276, L287, L3172) | 1 (L61) |
| `.innerHTML` | 53 | 63 (L336 … L3485+) | 5 (L53,54,57,70) |
| `.outerHTML` | 11 | 11 | 0 |
| `eval(` | 47 | 47 (L386,591,756,1573,1581,1687,1768,2452,2478,2491,2532,3054,3060,3202,3342,3693,3777,3794 …) | 4 (L86,94,234,237) |
| `new Function(` | 0 | 0 | 0 |
| `setTimeout('...')` (문자열 인자) | 9 | 9 (L664,669,890,1132,1199,5056,5064,5554,5770) | 0 |
| `document.cookie` | 0 | 0 | 0 |
| `XMLHttpRequest` | 0 | 0 | 0 |
| `ActiveXObject` | 0 | 0 | 0 |
| `createElement('script')` | 0 | 0 | 0 |
| `execCommand(` | 68 | 68 | 5 |

대표 코드(원문 그대로):
```
[tiny_mce_src.js:276]  document.write('<sc'+'ript language="javascript" type="text/javascript" src="' + url + '"></script>');
[tiny_mce_src.js:287]  document.write('<link href="' + url + '" rel="stylesheet" type="text/css" />');
[tiny_mce_src.js:3172] win.document.write(html);
[tiny_mce_popup.js:61] document.write('<link href="' + tinyMCE.getParam("popups_css") + '" rel="stylesheet" type="text/css">');
[tiny_mce_src.js:386]  var content = eval(tinyMCE.settings['save_callback'] + "(inst.formTargetElementId,htm,inst.getBody());");
[tiny_mce_src.js:1768] attribValue = eval(tinyMCE.cleanup_urlconverter_callback + "(attribValue, element_node, tinyMCE.cleanup_on_save);");
[tiny_mce_src.js:2452] href = eval(tinyMCE.settings['urlconverter_callback'] + "(href, linkElement);");
[tiny_mce_src.js:3060] if (eval("typeof(TinyMCE_" + plugins[i] + "_cleanup)") != "undefined")
[tiny_mce_src.js:1573] eval('elm.style.' + style + ' = val;');   // 1581,1620,1687,3342 도 동일 계열
```
정리: 위험 API는 대부분 (i) `<script>`/`<link>` 동적 삽입(`document.write`),
(ii) 설정값으로 전달된 **콜백 함수 이름을 `eval`로 실행**(`save_callback`,
`urlconverter_callback`, `cleanup_urlconverter_callback`, 플러그인 `TinyMCE_<plugin>_cleanup`),
(iii) 엘리먼트/스타일 속성 이름 문자열을 `eval`로 접근하는 데 쓰임.
`document.write`는 로드 시점에만 실행되며 DOM 삽입 위치는 스크립트 태그 위치 기준.

### 4.5 (d) 서버로 보내는 요청 경로
- **AJAX/폼 전송/XHR 없음** (위 표의 `XMLHttpRequest`=0, `document.cookie`=0).
- JS가 서버에서 **추가로 가져오는(로드하는) 경로**는 위 4.3의 `baseURL + ...` 조립식 전부이며,
  그 외 서버 측 스크립트 참조는 1건: **`tiny_mce_gzip.php`** (`tiny_mce_src.js:66`의
  script-tag 판별 문자열). 해당 파일은 서버에 없음(404) — 실제 배포는 개별 `.js` 로더 방식.

### 4.6 (e) 사이트 자체 .js 보유 여부 / `/jscripts/` 구조 (실측 상태코드)
- 사이트가 직접 만든 JS는 **발견되지 않음**: `/main.js`, `/forum.js`, `/functions.js`, `/scripts.js`,
  `/jscripts/main.js`, `/jscripts/forum.js`, `/jscripts/functions.js`, `/jscripts/scripts.js`,
  `/jscripts/global.js`, `/jscripts/common.js`, `/scripts/forum.js`, `/js/forum.js` → 전부 **404**.
  수집한 HTML 12종에도 자체 `<script src>`가 없음(4.2절과 2.1절 참고).
- 디렉터리 목록은 비활성(`/jscripts/` → 403, `/jscripts/tiny_mce/` → 403, `/Templates/` → 403,
  `/Images/` → 403, `/avatars/` → 403, `/html/` → 403). 개별 파일 직접 접근은 가능.
- `/jscripts/` 하위에서 확인된 것(전부 200으로 실파일 수신):
  `tiny_mce/tiny_mce.js`, `tiny_mce/tiny_mce_src.js`, `tiny_mce/tiny_mce_popup.js`,
  `tiny_mce/langs/en.js`, `tiny_mce/license.txt`, `tiny_mce/LICENSE.txt`,
  `tiny_mce/themes/simple/editor_template.js`, `…/editor_template_src.js`,
  `…/themes/simple/css/{editor_content,editor_ui,editor_popup}.css`, `…/themes/simple/images/{bold,spacer}.gif`.
- 404로 확인된 후보: `tiny_mce_gzip.php`, `tiny_mce_gzip.js`, `tiny_mce_dev.js`, `readme.txt`,
  `changelog.txt`, `index.php`, `docs/`, `examples/`, `themes/advanced/*`, `themes/default/*`,
  `plugins/table|contextmenu|flash|emotions|fullscreen|insertdatetime|advlink|advimage|advhr|paste|_template/*`,
  `langs/en_dlg.js`, `langs/kr.js` → **deployed copy는 소스+simple 테마+en 언어팩 최소 구성**.
- `/jscripts/Trace.axd` 403 (ASP.NET 추적 핸들러 경로 존재, 비활성), `/jscripts/tiny_mce/Trace.axd` 403.

---

## 5. 소스맵(.map) 및 기타 노출 여부

| 경로 | 상태 | 해석 |
|---|---|---|
| `/jscripts/tiny_mce/tiny_mce.js.map` | **404** | 소스맵 없음 |
| `/jscripts/tiny_mce/tiny_mce_src.js.map` | **404** | 소스맵 없음 |
| `/styles.css.map` | **404** | 소스맵 없음 |
| `/jscripts/tiny_mce/tiny_mce_popup.js.map` | **404** | 소스맵 없음 |
| `/jscripts/tiny_mce/themes/simple/editor_template.js.map` | **404** | 소스맵 없음 |
| `/jscripts/tiny_mce/themes/simple/css/editor_content.css.map` / `editor_ui.css.map` | **404** | 소스맵 없음 |
| `/jscripts/tiny_mce/langs/en.js.map` | **404** | 소스맵 없음 |

→ **소스맵 파일은 존재하지 않음**(모두 IIS 404 1245바이트 오류 페이지). 다만 minify 버전과
동등한 비압축 원본(`tiny_mce_src.js`)이 그대로 서비스되므로 소스 노출 측면의 이득은 동일.

기타 노출(모두 실제 응답으로 확인):
- **`/Templates/MainTemplate.dwt.asp` → 200 (2488b)**: DreamWeaver 템플릿 원본 서비스.
- **`/_vti_cnf/<파일>` → 200**: FrontPage 메타데이터가 통째로 노출 (Default/Search 926b,
  showthread 882b, showforum 861b, register 778b, Login 772b, Templatize 930b, styles.css 404b,
  db/DB/logout 338b). 내부 앱 경로명 `acuforum`, 원본 파일 크기, 백링크 그래프, 수정시각(2007-10-05) 포함.
- `_vti_cnf/logInput.asp` → 404 (해당 파일 미추적).
- 노출 없음(404): `/.git/config`, `/.svn/entries`, `/web.config`, `/Global.asax`, `/bin/`,
  `/App_Data/`, `/_vti_inf.html`, `/_vti_bin/`, `/_vti_pvt/`, `/MSOffice/`, `/_layouts/`,
  `/env`성 파일, `/admin.asp`, `/post.asp`, `/reply.asp`, `/showpost.asp`, `/profile.asp`, `/dsn.asp`.
- `Trace.axd` → **403** (핸들러는 존재하나 원격 비활성), `/elmah.axd` → 404 (404 본문 1504b로 다른 크기 — 별도 처리).
- 디렉터리 리스팅 없음(403), `robots.txt`는 `User-agent: *` 한 줄만이라 추가 경로 힌트 없음.
- 인증 없이 접근 가능한 미디어/정적: `Images/logo.gif`(200 image/gif), `avatars/noavatar.gif`(200 image/gif),
  `html/about.html`(200 text/html, 로컬 html 디렉터리 실파일), `styles.css`(200 text/css).

---

## 6. 부록: 산출물 파일 목록

- `scratch/pages/` — 12개 요구 페이지 + 8개 파라미터 변형 (`<slug>.body`, `<slug>.headers.txt`) 및
  디렉터리 접근 결과 헤더(`dl_*.headers.txt`). *(이전 라운드의 `body_*.html`/`hdr_*.txt` 파일도 동일 디렉터리에 잔존)*
- `scratch/js/` — JS/CSS/템플릿/라이선스/이미지 원본 + 각 `.headers.txt`, `.map` 404 응답 본문
- `scratch/vti/` — `_vti_cnf` 메타파일 16종
- `scratch/round4/`
  - `fetch_pages.sh` (수집 스크립트), `probe_paths.py` / `probe_path2.json`,
    `analyze_js.py` / `js_analysis.json`, `analyze_js_all.py` / `js_analysis_all.json`,
    `extract_pages.py` / `page_extract.json`,
    `vti_cnf.json`, `jscripts.json`, `tiny_mce.json`, `plugins.json`, `path_probe.json`,
  - 본 문서 `static_analysis.md`
