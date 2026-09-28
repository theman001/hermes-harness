"""방식 2(라이브 위변조) 규칙 관리 CLI — add / list / remove / clear.

근거: etc/레드블루-에이전트-실행가능성-검토.md "웹 프록시 도입" 결정.
A가 terminal 도구로 직접 호출. `proxy_rule.py add`는 반드시 approvals.deny에 등록해서
Mattermost 승인을 거치게 함(체크리스트 25/27번) — add 외 명령은 승인 불필요.

규칙 파일 위치: `$HERMES_HARNESS_ROOT/.phase-runtime/current/proxy_rules.json`
(capture_addon.py가 매 flow마다 다시 읽음).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import locked_state_file, phase_runtime_dir  # noqa: E402


def _rules_path() -> Path:
    d = phase_runtime_dir()
    d.mkdir(parents=True, exist_ok=True)  # A가 직접 부르는 CLI라 방어적으로 유지
    return d / "proxy_rules.json"


def _load() -> list[dict]:
    path = _rules_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(rules: list[dict]) -> None:
    _rules_path().write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_add(args: argparse.Namespace) -> None:
    rule: dict = {
        "id": str(uuid.uuid4())[:8],
        "target": args.target,
        "match": {},
        "max_applies": args.max_applies,
        "expires_at": time.time() + args.ttl,
        "applied_count": 0,
    }
    if args.url_regex:
        rule["match"]["url_regex"] = args.url_regex
    if args.method:
        rule["match"]["method"] = args.method
    if args.set_status is not None:
        rule["set_status"] = args.set_status
    if args.body_replace:
        find, _, replace = args.body_replace.partition(":")
        rule["body_replace"] = [{"find": find, "replace": replace}]

    # 2단계 재검토로 락 추가 — mitmproxy(capture_addon.py, 별도 프로세스)가 같은 파일을
    # 동시에 읽고 쓸 수 있어서, 이 CLI 쪽에서도 락 없이 저장하면 서로 쓰기를 덮어써서
    # 방금 추가한 규칙이 사라지거나 mitmproxy가 갱신한 applied_count가 유실될 수 있었음.
    with locked_state_file("proxy_rules"):
        rules = _load()
        rules.append(rule)
        _save(rules)
    print(f"규칙 추가됨: id={rule['id']}, target={rule['target']}, "
          f"max_applies={rule['max_applies']}, ttl={args.ttl}s")


def cmd_list(_args: argparse.Namespace) -> None:
    with locked_state_file("proxy_rules"):
        rules = _load()
    if not rules:
        print("(활성 규칙 없음)")
        return
    now = time.time()
    for r in rules:
        remaining = max(0, int(r.get("expires_at", now) - now))
        print(f"- {r['id']}: target={r['target']} match={r.get('match')} "
              f"applied={r.get('applied_count', 0)}/{r.get('max_applies', 1)} "
              f"만료까지 {remaining}s")


def cmd_remove(args: argparse.Namespace) -> None:
    with locked_state_file("proxy_rules"):
        rules = _load()
        remaining = [r for r in rules if r["id"] != args.rule_id]
        if len(remaining) == len(rules):
            print(f"id={args.rule_id} 규칙을 못 찾음")
            return
        _save(remaining)
    print(f"규칙 제거됨: {args.rule_id}")


def cmd_clear(_args: argparse.Namespace) -> None:
    with locked_state_file("proxy_rules"):
        _save([])
    print("전체 규칙 무효화됨(킬스위치)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="새 위변조 규칙 등록 (approvals.deny 대상)")
    p_add.add_argument("--target", choices=["request", "response"], required=True)
    p_add.add_argument("--url-regex", default=None)
    p_add.add_argument("--method", default=None)
    p_add.add_argument("--set-status", type=int, default=None)
    p_add.add_argument("--body-replace", default=None,
                        help="'찾을문자열:바꿀문자열' 형태(콜론 하나로 구분)")
    p_add.add_argument("--max-applies", type=int, default=1)
    p_add.add_argument("--ttl", type=int, default=300, help="초 단위 만료 시간(기본 300초)")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="활성 규칙 목록")
    p_list.set_defaults(func=cmd_list)

    p_remove = sub.add_parser("remove", help="특정 규칙 제거")
    p_remove.add_argument("rule_id")
    p_remove.set_defaults(func=cmd_remove)

    p_clear = sub.add_parser("clear", help="전체 규칙 즉시 무효화(킬스위치)")
    p_clear.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
