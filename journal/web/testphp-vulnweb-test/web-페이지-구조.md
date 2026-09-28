# 페이지 구조 — testphp-vulnweb-test

대상: `testasp.vulnweb.com` (2026-09-23 라운드 1에서 원래 타겟 `testphp.vulnweb.com` 이
다운된 것을 확인하고, 사용자가 `targets/testphp-vulnweb-test.json` 의 scope를 이 호스트로
갱신 — project_id 는 그대로 유지).

성격: Acunetix 가 공개 운영하는 **의도적 취약 ASP 포럼**("acuforum"). 사이트 자체 경고문에
"deliberately vulnerable to SQL Injections, directory traversal, and other web-based
attacks / built using ASP / content is erased daily" 라고 명시. 정적 파일 구조는 Dreamweaver
템플릿(`/Templates/MainTemplate.dwt.asp`) 기반이라 모든 페이지가 동일 헤더/메뉴를 공유.

## 공개 영역 (인증 불필요)

| 경로 | 설명 | 파라미터 |
|---|---|---|
| `/` , `/Default.asp` | 포럼 목록 (랜딩). 포럼 3개: id=0 Acunetix WVS, id=1 Weather, id=2 Miscellaneous | — |
| `/showforum.asp` | 특정 포럼의 스레드 목록 | `id` (GET, 정수) |
| `/showthread.asp` | 특정 스레드의 게시글 목록 | `id` (GET, 정수) |
| `/Search.asp` | 게시글 검색 폼 + 결과 | `tfSearch` (GET) |
| `/Login.asp` | 로그인 폼 | `RetURL` (GET, 로그인 후 돌아갈 경로) / POST `tfUName`,`tfUPass` |
| `/Register.asp` | 회원가입 폼 | `RetURL` (GET) / POST `tfUName`,`tfRName`,`tfEmail`,`tfUPass` |
| `/Templatize.asp` | `html/` 하위 정적 템플릿 조각을 렌더 | `item` (GET, 경로 문자열 — 기본 `html/about.html`) |
| `/styles.css` | 스타일시트 | — |
| `/Images/`, `/Templates/` | 정적 자원 디렉토리 (디렉토리 리스팅은 403) | — |
| `/Templates/MainTemplate.dwt.asp` | Dreamweaver 템플릿 원본이 **직접 200으로 노출** (소스 레벨 정보 노출) | — |
| `/Logout.asp` | 로그아웃 (인증 상태에서 메뉴에 나타남) | `RetURL` (GET) |

## 인증 필요 영역 (Round 4 에서 우회 세션으로 실제 확인)

- `/showthread.asp?id=N` 하단 **답글 작성 폼** — 비로그인 상태에서는 렌더되지 않고, 인증 후에만
  다음 폼이 나타난다(**실제 권한 상승 확인**, 2026-09-23 Round 4):
  ```html
  <form name="frmPostMessage" method="post" enctype="application/x-www-form-urlencoded">
    <textarea name="tfText" class="postit" id="tfText"></textarea>
  </form>
  ```
- `/Default.asp` 메뉴 — 인증 시 `Logout.asp?RetURL=%2FDefault%2Easp%3F` 링크가 생기고
  로그인한 사용자명이 라벨에 그대로 출력된다(`logout admin'--` 처럼 **입력값이 검증 없이** 표시됨).
- 회원가입은 `/Register.asp` 로 개방돼 있음(사이트가 매일 초기화되므로 계정도 매일 새로 필요).

## Hidden / 발견된 페이지

- `/Admin*`, `/admin.asp`, `/web.config`, `/global.asa`, `/_vti_bin/`, `/Default.asp.bak` → 전부 **404**
  (직접 접근 기준)
- `/web.config` 는 직접 GET 은 404 지만 **`/Templatize.asp?item=html/../web.config` 로 읽힌다**
  (Round 4 — traversal 경유로만 접근 가능한 파일)
- traversal 경유로 접근 가능한 파일시스템 경로(Windows): `windows/win.ini`,
  `windows/system.ini`, `windows/system32/drivers/etc/hosts` — 응용 프로그램 루트 상위 전체가 열림
- 세션/게시판 파일 업로드 경로, DB 백업 경로 — 아직 미탐색
- **공개 URL 로는 존재하지 않지만 traversal 로 읽히는 서버측 파일** (Round 5):
  `/db.asp`(DB 연결 문자열), `/logInput.asp`(파일 쓰기 함수), 그리고 `/showforum.asp`·`/Login.asp`
  등 모든 .asp 의 **소스**. 이들은 "페이지"가 아니라 include 대상이지만, 공격자 관점에서는
  traversal 로 접근 가능한 자산이므로 여기에 기록한다.

## 관측된 폼 (전부 `action=""` 즉 자기 자신으로 전송)

```html
<!-- /Login.asp (POST) -->
<form action="" method="POST">
  <input name="tfUName" type="text">
  <input name="tfUPass" type="password">
  <input type="submit" value="Login">
</form>

<!-- /Register.asp (POST) -->
<form action="" method="post" name="frmRegister">
  <input name="tfUName"><input name="tfRName"><input name="tfEmail"><input name="tfUPass">
</form>

<!-- /Search.asp (GET) -->
<form name="frmSearch" method="get" action="">
  <input name="tfSearch" type="text"><input type="submit" value="search posts">
</form>
```

## Round 7 (2026-09-28) 페이지 인벤토리 재확인

- 기존 인벤토리 전 경로 200 재확인(사이트는 매일 초기화되지만 코드/구조는 동일 —
  `Templatize.asp?item=<파일>` 로 받은 소스 11개가 이전 phase 사본과 바이트 단위로 같은 내용).
- **미발견 페이지 열거 실패**: `post/showposts/users/user/admin/edit/delete/upload/download/
  forum/thread/newthread/postmessage/profile/members/conn/config/include/header/footer` +
  `Search.asp.bak`/`Default.asp.bak` → 전부 404(이 서버의 404 본문 1245B와 동일). 즉 공개
  페이지 집합은 위 표가 전부다.
- `/Search.asp` 는 **SQLi 결과가 페이지에 직접 렌더되는 데이터 출력 채널**로도 쓸 수 있음
  (UNION 페이지 가시 추출 — `web-서버-구조.md` Round 7 절 참고). "페이지"는 아니지만
  공격자 관점의 출력 경로라 기록.
- traversal 로만 접근되는 서버측 파일 목록은 이번 라운드에서 늘어나지 않음(잔여 후보 전부 500).

## 사이트맵 (2026-09-23 관측)

```
/                              → Default.asp (포럼 목록)
├─ showforum.asp?id=0          → 스레드 목록(6 threads)
│  └─ showthread.asp?id=0..4
├─ showforum.asp?id=1          → Weather (thread id=0)
├─ showforum.asp?id=2          → Miscellaneous (0 threads)
├─ Search.asp?tfSearch=<q>
├─ Login.asp?RetURL=<path>
├─ Register.asp?RetURL=<path>
└─ Templatize.asp?item=html/about.html
```
