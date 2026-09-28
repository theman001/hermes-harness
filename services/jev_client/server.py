"""Jev 판단모델 MCP 서버 — 얇은 MCP 프로토콜 래퍼(실제 로직은 jev_client.py/jev_log.py).

근거: etc/레드블루-에이전트-실행가능성-검토.md "결정 완료(2026-09-28)". A가 recon 후보
중 공격지점/기법을 고를 때 참고용으로 부르는 보조 도구 — 승인/차단 권한 없음(가산적
설계), 실패해도 A는 그냥 자기 판단으로 계속 진행하면 됨(필수 의존성 아님).

rag_mcp_server/server.py와 동일한 패턴(FastMCP, mcp 패키지 미설치 상태에서도
jev_client/jev_log는 독립 테스트 가능).
"""

from __future__ import annotations

from typing import Literal

from jev_client import call_systemone
from jev_log import log_call
from pydantic import BaseModel, Field

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    FastMCP = None
    _import_error = e


# 2026-09-29 추가 — 이전엔 `questions: dict`로 타입힌트 없이 받아서 MCP가 모델에게 넘기는
# 도구 스키마가 `{"type": "object", "additionalProperties": true}`뿐이었음(실측 확인,
# `list_tools()`로 직접 스키마 덤프해서 확인함) — 내부 구조를 스키마가 전혀 안 알려주니
# 모델이 도큐스트링만 보고 추측 생성했고, 실제 라이브 라운드(google-gruyere-trial
# Round 4·6)에서 복잡한 중첩 payload를 생성하다 간헐적으로 깨지는 문제(`calls[0] requires
# a 'name'`)가 A 스스로 보고됨. Pydantic 모델로 명시하면 FastMCP가 실제 중첩 JSON Schema를
# 만들어줘서(`$defs`/`$ref`) 모델이 구조를 추측 안 하고 스키마를 그대로 따라가게 됨 —
# 모델에게 매 턴 보내지는 스키마 설명은 토큰 낭비 방지를 위해 짧게 유지(자세한 배경은
# 이 주석에만 남김).
class JevQuestion(BaseModel):
    """choice/score/noul 판단 질문 하나."""

    type: Literal["choice", "score", "noul"]
    instructions: str
    criteria: dict[str, str] | None = Field(
        default=None,
        description="choice/score 타입일 때만: {후보명: 설명} — noul(yes/no)에는 없어도 됨.",
    )


def build_server() -> "FastMCP":
    if FastMCP is None:  # pragma: no cover
        raise ImportError(
            f"mcp 패키지가 설치돼 있지 않음(하네스 전용 venv에 설치 필요): {_import_error}"
        )

    mcp = FastMCP("jev")

    @mcp.tool()
    def decide(
        project_id: str, state: str, questions: dict[str, JevQuestion], model: str = "jev-latest"
    ) -> dict:
        """공격지점/기법 후보에 대한 choice/score/noul 판단을 Jev에 물어본다. **참고용
        보조 신호일 뿐** — 이 결과만으로 취약점을 확정하거나 승인 절차를 건너뛰지 않는다.
        호출마다 journal/web/<project_id>/jev_calls.jsonl에 기록됨(체크리스트 35(b)
        파인튜닝 데이터로 재사용)."""
        raw_questions = {qid: q.model_dump(exclude_none=True) for qid, q in questions.items()}
        response = call_systemone(state, raw_questions, model=model)
        log_call(project_id, state, raw_questions, response.get("answers", {}), model)
        return response["answers"]

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
