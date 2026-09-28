# Recon(정찰) 방법론

recon의 목적은 공격이 아니라, `update-recon-summary`의 `tech_stack`을 정확히 채우는 것 —
이게 틀리면 이후 모든 RAG 검색이 엉뚱한 카테고리를 가져온다. 아래 순서로 진행하되, 0번은
항상 가장 먼저.

## 0. 실사용자 시뮬레이션 (가장 먼저)

스캐너부터 돌리지 말고, `browser`/`vision` toolset으로 메인 플로우(회원가입/로그인,
둘러보기, 검색, 결제류 플로우가 있으면 그것까지)를 실제로 클릭해서 타고 들어간다. 세 신호를
동시에 관찰:

| 관찰 대상 | 방법 | 목적 |
|---|---|---|
| 웹 소스 | DOM 확인 | 클라이언트 구조, 프레임워크 흔적 |
| 요청/응답 | mitmproxy 캡처(이미 모든 트래픽이 잡히고 있음) | API 패턴, 인증 방식, 상태 관리 |
| 화면(GUI) | 스크린샷 | 기능 단위 파악, 에러/권한 메시지 |

세 신호를 교차해서 서버 구조를 논리적으로 추론하고 `web-서버-구조.md`/`web-페이지-구조.md`에
기록한다(`update-web-structure` Skill 참고). 계정이 필요한 페이지를 만나면 자동으로 만들려
하지 말고 Mattermost로 테스트 계정을 요청한다.

## 1. 자산 발굴 — passive 우선

| 도구 | 역할 | 리스크 |
|---|---|---|
| `subfinder` | 서브도메인 열거(passive) | 낮음 |
| crt.sh / `ctfr` | 인증서 투명성 로그 기반 서브도메인 발굴 | 낮음 |
| `gau` / `waybackurls` | 웨이백머신 기반 과거 엔드포인트/파라미터 | 낮음 |
| `amass`(active) | 능동적 서브도메인 브루트포스 | 중간 — rate-limit/스코프 위반 가능, 자동화 정책 확인 후 사용 |

원칙: passive 소스부터 다 훑고, 부족할 때만 능동적 도구를 스코프 규칙 확인 후 사용. 결과는
`assets` 필드로.

## 2. 살아있는 호스트 확인 + 기술스택 지문 채취

| 도구 | 역할 |
|---|---|
| `httpx -tech-detect` | 살아있는 호스트 필터링 + `tech_stack`의 1차 소스 |
| 응답 헤더(`Server`, `X-Powered-By`) | httpx가 놓친 경우 보완 |
| 쿠키 이름(`laravel_session`, `PHPSESSID`, `JSESSIONID` 등) | 프레임워크 교차검증 |
| 기본 에러 페이지 패턴 | 프레임워크별 디폴트 페이지로 교차검증 |

헤더+쿠키+에러페이지 중 최소 2개 이상 일치해야 `tech_stack` 확정. 불확실하면
`notable_findings`에 "추정, 미확정"으로 남기고 검색은 `web/general/`만 우선 적용.

## 3. 엔드포인트/경로 탐색

| 도구 | 역할 | 리스크 |
|---|---|---|
| 알려진 프레임워크 기본 경로(Laravel `/.env`, WordPress `/wp-json/`, Spring Boot `/actuator/*`, Django `/admin/`) | `tech_stack` 확정 후 확인 | 낮음 |
| `ffuf` | 디렉토리/파라미터 퍼징 | 중간~높음 — `target-config.json`의 `automation_policy` 반드시 먼저 확인 |

## 4. 정적 분석(JS/소스맵)

| 도구 | 역할 |
|---|---|
| JS 파일 수집(`gau`/`httpx` 결과에서 `.js` 필터) + grep/nuclei js-exposure | 엔드포인트/키 패턴 노출 → `js_findings` |
| `.map` 소스맵 존재 확인 | 원본 소스 구조 노출 가능성 → `notable_findings` |

## 5. 브라우저 기반 정찰 (JS 렌더링 SPA일 때만)

1~4번은 curl 계열이라 JS로 렌더링되는 SPA의 실제 라우트/엔드포인트를 못 본다. `tech_stack`이
React/Vue/Angular 등으로 확정된 경우에만: `browser`/`vision` toolset으로 페이지 로드 후
네트워크 요청 관찰(mitmproxy 캡처로 확인), accessibility snapshot + 클릭/입력으로 로그인 후
화면 확인, 스크린샷으로 시각적 근거 확보. 1~4번보다 느리므로 SSR 사이트에서는 생략.

## 라운드 배분

`max_rounds_per_phase` 중 초반 일부를 recon 전용으로 쓰되, 정확한 비율은 아직 실측 전이라
고정 기준 없음 — 상황 봐가며 판단. exploit 라운드 중 새 표면이 드러나면 언제든 recon으로
돌아갈 수 있다(recon이 다 끝나야 exploit을 시작하는 엄격한 게이트 아님).
