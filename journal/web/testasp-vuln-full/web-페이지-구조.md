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
- `/Templatize.asp` (500) — 항상 IIS 500 오류 페이지(1208B)

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
