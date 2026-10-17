from __future__ import annotations

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
                "source_class": "ISSUER_PRIMARY",
                "source_ref": "https://example.invalid/h1.pdf",
                "published_at": "2026-08-30",
                "known_at": "2026-08-30",
                "summary": "Synthetic test source; not real evidence.",
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
                {"rank": 1, "driver": "volume growth", "impact": "POSITIVE", "rationale": "synthetic", "evidence_refs": ["E1"]}
            ],
            "market_implied_expectation": {"status": "PASS", "summary": "synthetic test only", "evidence_refs": ["E1"]},
            "expectation_gap": {
                "status": "PASS",
                "direction": "POSITIVE",
                "summary": "synthetic test gap",
                "evidence_refs": ["E1"],
            },
            "risk": {"status": "PASS", "summary": "synthetic risk", "max_loss_pct": "25", "items": ["synthetic downside"]},
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
    assert prepared["referenced_evidence_ids"] == ["E-ASSUMPTION-MISSING", "E-RISK-MISSING", "E1"]
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
    assert analysis["unresolved_evidence_references"] == ["E-MISSING", "E1"]


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


def test_thesis_break_stress_is_not_probability_weighted_and_missing_stress_gates_action():
    payload = _payload()
    analysis, report = _analyse(payload, "TEST-STRESS")

    assert analysis["thesis_break_stress_review"]["status"] == "PASS"
    assert analysis["thesis_break_stress_review"]["probability_weighted"] is False
    assert str(analysis["thesis_break_stress_review"]["stress_terminal_wealth"]) == "80"
    assert str(analysis["thesis_break_stress_review"]["stress_total_return"]) == "-0.2"
    assert analysis["return_metrics"]["expected_terminal_wealth"] != analysis["thesis_break_stress_review"]["stress_terminal_wealth"]
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
    analysis, report = _analyse(payload, "TEST-SCENARIO-ORDER")
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "SCENARIO_WEALTH_ORDERING_INCONSISTENT"
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "SCENARIO_WEALTH_ORDERING_INCONSISTENT" in analysis["decision"]["gating_issues"]



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


def test_extract_json_object_blocks_incomplete_clipboard_response():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    fence = chr(96) * 3
    source = fence + 'json\n{"schema_version": '
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID"):
        _extract_json_object(source)


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
    return payload


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



def test_operator_selected_sotp_blocks_eps_multiple_price_calculation():
    payload = _b5_ready_payload()
    payload["operator_valuation_context"]["selected_model_family"] = "SOTP"
    analysis, report = _analyse(payload, "TEST-PRIMARY-MODEL-MISMATCH")

    contract = analysis["valuation_model_consistency"]
    assert contract["status"] == "MODEL_FAMILY_MISMATCH"
    assert contract["operator_selected_model_family"] == "SOTP"
    assert contract["calculation_model_family"] == "EPS_MULTIPLE"
    assert contract["primary_model_price_calculation_eligible"] is False
    assert contract["scenario_values_role"] == "ALTERNATIVE_OR_UNRESOLVED_ONLY"
    assert analysis["return_metrics"] is None
    assert analysis["return_metrics_reason"] == "PRIMARY_VALUATION_MODEL_NOT_ELIGIBLE:MODEL_FAMILY_MISMATCH"
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
    assert forged_contract["status"] == "CALCULATION_MODEL_NAME_FAMILY_MISMATCH"
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
    assert "- 每股现金分配：UNKNOWN CNY" in report
    assert "每股现金分配：None CNY" not in report


def test_null_valuation_fields_render_as_unknown_in_json_report_sections():
    payload = _b5_ready_payload()
    payload["forecast_valuation"]["scenarios"]["bear"]["probability"] = None
    payload["forecast_valuation"]["scenarios"]["bear"]["terminal_value_per_share"] = None

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
