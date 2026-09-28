# 페이지 구조 — testasp-vulnweb-jev-trial

대상: http://testasp.vulnweb.com (Acunetix 공개 취약 테스트 포럼, IIS 8.5 / classic ASP).
갱신: 2026-09-28 (Round 1 정찰 + Round 2·3 실증)

## 공개 영역 (인증 불요)

- `/` , `/Default.asp` — 포럼 목록 (forums/threads 렌더, 200/3538)
- `/showforum.asp?id={0,1,2}` — 포럼 상세 (id 없으면 302 → Default.asp, 200/3077)
- `/showthread.asp?id={0..4}` — 스레드 상세 (id 없으면 302, 200/3083; id≥5 및 비정수는 500)
- `/Search.asp?tfSearch=` — 검색 (파라미터 없음 200/2809, 빈값 200, 값 있으면 결과 렌더)
- `/Login.asp?RetURL=` — 로그인 폼 (인증 방식은 `web-서버-구조.md`)
- `/Register.asp?RetURL=` — 가입 폼
- `/Logout.asp?RetURL=` — 로그아웃 (302)
- `/Templatize.asp?item=html/about.html` — Dreamweaver 템플릿 + 파일 렌더 (200/4594)
- `/HTML/About.html` — 위 item 이 로드하는 정적 파일 (200/1995)
- 정적 자원: `/styles.css`(200/3390), `/rpb.png`(200/40), `/Images/logo.gif`(200/4933),
  `/avatars/noavatar.gif`(200/950), `/robots.txt`(200/13, `User-agent: *` 만)

## 인증 필요 영역 (세션 쿠키 보유 시에만)

- `showforum.asp` 내 새 스레드 폼 `frmPostMessage`(tfSubject + tfText) — 익명 3077B vs 인증 4146B
- `showthread.asp` 내 답글 폼 `frmPostMessage`(tfSubject + tfText) — 위와 동일 조건
- ※ 로그인 자체는 SQLi 우회로도 가능(`web-서버-구조.md` 참조)

## Hidden / 발견된 페이지 (2026-09-28 Round 1~3 추가)

- `/_vti_cnf/<파일명>` (12종, 전부 200) — FrontPage Server Extensions 메타데이터:
  `Default.asp` 926, `Search.asp` 926, `templatize.asp` 930, `showthread.asp` 882,
  `showforum.asp` 861, `register.asp` 778, `Login.asp` 772, `styles.css` 404,
  `logout.asp` 338, `DB.asp` 338, `shownews.asp` 338
  → 파일 인벤토리(backlink)·내부경로·FPSE 버전(4.0.2.8912, 2007-10-05) 노출
- `/Images/_vti_cnf/`(403) + `/Images/_vti_cnf/logo.gif`(200/286) — 하위 메타디렉터리도 존재
- `/jscripts/tiny_mce/`(403) — **TinyMCE 2.0RC4(2005)** 트리:
  `tiny_mce.js`(200/132342), `tiny_mce_popup.js`(200/6835), `blank.htm`(200/213),
  `langs/en.js`(200/1650), `utils/{validate,form_utils,mctabs}.js`(200),
  `themes/simple/editor_template.js`(200/5727), `_vti_cnf/tiny_mce.js`(200/180)
  → `showthread.asp`/`showforum.asp` 의 글쓰기 폼이 이 에디터를 로드한다
- `/Templates/MainTemplate.dwt.asp`(200/2488) — Templatize 이 include 하는 템플릿
- `/cgi-bin/`(403) + `/cgi-bin/test.txt`(200/3) — 리스트는 막혀 있고 파일 하나만 읽힘
- `/aspnet_client/system_web/`(403) + `/aspnet_client/system_web/2_0_50727/`(403)
- `/t/`(301) + `/t/fit.txt`(200/64), `/t/xss.html`(200/33), `/t/xss.js`(200/27),
  `/t/dot.gif`(200/43) — 이전 테스터가 남긴 산출물/아티팩트
- **`/db.asp` , `/DB.asp`** (200/0) — 링크는 없지만 `<!--#INCLUDE FILE="db.asp"-->` 로 모든 페이지에
  포함되는 DB 연결 모듈 (`GetConnection()`, 접속문자열 하드코딩)
- **`/loginput.asp`** (200/0) — `db.asp:26` 이 `<!--#INCLUDE FILE="logInput.asp"-->` 로 포함.
  `WriteToFile()` 함수 보유, `C:\scripts\logInput.txt` 쓰기 호출은 주석 처리. 미링크
- **`/shownews.asp?item=<상대경로>`** — 미링크 orphan. `Templatize.asp` 와 **동일한 파일 읽기
  프리미티브의 두 번째 인스턴스**(템플릿 래퍼 없이 raw 반환, 출력만 Server.HTMLEncode).
  무파라미터/`item=0,1,2,3,test,.` 는 500(차단 아님, 디렉터리를 OpenTextFile 한 예외)

## 미존재 확인 (404 — 재탐색 불필요)

`/admin`, `/session`, `/Acunetix`, `/campaign/adidas-x16`, `/favicon.ico`, `/logo.gif`,
`/news.asp`, `/avatars/0..3`, `/1`, `/123`, `/index.asp`, `/index.html`, `/web.config`,
`/global.asa`, `/conn.asp`, `/config.asp`, `/admin.asp`, `/_vti_pvt/*`, `/_vti_bin/*`,
`/_vti_inf.html`, `/_vti_log`, `/_vti_text`, IIS 8.3 단축명(tilde) 전부
