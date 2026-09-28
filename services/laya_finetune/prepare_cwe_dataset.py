"""Laya 파인튜닝 1단계(공개 데이터셋 웜스타트) 준비 — 체크리스트 35(a)
(etc/레드블루-에이전트-실행가능성-검토.md).

`Dunateo/VulnDesc_CWE_Mapping`(HF, 2601건, {text, label} — label은 "CWE-89 SQL
Injection" 형식)을 Laya의 파인튜닝 스키마({state, questions, gold} JSON 컬럼 3개,
GitHub NandhaKishorM/laya 파인튜닝 노트북 확인)로 변환한다.

**분류 체계는 CWE 원본 그대로 안 씀** — Laya 자신의 모델카드가 "choice 옵션이 ~20개
넘으면 정확도가 크게 떨어진다"고 명시하는데, 이 데이터셋의 원본 CWE는 종류가 훨씬
많고(버퍼오버플로우 등 웹 무관 항목 다수 포함) 우리 도메인(웹 침투테스트 공격 기법
선택)과도 안 맞음 — 그래서 `red/SOUL.md`가 이미 다루는 공격 유형 위주로 14개 카테고리로
축소 매핑하고, 안 맞는 CWE는 버린다(억지로 "기타" 버킷에 다 몰아넣지 않음 — 그러면
그 버킷이 제일 큰 잡음 클래스가 돼서 나머지 13개 구분을 오히려 방해함). 매핑표는
잘 알려진 CWE ID 기준이라 완벽하지 않을 수 있음 — 실제 파인튜닝 결과 보고 카테고리
조정 여지 있음.

`requests`/`datasets` 패키지 없이 표준 라이브러리(urllib)만 사용, HF의
datasets-server REST API를 페이지네이션으로 호출.

사용:
    python prepare_cwe_dataset.py [--limit N] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

DATASET = "Dunateo/VulnDesc_CWE_Mapping"
PAGE_SIZE = 100
DEFAULT_OUT = Path(__file__).resolve().parent / "data" / "cwe_warmstart.jsonl"

# CWE ID(숫자만) -> 우리 14개 공격 기법 카테고리. 근거: SOUL.md의 ROI 분류 + 흔한 웹
# 취약점 유형. 여기 없는 CWE는 우리 도메인 밖(버퍼오버플로우 등)으로 간주해 버린다.
CWE_TO_CATEGORY = {
    "89": "sqli",
    "564": "sqli",
    "79": "xss",
    "80": "xss",
    "22": "lfi_path_traversal",
    "23": "lfi_path_traversal",
    "36": "lfi_path_traversal",
    "73": "lfi_path_traversal",
    "98": "lfi_path_traversal",
    "918": "ssrf",
    "77": "rce_command_injection",
    "78": "rce_command_injection",
    "94": "rce_command_injection",
    "95": "rce_command_injection",
    "287": "auth_bypass",
    "306": "auth_bypass",
    "384": "auth_bypass",
    "613": "auth_bypass",
    "798": "auth_bypass",
    "639": "access_control",
    "862": "access_control",
    "863": "access_control",
    "284": "access_control",
    "285": "access_control",
    "566": "access_control",
    "352": "csrf",
    "601": "open_redirect",
    "611": "xxe",
    "776": "xxe",
    "502": "deserialization",
    "200": "info_disclosure",
    "209": "info_disclosure",
    "538": "info_disclosure",
}

CATEGORY_DESCRIPTIONS = {
    "sqli": "SQL Injection — 사용자 입력이 SQL 쿼리에 그대로 삽입됨",
    "xss": "Cross-Site Scripting — 사용자 입력이 검증 없이 HTML/JS로 반영됨",
    "lfi_path_traversal": "Local File Inclusion / Path Traversal — 경로 조작으로 임의 파일 접근",
    "ssrf": "Server-Side Request Forgery — 서버가 공격자가 지정한 내부/외부 URL로 요청",
    "rce_command_injection": "RCE / Command Injection — 임의 코드/쉘 명령 실행",
    "auth_bypass": "인증/세션 우회 — 로그인·세션·자격증명 관련 결함",
    "access_control": "접근 제어 결함 (IDOR/권한 상승) — 인가 없이 자원/기능 접근",
    "csrf": "Cross-Site Request Forgery — 사용자 의도 없는 상태변경 요청 위조",
    "open_redirect": "Open Redirect — 검증 없는 리다이렉트 목적지",
    "xxe": "XML External Entity — XML 파서가 외부 엔티티를 처리",
    "deserialization": "Insecure Deserialization — 신뢰할 수 없는 데이터 역직렬화",
    "info_disclosure": "정보 노출 — 민감 정보/디버그 정보가 응답에 노출",
}


def fetch_rows(limit: int | None = None) -> list[dict]:
    rows = []
    offset = 0
    while True:
        page_len = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(rows))
        if page_len <= 0:
            break
        url = (
            "https://datasets-server.huggingface.co/rows?dataset="
            f"{DATASET}&config=default&split=train&offset={offset}&length={page_len}"
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read())
        page_rows = [r["row"] for r in payload["rows"]]
        if not page_rows:
            break
        rows.extend(page_rows)
        offset += len(page_rows)
        if limit is not None and len(rows) >= limit:
            break
        if offset >= payload.get("num_rows_total", offset):
            break
    return rows


def label_to_category(label: str) -> str | None:
    m = re.match(r"CWE-(\d+)", label)
    return CWE_TO_CATEGORY.get(m.group(1)) if m else None


def build_questions() -> dict:
    return {
        "attack_category": {
            "type": "choice",
            "instructions": "이 취약점 설명에 가장 잘 맞는 공격 기법 카테고리는?",
            "criteria": CATEGORY_DESCRIPTIONS,
        }
    }


def to_laya_case(text: str, category: str) -> dict:
    return {
        "state": json.dumps(text, ensure_ascii=False),
        "questions": json.dumps(build_questions(), ensure_ascii=False),
        "gold": json.dumps(
            {"attack_category": {"label": category}}, ensure_ascii=False
        ),
    }


def convert(rows: list[dict]) -> tuple[list[dict], Counter]:
    kept = []
    dist = Counter()
    for row in rows:
        category = label_to_category(row["label"])
        if category is None:
            dist["_discarded"] += 1
            continue
        kept.append(to_laya_case(row["text"], category))
        dist[category] += 1
    return kept, dist


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="가져올 원본 행 수 제한")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = fetch_rows(limit=args.limit)
    cases, dist = convert(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"원본 {len(rows)}건 중 {len(cases)}건 채택, {dist['_discarded']}건 폐기(도메인 밖 CWE)")
    print("카테고리 분포:")
    for cat, n in sorted(dist.items(), key=lambda kv: -kv[1]):
        if cat != "_discarded":
            print(f"  {cat}: {n}")
    print(f"출력: {args.out}")


if __name__ == "__main__":
    main()
