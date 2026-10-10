from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "iios_one_click_readiness_ui_v01.py"
SPEC = importlib.util.spec_from_file_location("iios_one_click_readiness_ui_v01", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_chinese_report_is_readable_and_disclaims_execution() -> None:
    report = {
        "status": "BLOCKED",
        "case_id": "RC-CN-A-605016-20261009",
        "canonical_git_head": "abc",
        "generated_at": "2026-10-10T00:00:00Z",
        "company_case_manifest_present": True,
        "request_bundle_candidates": [],
        "admission_root": {"usable": False},
        "b2": {
            "evidence_admission": False,
            "pit_admission": False,
            "missing_required_field_groups": ["market_price"],
            "current_blocker_reason": "The current price source is not admitted.",
        },
        "blockers": [
            {"id": "CANONICAL_REQUEST_BUNDLE_NOT_FOUND", "finding": "missing", "next": "stage it"},
            {"id": "CANONICAL_ADMISSION_ROOT_NOT_PROVISIONED", "finding": "missing", "next": "provision"},
            {"id": "B2_EVIDENCE_PIT_NOT_ADMITTED", "finding": "blocked", "next": "resolve"},
        ],
    }
    markdown = MODULE.render_chinese(report)
    assert "一键预检报告" in markdown
    assert "找不到该公司的正式 canonical request bundle" in markdown
    assert "没有可用的正式 admission 根目录" in markdown
    assert "market_price" in markdown
    assert "没有调用 ChatGPT" in markdown
    assert "没有运行正式投资决策链" in markdown
