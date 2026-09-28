"""mitmproxy addon — 캡처(방식 1) + WAF/rate-limit 감지 + 방식 2 규칙 적용.

근거: etc/레드블루-에이전트-실행가능성-검토.md "웹 프록시(mitmproxy) 도입" 결정,
"Rate-limit/WAF 트립 감지" 결정.

실행: mitmdump -s capture_addon.py  (phase_start.py가 .phase-runtime/current/ 안에서 기동)

경로 규약: 모든 상태 파일은 `$HERMES_HARNESS_ROOT/.phase-runtime/current/` 아래에 둠
(phase_start.py가 생성, phase_end.py가 통째로 삭제 — 이 addon 자신은 안 지움).

전달 방식: WAF 경고/방식2 규칙 결과를 "다음 A 프롬프트에 자동 주입"하지 않는다(Hermes의
동적 파일 주입 지원 여부 미확인) — A가 매 라운드 `terminal`로 이 파일들을 직접 확인한다
(SOUL.md "라운드 판단 규칙" 참고). 이 addon은 그 파일들을 정확히 채워두는 역할까지만.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from mitmproxy import http

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/
from harness_paths import locked_state_file  # noqa: E402
from harness_paths import phase_runtime_dir as _phase_runtime_dir  # noqa: E402

WAF_WINDOW_SEC = 30
WAF_ERROR_RATIO_THRESHOLD = 0.3
WAF_MIN_SAMPLES = 5  # 표본이 너무 적을 때 오탐 방지

# 디렉토리 자체는 phase_start.py가 mitmdump를 띄우기 전에 이미 만들어둠(항상 이 순서를
# 지킨다는 전제) — 여기서 또 mkdir하지 않음, 없으면 그게 오히려 버그 신호.
#
# 락은 harness_paths.locked_state_file()의 공유 구현을 씀(2단계 재검토로 수정) — 원래
# 이 파일 안에서만 락을 정의했었는데, `proxy_rule.py`(A가 별도 프로세스로 실행)가 같은
# proxy_rules.json을 락 없이 건드리고 있어서 이 addon 내부 동시성만 막고 프로세스 간
# 경합은 전혀 못 막고 있었음 — 공통 모듈로 옮겨서 두 프로세스가 같은 락 파일을 쓰게 함.
# `capture.jsonl` append는 순수 추가만이라 락 대상에서 계속 제외(더 빈번하게 불리는데
# 경합의 최악 결과가 파싱 안 되는 로그 한 줄 정도라 직렬화할 만큼 위험하지 않음).


def _capture_path() -> Path:
    return _phase_runtime_dir() / "capture.jsonl"


def _rules_path() -> Path:
    return _phase_runtime_dir() / "proxy_rules.json"


def _waf_status_log_path() -> Path:
    return _phase_runtime_dir() / "_waf_status_log.jsonl"


def _waf_flag_path() -> Path:
    return _phase_runtime_dir() / "waf_warning.flag"


def _to_curl(flow: http.HTTPFlow) -> str:
    req = flow.request
    parts = ["curl", "-s", "-X", req.method, f"'{req.pretty_url}'"]
    for k, v in req.headers.items(multi=True):
        if k.lower() == "content-length":
            continue
        parts.append(f"-H '{k}: {v}'")
    if req.content:
        body = req.get_text(strict=False) or ""
        body = body.replace("'", "'\\''")
        parts.append(f"--data '{body}'")
    return " ".join(parts)


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_rules() -> list[dict]:
    path = _rules_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_rules(rules: list[dict]) -> None:
    _rules_path().write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def _rule_matches(rule: dict, flow: http.HTTPFlow) -> bool:
    match = rule.get("match", {})
    if "method" in match and flow.request.method.upper() != match["method"].upper():
        return False
    url_regex = match.get("url_regex")
    if url_regex and not re.search(url_regex, flow.request.pretty_url):
        return False
    return True


def _rule_expired(rule: dict) -> bool:
    expires_at = rule.get("expires_at")
    if expires_at is None:
        return False
    return time.time() >= expires_at


def _apply_body_replace(text: str, body_replace: list[dict]) -> str:
    for item in body_replace or []:
        text = text.replace(item["find"], item["replace"])
    return text


def _consume_matching_rules(flow: http.HTTPFlow, target: str) -> None:
    """target 단계("request"|"response")에 해당하는, 아직 안 만료/안 소진된 규칙을 적용하고
    적용 횟수를 갱신한다. max_applies 소진 또는 expires_at 경과 규칙은 목록에서 제거한다.
    """
    with locked_state_file("proxy_rules"):
        _consume_matching_rules_locked(flow, target)


def _consume_matching_rules_locked(flow: http.HTTPFlow, target: str) -> None:
    rules = _load_rules()
    if not rules:
        return
    remaining = []
    for rule in rules:
        if _rule_expired(rule):
            continue  # 만료 -> 드롭
        if rule.get("target") != target or not _rule_matches(rule, flow):
            remaining.append(rule)
            continue

        if target == "request":
            if "set_headers" in rule:
                for k, v in rule["set_headers"].items():
                    flow.request.headers[k] = v
            for k in rule.get("remove_headers", []):
                # mitmproxy Headers는 .pop() 지원 여부가 불확실 — del/in만 믿음(둘 다
                # netlib multidict 인터페이스에 항상 있음, 체크리스트 22번에서 실제
                # mitmproxy 버전으로 재확인)
                if k in flow.request.headers:
                    del flow.request.headers[k]
            if "body_replace" in rule:
                text = flow.request.get_text(strict=False) or ""
                flow.request.text = _apply_body_replace(text, rule["body_replace"])
        else:  # response
            if "set_status" in rule:
                flow.response.status_code = rule["set_status"]
            if "set_headers" in rule:
                for k, v in rule["set_headers"].items():
                    flow.response.headers[k] = v
            for k in rule.get("remove_headers", []):
                if k in flow.response.headers:
                    del flow.response.headers[k]
            if "body_replace" in rule:
                text = flow.response.get_text(strict=False) or ""
                flow.response.text = _apply_body_replace(text, rule["body_replace"])

        rule["applied_count"] = rule.get("applied_count", 0) + 1
        if rule["applied_count"] < rule.get("max_applies", 1):
            remaining.append(rule)
        # max_applies 도달 -> remaining에 안 넣어서 드롭(자동 비활성화)

    _save_rules(remaining)


def _check_waf(status_code: int) -> None:
    with locked_state_file("waf_log"):
        _check_waf_locked(status_code)


def _check_waf_locked(status_code: int) -> None:
    now = time.time()
    log_path = _waf_status_log_path()
    entries = []
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            # 2단계 재검토로 수정: 한 줄이라도 깨지면 try/except가 전체 루프를 감싸고
            # 있어서 롤링 윈도우 전체가 날아갔음 — 깨진 줄 하나만 건너뛰도록 개별 처리
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries.append({"t": now, "status": status_code})
    entries = [e for e in entries if now - e["t"] <= WAF_WINDOW_SEC]

    with log_path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    if len(entries) < WAF_MIN_SAMPLES:
        return
    error_count = sum(1 for e in entries if e["status"] in (403, 429))
    ratio = error_count / len(entries)
    flag_path = _waf_flag_path()
    if ratio >= WAF_ERROR_RATIO_THRESHOLD:
        flag_path.write_text(
            f"최근 {WAF_WINDOW_SEC}초 동안 요청의 {ratio:.0%}가 403/429 응답 "
            f"({error_count}/{len(entries)}) — 대상이 rate-limit/WAF를 걸고 있을 수 있음.\n",
            encoding="utf-8",
        )
    elif flag_path.exists():
        flag_path.unlink()  # 상황이 정상화되면 플래그도 내림


def request(flow: http.HTTPFlow) -> None:
    _consume_matching_rules(flow, target="request")


def response(flow: http.HTTPFlow) -> None:
    _consume_matching_rules(flow, target="response")

    record = {
        "timestamp": time.time(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "request_headers": dict(flow.request.headers),
        "request_body": flow.request.get_text(strict=False),
        "response_status": flow.response.status_code,
        "response_headers": dict(flow.response.headers),
        "response_body": flow.response.get_text(strict=False),
        "curl": _to_curl(flow),
    }
    _append_jsonl(_capture_path(), record)

    _check_waf(flow.response.status_code)
