"""Jev 판단모델 MCP 서버 — 얇은 MCP 프로토콜 래퍼(실제 로직은 jev_client.py/jev_log.py).

근거: etc/레드블루-에이전트-실행가능성-검토.md "결정 완료(2026-09-28)". A가 recon 후보
중 공격지점/기법을 고를 때 참고용으로 부르는 보조 도구 — 승인/차단 권한 없음(가산적
설계), 실패해도 A는 그냥 자기 판단으로 계속 진행하면 됨(필수 의존성 아님).

rag_mcp_server/server.py와 동일한 패턴(FastMCP, mcp 패키지 미설치 상태에서도
jev_client/jev_log는 독립 테스트 가능).
"""

from __future__ import annotations

from jev_client import call_systemone
from jev_log import log_call

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    FastMCP = None
    _import_error = e


def build_server() -> "FastMCP":
    if FastMCP is None:  # pragma: no cover
        raise ImportError(
            f"mcp 패키지가 설치돼 있지 않음(하네스 전용 venv에 설치 필요): {_import_error}"
        )

    mcp = FastMCP("jev")

    @mcp.tool()
    def decide(project_id: str, state: str, questions: dict, model: str = "jev-latest") -> dict:
        """공격지점/기법 후보에 대한 choice/score/noul 판단을 Jev에 물어본다. **참고용
        보조 신호일 뿐** — 이 결과만으로 취약점을 확정하거나 승인 절차를 건너뛰지 않는다.
        호출마다 journal/web/<project_id>/jev_calls.jsonl에 기록됨(체크리스트 35(b)
        파인튜닝 데이터로 재사용)."""
        response = call_systemone(state, questions, model=model)
        log_call(project_id, state, questions, response.get("answers", {}), model)
        return response["answers"]

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
