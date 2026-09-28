"""Phase 종료 오케스트레이션.

근거: etc/레드블루-에이전트-실행가능성-검토.md phase_loop 5~7단계 +
"phase 종료 != project 종료" 결정(Option C).

핵심 전제: phase가 끝나는 것과 project가 끝나는 것은 다른 사건. 종료조건(공격 경로 소진
또는 최대 라운드 도달)이 걸리면 이 phase는 끝나지만, project 자체를 끝내고 Claude Code로
넘길지는 매번 사람에게 물어본다(request-decision, Mattermost 승인) — 시스템이 "진짜 다
찾았는지"를 스스로 오분류할 위험이 있어서 자동 분류 대신 항상 사람 판단.

**5, 5.5번(산출물 정리 + 결정 요청)은 A 자신이 Hermes 대화 안에서 Skill/커맨드로 수행한다**
(organize-exploit-artifacts Skill 호출, assemble_handoff.py generate/request-decision
호출) — 이 스크립트는 **그 이후, A의 Hermes 세션이 끝난 뒤** 6~7번(cleanup + 상태 확인)만
담당한다. 즉 이 스크립트를 실행하는 시점엔 이미 request-decision의 Mattermost 승인/거부가
끝나 있고 `targets/<project_id>.json`의 status가 "done" 또는 "paused"로 갱신돼 있어야
한다.

사용: python phase_end.py <project_id>
(session_name/PID는 phase_start.py가 남긴 .phase-runtime/current/phase_state.json에서
자동으로 읽음 — 2단계 검토로 수정: 원래 session_name을 수동 인자로 받았는데, 그러면
운영자가 phase_start.py 출력에서 세션 이름을 손으로 옮겨 적어야 하는 번거로움이 있었음.
같은 이유로 프로세스 종료도 pgrep 패턴매칭 대신 저장해둔 정확한 PID로 함 — 패턴매칭은
같은 이름의 무관한 프로세스까지 죽일 위험이 있었음.)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import harness_root, phase_runtime_dir, target_config_path  # noqa: E402


def _run(cmd: list[str], **kwargs) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=False, **kwargs)  # check=False: 이미 죽은 세션이어도 cleanup은 계속


def _load_phase_state() -> dict | None:
    path = phase_runtime_dir() / "phase_state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def step6_cleanup() -> None:
    """colab stop + mitmproxy/watchdog 프로세스 kill + .phase-runtime/current/ 통째로 삭제.
    5.5의 답변(done/paused)과 무관하게 항상 실행 — project가 계속되더라도 이번 GPU 세션
    자체는 끝내는 게 맞고, 다음 phase는 새 Colab 세션으로 시작한다."""
    rt_dir = phase_runtime_dir()
    state = _load_phase_state()

    if state is None:
        print("!! phase_state.json 없음 — session_name/PID를 못 찾음, colab/프로세스 "
              "정리는 수동으로 확인 필요(디렉토리만 삭제함)")
    else:
        session_name = state.get("session_name")
        if session_name:
            _run(["colab", "stop", "-s", session_name])
        else:
            # phase_start_local.py(2026-09-23 추가, Colab 없이 DeepSeek API로 하네스
            # 배관만 테스트하는 로컬 모드)가 session_name=None으로 저장한 경우 — 애초에
            # colab 세션이 없으므로 colab stop 자체를 건너뛴다.
            print("session_name 없음(로컬 테스트 모드) — colab stop 건너뜀")
        _kill_pid(state.get("mitmdump_pid"), "mitmdump")
        _kill_pid(state.get("watchdog_pid"), "round_watchdog")

    if rt_dir.exists():
        shutil.rmtree(rt_dir)
        print(f"{rt_dir} 정리됨")
    # test_account.json/web-구조파일/journal/exhaustion_state.json은 journal/web/<project_id>/
    # (project 레벨)에 있어서 여기서 안 건드림.


def _kill_pid(pid: int | None, label: str) -> None:
    """phase_start.py가 남긴 정확한 PID만 죽인다(pgrep 패턴매칭이 아니라 — 2단계 검토로
    수정: 패턴매칭은 같은 이름의 무관한 프로세스까지 죽일 위험이 있었음)."""
    if pid is None:
        print(f"!! {label} PID 없음 — 수동 확인 필요")
        return
    try:
        os.kill(pid, 15)  # SIGTERM
        print(f"{label}(pid={pid}) 종료 신호 보냄")
    except ProcessLookupError:
        print(f"{label}(pid={pid}) 이미 종료돼 있음")
    except PermissionError:
        print(f"!! {label}(pid={pid}) 종료 권한 없음 — 수동 확인 필요")


def step7_report_status(project_id: str) -> None:
    config = json.loads(target_config_path(project_id).read_text(encoding="utf-8"))
    status = config.get("status")
    if status == "done":
        handoff = harness_root() / "journal" / "web" / project_id / "HANDOFF.md"
        print(f"project 종료됨 — 사용자가 {handoff}를 시작점 삼아 Claude Code로 넘겨받으세요.")
    elif status == "paused":
        print(f"project 계속 진행 예정 — 나중에 phase_start.py {project_id}로 재개하세요 "
              f"(test_account.json/exhaustion_state.json 그대로 로드됨).")
    else:
        print(f"!! status가 예상치 못한 값({status}) — request-decision이 status를 "
              f"제대로 갱신했는지 확인 필요.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    args = parser.parse_args()

    step6_cleanup()
    step7_report_status(args.project_id)


if __name__ == "__main__":
    main()
