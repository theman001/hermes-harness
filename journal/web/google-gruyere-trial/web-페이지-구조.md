# 페이지 구조 — google-gruyere-trial

인스턴스: `https://google-gruyere.appspot.com/399820027374159079597995648128134925001/`
(방문자별 GID 샌드박스. `/start` → `GRUYERE_ID` 쿠키 발급 → `/<gid>/` 로 리다이렉트.
GID 를 바꾸면 완전히 다른 샌드박스 인스턴스가 되므로 라운드 간 재사용 필요.)

## 공개 영역 (무인증)
- `/start` — 인스턴스 발급 안내 페이지
- `/<gid>/` — Home: 전체 사용자 최근 스니펫 + (로그인 시) 내 private_snippet
- `/<gid>/login` — 로그인 폼 → GET `/<gid>/login?uid=&pw=`
- `/<gid>/newaccount.gtl` — 가입 폼 → GET `/<gid>/saveprofile?action=new&uid=&pw=&is_author=`
- `/<gid>/snippets.gtl` — `?uid=<u>` 로 **타 사용자 스니펫 열람**(작성자면 스니펫 전체)
- `/<gid>/feed.gtl` — AJAX JSON 피드. `?uid=<u>` 있으면 해당 사용자, 없으면 전체 요약 + 내 private_snippet
- `/<gid>/lib.js` — 클라이언트 스크립트 (응답을 `eval()` 로 파싱)
- `/<gid>/dump.gtl` — **디버그 덤프 템플릿(무인증)**
- `/<gid>/manage.gtl` — **관리자 페이지 템플릿(무인증 접근됨)**
- `/<gid>/showprofile.gtl` — 레거시 템플릿(폼 action=`/set`, 서버 핸들러 없음)
- `/<gid>/base.css`, `/<gid>/menubar.gtl`, `/<gid>/error.gtl` — 리소스/템플릿 직접 서빙
- `/<gid>/error.gtl` 렌더 경로: 잘못된 경로/업로드 실패 등에서 `Invalid request: <path>` 반사

## 인증 필요 영역 (쿠키 `GRUYERE` 보유 시)
- `/<gid>/newsnippet.gtl` / `/<gid>/newsnippet2?snippet=` — 스니펫 작성
- `/<gid>/deletesnippet?index=N` — 스니펫 삭제
- `/<gid>/upload.gtl` / POST `/<gid>/upload2` — 파일 업로드
- `/<gid>/editprofile.gtl` / `/<gid>/saveprofile?action=update...` — 프로필 편집
- `/<gid>/logout` — 로그아웃

## 관리자 전용 (쿠키의 is_admin 플래그 필요)
- `/<gid>/reset` — DB 리셋 (`_PROTECTED_URLS`, admin 필요)
- `/<gid>/quit` — 서버 종료 (`_PROTECTED_URLS`, admin 필요)
- `/<gid>/quitserver` — 서버 종료 핸들러. **`_PROTECTED_URLS` 에 미등록** (핸들러명과 보호목록 불일치)

## Hidden/발견된 페이지 (2026-09-28 Round 1 추가)
- `/<gid>/dump.gtl` — 핸들러가 없는 템플릿이라 `_SendFileResponse` 경로로 렌더됨 → **무인증 DB 전체 덤프**
- `/<gid>/manage.gtl` — 위와 같은 이유로 무인증 렌더 → 관리자 기능 링크 노출
- `/<gid>/showprofile.gtl` — 레거시 잔존 템플릿
- `/<gid>/menubar.gtl`, `/<gid>/base.css` — 리소스 디렉터리가 URL 로 직접 노출

## 외부(스코프 내) 문서/배포물
- `/` `/part1` `/part2` `/part3` `/part4` `/part5` — 코드랩 문서(공격 유형 목록 포함)
- `/code/` `/static/codeindex/html` — 소스 브라우저
- `/gruyere-code.zip` — 소스 전체 다운로드 (Python 2.7, 로컬판)

## 페이지별 인젝션/노출 지점 (Round 4~5 실측)
| 페이지 | 지점 | 상태 |
|---|---|---|
| `<gid>/` (홈) | 스니펫 `{{snippets.0:html}}`, icon `src='{{icon:text}}'` | 저장형 XSS 실행 확인 |
| `<gid>/snippets.gtl?uid=` | h2 `{{uid.0}}`(HTML), Refresh `onclick`(속성) | 반사형 XSS 실행 확인 |
| `<gid>/snippets.gtl` | 본인 스니펫 `{{_this:html}}` | 저장형 XSS 실행 확인 |
| `<gid>/feed.gtl?uid=` | JS 문자열 안 `{{uid.0}}` | JS 인젝션(앱 `_refresh()` eval 경유) 실행 확인 |
| `/<gid>/<아무경로>` | `Invalid request: <path>` | 반사형 XSS 실행 확인 |
| `<gid>/dump.gtl` | `_cookie`/`_profile`/`_db` 전부 | 무인증 전량 노출 |
| `<gid>/manage.gtl` | 관리자 기능 링크 | 무인증 접근 가능 |
| `<gid>/upload2.gtl` | 업로드 결과의 `{{url}}` | 무이스케이프(미실증, 응답에만 노출) |

## 파일 업로드 계열 (Round 6 추가, phase 2)
| 지점 | 관찰 | 상태 |
|---|---|---|
| `/<gid>/upload.gtl` | 업로드 폼(`action='/<gid>/upload2'`, `name='upload_file'`) | 정상 |
| `/<gid>/upload2` (POST) | `_Open('resources/<uid>/' + filename, 'wb')` — 파일명 정규화 없음 | 경로이탈 쓰기 실증 |
| `/<gid>/<uid>/<file>` | 업로드한 파일이 확장자 화이트리스트대로 서빙(`.html`→`text/html`, `.js`→`application/javascript`) | 저장형 XSS 실증 |
| `/<gid>/<uid>/<file>.html` | 로그인 피해자가 열면 같은 출처에서 스크립트 실행 → `document.cookie` 탈취 | 저장형 XSS 실증 |

## GTL 템플릿 표면 (Round 7 추가, phase 2)
- `.gtl` 확장자는 **정적 파일이 아니라 서버 템플릿**으로 렌더된다(`_SendFileResponse` 의
  `if filename.endswith('.gtl'): _SendTemplateResponse(...)`). 파이썬 핸들러가 없는
  `.gtl`(dump/manage/showprofile/feed/upload2…)이 전부 이 경로다.
- 따라서 `/<gid>/<uid>/<업로드한 파일>.gtl` 도 서버측에서 렌더된다 → 업로드가 곧 템플릿 주입.
- 템플릿에서 쓸 수 있는 것: `{{_db:pprint}}`(전 DB), `{{_profile...}}`, `{{_cookie...}}`,
  `[[include:<경로>]]`(파일 읽기, 경로이탈 가능), `[[for:]]`/`[[if:]]`, `{{x:*param}}`(파라미터
  로 필드명 지정).
- `feed.gtl` 은 JSON API 가 아니라 템플릿이며 `?uid=<임의 사용자>` 로 타 사용자 데이터를
  인증 없이 뽑는다.

## 무인증 상태변경 엔드포인트 (Round 8 추가, phase 2)
| 엔드포인트 | 인증 요구 | 비고 |
|---|---|---|
| `/<gid>/saveprofile?action=update&uid=<임의>` | **불필요** | pw 파라미터 없으면 검사 없음. 8개 필드 전부 반영 |
| `/<gid>/saveprofile?action=new` | 불필요 | 계정 생성(열린 가입) → 쿠키 구분자 인젝션의 진입점 |
| `/<gid>/newsnippet2`, `/<gid>/deletesnippet` | 세션 필요(uid 기준) | |
| `/<gid>/upload2` | 세션 필요(uid 기준) | uid 없으면 `resources/None/` 로 감 |
| `/<gid>/dump.gtl`, `/<gid>/manage.gtl`, `/<gid>/feed.gtl?uid=` | **불필요** | 읽기 노출 |

## 가입·쿠키 필드 주입 경로 (Round 9, phase 2)
- `/<gid>/saveprofile?action=new&uid=<anything>&pw=<8자이상>` → **중복 검사만** 하고 uid 를
  그대로 DB 키 + 쿠키 필드로 사용. uid 문자 검증 없음.
- uid 에 `|` 를 넣으면 서버가 발급하는 쿠키의 `is_admin`/`is_author` 필드가 공격자 의도대로
  정해진다 → **가입 폼 하나로 관리자 권한 상승**(시드 계정 비밀번호·시크릿 불필요).
- 검증된 흐름: 가입 → Set-Cookie 관찰 → 쿠키 재사용(`/dump.gtl` 의 `_cookie` 행, `/manage.gtl`
  의 `Manage this server` 링크) → DB 덤프와 대조해 권한 불일치 확인.

## 살균기 경유 렌더 지점 (Round 10, phase 2)
- `{{...:html}}` 를 쓰는 템플릿 = 살균기를 거치는 곳 = XSS 방어가 "있다고 가정된" 지점:
  `home.gtl`(private_snippet, 최신 스니펫), `feed.gtl`(uid 별 스니펫/비공개 스니펫).
- 스니펫 저장 경로: `/<gid>/newsnippet2?snippet=<본문>` (내 계정 스니펫만 사용).
- 검증 3단: ① 오프라인 `sanitize.SanitizeHtml()` 단위검사 → ② 실서버 저장 후 응답에 원문 보존
  확인 → ③ 브라우저(가능하면 비인증 세션)에서 `document.title`/DOM 속성으로 실행 확인.
