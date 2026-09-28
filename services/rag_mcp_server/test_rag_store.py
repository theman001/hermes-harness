"""rag_store.py 핵심 로직(특히 스코프 강제) self-check.

실행: python test_rag_store.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from rag_store import RagStore


def test_site_specific_scoped_to_project():
    with tempfile.TemporaryDirectory() as tmp:
        store = RagStore(Path(tmp) / "rag.db")
        store.write_journal_round(
            project_id="project-a", content="project A의 IDOR 발견 상세",
            title="IDOR in /api/orders", vuln_class="idor",
        )
        store.write_journal_round(
            project_id="project-b", content="project B의 SQLi 발견 상세",
            title="SQLi in /login", vuln_class="sqli",
        )

        results_a = store.search(query="IDOR", category="web", current_project="project-a")
        results_b = store.search(query="IDOR", category="web", current_project="project-b")

        assert any("project A" in r["content"] for r in results_a), \
            "project-a로 검색하면 project-a의 site_specific 항목이 나와야 함"
        assert not any("project A" in r["content"] for r in results_b), \
            "project-b로 검색할 때 project-a의 site_specific 항목이 새면 안 됨(NDA 격리)"
        store.close()


def test_generalized_knowledge_is_global():
    with tempfile.TemporaryDirectory() as tmp:
        store = RagStore(Path(tmp) / "rag.db")
        store.write_generalized_knowledge(
            content="Laravel IDOR 패턴 일반화 교훈", title="Laravel IDOR lessons",
            tag_type="framework_knowledge", tech_stack="laravel",
        )
        results_x = store.search(query="Laravel IDOR", category="web", current_project="project-x")
        results_y = store.search(query="Laravel IDOR", category="web", current_project="project-y")
        assert any("일반화" in r["content"] for r in results_x)
        assert any("일반화" in r["content"] for r in results_y), \
            "framework_knowledge는 scope_project 무관하게 전역 노출돼야 함"
        store.close()


def test_naive_embed_stable_across_processes():
    """2단계 4차 재검토로 발견한 버그의 회귀 테스트: 예전엔 Python 내장 hash()를 써서
    PYTHONHASHSEED가 다른 프로세스끼리 같은 텍스트도 다른 벡터를 냈음(문자열 해시
    랜덤화) — RAG 서버는 매 세션마다 새 프로세스로 뜨므로 이게 실제로 터지는 버그였음.
    PYTHONHASHSEED를 다르게 강제한 두 서브프로세스가 같은 텍스트에 대해 똑같은 임베딩을
    내는지 직접 확인(이게 실제 실패 모드였음 — 단일 프로세스 안에서는 절대 못 잡음)."""
    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from rag_store import _naive_embed; "
        "print(_naive_embed('IDOR in /api/orders'))"
    )
    results = []
    for seed in ("0", "12345"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parent, capture_output=True, text=True,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr
        results.append(proc.stdout.strip())
    assert results[0] == results[1], (
        "PYTHONHASHSEED가 다른 두 프로세스가 같은 텍스트에 다른 임베딩을 냄 — "
        "hash() 대신 안정적인 해시를 써야 함"
    )


def test_used_safely_from_a_different_thread():
    """2단계 7차 재검토로 발견: sqlite3 커넥션은 기본적으로 생성한 스레드에서만 쓸 수
    있음(check_same_thread=True 기본값) — MCP 서버 프레임워크(FastMCP)가 동기 도구
    함수를 스레드 풀에서 돌릴 가능성이 있는데(이벤트루프를 안 막으려는 흔한 패턴), 그
    경우 RagStore를 만든 스레드가 아닌 다른 스레드에서 메서드를 호출하면 바로
    ProgrammingError로 죽었을 것 — check_same_thread=False + Lock으로 방어했는지 확인."""
    with tempfile.TemporaryDirectory() as tmp:
        store = RagStore(Path(tmp) / "rag.db")  # 이 스레드(메인)에서 생성
        errors = []

        def call_from_other_thread():
            try:
                store.write_journal_round(project_id="p", content="c", title="t")
                store.search(query="c", category="web", current_project="p")
            except Exception as e:  # noqa: BLE001 - 테스트에서 어떤 예외든 잡아서 보고
                errors.append(e)

        t = threading.Thread(target=call_from_other_thread)
        t.start()
        t.join()

        assert not errors, f"다른 스레드에서 호출 시 예외 발생: {errors}"
        store.close()


def test_report_score_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = RagStore(Path(tmp) / "rag.db")
        entry_id = store.write_journal_round(
            project_id="p1", content="c", title="t",
        )
        report_id = store.write_report(project_id="p1", source_ref="reports/p1/1.md",
                                        entry_ids=[entry_id])
        store.update_report_score(report_id=report_id, score=8)
        row = store.conn.execute("SELECT score FROM reports WHERE id=?", (report_id,)).fetchone()
        assert row["score"] == 8
        store.close()


if __name__ == "__main__":
    test_site_specific_scoped_to_project()
    test_generalized_knowledge_is_global()
    test_naive_embed_stable_across_processes()
    test_used_safely_from_a_different_thread()
    test_report_score_roundtrip()
    print("OK — rag_store self-check passed")
