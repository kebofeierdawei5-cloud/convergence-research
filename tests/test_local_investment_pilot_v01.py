from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import subprocess

import pytest

from iios_mvp.local_investment_pilot_v01 import (
    LocalInvestmentPilotError,
    PILOT_SCHEMA,
    _normalize_guided_symbol,
    _previous_weekday,
    _read_json_response_file,
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
            "model_rationale": "synthetic test only",
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
        "",
    ])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))

    def completed_response(_response_path):
        template_paths = list((tmp_path / "inputs").glob("pilot-input-*.json"))
        assert len(template_paths) == 1
        template = json.loads(template_paths[0].read_text(encoding="utf-8"))
        canned = _payload(cutoff="2026-10-12")
        for key in ("evidence_register", "assessment", "forecast_valuation", "decision_parameters", "notes"):
            template[key] = canned[key]
        return template

    monkeypatch.setattr(pilot, "_read_json_response_file", completed_response)
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
    assert analysis["return_metrics"]["target_entry_price"] == "130.4347826086956521739130435"
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


def test_extract_json_object_blocks_incomplete_clipboard_response():
    from iios_mvp.local_investment_pilot_v01 import _extract_json_object

    fence = chr(96) * 3
    source = fence + 'json\n{"schema_version": '
    with pytest.raises(LocalInvestmentPilotError, match="CHATGPT_JSON_INVALID"):
        _extract_json_object(source)


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

