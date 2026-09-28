"""prepare_cwe_dataset.py 최소 self-check(네트워크 없이 매핑/변환 로직만).

실행: python test_prepare_cwe_dataset.py
"""

from __future__ import annotations

import json

import prepare_cwe_dataset as pcd


def test_label_to_category_known_and_unknown_cwe():
    assert pcd.label_to_category("CWE-89 SQL Injection") == "sqli"
    assert pcd.label_to_category("CWE-79 Cross-site Scripting") == "xss"
    assert pcd.label_to_category("CWE-601 URL Redirection to Untrusted Site") == "open_redirect"
    # 웹 무관(버퍼오버플로우)은 우리 카테고리에 없음 -> 버려야 함
    assert pcd.label_to_category("CWE-125 Out-of-bounds Read") is None
    assert pcd.label_to_category("not a cwe label") is None


def test_convert_discards_unmapped_and_produces_valid_laya_schema():
    rows = [
        {"text": "user input concatenated into SQL query", "label": "CWE-89 SQL Injection"},
        {"text": "heap overflow in decoder", "label": "CWE-122 Heap-based Buffer Overflow"},
        {"text": "reflected script tag in response", "label": "CWE-79 Cross-site Scripting"},
    ]
    cases, dist = pcd.convert(rows)

    assert len(cases) == 2  # 버퍼오버플로우 1건은 폐기됨
    assert dist["_discarded"] == 1
    assert dist["sqli"] == 1
    assert dist["xss"] == 1

    case = cases[0]
    state = json.loads(case["state"])
    questions = json.loads(case["questions"])
    gold = json.loads(case["gold"])
    assert state == "user input concatenated into SQL query"
    assert questions["attack_category"]["type"] == "choice"
    assert gold["attack_category"]["label"] == "sqli"
    # criteria(선택지)가 14개 카테고리 그 어떤 것보다 많아지지 않는지(Laya의 "~20개
    # 넘으면 정확도 급락" 제약 대비 여유 확인)
    assert len(questions["attack_category"]["criteria"]) <= 20


if __name__ == "__main__":
    test_label_to_category_known_and_unknown_cwe()
    test_convert_discards_unmapped_and_produces_valid_laya_schema()
    print("OK — prepare_cwe_dataset self-check passed")
