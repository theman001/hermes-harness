"""phase_start.py self-check: `is_resuming_project`(2단계 전체 재검토로 발견한 버그의
회귀 테스트) + `step3_update_model_endpoint`(2026-09-23 phase_start_local.py 추가로
base_url/api_key 옵션 인자가 생긴 것에 대한 회귀 테스트).

실행: python test_phase_start.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import phase_start as ps


def test_resuming_detected_without_test_account():
    """원래 `load_test_account(...) is not None`으로 판단했었는데, 로그인이 필요 없는
    타겟은 test_account.json이 애초에 안 생겨서 phase가 몇 번을 거쳐도 resuming=False로
    잘못 판정됐음 — project journal 폴더 존재 여부(project_dir)로 판단해야
    test_account.json 유무와 무관하게 정확하다."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        project_id = "no-login-target"

        assert ps.is_resuming_project(project_id) is False, "첫 phase는 resuming 아니어야 함"

        pdir = ps.project_dir(project_id)
        pdir.mkdir(parents=True)
        (pdir / "2026-09-22.md").write_text("## Round 1\n", encoding="utf-8")

        assert ps.load_test_account(project_id) is None, \
            "로그인 없는 타겟이라 test_account.json은 여전히 없어야 함"
        assert ps.is_resuming_project(project_id) is True, (
            "journal 폴더가 이미 있으면(이전 phase가 라운드를 남겼으면) test_account.json "
            "유무와 무관하게 resuming=True여야 함 — 아니면 A가 기존 기록을 안 읽고 처음부터 "
            "다시 시작하는 버그가 재현됨"
        )


def test_update_model_endpoint_leaves_unset_fields_untouched():
    """base_url/api_key/provider를 안 넘기면(기존 Colab 경로) model 이름(`default` 키)만
    바뀌고 나머지는 그대로, 넘기면(phase_start_local.py 경로) 다 바뀌는지 확인.

    2026-09-23 하네스 실측(`hermes doctor`)으로 발견: 원래 `model_id`/`provider:
    openai_compatible`이 둘 다 실재하지 않는 키/값이었음 — 실제 키는 `default`(모델 이름),
    `provider: "custom"`(커스텀 OpenAI 호환 엔드포인트) 또는 named provider(`"deepseek"` 등).
    """
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HERMES_HARNESS_ROOT"] = tmp
        config_path = Path(tmp) / "red" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            'model:\n'
            '  provider: "custom"\n'
            '  base_url: "http://localhost:8000/v1"\n'
            '  default: "old-model"\n'
            '  api_key: "not-required"\n',
            encoding="utf-8",
        )

        ps.step3_update_model_endpoint("new-model")
        text = config_path.read_text(encoding="utf-8")
        assert 'default: "new-model"' in text
        assert 'base_url: "http://localhost:8000/v1"' in text, \
            "base_url 미지정이면 Colab 경로 그대로 안 건드려야 함"
        assert 'api_key: "not-required"' in text, \
            "api_key 미지정이면 그대로 안 건드려야 함"
        assert 'provider: "custom"' in text, \
            "provider 미지정이면 그대로 안 건드려야 함"

        ps.step3_update_model_endpoint("deepseek-chat", provider="deepseek")
        text = config_path.read_text(encoding="utf-8")
        assert 'default: "deepseek-chat"' in text
        assert 'provider: "deepseek"' in text, \
            "phase_start_local.py 경로에서는 provider도 named provider로 바뀌어야 함"
        assert 'base_url: "http://localhost:8000/v1"' in text, \
            "deepseek는 named provider라 base_url을 안 건드려도 됨(그대로 유지 확인)"


if __name__ == "__main__":
    test_resuming_detected_without_test_account()
    test_update_model_endpoint_leaves_unset_fields_untouched()
    print("OK — phase_start self-check passed")
