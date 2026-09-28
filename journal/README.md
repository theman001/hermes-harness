# journal/

A_journal 저장소. 실제 엔게이지먼트가 시작되면 여기 `<category>/<project_id>/` 폴더가
런타임에 생김(지금은 카테고리가 항상 `web`이라 `web/<project_id>/`). 정적으로 미리
만들어두지 않음 — `colab_orchestrator/phase_start.py`가 최초 phase 시작 시 생성.

한 project 폴더 안에 쌓이는 파일들(전부 project 레벨, phase 경계와 무관하게 영속):

| 파일 | 만드는 주체 |
|---|---|
| `<date>.md` (여러 개, 라운드별) | `write-journal-entry` Skill |
| `recon_summary.json` | `update-recon-summary` Skill |
| `web-페이지-구조.md` / `web-서버-구조.md` | `update-web-structure` Skill |
| `test_account.json` | **A 자신**이 `file` 도구로 직접 씀(Mattermost 응답은 대화 컨텍스트로 A에게 옴 — phase_start.py는 대화 루프 밖에 있어서 이걸 못 받음. 전용 Skill 아님, 한 번 쓰는 단순 key-value라 기존 `file` 도구로 충분) — phase_start.py는 **로드만** 함(있으면) |
| `attempted_exploits.json` | `write-journal-entry` Skill (exploit 라운드) |
| `exhaustion_state.json` | `services/watchdog` — 웹 구조 파일 diff 무갱신 카운터(2026-09-22 정정: 원래 phase 로컬에 뒀다가 project가 여러 phase에 걸치면 카운터가 리셋되는 버그 발견, project 레벨로 이동) |
| `PoC-코드.md` / `Exploit-코드.md` / `PoC-시나리오.md` / `Exploit-시나리오.md` (+그 외) | `organize-exploit-artifacts` Skill (project 종료 시) |
| `screenshots/` | `organize-exploit-artifacts` Skill |
| `HANDOFF.md` | `services/handoff/assemble_handoff.py`의 `generate()` — 인가 맥락 프레이밍 + 이번 phase 종료 사유(3가지 분류) + 위 파일들 목록/링크를 담은 단일 진입점. **project가 끝났든 아니든 매 phase 종료마다 덮어써서 갱신**(2026-09-22 "phase 종료 != project 종료" 결정 — 최신 진행상황 초안 개념). Claude Code는 `targets/<project_id>.json`의 status가 `"done"`일 때 이 파일을 시작점 삼아 열면 나머지로 다 연결됨 |

phase 세션 로컬(mitmproxy 캡처/규칙 파일 등, phase 끝나면 삭제)은 여기가 아니라
`hermes-harness/.phase-runtime/current/`(고정 경로 — 2026-09-22 5차 재검토: 동적 ID를
A가 알 방법이 없어서 고정 이름으로 정정, phase는 한 번에 하나만 돌아서 충돌 없음. 런타임
생성, 정적 구조에 안 만들어둠) — `colab_orchestrator`/`mitmproxy_addon` 쪽 TODO 참고.
