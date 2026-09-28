"""capture_addon.py의 파일 락(2단계 재검토로 추가) self-check.

mitmproxy 패키지가 하네스 전용 venv에만 있어서(이 검사 환경엔 없음), 실제 import 전에
`mitmproxy`/`mitmproxy.http`를 더미 모듈로 스텁 — 이 테스트는 `http.HTTPFlow` 객체가
필요 없는 `_check_waf`(WAF 로그 read-modify-write)만 동시성 관점에서 검증하므로 문제없음.

실행: python test_capture_addon.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import types
from pathlib import Path

# --- mitmproxy 스텁(실제 패키지 없이 import 가능하게) ---
_mitmproxy = types.ModuleType("mitmproxy")
_mitmproxy_http = types.ModuleType("mitmproxy.http")
_mitmproxy_http.HTTPFlow = object  # 타입 힌트용 더미, 이 테스트에선 실제로 안 씀
_mitmproxy.http = _mitmproxy_http
sys.modules["mitmproxy"] = _mitmproxy
sys.modules["mitmproxy.http"] = _mitmproxy_http

import capture_addon as ca  # noqa: E402


def test_concurrent_waf_checks_dont_lose_updates():
    """2단계 재검토로 발견한 경합 시나리오의 회귀 테스트: recon 라운드에서 delegate_task
    자식 여러 개가 동시에 프록시를 거치면 `_check_waf`의 read-modify-write가 겹칠 수
    있었음 — 락 없이 스레드 20개가 동시에 호출하면 일부 기록이 유실될 수 있는데, 락을
    걸면 모든 기록이 로그에 남아야 한다(유실 없음)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        (Path(tmp) / ".phase-runtime" / "current").mkdir(parents=True)

        n_threads = 20
        threads = [
            threading.Thread(target=ca._check_waf, args=(200,)) for _ in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log_path = ca._waf_status_log_path()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == n_threads, (
            f"동시 호출 {n_threads}건 중 {len(lines)}건만 로그에 남음 — 락이 없으면 "
            f"read-modify-write 경합으로 기록이 유실될 수 있음"
        )


if __name__ == "__main__":
    test_concurrent_waf_checks_dont_lose_updates()
    print("OK — capture_addon self-check passed")
