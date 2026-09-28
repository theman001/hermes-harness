"""Jev(TypeSafe AI) API 클라이언트 — choice/score/noul 판단 요청 얇은 래퍼.

공식 스펙(etc/레드블루-에이전트-실행가능성-검토.md "결정 완료(2026-09-28)" 참고):
POST https://api.typesafe.ai/v1/systemone, Bearer 인증, {model, state, questions} ->
{model, answers, usage}. **self-host 옵션 없음(API 전용)** — 호출할 때마다 state에 담긴
내용이 TypeSafe 클라우드로 나간다는 걸 항상 인지할 것. own_system/공개 테스트 대상
한정(체크리스트 34) — 실제 버그바운티 대상 정보는 여기로 보내지 않는다.

`requests` 등 추가 의존성 없이 표준 라이브러리(urllib)만 사용.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"


class JevKeyMissing(RuntimeError):
    """TYPESAFE_API_KEY가 없을 때 발생 — 호출부는 이걸 "아직 키가 없다"는 신호로 다루고
    dry-run으로 전환해야 한다(Jev API 키 발급은 추후 진행하기로 확정된 상태, PROGRESS.md
    2026-09-28)."""


def call_systemone(
    state: str | dict,
    questions: dict,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: float = 30.0,
) -> dict:
    """`state`+`questions`를 Jev에 보내고 `{model, answers, usage}` 응답을 그대로 반환."""
    api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise JevKeyMissing(
            "TYPESAFE_API_KEY 미설정 — console.typesafe.ai에서 발급 후 .env에 추가할 것"
        )

    payload = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Jev API {e.code}: {body}") from e
