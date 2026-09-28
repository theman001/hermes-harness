"""jev_client.py / offline_eval.py 최소 self-check.

실행: python test_jev_client.py
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

import jev_client as jc
import jev_log
import offline_eval as oe
from harness_paths import project_dir


def test_call_systemone_raises_clear_error_without_key():
    os.environ.pop("TYPESAFE_API_KEY", None)
    try:
        jc.call_systemone("state", {"q": {"type": "noul"}}, api_key=None)
        raise AssertionError("키 없이 호출했는데 예외가 안 남")
    except jc.JevKeyMissing:
        pass


def test_base_path_extracts_script_ignoring_query_and_notes():
    assert oe.base_path("/Templatize.asp?item=<상대경로>") == "/templatize.asp"
    assert oe.base_path("`/Logout.asp?RetURL=` (권장 PoC)") == "/logout.asp"
    assert oe.base_path("/robots.txt") == "/robots.txt"
    assert oe.base_path("/_vti_cnf/ (존재 오라클)") is None  # 확장자 없는 디렉터리는 스킵


def _write_fixture_project(root: Path, project_id: str) -> None:
    pdir = root / "journal" / "web" / project_id
    pdir.mkdir(parents=True)
    (pdir / "recon_summary.json").write_text(
        json.dumps(
            {
                "tech_stack": ["iis", "asp"],
                "discovered_endpoints": [
                    "/search.asp?tfSearch=<입력값>",
                    {"path": "/Templatize.asp?item=<경로>", "method": "GET",
                     "note": "LFI 의심"},
                    "/robots.txt",
                ],
            }
        ),
        encoding="utf-8",
    )
    (pdir / "PoC-코드.md").write_text(
        "# PoC\n\n"
        "## 1. LFI — `/Templatize.asp?item=`\n내용\n\n"
        "## 2. SQLi — `/search.asp?tfSearch=`\n내용\n",
        encoding="utf-8",
    )


def test_evaluate_dry_run_matches_confirmed_paths_against_recon_candidates():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        project_id = "fixture-project"
        _write_fixture_project(Path(tmp), project_id)

        report = oe.evaluate(project_id, dry_run=True)

        assert report["total_candidates"] == 3
        assert report["confirmed_paths"] == ["/search.asp", "/templatize.asp"]
        # dry-run이므로 실제 평가는 0건, 그러나 gold_confirmed는 정확히 계산돼 있어야 함
        assert report["evaluated"] == 0
        assert report["accuracy"] is None
        gold_by_path = {r["path"]: r["gold_confirmed"] for r in report["results"]}
        assert gold_by_path["/search.asp"] is True
        assert gold_by_path["/templatize.asp"] is True
        assert gold_by_path["/robots.txt"] is False


def test_log_call_appends_jsonl_entry():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        project_id = "log-fixture"

        jev_log.log_call(project_id, "state1", {"q": {"type": "noul"}},
                          {"q": {"label": "true"}}, "jev-latest")
        jev_log.log_call(project_id, "state2", {"q": {"type": "noul"}},
                          {"q": {"label": "false"}}, "jev-latest")

        log_file = project_dir(project_id) / "jev_calls.jsonl"
        lines = [json.loads(line) for line in log_file.read_text().splitlines()]

        assert len(lines) == 2
        assert lines[0]["state"] == "state1"
        assert lines[1]["answer"]["q"]["label"] == "false"
        assert "ts" in lines[0]


def test_concurrent_log_calls_dont_corrupt_jsonl():
    """실측 재현(2026-09-28, testasp-vulnweb-jev-trial Round 2): 락 없이 거의 동시에
    log_call이 여러 번 불리면 두 레코드가 개행 없이 이어붙어 JSONL이 깨질 수 있었음 —
    락을 걸면 N번 호출 = N개의 온전히 파싱 가능한 줄이어야 한다(유실도, 병합도 없이)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        project_id = "concurrency-fixture"

        n_calls = 30
        threads = [
            threading.Thread(
                target=jev_log.log_call,
                args=(project_id, f"state-{i}", {"q": {"type": "noul"}},
                      {"q": {"label": "true"}}, "jev-latest"),
            )
            for i in range(n_calls)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log_file = project_dir(project_id) / "jev_calls.jsonl"
        lines = log_file.read_text(encoding="utf-8").splitlines()

        assert len(lines) == n_calls, (
            f"{n_calls}번 동시 호출했는데 {len(lines)}줄만 남음 — 개행 유실/병합 의심"
        )
        parsed = [json.loads(line) for line in lines]  # 한 줄이라도 깨졌으면 여기서 예외
        states = {p["state"] for p in parsed}
        assert states == {f"state-{i}" for i in range(n_calls)}


if __name__ == "__main__":
    test_call_systemone_raises_clear_error_without_key()
    test_base_path_extracts_script_ignoring_query_and_notes()
    test_evaluate_dry_run_matches_confirmed_paths_against_recon_candidates()
    test_log_call_appends_jsonl_entry()
    test_concurrent_log_calls_dont_corrupt_jsonl()
    print("OK — jev_client/offline_eval self-check passed")
