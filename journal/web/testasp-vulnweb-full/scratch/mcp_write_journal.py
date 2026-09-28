"""RAG MCP write_journal_round 실제 호출 + DB 삽입 검증.

도구가 Hermes 세션에 등록돼 있지 않아(mcp.servers 가 Hermes 스키마가 아님) 동일 서버를
stdio 로 직접 기동해 write_journal_round 를 호출하고, 그 결과를 rag.db 에서 다시 읽어
삽입을 검증한다. 실행: <harness>/.venv/bin/python mcp_write_journal.py <journal_md> <round_header>
"""
from __future__ import annotations

import json
import os
import select
import sqlite3
import subprocess
import sys
import time

ROOT = "/home/taeuk/projects/llm-abliteration/hermes-harness"
PY = f"{ROOT}/.venv/bin/python"
SERVER = f"{ROOT}/services/rag_mcp_server/server.py"
DB = f"{ROOT}/services/rag_mcp_server/rag.db"
PROJECT = "testasp-vulnweb-full"


def extract_section(text: str, header: str) -> str:
    i = text.find(header)
    if i < 0:
        raise SystemExit(f"section not found: {header}")
    j = text.find("\n## ", i + len(header))
    return text[i:j] if j > 0 else text[i:]


def main() -> int:
    md_path = sys.argv[1]
    header = sys.argv[2] if len(sys.argv) > 2 else "## Round 4 —"
    content = extract_section(open(md_path, encoding="utf-8").read(), header)

    env = dict(os.environ)
    env["HERMES_HARNESS_ROOT"] = ROOT
    p = subprocess.Popen([PY, SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, cwd=ROOT, env=env, text=True, bufsize=1)

    def send(o):
        p.stdin.write(json.dumps(o) + "\n")
        p.stdin.flush()

    def read(timeout=25.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([p.stdout], [], [], max(0.1, deadline - time.time()))
            if not r:
                continue
            line = p.stdout.readline()
            if line.strip():
                return json.loads(line)
        return None

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "hermes-journal", "version": "0.1"}}})
    print("initialize:", json.dumps(read(), ensure_ascii=False)[:200])
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    before = sqlite3.connect(DB).execute("select count(*) from rag_entries").fetchone()[0]

    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "write_journal_round",
                     "arguments": {
                         "project_id": PROJECT,
                         "content": content,
                         "title": "Round 4 — 체크리스트 자가진단(cronjob/browser/RAG) + recon 0~2단계, search.asp 500 분기 발견",
                         "vuln_class": "recon",
                         "tech_stack": "iis,asp,asp.net,dreamweaver,tinymce",
                         "source_ref": "journal/web/testasp-vulnweb-full/2026-09-23.md"}}})
    resp = read()
    print("write_journal_round:", json.dumps(resp, ensure_ascii=False)[:600])

    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "search",
                     "arguments": {"query": "search.asp 500 tfSearch", "current_project": PROJECT,
                                   "category": "web", "top_k": 3}}})
    print("search:", json.dumps(read(), ensure_ascii=False)[:600])

    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()

    con = sqlite3.connect(DB)
    after = con.execute("select count(*) from rag_entries").fetchone()[0]
    print(f"\nrag_entries: before={before} after={after}")
    for row in con.execute(
            "select id, tag_type, scope_project, source_type, source_ref, title, length(content) "
            "from rag_entries order by rowid desc limit 3"):
        print("ROW:", row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
