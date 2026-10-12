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
    _validate_guided_observation_date,
    run_guided_wizard,
    run_local_investment_pilot,
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
                "bear": {"probability": "0.20", "terminal_value_per_share": "120", "cash_distributions_per_share": "0", "rationale": "synthetic bear"},
                "base": {"probability": "0.50", "terminal_value_per_share": "150", "cash_distributions_per_share": "0", "rationale": "synthetic base"},
                "bull": {"probability": "0.30", "terminal_value_per_share": "180", "cash_distributions_per_share": "0", "rationale": "synthetic bull"},
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
    assert "1. **growth A**" in report
    assert "2. **growth B**" in report
    assert "{'assumption_id':" not in report
    assert analysis["unresolved_evidence_references"] == ["E-MISSING", "E1"]


def test_guided_observation_date_must_precede_date_only_cutoff():
    from datetime import date
    cutoff = date(2026, 10, 12)
    assert _validate_guided_observation_date(date(2026, 10, 9), cutoff) == date(2026, 10, 9)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF"):
        _validate_guided_observation_date(cutoff, cutoff)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_OBSERVATION_MUST_PRECEDE_DATE_ONLY_CUTOFF"):
        _validate_guided_observation_date(date(2026, 10, 13), cutoff)


def test_guided_wizard_reprompts_same_day_price_before_confirming(tmp_path, monkeypatch, capsys):
    import builtins

    answers = iter([
        "山东赫达",
        "SZ002810",
        "1",
        "2026-10-12",
        "",
        "0",
        "19.74",
        "2026-10-12",
        "2026-10-09",
        "",
        "人工输入",
        "0",
    ])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))
    result = run_guided_wizard(
        template_root=tmp_path / "inputs",
        output_root=tmp_path / "runs",
    )
    output = capsys.readouterr().out
    assert result["status"] == "CANCELLED"
    assert "价格日期/时点不符合当前 PIT 规则" in output
    assert "请重新输入" in output
    assert "观察日 2026-10-09" in output
    assert not (tmp_path / "inputs").exists()


def test_candidate_driven_pilot_uses_existing_return_solver_and_outputs_chinese_report(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_local_investment_pilot(input_path=input_path, output_root=tmp_path / "private-runs")
    assert result["status"] == "PILOT_CREATED"
    bundle = Path(result["run_dir"])
    analysis = json.loads((bundle / "analysis.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")
    assert analysis["status"] == "PILOT_NON_CANONICAL"
    assert analysis["decision"]["provisional_action"] == "BUY"
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
    assert analysis["decision"]["provisional_action"] == "NO-BUY"


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
    assert replay["status"] == "PILOT_REPLAY_RECOMPUTED"
    assert replay["replay_of"] == first["pilot_id"]
    assert replay_analysis["return_metrics"] == first_analysis["return_metrics"]
    assert replay_analysis["decision"]["provisional_action"] == first_analysis["decision"]["provisional_action"]


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
