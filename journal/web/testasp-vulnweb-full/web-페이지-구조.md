# 페이지 구조 — testasp-vuln-full

타겟: `http://testasp.vulnweb.com` (Acunetix 공개 테스트 사이트, IIS 8.5)
최초 작성: 2026-09-23 (Round 1, ffuf/gobuster 디렉터리·파일 탐색)

## 사이트 정체
- 사이트 자체 이름은 "acuforum" (Default.asp 의 title, _vti_cnf 메타데이터의 vti_title 둘 다
  `acuforum forums`). 포럼 형태의 게시판 앱.
- 문서상 물리/가상 경로는 `acuforum/` (IIS 가상 디렉터리).

## 공개 영역 (인증 없이 200 확인)
- `/` → `Default.asp` (200, 3540B) — 랜딩(포럼 메인). `/.` 도 동일 200.
- `/login.asp` (200, 3194B) — 로그인 폼. `method="POST"`, 필드 `tfUName`, `tfUPass`
- `/register.asp` (200, 3617B) — 회원가입 폼
- `/search.asp` (200, 2809B) — 검색 폼. `method="get"`, 필드 `tfSearch`, form name `frmSearch`
- `/robots.txt` (200, 13B) — 내용은 `User-agent: *` 한 줄뿐, Disallow 없음
- `/db.asp` (200, **0바이트**) — 파라미터 없이 호출 시 빈 응답
- `/logInput.asp` (200, **0바이트**) — 파라미터 없이 호출 시 빈 응답
- `/Templatize.asp` (파라미터 없이 500) — **`?item=<상대경로>` 로 정상 동작한다. 임의 파일 읽기.
  아래 Round 5 절 참조. (Round 4 이전 기록의 "항상 500, 익스플로잇 표면 아님" 은 오류 — Round 5 에서 정정)
- `/shownews.asp` (파라미터 없이 500) — **`?item=<상대경로>` 로 파일을 읽는 두 번째 프리미티브.
  Round 5 신규. 아래 참조.

## 인증 필요 / 세션 의존 영역 (302 → Default.asp)
세션 없이 호출하면 `Location: Default.asp` 로 되돌림:
- `/logout.asp` (302, 132B)
- `/showforum.asp` (302, 132B)
- `/showthread.asp` (302, 132B)

→ showforum.asp / showthread.asp 는 게시판의 실제 기능 페이지이며, 로그인 후 접근 가능할
가능성이 높음(다음 phase에서 테스트 계정 필요).

## 디렉터리 계층
- `/images/` — 301 → 403 (리스팅 차단)
- `/Images/`, `/IMAGES/` — 동일(IIS 대소문자 비구분)
- `/html/`, `/avatars/`, `/templates/`, `/T/`, `/cgi-bin/`, `/aspnet_client/`, `/jscripts/`
  — 모두 슬래시 없이 301 → 슬래시 붙이면 403 (리스팅 차단)
- `/jscripts/tiny_mce/` — 403 (TinyMCE 배포 디렉터리, 아래 참조)
- `/_vti_cnf/` — **301 이 아니라 200** (FrontPage 메타데이터 노출, 아래 "Hidden" 참조)

## Hidden / 발견된 페이지 (2026-09-23 추가)
- `/_vti_cnf/<원본파일명>` — FrontPage 확장 메타데이터가 200 으로 서빙됨.
  확인된 것: `_vti_cnf/Default.asp`(926B), `_vti_cnf/Login.asp`(772B),
  `_vti_cnf/DB.asp`(338B), `_vti_cnf/search.asp`(926B). **파일 존재 오라클**로 사용 가능
  (200=존재, 404=미존재). vti_backlinkinfo 가 `login.asp register.asp search.asp
  default.asp showthread.asp showforum.asp templatize.asp` 를 나열 → 페이지 목록 유출.
- `/cgi-bin/test.txt` (200, 3B, 본문 `aaa`, Last-Modified 2008-07-14) — 잔여 테스트 파일
- `/jscripts/tiny_mce/tiny_mce.js` (200, 132KB), `/jscripts/tiny_mce/tiny_mce_src.js`
  (200, 180KB, 비압축 소스), `/jscripts/tiny_mce/license.txt` (200, 23KB)
  → TinyMCE 2.0RC4 (2005-10-30), majorVersion=2/minorVersion=0RC4
- `/Trace.axd` (403, ASP.NET `Trace Error` 페이지 2062B) — 추적 기능 설정됨, localOnly 로
  원격 차단. 애플리케이션 핸들러가 임의 경로의 Trace.axd 를 잡으므로 "디렉터리별 파일" 아님.

## 부재 확인 (404)
`/admin.asp`, `/admin/`, `/upload.asp`, `/guestbook.asp`, `/bin/`, `/App_Data/`,
`/web.config`, `/global.asa`, `/iisstart.htm`, `/_vti_bin/`, `/_vti_inf.html`,
`/_vti_pvt/`, `/Default.asp.bak`, `/elmah.axd`, `/Templatize.asp?name=...`

## Round 4 추가 (2026-09-23 07:20Z)

### 브라우저로 직접 렌더링해 확인한 실제 화면 (CDP 캡처, 증거: `scratch/pages/shot_*.png`)
| URL | 문서 title | PNG |
|---|---|---|
| `/Default.asp` | `acuforum forums` | shot_Default.png (66,692B) |
| `/login.asp` | `acuforum login` | shot_login.png (47,649B) |
| `/register.asp` | `acuforum register` | shot_register.png (50,171B) |
| `/search.asp?tfSearch=test` | `500 - Internal server error.` | shot_search.png (16,801B) |

→ 페이지 title 이 각각 `acuforum <기능명>` 형태라 **사이트 이름이 acuforum 이고 페이지가
기능별로 명확히 나뉜다**는 기존 추론이 GUI 로도 확인됐다(HTML 파싱만이 아니라 실제 렌더 결과).

### 동적 입력 지점의 응답 분기 (다음 라운드 exploit 1순위)
`/search.asp?tfSearch=` 는 검색어 종류에 따라 응답이 갈린다:
- 값 없음 → 200 / 2809B (검색 폼)
- `test`, `1`, `a`, `test post` → **500 / 1208B** (IIS 기본 500, 정보 누출 없음)
- `%27` (작은따옴표 단독) → **200 / 2963B** (본문이 154B 증가)

`search.asp` 는 인증 없이 접근 가능한 **유일한 동적 입력 지점**이다. 게시판(`showforum.asp`,
`showthread.asp`)은 세션 없이 302 이므로, 테스트 계정 없이 검증 가능한 공격 표면은 현재
`search.asp` 와 `login.asp`/`register.asp` POST 뿐이다.

### 폼 구조 확정 (hidden 필드 전무 — CSRF 토큰 없음)
- `POST /login.asp` (action="" = 자기 자신) — `tfUName`(text, id=tfUName), `tfUPass`(password, id=tfUPass)
- `POST /register.asp` name=`frmRegister` enctype=`application/x-www-form-urlencoded`
  — `tfUName`, `tfRName`, `tfEmail`, `tfUPass`
- `GET /search.asp` name=`frmSearch` — `tfSearch`

hidden 필드가 하나도 없다 → **안티-CSRF 토큰 부재**가 폼 레벨에서 확정(상태변경 POST 에
CSRF 보호가 없다는 뜻이며, 인증 후 기능에서 별도 확인 가치가 있다).

### 미확인(다음 라운드)
- `Templates/MainTemplate.dwt.asp` — DreamWeaver 템플릿 파일. HTML 주석
  `<!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" ... -->` 로 존재가 강하게
  추정되나 직접 요청해 본 적 없음.
- `styles.css` — 페이지가 참조하는 스타일시트(루트 기준 상대경로).

## Round 5 추가 (2026-09-23 08:35Z) — exploit 라운드에서 확정된 페이지/파라미터

### 파일 읽기 전용 페이지 2개 (둘 다 인증 불요, `item` 파라미터)
| 페이지 | 파라미터 없음 | `?item=html/about.html` | 인코딩 | 비고 |
|---|---|---|---|---|
| `/Templatize.asp` | 500 (1208B) | 200 4594B | **없음(원문)** | `Response.Write(oFile.ReadAll)` |
| `/shownews.asp` | 500 (1208B) | 200 2161B | **HTML 인코딩** | `Response.Write Server.HTMLEncode(oFile.ReadAll)` |

`shownews.asp` 는 이전 라운드에 "500 만 나오는 존재 오라클"로 기록됐으나 실제로는 `item`
파라미터를 받는 **파일 리더**다(파라미터명이 `item` 이 아니면 전부 500 — `id`/`newsid`/
`fname`/`file`/`n`/`note` 시도 결과 500). 두 페이지 모두 `Server.MapPath(".") & "\" & item`
으로 경로를 조립하며 **어떤 필터도 없다** — `..` 개수가 실제 깊이와 맞으면 상위 어디든 읽힌다
(깊이 3 = 웹루트에서 C:\ 도달).

### 파라미터 확정 (Round 5)
| 페이지 | 메서드 | 파라미터 | 인증 |
|---|---|---|---|
| `/search.asp` | GET | `tfSearch` (SQLi + 반사 XSS, 아래 서버 구조 참조) | 불요 |
| `/Login.asp` | POST | `tfUName`, `tfUPass` + GET `RetURL` | 불요(우회 가능) |
| `/showforum.asp` | GET | `id` (SQLi 후보) / POST `tfSubject`,`tfText` (**파괴적 — 승인 필요**) | 열람 불요, 쓰기 인증 필요 |
| `/showthread.asp` | GET | `id` (SQLi 후보) / POST `tfSubject`,`tfText` (**파괴적 — 승인 필요**) | 열람 불요, 쓰기 인증 필요 |
| `/Templatize.asp`, `/shownews.asp` | GET | `item` | 불요 |

### 비인증으로 열람 가능함이 확인된 것 (Round 5 정정)
- `/showforum.asp?id=1` → **200** (미인증에서도 포럼 목록이 렌더된다. 세션 없이 `/showforum.asp`
  를 호출하면 302 인 것은 `id` 가 비어 있을 때의 리다이렉트 때문이었다). 인증 여부는 메뉴가
  `logout <사용자명>` 인지 `login - register` 인지로 구별된다(4146B vs 3077B).
- 인증 세션 확보 경로: `POST /Login.asp` 에 `tfUName=admin'--&tfUPass=x` → SQLi 우회로 302 성공.

### Hidden/신규 파일 (Round 5 확정)
- `/Templates/MainTemplate.dwt.asp` (200, 5598B) — DreamWeaver 템플릿. 내용 분석은 다음 라운드.
- `/html/about.html` (200, 1995B) — `Templatize.asp?item=html/about.html` 기본값.
- `/styles.css` (200, 3390B), `/images/logo.gif` (200, 4933B)
- `/images/_vti_cnf/` · `/jscripts/tiny_mce/_vti_cnf/` (403 = 디렉터리 실존) — 디렉터리별
  FrontPage 오라클 표면(각각 노출 파일 1종: `logo.gif`, `tiny_mce.js`).

## Round 6 추가 (2026-09-23 09:05Z) — 게시판 id 구조와 쓰기 표면

### 포럼/스레드 (실측)
| 페이지 | 설명 | 인증 |
|---|---|---|
| `showforum.asp?id=<n>` | 포럼의 스레드 목록 | **미인증에서도 200**(열람 제한 없음) |
| `showthread.asp?id=<n>` | 스레드의 게시글 목록 | **미인증에서도 200** |

확인된 id: forum `0` = "Acunetix Web Vulnerability Scanner", forum `1` = "Weather",
thread `0` / `1` / `2`. 게시글 제목에는 서버가 `" - " & REMOTE_ADDR` 를 자동 append(작성자 IP 노출).

### 저장형 XSS (Round 6 확정)
`showthread.asp?id=0` 에 작성한 테스트 게시글 1건이 `scratch/round6/` 증거에 남아 있다
(제목 `RT6-STORED-XSS-PROOF - 49.142.61.26`, 본문 `<img src=x onerror=alert(1)>`).
- 페이로드는 **모든 열람자**(미인증 포함)에게 실행된다 — CDP 로 `alert` 다이얼로그 발생 확인.
- 사이트 안내상 게시글은 매일 초기화되므로 이 테스트 글은 의도적으로 남겨둔다(삭제에는 파괴적
  경로가 필요해 사용하지 않음).

### Round 7 추가 — 우리 소유 테스트 스레드 + 게시판 id 표면

| 위치 | 내용 | 비고 |
|---|---|---|
| `showforum.asp?id=0` POST | **thread id=9 생성** (제목 `RT7-OWN-THREAD-DO-NOT-USE`) | 우리 소유, 후속 테스트 기준점 |
| `showthread.asp?id=9` | 우리 스레드. 게시글 3건(`RT7-OWN-THREAD-DO-NOT-USE`, `RT7-OWN-POST-2`, `RT7-OWN-POST-3`) | 전부 `RT7-` 마커로 식별 가능 |
| thread id 집합 | forum 0 = `0~9`, forum 1 = `1` | Round 7 종료 시점, 외부 사용자 글은 유입되지 않음 |

- 스레드 **생성 경로(`showforum.asp` POST)도 저장형 XSS 성립** — 우리 스레드 본문
  `<img src=x onerror=alert(7)>` 가 이스케이프 없이 렌더됨(Round 6 의 `showthread.asp` 경로와 동일).
- `showforum.asp?id=` · `showthread.asp?id=` 는 **둘 다 SQLi** (Round 7 확정, GET 은 읽기 전용).
  우리가 만든 thread 9 를 기준으로 게시글 수를 블라인드 추출해 실제값 2 를 얻었다.
- `Default.asp` 의 포럼별 카운트 두 컬럼은 값이 항상 동일하게 나온다(같은 값을 두 번 표시하는
  구현으로 보임) — Round 7 에서 13→16 으로 변한 것은 우리가 추가한 게시글 3건과 정확히 일치했다.
  **콘텐츠 변화를 판정할 때 이 페이지 카운트만 보면 오독한다**(스레드 수가 아님).



---

## Round 12 (2026-09-23 11:30Z) — 페이지 인벤토리 확정 + 신규 페이지 2건

**웹루트 ASP 는 11개가 전부임을 확정** (56종 후보를 LFI 존재 오라클로 조사 → 전부 500):
```
Default.asp  db.asp  logInput.asp  Login.asp  Logout.asp  Register.asp
Search.asp   ShowForum.asp  ShowThread.asp  shownews.asp  Templatize.asp
```

**신규 확인 페이지**

| 경로 | 메서드 | 파라미터 | 설명 |
|---|---|---|---|
| `/Logout.asp` | GET | `RetURL` | ★ 세션 삭제 후 `RetURL` 로 **무인증 오픈 리다이렉트**(302). 인증 불필요 |
| `/_vti_cnf/<file>` | GET | — | ★ FrontPage 메타데이터 디렉터리(HTTP 200). 내부 가상경로명 `acuforum/` + 페이지 인벤토리 + 파일별 크기/백링크 노출. 없는 파일은 404 ⇒ 존재 오라클(디렉터리 리스팅은 아님) |
| `/Register.asp` | POST | `tfUName`·`tfUPass`·`tfEmail`·`tfRName`(+`RetURL`) | 회원가입 → `INSERT INTO users` **4필드 무이스케이프**(신규 주입 지점, 쓰기) |
| `/logInput.asp` | GET/POST | — | 서버변수·POST 전량을 파일로 쓰는 함수가 있으나 **호출부 주석 처리**(로그 미생성). 소스에서 경로 `C:\scripts\logInput.txt` 노출 |

**401/403/404 로 확정된 비존재 경로(재시도 금지)**

| 경로 | 응답 |
|---|---|
| `/_vti_pvt/*` (service.pwd·administrators.pwd·authors.pwd·users.pwd·service.cnf·access.cnf) | 404 |
| `/_vti_bin/*` (shtml.dll·_vti_aut/author.dll·_vti_adm/admin.dll·author.exe) | 404 |
| `/_vti_inf.html`·`/_vti_log/`·`/_vti_txt/`·`/_vti_script/` | 404 |
| 하위 디렉터리 `_vti_cnf`(`/html/`·`/jscripts/`·`/images/`·`/avatars/`·`/Templates/`) | 404 |
| 디렉터리 리스팅(`/html/`·`/jscripts/`·`/images/`·`/avatars/`·`/Templates/`·`/aspnet_client/`) | 403 |
| 업로드·파일매니저 23종(`upload.asp`·`filemanager.asp`·`saveimage.asp`·`jscripts/tiny_mce/plugins/mcpuk/...`) | 500 (500=없음) |
| 숨은 스크립트 56종(`admin.asp`·`conn.asp`·`config.asp`·`setup.asp`·`install.asp`·`xmlrpc.asp`·`api.asp`·`soap.asp`·`mail.asp`·…) | 500 |
