# Open Redirect

> 승격 대상: `tech-docs/web/general/open-redirect.md`

## 1. 원리

`Response.Redirect(요청값)` 처럼 **검증 없이 사용자 입력을 Location 헤더에 넣으면**, 링크가
신뢰 도메인을 가리키므로 피싱/OAuth code 탈취/SSRF-체인 등에 쓰인다. 단독 심각도는 낮지만
**체이닝 재료**로서 가치가 있다(OAuth `redirect_uri` 와 결합하면 계정 탈취).

## 2. 케이스 A — 같은 취약 패턴이 여러 파일에 복제된 경우

이 프로젝트에서는 `RetURL` 을 받아 리다이렉트/링크에 쓰는 코드가 **4개 파일에 복제**돼 있었고,
**파일마다 선행 조건이 달랐다.** 이럴 때는 "가장 조건이 약한 복사본"을 대표 PoC 로 삼는다 —
보고서 임팩트가 가장 크고 검증도 쉽다.

| 복사본 | 선행 조건 | 리다이렉트 대상 | 판정 |
|---|---|---|---|
| **로그아웃** | **없음(무인증 · 단일 GET)** | 입력 그대로 | ★ **대표 PoC** |
| 로그인 | 로그인 POST 성공(자격증명 또는 SQLi 우회) | 입력 그대로 | 취약 |
| 회원가입 | 가입 POST 성공 | `Login.asp?RetURL=<값>` 로 **동일 호스트 전달** | 취약(2단계) |
| 템플릿/기타 | — | 링크 생성에만 사용(`URLEncode`) | **해당 없음** |

★ **"리다이렉트하는 파일"과 "파라미터를 전달만 하는 파일"을 구분하라.** 회원가입 건은 자기
호스트로 리다이렉트하고 파라미터를 넘길 뿐이라 **단독 오픈 리다이렉트가 아니다** — 이후 로그인
단계가 성립해야 완성된다. 이걸 구분하지 않으면 4건이라고 부풀렸다가 1건으로 깎인다.

**정적 근거 + 동적 근거를 함께 남긴다**: 소스에서 `Response.Redirect(Request.QueryString("RetURL"))`
를 확보하고, 실제 `Location` 헤더를 실측한다.

```bash
curl -s -D - -o /dev/null "$BASE/Logout.asp?RetURL=http%3A%2F%2Fexample.com%2F" | grep -i '^location'
# → Location: http://example.com/
curl -s -D - -o /dev/null "$BASE/Logout.asp" | grep -i '^location'   # 대조군 → Default.asp
```

## 3. ★ 함정 — 자동 리다이렉트 추적이 검증을 무효화한다

`curl -L` 과 `urllib` 기본 opener 는 **302 를 자동으로 따라간다.** 그러면 응답이 최종 페이지의
**200** 으로 보여 "리다이렉트가 없다"고 **정반대로 오판**한다(이 프로젝트에서 실제로 발생).
게다가 외부 도메인으로 따라가면 DNS 실패로 스크립트가 죽는다.

```python
# 리다이렉트를 따라가지 않는 opener
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
OPENER = urllib.request.build_opener(NoRedirect)
```
```bash
# curl 은 -L 을 쓰지 않는다(기본값이 원 응답 관측)
curl -s -D - -o /dev/null "$URL" | grep -i '^location'
```
리다이렉트 취약점은 **항상 원 응답의 상태코드와 `Location` 헤더**로 판정한다.

## 4. 우회 변형 매트릭스 (검증 부재를 보이기 위해 함께 테스트)

`http://` 만 막는 블랙리스트를 가정하고 다음을 모두 시도한다. 이 프로젝트에서는 **검증이 아예
없어 6종 전부 그대로 통과**했다 — "차단 시도조차 없음"이 보고서에서 더 강한 근거다.

```
http://example.com/          기본
//evil.example/p             프로토콜 상대
https://attacker.tld/phish   https
https:example.com            스킴만 지정(콜론 뒤 슬래시 없음)
%09//evil.example            탭 접두(프로토콜 검사 우회)
/%5Cevil.example             백슬래시 혼합
```
대조군(파라미터 없음/정상 경로)도 함께 보내 **"파라미터가 있을 때만 외부로 나간다"** 를 보인다.

## 5. 보고서에서의 위치

단독으로는 Low~Medium. **체이닝 항목으로 배치**하라:
- 저장형 XSS/오픈 리다이렉트 → 피싱 신뢰도 상승
- 오픈 리다이렉트 + OAuth/SSO `redirect_uri` → **토큰 탈취**(심각도 급상승, 반드시 확인)
- 오픈 리다이렉트 + 인증 쿠키가 URL 로 전달되는 구조 → 세션 노출

## 6. 방어 관점

- 리다이렉트 목적지는 **허용 목록**으로만 허용한다(경로만 받고 호스트는 서버가 결정).
- 상대경로만 허용하더라도 `//`(프로토콜 상대)와 `\` 를 별도로 차단해야 한다.
- 리다이렉트/링크 생성 코드가 **여러 파일에 복제**돼 있으면 한 곳만 고치고 끝내지 않는다.

<!-- 출처: journal/web/testasp-vulnweb-full/, Round 12·14 -->
