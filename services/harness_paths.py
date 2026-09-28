"""공통 경로 헬퍼 — hermes-harness의 여러 서비스가 중복 정의하던 것을 통합.

2단계 재검토로 추가: `harness_root()`/`project_dir()`/`phase_runtime_dir()`/
`target_config_path()`가 round_watchdog.py, phase_start.py, phase_end.py,
assemble_handoff.py, capture_addon.py, proxy_rule.py 6곳에 각각 거의 똑같이 복붙돼
있었음 — 경로 로직을 또 고쳐야 할 때(이미 5~6차 재검토에서 두 번 있었음) 한 곳을 놓치면
조용히 어긋나는 위험이 실제로 있었음. 이제 여기 하나만 고치면 전부 반영됨.

사용법(각 스크립트 상단, 직접 파일 경로로 실행되거나 mitmdump -s로 로드돼도 동작하도록
sys.path를 스크립트 자신의 위치 기준으로 조정):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
    from harness_paths import harness_root, project_dir, phase_runtime_dir, target_config_path
"""

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path


def harness_root() -> Path:
    root = os.environ.get("HERMES_HARNESS_ROOT")
    return Path(root) if root else Path.cwd()


def project_dir(project_id: str, category: str = "web") -> Path:
    return harness_root() / "journal" / category / project_id


def phase_runtime_dir() -> Path:
    return harness_root() / ".phase-runtime" / "current"


def target_config_path(project_id: str) -> Path:
    return harness_root() / "targets" / f"{project_id}.json"


@contextlib.contextmanager
def locked_state_file(name: str):
    """`.phase-runtime/current/`의 상태 파일을 **여러 프로세스에 걸쳐** 원자적으로
    read-modify-write하기 위한 공유 락(2단계 재검토로 추가). `capture_addon.py`(mitmproxy
    플로우가 트리거)와 `proxy_rule.py`(A가 `terminal`로 직접 실행하는 별도 프로세스)가
    똑같은 `proxy_rules.json`을 각자 락 없이 건드리고 있었던 게 발견된 문제 — 한쪽
    파일(`capture_addon.py`) 안에서만 락을 정의하면 그 프로세스 내부 동시성만 막을 뿐,
    별도 프로세스인 `proxy_rule.py`의 쓰기와는 전혀 동기화가 안 됨. 여기(공통 모듈)로
    옮겨서 두 프로세스가 **같은 락 파일**을 참조하게 함 — `name`으로 잠글 자원을 구분
    (예: `"proxy_rules"`, `"waf_log"` — 서로 다른 자원끼리는 불필요하게 직렬화 안 되게).
    """
    lock_path = phase_runtime_dir() / f".{name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)
    with open(lock_path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
