"""핸드오프 템플릿 — AI 판단 없는 단순 조립 스크립트 + project 종료/계속 결정 요청.

근거: etc/레드블루-에이전트-실행가능성-검토.md 체크리스트 19번,
"Project 종료 시 산출물 정리" 결정, "핸드오프 무결성" 결정,
"phase 종료 != project 종료" 결정(Option C).

핵심 전제: phase가 끝난다고 project가 끝난 게 아니다(project는 여러 phase에 걸칠 수
있음). 그래서 매 phase 종료마다 (1) 항상 실행되는 초안 생성/갱신(generate, 승인 불필요),
(2) 사람에게 "여기서 끝낼지 계속할지" 물어보는 request-decision(approvals.deny 등록
대상, 승인 필수)을 분리해서 둔다.

사용:
    python assemble_handoff.py generate <project_id>
    python assemble_handoff.py request-decision <project_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import phase_runtime_dir, project_dir, target_config_path  # noqa: E402

EXPECTED_ARTIFACTS = [
    "PoC-코드.md",
    "Exploit-코드.md",
    "PoC-시나리오.md",
    "Exploit-시나리오.md",
]

REASON_TEXT = {
    (True, True): "① 최대 라운드 도달 AND 공격 경로 소진 — 더 확인할 거 없음",
    (False, True): "② 공격 경로 소진, 최대 라운드는 미도달 — 더 이상 공격할 경로 없음",
    (True, False): "③ 최대 라운드 도달, 공격 경로는 아직 남음 — 예산만 소진",
    (False, False): "④ 사유 불명 — 수동/외부 중단으로 추정",
}


def _load_termination_reason() -> dict | None:
    path = phase_runtime_dir() / "termination_reason.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_target_config(project_id: str) -> dict:
    path = target_config_path(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def reason_text(reason: dict | None) -> str:
    if reason is None:
        return REASON_TEXT[(False, False)]
    key = (bool(reason.get("max_rounds_reached")), bool(reason.get("attack_exhausted")))
    return REASON_TEXT[key]


def generate(project_id: str) -> Path:
    """항상 실행, 승인 불필요 — HANDOFF.md를 매번 새로 씀(덮어쓰기, "최신 초안" 개념)."""
    pdir = project_dir(project_id)
    pdir.mkdir(parents=True, exist_ok=True)
    target = _load_target_config(project_id)
    reason = _load_termination_reason()

    program_name = target.get("target", {}).get("program_name", project_id)
    mode = target.get("mode", "unknown")

    if mode == "bug_bounty":
        framing = (
            f"아래는 **{program_name}**의 승인된 버그바운티 엔게이지먼트 작업 일지입니다. "
            f"`targets/{project_id}.json`에 명시된 스코프/규칙 안에서 수행됐습니다."
        )
    else:
        framing = (
            f"아래는 자체 시스템 **{program_name}**에 대한 승인된 보안 점검 작업 일지입니다."
        )

    missing = [f for f in EXPECTED_ARTIFACTS if not (pdir / f).exists()]
    integrity_note = (
        "모든 예상 산출물이 존재합니다." if not missing
        else f"**주의**: 아래 파일이 아직 없습니다 — {', '.join(missing)} "
             f"(organize-exploit-artifacts가 아직 못 만들었을 수 있음, 확인 필요)."
    )

    existing_files = sorted(
        p.name for p in pdir.iterdir()
        if p.is_file() and p.name != "HANDOFF.md"
    )
    file_list = "\n".join(f"- [{name}]({name})" for name in existing_files)

    content = f"""# 핸드오프 — {project_id}

{framing}

**이번 phase 종료 사유**: {reason_text(reason)}

**무결성 확인**: {integrity_note}

## 포함된 파일

{file_list}

---
*생성 시각: {datetime.now(timezone.utc).isoformat()} — 매 phase 종료마다 이 파일 전체가
새로 갱신됩니다(이전 내용은 안 남음). project가 실제로 끝났는지는
`targets/{project_id}.json`의 `status` 필드를 확인하세요("done"이면 종료).*
"""
    out_path = pdir / "HANDOFF.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def request_decision(project_id: str) -> None:
    """approvals.deny 등록 대상 — Mattermost 승인 필요.

    이 함수 자체는 status를 쓰지 않는다(A가 Mattermost 응답을 대화 컨텍스트로 받아서
    `file` 도구로 직접 쓴다 — SOUL.md 참고). 여기서는 승인 요청에 필요한 메시지 내용만
    구성해서 표준출력으로 낸다(Hermes의 Mattermost 게이트웨이가 approvals.deny 매칭 시
    이 커맨드의 실행을 승인 대기시키고, 승인되면 그대로 진행되는 구조 — 실제 알림 발송은
    Hermes 승인 엔진이 처리하므로 이 스크립트는 승인 대상이 되는 것 자체가 역할).
    """
    handoff_path = project_dir(project_id) / "HANDOFF.md"
    reason = _load_termination_reason()
    summary = handoff_path.read_text(encoding="utf-8") if handoff_path.exists() else \
        "(HANDOFF.md 없음 — 먼저 generate를 실행하세요)"

    message = (
        f"[Project 종료/계속 결정 요청] {project_id}\n"
        f"종료 사유: {reason_text(reason)}\n\n"
        f"이 project를 여기서 끝내고 Claude Code로 넘길까요, 아니면 다음 phase를 예약해서 "
        f"계속할까요?\n\n--- HANDOFF.md 요약 ---\n{summary[:2000]}"
    )
    print(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("project_id")

    p_dec = sub.add_parser("request-decision")
    p_dec.add_argument("project_id")

    args = parser.parse_args()
    if args.command == "generate":
        path = generate(args.project_id)
        print(f"HANDOFF.md 갱신됨: {path}")
    elif args.command == "request-decision":
        request_decision(args.project_id)


if __name__ == "__main__":
    main()
