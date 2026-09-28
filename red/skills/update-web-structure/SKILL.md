---
name: update-web-structure
description: recon 0단계의 구조 추론을 web-페이지-구조.md/web-서버-구조.md 두 파일로 영속화하고, 이후 라운드마다 수정/추가/삭제로 계속 갱신한다. "공격 경로 소진 판단"의 입력이 된다.
version: 1.0.0
author: llm-abliteration project
license: MIT
platforms: [linux]
tags: [recon, redteam, bugbounty, structure]
category: redteam
---

# Update Web Structure

recon 0단계(실사용자 시뮬레이션)에서 타겟을 실제 이용자처럼 써보며 얻은 구조 추론을
1회성 기록이 아니라 project 내내 계속 갱신되는 살아있는 문서로 관리한다. 이후 recon/
exploit 라운드마다 확인되거나 예측되는 변화를 반영한다(수정/추가/삭제 자유 — 고정
스키마에 값만 채우는 `update-recon-summary`와 달리 서술형 문서).

## 두 파일의 역할 차이

- **`web-페이지-구조.md`**: 사이트맵/페이지 계층. 정상 플로우(로그인, 메인 기능들)로
  시작해서, recon/exploit 중 발견되는 hidden 페이지나 관리자 페이지를 추가한다. 갱신
  빈도는 비교적 낮음 — 골격은 recon 0단계에서 대부분 잡히고 이후엔 새 페이지 발견 시에만
  추가.

  형식 예시:
  ```markdown
  # 페이지 구조 — <project_id>

  ## 공개 영역
  - `/` — 랜딩 페이지
  - `/login`, `/signup` — 인증
  - `/products/{id}` — 상품 상세

  ## 인증 필요 영역
  - `/account/mypage` — 마이페이지
  - `/account/orders` — 주문 내역

  ## Hidden/발견된 페이지 (2026-09-22 추가)
  - `/admin-old` — 레거시 관리자 페이지, 인증 없음(notable_findings 참고)
  ```

- **`web-서버-구조.md`**: 추론된 백엔드 아키텍처(인증 방식, API 패턴, 데이터 흐름,
  `tech_stack` 판단 근거). **인증 방식은 서술로 그치지 말고, 그대로 재실행 가능한 로그인
  curl을 그대로 기록**한다 — mitmproxy 캡처는 phase가 끝나면 사라지는데 project는 여러
  phase에 걸칠 수 있으므로, project 레벨로 영속되는 이 파일이 유일하게 안전한 재현 수단이다.
  갱신 빈도가 높음 — 라운드마다 확인/반증되는 대로 수시 갱신.

  형식 예시:
  ```markdown
  # 서버 구조 — <project_id>

  ## 인증 방식
  JWT 기반(세션 쿠키 아님) — 로그인 후 `/api/v1/session` 응답 body의 `token` 필드를
  이후 모든 요청의 `Authorization: Bearer <token>` 헤더에 실어야 함.

  **재현 가능한 로그인 curl**:
  ```bash
  curl -s -X POST https://api.target.com/api/v1/session \
    -H "Content-Type: application/json" \
    -d '{"email":"<test_account.json의 email>","password":"<test_account.json의 password>"}'
  # 응답: {"token": "...", "user_id": ...}
  ```

  ## API 패턴
  REST, `/api/v1/<resource>/<id>` 형태. 페이지네이션은 `?page=&limit=`.

  ## tech_stack 근거
  `Server: nginx`, `laravel_session` 쿠키 없음(JWT 기반이라 예상대로), 에러 페이지가
  Laravel 기본 디버그 페이지 형태 — PHP/Laravel로 확정.
  ```

## When This Skill Activates

recon 0단계에서 최초 생성, 이후 recon/exploit 라운드마다 확인된(또는 예측되는) 변화를
반영한다.

**동시쓰기 방지**: recon 라운드에서 `delegate_task`로 최대 10개 자식이 병렬로 돌 수 있는데,
자식들이 이 Skill을 직접 호출하면 같은 파일에 동시에 써서 경합이 날 수 있다 — **자식은
원본 조사만 하고 부모에게 요약만 반환**(Hermes 기본 동작), **이 Skill 호출은 항상
부모(A)만** 위임 완료 후 결과를 취합해서 한다. 자식이 이 Skill을 직접 호출하는 건 금지다.

## 저장 위치

`journal/web/<project_id>/web-페이지-구조.md`, `web-서버-구조.md` — project 레벨,
phase 경계와 무관하게 영속.

## 워치독과의 관계

이 두 파일의 diff를 `services/watchdog/round_watchdog.py`가 라운드마다 비교해서 "공격
경로 소진"을 판정한다 — 이 Skill 자신은 그 판정에 관여하지 않고, 파일 내용을 정확하고
성실하게 유지하는 데만 집중한다.

정확한 판정식(코드 확인값):

```
attack_exhausted = (page_stale_rounds  >= 3)
               and (server_stale_rounds >= 3)   # EXHAUSTION_THRESHOLD = 3
```

- 라운드 카운트는 project 누적(`total`) 기준 — phase 경계와 무관하게 이어진다.
- **두 축 모두** 임계값을 넘어야 한다(`AND`). 한 파일만 갱신돼도 그 축은 0으로 리셋된다.
- 상태는 `journal/web/<project_id>/exhaustion_state.json` 에 누적된다.

### 함정: 미갱신이 "소진"으로 오판되어 phase 가 조기 종료된다

**exploit 라운드에서도 매 라운드 이 파일들을 갱신하지 않으면, 라운드 예산을 대부분
남긴 채 phase 가 강제 종료된다.** 학습한 내용을 일지(`write-journal-entry`)에만 적고
구조 파일에 반영하지 않으면, 위 두 축이 모두 3라운드 연속 무갱신이 되어 워치독이
`termination_reason.json` 에 `attack_exhausted: true` 를 쓰고, SOUL 규칙에 따라 새 공격을
시작할 수 없게 된다.

실측 사례: 5라운드만 쓰고(상한 20, 예산 15라운드 잔여) XSS 3종까지 실증했는데도
Round 2~4 에서 두 파일을 갱신하지 않아 종료 신호가 났다. 종료 시점에 남아 있던 미실증
경로는 업로드 임의쓰기·CSRF·쿠키 구분자 인젝션 등 다수였다 — 즉 "소진"은 사실이 아니었다.

**라운드 마감 체크리스트(exploit 라운드에도 적용):**

1. 이번 라운드에 새로 알게 된 것 중 **구조에 해당하는 것**을 고른다 — 새 엔드포인트/파라미터
   이름, 확정된 서버측 동작(정규화·필터·확장자 화이트리스트), 인증·서명 스킴, 렌더링 문맥,
   응답 헤더 특성, 권한 판정 위치.
2. 그 내용을 `web-페이지-구조.md`(페이지·엔드포인트 축) 또는 `web-서버-구조.md`
   (서버 동작·인증 축)에 **실제로 반영**한다 — 둘 중 하나만이라도 확실히.
3. 반영할 게 정말 없으면(드묾) 그 사실을 일지에 적어 둔다. 다만 "공격만 하고 구조는
   안 배운 라운드"가 연속 3번 나오는 건 거의 없다 — 대개 확인만 안 했을 뿐이다.

**금지**: 무갱신 카운터를 속이려고 의미 없는 재작성(공백·날짜만 바꾸기)을 하는 것.
그러면 소진 판정 자체가 무력해져서 진짜 소진과 "내가 기록을 안 한 것"을 구별할 수 없게 된다.
판정이 틀렸다고 느껴지면 조용히 속이지 말고, 종료 시점에 그 사실(기계적 판정이었다는 것,
실제 미실증 경로 목록)을 `HANDOFF.md` 에 명시해 **사람이 계속/종료를 판단**하게 한다.

