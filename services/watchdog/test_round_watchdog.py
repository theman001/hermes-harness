"""round_watchdog.py의 핵심 분기(라운드 카운팅, 소진 판정, phase 간 베이스라인)에 대한
최소 self-check.

실행: python test_round_watchdog.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import round_watchdog as rw


def _setup(tmp: Path) -> str:
    os.environ["HERMES_HARNESS_ROOT"] = str(tmp)
    project_id = "test-project"
    pdir = rw.project_dir(project_id)
    pdir.mkdir(parents=True)
    return project_id


def _start_new_phase(tmp: Path) -> None:
    """phase_start.py가 실제로 하는 것처럼 phase마다 .phase-runtime/current/를 새로 만듦
    (round_count_baseline.json이 이번 phase 시작 시점 기준으로 다시 잡히게)."""
    rt_dir = Path(tmp) / ".phase-runtime" / "current"
    if rt_dir.exists():
        import shutil
        shutil.rmtree(rt_dir)


def test_round_counting_and_max_rounds():
    with tempfile.TemporaryDirectory() as tmp:
        project_id = _setup(Path(tmp))
        pdir = rw.project_dir(project_id)
        journal = pdir / "2026-09-22.md"

        # 실제 순서와 동일: 워치독(baseline=0)이 먼저 뜬 뒤에 라운드가 기록됨
        _start_new_phase(Path(tmp))
        assert rw.check_once(project_id, max_rounds_per_phase=2) is None  # 라운드 0개

        journal.write_text("## Round 1\n...\n## Round 2\n...\n", encoding="utf-8")
        result = rw.check_once(project_id, max_rounds_per_phase=2)
        assert result is not None, "라운드 2개 == 상한 2 -> 종료 신호가 떠야 함"
        assert result["max_rounds_reached"] is True
        assert result["attack_exhausted"] is False
        assert result["round_count"] == 2

        result_under = rw.check_once(project_id, max_rounds_per_phase=5)
        assert result_under is None, "상한 미달이면 신호 없어야 함"


def test_max_rounds_resets_per_phase_not_cumulative_project():
    """2단계 재검토로 발견한 버그의 회귀 테스트: project가 여러 phase에 걸치면, 이전
    phase에서 이미 쌓인 라운드 수가 다음 phase의 max_rounds_per_phase 판정에 섞이면 안 됨."""
    with tempfile.TemporaryDirectory() as tmp:
        project_id = _setup(Path(tmp))
        pdir = rw.project_dir(project_id)
        journal = pdir / "2026-09-22.md"

        # phase 1: 25라운드까지 쌓임(상한 30 안에서 끝남, 소진 등 다른 이유로 종료됐다고 가정)
        _start_new_phase(Path(tmp))
        rounds_text = "".join(f"## Round {n}\n" for n in range(1, 26))
        journal.write_text(rounds_text, encoding="utf-8")
        result_phase1 = rw.check_once(project_id, max_rounds_per_phase=30)
        assert result_phase1 is None, "phase 1: 25 < 30 이므로 아직 상한 아님"

        # phase 2 시작 — .phase-runtime/current/가 새로 생김(phase_start.py와 동일)
        _start_new_phase(Path(tmp))
        assert rw.check_once(project_id, max_rounds_per_phase=30) is None, \
            "phase 2 시작 직후는 이번 phase 라운드 0개 — project 누적(25)이 아니라 0으로 봐야 함"

        # phase 2에서 5라운드만 추가로 진행(같은 날짜 파일에 이어 씀 — project 누적은 30, 이번
        # phase만 5)
        journal.write_text(
            journal.read_text(encoding="utf-8")
            + "".join(f"## Round {n}\n" for n in range(26, 31)),
            encoding="utf-8",
        )
        result_phase2 = rw.check_once(project_id, max_rounds_per_phase=30)
        assert result_phase2 is None, (
            "project 누적은 30(=상한)이지만 이번 phase는 5라운드뿐이라 아직 종료 신호가 "
            "뜨면 안 됨 — 뜨면 이전 phase 라운드가 섞여 든 버그"
        )


def test_exhaustion_requires_both_axes_and_real_rounds():
    with tempfile.TemporaryDirectory() as tmp:
        project_id = _setup(Path(tmp))
        pdir = rw.project_dir(project_id)
        journal = pdir / "2026-09-22.md"
        page_file = pdir / "web-페이지-구조.md"
        server_file = pdir / "web-서버-구조.md"
        _start_new_phase(Path(tmp))

        # 라운드 1: 두 파일 다 처음 생김(베이스라인) — 아직 소진 아님
        journal.write_text("## Round 1\n", encoding="utf-8")
        page_file.write_text("초기 페이지 구조", encoding="utf-8")
        server_file.write_text("초기 서버 구조", encoding="utf-8")
        assert rw.check_once(project_id, max_rounds_per_phase=100) is None

        # 라운드 2~4: 두 파일 다 안 바뀜 (연속 3라운드 무갱신)
        for n in (2, 3, 4):
            journal.write_text(journal.read_text(encoding="utf-8") + f"## Round {n}\n",
                                encoding="utf-8")
            result = rw.check_once(project_id, max_rounds_per_phase=100)

        assert result is not None, "두 축 다 연속 3라운드 무갱신이면 소진 신호가 떠야 함"
        assert result["attack_exhausted"] is True
        assert result["max_rounds_reached"] is False


def test_one_axis_updating_prevents_exhaustion():
    with tempfile.TemporaryDirectory() as tmp:
        project_id = _setup(Path(tmp))
        pdir = rw.project_dir(project_id)
        journal = pdir / "2026-09-22.md"
        page_file = pdir / "web-페이지-구조.md"
        server_file = pdir / "web-서버-구조.md"
        _start_new_phase(Path(tmp))

        journal.write_text("## Round 1\n", encoding="utf-8")
        page_file.write_text("v1", encoding="utf-8")
        server_file.write_text("v1", encoding="utf-8")
        rw.check_once(project_id, max_rounds_per_phase=100)

        for n in (2, 3, 4):
            journal.write_text(journal.read_text(encoding="utf-8") + f"## Round {n}\n",
                                encoding="utf-8")
            page_file.write_text(f"v{n}", encoding="utf-8")  # 페이지 구조는 계속 갱신됨
            result = rw.check_once(project_id, max_rounds_per_phase=100)

        assert result is None, "한 축이라도 계속 갱신되면 소진 판정 나면 안 됨"


def test_subheading_does_not_inflate_round_count():
    """실측 재현(2026-09-28, google-gruyere-trial): A가 라운드 안에 소제목으로 쓴
    '### Round 6 후속'이 옛 `text.count("## Round ")`(부분문자열 매칭)에 걸려서
    카운트를 부풀렸음 — `###`의 두 번째 `#`부터 시작하면 정확히 `## Round ` 9글자가
    매칭됨. 줄 시작 앵커로 고친 뒤에는 실제 "## Round N" 헤더 2개만 세야 한다."""
    with tempfile.TemporaryDirectory() as tmp:
        project_id = _setup(Path(tmp))
        pdir = rw.project_dir(project_id)
        journal = pdir / "2026-09-22.md"

        journal.write_text(
            "## Round 1 — 2026-09-22T00:00:00Z\n"
            "본문...\n"
            "### Round 6 후속 — 추가 조사\n"  # 실제로 카운트를 부풀렸던 서브헤딩
            "본문...\n"
            "## Round 2 — 2026-09-22T00:10:00Z\n",
            encoding="utf-8",
        )
        assert rw._count_journal_rounds(project_id) == 2, (
            "서브헤딩('### Round N ...')이 섞여 들어가면 실제 라운드 수(2)보다 많이 "
            "세면 안 됨"
        )


if __name__ == "__main__":
    test_round_counting_and_max_rounds()
    test_max_rounds_resets_per_phase_not_cumulative_project()
    test_exhaustion_requires_both_axes_and_real_rounds()
    test_one_axis_updating_prevents_exhaustion()
    test_subheading_does_not_inflate_round_count()
    print("OK — round_watchdog self-check passed")
