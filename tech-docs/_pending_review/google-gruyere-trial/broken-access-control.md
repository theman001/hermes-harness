# Broken Access Control — "CSRF 가능"을 주장하기 전에 "인증이 아예 없는가"를 먼저 배제하라

## 원리

상태변경 엔드포인트를 볼 때 흔히 다음 순서로 생각한다: *"GET 으로 상태가 바뀌고 CSRF 토큰이
없다 → CSRF 다."* 그런데 그 주장은 **쿠키가 실려야 성립하는 더 약한 형태**다. 인증 검사가
아예 없으면 CSRF 는 필요 없고(피해자 브라우저도, 피해자도 필요 없다), 임팩트는 같으면서
공격 표면은 더 넓다. **약한 프레임으로 보고하면 심각도가 깎인다.**

배제해야 할 패턴 두 가지:

1. **권한 플래그/대상 ID 가 요청 파라미터에서 온다**
   ```python
   uid = self._GetParameter(params, 'uid', cookie[COOKIE_UID])   # 파라미터가 우선!
   ```
   쿠키는 **폴백**일 뿐이다. 쿠키 없이도 임의 계정을 지정할 수 있다.

2. **인증 검사가 조건식 안에 숨어 있다**
   ```python
   elif (newpw and database[uid]['pw'] != oldpw and not cookie.get(COOKIE_ADMIN)):
       message = 'Incorrect password.'
   else:
       database[uid].update(profile_data)     # ← 여기엔 검사가 없다
   ```
   `newpw` 를 주지 않으면 조건이 거짓이 되어 **검사가 실행되지 않고** 바로 수정 경로로 간다.
   "비밀번호 변경만 보호되고 나머지 필드는 무보호"인 비대칭이 생긴다.

## 케이스 A — 무인증 상태변경 실증 (쿠키를 전혀 주지 않는다)

```bash
# -b/-c 옵션을 주지 않는다. 파라미터로 대상 계정을 지정한다.
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://<target>/<base>/saveprofile?action=update&uid=<any_user>&<field>=<marker>"
#   → 302 (성공)
```

**검증은 값 비교로**: 응답의 디버그/덤프에서 해당 계정의 필드를 파싱해 **변경 전후를 비교**하고,
**다른 계정은 무변경**임을 함께 보인다(그래야 "uid 파라미터가 계정을 정확히 겨냥한다"는
인과관계가 닫힌다). 파싱은 정규식보다 `ast.literal_eval` 등 구조 파서를 쓴다(멀티라인 repr
에서 정규식은 쉽게 어긋난다).

```python
import re, ast
for b in re.findall(r"<pre>(.*?)</pre>", html, re.S):
    try: d = ast.literal_eval(b)
    except Exception: continue
    if isinstance(d, dict) and "<any_user>" in d: print(d["<any_user>"])
```

**테스트 계정 예절**: 자기 계정으로 실증한 뒤 **같은 무인증 경로로 원래 값을 되돌린다**.
변경 흔적을 남기지 않으면 재현 기록도 깨끗해진다.

## 케이스 B — 매스어사인먼트(권한 필드가 요청에서 그대로 저장)

```bash
# 내 계정을 스스로 승격 (로그인 세션 사용)
curl -s -b <session> "https://<target>/<base>/saveprofile?action=update&uid=<me>&is_admin=True"
# 권한 플래그가 쿠키/토큰에 복사되는 구조라면 재로그인이 필요할 수 있다
curl -s -c <session> -b <session> -D - "https://<target>/<base>/login?uid=<me>&pw=<pw>" | grep -i set-cookie
```

주의: 권한 플래그가 **로그인 시점에 스냅샷**되는 구현이 있다 → 저장 직후가 아니라
**재로그인 후**의 쿠키/세션을 확인해야 "승격 완료"를 닫을 수 있다.

## 케이스 C — 같은 엔드포인트를 두 번째로 볼 때 물어야 할 질문

이 프로젝트에서 실제로 이렇게 발견됐다: Round 3 에서 같은 함수를 "로그인 세션 + 매스어사인먼트"
로 기록했는데, Round 8 에서 "**그 로그인이 정말 필요했나?**"를 다시 물어 쿠키 없이도 성립함을
확인했다. 우선순위가 낮아 보여도 **같은 엔드포인트를 재방문**할 가치가 있다.

체크리스트:
- 이 엔드포인트는 인증을 **어디서** 확인하는가(진입부 vs 조건식 내부 vs 아예 없음)?
- 대상 ID 는 어디서 오는가(쿠키/세션 vs 파라미터 vs 본문)?
- 인증 없이 호출하면 무슨 일이 일어나는가 — **직접 보내 본다**(자기 계정 범위에서).

## 승인 경계 (own_system 모드 기준)

자기 계정 범위를 넘는 상태변경(다른 사용자 계정 대상)은 **사전 승인이 필요한 별도 단계**다.
이 프로젝트에서는 `uid=<타인>&is_admin=True` 를 실행하지 않고, "uid 파라미터가 계정을
겨냥함"은 **자기 계정 실험 + 타 계정 무변경 대조**로 닫았다 — 증거 중복이면서 경계를 넘는
실행을 피하는 방법으로 유효했다.

## 확인된 사례

- 재확인된 사례: `google-gruyere-trial` (Round 3 → Round 8 — `saveprofile?action=update` 가
  `pw` 파라미터가 없으면 인증 검사를 실행하지 않고, `uid` 는 파라미터 우선이라 **쿠키 없이**
  임의 계정 프로필 변경이 가능. CSRF 후보를 이 발견이 흡수함).

## 방어 관점 메모

- 인증·인가 검사는 **진입부에서 무조건** 수행하고, 권한 판단 조건식 안에 숨기지 않는다.
- 대상 리소스 ID 는 세션에서 도출하고, 파라미터로 받은 ID 는 **소유권 검사**를 반드시 거친다.
- 상태변경은 GET 이 아닌 POST/PUT + CSRF 토큰으로. (단, 이는 인증 부재를 대체하지 못한다 —
  인증이 없으면 CSRF 대책은 무의미하다.)

<!-- 출처: journal/web/google-gruyere-trial/, Round 3 / Round 8 -->
