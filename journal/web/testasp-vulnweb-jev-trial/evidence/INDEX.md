# evidence/ 인덱스 — testasp-vulnweb-jev-trial

회수 시각: 2026-09-28T08:30:38Z (phase cleanup 이전)

※ 모든 증거는 **수집 시각 기준**으로만 유효하다 — 이 공개 데모는 수시로 리셋되고, 앱 자체의
`total>100 → DELETE` 분기 때문에 게시글이 사라질 수 있다(실제로 Round 3 의 XSS 게시글이 소멸).

- `cred_sample1.body` (4,170B) — 민감데이터 증거 — users 최소 샘플 1행(MIN(uname)) 원문 응답
- `db_asp_source.body` (2,908B) — LFI 로 읽은 db.asp 소스 — DB 접속문자열/Uid·Pwd 평문 노출
- `default_asp_source.body` (7,142B) — Default.asp 소스 — 55행: 세션명 무이스케이프 출력(반사 XSS 근거)
- `login_asp_source.body` (7,154B) — Login.asp 소스 — 인증 쿼리(33)·세션 대입(36)·RetURL 리다이렉트(39)
- `login_bypass.hdr` (276B) — 인증우회 로그인 응답 헤더(302 Location: Default.asp + ASPSESSIONID 쿠키)
- `loginput_asp_source.body` (3,538B) — loginput.asp 소스 — WriteToFile 함수 존재, C:\scripts 로그 호출은 주석 처리
- `mitmproxy_capture_phase.jsonl` (4,481B) — 이 phase 의 mitmproxy 캡처 원본(cleanup 전 회수)
- `perm_oracle.body` (5,297B) — 권한 오라클 — sysadmin/xp_cmdshell/CONTROL SERVER/교차DB 권한 값
- `register_asp_source.body` (7,367B) — Register.asp 소스 — INSERT 무이스케이프(회원가입 SQLi)
- `search_asp_source.body` (7,786B) — Search.asp 소스 — 문자열 결합 SQL(CHARINDEX), 단일 쿼리 → UNION 10열 가능 근거
- `secondorder_500.body` (1,208B) — second-order 증거 — 따옴표 포함 세션으로 답글 POST 시 500(1208B)
- `session_form_anon.body` (3,077B) — 익명 동일 페이지(게시 폼 없음) 대조군
- `session_form_auth.body` (4,146B) — 인증 세션에서 게시 폼(tfSubject) 노출 확인 응답
- `showforum_asp_source.body` (10,668B) — showforum.asp 소스 — 게시 INSERT + total>100 → DELETE 분기(⚠️ POST 경로 id 주입 금지 근거)
- `shownews_raw_lfi.body` (92B) — LFI #2 증거 — shownews.asp?item=win.ini raw 응답(템플릿 래퍼 없음)
- `shownews_verdict.md` (8,874B) — shownews.asp 정체 판정 정리(LFI 인스턴스 확정 과정)
- `showthread_asp_source.body` (9,786B) — showthread.asp 소스 — 답글 INSERT(60: Session uname 무이스케이프), total>100 DELETE 분기
- `sqli_RESULTS.md` (4,944B) — Round 2 SQLi 판정 정리(지점별 오라클·증거값·함정)
- `sqli_boolean_false.body` (1,208B) — SQLi boolean 거짓조건 응답(id=1 AND 1=2 → 500, 1208B IIS 기본 페이지)
- `sqli_boolean_true.body` (3,117B) — SQLi boolean 참조건 응답(id=1 AND 1=1 → 200)
- `sqli_requests.jsonl` (77,582B) — Round 2 SQLi 전 요청/응답 메타 265건
- `sqli_union_10col.body` (3,841B) — SQLi UNION 10열 렌더 응답(ACUVERIFY=acuforum 등 값이 본문에 출력)
- `verify_chain_output.txt` (6,522B) — Round 4 재현 스크립트 전체 출력(PASS=65 FAIL=0)
- `web_config_source.body` (3,138B) — LFI 로 읽은 web.config
- `win_ini_output.body` (2,763B) — LFI #1 증거 — Templatize.asp?item=../../../../windows/win.ini 응답(200, [fonts] 포함)
- `xss_session_reflected.body` (3,556B) — 반사 XSS(쓰기 없음) 증거 — 세션명이 Default.asp 로그아웃 메뉴에 원문 출력
- `xss_stored_anon.body` (3,398B) — 저장형 XSS 증거 — 비인증 재방문 시 <script>alert(...) 원문 렌더
