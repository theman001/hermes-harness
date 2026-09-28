# 신규 타겟 생성 프롬프트 (재사용용)

이 파일 내용을 그대로 복사해서 Claude Code에 붙여넣고, 그 아래에 **① 버그바운티 프로그램
페이지 원문(스코프/정책 나온 부분 전체)을 그대로 붙여넣거나, ② 도메인 하나만** 적으면
`targets/<project_id>.json`을 만들어준다. 스키마 근거: `targets/example-corp-2026-09.example.json`,
`etc/RAG-스키마.md`.

---

## 프롬프트 시작

너는 이 프로젝트(`hermes-harness`)의 `targets/<project_id>.json` 파일을 새로 만드는 역할이다.
아래 입력을 보고 두 가지 모드 중 하나로 판단해라.

### 입력 판별
- **입력이 웹페이지에서 긁어온 덩어리 텍스트**(스코프 표, 정책 문구, 보상 테이블, "In scope"/
  "Out of scope" 같은 섹션이 보임) → **버그바운티 모드**.
- **입력이 도메인/URL 하나뿐**(그 외 맥락 없음) → **own_system 모드**.
- 애매하면 먼저 물어봐라(추측해서 진행하지 마라 — 특히 스코프/자동화 정책은 잘못 읽으면
  실제 사고로 이어진다).

### 버그바운티 모드 — 원문에서 추출할 것
1. **`program_name`**: 프로그램/회사 이름.
2. **`platform`**: hackerone / bugcrowd / yeswehack / intigriti / 자체운영이면 `none`.
   URL이나 페이지 브랜딩에서 판단.
3. **`scope.in_scope_domains` / `scope.out_of_scope_domains`**: 스코프 표/목록을 **글자
   그대로** 옮긴다 — 요약하거나 일반화하지 마라(`*.example.com`처럼 와일드카드가 있으면
   그대로, 서브도메인 하나하나 적혀있으면 그대로 리스트로).
4. **`rules_url`**: 정책 페이지 자체의 URL(사용자가 원문과 같이 URL을 안 줬으면 빈 문자열로
   두고 "rules_url 직접 채워달라"고 표시해라 — 지어내지 마라).
5. **`reward_table_url`**: 별도 보상 테이블 페이지가 있으면 그 URL, 없으면 빈 문자열.
6. **`automation_policy`** — **가장 신중하게 볼 것**:
   - `prohibits_automation`: "자동화 금지", "no automated scanning", "scanners not allowed",
     "manual testing only" 같은 문구가 있으면 `true`. 명시적으로 허용한다는 문구가 있으면
     `false`. **아무 언급이 없으면 `true`로 보수적으로 잡아라**(허용 문구가 없다=허용 아님,
     이게 안전한 기본값).
   - `prohibits_third_party_ai_sharing`: "제3자 도구/AI에 대상 정보 공유 금지" 계열 문구가
     있으면 `true`. 이 값이 `true`면 이 프로젝트는 **DeepSeek API/Jev API를 못 쓴다**(둘 다
     제3자 클라우드) — 발견하면 반드시 사용자에게 이 사실을 짚어줘라.
   - `notes`: 위 두 판단의 근거가 된 원문 문구를 그대로 인용해서 남겨라(나중에 재확인 가능하게).
7. **`vpn`**: VPN 연결이 필요하다는 문구(사설 프로그램 초대 메일 등)가 있으면
   `required: true`+ 프로그램명을 `profile_name`에, 없으면 `required: false, profile_name: null`.
8. **`mode`**: `"bug_bounty"`.

### own_system 모드 — 도메인만 줬을 때
1. **먼저 사용자에게 확인**: "이 도메인이 본인 소유 시스템이거나 이미 테스트 허가를 받은
   대상인가?"를 짧게 물어봐라 — 도메인 문자열 하나만으로는 권한이 있다는 보장이 없다.
   확인(또는 이미 이 대화에서 명백히 확인된 경우 — 예: 이전에 이미 논의된 자체 시스템)되면
   진행.
2. `program_name`: 도메인 이름 + "(own_system)" 같은 짧은 설명.
3. `platform: "none"`, `scope.in_scope_domains: [그 도메인]`, `out_of_scope_domains: []`.
4. `rules_url`: `http://<도메인>/` 정도로 채우거나 빈 문자열.
5. `automation_policy`: `prohibits_automation: false, prohibits_third_party_ai_sharing: false`
   + `notes`에 "own_system, 자동화 제약 문서화된 바 없음 — 사용자 확인 하에 own_system으로
   지정" 같은 근거를 남겨라.
6. `vpn: {required: false, profile_name: null}`.
7. `mode: "own_system"`.

### 공통 — 나머지 필드
- **`project_id`**: `<대상slug>-<짧은 목적>` 형태(예: `example-corp-2026-09`,
  `testasp-vulnweb-jev-trial`). **먼저 `targets/` 폴더의 기존 파일명과 안 겹치는지
  확인해라.** 한번 정하면 이후 이 project의 모든 파일 경로에 이 문자열을 한 글자도
  안 줄이고 그대로 써야 한다(`journal/web/<project_id>/...`) — 실제로 축약해서 사고
  난 적 있음(SOUL.md 참고).
- **`category`**: 지금은 항상 `"web"`(다른 값은 아직 코드가 안 읽음 — `_category_note`
  참고).
- **`max_rounds_per_phase`**: 사용자가 안 정해주면 20을 기본값으로 제안(공격 경로 자연
  소진이 라운드 상한보다 먼저 오게 하려는 의도, 너무 작으면 워치독이 조기 종료 오판할
  수 있음).
- **`status`**: `"active"`(바로 쓸 수 있게).

### 출력
1. 위 스키마 그대로 `targets/<project_id>.json` 파일을 만들어라(아래 예시와 정확히 같은
   필드 구조, `_comment`에 이 파일을 만든 근거/원문에서 못 찾은 값이 있으면 그것도 명시).
2. **파일을 쓰기 전에** 추출한 핵심 사실(스코프 도메인 목록, `automation_policy` 판단과
   근거 문구, VPN 필요 여부)을 사용자에게 요약해서 보여주고 확인을 받아라 — 스코프/자동화
   정책을 잘못 읽으면 실제 사고(스코프 밖 테스트, 금지된 자동화)로 이어질 수 있는 항목이라
   조용히 확정하지 마라.

### 스키마 예시
```json
{
  "_comment": "이 프로젝트를 어떻게/왜 이렇게 채웠는지, 원문에서 못 찾은 값이 있으면 명시",
  "project_id": "example-corp-2026-09",
  "category": "web",
  "mode": "bug_bounty",
  "target": {
    "program_name": "Example Corp Bug Bounty",
    "platform": "hackerone",
    "scope": {
      "in_scope_domains": ["*.example.com", "api.example.com"],
      "out_of_scope_domains": ["blog.example.com", "status.example.com"]
    },
    "rules_url": "https://hackerone.com/example/policy",
    "reward_table_url": "https://hackerone.com/example",
    "automation_policy": {
      "prohibits_automation": false,
      "prohibits_third_party_ai_sharing": false,
      "notes": "원문 인용 근거"
    },
    "vpn": {"required": false, "profile_name": null}
  },
  "max_rounds_per_phase": 20,
  "status": "active"
}
```

## 프롬프트 끝 — 아래에 원문 또는 도메인을 붙여넣을 것
