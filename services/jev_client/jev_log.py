"""Jev 호출 로깅 — 매 호출의 {state, questions, answer}를 project journal에 누적.

체크리스트 34의 전제조건("Jev 호출마다 기록하는 로깅 훅")이자, 체크리스트 35(b)
(Laya 자체 도메인 파인튜닝)의 원재료가 되는 파일. `write_journal_round`(RAG MCP)와는
별개 — 그건 서술형 일지고, 이건 fine-tune에 바로 쓸 수 있는 구조화된 원본 데이터.

`journal/web/<project_id>/jev_calls.jsonl`에 한 호출당 한 줄(JSON) append.

**동시쓰기 보호(2026-09-28, 실측 재현 후 추가)**: 첫 라이브 실측(`testasp-vulnweb-
jev-trial` Round 2)에서 실제로 두 레코드가 개행 없이 이어붙어 저장되는 걸 A가 직접
발견함(JSONL 파싱 깨짐). `rag_store.py`가 이미 같은 이유로 겪었던 문제와 동일 계열 —
FastMCP가 동기 도구 함수를 스레드 풀에서 돌릴 수 있어서, `decide()`가 거의 동시에
여러 스레드에서 불리면 append(`open(...,"a")`)가 단일 write() 라도 겹칠 수 있음.
`capture_addon.py`/`proxy_rule.py`가 겪었던 것과 같은 이유로(로컬 스레드락만으로는
프로세스 경계를 넘는 경합을 못 잡음 — 2단계 8차 재검토 교훈) 처음부터 `harness_paths`의
공유 `fcntl.flock` 락(`locked_state_file`)을 씀 — in-process 스레드 경합과
cross-process 경합을 한 번에 방어.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import locked_state_file, project_dir  # noqa: E402


def log_call(project_id: str, state, questions: dict, answer: dict, model: str) -> None:
    pdir = project_dir(project_id)
    pdir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "state": state,
        "questions": questions,
        "answer": answer,
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with locked_state_file("jev_calls"):
        with (pdir / "jev_calls.jsonl").open("a", encoding="utf-8") as f:
            f.write(line)
