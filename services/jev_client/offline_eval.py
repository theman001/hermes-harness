"""Jev 오프라인 정확도 검증 — 체크리스트 34 (etc/레드블루-에이전트-실행가능성-검토.md).

이미 라이브로 끝난 project(`testasp-vulnweb-full` 등)의 recon 후보 목록을 다시 Jev에
태워서, "Jev가 유망하다고 고른 후보가 실제로 그때 확정된 취약점과 얼마나 겹치는지"를
Hermes/Mattermost/승인흐름 전혀 안 거치고 순수 오프라인으로 확인한다. Jev API 키
발급은 추후 진행이라(PROGRESS.md 2026-09-28), `TYPESAFE_API_KEY`가 없으면 자동으로
dry-run(실제 호출 없이 페이로드만 구성해서 출력)으로 전환된다.

**라벨(ground truth) 출처와 그 한계**: `PoC-코드.md`(project별로 사람이 "가장 깔끔한
최소 재현"만 골라 담은 문서)의 `## N. <제목> — <path>` 헤더에서 확정된 취약점의 경로를
뽑아 정답셋으로 쓴다. recon_summary.json의 discovered_endpoints와 자유 형식 경로
문자열이라 정확히 안 맞을 수 있어, **경로의 스크립트 이름 부분만(base path, 쿼리스트링/
주석 제외) 대소문자 무시하고 매칭**한다 — 완벽한 정답이 아니라 "실제로 exploit까지
이어진 경로인가"의 실용적 근사치임을 감안할 것. attempted_exploits.json의 키 이름은
"_confirmed"/"_verified"/한글 설명 등으로 표기가 제각각이라(실제 확인함) 정답 소스로
쓰기엔 너무 불규칙해서 PoC-코드.md만 쓴다.

사용:
    python offline_eval.py <project_id> [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import project_dir  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev_client import JevKeyMissing, call_systemone  # noqa: E402

_PATH_RE = re.compile(r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+")


def base_path(raw: str) -> str | None:
    """자유 형식 경로 문자열에서 `/foo/bar.ext` 부분만 뽑아 소문자로 정규화."""
    m = _PATH_RE.search(raw.replace("`", ""))
    return m.group(0).split("?")[0].lower() if m else None


def load_candidates(project_id: str) -> list[dict]:
    """recon_summary.json의 discovered_endpoints를 {path, description} 리스트로 정규화.
    항목이 plain string이거나 {path, method, note} dict인 두 형태가 실제로 섞여 있다."""
    summary = json.loads((project_dir(project_id) / "recon_summary.json").read_text())
    candidates = []
    for entry in summary.get("discovered_endpoints", []):
        if isinstance(entry, dict):
            desc = f"{entry.get('method', 'GET')} {entry['path']} — {entry.get('note', '')}"
            raw_path = entry["path"]
        else:
            desc = entry
            raw_path = entry
        bp = base_path(raw_path)
        if bp:
            candidates.append({"path": bp, "description": desc.strip()})
    return candidates


def load_confirmed_paths(project_id: str) -> set[str]:
    """PoC-코드.md의 `## N. ... — path` 헤더에서 확정된 취약점 경로 집합을 뽑음."""
    poc_file = project_dir(project_id) / "PoC-코드.md"
    confirmed = set()
    for line in poc_file.read_text().splitlines():
        if line.startswith("## ") and re.match(r"## \d+\.", line):
            bp = base_path(line)
            if bp:
                confirmed.add(bp)
    return confirmed


def build_questions() -> dict:
    return {
        "is_likely_vuln": {
            "type": "noul",
            "instructions": (
                "이 웹 엔드포인트가 실제로 익스플로잇 가능한 취약점으로 이어질 "
                "가능성이 높은가? 이미 알려진 CMS/프레임워크 취약점 패턴, 사용자 입력이 "
                "그대로 반영되는 파라미터, 관리자/설정 파일 노출 패턴 등을 근거로 판단하라."
            ),
        }
    }


def evaluate(
    project_id: str,
    *,
    api_key: str | None = None,
    model: str = "jev-latest",
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    tech_stack = json.loads(
        (project_dir(project_id) / "recon_summary.json").read_text()
    ).get("tech_stack", [])
    candidates = load_candidates(project_id)
    if limit:
        candidates = candidates[:limit]
    confirmed = load_confirmed_paths(project_id)
    questions = build_questions()

    results = []
    for c in candidates:
        state = f"tech_stack={tech_stack}\nendpoint={c['path']}\nnote={c['description']}"
        gold = c["path"] in confirmed
        row = {"path": c["path"], "gold_confirmed": gold, "state": state}

        try:
            if dry_run:
                raise JevKeyMissing("--dry-run 지정됨")
            answer = call_systemone(state, questions, api_key=api_key, model=model)
            p_true = answer["answers"]["is_likely_vuln"]["probabilities"]["true"]
            row["jev_p_true"] = p_true
            row["jev_predicted"] = p_true >= 0.5
        except JevKeyMissing as e:
            row["dry_run"] = True
            row["skip_reason"] = str(e)
        results.append(row)

    evaluated = [r for r in results if "jev_predicted" in r]
    correct = sum(1 for r in evaluated if r["jev_predicted"] == r["gold_confirmed"])
    return {
        "project_id": project_id,
        "total_candidates": len(candidates),
        "confirmed_paths": sorted(confirmed),
        "evaluated": len(evaluated),
        "accuracy": (correct / len(evaluated)) if evaluated else None,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = evaluate(args.project_id, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["accuracy"] is None:
        print(
            f"\n(dry-run — {report['total_candidates']}개 후보 중 실제 Jev 호출 0건. "
            "TYPESAFE_API_KEY 발급 후 --dry-run 없이 재실행할 것)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
