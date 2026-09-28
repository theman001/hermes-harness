"""Phase 시작 오케스트레이션.

근거: etc/레드블루-에이전트-실행가능성-검토.md phase_loop 0~4단계.

경로 규약: Colab 세션 자체는 `colab new -s <이름>`처럼 고유 이름이 필요하지만, 그게 우리
`.phase-runtime/` 디렉토리 이름과 같을 필요는 없다 — `.phase-runtime/current/`로 고정
(phase는 한 번에 하나만 도니까 이름 충돌 없음).

`HERMES_HARNESS_ROOT`/`HTTP_PROXY`/`HTTPS_PROXY`는 이 스크립트가 매 phase 설정하는 게
아니라 `.env`에 배치 시 1회 설정된 정적 값이다(배치 위치와 mitmproxy 포트는 안 바뀜) —
phase마다 실제로 바뀌는 건 Colab 모델 엔드포인트뿐(아래 3번).

사용: python phase_start.py <project_id>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import (  # noqa: E402
    harness_root,
    phase_runtime_dir,
    project_dir,
    target_config_path,
)

MITM_PORT = 8080


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def load_target_config(project_id: str) -> dict:
    path = target_config_path(project_id)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 없음 — Mattermost로 사용자에게 target-config.json 작성을 요청할 것"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def update_target_status(project_id: str, status: str) -> None:
    path = target_config_path(project_id)
    config = json.loads(path.read_text(encoding="utf-8"))
    config["status"] = status
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_test_account(project_id: str) -> dict | None:
    path = project_dir(project_id) / "test_account.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def is_resuming_project(project_id: str) -> bool:
    """이 project가 이전 phase에서 이어지는 것인지 판단(2단계 재검토로 수정) — 원래
    `load_test_account(...) is not None`으로 판단했었는데, 로그인이 필요 없는 타겟은
    test_account.json이 애초에 안 생겨서 phase가 몇 번을 거쳐도 계속 resuming=False로
    잘못 판정됐음(A가 매 phase를 첫 phase로 착각해 기존 journal/recon_summary/
    attempted_exploits를 안 읽는 위험). project journal 폴더 존재 여부로 판단해야
    로그인 유무와 무관하게 정확함 — 이 폴더는 write-journal-entry Skill이 첫 라운드에서
    만들고 이후 phase에도 그대로 남아있음."""
    return project_dir(project_id).exists()


def step0_prepare(project_id: str) -> dict:
    """target-config.json 로드, status paused->active, VPN/automation_policy 확인."""
    config = load_target_config(project_id)
    if config.get("status") == "paused":
        update_target_status(project_id, "active")
        config["status"] = "active"

    automation_policy = config.get("target", {}).get("automation_policy", {})
    if automation_policy.get("prohibits_automation"):
        print(
            "!! automation_policy.prohibits_automation=true — Mattermost로 사용자 승인 "
            "1회 대기 필요(Hermes 승인 엔진이 처리, 이 스크립트는 여기서 안 막음)"
        )

    vpn = config.get("target", {}).get("vpn", {})
    if vpn.get("required"):
        profile_name = vpn.get("profile_name")
        print(f"!! VPN 재연결 필요: profile={profile_name} (이전 타겟에서 끊고 재연결 — "
              f"실제 VPN 클라이언트 연동은 배치 환경에 따라 다름, 여기선 로그만 남김)")

    test_account = load_test_account(project_id)
    print(f"test_account.json {'있음(재사용)' if test_account else '없음(recon 0단계에서 A가 요청할 것)'}")

    return config


def step1_colab_new(session_name: str) -> None:
    _run(["colab", "new", "-s", session_name, "--gpu", "A100", "--high-mem"])


def step2_colab_install_and_serve(session_name: str, model_id: str) -> None:
    # 2단계 검토로 수정: 원래 "heretic-llm"이었으나 그건 abliteration 도구고, 지금 하는 건
    # 이미 abliterate된 체크포인트를 "서빙"만 하는 것 — .claude/PROGRESS.md에 이미 기록된
    # 검증된 명령(`pip install "transformers[serving]"`)으로 정정.
    _run(["colab", "install", "-s", session_name, "transformers[serving]"])
    start_serve = Path(__file__).parents[3] / "scripts" / "start_serve.py"
    if start_serve.exists():
        _run(["colab", "exec", "-s", session_name, "--file", str(start_serve)])
    else:
        print(f"!! {start_serve} 없음 — 수동으로 transformers serve 기동 필요")

    # 추론서버가 뜰 때까지 대기 — .claude/PROGRESS.md 기록: 32B는 다운로드(65GB)+로딩에
    # 3~4분 걸림(2단계 검토로 수정: 원래 30초였던 건 이 기록과 안 맞는 명백한 과소평가).
    # 실제 헬스체크는 colab ssh 터널 확립 후 가능 — 그 전까지는 넉넉한 고정 대기로 폴백
    # (체크리스트에서 실측 후 폴링 로직으로 교체 권장).
    print("추론서버 기동 대기 중(최대 5분)...")
    time.sleep(300)


def step2b_start_phase_runtime() -> int:
    """mitmproxy를 .phase-runtime/current/에서 기동 — GPU와 무관, colab 단계와 동시 진행.
    PID를 반환(phase_end.py가 pgrep 패턴매칭 대신 정확히 이 PID만 죽이도록 phase_state.json에
    남기기 위함 — 2단계 검토로 추가: 패턴매칭은 같은 이름의 무관한 프로세스까지 죽일 위험)."""
    rt_dir = phase_runtime_dir()
    if rt_dir.exists():
        shutil.rmtree(rt_dir)  # 이전 phase 걸 혹시 못 지웠으면 먼저 비움
    rt_dir.mkdir(parents=True)

    addon_path = Path(__file__).parents[1] / "mitmproxy_addon" / "capture_addon.py"
    env = os.environ.copy()
    log_path = rt_dir / "mitmdump.log"
    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        ["mitmdump", "-p", str(MITM_PORT), "-s", str(addon_path)],
        stdout=log_file, stderr=subprocess.STDOUT, env=env,
        start_new_session=True,
    )
    print(f"mitmproxy 기동됨(127.0.0.1:{MITM_PORT}), pid={proc.pid}, 로그: {log_path}")
    return proc.pid


def step2c_start_watchdog(project_id: str, max_rounds_per_phase: int) -> int:
    watchdog_path = Path(__file__).parents[1] / "watchdog" / "round_watchdog.py"
    log_path = phase_runtime_dir() / "watchdog.log"
    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(watchdog_path), project_id, str(max_rounds_per_phase)],
        stdout=log_file, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"round_watchdog 기동됨, pid={proc.pid}, 로그: {log_path}")
    return proc.pid


def _save_phase_state(session_name: str, mitmdump_pid: int, watchdog_pid: int) -> None:
    """phase_end.py가 session_name/PID를 수동 인자로 안 받아도 되도록 저장(2단계 검토로
    추가) — 안 그러면 운영자가 phase_start.py 출력에서 세션 이름을 손으로 옮겨 적어야 함."""
    state = {
        "session_name": session_name,
        "mitmdump_pid": mitmdump_pid,
        "watchdog_pid": watchdog_pid,
    }
    (phase_runtime_dir() / "phase_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def step3_update_model_endpoint(
    model_name: str, base_url: str | None = None, api_key: str | None = None,
    provider: str | None = None,
) -> None:
    """colab ssh --proxy-mode 터널 이후 로컬에 뜨는 포트를 config.yaml의 model.base_url에
    반영. 정확한 터널 기동 방식은 체크리스트(Colab<->로컬호스트 네트워크 연결)에서 실측 —
    Colab 경로에서는 로컬 8000 포트로 이미 떠 있다고 가정하고 model 이름만 갱신한다
    (base_url/api_key/provider 미지정 시 기존 값 유지).

    `base_url`/`api_key`/`provider`는 `phase_start_local.py`(Colab CU 회복 전 DeepSeek API로
    하네스 배관을 테스트하는 로컬 모드, 2026-09-23 추가)가 넘겨준다 — 이 경우 실제 다른
    provider 엔드포인트로 완전히 바꾸는 것이라 네 필드 다 갱신 필요.

    (2단계 전체 재검토로 정리: 원래 있던 `session_name` 매개변수는 함수 안에서 전혀 안 쓰여서
    삭제 — 정리 중 발견. 2026-09-23 하네스 실측으로 매개변수명도 `model_id`→`model_name`으로
    바꿈 — 실제 config.yaml 키가 `model_id`가 아니라 `default`/`model`이라 이름이 혼동을
    유발했었음, `hermes doctor`로 `provider: openai_compatible`이 실재하지 않는 값인 것도
    같이 확인됨 — 커스텀 OpenAI 호환 엔드포인트는 `provider: "custom"`가 맞는 값.)"""
    config_path = harness_root() / "red" / "config.yaml"
    # YAML 파서 의존성을 늘리지 않기 위해 단순 텍스트 치환(스키마가 확정되면 정식 YAML
    # 라이브러리로 교체 권장 — 체크리스트 0번)
    text = config_path.read_text(encoding="utf-8")
    text = re.sub(r'default:\s*".*"', f'default: "{model_name}"', text)
    if base_url is not None:
        text = re.sub(r'base_url:\s*".*"', f'base_url: "{base_url}"', text)
    if api_key is not None:
        text = re.sub(r'api_key:\s*".*"', f'api_key: "{api_key}"', text)
    if provider is not None:
        text = re.sub(r'provider:\s*".*"', f'provider: "{provider}"', text)
    config_path.write_text(text, encoding="utf-8")
    print(f"config.yaml의 model 필드 갱신: default={model_name}"
          + (f", base_url={base_url}" if base_url is not None else "")
          + (f", api_key={api_key}" if api_key is not None else "")
          + (f", provider={provider}" if provider is not None else ""))


def step4_start_hermes_conversation(project_id: str, resuming: bool) -> None:
    """Hermes 대화 시작 — "시스템 프롬프트 동적 주입"이 아니라 그냥 첫 메시지로 project_id를
    전달한다(확실히 지원되는 평범한 대화 시작 메시지).

    2026-09-23 실측으로 정정 — 예전엔 "각 phase는 이전 phase와 대화가 이어지지 않는 새
    세션"이라고 적혀 있었는데, 그건 phase마다 `-q`로 새 프로세스를 띄우던 옛 설계
    기준이었음. 지금은 `hermes gateway`(상시 세션)로 바뀌었고, `-q`는 승인 왕복이
    구조적으로 안 되는 것도 확인됨(approvals.single_query_mode) — 그래서 이 메시지는
    Mattermost로 **새 최상위 메시지**로 보내야 새 세션이 됨(`MATTERMOST_REPLY_MODE=
    thread` 필요, README "배치 방법" 참고) — 스레드 답장으로 보내면 이전 project와 세션이
    섞인다."""
    message = f"{project_id} 시작. targets/{project_id}.json 참고."
    if resuming:
        message += (
            " 이 project는 이미 진행 중이던 것을 재개하는 것 — journal/recon_summary.json/"
            "web-페이지-구조.md/web-서버-구조.md/attempted_exploits.json을 먼저 읽고 "
            "지금까지 상황을 파악한 뒤 이어서 진행할 것."
        )
    print(f"Hermes 대화 시작 메시지(Mattermost에 **새 최상위 메시지**로 보낼 것 — "
          f"스레드 답장 금지, 세션 분리 위함):\n  {message}")
    # 실제 실행은 배치 환경(대화형 세션 vs 완전 무인 -q 모드)에 따라 운영자가 선택 —
    # 여기서는 커맨드만 안내(무인 모드로 자동 실행하려면 아래 주석 해제)
    # _run(["hermes", "--profile", "red", "-q", message])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    args = parser.parse_args()

    config = step0_prepare(args.project_id)
    resuming = is_resuming_project(args.project_id)
    max_rounds = config.get("max_rounds_per_phase", 30)

    session_name = f"{args.project_id}-{int(time.time())}"
    step1_colab_new(session_name)

    model_id = "9theman9/deepseek-r1-distill-qwen-32b-heretic"  # TODO: target-config에서 override 가능하게
    step2_colab_install_and_serve(session_name, model_id)
    mitmdump_pid = step2b_start_phase_runtime()
    watchdog_pid = step2c_start_watchdog(args.project_id, max_rounds)
    _save_phase_state(session_name, mitmdump_pid, watchdog_pid)

    step3_update_model_endpoint(model_id)
    step4_start_hermes_conversation(args.project_id, resuming)

    print(f"\nphase 시작 완료: session={session_name}, project={args.project_id}")
    print(f"종료 시 phase_end.py {args.project_id} 실행할 것 "
          f"(session_name/PID는 phase_state.json에서 자동으로 읽음)")


if __name__ == "__main__":
    main()
