"""RAG NDA 스코프 격리 MCP 서버 — 얇은 MCP 프로토콜 래퍼(실제 로직은 rag_store.py).

근거: etc/RAG-스키마.md 전체.
Hermes red 프로필과 Claude Code 둘 다 이 서버를 MCP 도구로 붙여서 씀.

경로 규약(2026-09-22 5차 재검토): 이 프로세스가 실제로 어느 cwd에서 뜨는지 보장이
없어서, DB 파일 경로는 `os.environ["HERMES_HARNESS_ROOT"]` 기준 절대경로로 둠(cwd
상대경로 금지). Claude Code 쪽에서 이 서버를 붙일 때도 같은 환경변수를 설정해줘야 함
(레드 프로필과 무관하게 독립 실행 가능해야 하므로).

MCP SDK 스키마 확인 필요(체크리스트 0번) — 아래는 `mcp` 파이썬 패키지의 FastMCP 패턴을
가정. 실제 설치 후 데코레이터/실행 방식이 다르면 이 파일만 고치면 됨(rag_store.py는
MCP와 무관하게 그대로 재사용 가능).
"""

from __future__ import annotations

import os
from pathlib import Path

from rag_store import RagStore

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover - 하네스 전용 venv 미설치 상태에서도 rag_store는
    # 독립적으로 테스트 가능하게 하기 위해 최상단에서 죽이지 않음
    FastMCP = None
    _import_error = e


def _db_path() -> Path:
    root = os.environ.get("HERMES_HARNESS_ROOT")
    if not root:
        raise RuntimeError(
            "HERMES_HARNESS_ROOT 환경변수가 없음 — .env에 배치 시 1회 설정 필요 "
            "(README.md '배치 방법' 참고)"
        )
    return Path(root) / "services" / "rag_mcp_server" / "rag.db"


def build_server() -> "FastMCP":
    if FastMCP is None:  # pragma: no cover
        raise ImportError(
            f"mcp 패키지가 설치돼 있지 않음(하네스 전용 venv에 설치 필요): {_import_error}"
        )

    store = RagStore(_db_path())
    mcp = FastMCP("rag")

    @mcp.tool()
    def search(query: str, current_project: str, category: str = "web",
               top_k: int = 5) -> list[dict]:
        """정적 라이브러리가 아니라 동적 학습 데이터(rag_entries)를 검색한다. site_specific
        결과는 current_project와 일치하는 것만 나온다(NDA 스코프 강제)."""
        return store.search(query=query, category=category,
                             current_project=current_project, top_k=top_k)

    @mcp.tool()
    def write_journal_round(project_id: str, content: str, title: str,
                             vuln_class: str | None = None,
                             tech_stack: str | None = None,
                             source_ref: str | None = None) -> str:
        """write-journal-entry Skill이 라운드마다 호출 — journal_round를 site_specific으로
        삽입하고 새 entry id를 반환한다."""
        return store.write_journal_round(
            project_id=project_id, content=content, title=title,
            vuln_class=vuln_class, tech_stack=tech_stack, source_ref=source_ref,
        )

    @mcp.tool()
    def write_generalized_knowledge(content: str, title: str, tag_type: str = "framework_knowledge",
                                     vuln_class: str | None = None,
                                     tech_stack: str | None = None,
                                     source_ref: str | None = None) -> str:
        """Claude Code가 일반화 추출의 예외 경로로 호출 — 대부분은 정적 라이브러리(폴더)로
        가고, 폴더로 옮기기엔 너무 파편적인 경우만 이 도구로 rag_entries에 전역 저장."""
        return store.write_generalized_knowledge(
            content=content, title=title, tag_type=tag_type,
            vuln_class=vuln_class, tech_stack=tech_stack, source_ref=source_ref,
        )

    @mcp.tool()
    def write_report(project_id: str, source_ref: str, entry_ids: list[str]) -> str:
        """Claude Code가 보고서 작성 후 호출 — reports 행 삽입 + 참고한 라운드들을
        report_entries로 매핑."""
        return store.write_report(project_id=project_id, source_ref=source_ref,
                                   entry_ids=entry_ids)

    @mcp.tool()
    def update_report_score(report_id: str, score: int) -> None:
        """심사 결과 피드백 도착 시 Claude Code가 호출 — reports.score만 갱신
        (라운드 엔트리는 안 건드림)."""
        store.update_report_score(report_id=report_id, score=score)

    return mcp


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
