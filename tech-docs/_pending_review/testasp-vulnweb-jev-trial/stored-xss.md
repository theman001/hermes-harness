# Stored XSS — 추가 케이스 (쓰기 없는 세션명 반사 · 쿠키 플래그)

> 기존 초안(`동일 대상의 기존 초안/stored-xss.md`)과 **같은 파일명** →
> 승격 시 그 문서에 아래 케이스를 병합하는 것이 목적.

## 재확인된 사례: `testasp-vulnweb-jev-trial`

- 기존 문서의 저장형 XSS 절차(로그인 → 게시글 본문에 `<script>` → **비인증 재방문**에서 원문 렌더)가 그대로 재현됨.
- 게시 본문은 **따옴표만 SQL 용도로 이스케이프**되고 HTML 인코딩은 되지 않는다(소스 근거: `Replace(x, "'", "''")` 만 존재).
- 반응 헤더에 `Content-Security-Policy` / `X-XSS-Protection` / `X-Frame-Options` **전부 없음** → 실행 보장.
- 기존 문서의 "저장형 PoC 는 서버에 남지 않는다" 교훈도 재확인됨(게시 직후 재조회에서 글 소멸 — 대상 환경 리셋 + 앱 자체 정리 로직).

## 신규 케이스 — **쓰기 0건**으로 XSS 실증: 세션 식별자 반사 ★

**상황**: 로그인 구현이 `Session("user") = Request.Form("id")` 로 **입력 원문**을 세션에 저장하고,
모든 페이지가 그 값을 **출력 인코딩 없이** 메뉴 등에 출력한다.

**핵심 제약**: 로그인 판정이 "쿼리 결과가 비어있지 않은가"이므로,
HTML 페이로드를 넣으려면 **행을 반환하는 조건을 함께** 넣어야 한다:

```bash
# 페이로드 = 우회 조건(행 반환) + HTML. 둘 다 만족해야 세션에 HTML 이 들어간다
XS="admin' AND '<img src=x onerror=alert(1)>'='<img src=x onerror=alert(1)>'--"
curl -s -o /dev/null -c c.txt -X POST --data-urlencode "id=$XS" --data-urlencode "pw=x" "http://<target>/Login.asp"   # → 302
curl -s -b c.txt "http://<target>/Default.asp" | grep -o "onerror=alert(1)"     # → 원문 렌더(= 실행)
```

**왜 유용한가**: 저장형 XSS 는 승인이 필요한 **쓰기**를 유발하지만, 이 변형은
**데이터 변경 0건**으로 XSS 실행을 증명한다 — 검증 라운드/재현 스크립트/승인 전 정찰에서 특히 쓸모가 있다.

**함정**
- `<img ...>'--` 처럼 **행을 반환하지 않는** 페이로드는 로그인 자체가 실패(200)한다 → "XSS 안 됨"으로 오판하기 쉽다.
- 세션명이 출력되는 위치를 먼저 소스에서 찾는다(예: 로그아웃 링크 옆 사용자 표시). 없으면 이 변형은 성립하지 않는다.
- 인코딩 흔적(`&lt;`)이 나오면 그 지점은 인코딩된 것 → 다른 출력 지점을 찾는다.

## 신규 케이스 — 임팩트 등급을 결정하는 **쿠키 플래그 확인** ★

XSS 의 실제 등급은 "세션 탈취 가능 여부"로 갈린다. 로그인 응답 헤더를 그대로 증거로 남긴다:

```bash
curl -s -o /dev/null -D - -X POST --data-urlencode "id=admin'--" --data-urlencode "pw=x" "http://<target>/Login.asp" \
  | grep -i 'set-cookie'
# 실측: Set-Cookie: <SESSIONID>=...; path=/        ← HttpOnly·Secure·SameSite 전부 없음
```

플래그가 없으면 `document.cookie` 판독이 가능해 **저장형 XSS 1회 게시 → 방문자 세션 하이재킹**까지 이어진다
(런타임 탈취는 실 피해자 세션이 필요하므로 시도하지 않고 **헤더 원문까지만 검증**하고
시나리오 문서에는 "미검증 확장"으로 표기한다).

## 방어 관점

- 사용자 유래 값은 **저장 시점이 아니라 출력 시점에** 문맥별 인코딩한다(HTML/JS/URL 분리).
- 세션 식별자에 사용자 입력을 그대로 담지 않는다(DB 조회값 또는 임의 토큰).
- 쿠키에 `HttpOnly`(필수) + `Secure` + `SameSite` 를 설정하고, CSP 로 인라인 스크립트를 차단한다.
- 게시판 본문은 허용 태그 화이트리스트 방식으로 정제한다(따옴표 이스케이프만으로는 XSS 를 못 막는다).

<!-- 출처: journal/web/testasp-vulnweb-jev-trial/, Round 3 · Round 4 -->
