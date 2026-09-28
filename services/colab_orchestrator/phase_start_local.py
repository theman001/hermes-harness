"""Phase 시작 — Colab 없이 로컬에서 (2026-09-23 추가).

Colab CU 소진 등으로 GPU 세션을 못 띄우는 동안, 하네스 배관(승인 흐름/Skill/MCP/
mitmproxy/round_watchdog/handoff)이 실제로 동작하는지 DeepSeek 공식 API를 임시
모델 백엔드로 붙여서 검증하기 위한 것 — `phase_start.py`와 GPU/Colab 관련 없는
부분(mitmproxy 기동, watchdog 기동, phase_state 저장, model 엔드포인트 갱신, Hermes
대화 시작 메시지)을 그대로 재사용하고 `step1_colab_new`/`step2_colab_install_and_serve`
(Colab 전용)만 건너뛴다.

**주의 — 이걸로 검증되는 것과 안 되는 것**:
- 검증됨: Hermes 프로필/toolset/승인 게이트웨이/MCP rag 서버/Skill 4개/mitmproxy 캡처·
  WAF·방식2/round_watchdog 소진 판정/assemble_handoff 전체 흐름 — 전부 모델과 무관.
- 검증 안 됨: abliteration 자체의 거절률(DeepSeek 공식 API는 안전정렬돼 있어 당연히
  다름). 이건 이 스크립트의 목적이 아니다.
- **부가로 확인할 가치가 있는 것**: `.claude/PROGRESS.md`(2026-09-17)에 실제 배포 모델
  (`9theman9/deepseek-r1-distill-qwen-32b-heretic`, `transformers serve`)이 OpenAI
  스타일 `tools`/`tool_calls`를 아예 생성하지 않고 텍스트로만 답했다는 기록이 있다 —
  Hermes의 도구 호출이 표준 tool-calling 프로토콜에 의존한다면 이건 하네스 버그가
  아니라 그 모델 자체의 호환성 문제일 수 있다. DeepSeek 공식 API(`deepseek-chat`)는
  정상적으로 tool_calls를 지원하므로, 이 스크립트로 먼저 "하네스가 tool-calling이
  되는 모델과는 의도대로 동작하는가"를 확인해두면 나중에 실제 모델을 다시 붙였을 때
  안 되는 원인이 하네스 쪽인지 모델 쪽인지 분리해서 판단할 수 있다.

**테스트 대상은 반드시 로컬에 직접 띄운 연습용 취약 앱(DVWA/OWASP Juice Shop 등)이나
PortSwigger Academy 랩으로** — `target-config.json`의 `mode`를 `"own_system"`으로
설정해서 안전정렬된 API가 "인가된 자체 시스템 점검"으로 인식하게 할 것. 실제 제3자
버그바운티 대상에 이 모드로 접근하지 말 것(대상 정보가 DeepSeek 클라우드로 나가는
것 자체가 NDA 위반일 수 있음 — 이 위험 때문에 원래 하네스는 Colab 자체 호스팅 모델만
쓰도록 설계됐다는 걸 잊지 말 것, 이 스크립트는 어디까지나 임시 배관 테스트용).

**실측으로 정정(2026-09-23, 실제 대화 시도)**: named provider(`deepseek`)도 config.yaml에
남아있는 `base_url`/`api_key`가 있으면 그 값이 provider 내장 기본값보다 우선 적용된다 —
처음엔 "named provider니까 base_url/api_key를 안 건드려도 되겠지"라고 가정했다가, 실제로
Colab용 `base_url: "http://localhost:8000/v1"`이 그대로 남아있어서 DeepSeek API 대신
존재하지도 않는 로컬 8000 포트로 요청을 보내 502로 실패하는 것까지 직접 확인함 — 그래서
세 필드(`provider`/`base_url`/`api_key`) 전부 명시적으로 갱신한다. 모델 이름도 마찬가지로
실측: `deepseek-chat`/`deepseek-reasoner`는 Hermes가 내부적으로 `deepseek-flash`로
정규화하는 구버전 별칭(DeepSeek의 2026-09 Flash 개편) — 처음부터 `deepseek-flash`를 쓴다.

사용: python phase_start_local.py <project_id> [--model deepseek-flash]
"""

from __future__ import annotations

import argparse

import phase_start as ps

DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                         help="DeepSeek 모델 이름(예: deepseek-flash, deepseek-v4-pro)")
    args = parser.parse_args()

    config = ps.step0_prepare(args.project_id)
    resuming = ps.is_resuming_project(args.project_id)
    max_rounds = config.get("max_rounds_per_phase", 30)

    print("!! Colab 단계(colab new/install/serve) 건너뜀 — 로컬 테스트 모드")
    mitmdump_pid = ps.step2b_start_phase_runtime()
    watchdog_pid = ps.step2c_start_watchdog(args.project_id, max_rounds)
    # session_name=None — phase_end.py가 이걸 보고 `colab stop` 호출을 건너뛴다.
    ps._save_phase_state(None, mitmdump_pid, watchdog_pid)

    ps.step3_update_model_endpoint(
        args.model, provider="deepseek", base_url=DEFAULT_BASE_URL,
        api_key="${DEEPSEEK_API_KEY}",
    )
    print("!! .env에 DEEPSEEK_API_KEY=<실제 DeepSeek API 키>가 설정돼 있는지 확인할 것")

    ps.step4_start_hermes_conversation(args.project_id, resuming)

    print(f"\n로컬 테스트 phase 시작 완료: project={args.project_id}, model={args.model}")
    print(f"종료 시 phase_end.py {args.project_id} 실행할 것 "
          f"(colab stop은 자동으로 건너뜀 — session_name 없음)")


if __name__ == "__main__":
    main()
