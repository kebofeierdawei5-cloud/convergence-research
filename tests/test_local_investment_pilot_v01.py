from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from datetime import date
from pathlib import Path
import subprocess
import threading
import time as _time

import pytest

import iios_mvp.local_investment_pilot_v01 as pilot
from iios_mvp.operating_driver_forecast_v01 import render_operating_driver_section, evaluate_operating_driver_forecast

from iios_mvp.local_investment_pilot_v01 import (
    LocalInvestmentPilotError,
    PILOT_SCHEMA,
    _normalize_guided_symbol,
    _previous_weekday,
    _read_json_response_file,
    _response_file_signature,
    _wait_for_response_file_change,
    _analyse,
    _prepare_input,
    _assert_response_preserves_operator_inputs,
    _restore_operator_controlled_fields_from_template,
    _validate_guided_observation_date,
    _guided_cutoff_timestamp,
    _validate_guided_research_response,
    _build_response_repair_prompt,
    run_guided_wizard,
    run_local_investment_pilot,
    verify_local_pilot_bundle,
)


def _payload(*, price: str = "100", cutoff: str = "2026-10-10") -> dict:
    forecast_year = int(cutoff[:4]) + 1
    return {
        "schema_version": PILOT_SCHEMA,
        "case": {
            "company": "示例公司",
            "market": "CN-A",
            "symbol": "300750",
            "currency": "CNY",
            "as_of_date": cutoff,
            "current_position_pct": "0",
        },
        "price_input": {
            "price": price,
            "currency": "CNY",
            "observation_date": "2026-10-09",
            "known_at": "2026-10-09T15:00:00+08:00",
            "assurance_label": "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED",
            "sources_claimed": ["operator-entered test quote"],
        },
        "evidence_register": [
            {
                "source_id": "E1",
                "title": "示例公司 2026 H1 报告",
                "source_class": "EXCHANGE_PRIMARY",
                "source_ref": "https://static.sse.com.cn/synthetic-tests/300750-h1.pdf",
                "published_at": "2026-08-30",
                "known_at": "2026-08-30",
                "summary": "Synthetic test source; not real evidence.",
            },
            {
                "source_id": "E2",
                "title": "Synthetic no-future-distribution review support",
                "source_class": "EXCHANGE_PRIMARY",
                "source_ref": "https://static.sse.com.cn/synthetic-tests/distribution-review.pdf",
                "published_at": "2026-08-29",
                "known_at": "2026-08-29",
                "summary": "Synthetic test source used only for the explicit distribution review; not real evidence.",
            }
        ],
        "assessment": {
            "trust": {"status": "PASS", "summary": "synthetic trust check", "evidence_refs": ["E1"]},
            "reality": {"status": "PASS", "summary": "synthetic reality check", "evidence_refs": ["E1"]},
            "quality": {"status": "PASS", "summary": "synthetic quality check", "evidence_refs": ["E1"]},
            "thesis": {
                "status": "INTACT",
                "core_statement": "synthetic thesis",
                "drivers": [{"name": "volume growth", "evidence_refs": ["E1"]}],
                "break_conditions": ["synthetic break"],
                "reassessment_triggers": ["synthetic trigger"],
                "evidence_refs": ["E1"],
            },
            "value_drivers": [
                {
                    "rank": 1,
                    "driver": "volume growth",
                    "driver_type": "VOLUME",
                    "historical_evidence": "Synthetic prior-period shipped-volume trend; illustrative test basis only.",
                    "valuation_transmission": "More shipped volume at unchanged net ASP and unit cost increases revenue and contribution profit before fixed costs.",
                    "impact": "POSITIVE",
                    "rationale": "Synthetic test driver with an explicit historical baseline and per-share value mechanism.",
                    "evidence_refs": ["E1"],
                }
            ],
            "market_implied_expectation": {"status": "PASS", "summary": "synthetic test only", "evidence_refs": ["E1"]},
            "expectation_gap": {
                "status": "PASS",
                "direction": "POSITIVE",
                "summary": "synthetic test gap",
                "evidence_refs": ["E1"],
            },
            "risk": {
                "status": "PASS",
                "summary": "synthetic risk",
                "max_loss_pct": "25",
                "items": [{
                    "risk_id": "R-SYNTHETIC",
                    "severity": "HIGH",
                    "name": "synthetic downside",
                    "description": "synthetic risk item for tests",
                    "monitoring_trigger": "synthetic metric misses threshold for two periods",
                    "evidence_refs": ["E1"],
                }],
                "evidence_refs": ["E1"],
            },
        },
        "forecast_valuation": {
            "model": "SYNTHETIC EPS x PE",
            "model_family": "EPS_MULTIPLE",
            "model_rationale": "synthetic test only",
            "valuation_terminal_date": f"{forecast_year}-12-31",
            "valuation_terminal_date_basis": "Synthetic fixture: explicit FY endpoint assumption.",
            "entry_value_reference_per_share": "150",
            "probabilities_calibrated": False,
            "assumptions": ["Synthetic assumptions; not forecasts."],
            "cash_distribution_review": {
                "status": "NO_FUTURE_DISTRIBUTIONS_CONFIRMED",
                "summary": "Synthetic fixture only: no distributions scheduled in the test horizon.",
                "evidence_refs": ["E2"],
            },
            "scenarios": {
                "bear": {
                    "probability": "0.20", "terminal_value_per_share": "120", "cash_distributions_per_share": "0",
                    "rationale": "synthetic bear", "failure_trigger": "core volume growth fails",
                    "operating_impact": "volume and profit miss base case", "valuation_mechanism": "lower normalized EPS and multiple",
                },
                "base": {"probability": "0.50", "terminal_value_per_share": "150", "cash_distributions_per_share": "0", "rationale": "synthetic base"},
                "bull": {"probability": "0.30", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "rationale": "synthetic bull"},
            },
            "thesis_break_stress": {
                "failure_trigger": "core thesis fails",
                "operating_impact": "profit recovery does not occur and margins contract",
                "valuation_method": "normalized downside earnings at a compressed multiple",
                "terminal_value_per_share": "80",
                "cash_distributions_per_share": "0",
                "rationale": "synthetic thesis-break case, not a forecast",
                "evidence_refs": ["E1"],
            },
        },
        "decision_parameters": {
            "horizon_years": 1,
            "horizon_override": False,
            "horizon_override_basis": [],
            "horizon_selection_rationale": "Default one-year reference horizon.",
            "required_return_annualized": "0.15",
            "max_loss_pct": "25",
        },
        "operating_driver_forecast": {
            "schema_version": "IIOS-OPERATING-DRIVER-FORECAST-0.1",
            "scope": "COMPANY_WIDE",
            "status": "UNKNOWN",
            "actuals_period": "UNKNOWN",
            "forecast_period": f"{forecast_year}FY",
            "summary": "Synthetic pilot driver tree; actual product-specific quantities, net ASP and unit costs remain UNKNOWN.",
            "product_lines": [],
            "scenarios": {"bear": {}, "base": {}, "bull": {}},
            "limitations": ["Synthetic test only."],
        },
        "eps_multiple_valuation": {
            "schema_version": "IIOS-EPS-MULTIPLE-VALUATION-0.1",
            "calculation_method": "EPS_PER_SHARE_X_PE_MULTIPLE",
            "summary": "Synthetic test assumption: terminal value is explicitly recalculated as EPS times P/E.",
            "forecast_period": f"{forecast_year}FY",
            "valuation_terminal_date": f"{forecast_year}-12-31",
            "scenarios": {
                "bear": {"rationale": "Synthetic bear EPS and multiple.", "eps_per_share": {"value": "10", "unit": "CNY/share", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic EPS fixture.", "assumption_derivation": "Synthetic, explicitly declared analyst scenario EPS; not an issuer forecast and not independently bridged to company earnings.", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": "12", "unit": "x", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic low multiple.", "evidence_refs": [], "note": ""}},
                "base": {"rationale": "Synthetic base EPS and multiple.", "eps_per_share": {"value": "10", "unit": "CNY/share", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic EPS fixture.", "assumption_derivation": "Synthetic, explicitly declared analyst scenario EPS; not an issuer forecast and not independently bridged to company earnings.", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": "15", "unit": "x", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic base multiple.", "evidence_refs": [], "note": ""}},
                "bull": {"rationale": "Synthetic bull EPS and multiple.", "eps_per_share": {"value": "10", "unit": "CNY/share", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic EPS fixture.", "assumption_derivation": "Synthetic, explicitly declared analyst scenario EPS; not an issuer forecast and not independently bridged to company earnings.", "earnings_bridge": None, "evidence_refs": [], "note": ""}, "pe_multiple_x": {"value": "18", "unit": "x", "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic high multiple.", "evidence_refs": [], "note": ""}}
            }
        },
        "sotp_valuation": {
            "schema_version": "IIOS-SOTP-VALUATION-0.1",
            "calculation_method": "SEGMENT_ATTRIBUTABLE_NET_PROFIT_X_SEGMENT_PE",
            "summary": "",
            "forecast_period": "UNKNOWN",
            "valuation_terminal_date": None,
            "scenarios": {"bear": {}, "base": {}, "bull": {}},
        },
        "valuation_transmission": {
            "schema_version": "IIOS-VALUATION-TRANSMISSION-0.1",
            "model_family": "UNKNOWN",
            "valuation_model_name": "UNKNOWN",
            "earnings_period": "UNKNOWN",
            "summary": "Synthetic B5 bridge left intentionally unlinked.",
            "scenarios": {
                name: {
                    "ownership_ratio": {"value": None, "unit": "ratio", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                    "displaced_existing_after_tax_profit_cny": {"value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                    "basic_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                    "convertible_bond_incremental_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                    "other_dilution_shares": {"value": None, "unit": "shares", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                    "pe_multiple_x": {"value": None, "unit": "x", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [], "note": "Synthetic unknown"},
                }
                for name in ("bear", "base", "bull")
            },
        },
        "operator_valuation_context": {
            "selected_model_family": "EPS_MULTIPLE",
            "baseline_includes_project": None,
            "input_owner": "OPERATOR",
        },
        "notes": "Synthetic pytest fixture only.",
    }


def _sync_eps_multiple_values(payload: dict, terminal_values: dict[str, object]) -> None:
    """Keep synthetic EPS×P/E assumptions aligned when a test intentionally changes its scenario values."""
    node = payload["eps_multiple_valuation"]
    node["forecast_period"] = payload["operating_driver_forecast"]["forecast_period"]
    node["valuation_terminal_date"] = payload["forecast_valuation"]["valuation_terminal_date"]
    for name, terminal_value in terminal_values.items():
        value = Decimal(str(terminal_value))
        row = node["scenarios"][name]
        row["eps_per_share"]["unit"] = str(payload["case"]["currency"]) + "/share"
        row["eps_per_share"]["value"] = format(value / Decimal("10"), "f")
        row["pe_multiple_x"]["value"] = "10"


def _write_input(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "pilot-input.json"
    path.write_text(json.dumps(payload or _payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("market", "raw", "expected"),
    [
        ("CN-A", "SZ002810", "002810.SZ"),
        ("CN-A", "SH600000", "600000.SH"),
        ("CN-A", "BJ430047", "430047.BJ"),
        ("CN-A", "002810", "002810"),
        ("HK", "HK00700", "00700.HK"),
        ("HK", "00700", "00700"),
    ],
)
def test_guided_entry_normalizes_common_symbol_formats(market, raw, expected):
    assert _normalize_guided_symbol(raw, market) == expected


def test_default_price_date_skips_weekends_but_does_not_guess_exchange_holidays():
    assert _previous_weekday(date(2026, 10, 12)) == date(2026, 10, 9)
    assert _previous_weekday(date(2026, 10, 13)) == date(2026, 10, 12)


def test_response_file_reader_accepts_large_json_without_terminal_paste(tmp_path):
    response_path = tmp_path / "chatgpt-response.json"
    large_payload = {
        "schema_version": PILOT_SCHEMA,
        "large_notes": "x" * 1_000_000,
    }
    response_path.write_text(json.dumps(large_payload), encoding="utf-8")
    result = _read_json_response_file(response_path)
    assert result["schema_version"] == PILOT_SCHEMA
    assert len(result["large_notes"]) == 1_000_000


def test_response_file_reader_rejects_empty_file_with_actionable_error(tmp_path):
    response_path = tmp_path / "chatgpt-response.json"
    response_path.write_text("", encoding="utf-8")
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_RESPONSE_FILE_EMPTY"):
        _read_json_response_file(response_path)


def test_guided_wizard_uses_a_file_for_chatgpt_response_not_pbpaste():
    source = Path(__file__).resolve().parents[1] / "iios_mvp" / "local_investment_pilot_v01.py"
    content = source.read_text(encoding="utf-8")
    assert "pbpaste" not in content
    assert "_read_json_response_file(response_path)" in content
    assert '["open", "-a", "TextEdit", str(response_path)]' in content


def test_evidence_references_in_assessment_and_valuation_are_resolved_or_explicitly_unresolved():
    payload = _payload()
    payload["assessment"]["risk"]["items"] = [
        {
            "risk_id": "R-1",
            "name": "synthetic risk",
            "description": "risk text",
            "evidence_refs": ["E-RISK-MISSING"],
        }
    ]
    payload["forecast_valuation"]["assumptions"] = [
        {
            "assumption_id": "A-1",
            "name": "synthetic assumption",
            "values": {"base_eps": "1.15"},
            "evidence_refs": ["E-ASSUMPTION-MISSING"],
        }
    ]
    prepared = _prepare_input(payload)
    assert prepared["referenced_evidence_ids"] == ["E-ASSUMPTION-MISSING", "E-RISK-MISSING", "E1", "E2"]
    assert prepared["unresolved_evidence_references"] == ["E-ASSUMPTION-MISSING", "E-RISK-MISSING"]


def test_duplicate_referenced_evidence_id_is_ambiguous_and_blocks_decision():
    payload = _payload()
    payload["evidence_register"].append({
        "source_id": "E1",
        "title": "Conflicting duplicate source",
        "source_class": "MEDIA",
        "source_ref": "https://conflict.example.invalid/changed.pdf",
        "published_at": "2026-10-10",
        "known_at": "2026-10-10T12:00:00+08:00",
        "summary": "Conflicting duplicate record for the same evidence ID.",
    })

    analysis, report = _analyse(payload, "TEST-DUPLICATE-SOURCE-ID")

    assert analysis["duplicate_evidence_ids"] == ["E1"]
    assert "E1" in analysis["referenced_evidence_ids"]
    assert "E1" in analysis["unresolved_evidence_references"]
    assert "DUPLICATE_EVIDENCE_SOURCE_IDS" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert analysis["return_metrics"] is not None  # duplicate refs invalidate decision readiness, not arithmetic alone
    assert "来源登记表重复 ID：E1" in report
    assert "**E1**：**来源 ID 重复登记，引用无法唯一解析**" in report


def test_unreferenced_duplicate_evidence_id_is_disclosed_without_false_reference_block():
    payload = _payload()
    payload["evidence_register"].append({
        "source_id": "E-UNUSED",
        "title": "First unused record",
        "source_class": "ISSUER_PRIMARY",
        "source_ref": "https://example.invalid/unused-a.pdf",
        "known_at": "2026-08-30",
        "summary": "First unused record.",
    })
    payload["evidence_register"].append({
        "source_id": "E-UNUSED",
        "title": "Second unused record",
        "source_class": "MEDIA",
        "source_ref": "https://example.invalid/unused-b.pdf",
        "known_at": "2026-08-31",
        "summary": "Conflicting second unused record.",
    })

    analysis, report = _analyse(payload, "TEST-UNREFERENCED-DUPLICATE-SOURCE-ID")

    assert analysis["duplicate_evidence_ids"] == ["E-UNUSED"]
    assert "E-UNUSED" not in analysis["referenced_evidence_ids"]
    assert "DUPLICATE_EVIDENCE_SOURCE_IDS" not in analysis["decision"]["gating_issues"]
    assert "来源登记表重复 ID：E-UNUSED" in report


@pytest.mark.parametrize(
    ("field", "placeholder"),
    [
        ("source_ref", "UNKNOWN"),
        ("source_ref", "N/A"),
        ("title", "UNKNOWN"),
        ("summary", "未提供事实摘要"),
        ("summary", "TBD"),
    ],
)
def test_referenced_evidence_with_placeholder_locator_or_context_is_unresolved(field, placeholder):
    payload = _payload()
    payload["evidence_register"][0][field] = placeholder

    analysis, report = _analyse(payload, f"TEST-UNTRACEABLE-SOURCE-{field}-{placeholder}")

    assert analysis["untraceable_evidence_ids"] == ["E1"]
    assert field in analysis["untraceable_evidence_fields"]["E1"]
    assert "E1" in analysis["referenced_evidence_ids"]
    assert "E1" in analysis["unresolved_evidence_references"]
    assert "UNTRACEABLE_EVIDENCE_SOURCE_RECORDS" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "**E1**：**引用无法完成来源定位**" in report


def test_report_uses_portable_prose_instead_of_markdown_tables_and_python_dict_repr(tmp_path):
    payload = _payload()
    payload["evidence_register"] = []
    payload["assessment"]["value_drivers"] = [
        {"rank": 1, "driver": "growth A", "impact": "POSITIVE", "rationale": "reason A", "evidence_refs": ["E1"]},
        {"rank": 1, "driver": "growth B", "impact": "MIXED", "rationale": "reason B", "evidence_refs": ["E-MISSING"]},
    ]
    payload["assessment"]["risk"]["items"] = [
        {"risk_id": "R-1", "name": "cash collection", "severity": "HIGH", "description": "synthetic risk", "monitoring_trigger": "receivables rise", "evidence_refs": ["E-MISSING"]}
    ]
    payload["forecast_valuation"]["assumptions"] = [
        {"assumption_id": "A-1", "name": "base EPS", "values": {"bear_eps": "0.75", "base_eps": "1.15"}, "basis": "synthetic assumption", "evidence_refs": ["E1"]}
    ]
    analysis, report = _analyse(payload, "TEST-RUN")
    assert "|---" not in report
    assert "| 情景 |" not in report
    assert "A-1｜base EPS" in report
    assert "R-1｜cash collection" in report
    assert "**E-MISSING**：**未解析**" in report
    assert "**E1**：**未解析**" in report
    assert "来源登记表为空" in report
    assert "**价值驱动因素 1：growth A**" in report
    assert "**价值驱动因素 2：growth B**" in report
    assert "{'assumption_id':" not in report
    assert analysis["unresolved_evidence_references"] == ["E-MISSING", "E1", "E2"]


def test_report_keeps_source_url_punctuation_outside_link_and_renders_risk_summary():
    payload = _payload()
    payload["evidence_register"][0]["source_ref"] = "https://example.invalid/facts.pdf"
    payload["assessment"]["value_drivers"] = [
        {"rank": 1, "driver": "增长驱动 A", "impact": "POSITIVE", "rationale": "说明 A", "evidence_refs": ["E1"]},
        {"rank": 2, "driver": "增长驱动 B", "impact": "MIXED", "rationale": "说明 B", "evidence_refs": ["E1"]},
    ]
    payload["assessment"]["risk"]["items"] = [
        {
            "risk_id": "R-DETAIL",
            "title": "应收账款风险",
            "severity": "HIGH",
            "summary": "应收账款增速持续高于收入增速，回款风险上升。",
            "evidence_refs": ["E1"],
        }
    ]
    _analysis, report = _analyse(payload, "TEST-REPORT-RENDER")

    assert "**价值驱动因素 1：增长驱动 A**" in report
    assert "**价值驱动因素 2：增长驱动 B**" in report
    assert "摘要：应收账款增速持续高于收入增速，回款风险上升。" in report
    assert "来源位置：<https://example.invalid/facts.pdf>。" in report


def test_guided_observation_date_must_precede_date_only_cutoff():
    from datetime import date
    cutoff = date(2026, 10, 12)
    assert _validate_guided_observation_date(date(2026, 10, 9), cutoff) == date(2026, 10, 9)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF"):
        _validate_guided_observation_date(cutoff, cutoff)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF"):
        _validate_guided_observation_date(date(2026, 10, 13), cutoff)


def test_assessment_pass_or_intact_requires_its_own_resolved_evidence_reference():
    payload = _payload()
    payload["assessment"]["trust"]["evidence_refs"] = []

    analysis, report = _analyse(payload, "TEST-ASSESSMENT-PASS-NO-REF")
    trust = analysis["assessment"]["trust"]

    assert trust["status_input"] == "PASS"
    assert trust["status"] == "UNKNOWN"
    assert "ASSESSMENT_PASS_EVIDENCE_LINK_NOT_RESOLVED" in trust["status_issues"]
    assert "TRUST_ASSESSMENT_PASS_EVIDENCE_LINK_NOT_RESOLVED" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "输入标签 PASS" in report


def test_assessment_pass_with_unresolved_reference_is_not_preserved():
    payload = _payload()
    payload["assessment"]["expectation_gap"]["evidence_refs"] = ["E-MISSING"]

    analysis, _report = _analyse(payload, "TEST-ASSESSMENT-PASS-UNRESOLVED-REF")
    gap = analysis["assessment"]["expectation_gap"]

    assert gap["status"] == "UNKNOWN"
    assert "ASSESSMENT_PASS_EVIDENCE_LINK_NOT_RESOLVED" in gap["status_issues"]
    assert "EXPECTATION_GAP_ASSESSMENT_PASS_EVIDENCE_LINK_NOT_RESOLVED" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("section", "status", "placeholder"),
    [
        ("trust", "PASS", "UNKNOWN"),
        ("reality", "PASS", "TBD"),
        ("quality", "PASS", "N/A"),
        ("thesis", "INTACT", "NOT_IDENTIFIABLE"),
        ("risk", "PASS", "未提供依据"),
    ],
)
def test_assessment_gate_status_downgrades_when_summary_is_placeholder(section, status, placeholder):
    payload = _payload()
    payload["assessment"][section]["status"] = status
    if section == "thesis":
        payload["assessment"][section]["core_statement"] = placeholder
    else:
        payload["assessment"][section]["summary"] = placeholder

    analysis, report = _analyse(payload, f"TEST-ASSESSMENT-SUMMARY-PLACEHOLDER-{section}")

    normalized = analysis["assessment"][section]
    assert normalized["status"] == "UNKNOWN"
    assert normalized["status_input"] == status
    assert normalized["status_issues"] == ["ASSESSMENT_EXPLANATION_NOT_IDENTIFIABLE"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert analysis["decision"]["provisional_action"] not in {"BUY", "ADD", "HOLD"}
    assert "输入标签 " + status in report


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    [
        ("break_conditions", [], "BREAK_CONDITIONS_NOT_IDENTIFIABLE"),
        ("break_conditions", ["UNKNOWN"], "BREAK_CONDITIONS_NOT_IDENTIFIABLE"),
        ("reassessment_triggers", [], "REASSESSMENT_TRIGGERS_NOT_IDENTIFIABLE"),
        ("reassessment_triggers", ["TBD"], "REASSESSMENT_TRIGGERS_NOT_IDENTIFIABLE"),
    ],
)
def test_thesis_intact_downgrades_when_break_or_monitoring_triggers_are_unidentifiable(field, value, expected_issue):
    payload = _payload()
    payload["assessment"]["thesis"][field] = value

    analysis, report = _analyse(payload, f"TEST-THESIS-TRIGGERS-{field}")

    thesis = analysis["assessment"]["thesis"]
    assert thesis["status"] == "UNKNOWN"
    assert thesis["status_input"] == "INTACT"
    assert expected_issue in thesis["status_issues"]
    assert "THESIS_" + expected_issue in analysis["decision"]["gating_issues"]
    assert "Thesis 状态：UNKNOWN" in report


def test_structured_thesis_triggers_are_rendered_as_readable_text_not_python_dict_repr():
    payload = _payload()
    payload["assessment"]["thesis"]["break_conditions"] = [{
        "condition": "核心产品毛利率连续两个季度同比下滑",
        "measurement": "季度分产品毛利率同比",
        "threshold": "连续两个季度为负增长",
        "effect": "下调收入质量与可持续利润率判断",
        "evidence_refs": ["E1"],
    }]
    payload["assessment"]["thesis"]["reassessment_triggers"] = [{
        "trigger": "下一次定期报告披露",
        "metric": "核心产品收入增速与经营现金流",
        "threshold": "收入减速且现金流转化同步恶化",
        "decision_effect": "重新评估基准情景与估值倍数",
        "evidence_refs": ["E1"],
    }]

    analysis, report = _analyse(payload, "TEST-THESIS-STRUCTURED-TRIGGERS")

    assert "核心产品毛利率连续两个季度同比下滑" in analysis["assessment"]["thesis"]["break_conditions"][0]
    assert "验证方法：季度分产品毛利率同比" in analysis["assessment"]["thesis"]["break_conditions"][0]
    assert "决策影响：重新评估基准情景与估值倍数" in analysis["assessment"]["thesis"]["reassessment_triggers"][0]
    assert "{'condition':" not in report
    assert "{'trigger':" not in report
    assert "验证方法：季度分产品毛利率同比" in report
    assert "决策影响：重新评估基准情景与估值倍数" in report


def test_thesis_intact_is_preserved_with_identifiable_break_and_reassessment_triggers():
    analysis, _report = _analyse(_payload(), "TEST-THESIS-TRIGGERS-IDENTIFIABLE")

    thesis = analysis["assessment"]["thesis"]
    assert thesis["status"] == "INTACT"
    assert thesis["status_issues"] == []


@pytest.mark.parametrize(
    ("field", "placeholder", "expected_issue"),
    [
        ("driver", "TBD", "DRIVER_NAME_NOT_IDENTIFIABLE"),
        ("impact", "UNKNOWN", "IMPACT_NOT_IDENTIFIABLE"),
        ("rationale", "N/A", "RATIONALE_NOT_IDENTIFIABLE"),
        ("historical_evidence", "UNKNOWN", "HISTORICAL_EVIDENCE_NOT_IDENTIFIABLE"),
        ("valuation_transmission", "TBD", "VALUATION_TRANSMISSION_NOT_IDENTIFIABLE"),
    ],
)
def test_value_driver_gate_downgrades_placeholder_only_subfields(field, placeholder, expected_issue):
    payload = _payload()
    payload["assessment"]["value_drivers"][0][field] = placeholder

    analysis, report = _analyse(payload, f"TEST-VALUE-DRIVER-PLACEHOLDER-{field}")

    driver = analysis["assessment"]["value_drivers"][0]
    assert driver["status"] == "UNKNOWN"
    assert expected_issue in driver["status_issues"]
    assert "内容门禁：UNKNOWN" in report
    assert expected_issue in report


@pytest.mark.parametrize("invalid_rank", ["TBD", None, 0, -1, 1.5])
def test_invalid_value_driver_rank_downgrades_row_without_crashing(invalid_rank):
    payload = _payload()
    payload["assessment"]["value_drivers"][0]["rank"] = invalid_rank

    analysis, report = _analyse(payload, f"TEST-VALUE-DRIVER-RANK-{invalid_rank}")

    driver = analysis["assessment"]["value_drivers"][0]
    assert driver["rank"] == 1
    assert driver["status"] == "UNKNOWN"
    assert "RANK_NOT_IDENTIFIABLE" in driver["status_issues"]
    assert "VALUE_DRIVER_RANK_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]
    assert "按输入顺序临时展示" in report


def test_duplicate_value_driver_ranks_downgrade_all_conflicting_rows():
    payload = _payload()
    first = payload["assessment"]["value_drivers"][0]
    second = dict(first)
    second.update({
        "rank": first.get("rank", 1),
        "driver": "成本改善",
        "rationale": "单位成本下降扩大利润率，但需对照原料价格与产能利用率验证。",
        "evidence_refs": ["E1"],
    })
    payload["assessment"]["value_drivers"].append(second)

    analysis, report = _analyse(payload, "TEST-VALUE-DRIVER-DUPLICATE-RANK")

    drivers = analysis["assessment"]["value_drivers"]
    assert len(drivers) == 2
    assert [driver["rank"] for driver in drivers] == [1, 1]
    assert all(driver["status"] == "UNKNOWN" for driver in drivers)
    assert all(
        "DUPLICATE_RANK_NOT_IDENTIFIABLE" in driver["status_issues"]
        for driver in drivers
    )
    assert "VALUE_DRIVER_DUPLICATE_RANK_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]
    assert report.count("排序不唯一") == 2


@pytest.mark.parametrize(
    "evidence_refs",
    [
        None,
        ["E-DOES-NOT-EXIST"],
    ],
)
def test_value_driver_requires_its_own_resolved_evidence_link(evidence_refs):
    payload = _payload()
    driver = payload["assessment"]["value_drivers"][0]
    if evidence_refs is None:
        driver.pop("evidence_refs")
    else:
        driver["evidence_refs"] = evidence_refs

    analysis, report = _analyse(payload, "TEST-VALUE-DRIVER-EVIDENCE-LINK")

    normalized = analysis["assessment"]["value_drivers"][0]
    assert normalized["status"] == "UNKNOWN"
    assert "DRIVER_EVIDENCE_LINK_NOT_RESOLVED" in normalized["status_issues"]
    assert "VALUE_DRIVER_DRIVER_EVIDENCE_LINK_NOT_RESOLVED" in analysis["decision"]["gating_issues"]
    assert "该价值驱动因素没有自己的可追溯截止时点证据" in report


def test_value_driver_legacy_evidence_and_transmission_fields_are_preserved_and_rendered():
    payload = _payload()
    payload["assessment"]["value_drivers"] = [{
        "rank": 1,
        "name": "出口市场收入增长与订单兑现",
        "type": "REVENUE_GROWTH_AND_MIX",
        "historical_evidence": "2025年外销主营业务收入同比增长38.51%，外销毛利率41.81%。",
        "valuation_transmission": "出口订单若持续兑现，将提高收入与利润；订单延期可能压低固定费用吸收率和估值倍数。",
        "evidence_refs": ["E1"],
    }]

    analysis, report = _analyse(payload, "TEST-VALUE-DRIVER-LEGACY-FIELDS")

    item = analysis["assessment"]["value_drivers"][0]
    # Missing direction stays UNKNOWN: the normalizer must not infer positive
    # impact merely from a growth-oriented label or causal narrative.
    assert item["impact"] == "UNKNOWN"
    assert item["status"] == "UNKNOWN"
    assert item["status_issues"] == ["IMPACT_NOT_IDENTIFIABLE"]
    assert item["driver_type"] == "REVENUE_GROWTH_AND_MIX"
    assert item["historical_evidence"].startswith("2025年外销主营业务收入同比增长")
    assert item["valuation_transmission"].startswith("出口订单若持续兑现")
    assert item["rationale"] == item["valuation_transmission"]
    assert "类型：REVENUE_GROWTH_AND_MIX" in report
    assert "历史依据：2025年外销主营业务收入同比增长38.51%" in report
    assert "价值传导：出口订单若持续兑现" in report
    assert "未提供理由。" not in report
    assert "RATIONALE_NOT_IDENTIFIABLE" not in item["status_issues"]


def test_value_driver_gate_passes_with_identifiable_name_impact_and_rationale():
    analysis, report = _analyse(_payload(), "TEST-VALUE-DRIVER-IDENTIFIABLE")

    driver = analysis["assessment"]["value_drivers"][0]
    assert driver["status"] == "PASS"
    assert driver["status_issues"] == []
    assert driver["historical_evidence"].startswith("Synthetic prior-period")
    assert driver["valuation_transmission"].startswith("More shipped volume")
    assert "历史依据：Synthetic prior-period" in report
    assert "价值传导：More shipped volume" in report
    assert "内容门禁：PASS" in report


@pytest.mark.parametrize(
    "risk_items",
    [
        [],
        ["UNKNOWN"],
        [{"risk_id": "R-1", "name": "UNKNOWN", "summary": "TBD"}],
        [{"risk_id": "R-1", "name": "应收账款风险", "description": "N/A"}],
    ],
)
def test_risk_pass_downgrades_when_structured_risk_items_are_missing_or_placeholder_only(risk_items):
    payload = _payload()
    payload["assessment"]["risk"]["items"] = risk_items

    analysis, report = _analyse(payload, "TEST-RISK-ITEMS-PLACEHOLDER")

    risk = analysis["assessment"]["risk"]
    assert risk["status"] == "UNKNOWN"
    assert risk["status_input"] == "PASS"
    assert "ITEMS_NOT_IDENTIFIABLE" in risk["status_issues"]
    assert "RISK_UNKNOWN" in analysis["decision"]["gating_issues"]
    assert "RISK_ITEMS_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]
    assert "风险门禁原标为 PASS" in report


@pytest.mark.parametrize("trigger", [None, "", "UNKNOWN", "TBD", "未提供依据"])
def test_structured_risk_item_requires_identifiable_monitoring_trigger(trigger):
    payload = _payload()
    item = {
        "risk_id": "R-TRIGGER",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "evidence_refs": ["E1"],
    }
    if trigger is not None:
        item["monitoring_trigger"] = trigger
    payload["assessment"]["risk"]["items"] = [item]

    analysis, report = _analyse(payload, "TEST-RISK-ITEM-MONITORING-TRIGGER")

    risk = analysis["assessment"]["risk"]
    normalized = risk["items"][0]
    assert risk["status"] == "UNKNOWN"
    assert "RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE" in risk["status_issues"]
    assert normalized["status"] == "UNKNOWN"
    assert "RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE" in normalized["status_issues"]
    assert "RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]
    assert "RISK_RISK_ITEM_MONITORING_TRIGGER_NOT_IDENTIFIABLE" not in analysis["decision"]["gating_issues"]
    assert "明确且非占位的监控触发条件" in report


def test_duplicate_structured_risk_ids_downgrade_all_conflicting_risk_rows():
    payload = _payload()
    template = {
        "risk_id": "R-1",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "monitoring_trigger": "连续两个季度经营现金流低于净利润。",
        "evidence_refs": ["E1"],
    }
    second = dict(template)
    second.update({
        "name": "客户集中度恶化",
        "description": "最大客户收入占比持续提升，单一客户依赖度上升。",
        "monitoring_trigger": "最大客户收入占比连续两个季度上升。",
    })
    payload["assessment"]["risk"]["items"] = [template, second]

    analysis, report = _analyse(payload, "TEST-DUPLICATE-RISK-ID")

    risk = analysis["assessment"]["risk"]
    assert risk["status"] == "UNKNOWN"
    assert "DUPLICATE_RISK_ID_NOT_IDENTIFIABLE" in risk["status_issues"]
    assert all(item["status"] == "UNKNOWN" for item in risk["items"])
    assert all(
        "DUPLICATE_RISK_ID_NOT_IDENTIFIABLE" in item["status_issues"]
        for item in risk["items"]
    )
    assert "RISK_DUPLICATE_RISK_ID_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]
    assert "多个结构化风险项使用相同 risk_id" in report


def test_legacy_plain_text_risk_list_remains_renderable_but_cannot_claim_pass():
    payload = _payload()
    payload["assessment"]["risk"]["items"] = ["应收账款回款风险"]

    analysis, report = _analyse(payload, "TEST-LEGACY-PLAIN-TEXT-RISK")

    risk = analysis["assessment"]["risk"]
    assert risk["status_input"] == "PASS"
    assert risk["status"] == "UNKNOWN"
    assert "ITEMS_REQUIRE_STRUCTURED_MONITORING" in risk["status_issues"]
    assert "RISK_ITEMS_REQUIRE_STRUCTURED_MONITORING" in analysis["decision"]["gating_issues"]
    assert "应收账款回款风险" in report
    assert "不能证明每项风险都有独立证据和可执行监控触发器" in report
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    [
        ("risk_id", None, "RISK_ITEM_ID_NOT_IDENTIFIABLE"),
        ("risk_id", "UNKNOWN", "RISK_ITEM_ID_NOT_IDENTIFIABLE"),
        ("severity", None, "RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE"),
        ("severity", "UNKNOWN", "RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE"),
        ("severity", "SEVEREISH", "RISK_ITEM_SEVERITY_NOT_IDENTIFIABLE"),
    ],
)
def test_structured_risk_items_require_stable_id_and_recognized_severity(field, value, expected_issue):
    payload = _payload()
    item = {
        "risk_id": "R-1",
        "severity": "HIGH",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "monitoring_trigger": "连续两个季度经营现金流低于净利润。",
        "evidence_refs": ["E1"],
    }
    if value is None:
        item.pop(field, None)
    else:
        item[field] = value
    payload["assessment"]["risk"]["items"] = [item]

    analysis, report = _analyse(payload, "TEST-RISK-ITEM-ID-SEVERITY")

    risk = analysis["assessment"]["risk"]
    normalized = risk["items"][0]
    assert risk["status"] == "UNKNOWN"
    assert expected_issue in risk["status_issues"]
    assert normalized["status"] == "UNKNOWN"
    assert expected_issue in normalized["status_issues"]
    assert expected_issue in analysis["decision"]["gating_issues"]
    assert expected_issue in report


def test_risk_pass_is_preserved_with_identifiable_structured_risk_item():
    payload = _payload()
    payload["assessment"]["risk"]["items"] = [{
        "risk_id": "R-1",
        "severity": "HIGH",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "monitoring_trigger": "连续两个季度经营现金流低于净利润。",
        "evidence_refs": ["E1"],
    }]

    analysis, _report = _analyse(payload, "TEST-RISK-ITEMS-IDENTIFIABLE")

    assert analysis["assessment"]["risk"]["status"] == "PASS"
    assert analysis["assessment"]["risk"]["status_issues"] == []
    assert analysis["assessment"]["risk"]["items"][0]["evidence_refs"] == ["E1"]


@pytest.mark.parametrize("item_status", ["UNKNOWN", "FAIL", "TBD"])
def test_overall_risk_pass_is_blocked_by_nonpassing_structured_item_status(item_status):
    payload = _payload()
    payload["assessment"]["risk"]["items"] = [{
        "risk_id": "R-STATUS",
        "severity": "HIGH",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "monitoring_trigger": "连续两个季度经营现金流低于净利润。",
        "evidence_refs": ["E1"],
        "status": item_status,
    }]

    analysis, report = _analyse(payload, "TEST-RISK-CHILD-STATUS-CONSISTENCY")

    risk = analysis["assessment"]["risk"]
    item = risk["items"][0]
    assert risk["status"] == "UNKNOWN"
    assert "RISK_ITEM_STATUS_NOT_PASS" in risk["status_issues"]
    assert item["status"] == item_status
    assert "RISK_ITEM_STATUS_NOT_PASS" in item["status_issues"]
    assert "RISK_ITEM_STATUS_NOT_PASS" in analysis["decision"]["gating_issues"]
    assert "整体风险状态不能继续标为 PASS，已降为 UNKNOWN" in report


def test_risk_item_legacy_trigger_alias_and_operating_fields_are_preserved_and_rendered():
    payload = _payload()
    payload["assessment"]["risk"]["items"] = [{
        "risk_id": "R1",
        "severity": "HIGH",
        "name": "外销敞口及海外资本开支周期",
        "trigger": "外销订单或海外交付持续走弱。",
        "operating_impact": "总收入、产能利用及固定费用吸收同步走弱。",
        "valuation_mechanism": "下调可持续 EPS 并降低 P/E 倍数。",
        "evidence_refs": ["E1"],
    }]

    analysis, report = _analyse(payload, "TEST-RISK-LEGACY-TRIGGER-ALIAS")

    risk = analysis["assessment"]["risk"]
    item = risk["items"][0]
    assert risk["status"] == "PASS"
    assert item["monitoring_trigger"] == "外销订单或海外交付持续走弱。"
    assert item["monitoring_trigger_source_field"] == "trigger"
    assert item["status"] == "PASS"
    assert report.count("监控触发条件：外销订单或海外交付持续走弱。") == 1
    assert "经营影响：总收入、产能利用及固定费用吸收同步走弱。" in report
    assert "估值传导机制：下调可持续 EPS 并降低 P/E 倍数。" in report


def test_risk_report_renders_full_structured_risk_thesis_fields():
    payload = _payload()
    payload["assessment"]["risk"]["items"] = [{
        "risk_id": "R-REPORT",
        "severity": "HIGH",
        "name": "利润与经营现金流背离",
        "trigger": "经营现金流多期显著低于归母净利润。",
        "operating_impact": "应收、存货与票据可能占用更多现金。",
        "valuation_mechanism": "下调现金转换假设并提高安全边际。",
        "evidence_refs": ["E1"],
    }]

    _analysis, report = _analyse(payload, "TEST-RISK-FIELDS-REPORT")

    assert "R-REPORT｜利润与经营现金流背离" in report
    assert "严重程度：HIGH" in report
    assert "监控触发条件：经营现金流多期显著低于归母净利润。" in report
    assert "经营影响：应收、存货与票据可能占用更多现金。" in report
    assert "估值传导机制：下调现金转换假设并提高安全边际。" in report
    assert "风险项门禁：PASS" in report


@pytest.mark.parametrize(
    ("refs", "source_change"),
    [
        (None, None),
        (["E-RISK-MISSING"], None),
        (["E1"], "AFTER_CUTOFF"),
        (["E1"], "KNOWN_AT_INVALID"),
    ],
)
def test_structured_risk_item_requires_its_own_resolved_cutoff_compatible_evidence(refs, source_change):
    payload = _payload()
    item = {
        "risk_id": "R-OWN-EVIDENCE",
        "name": "应收账款回款恶化",
        "description": "应收账款增速持续高于收入增速，回款周期拉长。",
        "monitoring_trigger": "连续两个季度经营现金流低于净利润。",
    }
    if refs is not None:
        item["evidence_refs"] = refs
    payload["assessment"]["risk"]["items"] = [item]
    if source_change == "AFTER_CUTOFF":
        payload["evidence_register"][0]["known_at"] = "2026-10-11T10:00:00+08:00"
    elif source_change == "KNOWN_AT_INVALID":
        payload["evidence_register"][0]["known_at"] = "not-a-date"
        payload["evidence_register"][0]["published_at"] = "UNKNOWN"

    analysis, report = _analyse(payload, "TEST-RISK-ITEM-OWN-EVIDENCE")

    risk = analysis["assessment"]["risk"]
    normalized = risk["items"][0]
    assert risk["status"] == "UNKNOWN"
    assert "RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED" in risk["status_issues"]
    assert normalized["status"] == "UNKNOWN"
    assert "RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED" in normalized["status_issues"]
    assert "RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED" in analysis["decision"]["gating_issues"]
    assert "RISK_RISK_ITEM_EVIDENCE_LINK_NOT_RESOLVED" not in analysis["decision"]["gating_issues"]
    assert "至少一个结构化风险项没有自己的可追溯截止时点证据" in report


def test_ai_response_must_preserve_operator_owned_case_and_price_input(tmp_path):
    template_path = _write_input(tmp_path, _payload(cutoff="2026-10-10"))
    payload = json.loads(template_path.read_text(encoding="utf-8"))

    # Exact preservation of the template's operator-controlled sections is accepted.
    _assert_response_preserves_operator_inputs(template_path, payload)

    # A changed price is rejected instead of silently overriding the operator's quote.
    payload["price_input"]["price"] = "19.51"
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: price_input"):
        _assert_response_preserves_operator_inputs(template_path, payload)

    # Changes to case identity/cutoff are also rejected.
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload["case"]["as_of_date"] = "2026-10-11"
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: case"):
        _assert_response_preserves_operator_inputs(template_path, payload)

    # The model must not change the risk cap that feeds the Bear-loss pass/fail
    # and B6 price ceiling. Operators can edit the local template themselves.
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload["decision_parameters"]["max_loss_pct"] = "90"
    with pytest.raises(
        LocalInvestmentPilotError,
        match=r"CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: decision_parameters\.max_loss_pct",
    ):
        _assert_response_preserves_operator_inputs(template_path, payload)

    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload["decision_parameters"].pop("max_loss_pct")
    with pytest.raises(
        LocalInvestmentPilotError,
        match=r"CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: decision_parameters\.max_loss_pct",
    ):
        _assert_response_preserves_operator_inputs(template_path, payload)


def test_guided_response_restores_all_operator_controlled_fields_from_local_template(tmp_path):
    template_payload = _payload(cutoff="2026-10-10")
    template_payload["operator_valuation_context"] = {
        "selected_model_family": "SOTP",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": False,
    }
    template_payload["decision_parameters"]["max_loss_pct"] = "25"
    template_payload["decision_parameters"]["required_return_annualized"] = "0.20"
    template_path = _write_input(tmp_path, template_payload)
    template_bytes_before = template_path.read_bytes()

    response = json.loads(template_bytes_before.decode("utf-8"))
    response["case"]["symbol"] = "999999"
    response["case"]["as_of_date"] = "2030-01-01"
    response["price_input"]["price"] = "1"
    response["operator_valuation_context"]["selected_model_family"] = "EPS_MULTIPLE"
    response["decision_parameters"]["max_loss_pct"] = "90"
    response["decision_parameters"]["required_return_annualized"] = "0.15"
    response["notes"] = "Keep model-authored research notes; only operator controls are restored."

    restored = _restore_operator_controlled_fields_from_template(template_path, response)

    assert restored == [
        "case", "price_input", "operator_valuation_context",
        "decision_parameters.max_loss_pct", "decision_parameters.required_return_annualized",
    ]
    assert response["case"] == template_payload["case"]
    assert response["price_input"] == template_payload["price_input"]
    assert response["operator_valuation_context"] == template_payload["operator_valuation_context"]
    assert response["decision_parameters"]["max_loss_pct"] == "25"
    assert response["decision_parameters"]["required_return_annualized"] == "0.20"
    assert response["notes"] == "Keep model-authored research notes; only operator controls are restored."
    assert template_path.read_bytes() == template_bytes_before
    _assert_response_preserves_operator_inputs(template_path, response)


def test_operator_field_recovery_fails_closed_if_trusted_template_is_incomplete(tmp_path):
    template_path = _write_input(tmp_path, _payload())
    template = json.loads(template_path.read_text(encoding="utf-8"))
    del template["decision_parameters"]["required_return_annualized"]
    template_path.write_text(json.dumps(template), encoding="utf-8")
    response = json.loads(template_path.read_text(encoding="utf-8"))

    with pytest.raises(LocalInvestmentPilotError, match="OPERATOR_INPUT_TEMPLATE_POLICY_FIELD_MISSING:required_return_annualized"):
        _restore_operator_controlled_fields_from_template(template_path, response)


@pytest.mark.parametrize(
    ("field", "invalid_value", "error_code"),
    [
        ("required_return_annualized", "TBD", "REQUIRED_RETURN_POLICY_INVALID"),
        ("required_return_annualized", None, "REQUIRED_RETURN_POLICY_INVALID"),
        ("max_loss_pct", "N/A", "MAX_LOSS_PCT_POLICY_INVALID"),
        ("max_loss_pct", None, "MAX_LOSS_PCT_POLICY_INVALID"),
        ("max_loss_pct", "100", "MAX_LOSS_PCT_OUT_OF_RANGE"),
        ("max_loss_pct", "-1", "MAX_LOSS_PCT_OUT_OF_RANGE"),
    ],
)
def test_invalid_explicit_risk_or_return_policy_input_fails_closed(field, invalid_value, error_code):
    payload = _payload()
    payload["decision_parameters"][field] = invalid_value

    with pytest.raises(LocalInvestmentPilotError, match=error_code):
        _analyse(payload, f"TEST-INVALID-POLICY-{field}-{invalid_value}")


def test_ai_response_must_preserve_operator_required_return_hurdle(tmp_path):
    template_payload = _payload(cutoff="2026-10-10")
    template_payload["decision_parameters"]["required_return_annualized"] = "0.20"
    template_path = _write_input(tmp_path, template_payload)
    response = json.loads(template_path.read_text(encoding="utf-8"))

    # A response that silently reverts the operator's 20% hurdle to the 15% floor
    # must not be accepted as if the original policy had never been changed.
    response["decision_parameters"]["required_return_annualized"] = "0.15"
    with pytest.raises(
        LocalInvestmentPilotError,
        match=r"CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: decision_parameters\.required_return_annualized",
    ):
        _assert_response_preserves_operator_inputs(template_path, response)

    response = json.loads(template_path.read_text(encoding="utf-8"))
    response["decision_parameters"].pop("required_return_annualized")
    with pytest.raises(
        LocalInvestmentPilotError,
        match=r"CHATGPT_CHANGED_OPERATOR_CONTROLLED_FIELDS: decision_parameters\.required_return_annualized",
    ):
        _assert_response_preserves_operator_inputs(template_path, response)


def test_guided_wizard_collects_manual_price_source_claim_and_completes(tmp_path, monkeypatch, capsys):
    import builtins
    import iios_mvp.local_investment_pilot_v01 as pilot

    source_claim = "用户手动提供的 19.74；按 收盘价 15:00 处理；未从交易所或行情供应商独立核验"
    answers = iter([
        "山东赫达",
        "SZ002810",
        "1",
        "2026-10-12",
        "2",
        "0",
        "19.74",
        "2026-10-12",
        "1",
        "1",
        "0",
        "0",
    ])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))

    def simulate_saved_response(response_path, *, previous_signature):
        # Simulate the operator pasting ChatGPT's complete response into TextEdit
        # and saving it. The real file watcher remains bypassed only in this
        # wizard orchestration test; dedicated tests exercise watcher behavior.
        template_paths = list((tmp_path / "inputs").glob("pilot-input-*.json"))
        assert len(template_paths) == 1
        template = json.loads(template_paths[0].read_text(encoding="utf-8"))
        canned = _payload(cutoff="2026-10-12")
        for key in ("evidence_register", "assessment", "forecast_valuation", "operating_driver_forecast", "valuation_transmission", "decision_parameters", "notes"):
            template[key] = canned[key]
        Path(response_path).write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
        signature = pilot._response_file_signature(response_path)
        assert signature is not None and signature != previous_signature
        return signature

    monkeypatch.setattr(pilot, "_wait_for_response_file_change", simulate_saved_response)
    result = run_guided_wizard(
        template_root=tmp_path / "inputs",
        output_root=tmp_path / "runs",
    )

    assert result["status"] == "PILOT_CREATED"
    completed_files = list((tmp_path / "inputs").glob("pilot-completed-*.json"))
    assert len(completed_files) == 1
    saved = json.loads(completed_files[0].read_text(encoding="utf-8"))
    assert saved["price_input"]["price"] == "19.74"
    assert saved["price_input"]["sources_claimed"] == [source_claim]
    assert saved["price_input"]["assurance_label"] == "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"
    assert result["formal_decision_created"] is False
    assert result["auto_execution"] is False
    output = capsys.readouterr().out
    assert "本次完整 JSON 模板" in output
    assert '"schema_version": "IIOS-LOCAL-INVESTMENT-PILOT-0.1"' in output
    assert "不要求操作者另行上传公告或模板" in output
    prompt_files = list((tmp_path / "inputs").glob("pilot-prompt-*.md"))
    assert len(prompt_files) == 1
    assert "经营驱动因素树要求（IIOS-OPERATING-DRIVER-FORECAST-0.1）" in prompt_files[0].read_text(encoding="utf-8")
    assert "B5 估值传导要求（IIOS-VALUATION-TRANSMISSION-0.1）" in prompt_files[0].read_text(encoding="utf-8")
    prompt_text = prompt_files[0].read_text(encoding="utf-8")
    assert "核心投资判断链：必须逐项回答以下六个问题" in prompt_text
    assert "公司究竟靠什么赚钱" in prompt_text
    assert "未来最重要的变化是什么" in prompt_text
    assert "为什么相信变化会发生" in prompt_text
    assert "变化如何进入每股价值" in prompt_text
    assert "当前价格已反映多少" in prompt_text
    assert "哪些事实要求改变看法" in prompt_text
    assert "绝不能把自己的 Base 估值伪装成市场预期" in prompt_text
    assert "15% 年化门槛、共同约束入场价与暂定动作由本地既有计算器独立计算" in prompt_text
    assert "上传输入模板和需要引用的公司公告/财报材料" not in output


def test_guided_wizard_reprompts_same_day_price_before_confirming(tmp_path, monkeypatch, capsys):
    import builtins

    answers = iter([
        "山东赫达",
        "SZ002810",
        "1",
        "2026-10-12",
        "1",
        "0",
        "19.74",
        "2026-10-12",
        "2026-10-09",
        "",
        "0",
    ])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))
    result = run_guided_wizard(
        template_root=tmp_path / "inputs",
        output_root=tmp_path / "runs",
    )
    output = capsys.readouterr().out
    assert result["status"] == "CANCELLED"
    assert "价格观察日期不合法" in output
    assert "PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF" in output
    assert "观察日 2026-10-09" in output
    assert not (tmp_path / "inputs").exists()


def test_response_repair_prompt_includes_validation_feedback_template_and_prior_answer(tmp_path):
    response_path = tmp_path / "response.json"
    response_path.write_text('{"assessment": {}}', encoding="utf-8")
    prompt = _build_response_repair_prompt(
        original_prompt='{"schema_version": "test-template"}',
        response_path=response_path,
        validation_error="CHATGPT_RESPONSE_INCOMPLETE: missing thesis",
    )
    assert "CHATGPT_RESPONSE_INCOMPLETE: missing thesis" in prompt
    assert '"schema_version": "test-template"' in prompt
    assert '{"assessment": {}}' in prompt
    assert "不要让用户手工编辑 JSON" in prompt
    assert "operator_valuation_context" in prompt
    assert "decision_parameters.max_loss_pct" in prompt
    assert "decision_parameters.required_return_annualized" in prompt


def test_candidate_driven_pilot_uses_existing_return_solver_and_outputs_chinese_report(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_local_investment_pilot(input_path=input_path, output_root=tmp_path / "private-runs")
    assert result["status"] == "PILOT_CREATED"
    bundle = Path(result["run_dir"])
    analysis = json.loads((bundle / "analysis.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")
    assert analysis["status"] == "PILOT_NON_CANONICAL"
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert analysis["decision"]["price_screen_action"] == "PRICE_SCREEN_PASS"
    assert analysis["decision"]["core_policy_evaluation"]["status"] == "PILOT_POLICY_PREVIEW_NOT_CANONICAL"
    assert analysis["decision"]["core_policy_evaluation"]["action"] == "REVIEW_REQUIRED"
    assert analysis["decision"]["core_policy_evaluation"]["primary_reason"] == "PORTFOLIO_CONSTRAINT_UNKNOWN"
    assert analysis["decision"]["core_policy_evaluation"]["thesis_admission_status"] == "NOT_ADMITTED"
    assert analysis["decision"]["core_policy_evaluation"]["buy_add_package_complete"] is False
    assert analysis["return_metrics"]["fundamental_target_pass"] is True
    elapsed_days = (date(2027, 12, 31) - date(2026, 10, 10)).days
    year_fraction = Decimal(elapsed_days) / Decimal("365")
    expected_return_cap = Decimal("153") / (Decimal("1.15").ln() * year_fraction).exp()
    assert abs(Decimal(analysis["return_metrics"]["target_entry_price_for_return"]) - expected_return_cap) < Decimal("1e-20")
    assert analysis["return_metrics"]["annualization_year_fraction"] == str(year_fraction)
    assert "PILOT_NON_CANONICAL" in report
    assert "MIE" in report
    assert analysis["governance"]["formal_decision_created"] is False
    assert analysis["governance"]["canonical_run_receipt_created"] is False
    assert analysis["governance"]["auto_execution"] is False


def test_price_above_return_and_risk_entry_ceiling_is_no_buy_when_flat(tmp_path):
    input_path = _write_input(tmp_path, _payload(price="140"))
    result = run_local_investment_pilot(input_path=input_path, output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["return_metrics"]["return_gate_pass"] is False
    assert analysis["decision"]["price_screen_action"] == "PRICE_SCREEN_FAIL"
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "PORTFOLIO_CONSTRAINT_NOT_PROVIDED" in analysis["decision"]["gating_issues"]


def test_core_kernel_capital_action_is_downgraded_without_formal_admission():
    payload = _payload()
    payload["case"]["current_position_pct"] = "5"
    payload["assessment"]["thesis"]["status"] = "BROKEN"
    analysis, _report = _analyse(payload, "TEST-CORE-KERNEL-DEMOTION")
    decision = analysis["decision"]

    # The shared IIOS policy kernel sees the thesis-exit precedence, but the
    # non-canonical AI response cannot itself authorize an EXIT recommendation.
    assert decision["core_policy_evaluation"]["action"] == "EXIT"
    assert decision["core_policy_evaluation"]["capital_action_downgraded"] is True
    assert decision["core_policy_evaluation"]["effective_pilot_action"] == "REVIEW_REQUIRED"
    assert decision["provisional_action"] == "REVIEW_REQUIRED"
    assert decision["formal_decision_created"] is False
    assert decision["execution_authorized"] is False
    assert "NON_CANONICAL_SEMANTICS_CANNOT_AUTHORIZE_CAPITAL_ACTION" in decision["gating_issues"]


def test_unknown_mie_keeps_pilot_action_at_review_required(tmp_path):
    payload = _payload()
    payload["assessment"]["market_implied_expectation"]["status"] = "NOT_IDENTIFIABLE"
    payload["assessment"]["expectation_gap"]["status"] = "UNKNOWN"
    payload["assessment"]["expectation_gap"]["direction"] = "UNKNOWN"
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["return_metrics"]["fundamental_target_pass"] is True
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "MARKET_IMPLIED_EXPECTATION_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]


def test_quote_after_date_only_cutoff_is_not_used_for_price_math(tmp_path):
    payload = _payload(cutoff="2026-10-09")
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["price_input"]["pit_time_status"] == "PRICE_NOT_PIT_QUALIFIED"
    assert analysis["return_metrics"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


def test_explicit_timestamp_cutoff_allows_same_day_attested_price_for_pilot_only():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T15:30:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"

    prepared = _prepare_input(payload)

    assert prepared["case"]["cutoff_semantics"] == "EXPLICIT_TIMESTAMP"
    assert prepared["case"]["as_of_timestamp"] == "2026-10-09T15:30:00+08:00"
    assert prepared["price_input"]["pit_time_status"] == "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY"
    assert prepared["price_input"]["canonical_price_admission"] is False
    assert prepared["price_input"]["source_origin_verified"] is False
    assert prepared["price_input"]["source_use_rights_verified"] is False


def test_explicit_timestamp_cutoff_rejects_price_known_after_cutoff():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T14:59:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"

    prepared = _prepare_input(payload)

    assert prepared["price_input"]["pit_time_status"] == "PRICE_NOT_PIT_QUALIFIED"
    assert "PRICE_KNOWN_AFTER_EXPLICIT_TIMESTAMP_CUTOFF" in prepared["price_input"]["pit_issues"]


def test_explicit_timestamp_cutoff_must_be_timezone_aware_and_match_as_of_date():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T15:30:00"
    with pytest.raises(LocalInvestmentPilotError, match="AS_OF_TIMESTAMP_MUST_INCLUDE_TIMEZONE"):
        _prepare_input(payload)

    payload["case"]["as_of_timestamp"] = "2026-10-10T15:30:00+08:00"
    with pytest.raises(LocalInvestmentPilotError, match="AS_OF_TIMESTAMP_DATE_MUST_MATCH_AS_OF_DATE"):
        _prepare_input(payload)


def test_explicit_timestamp_cutoff_allows_same_day_attested_price_for_pilot_only():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T15:30:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"
    payload["evidence_register"][0]["known_at"] = "2026-10-09T15:20:00+08:00"

    prepared = _prepare_input(payload)

    assert prepared["case"]["cutoff_semantics"] == "EXPLICIT_TIMESTAMP"
    assert prepared["case"]["as_of_timestamp"] == "2026-10-09T15:30:00+08:00"
    assert prepared["price_input"]["pit_time_status"] == "PIT_TIME_COMPATIBLE_FOR_PILOT_ONLY"
    assert prepared["price_input"]["canonical_price_admission"] is False
    assert prepared["price_input"]["source_origin_verified"] is False
    assert prepared["price_input"]["source_use_rights_verified"] is False
    assert prepared["evidence_register"][0]["time_status"] == "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"


def test_explicit_timestamp_cutoff_rejects_price_known_after_cutoff():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T14:59:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"

    prepared = _prepare_input(payload)

    assert prepared["price_input"]["pit_time_status"] == "PRICE_NOT_PIT_QUALIFIED"
    assert "PRICE_KNOWN_AFTER_EXPLICIT_TIMESTAMP_CUTOFF" in prepared["price_input"]["pit_issues"]


def test_explicit_timestamp_cutoff_must_be_timezone_aware_and_match_as_of_date():
    payload = _payload(cutoff="2026-10-09")
    payload["case"]["as_of_timestamp"] = "2026-10-09T15:30:00"
    with pytest.raises(LocalInvestmentPilotError, match="AS_OF_TIMESTAMP_MUST_INCLUDE_TIMEZONE"):
        _prepare_input(payload)

    payload["case"]["as_of_timestamp"] = "2026-10-10T15:30:00+08:00"
    with pytest.raises(LocalInvestmentPilotError, match="AS_OF_TIMESTAMP_DATE_MUST_MATCH_AS_OF_DATE"):
        _prepare_input(payload)


@pytest.mark.parametrize(
    ("known_at", "expected_status"),
    [
        ("2026-10-10", "KNOWN_AT_PRECISION_INSUFFICIENT"),
        ("", "UNKNOWN"),
        ("not-a-date", "KNOWN_AT_INVALID"),
    ],
)
def test_uncertain_timing_for_referenced_evidence_forces_review_required(tmp_path, known_at, expected_status):
    payload = _payload(cutoff="2026-10-10")
    payload["evidence_register"][0]["known_at"] = known_at
    if known_at in {"", "not-a-date"}:
        # No dated publication fallback exists in these deliberately unknown cases.
        payload["evidence_register"][0]["published_at"] = "UNKNOWN"

    prepared = _prepare_input(payload)
    assert prepared["evidence_register"][0]["time_status"] == expected_status
    assert prepared["uncertain_timing_evidence_references"] == ["E1"]

    analysis, report = _analyse(payload, "TEST-TIMING-UNKNOWN")
    assert analysis["return_metrics"] is not None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "REFERENCED_EVIDENCE_TIMING_UNCERTAIN" in analysis["decision"]["gating_issues"]
    assert "被引用来源缺少可靠的截止前已知时点" in report
    assert "E1" in report


def test_guided_observation_date_accepts_same_day_only_with_explicit_cutoff():
    from datetime import datetime, timedelta, timezone

    same_day = date(2026, 10, 9)
    instant = datetime(2026, 10, 9, 15, 30, tzinfo=timezone(timedelta(hours=8)))
    assert _validate_guided_observation_date(same_day, same_day, cutoff_timestamp=instant) == same_day
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF"):
        _validate_guided_observation_date(same_day, same_day)


def test_guided_cutoff_modes_remove_timezone_syntax_from_common_path():
    cutoff = date(2026, 10, 12)

    instant, timestamp = _guided_cutoff_timestamp(cutoff, "1")
    assert timestamp is None
    assert instant.isoformat() == "2026-10-12T00:00:00+08:00"

    instant, timestamp = _guided_cutoff_timestamp(cutoff, "2")
    assert timestamp == "2026-10-12T15:30:00+08:00"
    assert instant.isoformat() == timestamp

    with pytest.raises(LocalInvestmentPilotError, match="AS_OF_TIMESTAMP_MUST_INCLUDE_TIMEZONE"):
        _guided_cutoff_timestamp(cutoff, "3", "2026-10-12")
    with pytest.raises(LocalInvestmentPilotError, match="CUTOFF_MODE_MUST_BE_1_2_OR_3"):
        _guided_cutoff_timestamp(cutoff, "2026-10-12")


def test_guided_observation_date_rejects_weekends_instead_of_treating_them_as_market_closes():
    saturday = date(2026, 10, 10)
    cutoff = date(2026, 10, 12)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_BE_TRADING_WEEKDAY"):
        _validate_guided_observation_date(
            saturday, cutoff, cutoff_timestamp=None
        )


def test_guided_research_response_blocks_an_untouched_or_mostly_empty_template():
    payload = _payload()
    _validate_guided_research_response(payload)

    payload["evidence_register"] = []
    payload["assessment"]["trust"]["summary"] = "尚未完成信任审查"
    payload["assessment"]["thesis"]["core_statement"] = ""
    payload["forecast_valuation"]["thesis_break_stress"]["rationale"] = ""

    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_RESPONSE_INCOMPLETE"):
        _validate_guided_research_response(payload)


def test_guided_research_response_allows_explicit_unknowns_with_real_explanations():
    payload = _payload()
    for section, summary in (
        ("trust", "当前未能独立验证最终控制人与审计质量，列为 UNKNOWN，需人工复核年报附注。"),
        ("reality", "关键产品需求数据尚不充分，因此经营现实暂列 UNKNOWN。"),
        ("quality", "现金流与利润需跨周期验证，暂列 UNKNOWN。"),
        ("market_implied_expectation", "无法从可获得历史一致预期识别市场隐含假设，列为 NOT_IDENTIFIABLE。"),
        ("expectation_gap", "由于市场隐含预期不可识别，预期差方向未知。"),
        ("risk", "未能完成全部风险量化，当前结论需人工复核。"),
    ):
        payload["assessment"][section]["status"] = "UNKNOWN"
        payload["assessment"][section]["summary"] = summary
    _validate_guided_research_response(payload)


def test_incomplete_valuation_produces_report_without_inventing_returns(tmp_path):
    payload = _payload()
    payload["forecast_valuation"]["entry_value_reference_per_share"] = None
    payload["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] = None
    payload["eps_multiple_valuation"]["scenarios"]["base"]["eps_per_share"]["value"] = None
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    report = (Path(result["run_dir"]) / "report.md").read_text(encoding="utf-8")
    assert analysis["return_metrics"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "回报计算尚未完成" in report


def test_replay_reruns_the_saved_input_and_matches_return_calculation(tmp_path):
    input_path = _write_input(tmp_path)
    output_root = tmp_path / "private-runs"
    first = run_local_investment_pilot(input_path=input_path, output_root=output_root)
    replay = run_local_investment_pilot(
        input_path=Path(first["run_dir"]) / "input.json",
        output_root=output_root,
        replay_of=first["pilot_id"],
    )
    first_analysis = json.loads((Path(first["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    replay_analysis = json.loads((Path(replay["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert replay["status"] == "PILOT_REPLAY_MATCHED"
    assert replay["replay_of"] == first["pilot_id"]
    assert replay["replay_comparison"]["status"] == "MATCH"
    assert replay["replay_comparison"]["hash_verification"] == "PASS"
    assert "decision" in replay["replay_comparison"]["compared_fields"]
    assert replay_analysis["return_metrics"] == first_analysis["return_metrics"]
    assert replay_analysis["decision"]["provisional_action"] == first_analysis["decision"]["provisional_action"]
    receipt = json.loads((Path(replay["run_dir"]) / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert receipt["replay_comparison"]["status"] == "MATCH"


def test_prepare_input_rejects_weekend_price_observation_dates():
    payload = _payload(cutoff="2026-10-12")
    payload["price_input"]["observation_date"] = "2026-10-10"
    payload["price_input"]["known_at"] = "2026-10-10T15:00:00+08:00"
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_BE_TRADING_WEEKDAY"):
        _prepare_input(payload)


def test_entry_price_is_explicitly_hypothetical_and_never_claims_a_fill():
    payload = _payload(cutoff="2026-10-16")
    payload["case"]["as_of_timestamp"] = "2026-10-16T15:30:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-16"
    payload["price_input"]["known_at"] = "2026-10-16T15:00:00+08:00"

    prepared = _prepare_input(payload)
    entry = prepared["price_input"]["entry_assumption"]

    assert entry["schema_version"] == "IIOS-ENTRY-PRICE-ASSUMPTION-0.1"
    assert entry["mode"] == "HYPOTHETICAL_ENTRY_AT_INPUT_PRICE_ON_CUTOFF_DATE"
    assert entry["hypothetical_entry_date"] == "2026-10-16"
    assert entry["price_observation_vs_cutoff"] == "SAME_CALENDAR_DATE"
    assert entry["price_known_before_cutoff"] is True
    assert entry["actual_execution_status"] == "NOT_CONFIRMED"
    assert entry["actual_execution_confirmed"] is False
    assert entry["execution_guaranteed"] is False
    assert entry["actual_dividend_entitlement_confirmed"] is False

    analysis, report = _analyse(payload, "TEST-HYPOTHETICAL-ENTRY-NOT-A-FILL")
    returned_entry = analysis["price_input"]["entry_assumption"]
    assert returned_entry == entry
    assert "反事实测算" in report
    assert "实际成交：未确认，不保证能以该价格成交" in report
    assert "不代表实际成交或实际分红权益已确认" in report


def test_prior_date_price_is_labelled_as_a_reference_not_a_fresh_execution_quote():
    payload = _payload(cutoff="2026-10-12")
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"

    prepared = _prepare_input(payload)
    entry = prepared["price_input"]["entry_assumption"]

    assert entry["price_observation_vs_cutoff"] == "PRIOR_DATE_REFERENCE"
    assert entry["hypothetical_entry_date"] == "2026-10-12"
    assert entry["actual_execution_confirmed"] is False
    assert entry["execution_guaranteed"] is False


def test_manual_price_cannot_be_relabelled_as_source_verified(tmp_path):
    payload = _payload()
    payload["price_input"]["assurance_label"] = "CANONICAL_PRICE_ADMISSION_VERIFIED"
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_MUST_REMAIN_OPERATOR_ATTESTED"):
        run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")


def test_invalid_three_year_override_falls_back_to_default_horizon(tmp_path):
    payload = _payload()
    payload["decision_parameters"]["horizon_years"] = 3
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["decision_parameters"]["horizon_years"] == 1
    assert "3 年覆盖条件不足" in analysis["decision_parameters"]["horizon_selection_rationale"]



def test_explicit_note_price_conflict_forces_review_required(tmp_path):
    payload = _payload(price="19.51")
    payload["notes"] = "用户手动提供的19.74；本次未独立核验价格来源。"
    result = run_local_investment_pilot(
        input_path=_write_input(tmp_path, payload),
        output_root=tmp_path / "private-runs",
    )
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    report = (Path(result["run_dir"]) / "report.md").read_text(encoding="utf-8")

    assert analysis["price_input"]["price"] == "19.51"
    assert analysis["notes_price_conflicts"] == ["19.74"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "OPERATOR_NOTE_PRICE_CONFLICTS_WITH_PRICE_INPUT" in analysis["decision"]["gating_issues"]
    assert "当前价：19.51 CNY" in report
    assert "19.74" in report
    assert "带标签的备注股价一致性：**CONFLICT**" in report


@pytest.mark.parametrize("scenario_name", ["bear", "base", "bull"])
def test_missing_scenario_cash_distributions_do_not_silently_default_to_zero(scenario_name):
    payload = _payload()
    payload["forecast_valuation"]["scenarios"][scenario_name].pop("cash_distributions_per_share")

    analysis, report = _analyse(payload, f"TEST-MISSING-SCENARIO-DISTRIBUTIONS-{scenario_name}")

    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == f"{scenario_name.upper()}_SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED"
    assert analysis["price_zone_sensitivity"]["status"] == "UNKNOWN"
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert f"### {scenario_name.title()} 情景" in report
    assert "- 每股现金分配合计：UNKNOWN CNY" in report
    assert "不能将缺失字段默认为零" in report


def test_explicit_zero_scenario_cash_distributions_remain_calculable():
    payload = _payload()
    for row in payload["forecast_valuation"]["scenarios"].values():
        row["cash_distributions_per_share"] = "0"

    analysis, _report = _analyse(payload, "TEST-EXPLICIT-ZERO-DISTRIBUTIONS")

    assert analysis["return_metrics"] is not None
    assert analysis["price_zone_sensitivity"]["status"] != "UNKNOWN"
    assert "SCENARIO_CASH_DISTRIBUTIONS_UNRESOLVED" not in analysis["decision"]["gating_issues"]


@pytest.mark.parametrize(
    ("target", "field", "expected_issue"),
    [
        ("stress", "cash_distributions_per_share", "THESIS_BREAK_STRESS_CASH_DISTRIBUTIONS_UNRESOLVED"),
        ("bear", "cash_distributions_per_share", "THESIS_BREAK_STRESS_BEAR_CASH_DISTRIBUTIONS_UNRESOLVED"),
    ],
)
def test_missing_stress_or_bear_cash_distributions_blocks_stress_readiness(target, field, expected_issue):
    payload = _payload()
    if target == "stress":
        payload["forecast_valuation"]["thesis_break_stress"].pop(field)
    else:
        payload["forecast_valuation"]["scenarios"]["bear"].pop(field)

    analysis, report = _analyse(payload, f"TEST-MISSING-STRESS-DISTRIBUTIONS-{target}")

    assert analysis["thesis_break_stress_review"]["status"] == "REVIEW_REQUIRED"
    assert expected_issue in analysis["thesis_break_stress_review"]["issues"]
    assert expected_issue in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert analysis["portfolio_package"].get("conditional_proposed_position_pct") is None
    assert "不能将缺失字段默认为零" in report


def test_thesis_break_stress_is_not_probability_weighted_and_missing_stress_gates_action():
    payload = _payload()
    analysis, report = _analyse(payload, "TEST-STRESS")

    assert analysis["thesis_break_stress_review"]["status"] == "PASS"
    assert analysis["thesis_break_stress_review"]["probability_weighted"] is False
    assert str(analysis["thesis_break_stress_review"]["stress_terminal_wealth"]) == "80"
    assert str(analysis["thesis_break_stress_review"]["stress_total_return"]) == "-0.2"
    assert analysis["return_metrics"]["expected_terminal_wealth"] != analysis["thesis_break_stress_review"]["stress_terminal_wealth"]
    assert "PASS 仅表示压力输入可识别、数值可计算且压力总财富低于 Bear" in report
    assert "不表示这一下跌幅度符合投资者损失容忍度" in report
    assert "Bear 损失上限单独按 Bear 情景核验" in report
    assert "不纳入 Bear/Base/Bull 概率加权" in report

    payload["forecast_valuation"].pop("thesis_break_stress")
    missing_analysis, _missing_report = _analyse(payload, "TEST-STRESS-MISSING")
    assert missing_analysis["return_metrics"] is not None
    assert missing_analysis["thesis_break_stress_review"]["status"] == "MISSING"
    assert missing_analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "THESIS_BREAK_STRESS_MISSING" in missing_analysis["decision"]["gating_issues"]


def test_bear_failure_path_must_be_explicit():
    payload = _payload()
    payload["forecast_valuation"]["scenarios"]["bear"]["operating_impact"] = ""
    analysis, report = _analyse(payload, "TEST-BEAR-PATH")
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "BEAR_FAILURE_PATH_INCOMPLETE" in analysis["decision"]["gating_issues"]
    assert "经营影响路径：" in report


def test_thesis_break_stress_must_be_more_severe_than_bear():
    payload = _payload()
    payload["forecast_valuation"]["thesis_break_stress"]["terminal_value_per_share"] = "125"
    analysis, report = _analyse(payload, "TEST-STRESS-NOT-WORSE")
    assert analysis["thesis_break_stress_review"]["status"] == "REVIEW_REQUIRED"
    assert "THESIS_BREAK_STRESS_NOT_MORE_SEVERE_THAN_BEAR" in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("target", "field", "placeholder", "expected_issue"),
    [
        ("bear", "failure_trigger", "UNKNOWN", "BEAR_FAILURE_PATH_INCOMPLETE"),
        ("bear", "operating_impact", "TBD", "BEAR_FAILURE_PATH_INCOMPLETE"),
        ("stress", "failure_trigger", "N/A", "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE"),
        ("stress", "operating_impact", "NOT_IDENTIFIABLE", "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE"),
        ("stress", "valuation_method", "未提供依据", "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE"),
        ("stress", "rationale", "概率未知", "THESIS_BREAK_STRESS_INPUTS_INCOMPLETE"),
    ],
)
def test_bear_and_thesis_break_stress_reject_placeholder_only_rationales(
    target, field, placeholder, expected_issue
):
    payload = _payload()
    if target == "bear":
        payload["forecast_valuation"]["scenarios"]["bear"][field] = placeholder
    else:
        payload["forecast_valuation"]["thesis_break_stress"][field] = placeholder

    analysis, _report = _analyse(payload, f"TEST-STRESS-PLACEHOLDER-{target}-{field}")
    stress_review = analysis["thesis_break_stress_review"]

    assert stress_review["status"] == "REVIEW_REQUIRED"
    assert expected_issue in stress_review["issues"]
    assert expected_issue in analysis["decision"]["gating_issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    package = analysis["portfolio_package"]
    assert package.get("conditional_proposed_position_pct") is None


def test_bear_base_bull_total_wealth_ordering_is_required():
    payload = _payload()
    payload["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] = "160"
    _sync_eps_multiple_values(payload, {"bear": "160", "base": "150", "bull": "180"})
    analysis, report = _analyse(payload, "TEST-SCENARIO-ORDER")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "PRIMARY_VALUATION_MODEL_NOT_ELIGIBLE:EPS_MULTIPLE_CALCULATION_NOT_ELIGIBLE"
    assert "EPS_MULTIPLE_SCENARIO_ORDERING_INCONSISTENT" in analysis["valuation_model_consistency"]["issues"]
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"



def test_pilot_receipt_never_claims_canonical_authority(tmp_path):
    result = run_local_investment_pilot(input_path=_write_input(tmp_path), output_root=tmp_path / "private-runs")
    receipt = json.loads((Path(result["run_dir"]) / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PILOT_NON_CANONICAL"
    assert receipt["formal_decision_created"] is False
    assert receipt["canonical_run_receipt_created"] is False
    assert receipt["auto_execution"] is False


def test_extract_json_object_accepts_chatgpt_code_fence_and_leading_text():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    fence = chr(96) * 3
    source = 'Here is the result:\n' + fence + 'json\n{"schema_version": "IIOS-LOCAL-INVESTMENT-PILOT-0.1", "value": 2}\n' + fence
    result = _extract_json_object(source)
    assert result["schema_version"] == PILOT_SCHEMA
    assert result["value"] == 2


def test_extract_json_object_repairs_malformed_url_punctuation_escapes():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    # Regression from the 2026-10-16 pasted response: the text normalizer
    # inserted invalid JSON escapes before URL colons and a domain dot.
    source = r'{"source_ref":"https\://static.cninfo.com.cn/report.pdf",' \
        r'"issuer_ref":"https\://www\.wuxiapptec.com/news"}'
    result = _extract_json_object(source)
    assert result["source_ref"] == "https://static.cninfo.com.cn/report.pdf"
    assert result["issuer_ref"] == "https://www.wuxiapptec.com/news"


def test_extract_json_object_reports_json_parse_location():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    with pytest.raises(
        LocalInvestmentPilotError,
        match=r"CHATGPT_JSON_INVALID.*第 1 行，第 \d+ 列",
    ):
        _extract_json_object(r'{"source_ref":"bad\q"}')


@pytest.mark.parametrize(
    "known_at",
    [
        "2026-08-30；具体披露时分 UNKNOWN",
        "2026-08-30；具体披露时间 UNKNOWN",
    ],
)
def test_explicit_unknown_disclosure_time_keeps_valid_date_only_precision(known_at):
    payload = _payload(cutoff="2026-10-10")
    payload["evidence_register"][0]["known_at"] = known_at

    prepared = _prepare_input(payload)
    source = prepared["evidence_register"][0]

    assert source["known_at"] == "2026-08-30"
    assert source["known_at_original"] == known_at
    assert source["known_at_precision"] == "DATE_ONLY_EXPLICIT_TIME_UNKNOWN"
    assert source["time_status"] == "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
    assert "E1" not in prepared["uncertain_timing_evidence_references"]


def test_extract_json_object_blocks_incomplete_clipboard_response():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    fence = chr(96) * 3
    source = fence + 'json\n{"schema_version": '
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID"):
        _extract_json_object(source)


@pytest.mark.parametrize(
    "suffix",
    [
        " trailing explanation must not be silently ignored",
        '\\n{"second_object": true}',
        '\\n\\\u0060\\\u0060\\\u0060 trailing text',
    ],
)
def test_redteam_chatgpt_json_rejects_trailing_text_second_object_and_broken_fence(suffix):
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    source = '{"schema_version": "IIOS-LOCAL-INVESTMENT-PILOT-0.1", "value": 1}' + suffix
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT"):
        _extract_json_object(source)


def test_redteam_chatgpt_json_requires_closed_code_fence():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    fence = chr(96) * 3
    source = fence + 'json\\n{"schema_version": "IIOS-LOCAL-INVESTMENT-PILOT-0.1"}'
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID_CODE_FENCE_NOT_CLOSED"):
        _extract_json_object(source)


def test_redteam_url_escape_repair_does_not_ignore_trailing_text():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    source = r'{"source_ref":"https\\://example.com/a.pdf"} trailing note'
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT"):
        _extract_json_object(source)


@pytest.mark.parametrize(
    "source, expected",
    [
        ('{"a": 1,}', {"a": 1}),
        ('{"a": [1, 2,],}', {"a": [1, 2]}),
        (r'{"source_ref":"https\://example.com/a.pdf","items":[1,],}', {
            "source_ref": "https://example.com/a.pdf",
            "items": [1],
        }),
        (r'{"text":"literal ,} and escaped quote \",] here","items":[1,2,],}', {
            "text": 'literal ,} and escaped quote ",] here',
            "items": [1, 2],
        }),
    ],
)
def test_redteam_chatgpt_json_repairs_only_trailing_commas_outside_strings(source, expected):
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    assert _extract_json_object(source) == expected


def test_redteam_trailing_comma_repair_does_not_bypass_trailing_content_gate():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_TRAILING_CONTENT_AFTER_OBJECT"):
        _extract_json_object('{"a": 1,} trailing text')


def test_redteam_trailing_comma_repair_does_not_accept_non_trailing_malformed_comma():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT"):
        _extract_json_object('{"a": 1,, "b": 2}')


def test_redteam_trailing_comma_repair_does_not_complete_truncated_object():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID_COPY_THE_COMPLETE_JSON_OBJECT"):
        _extract_json_object('{"a": {"b": 1,}')



def test_research_status_aliases_known_at_precision_and_value_driver_schema():
    payload = _payload(cutoff="2026-10-10")
    payload["evidence_register"][0]["known_at"] = "2026-08-30；具体时分 UNKNOWN"
    payload["assessment"]["trust"]["status"] = "PASS_WITH_LIMITATIONS"
    payload["assessment"]["reality"]["status"] = "SUPPORTED_WITH_MATERIAL_CAVEATS"
    payload["assessment"]["quality"]["status"] = "HIGH_QUALITY_WITH_CYCLICAL_AND_POLICY_RISKS"
    payload["assessment"]["thesis"]["status"] = "CONDITIONALLY_VALID"
    payload["assessment"]["expectation_gap"] = {
        "status": "ANALYST_CASE_INDICATES_INSUFFICIENT_RETURN",
        "direction": "CURRENT_PRICE_ABOVE_RISK_ADJUSTED_ENTRY_REFERENCE",
        "summary": "Analyst case return is below hurdle; not market consensus.",
        "evidence_refs": ["E1"],
    }
    payload["assessment"]["risk"]["status"] = "MATERIAL"
    payload["assessment"]["value_drivers"] = [{
        "rank": 1,
        "name": "持续经营业务收入增长",
        "status": "OBSERVED_AND_FORECAST",
        "summary": "订单和收入推动长期价值，但需验证兑现。",
        "evidence_refs": ["E1"],
    }]

    prepared = _prepare_input(payload)
    assessment = prepared["assessment"]
    source = prepared["evidence_register"][0]

    assert assessment["trust"]["status"] == "REVALIDATION"
    assert assessment["trust"]["status_input"] == "PASS_WITH_LIMITATIONS"
    assert assessment["reality"]["status"] == "CONDITIONAL"
    assert assessment["quality"]["status"] == "CONDITIONAL"
    assert assessment["thesis"]["status"] == "WATCH"
    assert assessment["expectation_gap"]["status"] == "UNKNOWN"
    assert assessment["expectation_gap"]["direction"] == "NEGATIVE"
    assert assessment["risk"]["status"] == "UNKNOWN"
    assert assessment["value_drivers"][0]["driver"] == "持续经营业务收入增长"
    assert assessment["value_drivers"][0]["rationale"] == "订单和收入推动长期价值，但需验证兑现。"
    assert assessment["value_drivers"][0]["impact"] == "UNKNOWN"
    assert assessment["value_drivers"][0]["source_status"] == "OBSERVED_AND_FORECAST"
    assert source["known_at"] == "2026-08-30"
    assert source["known_at_original"] == "2026-08-30；具体时分 UNKNOWN"
    assert source["known_at_precision"] == "DATE_ONLY_EXPLICIT_TIME_UNKNOWN"
    assert source["time_status"] == "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
    assert "E1" not in prepared["uncertain_timing_evidence_references"]

    analysis, report = _analyse(payload, "test-status-aliases")
    report = pilot._render_report(analysis)
    assert "输入标签 PASS_WITH_LIMITATIONS" in report
    assert "持续经营业务收入增长" in report
    assert "订单和收入推动长期价值，但需验证兑现。" in report


def test_b4_links_explicit_service_revenue_and_reconciles_valuation_bridge():
    payload = _payload(cutoff="2026-10-10")
    scenario_values = {
        "bear": {
            "revenue": 1000, "cost_ratio": 0.50, "fixed": 100, "da": 50,
            "finance": 10, "tax": 0.20, "capex": 80, "wc": 10,
        },
        "base": {
            "revenue": 2000, "cost_ratio": 0.45, "fixed": 150, "da": 100,
            "finance": 20, "tax": 0.20, "capex": 100, "wc": 20,
        },
        "bull": {
            "revenue": 3000, "cost_ratio": 0.40, "fixed": 200, "da": 120,
            "finance": 30, "tax": 0.20, "capex": 130, "wc": 30,
        },
    }

    def measure(value, unit):
        return {
            "value": value,
            "unit": unit,
            "data_class": "ANALYST_ASSUMPTION",
            "basis": "Synthetic assumption for regression test only.",
            "evidence_refs": [],
            "note": "Not an actual result.",
        }

    payload["forecast_valuation"]["assumptions"] = [{
        "assumption_id": "A2",
        "name": "成本率",
        "values": {
            f"{name}_cost_of_revenue_ratio": row["cost_ratio"]
            for name, row in scenario_values.items()
        },
        "data_class": "ANALYST_ASSUMPTION",
        "basis": "Synthetic same-scenario cost-of-revenue ratio.",
        "evidence_refs": [],
    }]

    payload["operating_driver_forecast"] = {
        "schema_version": "IIOS-OPERATING-DRIVER-FORECAST-0.1",
        "scope": "COMPANY_WIDE",
        "actuals_period": "2026H1",
        "forecast_period": "2027FY",
        "summary": "Service company forecast uses direct segment revenue assumptions; tonnage metrics remain unknown.",
        "product_lines": [{
            "product_id": "SERVICE",
            "product_name": "研发/测试服务",
            "capacity_tonnes_per_year": {
                "value": None, "unit": "tonnes/year", "data_class": "UNKNOWN",
                "basis": "", "evidence_refs": [], "note": "Not a tonne-based service.",
            },
            "historical_actuals": {
                "revenue_cny": {
                    "value": 250000,
                    "unit": "CNY",
                    "data_class": "OBSERVED_ACTUAL",
                    "basis": "Synthetic observed segment revenue for regression testing only.",
                    "evidence_refs": ["E1"],
                    "note": "Source is a synthetic fixture, not real issuer evidence.",
                },
            },
        }],
        "scenarios": {},
    }

    for name, row in scenario_values.items():
        revenue = row["revenue"]
        cogs = revenue * row["cost_ratio"]
        gross_profit = revenue - cogs
        ebitda = gross_profit - row["fixed"]
        ebit = ebitda - row["da"]
        pretax = ebit - row["finance"]
        net_profit = pretax * (1 - row["tax"])
        payload["operating_driver_forecast"]["scenarios"][name] = {
            "product_lines": [{
                "product_id": "SERVICE",
                "revenue_cny": measure(revenue, "CNY"),
            }],
            "fixed_cash_opex_cny": measure(row["fixed"], "CNY"),
            "depreciation_amortization_cny": measure(row["da"], "CNY"),
            "finance_cost_cny": measure(row["finance"], "CNY"),
            "tax_rate": measure(row["tax"], "ratio"),
            "cash_capex_cny": measure(row["capex"], "CNY"),
            "change_working_capital_cny": measure(row["wc"], "CNY"),
        }
        payload["forecast_valuation"]["scenarios"][name]["operating_financial_bridge"] = {
            "revenue_cny": revenue,
            "cost_of_revenue_cny": cogs,
            "gross_profit_cny": gross_profit,
            "fixed_cash_opex_cny": row["fixed"],
            "ebitda_cny": ebitda,
            "depreciation_amortization_cny": row["da"],
            "ebit_cny": ebit,
            "finance_cost_cny": row["finance"],
            "pretax_profit_cny": pretax,
            "tax_rate": row["tax"],
            "net_profit_proxy_cny": net_profit,
            "cash_capex_cny": row["capex"],
            "change_working_capital_cny": row["wc"],
            "free_cash_flow_proxy_cny": net_profit + row["da"] - row["capex"] - row["wc"],
        }

    prepared = _prepare_input(payload)
    b4 = prepared["operating_driver_forecast"]
    assert b4["status"] == "SCENARIOS_CALCULATED"
    historical_bridge = b4["product_lines"][0]["historical_actual_bridge"]
    assert Decimal(historical_bridge["revenue_cny"]) == Decimal("250000")
    assert historical_bridge["revenue_basis"] == "DIRECT_REPORTED_REVENUE"
    historical_render = render_operating_driver_section(b4, payload["forecast_valuation"]["scenarios"])
    assert "已披露历史收入：250000 CNY" in "\\n".join(historical_render)
    assert "识别口径：DIRECT_REPORTED_REVENUE" in "\\n".join(historical_render)
    assert Decimal(b4["scenarios"]["bear"]["revenue_cny"]) == Decimal("1000")
    assert Decimal(b4["scenarios"]["bear"]["variable_cost_cny"]) == Decimal("500")
    assert Decimal(b4["scenarios"]["bear"]["net_profit_cny"]) == Decimal("272")
    assert b4["valuation_reconciliation"]["status"] == "MATCH"
    assert all(
        b4["valuation_reconciliation"]["scenarios"][name]["status"] == "MATCH"
        for name in ("bear", "base", "bull")
    )
    assert b4["cross_node_assumption_links"][0]["status"] == "LINKED_SAME_SCENARIO_ASSUMPTION"
    assert "free_cash_flow_proxy_cny" in b4["valuation_reconciliation"]["excluded_metrics"][0]["field"]

    # Same-scenario reuse must not turn a placeholder/missing source basis into
    # a seemingly identifiable B4 basis merely by wrapping it in generated prose.
    for invalid_basis in ("UNKNOWN", "N/A", "TBD", "未提供依据", ""):
        bad_payload = json.loads(json.dumps(payload))
        bad_payload["forecast_valuation"]["assumptions"][0]["basis"] = invalid_basis
        bad_analysis, bad_report = _analyse(
            bad_payload, f"TEST-B4-INVALID-CROSS-NODE-BASIS-{invalid_basis or 'EMPTY'}"
        )
        bad_b4 = bad_analysis["operating_driver_forecast"]
        bad_links = bad_b4["cross_node_assumption_links"]
        assert len(bad_links) == 3
        assert all(
            link["status"] == "ASSUMPTION_BASIS_NOT_IDENTIFIABLE_NOT_LINKED"
            for link in bad_links
        )
        assert bad_b4["scenarios"]["bear"]["net_profit_cny"] is None
        assert bad_b4["scenarios"]["base"]["net_profit_cny"] is None
        assert bad_b4["scenarios"]["bull"]["net_profit_cny"] is None
        assert "原始依据为空或仅为 UNKNOWN/N/A/TBD 等占位文本" in bad_report
        assert "LINKED_SAME_SCENARIO_ASSUMPTION" not in [
            link["status"] for link in bad_links
        ]


def test_root_one_click_launcher_uses_the_guided_entry_and_has_valid_bash():
    root = Path(__file__).resolve().parents[1]
    launcher = root / "启动IIOS投资分析.command"
    result = subprocess.run(["bash", "-n", str(launcher)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    content = launcher.read_text(encoding="utf-8")
    assert 'python3 -m iios_mvp.local_investment_pilot_v01 --wizard' in content
    assert "--create-template" not in content
    assert "git pull" not in content

def test_run_receipt_binds_exact_input_analysis_and_report_bytes(tmp_path):
    result = run_local_investment_pilot(
        input_path=_write_input(tmp_path),
        output_root=tmp_path / "private-runs",
    )
    bundle = Path(result["run_dir"])
    receipt = json.loads((bundle / "pilot_receipt.json").read_text(encoding="utf-8"))

    assert set(receipt["file_manifest"]) == {"input.json", "analysis.json", "report.md"}
    checked = verify_local_pilot_bundle(bundle)
    assert checked["status"] == "PILOT_BUNDLE_HASH_CHECK_PASS"
    assert checked["pilot_id"] == result["pilot_id"]
    assert checked["hash_algorithm"] == "SHA-256"
    assert all(item["byte_size"] >= 0 and len(item["sha256"]) == 64 for item in checked["verified_files"])


@pytest.mark.parametrize(
    "malformed_provenance",
    [
        "CAPTURED_RAW_CHATGPT_RESPONSE",
        ["CAPTURED_RAW_CHATGPT_RESPONSE"],
        True,
        1,
    ],
)
def test_run_bundle_verifier_rejects_malformed_response_claim_without_capture(
    tmp_path: Path,
    malformed_provenance: object,
) -> None:
    result = run_local_investment_pilot(
        input_path=_write_input(tmp_path),
        output_root=tmp_path / "private-runs",
    )
    run_dir = Path(result["run_dir"])
    input_path = run_dir / "input.json"
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload["_local_research_response_provenance"] = malformed_provenance
    input_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    input_path.write_bytes(input_bytes)

    receipt_path = run_dir / "pilot_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["file_manifest"]["input.json"] = {
        "sha256": hashlib.sha256(input_bytes).hexdigest(),
        "byte_size": len(input_bytes),
    }
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(
        LocalInvestmentPilotError,
        match="RUN_INPUT_CLAIMS_RESEARCH_RESPONSE_WITHOUT_CAPTURE",
    ):
        verify_local_pilot_bundle(run_dir)



@pytest.mark.parametrize(
    "malformed_receipt_provenance",
    [
        "CAPTURED_RAW_CHATGPT_RESPONSE",
        ["CAPTURED_RAW_CHATGPT_RESPONSE"],
        True,
        1,
        {"schema_version": pilot.LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA, "status": "UNKNOWN"},
    ],
)
def test_run_bundle_verifier_rejects_malformed_receipt_response_provenance(
    tmp_path: Path,
    malformed_receipt_provenance: object,
) -> None:
    result = run_local_investment_pilot(
        input_path=_write_input(tmp_path),
        output_root=tmp_path / "private-runs",
    )
    run_dir = Path(result["run_dir"])
    receipt_path = run_dir / "pilot_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["research_response_provenance"] = malformed_receipt_provenance
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(LocalInvestmentPilotError, match="RUN_RESEARCH_RESPONSE_PROVENANCE_INVALID"):
        verify_local_pilot_bundle(run_dir)


def _write_captured_research_input(tmp_path: Path) -> tuple[Path, Path, tuple[int, int, str]]:
    response_path = tmp_path / "chatgpt-response-original.txt"
    response_text = json.dumps(_payload(), ensure_ascii=False, indent=2)
    response_path.write_text(response_text, encoding="utf-8")
    signature = pilot._response_file_signature(response_path)
    assert signature is not None
    payload = _payload()
    payload["_local_research_response_provenance"] = {
        "schema_version": pilot.LOCAL_RESEARCH_RESPONSE_PROVENANCE_SCHEMA,
        "status": "CAPTURED_RAW_CHATGPT_RESPONSE",
        "source_filename": response_path.name,
        "sha256": signature[2],
        "byte_size": signature[0],
        "capture_stage": "RAW_RESPONSE_HASHED_ON_STABLE_SAVE_BEFORE_LOCAL_OPERATOR_FIELD_RECOVERY",
        "validation_status": "JSON_OBJECT_PARSE_PASSED; COMPLETED_INPUT_REQUIRED_FIELDS_PASSED_AFTER_LOCAL_OPERATOR_FIELD_RECOVERY",
        "raw_response_file_modified_by_runner": False,
    }
    input_path = _write_input(tmp_path, payload)
    return input_path, response_path, signature


def test_run_receipt_preserves_exact_raw_chatgpt_response_and_hash(tmp_path: Path):
    input_path, response_path, signature = _write_captured_research_input(tmp_path)
    result = run_local_investment_pilot(
        input_path=input_path,
        output_root=tmp_path / "private-runs",
        research_response_path=response_path,
        expected_research_response_sha256=signature[2],
        expected_research_response_byte_size=signature[0],
    )
    run_dir = Path(result["run_dir"])
    raw_path = run_dir / pilot.RAW_RESEARCH_RESPONSE_FILENAME
    receipt = json.loads((run_dir / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert raw_path.read_bytes() == response_path.read_bytes()
    assert raw_path.stat().st_mode & 0o077 == 0
    fp = pilot._fingerprint_file(raw_path)
    assert receipt["research_response_provenance"]["status"] == "CAPTURED_RAW_CHATGPT_RESPONSE"
    assert receipt["research_response_provenance"]["response_validation_status"] == (
        "RAW_JSON_OBJECT_PARSE_PASSED; NORMALIZED_INPUT_REQUIRED_FIELDS_PASSED_AFTER_OPERATOR_FIELD_RESTORATION"
    )
    assert receipt["research_response_provenance"]["sha256"] == fp["sha256"] == signature[2]
    assert receipt["research_response_provenance"]["byte_size"] == fp["byte_size"] == signature[0]
    assert receipt["research_response_provenance"]["origin_pilot_id"] == result["pilot_id"]
    assert receipt["file_manifest"][pilot.RAW_RESEARCH_RESPONSE_FILENAME] == fp
    analysis = json.loads((run_dir / "analysis.json").read_text(encoding="utf-8"))
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert analysis["research_response_provenance"]["sha256"] == fp["sha256"]
    assert analysis["research_response_provenance"]["byte_size"] == fp["byte_size"]
    assert "原始 ChatGPT 响应来源链" in report
    assert fp["sha256"] in report
    verified = verify_local_pilot_bundle(run_dir)
    assert pilot.RAW_RESEARCH_RESPONSE_FILENAME in {item["name"] for item in verified["verified_files"]}


def test_replay_copies_raw_chatgpt_response_from_hash_verified_parent(tmp_path: Path):
    input_path, response_path, signature = _write_captured_research_input(tmp_path)
    output_root = tmp_path / "private-runs"
    first = run_local_investment_pilot(
        input_path=input_path,
        output_root=output_root,
        research_response_path=response_path,
        expected_research_response_sha256=signature[2],
        expected_research_response_byte_size=signature[0],
    )
    replay = run_local_investment_pilot(
        input_path=Path(first["run_dir"]) / "input.json",
        output_root=output_root,
        replay_of=first["pilot_id"],
    )
    first_dir, replay_dir = Path(first["run_dir"]), Path(replay["run_dir"])
    first_raw = first_dir / pilot.RAW_RESEARCH_RESPONSE_FILENAME
    replay_raw = replay_dir / pilot.RAW_RESEARCH_RESPONSE_FILENAME
    replay_receipt = json.loads((replay_dir / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert replay["status"] == "PILOT_REPLAY_MATCHED"
    assert replay["replay_comparison"]["status"] == "MATCH"
    assert replay_raw.read_bytes() == first_raw.read_bytes() == response_path.read_bytes()
    assert replay_receipt["research_response_provenance"]["status"] == "INHERITED_FROM_VERIFIED_PRIOR_RUN"
    assert replay_receipt["research_response_provenance"]["origin_pilot_id"] == first["pilot_id"]
    assert replay_receipt["research_response_provenance"]["source_pilot_id"] == first["pilot_id"]
    first_analysis = json.loads((first_dir / "analysis.json").read_text(encoding="utf-8"))
    replay_analysis = json.loads((replay_dir / "analysis.json").read_text(encoding="utf-8"))
    first_report = (first_dir / "report.md").read_text(encoding="utf-8")
    replay_report = (replay_dir / "report.md").read_text(encoding="utf-8")
    assert first_analysis["research_response_provenance"] == replay_analysis["research_response_provenance"]
    assert first_report == replay_report
    assert verify_local_pilot_bundle(replay_dir)["status"] == "PILOT_BUNDLE_HASH_CHECK_PASS"


def test_guided_run_rejects_changed_response_after_validation_signature(tmp_path: Path):
    input_path, response_path, signature = _write_captured_research_input(tmp_path)
    response_path.write_text(response_path.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_RESPONSE_CHANGED_AFTER_VALIDATION"):
        run_local_investment_pilot(
            input_path=input_path,
            output_root=tmp_path / "private-runs",
            research_response_path=response_path,
            expected_research_response_sha256=signature[2],
            expected_research_response_byte_size=signature[0],
        )


def test_read_only_bundle_checker_blocks_changed_raw_chatgpt_response_bytes(tmp_path: Path):
    input_path, response_path, signature = _write_captured_research_input(tmp_path)
    result = run_local_investment_pilot(
        input_path=input_path,
        output_root=tmp_path / "private-runs",
        research_response_path=response_path,
        expected_research_response_sha256=signature[2],
        expected_research_response_byte_size=signature[0],
    )
    raw_path = Path(result["run_dir"]) / pilot.RAW_RESEARCH_RESPONSE_FILENAME
    raw_path.write_bytes(raw_path.read_bytes() + b"tampered")

    with pytest.raises(LocalInvestmentPilotError, match="RUN_BUNDLE_HASH_MISMATCH:chatgpt_response_raw.txt"):
        verify_local_pilot_bundle(Path(result["run_dir"]))


def test_replay_comparison_includes_raw_research_response_provenance():
    before = {"research_response_provenance": {"status": "RAW_CHATGPT_RESPONSE_HASH_BOUND", "sha256": "a" * 64}}
    after = {"research_response_provenance": {"status": "RAW_CHATGPT_RESPONSE_HASH_BOUND", "sha256": "b" * 64}}
    comparison = pilot._replay_comparison(before, after)
    assert comparison["status"] == "MISMATCH"
    assert "research_response_provenance" in comparison["mismatched_fields"]


def test_input_cannot_claim_raw_chatgpt_response_without_captured_file(tmp_path: Path):
    payload = _payload()
    payload["_local_research_response_provenance"] = {
        "status": "CAPTURED_RAW_CHATGPT_RESPONSE",
        "sha256": "a" * 64,
        "byte_size": 10,
    }
    with pytest.raises(LocalInvestmentPilotError, match="INPUT_CLAIMS_CHATGPT_RESPONSE_WITHOUT_VERIFIABLE_CAPTURE"):
        run_local_investment_pilot(
            input_path=_write_input(tmp_path, payload),
            output_root=tmp_path / "private-runs",
        )


@pytest.mark.parametrize("filename", ["input.json", "analysis.json", "report.md"])
def test_read_only_bundle_checker_blocks_changed_output_bytes(tmp_path, filename):
    result = run_local_investment_pilot(
        input_path=_write_input(tmp_path),
        output_root=tmp_path / "private-runs",
    )
    target = Path(result["run_dir"]) / filename
    target.write_bytes(target.read_bytes() + b"\n# changed after receipt\n")

    with pytest.raises(LocalInvestmentPilotError, match=f"RUN_BUNDLE_HASH_MISMATCH:{filename}"):
        verify_local_pilot_bundle(Path(result["run_dir"]))


def test_replay_reports_decision_material_mismatch_instead_of_claiming_success(tmp_path, monkeypatch):
    import iios_mvp.local_investment_pilot_v01 as pilot

    output_root = tmp_path / "private-runs"
    first = run_local_investment_pilot(input_path=_write_input(tmp_path), output_root=output_root)
    original_analyse = pilot._analyse

    def drifted_analyse(payload, run_id):
        analysis, _report = original_analyse(payload, run_id)
        analysis["assessment"]["quality"]["summary"] = "synthetic replay drift"
        return analysis, pilot._render_report(analysis)

    monkeypatch.setattr(pilot, "_analyse", drifted_analyse)
    replay = run_local_investment_pilot(
        input_path=Path(first["run_dir"]) / "input.json",
        output_root=output_root,
        replay_of=first["pilot_id"],
    )
    assert replay["status"] == "PILOT_REPLAY_MISMATCH"
    assert replay["replay_comparison"]["status"] == "MISMATCH"
    assert "assessment" in replay["replay_comparison"]["mismatched_fields"]
    receipt = json.loads((Path(replay["run_dir"]) / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert receipt["replay_comparison"]["status"] == "MISMATCH"


def test_replay_blocks_a_prior_bundle_without_hash_manifest(tmp_path):
    input_path = _write_input(tmp_path)
    output_root = tmp_path / "private-runs"
    first = run_local_investment_pilot(input_path=input_path, output_root=output_root)
    receipt_path = Path(first["run_dir"]) / "pilot_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.pop("file_manifest", None)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(LocalInvestmentPilotError, match="RUN_BUNDLE_HASH_MANIFEST_MISSING"):
        run_local_investment_pilot(
            input_path=Path(first["run_dir"]) / "input.json",
            output_root=output_root,
            replay_of=first["pilot_id"],
        )



def test_portfolio_context_prompt_defaults_to_fill_not_silent_skip(monkeypatch):
    import iios_mvp.local_investment_pilot_v01 as pilot

    # Pressing Enter at the first portfolio prompt must enter the collection
    # flow. These answers are operator-owned, not AI-authored portfolio fields.
    answers = iter(["", "1", "1", "1", "90", "100", "1", "4", "8"])
    monkeypatch.setattr(pilot, "_read_operator_prompt", lambda _prompt: next(answers))

    context = pilot._ask_operator_portfolio_context()

    assert context == {
        "constraint_status": "PASS",
        "can_add": True,
        "risk_budget_pct_nav": "1",
        "entry_zone_low": "90",
        "entry_zone_high": "100",
        "initial_position_pct": "1",
        "target_position_pct": "4",
        "max_position_pct": "8",
    }


def _driver_measure(value, unit, data_class="ANALYST_ASSUMPTION", refs=None, basis="explicit synthetic assumption"):
    return {
        "value": value, "unit": unit, "data_class": data_class, "basis": basis,
        "evidence_refs": list(refs or []), "note": basis,
    }


def _driver_payload():
    observed = lambda value, unit: _driver_measure(value, unit, "OBSERVED_ACTUAL", ["E1"], "Synthetic test actual with source ID")
    forecast = lambda value, unit: _driver_measure(value, unit, "ISSUER_FORECAST", ["E1"], "Synthetic test issuer forecast")
    assumption = lambda value, unit: _driver_measure(value, unit, "ANALYST_ASSUMPTION", [], "Explicit synthetic scenario assumption")
    result = {
        "schema_version": "IIOS-OPERATING-DRIVER-FORECAST-0.1", "scope": "PROJECT_INCREMENTAL",
        "status": "PARTIAL", "actuals_period": "2025FY", "forecast_period": "2026FY",
        "summary": "Synthetic test case; not real company facts.",
        "product_lines": [{
            "product_id": "product_a", "product_name": "示例产品",
            "capacity_tonnes_per_year": forecast("1000", "tonnes/year"),
            "historical_actuals": {
                "production_tonnes": observed("800", "tonnes"),
                "sales_volume_tonnes": observed("750", "tonnes"),
                "net_asp_cny_per_tonne": observed("1000", "CNY/tonne"),
                "variable_cost_cny_per_tonne": observed("400", "CNY/tonne"),
            },
        }], "scenarios": {}, "limitations": ["Synthetic data only."],
    }
    for name, production, sales in (("bear", "700", "650"), ("base", "800", "750"), ("bull", "900", "850")):
        result["scenarios"][name] = {
            "product_lines": [{
                "product_id": "product_a", "production_tonnes": assumption(production, "tonnes"),
                "sales_volume_tonnes": assumption(sales, "tonnes"),
                "net_asp_cny_per_tonne": assumption("1000", "CNY/tonne"),
                "variable_cost_cny_per_tonne": assumption("400", "CNY/tonne"),
            }],
            "fixed_cash_opex_cny": assumption("50000", "CNY"),
            "depreciation_amortization_cny": assumption("10000", "CNY"),
            "finance_cost_cny": assumption("5000", "CNY"),
            "tax_rate": assumption("0.25", "ratio"),
            "cash_capex_cny": assumption("20000", "CNY"),
            "change_working_capital_cny": assumption("3000", "CNY"),
        }
    return result


def test_operating_driver_bridge_calculates_volume_price_cost_and_cash_flow():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    source = [{"source_id": "E1", "known_at": "2026-08-30", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]
    driver = evaluate_operating_driver_forecast(_driver_payload(), evidence_register=source)
    bear = driver["scenarios"]["bear"]
    assert driver["scope"] == "PROJECT_INCREMENTAL"
    assert driver["historical_actuals_status"] == "PRODUCT_LINE_ACTUALS_TYPED_NOT_FORMALLY_ADMITTED"
    assert driver["status"] == "SCENARIOS_CALCULATED"
    assert bear["revenue_cny"] == "650000"
    assert bear["variable_cost_cny"] == "260000"
    assert bear["contribution_after_variable_cost_cny"] == "390000"
    assert bear["ebitda_cny"] == "340000"
    assert bear["ebit_cny"] == "330000"
    assert bear["profit_before_tax_cny"] == "325000"
    assert bear["net_profit_cny"] == "243750.00"
    assert bear["unlevered_fcf_proxy_cny"] == "234500.00"
    assert bear["calculation_status"] == "SCENARIO_ARITHMETIC_COMPLETE"
    assert bear["financial_outputs_decision_usable"] is True
    assert driver["valuation_transmission"]["status"] == "NOT_LINKED_TO_PER_SHARE_VALUE"
    assert driver["formal_forecast_admission_created"] is False


@pytest.mark.parametrize(
    "placeholder",
    ["UNKNOWN", "N/A", "NOT_IDENTIFIABLE", "TBD", "未提供依据"],
)
def test_operating_driver_numeric_assumption_with_placeholder_basis_is_not_calculated(placeholder):
    payload = _driver_payload()
    payload["scenarios"]["base"]["tax_rate"]["basis"] = placeholder
    source = [{"source_id": "E1", "known_at": "2026-08-30", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]

    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]

    assert base["net_profit_cny"] is None
    assert base["unlevered_fcf_proxy_cny"] is None
    assert "base.tax_rate:BASIS_NOT_IDENTIFIABLE" in base["issues"]
    assert base["calculation_status"] == "PARTIAL_SCENARIO_BRIDGE"
    assert base["financial_outputs_decision_usable"] is False


def test_b5_numeric_assumption_with_placeholder_basis_blocks_transmission_and_price():
    payload = _b5_ready_payload()
    payload["valuation_transmission"]["scenarios"]["base"]["pe_multiple_x"]["basis"] = "N/A"

    analysis, report = _analyse(payload, "TEST-B5-PLACEHOLDER-ASSUMPTION-BASIS")
    bridge = analysis["valuation_transmission"]

    assert bridge["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert "valuation_transmission.base.pe_multiple_x:BASIS_NOT_IDENTIFIABLE" in bridge["input_issues"]
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "不得将项目增量默认为已计入估值" in report


def test_b4_aggregate_cost_ratio_does_not_override_explicit_product_cost_conflict():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast

    payload = _driver_payload()
    # Sales volume * unit cost = 750 * 400 = 300,000, while the same
    # product explicitly declares total variable cost as 350,000. An
    # aggregate ratio must not silently choose a third cost amount.
    payload["scenarios"]["base"]["product_lines"][0]["variable_cost_cny"] = _driver_measure(
        "350000", "CNY", "ANALYST_ASSUMPTION", [], "Conflicting explicit total product variable cost"
    )
    payload["scenarios"]["base"]["cost_of_revenue_ratio"] = _driver_measure(
        "0.6", "ratio", "ANALYST_ASSUMPTION", [], "Explicit synthetic aggregate cost ratio"
    )
    source = [{"source_id": "E1", "known_at": "2026-08-30", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]

    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]

    assert base["revenue_cny"] == "750000"
    assert base["variable_cost_cny"] is None
    assert base["net_profit_cny"] is None
    assert base["unlevered_fcf_proxy_cny"] is None
    assert "EXPLICIT_VARIABLE_COST_CONFLICTS_WITH_VOLUME_X_UNIT_COST" in base["issues"]
    assert "AGGREGATE_COST_RATIO_FALLBACK_BLOCKED_BY_PRODUCT_COST_CONFLICT" in base["issues"]
    assert base["calculation_status"] == "PARTIAL_SCENARIO_BRIDGE"


def test_b4_aggregate_cost_ratio_can_fill_missing_product_cost_without_a_conflict():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast

    payload = _driver_payload()
    payload["scenarios"]["base"]["product_lines"][0].pop("variable_cost_cny_per_tonne")
    payload["scenarios"]["base"]["cost_of_revenue_ratio"] = _driver_measure(
        "0.6", "ratio", "ANALYST_ASSUMPTION", [], "Explicit synthetic aggregate cost ratio"
    )
    source = [{"source_id": "E1", "known_at": "2026-08-30", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]

    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]

    assert base["variable_cost_cny"] == "450000.0"
    assert base["variable_cost_basis"] == "AGGREGATE_COST_OF_REVENUE_RATIO"
    assert base["net_profit_cny"] is not None
    assert base["unlevered_fcf_proxy_cny"] is not None
    assert "AGGREGATE_COST_RATIO_FALLBACK_BLOCKED_BY_PRODUCT_COST_CONFLICT" not in base["issues"]


def test_operating_driver_forecast_refuses_unreferenced_actual_numbers():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["base"]["product_lines"][0]["net_asp_cny_per_tonne"] = _driver_measure("1000", "CNY/tonne", "OBSERVED_ACTUAL", [], "Claimed actual without source")
    result = evaluate_operating_driver_forecast(payload, evidence_register=[])
    base = result["scenarios"]["base"]
    assert base["revenue_cny"] is None
    assert any("SOURCE_REFERENCE_REQUIRED" in issue for issue in base["issues"])
    assert base["net_profit_cny"] is None


def test_operating_driver_forecast_preserves_unknown_revenue_when_asp_is_missing():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["base"]["product_lines"][0]["net_asp_cny_per_tonne"] = {
        "value": None, "unit": "CNY/tonne", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [],
        "note": "No product-specific realized net selling price."
    }
    result = evaluate_operating_driver_forecast(payload, evidence_register=[{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}])
    base = result["scenarios"]["base"]
    assert base["revenue_cny"] is None
    assert base["net_profit_cny"] is None
    assert "total_revenue" in base["missing_inputs"]
    assert base["calculation_status"] == "SCENARIO_ECONOMICS_NOT_IDENTIFIABLE"
    assert base["financial_outputs_decision_usable"] is False


def test_operating_driver_forecast_rejects_wrong_units():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["bear"]["product_lines"][0]["sales_volume_tonnes"] = _driver_measure("650", "kg", "ANALYST_ASSUMPTION", [], "Deliberate wrong unit")
    result = evaluate_operating_driver_forecast(payload, evidence_register=[{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}])
    bear = result["scenarios"]["bear"]
    assert bear["revenue_cny"] is None
    assert any("UNIT_MISMATCH" in issue for issue in bear["issues"])


def test_operating_driver_forecast_keeps_actual_asp_unknown_and_flags_capacity_mismatch():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["product_lines"][0]["historical_actuals"]["net_asp_cny_per_tonne"] = {
        "value": None, "unit": "CNY/tonne", "data_class": "UNKNOWN", "basis": "", "evidence_refs": [],
        "note": "Only aggregate revenue and production were available."
    }
    payload["scenarios"]["base"]["product_lines"][0]["production_tonnes"] = _driver_measure("1200", "tonnes", "ANALYST_ASSUMPTION", [], "Deliberate capacity overrun")
    result = evaluate_operating_driver_forecast(payload, evidence_register=[{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}])
    actual = result["product_lines"][0]["historical_actual_bridge"]
    base = result["scenarios"]["base"]
    assert actual["revenue_cny"] is None
    assert result["historical_actuals_status"] == "NOT_IDENTIFIABLE_OR_INCOMPLETE"
    assert any("ABOVE_NAMEPLATE_CAPACITY" in issue for issue in base["issues"])
    assert base["capacity_feasibility_status"] == "UNRESOLVED_OVER_NAMEPLATE_CAPACITY"
    assert base["financial_outputs_decision_usable"] is False
    assert base["net_profit_cny"] is None
    assert base["unlevered_fcf_proxy_cny"] is None
    assert base["diagnostic_net_profit_if_capacity_resolved_cny"] is not None
    assert base["diagnostic_unlevered_fcf_proxy_if_capacity_resolved_cny"] is not None


def test_operating_driver_forecast_allows_working_capital_release_but_rejects_invalid_tax_rate():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["base"]["change_working_capital_cny"] = _driver_measure("-3000", "CNY", "ANALYST_ASSUMPTION", [], "Working-capital release")
    payload["scenarios"]["base"]["tax_rate"] = _driver_measure("-0.1", "ratio", "ANALYST_ASSUMPTION", [], "Deliberately invalid tax ratio")
    result = evaluate_operating_driver_forecast(payload, evidence_register=[{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}])
    base = result["scenarios"]["base"]
    assert base["change_working_capital_cny"] == "-3000"
    assert base["unlevered_fcf_proxy_cny"] is None
    assert any("TAX_RATE_MUST_BE_RATIO_0_TO_1" in issue for issue in base["issues"])



def test_historical_actuals_do_not_use_issuer_forecast_values():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["product_lines"][0]["historical_actuals"]["net_asp_cny_per_tonne"] = _driver_measure(
        "1000", "CNY/tonne", "ISSUER_FORECAST", ["E1"], "Forecast mislabeled inside historical actuals"
    )
    source = [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]
    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    actual = result["product_lines"][0]["historical_actual_bridge"]
    assert actual["revenue_cny"] is None
    assert result["historical_actuals_status"] == "NOT_IDENTIFIABLE_OR_INCOMPLETE"
    assert any("DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT" in issue for issue in result["input_issues"])


def test_forward_scenario_does_not_silently_reuse_observed_actual_as_forecast():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["base"]["product_lines"][0]["net_asp_cny_per_tonne"] = _driver_measure(
        "1000", "CNY/tonne", "OBSERVED_ACTUAL", ["E1"], "Historical realized ASP incorrectly used as forward estimate"
    )
    source = [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]
    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]
    assert base["revenue_cny"] is None
    assert base["net_profit_cny"] is None
    assert any("DATA_CLASS_NOT_ALLOWED_FOR_CONTEXT" in issue for issue in base["issues"])


def test_duplicate_product_rows_block_scenario_totals_instead_of_selecting_one():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["scenarios"]["base"]["product_lines"].append(
        dict(payload["scenarios"]["base"]["product_lines"][0])
    )
    source = [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]
    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]
    assert base["revenue_cny"] is None
    assert base["variable_cost_cny"] is None
    assert base["net_profit_cny"] is None
    assert base["product_lines"][0]["revenue_cny"] is None
    assert any("DUPLICATE_PRODUCT_ID" in issue for issue in base["issues"])


def test_capacity_utilization_is_unknown_for_partial_year_forecast_period():
    from iios_mvp.operating_driver_forecast_v01 import evaluate_operating_driver_forecast
    payload = _driver_payload()
    payload["forecast_period"] = "2026Q4"
    source = [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}]
    result = evaluate_operating_driver_forecast(payload, evidence_register=source)
    base = result["scenarios"]["base"]
    assert base["product_lines"][0]["production_utilization"] is None
    assert any("CAPACITY_PERIOD_ALIGNMENT_UNKNOWN" in issue for issue in base["issues"])



def _b5_measure(value, unit, data_class="ANALYST_ASSUMPTION", refs=None, basis="Explicit synthetic B5 test assumption"):
    return {
        "value": value, "unit": unit, "data_class": data_class,
        "basis": basis, "evidence_refs": list(refs or []), "note": basis,
    }


def _b5_ready_payload():
    payload = _payload(cutoff="2026-10-10")
    payload["operating_driver_forecast"] = _driver_payload()
    payload["forecast_valuation"]["model"] = "Synthetic EPS x PE"
    payload["forecast_valuation"]["entry_value_reference_per_share"] = "150"
    payload["forecast_valuation"]["scenarios"] = {
        "bear": {
            "probability": "0.20", "terminal_value_per_share": "120", "cash_distributions_per_share": "0",
            "rationale": "synthetic bear", "failure_trigger": "project economics miss",
            "operating_impact": "incremental profits shrink", "valuation_mechanism": "lower EPS x PE",
        },
        "base": {"probability": "0.50", "terminal_value_per_share": "150", "cash_distributions_per_share": "0", "rationale": "synthetic base"},
        "bull": {"probability": "0.30", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "rationale": "synthetic bull"},
    }
    rows = {}
    for name in ("bear", "base", "bull"):
        rows[name] = {
            "ownership_ratio": _b5_measure("0.8", "ratio"),
            "displaced_existing_after_tax_profit_cny": _b5_measure("10000", "CNY"),
            "basic_shares": _b5_measure("1000000", "shares", "OBSERVED_ACTUAL", ["E1"], "Synthetic source-backed basic shares"),
            "convertible_bond_incremental_shares": _b5_measure("100000", "shares"),
            "other_dilution_shares": _b5_measure("10000", "shares"),
            "pe_multiple_x": _b5_measure("10", "x"),
        }
    payload["valuation_transmission"] = {
        "schema_version": "IIOS-VALUATION-TRANSMISSION-0.1",
        "model_family": "EPS_MULTIPLE",
        "valuation_model_name": "Synthetic EPS x PE",
        "earnings_period": "2026FY",
        "summary": "Synthetic test bridge; no real company fact.",
        "scenarios": rows,
    }
    payload["operator_valuation_context"] = {
        "selected_model_family": "EPS_MULTIPLE",
        "baseline_includes_project": False,
        "input_owner": "OPERATOR",
    }
    _sync_eps_multiple_values(payload, {"bear": "120", "base": "150", "bull": "180"})
    return payload


@pytest.mark.parametrize("scenario_name", ["bear", "base", "bull"])
def test_b5_does_not_apply_project_transmission_when_cash_distribution_is_omitted(scenario_name):
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"][scenario_name].pop("cash_distributions_per_share")

    analysis, report = _analyse(payload, f"TEST-B5-MISSING-DISTRIBUTIONS-{scenario_name}")

    bridge = analysis["valuation_transmission"]
    assert bridge["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert f"{scenario_name.upper()}:CASH_DISTRIBUTIONS_UNKNOWN" in bridge["input_issues"]
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "CASH_DISTRIBUTIONS_UNKNOWN" in report
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


def test_b5_transmits_project_profit_to_per_share_scenarios_and_entry_anchor():
    payload = _b5_ready_payload()
    analysis, report = _analyse(payload, "TEST-B5-APPLY")
    bridge = analysis["valuation_transmission"]

    assert bridge["status"] == "APPLIED_TO_PER_SHARE_SCENARIOS"
    assert bridge["applied_to_per_share_scenarios"] is True
    assert Decimal(bridge["scenarios"]["bear"]["incremental_attributable_profit_cny"]) == Decimal("185000")
    assert Decimal(bridge["scenarios"]["bear"]["value_delta_per_share_basic"]) > Decimal(
        bridge["scenarios"]["bear"]["value_delta_per_share_diluted"]
    )
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["b5_baseline_terminal_value_per_share"] == "120"
    assert Decimal(analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"]) > Decimal("120")
    assert Decimal(analysis["forecast_valuation"]["entry_value_reference_per_share"]) > Decimal("150")
    assert analysis["return_metrics"] is not None
    assert "B5：经营结果到每股估值的传导" in report
    assert "B5 当前传导状态：APPLIED_TO_PER_SHARE_SCENARIOS" in report
    assert "B5 传导后的每股估值情景终值" in report
    assert "价值传导仍需后续估值层完成" not in report
    assert "尚未与此经营桥接连通" not in report
    assert "B5 已按明确的 EPS_MULTIPLE 增量桥接" in report
    assert "论点失效压力测试不自动加回项目价值" in report



@pytest.mark.parametrize("rationale", ["UNKNOWN", "N/A", "TBD", "未提供依据"])
def test_primary_model_placeholder_rationale_blocks_return_entry_price_and_b6(rationale):
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["model_rationale"] = rationale

    analysis, report = _analyse(payload, f"TEST-PRIMARY-MODEL-RATIONALE-{rationale}")

    contract = analysis["valuation_model_consistency"]
    assert contract["status"] == "MODEL_RATIONALE_NOT_IDENTIFIABLE"
    assert contract["model_rationale_identifiable"] is False
    assert "FORECAST_VALUATION_MODEL_RATIONALE_NOT_IDENTIFIABLE" in contract["issues"]
    assert contract["primary_model_price_calculation_eligible"] is False
    assert contract["scenario_values_role"] == "ALTERNATIVE_OR_UNRESOLVED_ONLY"
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "PRIMARY_VALUATION_MODEL_NOT_ELIGIBLE:MODEL_RATIONALE_NOT_IDENTIFIABLE"
    assert analysis["price_zone_sensitivity"]["status"] == "UNKNOWN"
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "FORECAST_VALUATION_MODEL_RATIONALE_NOT_IDENTIFIABLE" in report
    assert "不进入预期回报、目标入场价或 B6 价格敏感性计算" in report


def test_primary_model_identifiable_rationale_keeps_price_screen_eligible():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["model_rationale"] = (
        "EPS_MULTIPLE 适用于以可持续归母净利润为主驱动的成熟业务，"
        "估值使用正常化 EPS 与可比估值区间交叉检查。"
    )
    analysis, _report = _analyse(payload, "TEST-PRIMARY-MODEL-RATIONALE-IDENTIFIABLE")

    contract = analysis["valuation_model_consistency"]
    assert contract["status"] == "MATCH"
    assert contract["model_rationale_identifiable"] is True
    assert contract["primary_model_price_calculation_eligible"] is True
    assert analysis["return_metrics"] is not None


def test_operator_selected_sotp_blocks_eps_multiple_price_calculation():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["selected_model_family"] = "SOTP"
    analysis, report = _analyse(payload, "TEST-PRIMARY-MODEL-MISMATCH")

    contract = analysis["valuation_model_consistency"]
    assert contract["status"] == "SOTP_CALCULATION_NOT_ELIGIBLE"
    assert "OPERATOR_MODEL_FAMILY_DIFFERS_FROM_CALCULATION_MODEL_FAMILY" in contract["issues"]
    assert "SOTP_ADAPTER_NOT_CALCULATED" in contract["issues"]
    assert contract["operator_selected_model_family"] == "SOTP"
    assert contract["calculation_model_family"] == "EPS_MULTIPLE"
    assert contract["primary_model_price_calculation_eligible"] is False
    assert contract["scenario_values_role"] == "ALTERNATIVE_OR_UNRESOLVED_ONLY"
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "PRIMARY_VALUATION_MODEL_NOT_ELIGIBLE:SOTP_CALCULATION_NOT_ELIGIBLE"
    assert analysis["price_zone_sensitivity"]["status"] == "UNKNOWN"
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "操作者选择的主模型类别：SOTP" in report
    assert "当前情景实际计算模型类别：EPS_MULTIPLE" in report
    assert "不进入预期回报、目标入场价或 B6 价格敏感性计算" in report

    # Red-team against a response that self-labels EPS x P/E values as SOTP.
    forged = _b5_ready_payload()
    forged["operator_valuation_context"]["selected_model_family"] = "SOTP"
    forged["forecast_valuation"]["model_family"] = "SOTP"
    forged["forecast_valuation"]["model"] = "Synthetic EPS x PE"
    forged_analysis, _ = _analyse(forged, "TEST-FORGED-MODEL-FAMILY")
    forged_contract = forged_analysis["valuation_model_consistency"]
    assert forged_contract["status"] == "SOTP_CALCULATION_NOT_ELIGIBLE"
    assert "FORECAST_VALUATION_MODEL_NAME_CONFLICTS_WITH_DECLARED_CALCULATION_FAMILY" in forged_contract["issues"]
    assert forged_contract["model_name_inferred_family"] == "EPS_MULTIPLE"
    assert forged_analysis["return_metrics"] is None
    assert forged_analysis["price_zone_sensitivity"]["target_entry_price"] is None



def test_unknown_or_product_line_scope_with_unlinked_b5_blocks_price_outputs():
    for scope in ("UNKNOWN", "PRODUCT_LINE", "PROJECT_INCREMENTAL"):
        payload = _payload()
        payload["operating_driver_forecast"]["scope"] = scope
        payload["valuation_transmission"]["model_family"] = "UNKNOWN"
        analysis, report = _analyse(payload, f"TEST-UNRESOLVED-SCOPE-{scope}")

        contract = analysis["valuation_model_consistency"]
        assert contract["status"] == "OPERATING_SCOPE_OR_B5_TRANSMISSION_NOT_RESOLVED"
        assert contract["primary_model_price_calculation_eligible"] is False
        assert analysis["return_metrics"] is None
        assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
        assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
        assert "B5 传导状态" in report

def test_explicit_rolling_ntm_dates_align_with_one_year_terminal_timing():
    timing = pilot._build_valuation_timing(
        cutoff_date="2026-10-16",
        forecast_period="NTM_2026-10-17_TO_2027-10-16",
        valuation_terminal_date="2027-10-16",
        valuation_terminal_date_basis="Explicit rolling twelve-month period from the day after the cutoff through 2027-10-16.",
    )
    assert timing["status"] == "PASS"
    assert timing["period_alignment_status"] == "ROLLING_12_MONTHS_EXPLICIT_DATES_ALIGNED_NOT_INDEPENDENTLY_VERIFIED"
    assert timing["elapsed_calendar_days"] == 365
    assert Decimal(timing["annualization_year_fraction"]) == Decimal("1")

    mismatched = pilot._build_valuation_timing(
        cutoff_date="2026-10-16",
        forecast_period="NTM_2026-10-18_TO_2027-10-16",
        valuation_terminal_date="2027-10-16",
        valuation_terminal_date_basis="Explicit but intentionally mismatched rolling forecast dates.",
    )
    assert mismatched["status"] == "FORECAST_NTM_PERIOD_START_MISMATCH"
    assert mismatched["period_alignment_status"] == "MISMATCH_OR_INVALID"


def test_blocked_primary_model_is_labeled_candidate_in_report():
    payload = _payload()
    payload["operator_valuation_context"]["selected_model_family"] = "SOTP"
    analysis, report = _analyse(payload, "TEST-BLOCKED-PRIMARY-MODEL-REPORT")

    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False
    assert "候选模型（未获主模型门禁批准）：" in report
    assert "研究回答中的候选模型理由（未经主模型门禁认可）" in report
    assert "候选模型参考锚（主模型门禁未通过，仅供诊断）" in report


def test_calendar_day_terminal_date_controls_annualization_and_return_cap():
    payload = _payload(price="144.30", cutoff="2026-10-16")
    analysis, report = _analyse(payload, "TEST-DATE-ANNUALIZATION")
    timing = analysis["valuation_timing"]
    metrics = analysis["return_metrics"]

    assert timing["status"] == "PASS"
    assert timing["valuation_terminal_date"] == "2027-12-31"
    assert timing["elapsed_calendar_days"] == 441
    assert Decimal(timing["annualization_year_fraction"]) == Decimal("441") / Decimal("365")
    assert Decimal(metrics["annualization_year_fraction"]) == Decimal("441") / Decimal("365")
    ratio = Decimal(metrics["expected_terminal_wealth"]) / Decimal("144.30")
    expected_annualized = (ratio.ln() / (Decimal("441") / Decimal("365"))).exp() - Decimal("1")
    assert abs(Decimal(metrics["expected_annualized_return"]) - expected_annualized) < Decimal("1e-24")
    expected_cap = Decimal(metrics["expected_terminal_wealth"]) / (
        Decimal("1.15").ln() * (Decimal("441") / Decimal("365"))
    ).exp()
    assert abs(Decimal(metrics["target_entry_price_for_return"]) - expected_cap) < Decimal("1e-24")
    assert "441" in report
    assert "ACT/365F_DATE_ONLY" in report


def test_missing_or_period_mismatched_terminal_date_blocks_return_metrics():
    payload = _payload()
    payload["forecast_valuation"]["valuation_terminal_date"] = None
    missing, _ = _analyse(payload, "TEST-MISSING-TERMINAL-DATE")
    assert missing["valuation_timing"]["status"] == "VALUATION_TERMINAL_DATE_MISSING"
    assert missing["return_metrics"] is None
    assert missing["price_zone_sensitivity"]["status"] == "UNKNOWN"

    basis_payload = _payload()
    basis_payload["forecast_valuation"]["valuation_terminal_date_basis"] = ""
    basis_missing, _ = _analyse(basis_payload, "TEST-MISSING-TERMINAL-DATE-BASIS")
    assert basis_missing["valuation_timing"]["status"] == "VALUATION_TERMINAL_DATE_BASIS_MISSING"
    assert basis_missing["return_metrics"] is None
    assert basis_missing["price_zone_sensitivity"]["target_entry_price"] is None

    # Non-empty sentinel values are not valid terminal-date bases. They must
    # fail closed just like a missing basis, before annualized-return/B6 output.
    for marker in ("UNKNOWN", "N/A", "NOT_IDENTIFIABLE", "TBD", "—"):
        unknown_payload = _payload()
        unknown_payload["forecast_valuation"]["valuation_terminal_date_basis"] = marker
        unknown_basis, _ = _analyse(unknown_payload, f"TEST-UNKNOWN-TERMINAL-BASIS-{marker}")
        assert unknown_basis["valuation_timing"]["status"] == "VALUATION_TERMINAL_DATE_BASIS_NOT_IDENTIFIABLE"
        assert unknown_basis["return_metrics"] is None
        assert unknown_basis["price_zone_sensitivity"]["target_entry_price"] is None
        assert unknown_basis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
        assert "VALUATION_TIMING_NOT_RESOLVED" in unknown_basis["decision"]["gating_issues"]

    mismatch_payload = _payload()
    mismatch_payload["forecast_valuation"]["valuation_terminal_date"] = "2029-12-31"
    mismatch, _ = _analyse(mismatch_payload, "TEST-PERIOD-MISMATCH")
    assert mismatch["valuation_timing"]["status"] == "VALUATION_TERMINAL_DATE_FORECAST_PERIOD_MISMATCH"
    assert mismatch["return_metrics"] is None
    assert mismatch["price_zone_sensitivity"]["target_entry_price"] is None

def test_b5_rejects_negative_adjusted_terminal_value_and_preserves_original_scenarios():
    payload = _b5_ready_payload()
    # Keep Base/Bull changes modest, but make Bear's displaced-profit assumption
    # so large that the incremental EPS-multiple bridge would imply negative equity value.
    payload["valuation_transmission"]["scenarios"]["bear"]["displaced_existing_after_tax_profit_cny"] = _b5_measure(
        "100000000", "CNY"
    )

    analysis, report = _analyse(payload, "TEST-B5-NEGATIVE-ADJUSTED-TERMINAL")
    bridge = analysis["valuation_transmission"]

    assert bridge["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert "BEAR:ADJUSTED_TERMINAL_VALUE_NEGATIVE" in bridge["input_issues"]
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert analysis["return_metrics"] is None
    assert "B5 当前传导状态：NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID" in report
    assert "不得将项目增量默认为已计入估值" in report


def test_b5_negative_counterfactual_does_not_block_confirmed_project_inclusive_baseline():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = True
    # The hypothetical "add the project again" scenario is negative, but this
    # counterfactual is not applied because the operator says the baseline already
    # includes the project. The unchanged primary valuation should remain usable.
    payload["valuation_transmission"]["scenarios"]["bear"]["displaced_existing_after_tax_profit_cny"] = _b5_measure(
        "100000000", "CNY"
    )

    analysis, report = _analyse(payload, "TEST-B5-NEGATIVE-COUNTERFACTUAL-INCLUDED-BASELINE")
    bridge = analysis["valuation_transmission"]

    assert bridge["status"] == "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert Decimal(bridge["scenarios"]["bear"]["hypothetical_terminal_value_if_added_per_share"]) < 0
    assert bridge["scenarios"]["bear"]["adjusted_terminal_value_per_share"] is None
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["return_metrics"] is not None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is not None
    assert "B5 因防止重复计价而没有二次叠加" in report
    assert "回报计算尚未完成" not in report


def test_b5_unapplied_counterfactual_ordering_does_not_block_included_baseline():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = True
    # The baseline itself remains Bear < Base < Bull. A deliberately large
    # hypothetical Base displaced-profit value makes the "add the project
    # again" counterfactual reorder scenarios; it must not be used as a gate
    # for the confirmed project-inclusive baseline.
    payload["valuation_transmission"]["scenarios"]["base"]["displaced_existing_after_tax_profit_cny"] = _b5_measure(
        "10000000", "CNY"
    )

    analysis, report = _analyse(payload, "TEST-B5-COUNTERFACTUAL-ORDERING-INCLUDED-BASELINE")
    bridge = analysis["valuation_transmission"]

    assert bridge["status"] == "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert "COUNTERFACTUAL_ADJUSTED_SCENARIO_WEALTH_ORDERING_INCONSISTENT" in bridge["counterfactual_issues"]
    assert bridge["scenarios"]["base"]["adjusted_terminal_value_per_share"] is None
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["return_metrics"] is not None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is not None
    assert "非阻断性反事实诊断（未参与价格计算）" in report
    assert "未用于回报、目标入场价或 B6 计算" in report
    assert "回报计算尚未完成" not in report


def test_b5_never_adds_project_twice_when_operator_says_baseline_includes_it():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = True
    analysis, report = _analyse(payload, "TEST-B5-ALREADY-INCLUDED")
    assert "B5 当前传导状态：CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT" in report
    assert "基准已含项目、未重复叠加的每股估值情景终值" in report
    assert "B5 因防止重复计价而没有二次叠加" in report
    assert "价值传导仍需后续估值层完成" not in report
    assert analysis["valuation_transmission"]["status"] == "CALCULATED_NOT_APPLIED_BASELINE_ALREADY_INCLUDES_PROJECT"
    assert analysis["valuation_transmission"]["applied_to_per_share_scenarios"] is False
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"


def test_b5_keeps_original_valuation_when_project_baseline_scope_is_unknown():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = None
    analysis, _ = _analyse(payload, "TEST-B5-BASELINE-UNKNOWN")
    assert analysis["valuation_transmission"]["status"] == "CALCULATED_NOT_APPLIED_BASELINE_SCOPE_UNKNOWN"
    assert analysis["valuation_transmission"]["applied_to_per_share_scenarios"] is False
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"


def test_b5_missing_cannibalization_blocks_all_scenario_value_changes():
    payload = _b5_ready_payload()
    payload["valuation_transmission"]["scenarios"]["base"]["displaced_existing_after_tax_profit_cny"] = {
        "value": None, "unit": "CNY", "data_class": "UNKNOWN", "basis": "",
        "evidence_refs": [], "note": "Cannibalization not identified",
    }
    analysis, report = _analyse(payload, "TEST-B5-CANNIBALIZATION-UNKNOWN")
    assert "B5 当前传导状态：NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID" in report
    assert "当前 B5 状态为 NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID" in report
    assert "价值传导仍需后续估值层完成" not in report
    assert analysis["valuation_transmission"]["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_transmission"]["applied_to_per_share_scenarios"] is False
    assert all(
        analysis["forecast_valuation"]["scenarios"][name]["terminal_value_per_share"] == base
        for name, base in (("bear", "120"), ("base", "150"), ("bull", "180"))
    )


def test_b5_refuses_cross_period_profit_to_valuation_mapping():
    payload = _b5_ready_payload()
    payload["valuation_transmission"]["earnings_period"] = "2027FY"
    analysis, _ = _analyse(payload, "TEST-B5-PERIOD-MISMATCH")
    assert analysis["valuation_transmission"]["status"] == "NOT_LINKED_PERIOD_MISMATCH"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"


def test_b5_does_not_apply_eps_multiple_formula_to_sotp_or_dcf():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["selected_model_family"] = "SOTP"
    analysis, _ = _analyse(payload, "TEST-B5-UNSUPPORTED-MODEL")
    assert analysis["valuation_transmission"]["status"] == "NOT_LINKED_UNSUPPORTED_MODEL_FAMILY"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"


def test_b5_dilution_uses_basic_plus_convertible_and_other_shares():
    payload = _b5_ready_payload()
    analysis, _ = _analyse(payload, "TEST-B5-DILUTION")
    bear = analysis["valuation_transmission"]["scenarios"]["bear"]
    assert bear["diluted_shares"] == "1110000"
    assert Decimal(bear["diluted_eps_delta"]) == Decimal("185000") / Decimal("1110000")
    assert Decimal(bear["value_delta_per_share_diluted"]) < Decimal(bear["value_delta_per_share_basic"])


def test_b5_does_not_apply_when_explicit_cash_distributions_are_unknown():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"]["base"]["cash_distributions_per_share"] = None

    analysis, report = _analyse(payload, "TEST-B5-UNKNOWN-DISTRIBUTIONS")
    bridge = analysis["valuation_transmission"]

    assert analysis["return_metrics"] is None
    assert bridge["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert bridge["applied_to_per_share_scenarios"] is False
    assert "BASE:CASH_DISTRIBUTIONS_UNKNOWN" in bridge["input_issues"]
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert "- 每股现金分配合计：UNKNOWN CNY" in report
    assert "每股现金分配：None CNY" not in report


def test_null_valuation_fields_render_as_unknown_in_json_report_sections():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"]["bear"]["probability"] = None
    payload["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] = None
    payload["eps_multiple_valuation"]["scenarios"]["bear"]["eps_per_share"]["value"] = None

    analysis, report = _analyse(payload, "TEST-NULL-VALUATION-RENDER")
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["probability"] is None
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] is None
    assert "- 情景概率：UNKNOWN" in report
    assert "- 期末每股价值：UNKNOWN CNY" in report
    assert "- 未应用 B5 增量的每股估值情景终值：UNKNOWN CNY" in report
    assert "情景概率：None" not in report
    assert "None CNY" not in report


def test_b6_names_binding_entry_price_constraint_from_existing_caps():
    payload = _b5_ready_payload()
    analysis, _ = _analyse(payload, "TEST-B6-BINDING-CAP")
    zone = analysis["price_zone_sensitivity"]
    metrics = analysis["return_metrics"]
    assert zone["status"] == "CALCULATED"
    caps = [Decimal(row["price_cap"]) for row in zone["price_caps"] if row["price_cap"] is not None]
    assert Decimal(zone["target_entry_price"]) == min(caps)
    assert Decimal(zone["binding_constraint"]["price_cap"]) == min(caps)
    assert zone["binding_constraint"]["tied_constraints"]
    assert zone["price_screen_only"] is True
    assert zone["decision_action_changed"] is False
    assert Decimal(zone["target_entry_price"]) == Decimal(metrics["target_entry_price"])


def test_b6_sensitivity_ladder_reuses_solver_and_matches_current_price_metrics():
    payload = _b5_ready_payload()
    analysis, report = _analyse(payload, "TEST-B6-SENSITIVITY")
    zone = analysis["price_zone_sensitivity"]
    ladder = zone["sensitivity_ladder"]
    assert [row["multiplier"] for row in ladder] == ["0.90", "1.00", "1.10"]
    assert [Decimal(row["price"]) for row in ladder] == [Decimal("90.00"), Decimal("100"), Decimal("110.0")]
    assert all(row["status"] == "CALCULATED" for row in ladder)
    assert Decimal(ladder[0]["expected_annualized_return"]) > Decimal(ladder[1]["expected_annualized_return"])
    assert Decimal(ladder[1]["expected_annualized_return"]) > Decimal(ladder[2]["expected_annualized_return"])
    assert Decimal(ladder[0]["entry_return_cushion"]) > Decimal(ladder[1]["entry_return_cushion"])
    assert Decimal(ladder[1]["entry_return_cushion"]) > Decimal(ladder[2]["entry_return_cushion"])
    assert Decimal(ladder[1]["expected_annualized_return"]) == Decimal(analysis["return_metrics"]["expected_annualized_return"])
    assert Decimal(ladder[1]["bear_return"]) == Decimal(analysis["return_metrics"]["bear_return"])
    metrics = analysis["return_metrics"]
    assert zone["target_entry_price"] == metrics["target_entry_price"]
    assert f"- 共同约束下目标入场价上限：{metrics['target_entry_price']} CNY" in report
    assert f"- 共同约束下目标入场价上限：{zone['target_entry_price']} CNY" in report
    for row in ladder:
        for key in (
            "target_entry_price_for_entry_cushion",
            "target_entry_price_for_return",
            "target_entry_price_for_required_return",
            "target_entry_price_for_risk",
        ):
            assert row[key] == metrics[key]
    assert "B6：当前价格区间与约束敏感性" in report
    # The calculator's success status is CALCULATED, not PASS. Successful
    # rows must be rendered with their computed prices instead of UNKNOWN.
    assert "- 90% 当前价 = 90.00 CNY" in report
    assert "- 100% 当前价 = 100.00 CNY" in report
    assert "- 110% 当前价 = 110.00 CNY" in report
    assert "- 90% 当前价 = 90.00：UNKNOWN" not in report
    assert "- 100% 当前价 = 100.00：UNKNOWN" not in report
    assert "- 110% 当前价 = 110.00：UNKNOWN" not in report
    assert "不是买入指令" in report


@pytest.mark.parametrize(
    "placeholder",
    ["UNKNOWN", "N/A", "NOT_IDENTIFIABLE", "TBD", "未提供依据", "概率未知"],
)
def test_scenario_probability_with_placeholder_rationale_blocks_return_and_entry_price(placeholder):
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"]["base"]["rationale"] = placeholder

    analysis, report = _analyse(payload, f"TEST-SCENARIO-PLACEHOLDER-PROBABILITY-RATIONALE-{placeholder}")

    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "BASE_SCENARIO_PROBABILITY_RATIONALE_NOT_IDENTIFIABLE"
    assert analysis["price_zone_sensitivity"]["status"] == "UNKNOWN"
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert all(row["status"] == "UNKNOWN" for row in analysis["price_zone_sensitivity"]["sensitivity_ladder"])
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "B6：当前价格区间与约束敏感性" in report
    assert "UNKNOWN" in report


def test_b6_preserves_unknown_when_return_inputs_are_incomplete():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["entry_value_reference_per_share"] = None
    payload["eps_multiple_valuation"]["scenarios"]["base"]["eps_per_share"]["value"] = None
    analysis, report = _analyse(payload, "TEST-B6-UNKNOWN")
    zone = analysis["price_zone_sensitivity"]
    assert analysis["return_metrics"] is None
    assert zone["status"] == "UNKNOWN"
    assert zone["target_entry_price"] is None
    assert zone["current_price_zone"] == "UNKNOWN"
    assert all(row["status"] == "UNKNOWN" for row in zone["sensitivity_ladder"])
    assert "UNKNOWN" in report


def test_b6_uses_b5_adjusted_entry_value_reference_not_the_old_anchor():
    payload = _b5_ready_payload()
    analysis, _ = _analyse(payload, "TEST-B6-B5-ADJUSTED-ANCHOR")
    bridge = analysis["valuation_transmission"]
    zone = analysis["price_zone_sensitivity"]
    assert bridge["status"] == "APPLIED_TO_PER_SHARE_SCENARIOS"
    assert Decimal(analysis["forecast_valuation"]["entry_value_reference_per_share"]) > Decimal("150")
    assert Decimal(zone["entry_value_reference_per_share"]) == Decimal(
        analysis["forecast_valuation"]["entry_value_reference_per_share"]
    )
    assert Decimal(zone["price_caps"][0]["price_cap"]) == Decimal(
        analysis["return_metrics"]["target_entry_price_for_entry_cushion"]
    )


def test_b6_price_screen_never_promotes_overall_decision():
    payload = _b5_ready_payload()
    payload["price_input"]["price"] = "10"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"
    payload["price_input"]["observation_date"] = "2026-10-09"
    before, _ = _analyse(payload, "TEST-B6-PRICE-ONLY")
    zone = before["price_zone_sensitivity"]
    assert zone["price_screen_only"] is True
    assert zone["decision_action_changed"] is False
    assert any(row["return_gate_pass"] is True for row in zone["sensitivity_ladder"])
    assert before["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert before["decision"]["provisional_action"] not in {"BUY", "ADD", "HOLD"}






def test_b6_invalid_return_scenario_input_keeps_price_interpretation_unknown():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"]["base"]["probability"] = "not-a-number"
    analysis, _ = _analyse(payload, "TEST-B6-INVALID")
    zone = analysis["price_zone_sensitivity"]
    assert analysis["return_metrics"] is None
    assert zone["status"] == "UNKNOWN"
    assert zone["target_entry_price"] is None
    assert all(row["status"] == "UNKNOWN" for row in zone["sensitivity_ladder"])

# B4 operating-driver bridge regression tests end here.

# Operator-attested non-canonical portfolio-package tests. These test sizing math
# and fail-closed gates only; they are not evidence of investment validity.
from iios_mvp.local_pilot_portfolio_package_v01 import build_local_pilot_portfolio_package


def _portfolio_package_args(**overrides):
    args = {
        "operator_context": {
            "constraint_status": "PASS",
            "can_add": True,
            "risk_budget_pct_nav": "1",
            "entry_zone_low": "90",
            "entry_zone_high": "100",
            "initial_position_pct": "1",
            "target_position_pct": "4",
            "max_position_pct": "8",
        },
        "case": {"case_id": "RC-CN-A-TEST", "as_of_date": "2026-10-10", "current_position_pct": "0"},
        "price_input": {"price": "95"},
        "decision_parameters": {"max_loss_pct": "25"},
        "assessment": {
            "risk": {"status": "PASS", "evidence_refs": ["E1"], "items": []},
            "thesis": {"break_conditions": ["key margin fails"], "reassessment_triggers": ["next quarterly report"]},
        },
        "forecast_valuation": {
            "thesis_break_stress": {
                "terminal_value_per_share": "50", "cash_distributions_per_share": "0"
            }
        },
        "return_metrics": {"return_gate_pass": True},
        "stress_review": {"status": "PASS", "stress_terminal_wealth": "50", "issues": []},
        "evidence_register": [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}],
        "unresolved_evidence_ids": [],
        "after_cutoff_evidence_ids": [],
        "uncertain_timing_evidence_ids": [],
    }
    args.update(overrides)
    return args


def test_portfolio_package_uses_thesis_break_stress_to_cap_position():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args())
    assert result["risk_portfolio_contract_status"] == "STRUCTURAL_VALIDATION_PASS_NOT_ADMITTED"
    assert result["stress_loss_at_entry_zone_high_pct"] == "50.0"
    assert result["risk_budget_max_position_pct"] == "2"
    assert result["effective_max_position_pct"] == "2"
    assert result["conditional_initial_position_pct"] == "1"
    assert result["conditional_target_position_pct"] == "2"
    assert result["conditional_proposed_position_pct"] == "2"
    assert result["status"] == "CONDITIONAL_PACKAGE_READY_NOT_AUTHORIZED"
    assert result["authorized_new_position_pct"] == "0"
    assert result["formal_decision_created"] is False
    assert result["execution_authorized"] is False


def test_portfolio_package_is_unknown_when_operator_skips():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args(operator_context=None))
    assert result["status"] == "NOT_PROVIDED"
    assert result["constraint_status"] == "UNKNOWN"
    assert result["effective_max_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_blocks_when_price_is_outside_entry_zone():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args(price_input={"price": "101"}))
    assert result["current_price_zone_status"] == "ABOVE_ENTRY_ZONE"
    assert result["conditional_proposed_position_pct"] is None
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_does_not_auto_reduce_an_existing_over_limit_position():
    args = _portfolio_package_args(
        case={"case_id": "RC-CN-A-TEST", "as_of_date": "2026-10-10", "current_position_pct": "3"}
    )
    result = build_local_pilot_portfolio_package(**args)
    assert result["effective_max_position_pct"] == "2"
    assert result["current_position_over_effective_max"] is True
    assert result["conditional_proposed_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"
    assert result["execution_authorized"] is False


def test_portfolio_package_blocks_risk_references_with_uncertain_timing():
    result = build_local_pilot_portfolio_package(
        **_portfolio_package_args(uncertain_timing_evidence_ids=["E1"])
    )
    assert result["risk_portfolio_contract_status"] == "BLOCKED"
    assert result["conditional_proposed_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_rejects_misordered_position_bands():
    result = build_local_pilot_portfolio_package(
        **_portfolio_package_args(operator_context={
            "constraint_status": "PASS", "can_add": True, "risk_budget_pct_nav": "1",
            "entry_zone_low": "90", "entry_zone_high": "100",
            "initial_position_pct": "5", "target_position_pct": "4", "max_position_pct": "8",
        })
    )
    assert result["status"] == "BLOCKED_INVALID_OPERATOR_CONTEXT"
    assert "POSITION_BOUNDS" in result["reason"]
    assert result["authorized_new_position_pct"] == "0"


def test_local_pilot_report_exposes_missing_portfolio_package_as_unknown():
    from iios_mvp.local_investment_pilot_v01 import _analyse

    analysis, report = _analyse(_payload(), "local-pilot-test-package")
    assert analysis["portfolio_package"]["status"] == "NOT_PROVIDED"
    assert analysis["decision"]["core_policy_evaluation"]["portfolio_status"] == "UNKNOWN"
    assert analysis["decision"]["execution_authorized"] is False
    assert "组合风险预算与条件仓位包" in report
    assert "实际获准新增仓位：0%" in report



# Operator-attested non-canonical portfolio-package tests. These test sizing math
# and fail-closed gates only; they are not evidence of investment validity.
from iios_mvp.local_pilot_portfolio_package_v01 import build_local_pilot_portfolio_package


def _portfolio_package_args(**overrides):
    args = {
        "operator_context": {
            "constraint_status": "PASS",
            "can_add": True,
            "risk_budget_pct_nav": "1",
            "entry_zone_low": "90",
            "entry_zone_high": "100",
            "initial_position_pct": "1",
            "target_position_pct": "4",
            "max_position_pct": "8",
        },
        "case": {"case_id": "RC-CN-A-TEST", "as_of_date": "2026-10-10", "current_position_pct": "0"},
        "price_input": {"price": "95"},
        "decision_parameters": {"max_loss_pct": "25"},
        "assessment": {
            "risk": {"status": "PASS", "evidence_refs": ["E1"], "items": []},
            "thesis": {"break_conditions": ["key margin fails"], "reassessment_triggers": ["next quarterly report"]},
        },
        "forecast_valuation": {
            "thesis_break_stress": {
                "terminal_value_per_share": "50", "cash_distributions_per_share": "0"
            }
        },
        "return_metrics": {"return_gate_pass": True},
        "stress_review": {"status": "PASS", "stress_terminal_wealth": "50", "issues": []},
        "evidence_register": [{"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"}],
        "unresolved_evidence_ids": [],
        "after_cutoff_evidence_ids": [],
        "uncertain_timing_evidence_ids": [],
    }
    args.update(overrides)
    return args


def test_portfolio_package_uses_thesis_break_stress_to_cap_position():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args())
    assert result["risk_portfolio_contract_status"] == "STRUCTURAL_VALIDATION_PASS_NOT_ADMITTED"
    assert result["stress_loss_at_entry_zone_high_pct"] == "50.0"
    assert result["risk_budget_max_position_pct"] == "2"
    assert result["effective_max_position_pct"] == "2"
    assert result["conditional_initial_position_pct"] == "1"
    assert result["conditional_target_position_pct"] == "2"
    assert result["conditional_proposed_position_pct"] == "2"
    assert result["status"] == "CONDITIONAL_PACKAGE_READY_NOT_AUTHORIZED"
    assert result["authorized_new_position_pct"] == "0"
    assert result["formal_decision_created"] is False
    assert result["execution_authorized"] is False


def test_portfolio_package_is_unknown_when_operator_skips():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args(operator_context=None))
    assert result["status"] == "NOT_PROVIDED"
    assert result["constraint_status"] == "UNKNOWN"
    assert result["effective_max_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_blocks_when_price_is_outside_entry_zone():
    result = build_local_pilot_portfolio_package(**_portfolio_package_args(price_input={"price": "101"}))
    assert result["current_price_zone_status"] == "ABOVE_ENTRY_ZONE"
    assert result["conditional_proposed_position_pct"] is None
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_does_not_auto_reduce_an_existing_over_limit_position():
    args = _portfolio_package_args(
        case={"case_id": "RC-CN-A-TEST", "as_of_date": "2026-10-10", "current_position_pct": "3"}
    )
    result = build_local_pilot_portfolio_package(**args)
    assert result["effective_max_position_pct"] == "2"
    assert result["current_position_over_effective_max"] is True
    assert result["conditional_proposed_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"
    assert result["execution_authorized"] is False


def test_portfolio_package_blocks_risk_references_with_uncertain_timing():
    result = build_local_pilot_portfolio_package(
        **_portfolio_package_args(uncertain_timing_evidence_ids=["E1"])
    )
    assert result["risk_portfolio_contract_status"] == "BLOCKED"
    assert result["conditional_proposed_position_pct"] is None
    assert result["authorized_new_position_pct"] == "0"


def test_portfolio_package_rejects_misordered_position_bands():
    result = build_local_pilot_portfolio_package(
        **_portfolio_package_args(operator_context={
            "constraint_status": "PASS", "can_add": True, "risk_budget_pct_nav": "1",
            "entry_zone_low": "90", "entry_zone_high": "100",
            "initial_position_pct": "5", "target_position_pct": "4", "max_position_pct": "8",
        })
    )
    assert result["status"] == "BLOCKED_INVALID_OPERATOR_CONTEXT"
    assert "POSITION_BOUNDS" in result["reason"]
    assert result["authorized_new_position_pct"] == "0"


def test_local_pilot_report_exposes_missing_portfolio_package_as_unknown():
    from iios_mvp.local_investment_pilot_v01 import _analyse

    analysis, report = _analyse(_payload(), "local-pilot-test-package")
    assert analysis["portfolio_package"]["status"] == "NOT_PROVIDED"
    assert analysis["decision"]["core_policy_evaluation"]["portfolio_status"] == "UNKNOWN"
    assert analysis["decision"]["execution_authorized"] is False
    assert "组合风险预算与条件仓位包" in report
    assert "本次实际获准新增仓位：0%" in report



def test_operator_prompt_uses_controlling_tty_when_python_runs_from_heredoc(monkeypatch):
    import builtins
    import io
    from unittest.mock import mock_open
    import iios_mvp.local_investment_pilot_v01 as pilot

    monkeypatch.setattr(pilot.sys, "stdin", io.StringIO("python source already consumed"))
    monkeypatch.setattr(pilot.sys.stdin, "isatty", lambda: False)
    tty = mock_open(read_data="1\\n")
    monkeypatch.setattr(builtins, "open", tty)

    assert pilot._read_operator_prompt("portfolio budget? ") == "1\\n"
    tty.assert_called_once_with("/dev/tty", "r+", encoding="utf-8", buffering=1)
    tty().write.assert_called_once_with("portfolio budget? ")


def test_operator_prompt_returns_actionable_error_when_no_tty_available(monkeypatch):
    import builtins
    import io
    import iios_mvp.local_investment_pilot_v01 as pilot

    monkeypatch.setattr(pilot.sys, "stdin", io.StringIO("python source already consumed"))
    monkeypatch.setattr(pilot.sys.stdin, "isatty", lambda: False)

    def no_tty(*args, **kwargs):
        raise OSError("not a tty")

    monkeypatch.setattr(builtins, "open", no_tty)
    with pytest.raises(LocalInvestmentPilotError, match="INTERACTIVE_TERMINAL_UNAVAILABLE"):
        pilot._read_operator_prompt("portfolio budget? ")



def test_saved_response_file_is_detected_automatically_after_stable_write(tmp_path: Path):
    """The wizard must resume after Save; pressing Enter is not required."""
    response_path = tmp_path / "pilot-chatgpt-response.json"
    response_path.write_text("", encoding="utf-8")
    initial_signature = _response_file_signature(response_path)
    assert initial_signature is not None

    def simulate_textedit_save():
        _time.sleep(0.04)
        response_path.write_text('{"partial":', encoding="utf-8")
        _time.sleep(0.04)
        response_path.write_text('{"complete": true, "company": "纽威股份"}', encoding="utf-8")

    writer = threading.Thread(target=simulate_textedit_save, daemon=True)
    writer.start()
    saved_signature = _wait_for_response_file_change(
        response_path,
        previous_signature=initial_signature,
        poll_interval=0.01,
        stable_seconds=0.04,
    )
    writer.join(timeout=1)
    assert not writer.is_alive()
    assert saved_signature != initial_signature
    assert json.loads(response_path.read_text(encoding="utf-8")) == {
        "complete": True,
        "company": "纽威股份",
    }


def test_response_file_watcher_ignores_existing_unsaved_stale_content(tmp_path: Path):
    """A previously read invalid response must be replaced/saved before re-checking."""
    response_path = tmp_path / "pilot-chatgpt-response.json"
    response_path.write_text('{"version": 1}', encoding="utf-8")
    old_signature = _response_file_signature(response_path)
    assert old_signature is not None

    def simulate_repair_save():
        _time.sleep(0.05)
        response_path.write_text('{"version": 2}', encoding="utf-8")

    writer = threading.Thread(target=simulate_repair_save, daemon=True)
    writer.start()
    new_signature = _wait_for_response_file_change(
        response_path,
        previous_signature=old_signature,
        poll_interval=0.01,
        stable_seconds=0.04,
    )
    writer.join(timeout=1)
    assert not writer.is_alive()
    assert new_signature != old_signature
    assert json.loads(response_path.read_text(encoding="utf-8"))["version"] == 2

def test_response_file_picker_can_import_saved_json_without_destroying_source(tmp_path: Path, monkeypatch):
    import types

    target = tmp_path / "pilot-chatgpt-response-target.json"
    target.write_text("", encoding="utf-8")
    saved_elsewhere = tmp_path / "pilot-chatgpt-response-saved.json"
    content = '{"schema_version":"test","case":{"symbol":"603699"}}'
    saved_elsewhere.write_text(content, encoding="utf-8")

    monkeypatch.setattr(pilot.sys, "platform", "darwin")

    def fake_run(command, **kwargs):
        assert command[0] == "osascript"
        assert kwargs["check"] is True
        return types.SimpleNamespace(stdout=str(saved_elsewhere) + "\n")

    monkeypatch.setattr(pilot.subprocess, "run", fake_run)
    assert pilot._choose_saved_response_file(target) is True
    assert target.read_text(encoding="utf-8") == content
    assert saved_elsewhere.read_text(encoding="utf-8") == content
    assert pilot._response_file_signature(target)[0] == len(content.encode("utf-8"))


def test_response_file_diagnostic_identifies_empty_target_without_leaking_contents(tmp_path: Path):
    target = tmp_path / "pilot-chatgpt-response.json"
    target.write_text("", encoding="utf-8")
    diagnostic = pilot._response_file_diagnostic(target)
    assert str(target) in diagnostic
    assert "0 字节" in diagnostic
    assert "文件存在" in diagnostic


def test_enter_force_rechecks_nonempty_response_even_when_signature_is_unchanged(tmp_path: Path, monkeypatch, capsys):
    class EnterTerminal:
        def isatty(self):
            return True

        def readline(self):
            return "\n"

    response_path = tmp_path / "pilot-chatgpt-response.json"
    response_path.write_text('{"version": 1}', encoding="utf-8")
    signature = _response_file_signature(response_path)
    assert signature is not None

    terminal = EnterTerminal()
    monkeypatch.setattr(pilot.sys, "stdin", terminal)
    monkeypatch.setattr(pilot.select, "select", lambda *_args, **_kwargs: ([terminal], [], []))
    detected = _wait_for_response_file_change(
        response_path,
        previous_signature=signature,
        poll_interval=0.001,
        stable_seconds=1.0,
    )
    assert detected == signature
    assert "重新校验当前文件" in capsys.readouterr().out



def test_b4_report_preserves_numeric_zero_in_operating_bridge_fields():
    zero = {
        "calculation_status": "SCENARIO_ARITHMETIC_COMPLETE",
        "production_volume_tonnes": 0,
        "sales_volume_tonnes": 0,
        "revenue_cny": 0,
        "variable_cost_cny": 0,
        "contribution_after_variable_cost_cny": 0,
        "ebitda_cny": 0,
        "ebit_cny": 0,
        "profit_before_tax_cny": 0,
        "net_profit_cny": 0,
        "cash_capex_cny": 0,
        "change_working_capital_cny": 0,
        "unlevered_fcf_proxy_cny": 0,
    }
    forecast = {
        "status": "CALCULATED",
        "product_lines": [
            {
                "product_id": "P1",
                "product_name": "测试产品",
                "capacity_tonnes_per_year": {"value": "100", "unit": "吨"},
                "historical_actuals": {},
                "historical_actual_bridge": {
                    "revenue_cny": 0,
                    "variable_cost_cny": 0,
                    "issues": [],
                },
            }
        ],
        "scenarios": {"bear": zero},
    }
    report = "\n".join(render_operating_driver_section(
        forecast,
        {"bear": {"terminal_value_per_share": 0}},
        valuation_transmission={
            "status": "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
            "applied_to_per_share_scenarios": False,
            "summary": "synthetic test",
        },
    ))
    assert "历史收入：0；识别口径：UNKNOWN；销量×单位变动成本：0。" in report
    assert "- 产量 / 销量：0 / 0 吨" in report
    assert "- 收入：0；变动成本：0；扣变动成本贡献：0" in report
    assert "- EBITDA / EBIT / 税前利润 / 净利润：0 / 0 / 0 / 0" in report
    assert "- 资本开支 / 营运资金变动 / 自由现金流代理：0 / 0 / 0" in report
    assert "未应用 B5 增量的每股估值情景终值：0 CNY" in report


def test_b4_report_renders_missing_operating_bridge_fields_as_unknown():
    forecast = {
        "status": "CALCULATED",
        "product_lines": [
            {
                "product_id": "P1",
                "product_name": "测试产品",
                "capacity_tonnes_per_year": {"value": "100", "unit": "吨"},
                "historical_actuals": {},
                "historical_actual_bridge": {
                    "revenue_cny": None,
                    "variable_cost_cny": "",
                    "issues": [],
                },
            }
        ],
        "scenarios": {
            "bear": {
                "calculation_status": "PARTIAL_SCENARIO_BRIDGE",
                "production_volume_tonnes": None,
                "sales_volume_tonnes": "",
                "revenue_cny": None,
                "variable_cost_cny": "",
                "contribution_after_variable_cost_cny": None,
                "ebitda_cny": None,
                "ebit_cny": "",
                "profit_before_tax_cny": None,
                "net_profit_cny": "",
                "cash_capex_cny": None,
                "change_working_capital_cny": "",
                "unlevered_fcf_proxy_cny": None,
            }
        },
    }
    report = "\n".join(render_operating_driver_section(
        forecast,
        {"bear": {"terminal_value_per_share": None}},
        valuation_transmission={
            "status": "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID",
            "applied_to_per_share_scenarios": False,
            "summary": "synthetic test",
        },
    ))
    assert "历史收入：UNKNOWN；识别口径：UNKNOWN；销量×单位变动成本：UNKNOWN。" in report
    assert "- 产量 / 销量：UNKNOWN / UNKNOWN 吨" in report
    assert "- 收入：UNKNOWN；变动成本：UNKNOWN；扣变动成本贡献：UNKNOWN" in report
    assert "- EBITDA / EBIT / 税前利润 / 净利润：UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN" in report
    assert "- 资本开支 / 营运资金变动 / 自由现金流代理：UNKNOWN / UNKNOWN / UNKNOWN" in report
    assert "未应用 B5 增量的每股估值情景终值：UNKNOWN CNY" in report

def test_b5_incomplete_counterfactual_does_not_block_confirmed_project_inclusive_primary_valuation():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = True
    payload["valuation_transmission"]["scenarios"]["base"]["displaced_existing_after_tax_profit_cny"] = {
        "value": None,
        "unit": "CNY",
        "data_class": "UNKNOWN",
        "basis": "",
        "evidence_refs": [],
        "note": "Counterfactual cannibalization is not identifiable; existing baseline already includes the project.",
    }

    analysis, report = _analyse(payload, "TEST-B5-INCOMPLETE-COUNTERFACTUAL-INCLUDED-BASELINE")

    assert analysis["valuation_transmission"]["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_transmission"]["applied_to_per_share_scenarios"] is False
    assert all(
        analysis["forecast_valuation"]["scenarios"][name]["terminal_value_per_share"] == base
        for name, base in (("bear", "120"), ("base", "150"), ("bull", "180"))
    )
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["return_metrics"] is not None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is not None
    assert "MATCH_BASELINE_PROJECT_INCLUDED_B5_DIAGNOSTIC_ONLY" in report
    assert "非阻断性说明：操作者已确认现有估值基准包含该项目" in report
    assert "回报计算尚未完成" not in report


def test_b4_overcapacity_scenario_does_not_feed_b5_or_target_entry_price():
    payload = _b5_ready_payload()
    # Nameplate is 1,000 tonnes/year; the scenario claims 1,200 tonnes for
    # an explicitly full-year forecast and provides no capacity expansion bridge.
    payload["operating_driver_forecast"]["scenarios"]["base"]["product_lines"][0]["production_tonnes"] = _driver_measure(
        "1200", "tonnes", "ANALYST_ASSUMPTION", [], "Unreconciled volume above nameplate capacity"
    )

    analysis, report = _analyse(payload, "TEST-B4-OVERCAPACITY-B5-BLOCK")

    driver = analysis["operating_driver_forecast"]["scenarios"]["base"]
    assert driver["net_profit_cny"] is None
    assert driver["unlevered_fcf_proxy_cny"] is None
    assert driver["financial_outputs_decision_usable"] is False
    assert analysis["valuation_transmission"]["status"] == "NOT_LINKED_INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_transmission"]["applied_to_per_share_scenarios"] is False
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "产能约束未闭合" in report
    assert "财务结果可用于下游估值：False" in report





def test_required_return_below_15_percent_remains_independent_from_fundamental_hurdle():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["baseline_includes_project"] = True
    payload["decision_parameters"]["required_return_annualized"] = "0.10"
    payload["forecast_valuation"]["scenarios"] = {
        "bear": {
            "probability": "0.20",
            "terminal_value_per_share": "100",
            "cash_distributions_per_share": "0",
            "rationale": "synthetic bear case with a 100 CNY terminal wealth",
            "failure_trigger": "core driver underperforms",
            "operating_impact": "earnings remain below base",
            "valuation_mechanism": "lower normalized EPS",
        },
        "base": {
            "probability": "0.50",
            "terminal_value_per_share": "115",
            "cash_distributions_per_share": "0",
            "rationale": "synthetic base case with a 115 CNY terminal wealth",
        },
        "bull": {
            "probability": "0.30",
            "terminal_value_per_share": "125",
            "cash_distributions_per_share": "0",
            "rationale": "synthetic bull case with a 125 CNY terminal wealth",
        },
    }
    _sync_eps_multiple_values(payload, {"bear": "100", "base": "115", "bull": "125"})

    analysis, report = _analyse(payload, "TEST-REQUIRED-RETURN-INDEPENDENT-OF-15-PCT")
    metrics = analysis["return_metrics"]
    params = analysis["decision_parameters"]

    assert params["required_return_annualized"] == "0.10"
    assert params["fundamental_target_annualized_return"] == "0.15"
    assert Decimal("0.10") <= Decimal(metrics["expected_annualized_return"]) < Decimal("0.15")
    assert metrics["required_return_pass"] is True
    assert metrics["fundamental_target_pass"] is False
    assert metrics["return_gate_pass"] is False
    assert Decimal(metrics["target_entry_price_for_return"]) < Decimal(
        metrics["target_entry_price_for_required_return"]
    )
    # Preserving the 10% benchmark does not relax the independent 15% hurdle:
    # the 15% target-return cap remains the binding entry-price ceiling.
    assert metrics["target_entry_price"] == metrics["target_entry_price_for_return"]
    assert "Required Return：0.10；结果：True" in report
    assert "15% 年化门槛：False" in report



def test_operator_model_prompt_records_unknown_as_unconfirmed(monkeypatch, capsys):
    monkeypatch.setattr(pilot, "_ask", lambda _prompt, default=None: "0")
    context = pilot._ask_operator_valuation_context()
    assert context["selected_model_family"] == "UNKNOWN"
    assert context["selection_source"] == "INTERACTIVE_OPERATOR_PROMPT"
    assert context["selection_confirmed"] is False
    assert "操作者明确确认：否" in capsys.readouterr().out


def test_unconfirmed_interactive_model_selection_cannot_be_reinterpreted_as_sotp():
    payload = _payload()
    payload["operator_valuation_context"] = {
        "selected_model_family": "SOTP",
        "baseline_includes_project": None,
        "input_owner": "OPERATOR",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": False,
    }
    prepared = _prepare_input(payload)
    assert prepared["operator_valuation_context"]["selected_model_family"] == "UNKNOWN"
    assert prepared["operator_valuation_context"]["selection_confirmed"] is False


def test_confirmed_interactive_sotp_is_preserved_as_operator_choice(monkeypatch):
    monkeypatch.setattr(pilot, "_ask", lambda _prompt, default=None: "4")
    context = pilot._ask_operator_valuation_context()
    assert context["selected_model_family"] == "SOTP"
    assert context["selection_source"] == "INTERACTIVE_OPERATOR_PROMPT"
    assert context["selection_confirmed"] is True


def test_value_driver_accepts_observed_basis_and_transmission_aliases():
    payload = _payload()
    driver = payload["assessment"]["value_drivers"][0]
    driver.pop("historical_evidence", None)
    driver.pop("valuation_transmission", None)
    driver["observed_basis"] = "FY2025 synthetic shipped-volume baseline."
    driver["transmission"] = "Volume × net ASP less unit variable cost reaches contribution profit and EPS."
    driver["unresolved_inputs"] = ["Next-year unit volume", "Net ASP"]
    prepared = _prepare_input(payload)
    normalized = prepared["assessment"]["value_drivers"][0]
    assert normalized["historical_evidence"] == driver["observed_basis"]
    assert normalized["valuation_transmission"] == driver["transmission"]
    assert normalized["unresolved_inputs"] == driver["unresolved_inputs"]
    assert normalized["status"] == "PASS"
    _, report = _analyse(payload, "TEST-VALUE-DRIVER-ALIASES")
    assert "历史依据：FY2025 synthetic shipped-volume baseline." in report
    assert "价值传导：Volume × net ASP less unit variable cost reaches contribution profit and EPS." in report
    assert "尚待验证的经营输入：" in report
    assert "Next-year unit volume" in report


def test_evidence_date_with_unknown_clock_time_is_not_marked_invalid():
    payload = _payload(cutoff="2026-10-10")
    source = payload["evidence_register"][0]
    source["published_at"] = "2026-08-30"
    source["known_at"] = "2026-08-30；确切发布时间UNKNOWN"
    prepared = _prepare_input(payload)
    normalized = prepared["evidence_register"][0]
    assert normalized["known_at"] == "2026-08-30"
    assert normalized["known_at_original"] == "2026-08-30；确切发布时间UNKNOWN"
    assert normalized["published_at"] == "2026-08-30"
    assert normalized["known_at_precision"] == "DATE_ONLY_EXPLICIT_TIME_UNKNOWN"
    assert normalized["time_status"] == "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"
    assert "E1" not in prepared["uncertain_timing_evidence_references"]
    _, report = _analyse(payload, "TEST-PUBLISHED-DATE-REPORT")
    assert "published_at：2026-08-30" in report
    assert "时间依据：KNOWN_AT_DATE_ONLY" in report


def test_unknown_dynamic_page_time_stays_unknown_and_preserves_published_at_text():
    payload = _payload(cutoff="2026-10-10")
    source = payload["evidence_register"][0]
    source["published_at"] = "持续更新的交易所页面；可见若干历史公告"
    source["known_at"] = "检索时可访问；页面确切更新时间UNKNOWN"
    prepared = _prepare_input(payload)
    normalized = prepared["evidence_register"][0]
    assert normalized["published_at"] == source["published_at"]
    assert normalized["time_status"] == "UNKNOWN"
    assert normalized["time_basis"] == "TIME_NOT_IDENTIFIABLE"
    assert "E1" in prepared["uncertain_timing_evidence_references"]


def test_positive_cash_distribution_without_dates_blocks_return_metrics():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic distribution is assumed announced.",
        "evidence_refs": ["E1"],
    }
    for row in payload["forecast_valuation"]["scenarios"].values():
        row["cash_distributions_per_share"] = "1"
        row["cash_distribution_events"] = []
    analysis, _ = _analyse(payload, "TEST-DISTRIBUTION-DATE-MISSING")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "BEAR_CASH_DISTRIBUTION_TIMING_UNRESOLVED"


def test_dated_cash_distribution_changes_irr_and_target_entry_price_correctly():
    payload = _b5_ready_payload()
    forecast = payload["forecast_valuation"]
    forecast["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic official distribution implementation for date-aware calculation test.",
        "evidence_refs": ["E1"],
    }
    for row in forecast["scenarios"].values():
        row["cash_distributions_per_share"] = "1"
        row["cash_distribution_events"] = [{
            "gross_amount_per_share": "1.10",
            "tax_amount_per_share": "0.10",
            "amount_per_share": "1.00",
            "tax_basis": "Synthetic test assumption; explicit tax/holding-period basis.",
            "tax_rationale": "Synthetic test assumption: gross 1.10 less tax 0.10 equals net 1.00.",
            "record_date": "2026-10-19",
            "ex_date": "2026-10-20",
            "payment_date": "2026-10-20",
            "eligible_if_entered_at_cutoff": True,
            "eligibility_basis": "Synthetic test assumption: cutoff precedes record date, so new entry at cutoff qualifies.",
            "evidence_refs": ["E1"],
        }]
    analysis, report = _analyse(payload, "TEST-DATED-DISTRIBUTION-IRR")
    assert analysis["return_metrics"] is not None
    assert analysis["return_metrics"]["expected_annualized_return_method"] == "PROBABILITY_WEIGHTED_DATED_CASH_FLOW_IRR"
    assert analysis["return_metrics"]["return_price_cap_method"] == "PRESENT_VALUE_OF_PROBABILITY_WEIGHTED_DATED_CASH_FLOWS"
    assert Decimal(analysis["return_metrics"]["target_entry_price_for_return"]) > Decimal("0")
    assert "登记日 2026-10-19；除息日 2026-10-20；支付日 2026-10-20" in report
    assert "税前 1.10；税额 0.10；计入每股税后现金流 1.00" in report
    event = analysis["forecast_valuation"]["scenarios"]["base"]["cash_distribution_events"][0]
    assert event["eligible_if_entered_at_cutoff"] is True
    assert event["eligibility_assumption"] == "CONDITIONAL_ON_HYPOTHETICAL_ENTRY_AT_INPUT_PRICE_ON_CUTOFF_DATE"
    assert event["actual_execution_confirmed"] is False
    assert event["actual_dividend_entitlement_confirmed"] is False
    assert "条件性；实际成交/实际权益未确认" in report


def test_distribution_review_must_explicitly_confirm_no_future_payouts_for_zero_to_count():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["cash_distribution_review"] = {
        "status": "UNKNOWN", "summary": "", "evidence_refs": []
    }
    analysis, _ = _analyse(payload, "TEST-DISTRIBUTION-UNKNOWN")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "CASH_DISTRIBUTION_REVIEW_NOT_RESOLVED"


def test_dated_distribution_tax_arithmetic_must_reconcile():
    payload = _b5_ready_payload()
    forecast = payload["forecast_valuation"]
    forecast["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic official distribution implementation for tax arithmetic check.",
        "evidence_refs": ["E1"],
    }
    for row in forecast["scenarios"].values():
        row["cash_distributions_per_share"] = "1.00"
        row["cash_distribution_events"] = [{
            "gross_amount_per_share": "1.10",
            "tax_amount_per_share": "0.05",
            "amount_per_share": "1.00",
            "tax_basis": "Synthetic explicit assumption",
            "tax_rationale": "Synthetic tax assumption",
            "record_date": "2026-10-19",
            "ex_date": "2026-10-20",
            "payment_date": "2026-10-20",
            "eligible_if_entered_at_cutoff": True,
            "eligibility_basis": "Synthetic cutoff-before-record-date assumption",
            "evidence_refs": ["E1"],
        }]
    analysis, _ = _analyse(payload, "TEST-DISTRIBUTION-TAX-MISMATCH")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "BEAR_CASH_DISTRIBUTION_EVENT_1_GROSS_TAX_NET_MISMATCH"


def test_dated_distribution_requires_record_date_eligibility_and_tax_basis():
    payload = _b5_ready_payload()
    forecast = payload["forecast_valuation"]
    forecast["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic dated payout with unresolved eligibility.",
        "evidence_refs": ["E1"],
    }
    for row in forecast["scenarios"].values():
        row["cash_distributions_per_share"] = "1.00"
        row["cash_distribution_events"] = [{
            "gross_amount_per_share": "1.10",
            "tax_amount_per_share": "0.10",
            "amount_per_share": "1.00",
            "tax_basis": "Synthetic explicit assumption",
            "tax_rationale": "Synthetic tax assumption",
            "record_date": "2026-10-19",
            "ex_date": "2026-10-20",
            "payment_date": "2026-10-20",
            "eligible_if_entered_at_cutoff": False,
            "eligibility_basis": "Synthetic purchase occurs after record date.",
            "evidence_refs": ["E1"],
        }]
    analysis, _ = _analyse(payload, "TEST-DISTRIBUTION-ELIGIBILITY-UNKNOWN")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "BEAR_CASH_DISTRIBUTION_EVENT_1_ENTRY_ELIGIBILITY_NOT_CONFIRMED"


def test_replay_comparison_includes_derived_valuation_and_evidence_integrity_fields():
    required = {
        "duplicate_evidence_ids",
        "untraceable_evidence_ids",
        "untraceable_evidence_fields",
        "valuation_model_consistency",
        "valuation_timing",
    }
    assert required.issubset(set(pilot.REPLAY_COMPARISON_FIELDS))

    before = {field: None for field in pilot.REPLAY_COMPARISON_FIELDS}
    before.update({
        "pilot_id": "prior-run",
        "valuation_model_consistency": {"status": "MATCH", "primary_model_price_calculation_eligible": True},
        "valuation_timing": {"status": "PASS", "annualization_year_fraction": "1.2"},
        "duplicate_evidence_ids": [],
        "untraceable_evidence_ids": [],
        "untraceable_evidence_fields": {},
    })
    after = dict(before)
    after["pilot_id"] = "replay-run"
    after["valuation_timing"] = {"status": "UNKNOWN", "annualization_year_fraction": None}
    result = pilot._replay_comparison(before, after)
    assert result["status"] == "MISMATCH"
    assert "valuation_timing" in result["mismatched_fields"]

    after = dict(before)
    after["pilot_id"] = "replay-run"
    after["valuation_model_consistency"] = {
        "status": "MODEL_FAMILY_MISMATCH",
        "primary_model_price_calculation_eligible": False,
    }
    result = pilot._replay_comparison(before, after)
    assert result["status"] == "MISMATCH"
    assert "valuation_model_consistency" in result["mismatched_fields"]

    after = dict(before)
    after["pilot_id"] = "replay-run"
    after["untraceable_evidence_fields"] = {"E1": ["published_at"]}
    result = pilot._replay_comparison(before, after)
    assert result["status"] == "MISMATCH"
    assert "untraceable_evidence_fields" in result["mismatched_fields"]


def test_hong_kong_dated_cash_distribution_uses_ex_date_before_record_date():
    payload = _b5_ready_payload()
    payload["case"]["market"] = "HK"
    payload["case"]["symbol"] = "0700.HK"
    payload["case"]["currency"] = "HKD"
    payload["price_input"]["currency"] = "HKD"
    _sync_eps_multiple_values(payload, {"bear": "120", "base": "150", "bull": "180"})
    forecast = payload["forecast_valuation"]
    forecast["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic official HK distribution chronology for market-specific unit test.",
        "evidence_refs": ["E2"],
    }
    for row in forecast["scenarios"].values():
        row["cash_distributions_per_share"] = "1.00"
        row["cash_distribution_events"] = [{
            "gross_amount_per_share": "1.10",
            "tax_amount_per_share": "0.10",
            "amount_per_share": "1.00",
            "tax_basis": "Synthetic explicit test assumption",
            "tax_rationale": "Synthetic gross 1.10 minus tax 0.10 equals net 1.00.",
            "record_date": "2026-10-21",
            "ex_date": "2026-10-20",
            "payment_date": "2026-10-30",
            "eligible_if_entered_at_cutoff": True,
            "eligibility_basis": "Synthetic case: cutoff is before the announced Hong Kong ex-date and entitlement dates.",
            "evidence_refs": ["E1"],
        }]
    analysis, _ = _analyse(payload, "TEST-HK-DATED-DISTRIBUTION")
    assert analysis["return_metrics"] is not None
    assert analysis["return_metrics"]["expected_annualized_return_method"] == "PROBABILITY_WEIGHTED_DATED_CASH_FLOW_IRR"


@pytest.mark.parametrize(
    ("market", "record_date", "ex_date"),
    [
        ("CN-A", "2026-10-21", "2026-10-20"),
        ("HK", "2026-10-20", "2026-10-21"),
    ],
)
def test_dated_distribution_rejects_cross_market_record_ex_date_order(market, record_date, ex_date):
    payload = _b5_ready_payload()
    payload["case"]["market"] = market
    if market == "HK":
        payload["case"]["symbol"] = "0700.HK"
        payload["case"]["currency"] = "HKD"
        payload["price_input"]["currency"] = "HKD"
    _sync_eps_multiple_values(payload, {"bear": "120", "base": "150", "bull": "180"})
    forecast = payload["forecast_valuation"]
    forecast["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "Synthetic dated cash distribution chronology cross-market rejection test.",
        "evidence_refs": ["E2"],
    }
    for row in forecast["scenarios"].values():
        row["cash_distributions_per_share"] = "1.00"
        row["cash_distribution_events"] = [{
            "gross_amount_per_share": "1.10",
            "tax_amount_per_share": "0.10",
            "amount_per_share": "1.00",
            "tax_basis": "Synthetic explicit test assumption",
            "tax_rationale": "Synthetic gross 1.10 minus tax 0.10 equals net 1.00.",
            "record_date": record_date,
            "ex_date": ex_date,
            "payment_date": "2026-10-30",
            "eligible_if_entered_at_cutoff": True,
            "eligibility_basis": "Synthetic cross-market chronology test.",
            "evidence_refs": ["E1"],
        }]
    analysis, _ = _analyse(payload, "TEST-CROSS-MARKET-DISTRIBUTION-ORDER")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "BEAR_CASH_DISTRIBUTION_EVENT_1_DATES_NOT_ELIGIBLE_FROM_CUTOFF"


def test_rehosted_dividend_source_cannot_pass_by_self_declared_source_class():
    payload = _payload()
    payload["evidence_register"][1]["source_class"] = "EXCHANGE_PRIMARY"
    payload["evidence_register"][1]["source_ref"] = "https://finance.sina.com.cn/rehosted/dividend-notice.html"
    payload["forecast_valuation"]["cash_distribution_review"]["summary"] = "已核实中期分红。"

    analysis, report = _analyse(payload, "TEST-REHOSTED-DIVIDEND-SOURCE")
    evidence = next(row for row in analysis["evidence_register"] if row["source_id"] == "E2")
    review = analysis["forecast_valuation"]["cash_distribution_review"]

    assert evidence["source_url_host"] == "finance.sina.com.cn"
    assert evidence["source_domain_class_status"] == "DOMAIN_NOT_ALLOWLISTED_AS_PRIMARY"
    assert evidence["cash_distribution_primary_domain_eligible"] is False
    assert review["source_validation_status"] == "BLOCKED_SOURCE_DOMAIN_CLASS_OR_CUTOFF_REVIEW"
    assert review["formal_evidence_pit_admission"] is False
    assert review["analyst_supplied_summary_unverified"] == "已核实中期分红。"
    assert "已核实中期分红" not in review["summary"]
    assert "未获准作为已核实现金流" in review["summary"]
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "CASH_DISTRIBUTION_SOURCE_DOMAIN_CLASS_NOT_ACCEPTED" in analysis["decision"]["gating_issues"]
    assert "URL 主机名：finance.sina.com.cn" in report
    assert "正式证据准入：未完成" in report


def test_official_exchange_domain_match_is_not_misreported_as_formal_admission():
    payload = _payload(cutoff="2026-10-12")
    payload["evidence_register"][1]["source_class"] = "EXCHANGE_PRIMARY"
    payload["evidence_register"][1]["source_ref"] = (
        "http://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/"
        "2026-10-13/603699_20261013_QYJT.pdf"
    )
    payload["forecast_valuation"]["cash_distribution_review"] = {
        "status": "KNOWN_FUTURE_DISTRIBUTIONS",
        "summary": "模型输入声明有一笔未来分红。",
        "evidence_refs": ["E2"],
    }
    event = {
        "amount_per_share": "0.42",
        "gross_amount_per_share": "0.42",
        "tax_amount_per_share": "0",
        "tax_basis": "Synthetic test tax treatment",
        "tax_rationale": "Synthetic fixture assumes no tax withheld",
        "record_date": "2026-10-20",
        "ex_date": "2026-10-21",
        "payment_date": "2026-10-23",
        "eligible_if_entered_at_cutoff": True,
        "eligibility_basis": "Synthetic fixture confirms entry before record date",
        "evidence_refs": ["E2"],
    }
    for row in payload["forecast_valuation"]["scenarios"].values():
        row["cash_distributions_per_share"] = "0.42"
        row["cash_distribution_events"] = [dict(event)]

    analysis, report = _analyse(payload, "TEST-OFFICIAL-EXCHANGE-DOMAIN-NOT-ADMITTED")
    evidence = next(row for row in analysis["evidence_register"] if row["source_id"] == "E2")
    review = analysis["forecast_valuation"]["cash_distribution_review"]

    assert evidence["source_domain_class_status"] == "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    assert evidence["cash_distribution_primary_domain_eligible"] is True
    assert review["source_validation_status"] == "OFFICIAL_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
    assert review["formal_evidence_pit_admission"] is False
    assert "未全部独立确认" in review["summary"]
    assert analysis["return_metrics"] is not None
    assert "模型输入声明，非正式证据准入" in report
    assert "正式证据准入：未完成" in report
    assert "source_domain_class_status" not in report


def test_confirmed_model_selection_neutralizes_stale_ai_confirmation_rationale():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"].update({
        "selected_model_family": "SOTP",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": True,
    })
    payload["forecast_valuation"]["model_rationale"] = (
        "操作者尚待本地确认主估值模型；当前草稿用 EPS_MULTIPLE 估算每股价值。"
    )

    analysis, report = _analyse(payload, "TEST-STALE-MODEL-CONFIRMATION-WORDING")
    forecast = analysis["forecast_valuation"]

    assert forecast["model_rationale_status"] == "STALE_OPERATOR_CONFIRMATION_LANGUAGE_NEUTRALIZED"
    assert "操作者尚待本地确认" not in forecast["model_rationale"]
    assert "操作者尚待本地确认" in forecast["model_rationale_original_untrusted"]
    assert "操作者尚待本地确认" not in report
    assert "旧稿待确认措辞已按本次本地操作者确认记录清理" in report
    assert "操作者选择的主模型类别：SOTP" in report
    assert "当前情景实际计算模型类别：EPS_MULTIPLE" in report
    assert analysis["return_metrics"] is None


def _sotp_measure(value, unit, data_class="ANALYST_ASSUMPTION", refs=None, basis="Explicit synthetic SOTP test assumption"):
    return {
        "value": str(value),
        "unit": unit,
        "data_class": data_class,
        "basis": basis,
        "evidence_refs": list(refs or []),
        "note": basis,
    }


def _sotp_ready_payload():
    payload = _payload(cutoff="2026-10-10")
    payload["operator_valuation_context"] = {
        "selected_model_family": "SOTP",
        "baseline_includes_project": None,
        "input_owner": "OPERATOR",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": True,
    }

    def scenario(profits, multiples, central_cost_multiple, rationale):
        segments = []
        for segment_id, segment_name, profit, multiple in (
            ("valves_core", "Core industrial valves", profits[0], multiples[0]),
            ("specialty", "Specialty valves", profits[1], multiples[1]),
        ):
            segments.append({
                "segment_id": segment_id,
                "segment_name": segment_name,
                "attributable_net_profit_cny": _sotp_measure(profit, "CNY"),
                "pe_multiple_x": _sotp_measure(multiple, "x"),
            })
        return {
            "rationale": rationale,
            "segments": segments,
            "parent_level_adjustments": {
                "central_cost_after_tax_cny": _sotp_measure("200000000", "CNY"),
                "central_cost_multiple_x": _sotp_measure(central_cost_multiple, "x"),
                "net_cash_debt_cny": _sotp_measure("2000000000", "CNY", basis="Explicit signed net-cash assumption"),
                "other_adjustments_cny": _sotp_measure("0", "CNY", basis="No additional adjustments in this synthetic fixture"),
            },
            "diluted_shares": _sotp_measure("1000000000", "shares", basis="Explicit synthetic diluted share count"),
        }

    payload["sotp_valuation"] = {
        "schema_version": "IIOS-SOTP-VALUATION-0.1",
        "calculation_method": "SEGMENT_ATTRIBUTABLE_NET_PROFIT_X_SEGMENT_PE",
        "summary": "Synthetic test only: use distinct segment P/E values and explicit parent-level adjustments.",
        "forecast_period": "2027FY",
        "valuation_terminal_date": "2027-12-31",
        "scenarios": {
            "bear": scenario(["4000000000", "2000000000"], ["8", "9"], "8", "Synthetic downside segment profits and compressed multiples."),
            "base": scenario(["5000000000", "2500000000"], ["10", "12"], "10", "Synthetic base segment profits and segment-specific multiples."),
            "bull": scenario(["6000000000", "3000000000"], ["12", "14"], "12", "Synthetic upside segment profits and expanded multiples."),
        },
    }
    return payload


def test_primary_eps_multiple_adapter_recomputes_values_and_entry_anchor_locally():
    payload = _payload()
    payload["forecast_valuation"]["entry_value_reference_per_share"] = "777"
    payload["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] = "999"
    payload["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] = "888"
    payload["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] = "777"

    analysis, report = _analyse(payload, "TEST-EPS-MULTIPLE-LOCAL-RECALC")
    adapter = analysis["eps_multiple_valuation"]

    assert adapter["status"] == "CALCULATED"
    assert adapter["scenarios"]["base"]["calculation"]["arithmetic"] == "10 × 15 = 150"
    assert analysis["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] == "120"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["bull"]["terminal_value_per_share"] == "180"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["declared_terminal_value_before_eps_multiple_calculation"] == "888"
    assert analysis["forecast_valuation"]["declared_entry_value_reference_before_eps_multiple_calculation"] == "777"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is True
    assert analysis["return_metrics"] is not None
    assert "EPS_MULTIPLE：每股盈利 × 市盈率的主估值计算链" in report
    assert "10 × 15 = 150" in report
    assert "EPS_MULTIPLE 原始声明终值（仅供审计，不进入主计算）：888 CNY" in report
    assert "EPS_MULTIPLE 原始声明锚（仅供审计，不进入主计算）：777" in report


def test_primary_eps_multiple_missing_structured_input_blocks_return_and_entry_price():
    payload = _payload()
    payload["eps_multiple_valuation"]["scenarios"]["base"]["eps_per_share"]["value"] = None

    analysis, report = _analyse(payload, "TEST-EPS-MULTIPLE-MISSING-EPS")
    assert analysis["eps_multiple_valuation"]["status"] == "INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False
    assert "EPS_MULTIPLE_ADAPTER_NOT_CALCULATED" in analysis["valuation_model_consistency"]["issues"]
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "EPS_MULTIPLE_CALCULATION_NOT_ELIGIBLE" in report


def _b27_eps_bridge_payload(*, declared_eps=None, source_class="EXCHANGE_PRIMARY", project_treatment="NO_PROJECT_INCREMENTAL_ADJUSTMENT", b5_status="NOT_LINKED"):
    payload = _payload(cutoff="2026-10-10")
    raw = payload["eps_multiple_valuation"]
    payload["case"]["currency"] = "CNY"
    for name in ("bear", "base", "bull"):
        eps = raw["scenarios"][name]["eps_per_share"]
        eps["value"] = str((declared_eps or {}).get(name, "10"))
        eps["unit"] = "CNY/share"
        eps["data_class"] = "ISSUER_FORECAST"
        eps["basis"] = "Synthetic declared issuer EPS fixture for bridge unit tests; not real company evidence."
        eps["assumption_derivation"] = ""
        eps["evidence_refs"] = ["E1"]
        eps["earnings_bridge"] = {
            "schema_version": "IIOS-EPS-EARNINGS-BRIDGE-0.1",
            "calculation_method": "B4_NET_PROFIT_PROXY_MINUS_NCI_PLUS_ADJUSTMENTS_DIVIDED_BY_DILUTED_SHARES",
            "forecast_period": raw["forecast_period"],
            "valuation_terminal_date": raw["valuation_terminal_date"],
            "scope": "COMPANY_WIDE",
            "project_profit_treatment": project_treatment,
            "non_controlling_interests_after_tax": {
                "value": "0", "unit": "CNY", "measure": "NON_CONTROLLING_INTERESTS_AFTER_TAX",
                "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic explicit zero for test only.",
                "evidence_refs": [], "forecast_period": raw["forecast_period"], "note": "",
            },
            "other_after_tax_attribution_adjustment": {
                "value": "0", "unit": "CNY", "measure": "OTHER_AFTER_TAX_ATTRIBUTION_ADJUSTMENT",
                "data_class": "ANALYST_ASSUMPTION", "basis": "Synthetic explicit zero adjustment for test only.",
                "evidence_refs": [], "forecast_period": raw["forecast_period"], "note": "",
            },
            "diluted_shares": {
                "value": "1000000", "unit": "shares", "measure": "WEIGHTED_AVERAGE_DILUTED_SHARES",
                "data_class": "ISSUER_FORECAST", "basis": "Synthetic same-period diluted share count for test only.",
                "evidence_refs": ["E1"], "forecast_period": raw["forecast_period"], "note": "",
            },
        }
    return {
        "raw": raw,
        "operating_driver_forecast": {
            "scope": "COMPANY_WIDE",
            "forecast_period": raw["forecast_period"],
            "status": "SCENARIOS_CALCULATED",
            "scenarios": {
                name: {"net_profit_cny": "10000000", "financial_outputs_decision_usable": True}
                for name in ("bear", "base", "bull")
            },
        },
        "valuation_transmission": {"status": b5_status, "scenarios": {}},
        "operator_baseline_includes_project": True if project_treatment == "INCLUDED_IN_COMPANY_WIDE_BASELINE" else False if project_treatment == "EXCLUDED_FROM_COMPANY_WIDE_BASELINE" else None,
        "evidence_register": [{
            "source_id": "E1",
            "source_class": source_class,
            "source_domain_class_status": (
                "OFFICIAL_EXCHANGE_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
                if source_class == "EXCHANGE_PRIMARY"
                else "OFFICIAL_REGULATOR_DOMAIN_CLASS_MATCH_NOT_FORMALLY_ADMITTED"
                if source_class == "REGULATOR_PRIMARY"
                else "SOURCE_CLASS_NOT_PRIMARY"
            ),
            "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
        }],
    }


def _run_b27_eps_bridge(case, unresolved=None):
    return pilot._evaluate_eps_earnings_bridge(
        case["raw"],
        selected_model_family="EPS_MULTIPLE",
        expected_forecast_period=case["raw"]["forecast_period"],
        expected_terminal_date=case["raw"]["valuation_terminal_date"],
        expected_currency="CNY",
        operating_driver_forecast=case["operating_driver_forecast"],
        valuation_transmission=case["valuation_transmission"],
        operator_baseline_includes_project=case["operator_baseline_includes_project"],
        evidence_register=case["evidence_register"],
        unresolved_evidence_ids=unresolved or [],
        after_cutoff_evidence_ids=[],
        uncertain_timing_evidence_ids=[],
    )


def test_b27_issuer_eps_bridge_matches_company_net_profit_proxy_and_diluted_shares():
    case = _b27_eps_bridge_payload()
    bridge = _run_b27_eps_bridge(case)

    assert bridge["status"] == "CALCULATED"
    assert bridge["primary_eps_price_calculation_eligible"] is True
    base = bridge["scenarios"]["base"]
    assert base["status"] == "CALCULATED"
    assert base["net_profit_attributable_to_listed_shareholders"]["arithmetic"] == "10000000 - 0 + (0) = 10000000"
    assert base["arithmetic"] == "10000000 CNY / 1000000 shares = 10 CNY/share"
    assert base["declared_eps_per_share"] == "10"
    assert base["eps_match"] is True
    assert base["formal_evidence_pit_admission"] is False


def test_b27_declared_eps_mismatch_blocks_the_eps_multiple_adapter_without_overwriting():
    case = _b27_eps_bridge_payload(declared_eps={"bear": "10", "base": "10.1", "bull": "10"})
    bridge = _run_b27_eps_bridge(case)

    assert bridge["status"] == "EPS_MISMATCH"
    assert bridge["scenarios"]["base"]["status"] == "EPS_MISMATCH"
    assert bridge["scenarios"]["base"]["declared_eps_per_share"] == "10.1"
    assert bridge["scenarios"]["base"]["calculated_eps_per_share"] == "10"
    adapter = pilot._evaluate_primary_eps_multiple_valuation(
        case["raw"],
        selected_model_family="EPS_MULTIPLE",
        expected_forecast_period=case["raw"]["forecast_period"],
        expected_terminal_date=case["raw"]["valuation_terminal_date"],
        expected_currency="CNY",
        evidence_register=case["evidence_register"],
        eps_earnings_bridge=bridge,
    )
    assert adapter["status"] == "INPUT_INCOMPLETE_OR_INVALID"
    assert any("BASE_EPS_EARNINGS_BRIDGE_NOT_ELIGIBLE:EPS_MISMATCH" in issue for issue in adapter["issues"])


def test_b27_issuer_eps_bridge_fails_closed_on_unverified_source_class_or_domain():
    case = _b27_eps_bridge_payload(source_class="SECONDARY_MEDIA")
    bridge = _run_b27_eps_bridge(case)

    assert bridge["status"] == "NOT_LINKED"
    assert any("ISSUER_FORECAST_SOURCE_CLASS_OR_DOMAIN_NOT_VERIFIED:E1" in issue for issue in bridge["issues"])
    assert bridge["primary_eps_price_calculation_eligible"] is False


def test_b27_project_profit_cannot_be_double_counted_over_an_applied_b5_increment():
    case = _b27_eps_bridge_payload(
        project_treatment="INCLUDED_IN_COMPANY_WIDE_BASELINE",
        b5_status="APPLIED_TO_PER_SHARE_SCENARIOS",
    )
    bridge = _run_b27_eps_bridge(case)

    assert bridge["status"] == "NOT_LINKED"
    assert any("PROJECT_INCREMENTAL_PROFIT_DOUBLE_COUNT_RISK" in issue for issue in bridge["issues"])
    assert bridge["primary_eps_price_calculation_eligible"] is False


def test_b27_eps_bridge_requires_company_wide_b4_scope_and_same_period_diluted_shares():
    case = _b27_eps_bridge_payload()
    case["operating_driver_forecast"]["scope"] = "PROJECT_INCREMENTAL"
    bridge = _run_b27_eps_bridge(case)
    assert bridge["status"] == "NOT_LINKED"
    assert any("EPS_BRIDGE_CANNOT_USE_NON_COMPANY_WIDE_B4:PROJECT_INCREMENTAL" in issue for issue in bridge["issues"])

    case = _b27_eps_bridge_payload()
    case["raw"]["scenarios"]["base"]["eps_per_share"]["earnings_bridge"]["diluted_shares"]["forecast_period"] = "2026FY"
    bridge = _run_b27_eps_bridge(case)
    assert bridge["status"] == "NOT_LINKED"
    assert any("WEIGHTED_AVERAGE_DILUTED_SHARES_FORECAST_PERIOD_MISMATCH" in issue for issue in bridge["issues"])


def test_b27_hkd_eps_without_fx_contract_remains_assumption_only_not_cny_calculation():
    case = _b27_eps_bridge_payload()
    raw = case["raw"]
    for name in ("bear", "base", "bull"):
        eps = raw["scenarios"][name]["eps_per_share"]
        eps["unit"] = "HKD/share"
        eps["data_class"] = "ANALYST_ASSUMPTION"
        eps["basis"] = "Synthetic HKD analyst scenario assumption."
        eps["assumption_derivation"] = "A disclosed hypothetical EPS path in HKD; no CNY-to-HKD conversion is asserted."
        eps["evidence_refs"] = []
        eps["earnings_bridge"] = None

    bridge = pilot._evaluate_eps_earnings_bridge(
        raw,
        selected_model_family="EPS_MULTIPLE",
        expected_forecast_period=raw["forecast_period"],
        expected_terminal_date=raw["valuation_terminal_date"],
        expected_currency="HKD",
        operating_driver_forecast=case["operating_driver_forecast"],
        valuation_transmission=case["valuation_transmission"],
        operator_baseline_includes_project=None,
        evidence_register=[],
    )
    assert bridge["status"] == "ASSUMPTION_ONLY"
    assert bridge["primary_eps_price_calculation_eligible"] is True
    assert bridge["scenarios"]["base"]["status"] == "ASSUMPTION_ONLY"
    assert "FX" in bridge["scenarios"]["base"]["note"]


def test_b27_eps_multiple_adapter_rejects_issuer_pe_with_unverified_source_domain():
    case = _b27_eps_bridge_payload()
    bridge = _run_b27_eps_bridge(case)
    assert bridge["status"] == "CALCULATED"

    case["raw"]["scenarios"]["base"]["pe_multiple_x"]["data_class"] = "ISSUER_FORECAST"
    case["raw"]["scenarios"]["base"]["pe_multiple_x"]["evidence_refs"] = ["E2"]
    case["evidence_register"].append({
        "source_id": "E2",
        "source_class": "SECONDARY_MEDIA",
        "source_domain_class_status": "SOURCE_CLASS_NOT_PRIMARY",
        "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED",
    })
    adapter = pilot._evaluate_primary_eps_multiple_valuation(
        case["raw"],
        selected_model_family="EPS_MULTIPLE",
        expected_forecast_period=case["raw"]["forecast_period"],
        expected_terminal_date=case["raw"]["valuation_terminal_date"],
        expected_currency="CNY",
        evidence_register=case["evidence_register"],
        eps_earnings_bridge=bridge,
    )
    assert adapter["status"] == "INPUT_INCOMPLETE_OR_INVALID"
    assert any("BASE_PE_MULTIPLE_X_ISSUER_FORECAST_SOURCE_CLASS_OR_DOMAIN_NOT_VERIFIED:E2" in issue for issue in adapter["issues"])


def test_b27_missing_issuer_bridge_blocks_primary_eps_price_path():
    payload = _payload()
    for name in ("bear", "base", "bull"):
        eps = payload["eps_multiple_valuation"]["scenarios"][name]["eps_per_share"]
        eps["data_class"] = "ISSUER_FORECAST"
        eps["evidence_refs"] = ["E1"]
        eps["earnings_bridge"] = None

    analysis, report = _analyse(payload, "TEST-B27-ISSUER-EPS-BRIDGE-MISSING")

    assert analysis["eps_earnings_bridge"]["status"] == "NOT_LINKED"
    assert analysis["eps_multiple_valuation"]["status"] == "INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert "ISSUER_FORECAST_EARNINGS_BRIDGE_REQUIRED" in report


def test_sotp_adapter_computes_segment_values_parent_adjustments_and_per_share_value():
    from iios_mvp.sotp_valuation_v01 import evaluate_sotp_valuation

    payload = _sotp_ready_payload()
    raw = payload["sotp_valuation"]
    evidence = [
        {"source_id": "E1", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
        {"source_id": "E2", "time_status": "PIT_TIME_COMPATIBLE_ONLY_NOT_ADMITTED"},
    ]
    result = evaluate_sotp_valuation(
        raw,
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        expected_currency="CNY",
        evidence_register=evidence,
    )

    assert result["status"] == "CALCULATED"
    assert result["formal_valuation_admission_created"] is False
    bear = result["scenarios"]["bear"]
    assert Decimal(bear["segments"][0]["segment_equity_value_cny"]) == Decimal("32000000000")
    assert Decimal(bear["segment_equity_value_cny"]) == Decimal("50000000000")
    assert Decimal(bear["parent_level_adjustments"]["capitalized_central_cost_value_cny"]) == Decimal("1600000000")
    assert Decimal(bear["total_equity_value_cny"]) == Decimal("50400000000")
    assert Decimal(bear["terminal_value_per_share"]) == Decimal("50.4")
    assert Decimal(result["scenarios"]["base"]["terminal_value_per_share"]) == Decimal("80")
    assert Decimal(result["scenarios"]["bull"]["terminal_value_per_share"]) == Decimal("113.6")




def test_sotp_adapter_requires_explicit_case_currency():
    from iios_mvp.sotp_valuation_v01 import evaluate_sotp_valuation

    payload = _sotp_ready_payload()
    result = evaluate_sotp_valuation(
        payload["sotp_valuation"],
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        evidence_register=[],
    )

    assert result["status"] == "SOTP_CURRENCY_NOT_SUPPORTED"
    assert result["scenarios"] == {}
    assert "SOTP_CASE_CURRENCY_NOT_CNY:UNKNOWN" in result["issues"]
    assert result["formal_valuation_admission_created"] is False
    assert result["decision_authority"] is False


def test_sotp_v01_rejects_non_cny_case_currency_without_fx_conversion():
    from iios_mvp.sotp_valuation_v01 import evaluate_sotp_valuation

    payload = _sotp_ready_payload()
    result = evaluate_sotp_valuation(
        payload["sotp_valuation"],
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        evidence_register=[],
        expected_currency="HKD",
    )

    assert result["status"] == "SOTP_CURRENCY_NOT_SUPPORTED"
    assert result["scenarios"] == {}
    assert "SOTP_V0_1_CNY_ONLY" in result["issues"]
    assert result["formal_valuation_admission_created"] is False
    assert result["decision_authority"] is False


def test_hkd_case_cannot_apply_cny_sotp_to_hkd_return_or_entry_price():
    payload = _sotp_ready_payload()
    payload["case"].update({
        "company": "Synthetic HK issuer",
        "market": "HK",
        "symbol": "0700",
        "currency": "HKD",
    })
    payload["price_input"].update({"price": "300", "currency": "HKD"})
    # Keep source locators synthetic: this test exercises currency isolation, not admission.
    analysis, report = _analyse(payload, "TEST-HKD-SOTP-CURRENCY-BLOCK")

    assert analysis["case"]["currency"] == "HKD"
    assert analysis["sotp_valuation"]["status"] == "SOTP_CURRENCY_NOT_SUPPORTED"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert all(row["status"] == "UNKNOWN" for row in analysis["price_zone_sensitivity"]["sensitivity_ladder"])
    assert "不得把 CNY/股重标为其他币种" in report
    assert "币种边界：v0.1 输入字段和计算值固定为 CNY" in report


def test_sotp_primary_calculation_overrides_draft_per_share_values_and_closes_price_math():
    payload = _sotp_ready_payload()
    original_draft_terminals = {
        name: row["terminal_value_per_share"]
        for name, row in payload["forecast_valuation"]["scenarios"].items()
    }
    analysis, report = _analyse(payload, "TEST-SOTP-PRIMARY-VALUATION")

    assert analysis["sotp_valuation"]["status"] == "CALCULATED"
    assert analysis["valuation_model_consistency"]["operator_selected_model_family"] == "SOTP"
    assert analysis["valuation_model_consistency"]["calculation_model_family"] == "SOTP"
    assert analysis["valuation_model_consistency"]["sotp_calculation_status"] == "CALCULATED"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is True
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "80"
    for name, expected in (("bear", "50.4"), ("base", "80"), ("bull", "113.6")):
        row = analysis["forecast_valuation"]["scenarios"][name]
        assert row["declared_terminal_value_before_sotp_calculation"] == original_draft_terminals[name]
        assert Decimal(row["terminal_value_per_share"]) == Decimal(expected)
        assert row["sotp_calculation_applied"] is True
    assert analysis["return_metrics"] is not None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is not None
    assert "SOTP：分部估值到每股终值的计算链" in report
    assert "Σ（已归属于上市公司股东的分部净利润 × 分部 P/E）" in report
    assert "SOTP 每股终值：80 CNY" in report
    assert "减资本化母公司税后成本与少数股东权益" not in report
    assert "未扣除未分配母公司层面税后成本的分部净利润" in report
    assert "B5 的 EPS_MULTIPLE 增量适配器不能用于 SOTP" in report
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


def test_sotp_missing_segment_inputs_block_return_entry_price_and_b6_without_eps_fallback():
    payload = _sotp_ready_payload()
    payload["sotp_valuation"]["scenarios"]["base"]["segments"] = []

    analysis, report = _analyse(payload, "TEST-SOTP-MISSING-SEGMENT-INPUT")
    assert analysis["sotp_valuation"]["status"] == "SOTP_INPUT_INCOMPLETE_OR_INVALID"
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False
    assert analysis["valuation_model_consistency"]["status"] == "SOTP_CALCULATION_NOT_ELIGIBLE"
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert all(row["status"] == "UNKNOWN" for row in analysis["price_zone_sensitivity"]["sensitivity_ladder"])
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "SOTP_CALCULATION_NOT_ELIGIBLE" in report
    assert "不进入预期回报、目标入场价或 B6 价格敏感性计算" in report


def test_sotp_requires_same_segment_universe_and_valid_typed_evidence():
    from iios_mvp.sotp_valuation_v01 import evaluate_sotp_valuation

    payload = _sotp_ready_payload()
    raw = payload["sotp_valuation"]
    raw["scenarios"]["bull"]["segments"].pop()
    result = evaluate_sotp_valuation(
        raw,
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        expected_currency="CNY",
        evidence_register=[],
    )
    assert result["status"] == "SOTP_SEGMENT_UNIVERSE_MISMATCH"

    payload = _sotp_ready_payload()
    raw = payload["sotp_valuation"]
    raw["scenarios"]["base"]["segments"][0]["attributable_net_profit_cny"] = _sotp_measure(
        "5000000000", "CNY", data_class="ISSUER_FORECAST", refs=[],
        basis="Synthetic issuer-forecast field intentionally missing a source reference",
    )
    result = evaluate_sotp_valuation(
        raw,
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        expected_currency="CNY",
        evidence_register=[],
    )
    assert result["status"] == "SOTP_INPUT_INCOMPLETE_OR_INVALID"
    assert "ISSUER_FORECAST_EVIDENCE_REQUIRED" in result["issues"][0]


def test_sotp_selected_without_adapter_blocks_even_when_draft_claims_sotp():
    payload = _payload()
    payload["operator_valuation_context"]["selected_model_family"] = "SOTP"
    payload["sotp_valuation"] = None
    payload["forecast_valuation"]["model"] = "SOTP"
    payload["forecast_valuation"]["model_family"] = "SOTP"
    payload["forecast_valuation"]["model_rationale"] = "A synthetic SOTP claim without segment calculations."
    analysis, _report = _analyse(payload, "TEST-SOTP-NO-ADAPTER")
    assert analysis["sotp_valuation"]["status"] == "SOTP_INPUT_MISSING"
    assert analysis["return_metrics"] is None
    assert analysis["price_zone_sensitivity"]["target_entry_price"] is None
    assert analysis["valuation_model_consistency"]["primary_model_price_calculation_eligible"] is False


def test_sotp_candidate_is_not_applied_when_operator_selects_another_model():
    payload = _sotp_ready_payload()
    payload["operator_valuation_context"] = {
        "selected_model_family": "EPS_MULTIPLE",
        "baseline_includes_project": None,
        "input_owner": "OPERATOR",
    }
    analysis, _report = _analyse(payload, "TEST-SOTP-NOT-SELECTED")

    assert analysis["sotp_valuation"]["status"] == "NOT_SELECTED"
    assert analysis["forecast_valuation"]["model_family"] == "EPS_MULTIPLE"
    assert analysis["forecast_valuation"]["entry_value_reference_per_share"] == "150"
    assert analysis["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] == "150"
    assert analysis["return_metrics"] is not None


def test_sotp_rejects_separate_minority_adjustment_with_attributable_segment_profit():
    from iios_mvp.sotp_valuation_v01 import evaluate_sotp_valuation

    payload = _sotp_ready_payload()
    payload["sotp_valuation"]["scenarios"]["base"]["parent_level_adjustments"]["minority_interests_cny"] = _sotp_measure(
        "1000000000", "CNY", basis="Deliberately overlapping minority interest value."
    )
    result = evaluate_sotp_valuation(
        payload["sotp_valuation"],
        selected_model_family="SOTP",
        expected_forecast_period="2027FY",
        expected_terminal_date="2027-12-31",
        expected_currency="CNY",
        evidence_register=[],
    )

    assert result["status"] == "SOTP_INPUT_INCOMPLETE_OR_INVALID"
    assert any(
        "SEPARATE_MINORITY_INTERESTS_ADJUSTMENT_CONFLICTS_WITH_ATTRIBUTABLE_SEGMENT_PROFIT" in issue
        for issue in result["issues"]
    )
