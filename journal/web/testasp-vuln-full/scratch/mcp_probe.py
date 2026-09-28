"""RAG MCP 서버 stdio 핸드셰이크 프로브 (체크리스트 자가진단 3번).

목적: Hermes 세션에 write_journal_round 도구가 잡히지 않는 원인이
  (a) 서버 측(server.py/rag_store.py) 문제인지
  (b) Hermes MCP 클라이언트 등록 문제인지
분리하기 위해, 서버를 직접 stdio 로 띄워 initialize -> tools/list 를 수행한다.

실행: <harness>/.venv/bin/python mcp_probe.py
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time

ROOT = "/home/taeuk/projects/llm-abliteration/hermes-harness"
PY = f"{ROOT}/.venv/bin/python"
SERVER = f"{ROOT}/services/rag_mcp_server/server.py"


def main() -> int:
    env = dict(os.environ)
    env["HERMES_HARNESS_ROOT"] = ROOT

    p = subprocess.Popen(
        [PY, SERVER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=ROOT, env=env, text=True, bufsize=1,
    )

    def send(obj: dict) -> None:
        p.stdin.write(json.dumps(obj) + "\n")
        p.stdin.flush()

    def read_msg(timeout: float = 15.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([p.stdout], [], [], max(0.1, deadline - time.time()))
            if not r:
                continue
            line = p.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                print(f"[non-json line] {line[:200]}")
        return None

    print("== initialize ==")
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05",
                     "capabilities": {},
                     "clientInfo": {"name": "hermes-probe", "version": "0.1"}}})
    init = read_msg()
    print(json.dumps(init, ensure_ascii=False)[:800] if init else "NO RESPONSE")

    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    print("\n== tools/list ==")
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = read_msg()
    if tools and "result" in tools:
        names = [t["name"] for t in tools["result"].get("tools", [])]
        print("TOOLS:", names)
        print("write_journal_round present:", "write_journal_round" in names)
    else:
        print("tools/list failed:", json.dumps(tools, ensure_ascii=False)[:800] if tools else "NO RESPONSE")

    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
    err = p.stderr.read()
    if err.strip():
        print("\n== stderr ==")
        print(err[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
