"""max_rounds_per_phase 강제 + 공격 경로 소진 감지.

근거: etc/레드블루-에이전트-실행가능성-검토.md "공격 경로 소진 판단 기준 구체화" 결정.
Hermes에 내장 라운드 상한이 없어서 외부 워치독으로 만듦(A가 스스로 세는 게 아니라 이
프로세스가 기계적으로 셈 — "무근거 자기판단을 없애자"는 이 기준 자체의 취지 때문).

동작 방식: phase_start.py가 이 스크립트를 백그라운드 프로세스로 띄운다(A가 직접 호출하는
게 아님 — A는 그냥 결과 파일만 읽는다). journal/web/<project_id>/ 안의 라운드별 일지
파일들의 mtime을 폴링해서 "새 라운드가 기록됐다"를 감지하고, 그때마다 라운드 카운터와
웹 구조 파일 diff를 갱신한다.

경로 규약 — 두 상태를 분리 저장(2026-09-22 자체 재검토: project가 여러 phase에 걸치면
phase 로컬에 둔 소진 카운터가 리셋되는 버그를 피하기 위함):
  - 라운드 카운터(이번 phase에서 지금까지 몇 라운드): 진짜 phase-scoped라
    `.phase-runtime/current/round_count.json`. **journal 파일 자체는 project 누적이라서
    (2단계 4차 재검토로 발견한 버그) 그대로 세면 이전 phase 라운드까지 섞임** —
    `round_count_baseline.json`(phase 시작 시점의 누적 라운드 수, self-init)을 빼서
    이번 phase만의 라운드 수를 구함(`_get_or_init_phase_baseline` 참고).
  - 소진 추적 상태(무갱신 카운터, 이전 라운드 구조파일 스냅샷): project 전체에 걸쳐
    누적돼야 하는 값이라 `journal/web/<project_id>/exhaustion_state.json`(project
    레벨, phase_end.py의 cleanup 대상 아님) — 이쪽은 baseline을 안 빼고 project 누적
    그대로 쓰는 게 맞음(project 전체 상태이므로).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import phase_runtime_dir, project_dir  # noqa: E402

POLL_INTERVAL_SEC = 5
EXHAUSTION_THRESHOLD = 3  # 연속 무갱신 라운드 수


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


_JOURNAL_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def _count_journal_rounds(project_id: str) -> int:
    """journal/web/<project_id>/*.md 안의 '## Round N' 헤더 총 개수를 센다.

    write-journal-entry Skill이 남기는 포맷(SKILL.md 참고)에 맞춰 카운트. **날짜 파일명
    패턴만 화이트리스트로 집계**(2단계 검토로 수정) — 처음엔 HANDOFF.md/web-*/PoC-*/
    Exploit-* 를 블랙리스트로 제외하는 식이었는데, organize-exploit-artifacts가 만드는
    "그 외 자유 파일명"(SKILL.md 참고)이 우연히 "## Round "라는 문자열을 포함하면 카운트가
    부풀려질 수 있었음 — 알려진 라운드 일지 파일명 형식(`YYYY-MM-DD.md`)만 믿는 게 안전.

    **줄 시작 앵커 추가(2026-09-28, 실측 재현 후 수정)**: `text.count("## Round ")`는
    부분문자열 매칭이라, A가 라운드 안에서 소제목으로 쓴 `### Round 6 후속`도 카운트에
    잡혔음(`###` 안의 두 번째 `#`부터 시작하면 정확히 `## Round ` 9글자가 매칭됨 —
    `google-gruyere-trial`에서 실제로 발생, A 자신이 발견). 줄 시작이 정확히 `## Round `
    (앞에 `#`가 하나 더 있으면 제외)인 줄만 세도록 수정.
    """
    pdir = project_dir(project_id)
    if not pdir.exists():
        return 0
    total = 0
    for md in pdir.glob("*.md"):
        if not _JOURNAL_FILENAME_RE.match(md.name):
            continue  # 라운드 일지가 아닌 다른 산출물 제외
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        total += sum(1 for line in text.splitlines() if line.startswith("## Round "))
    return total


def _get_or_init_phase_baseline(project_id: str) -> int:
    """이번 phase 시작 시점의 project 누적 라운드 수(2단계 재검토로 추가) — `max_rounds_
    per_phase`는 "이번 phase만의 라운드 수"와 비교해야 하는데, `_count_journal_rounds`는
    journal 파일 전체(모든 이전 phase 포함)를 세므로 그대로 쓰면 project가 여러 phase에
    걸칠 때 이전 phase들의 누적 라운드까지 이번 phase 카운트에 섞여서 상한을 훨씬 일찍
    잘못 트리거하는 버그가 있었음(예: phase 1이 25라운드에서 끝났으면 phase 2는 5라운드
    만에 "누적 30"으로 잘못 종료됨). `.phase-runtime/current/`는 phase마다 새로 생기므로
    "파일이 없으면 지금 이 순간의 누적 카운트를 baseline으로 기록"하는 방식으로 self-init.
    """
    path = phase_runtime_dir() / "round_count_baseline.json"
    cached = _read_json(path, None)
    if cached is not None:
        return cached["baseline"]
    baseline = _count_journal_rounds(project_id)
    _write_json(path, {"baseline": baseline})
    return baseline


def check_once(project_id: str, max_rounds_per_phase: int) -> dict | None:
    """한 번 확인해서 상태 파일들을 갱신한다. 종료 신호가 뜨면 그 dict를 반환, 아니면 None.

    폴링 주기(5초)와 실제 "라운드"는 속도가 다르므로(A가 한 라운드에 5초보다 훨씬 오래
    걸릴 수 있음), 소진 추적(무갱신 카운터)은 매 폴링 틱이 아니라 **누적 라운드 수가 실제로
    증가했을 때만** 전진시킨다 — 안 그러면 폴링 틱 수가 라운드 수보다 훨씬 많아져서
    "연속 3라운드 무갱신"이 실제 라운드 기준이 아니라 시간 기준으로 잘못 판정된다.
    """
    pdir = project_dir(project_id)
    rt_dir = phase_runtime_dir()

    # 1. 라운드 카운터 — total은 project 누적(exhaustion 추적용), round_count는
    #    baseline을 뺀 "이번 phase만의 라운드 수"(max_rounds_per_phase 비교용)
    total_rounds = _count_journal_rounds(project_id)
    baseline = _get_or_init_phase_baseline(project_id)
    round_count = total_rounds - baseline
    _write_json(rt_dir / "round_count.json", {"round_count": round_count})
    max_rounds_reached = round_count >= max_rounds_per_phase

    # 2. 소진 추적 상태 (project 레벨) — total_rounds가 실제로 늘었을 때만 갱신
    #    (exhaustion_state는 phase 경계와 무관한 project 전체 누적 상태라 total 기준이 맞음)
    exhaustion_path = pdir / "exhaustion_state.json"
    state = _read_json(
        exhaustion_path,
        {"last_round_count": 0,
         "page_structure": {"hash": None, "stale_rounds": 0, "seen": False},
         "server_structure": {"hash": None, "stale_rounds": 0, "seen": False}},
    )

    if total_rounds > state["last_round_count"]:
        state["last_round_count"] = total_rounds
        for key, filename in (
            ("page_structure", "web-페이지-구조.md"),
            ("server_structure", "web-서버-구조.md"),
        ):
            axis = state[key]
            current_hash = _file_hash(pdir / filename)
            if current_hash is None:
                # 아직 파일 자체가 없음(recon 0단계 완료 전) — 무갱신으로 카운트하지 않음
                continue
            if not axis["seen"]:
                # 이번에 처음 생김 — 베이스라인만 잡고 카운트 시작은 다음 라운드부터
                axis["hash"] = current_hash
                axis["seen"] = True
                axis["stale_rounds"] = 0
            elif current_hash == axis["hash"]:
                axis["stale_rounds"] += 1
            else:
                axis["hash"] = current_hash
                axis["stale_rounds"] = 0

        _write_json(exhaustion_path, state)

    page_exhausted = state["page_structure"]["stale_rounds"] >= EXHAUSTION_THRESHOLD
    server_exhausted = state["server_structure"]["stale_rounds"] >= EXHAUSTION_THRESHOLD
    attack_exhausted = page_exhausted and server_exhausted

    if not (max_rounds_reached or attack_exhausted):
        return None

    reason = {
        "max_rounds_reached": max_rounds_reached,
        "attack_exhausted": attack_exhausted,
        "round_count": round_count,
        "max_rounds_per_phase": max_rounds_per_phase,
    }
    _write_json(rt_dir / "termination_reason.json", reason)
    return reason


def run(project_id: str, max_rounds_per_phase: int) -> None:
    """phase_start.py가 백그라운드로 띄우는 폴링 루프. 종료 신호가 뜨면 계속 돌되(A가 마무리
    시퀀스를 끝낼 때까지) 이미 낸 신호를 덮어쓰지 않는다 — phase_end.py가 프로세스를 죽인다.
    """
    signaled = False
    while True:
        if not signaled:
            reason = check_once(project_id, max_rounds_per_phase)
            if reason is not None:
                signaled = True
        time.sleep(POLL_INTERVAL_SEC)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    parser.add_argument("max_rounds_per_phase", type=int)
    parser.add_argument("--once", action="store_true", help="한 번만 확인하고 종료(테스트용)")
    args = parser.parse_args()

    if args.once:
        result = check_once(args.project_id, args.max_rounds_per_phase)
        print(json.dumps(result, ensure_ascii=False) if result else "null")
        return

    run(args.project_id, args.max_rounds_per_phase)


if __name__ == "__main__":
    main()
