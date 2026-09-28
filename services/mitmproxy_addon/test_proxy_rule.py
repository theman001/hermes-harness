"""proxy_rule.py의 프로세스 간 락(2단계 재검토로 추가) self-check.

capture_addon.py는 mitmproxy 없이 import가 까다로워 스텁으로 우회하지만(test_capture_addon.py
참고), 이 테스트는 proxy_rule.py 자기 자신의 **다른 프로세스와의** 경합만 검증하면 되므로
실제 서브프로세스 여러 개를 동시에 띄워서 직접 확인한다 — capture_addon.py 쪽 락 적용
여부는 코드 리뷰로 갈음(같은 `harness_paths.locked_state_file("proxy_rules")`를 씀).

실행: python test_proxy_rule.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROXY_RULE_PY = str(Path(__file__).parent / "proxy_rule.py")


def test_concurrent_add_from_separate_processes_loses_nothing():
    """2단계 재검토로 발견한 버그의 회귀 테스트: capture_addon.py(mitmproxy, 별도 프로세스)와
    proxy_rule.py(A가 실행, 또 다른 별도 프로세스)가 같은 proxy_rules.json을 락 없이 건드리면
    서로 쓰기를 덮어써서 방금 추가한 규칙이 사라질 수 있었음 — 여기선 proxy_rule.py 여러
    인스턴스를 실제 서브프로세스로 동시에 띄워서, 프로세스 경계를 넘는 락이 실제로
    작동하는지 확인한다(스레드 테스트로는 프로세스 간 경합을 못 잡음)."""
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["HERMES_HARNESS_ROOT"] = tmp

        n = 15
        procs = [
            subprocess.Popen(
                [sys.executable, PROXY_RULE_PY, "add", "--target", "response",
                 "--url-regex", f"/api/x{i}", "--ttl", "60"],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            for i in range(n)
        ]
        for p in procs:
            stdout, stderr = p.communicate()
            assert p.returncode == 0, stderr.decode()

        rules_path = Path(tmp) / ".phase-runtime" / "current" / "proxy_rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        assert len(rules) == n, (
            f"동시에 add한 {n}개 중 {len(rules)}개만 남음 — 프로세스 간 락이 없으면 "
            f"서로 쓰기를 덮어써서 유실될 수 있음"
        )


if __name__ == "__main__":
    test_concurrent_add_from_separate_processes_loses_nothing()
    print("OK — proxy_rule self-check passed")
