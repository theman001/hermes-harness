# hermes-harness

`etc/`(특히 [레드블루-에이전트-실행가능성-검토.md](../etc/레드블루-에이전트-실행가능성-검토.md))에서
확정한 설계를 실제 파일/폴더로 옮긴 것. **1단계(구조) + 2단계(내용/코드) 완료** — 아래
"아직 안 된 것"만 실측(체크리스트) 대상으로 남음.

**실 서비스는 Docker + ARM64(Radxa Rock5 ITX)로 구동 예정** — 지금까지 x86_64 테스트
환경에 설치한 정찰 도구/의존성 목록과 ARM64 관련 주의사항은
[DOCKER_DEPENDENCIES.md](DOCKER_DEPENDENCIES.md)에 정리해둠(docker-compose 작성 시 참고).

## 배치 방법

- **`red/`** — 그대로 `~/.hermes/profiles/red/`에 복사(또는 심볼릭 링크)해서 씀:
  ```
  cp -r red ~/.hermes/profiles/red
  cp red/.env.example ~/.hermes/profiles/red/.env
  # .env에 HERMES_HARNESS_ROOT(이 디렉토리 절대경로)/HTTP_PROXY/HTTPS_PROXY 채우기(1회)
  cd hermes-harness && hermes --profile red chat   # 또는 -q 단일쿼리 모드
  ```
  **중요**: `journal/`, `targets/`, `tech-docs/`, `.phase-runtime/` 전부 이 `hermes-harness/`
  디렉토리 기준 상대경로로 설계돼 있음 — **A의 `terminal`/`file` 도구 작업 디렉토리가
  반드시 `hermes-harness/`여야 함**(위처럼 여기서 `hermes` 커맨드를 실행해서 보장, local
  terminal 백엔드는 통상 실행 시점의 cwd를 물려받음). `config.yaml`에 별도 working
  directory 키가 있는지는 2단계에서 확인(체크리스트 0번), 있으면 그걸로 이중 보장.
  **(2026-09-22 5차 재검토 추가, 6차에서 방식 수정)** cwd 상속만으로는 부족한 경우(MCP
  서버 프로세스 등, Hermes가 실제로 어느 디렉토리에서 띄우는지 별도 보장이 없음)를 위해
  **`HERMES_HARNESS_ROOT` 환경변수**로 이 디렉토리의 절대경로를 명시적으로 전달 —
  **배치 시 `.env`에 1회 설정**(phase마다 재설정 안 함 — `config.yaml`의 `${VAR}` 문법은
  셸 환경변수가 아니라 `.env`에서만 resolve되므로, `phase_start.py`가 셸 환경변수로
  주려던 최초 설계는 버그였음. 배치 위치는 어차피 안 바뀌는 값이라 1회 설정이면 충분).
  `config.yaml`의 `mcp.servers.rag.command`가 `${HERMES_HARNESS_ROOT}`로 이 값을 씀.
  `.phase-runtime/`도 동적 phase-session 이름 대신 **`current/`로 고정**(A가 매 라운드
  직접 확인해야 하는데 동적 이름을 알 방법이 없었음 — phase는 한 번에 하나만 도니까
  고정 이름으로 충분).
  **Mattermost 게이트웨이는 프로필별이 아니라 호스트당 하나**(2026-09-23 실측 —
  `hermes -p red gateway run`은 "Exactly one gateway per host" 에러로 거부됨, 두 프로필
  플랫폼 바인딩을 하나의 물리 프로세스가 멀티플렉싱). 기동은 `hermes gateway run`(포그라운드,
  프로필 지정 없이) 또는 `hermes gateway install`(서비스로 상시 등록) — `red` 프로필은
  `hermes gateway list`에 별도 행으로 뜨면서 같이 서빙됨. **`.env`에
  `MATTERMOST_ALLOWED_USERS`(봇에게 말 걸 수 있는 Mattermost 사용자 ID, 콤마 구분)를
  반드시 채울 것** — 비어있으면 fail-closed로 전부 거부됨(실측 중 실제로 막히는 것 확인,
  로그의 "Unauthorized user: <id>" 메시지에서 정확한 ID를 얻을 수 있음).
  **`.env`에 `MATTERMOST_REPLY_MODE=thread` 필수(2026-09-23 발견, 중요)** — 이게
  없으면(기본값 `off`) 같은 채널·같은 사용자가 보낸 메시지는 project가 달라도 전부 같은
  Hermes 세션 키로 묶여서 대화 컨텍스트가 project 경계 없이 계속 누적됨(실제로 여러
  project를 테스트하는 동안 이 문제로 컨텍스트가 안 끊긴 것 확인) — RAG DB는
  `scope_project`로 격리해놔도 **대화 컨텍스트 자체에는 그 격리가 전혀 적용 안 되므로**
  실제 서로 다른 NDA 프로그램을 같은 세션에서 다루면 정보가 샐 수 있는 심각한 문제.
  `thread` 모드에서는 새 최상위 메시지가 자기 자신을 스레드 루트로 취급해 자동으로 새
  세션이 됨 — **운영 규칙: project를 새로 시작할 땐 반드시 새 최상위 메시지로 보낼 것
  (이전 project 메시지에 스레드 답장 금지), 같은 project를 이어갈 땐 그 project의 첫
  메시지에 Mattermost "스레드로 답장"을 써서 이어갈 것.**
- **`services/`** — Hermes 밖에서 별도 프로세스로 도는 컴포넌트. Hermes 프로필 폴더에 넣지
  않음(로컬호스트에서 그냥 실행). **전용 venv 사용**(2026-09-22 결정 — 프로젝트 루트
  `.venv/`와 분리, GPU 파이프라인 의존성과 충돌 위험 원천 차단):
  ```
  cd hermes-harness && python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **`tech-docs/`, `journal/`, `targets/`** — 런타임 데이터/정적 라이브러리 위치. Hermes A와
  Claude Code 둘 다 파일시스템 경로로 직접 접근.
- **정찰 도구(terminal 백엔드 환경에 별도 설치 필요)** — `tech-docs/web/general/
  recon-methodology.md`가 전제하는 도구들(`nmap`/`ffuf`/`httpx`/`subfinder`/`gau`/
  `nuclei`/`nikto`/`gobuster`/`sqlmap`)은 하네스 코드가 아니라 **배치 환경 자체에
  설치돼 있어야 함** — 2026-09-23 실제 recon 라운드에서 전부 미설치인 걸 처음 발견함
  (문서에 나열만 돼 있었지 설치 절차가 어디에도 없었음). sudo 불필요한 것들은
  `go install`(Go 툴체인은 `https://go.dev/dl/`에서 tarball 받아 홈 디렉토리에 압축
  해제하면 sudo 없이 설치 가능)로: `httpx`/`subfinder`/`nuclei`/`gau`/`gobuster`/
  `ffuf`. `nikto`/`sqlmap`은 git clone(perl/python3 스크립트, nikto는 `cpanm`으로
  `XML::Writer` 모듈 추가 설치 필요할 수 있음). `nmap`은 `sudo apt install nmap`
  필요. `whatweb`은 이 환경에서 Debian 패키지 자체가 깨져 있어(`lib/messages.rb` 등
  파일 누락) 포기 — `httpx`가 tech-detection 1차 소스로 이미 지정돼 있어 기능 겹침.
  **중요**: 새로 설치한 도구의 PATH가 이미 떠 있는 `hermes gateway` 프로세스에는 반영
  안 됨 — 설치 후 반드시 새 셸(또는 `source ~/.bashrc`)에서 게이트웨이를 재시작할 것.

## 구조

```
hermes-harness/
├── red/                    # Hermes 프로필 그대로(A 단일 프로필)
│   ├── config.yaml         # 모델/terminal/toolset/승인/메모리 설정
│   ├── .env.example        # 비밀값 자리(API 키, 봇 토큰 등) — 실값은 .env로 별도 관리
│   ├── SOUL.md              # A의 정체성/행동규칙(소프트 제약 전부 여기)
│   ├── skills/               # write-journal-entry / update-recon-summary /
│   │                        #   update-web-structure / organize-exploit-artifacts /
│   │                        #   draft-generalized-knowledge(2026-09-23 추가)
│   └── memories/            # MEMORY.md / USER.md — 런타임에 Hermes가 채움(빈 채로 시작)
├── services/                # Hermes 밖 커스텀 컴포넌트 (etc/ 문서의 "여전히 커스텀으로
│   │                        #   만들어야 하는 것" 목록 그대로)
│   ├── harness_paths.py     # 공통 경로 헬퍼(harness_root/project_dir/phase_runtime_dir/
│   │                        #   target_config_path) — 6개 파일이 각자 중복 정의하던 걸
│   │                        #   통합(2단계 재검토로 추가)
│   ├── rag_mcp_server/      # rag_store.py(순수 로직)+server.py(MCP 래퍼)+schema.sql
│   │                        #   + test_rag_store.py (etc/RAG-스키마.md)
│   ├── colab_orchestrator/  # phase_start.py/phase_end.py — Colab 세션 + phase_loop
│   │                        #   + phase_start_local.py(Colab 없이 DeepSeek API로
│   │                        #   하네스 배관만 테스트, 2026-09-23 추가)
│   │                        #   + test_phase_start.py(`resuming` 판정 +
│   │                        #   model 엔드포인트 갱신 self-check)
│   ├── watchdog/            # round_watchdog.py + test_round_watchdog.py
│   ├── mitmproxy_addon/     # capture_addon.py(캡처+WAF감지+방식2) + proxy_rule.py(CLI)
│   │                        #   + test_capture_addon.py
│   ├── handoff/             # assemble_handoff.py (generate / request-decision)
│   ├── jev_client/          # jev_client.py(API 래퍼)+jev_log.py(호출 로깅)+
│   │                        #   server.py(MCP 래퍼)+offline_eval.py(오프라인 정확도
│   │                        #   검증)+test_jev_client.py(2026-09-28 추가)
│   └── laya_finetune/       # prepare_cwe_dataset.py(체크리스트 35(a) 공개 CWE 데이터셋
│                            #   웜스타트 변환)+test_prepare_cwe_dataset.py, data/
│                            #   (변환 결과 jsonl, 2026-09-28 추가)
├── tech-docs/web/           # 정적 기술문서 라이브러리(하이브리드 RAG의 폴더 부분)
├── tech-docs/_pending_review/ # A가 쓴 일반화 초안 스테이징(2026-09-23 추가,
│                            #   draft-generalized-knowledge Skill) — Claude Code 승격 대기
├── journal/                 # A_journal 저장소(런타임에 <project>/ 폴더가 여기 생김,
│                            #   project 레벨 — phase 경계 넘어서도 영속)
├── targets/                 # target-config.json들(project_id별 1개)
└── .phase-runtime/current/  # (런타임 생성, 정적으로 안 만들어둠, 고정 경로) phase 세션
                             #   로컬 상태 — mitmproxy 캡처/규칙/종료신호, phase 끝나면 삭제
```

## 구현 상태 (2026-09-22, 2단계 완료)

- **`red/`**: `SOUL.md`/`config.yaml`/`SKILL.md` 4개 전부 실제 내용 작성 완료.
- **`services/rag_mcp_server/`**: `rag_store.py`(순수 DB/검색 로직, `check_same_thread=
  False` + 자체 락으로 스레드 안전 — self-check `test_rag_store.py`가 다른 스레드에서의
  호출을 직접 재현해서 검증. NDA 스코프 격리도 같이 검증됨) + `server.py`(FastMCP 래퍼,
  `mcp` 패키지는 하네스 전용 venv에 설치 필요).
- **`services/watchdog/round_watchdog.py`**: 라운드 카운팅 + 소진 판정 구현, self-check
  `test_round_watchdog.py` 통과. **CONFIRMED 버그 수정(2026-09-28, `google-gruyere-
  trial` 실측 중 A가 발견)**: `_count_journal_rounds`가 `text.count("## Round ")`로
  부분문자열 매칭을 해서, A가 소제목으로 쓴 `### Round 6 후속`도 카운트에 잡혀 phase 1의
  "공격 경로 소진" 판정이 오판이었음 — 줄 시작이 정확히 `"## Round "`인 줄만 세도록
  수정, 회귀 테스트 `test_subheading_does_not_inflate_round_count` 추가(수정 전 3→
  수정 후 2로 재현 확인).
- **`services/mitmproxy_addon/`**: `capture_addon.py`(캡처+WAF감지+방식2 규칙 적용) +
  `proxy_rule.py`(add/list/remove/clear CLI, A가 `terminal`로 직접 실행하는 별도 프로세스) —
  둘 다 같은 `proxy_rules.json`/WAF 로그를 건드리므로 `harness_paths.locked_state_file()`
  (공유 `fcntl.flock`)로 **프로세스 간** 동시쓰기까지 보호(2단계 8차 재검토 — 처음엔
  `capture_addon.py` 안에서만 락을 정의해서 그 프로세스 내부 경합만 막고 있었음, 공유
  모듈로 옮겨서 실제로 고침). self-check `test_capture_addon.py`(스레드 20개로 단일
  프로세스 내부 경합 재현, `mitmproxy`는 더미 모듈로 import 우회해서 패키지 없이도 실행
  가능)와 `test_proxy_rule.py`(서브프로세스 15개로 프로세스 간 경합 직접 재현) 둘 다 통과.
- **`services/handoff/assemble_handoff.py`**: `generate`/`request-decision` 구현,
  수동 스모크 테스트 통과.
- **`services/colab_orchestrator/`**: `phase_start.py`/`phase_end.py` 구현 — `resuming`
  판정은 `test_account.json` 존재 여부가 아니라 project journal 폴더(`project_dir`)
  존재 여부로 함(2단계 9차 재검토 — 로그인 없는 타겟은 전자로 판단하면 몇 phase가
  지나도 항상 False로 잘못 판정됐음, self-check `test_phase_start.py`로 검증). 단,
  Colab↔로컬호스트 SSH 터널 확립(`colab ssh --proxy-mode`)과 실제 GPU 세션 연동은
  **아직 실측 안 됨**(체크리스트 대상, 지금은 로컬 8000 포트에 이미 떠 있다고 가정).
- **`services/colab_orchestrator/phase_start_local.py`**: Colab CU 회복 전까지 DeepSeek
  공식 API(`deepseek-chat`, tool-calling 정상 지원)를 임시 모델 백엔드로 붙여서 GPU/Colab과
  무관한 하네스 배관(승인 게이트웨이/Skill 4개/MCP rag 서버/mitmproxy/round_watchdog/
  handoff) 전체를 로컬에서 검증하기 위한 스크립트. `phase_start.py`의 Colab 무관 함수들
  (`step0_prepare`/`step2b_start_phase_runtime`/`step2c_start_watchdog`/
  `step3_update_model_endpoint`/`step4_start_hermes_conversation`)을 그대로 재사용하고
  `step1_colab_new`/`step2_colab_install_and_serve`만 건너뜀. **반드시 로컬 연습용 취약
  앱(DVWA/Juice Shop 등)을 `mode: "own_system"`으로 테스트할 것** — 실제 버그바운티
  대상 정보를 DeepSeek 클라우드로 보내면 안 됨(스크립트 자체 docstring에 경고 포함). 부수
  효과로 `.claude/PROGRESS.md`(2026-09-17)에 기록된 "실제 배포 모델이 OpenAI 스타일
  tool_calls를 아예 생성 안 함" 문제와, 지금의 하네스 도구 호출 설계가 실제로 맞물려
  동작하는지도 분리해서 확인 가능(tool-calling 지원되는 모델로 먼저 하네스 자체를
  검증). `step3_update_model_endpoint`는 이 스크립트를 위해 `base_url`/`api_key`
  옵션 인자를 추가하도록 확장(기존 Colab 경로는 그대로 `model_id`만 갱신, 미지정 필드는
  안 건드림 — `test_phase_start.py`의 새 테스트로 두 경로 다 검증).
- **`services/jev_client/`(2026-09-28 추가, 체크리스트 34)**: `jev_client.py`(표준
  라이브러리 urllib만 사용, `TYPESAFE_API_KEY` 없으면 `JevKeyMissing`으로 명확히
  실패) + `offline_eval.py`(이미 끝난 project의 `recon_summary.json` 후보 목록을
  `PoC-코드.md`의 확정 취약점 경로와 대조해서 Jev 정확도를 오프라인으로 재는 스크립트,
  API 키 없으면 자동 dry-run). **실제 `testasp-vulnweb-full` 데이터로 dry-run 실행
  확인** — 31개 후보 중 8개 경로가 `PoC-코드.md`와 정확히 매칭됨(`/showforum.asp`,
  `/register.asp` 등).
  **라이브 통합 완료(같은 날, API 키 발급 후)**: `jev_log.py`(호출마다
  `journal/web/<project_id>/jev_calls.jsonl`에 {state,questions,answer} 자동 기록 —
  체크리스트 34 로깅 훅 전제조건 + 35(b) 파인튜닝 원재료를 동시에 해결) +
  `server.py`(FastMCP 래퍼, `rag_mcp_server`와 동일 패턴 — **하네스 venv에서 실제
  빌드 성공 확인**). `red/config.yaml`의 `mcp_servers.jev`로 등록, `red/SOUL.md`에
  사용 규칙(공격지점/기법 우선순위 참고용 한정, PoC 코드는 여전히 A 작성, 승인 절차
  우회 불가, 실패 시 자기판단으로 폴백 — 가산적 설계) 추가.
  **라이브 실측 완료**: `testphp-vulnweb-test` 첫 실행에서 Jev가 한 번도 호출 안 됨
  (0회) — SOUL.md가 "애매하면 참고"로 재량에 맡겨서 A가 스스로 분석을 끝낸 뒤엔 항상
  "명확하다"고 판단, 트리거가 실질적으로 죽어있었음. **SOUL.md를 "exploit 라운드마다
  필수, 분석 전에 먼저 호출"로 순서 반전** 후 `testasp-vulnweb-jev-trial`(동일
  대상, 신규 project)로 재검증 — 4회 호출, exploit 라운드(1~3) 전부 준수 확인,
  Jev 순위가 2라운드 다 실제 결과와 일치(일화적 수준, 통계적 근거 아님).
  **CONFIRMED 버그(같은 실행에서 발견)**: `jev_calls.jsonl` 동시쓰기로 레코드가
  개행 없이 이어붙음 — `harness_paths.locked_state_file("jev_calls")` 락 추가로 수정,
  `test_jev_client.py`에 30스레드 회귀 테스트 추가(단, 정확한 레이스 재현은 실패 —
  프로덕션 증거 기반으로 방어적 적용).
- **`services/laya_finetune/`(2026-09-28 추가, 체크리스트 35(a))**:
  `prepare_cwe_dataset.py` — `Dunateo/VulnDesc_CWE_Mapping`(HF, 2601건)을
  datasets-server REST API로 받아 SOUL.md 기준 웹 공격 기법 12개 카테고리로 매핑,
  Laya 파인튜닝 스키마({state,questions,gold} JSONL)로 변환. **실제 실행 완료**:
  1187건 채택(1414건은 도메인 밖 CWE라 폐기), `data/cwe_warmstart.jsonl`에 저장.
  카테고리 분포가 불균형함(rce/xss/sqli 200개대 vs xxe 4건) — 실제 파인튜닝 시 클래스
  불균형 대응 필요할 수 있음, 지금은 준비 단계라 그대로 둠.

## 아직 안 된 것 (실측/체크리스트 대상)

**다음 세션 최우선 — 실제 Hermes 설치 후 실측(2026-09-23)으로 발견, 승인 흐름 일부를
다시 설계해야 함(자세한 경위는 `.claude/PROGRESS.md` 2026-09-23 항목 참고). Mattermost
승인 왕복 자체는 라이브 테스트로 정상 동작 확인됨(`curl | sh`를 Mattermost로 실제
승인 요청 → `/deny` 응답 → A가 정확히 차단·보고) — 아래는 그 왕복 메커니즘을 어떻게
우리 두 커스텀 스크립트에도 타게 만들지, 그리고 무인 실행 모드를 어떻게 바꿀지의 문제:**

- **`approvals.deny`는 "승인 요청" 게이트가 아니라 영구적으로 우회 불가능한 하드
  블록**(소스 `tools/approval.py`의 `check_dangerous_command` 흐름으로 확인) — 지금
  `proxy_rule.py add*`/`assemble_handoff.py request-decision*`를 이 목록에 넣어둔 건
  "승인받으면 실행됨"이 아니라 "영원히 실행 불가능"을 의미함. 이 두 스크립트는
  Hermes 자체 내장 위험 패턴(`DANGEROUS_PATTERNS_COMPILED`, 하드코딩돼 있어 config로
  커스텀 추가 불가)에도 안 걸려서, `deny`에서 빼면 이번엔 반대로 승인 절차 없이 조용히
  실행돼버림. 해결 방향 두 가지 중 택1 필요: (a) `pre_tool_call` 훅으로
  `request_tool_approval()`을 호출하는 Hermes 플러그인을 새로 작성 — 이 함수가 라이브로
  방금 확인한 것과 **동일한** 인간 승인 게이트를 재사용한다는 게 소스로 확인됐으므로
  실현 가능성 높음, (b) Hermes 승인 시스템을 안 쓰고 이 두 스크립트가
  `MATTERMOST_TOKEN`으로 직접 Mattermost에 승인 요청을 올리고 응답을 폴링하는 자체
  메커니즘 구현.
- **`-q`(single-query) 모드는 승인 왕복이 구조적으로 불가능**(소스
  `tools/approval_context.py`로 확인 — `approvals.single_query_mode` 고정값으로
  즉시 deny/approve 결정, 응답 대기 자체가 없음) — `phase_start.py`가 계획한
  `hermes --profile red -q "..."` 무인 실행 방식으로는 Mattermost 왕복이 필요한
  체크포인트가 전부 작동 안 함. `hermes gateway`(호스트당 하나, 위 "배치 방법" 참고)
  처럼 세션이 끊기지 않는 방식으로 바꿔야 함 — phase_start.py가 지금처럼 `-q`로 대화를
  시작하는 대신, 상시 떠 있는 게이트웨이에 메시지를 보내는 방식으로 재설계 필요.
- **`AUXILIARY_APPROVAL_BASE_URL`/`AUXILIARY_APPROVAL_MODEL` 미설정 상태로 확인됨**
  (체크리스트 0(g), 여전히 미해결) — 라이브 테스트 중 "Auxiliary Nous client
  unavailable" 경고가 반복 발생, guardian 호출 실패 시 안전하게 escalate(사람에게
  물어봄)로 fallback해서 지금은 문제 없었지만, 이대로면 smart 모드의 "저위험은 자동
  승인" 기능이 사실상 죽어있어 모든 플래그된 명령이 사람에게 감. 값을 채워야 smart
  모드가 원래 의도대로(저위험 자동 통과) 작동하는지 검증 가능.
- **`MATTERMOST_ALLOWED_USERS` 등록 필요**(이미 위 "배치 방법"에 반영, 여기 재언급 —
  안 채우면 봇에게 말 거는 사람 전부 거부됨).

**2026-09-23 라이브 recon 라운드로 확인됨 — 하네스 아키텍처(Skill/승인게이트/journal/
mitmproxy/watchdog)가 실전에서 정상 완주**: `testasp.vulnweb.com` 대상 5라운드에서
실제 취약점 5건(크리티컬 1건 포함) 확정, 소스 근거 확보, 승인 게이트도 정상 트리거됨
(자세한 내용 `.claude/PROGRESS.md` 참고). 이 과정에서 아래 항목들도 갱신됨:

- ~~`mcp.servers.*.command` 필드 안에서 `${VAR}` 치환이 실제로 되는지 미확인~~ →
  **완전히 해결됨(2026-09-23, 근본 원인까지 확정)**. 경로 절대화(`mcp<2` 고정 포함)는
  전부 필요했던 수정이지만, **A가 라이브 recon 중 `hermes --profile red mcp list` →
  "No MCP servers configured."를 직접 확인** — `config.yaml`의 `mcp: servers: rag:
  {transport, command}` 블록 자체가 **Hermes가 아예 안 읽는 가짜 스키마**였음(실제
  등록은 `hermes mcp add <name> --command <cmd> --env KEY=VALUE --args <script>`로
  해야 함, `--args`가 "must be the last option"이라 `--env`는 반드시 그 앞에 와야
  함 — 순서 실수로 한 번 실패 재현). 그 명령이 실제로 쓰는 스키마는 최상위
  `mcp_servers:`(언더스코어, `mcp:` 중첩 아님) + `command`(문자열)/`args`(리스트)/
  `env`(딕셔너리)/`enabled` — `red/config.yaml`을 이 스키마로 전면 교체하고
  `${HERMES_HARNESS_ROOT}` 치환도 이 새 스키마에서 실제로 되는 것까지 재확인(`hermes
  mcp test rag` → 5개 도구 정상 발견). 이전까지 고쳤던 venv 절대경로/`mcp<2`는 애초에
  Hermes가 그 설정 자체를 안 읽고 있었으니 전부 무의미했던 것 — 스키마 자체가 근본
  원인.
- **`browser` toolset — CDP 연결은 됨, HTTP 전용 대상 로드 문제 원인 확정+임시 값
  추가(미검증)**: sudo로 설치한 뒤 A가 직접 확인 — CDP 자체는 정상(about:blank JS
  실행, 스크린샷 성공). 그런데 **HTTP-only 대상(HTTPS 없음, 우리 테스트 대상 포함)이
  전부 `net::ERR_BLOCKED_BY_CLIENT`** — Chrome의 HTTPS-Upgrade 계열 기능이 원인,
  `--disable-features=HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode`로
  A가 원시 chrome에서 우회 성공 확인. 하네스 레벨 반영을 위해 `agent-browser`가
  읽는 `AGENT_BROWSER_ARGS` env var에 이 값을 넣어둠(`.env`) — **미검증**: 이 값
  자체에 콤마가 포함돼 있어서 `AGENT_BROWSER_ARGS`의 바깥쪽 콤마 분리 로직과
  충돌할 수 있음, 다음 라운드에서 실제로 HTTP 대상이 열리는지 확인 필요. 이번
  라운드는 CDP `Page.captureScreenshot` 직접 호출로 우회해서 스크린샷 4장 확보함
  (A 자체 제작 스크립트, `scratch/cdp_shot.py`).
- **`cronjob` 비활성화 — A에게 직접 물어봐서 확인 완료**: `tool_search` 매치 0건 +
  `config.yaml`의 `agent.disabled_toolsets`에 `cronjob` 명시 확인 — 기대대로 부재.
  (`hermes doctor`의 "Tool Availability" 목록이 profile별 설정을 반영 안 한다는
  점은 여전히 유효하니, 이 방법 — A에게 직접 tool_search로 물어보기 — 을 표준
  확인 절차로 채택.)
- Colab↔로컬호스트 네트워크 연결 실제 확립(장시간 스트리밍 안정성 포함).
- 임베딩 모델 선정(RAG-스키마.md "남은 확인 사항") — 그 전까지 `rag_store.py`는 의존성
  없는 폴백(`_naive_embed`, 어휘 중복 기반)으로 동작.
- 나머지 GPU 필요 체크리스트 항목 전체(0~33번, `레드블루-에이전트-실행가능성-검토.md` 참고).

## Docker 배포 (Radxa Rock5 / OpenMediaVault 8)

**2026-09-28부터 Colab은 홀드, DeepSeek API + Jev API 조합이 메인 배포 형태다** —
`phase_start_local.py`가 (이름과 달리) 주 실행 경로, `phase_start.py`(Colab 경로)는
Colab CU 재개 시 대안으로 남겨둠. 이 리포는 원래 `llm-abliteration` 모노레포의
서브폴더였다가, 배포 편의를 위해 2026-09-28에 별도 리포로 분리됐다(과거 이력/전체
결정 근거는 원본 모노레포의 `.claude/PROGRESS.md`/`etc/` 참고 — 이 리포엔 안 옮김).

**배치 절차(OMV8 GUI, "Compose" 플러그인)**:
1. 이 리포를 GitHub에서 **잠깐 public으로 토글**한다(`docker-compose.yml`의
   `build.context`가 git URL이라 private면 인증 없이 clone 실패 — `.env`/시크릿은
   git에 안 올라가 있으므로 이 토글 자체엔 노출 리스크 없음, `DOCKER_DEPENDENCIES.md`
   7번 참고).
2. Claude Code에게 실제 값을 채운 `docker-compose.yml`을 요청해서 받는다(이 파일 자체는
   `CHANGE_ME_*` 플레이스홀더뿐이라 그대로 쓰면 안 됨).
3. 그 결과물을 OMV8 GUI의 Compose 스택 생성 화면에 그대로 붙여넣고 "Up".
4. 빌드가 끝나면(수 분~수십 분, ARM64라 Go 도구 빌드가 느릴 수 있음) 리포를 다시
   private으로 되돌려도 된다 — 이미지는 이미 로컬에 빌드돼 있어서 재기동 시 다시
   clone할 필요 없음(코드를 바꿔서 재빌드할 때만 다시 public 토글 필요).
5. 새 project를 시작할 땐 여전히 수동으로 `docker exec hermes-harness
   /opt/hermes-harness/.venv/bin/python
   /opt/hermes-harness/services/colab_orchestrator/phase_start_local.py <project_id>`
   실행 필요(phase 시작은 항상 명시적 트리거라는 기존 설계 그대로 — SOUL.md 참고).

**HDD 마운트(아직 안 붙임, 나중을 위한 설계)**: `docker-compose.yml`의 모든
`volumes:` 항목이 `/srv/hermes-data` 접두사로 통일돼 있다 — HDD가 붙으면 그 문자열을
새 마운트 경로로 전체 치환하고 다시 Up하면 기존 journal/RAG/mitmproxy CA 등이 그대로
이전된다(`entrypoint.sh`가 이 경로를 `HERMES_DATA_ROOT` 환경변수로 읽음).

**ARM64 미검증 리스크** — `DOCKER_DEPENDENCIES.md`의 "ARM64 관련 알려진 리스크 요약"
순서대로 처음 빌드/기동 시 확인할 것(Playwright Chromium, mitmproxy의 cryptography
Rust 빌드, Go 도구 빌드 시간, whatweb, Hermes 설치 스크립트 자체의 ARM64 지원 — 전부
실기기에서 한 번도 안 돌려봤다).

진행 상황/결정 이력은 원본 모노레포(`llm-abliteration/.claude/PROGRESS.md`)에 있다.
