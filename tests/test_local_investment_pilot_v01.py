from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from iios_mvp.local_investment_pilot_v01 import (
    LocalInvestmentPilotError,
    PILOT_SCHEMA,
    create_pilot_template,
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
            "probability_calibration_basis": "",
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
    path.chmod(0o600)
    return path


def test_candidate_driven_pilot_uses_existing_return_solver_and_outputs_chinese_report(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_local_investment_pilot(input_path=input_path, output_root=tmp_path / "private-runs")
    assert result["status"] == "PILOT_CREATED"
    assert result["replay_status"] == "PILOT_REPLAY_PASS"
    bundle = Path(result["run_dir"])
    analysis = json.loads((bundle / "analysis.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")
    assert analysis["status"] == "PILOT_NON_CANONICAL"
    assert analysis["decision"]["provisional_action"] == "BUY"
    assert analysis["return_metrics"]["fundamental_target_pass"] is True
    assert analysis["return_metrics"]["target_entry_price"] == "130.4347826086956521739130435"
    assert "PILOT_NON_CANONICAL" in report
    assert "人工价格" in report
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


def test_unknown_mie_keeps_final_pilot_action_at_review_required(tmp_path):
    payload = _payload()
    payload["assessment"]["market_implied_expectation"]["status"] = "NOT_IDENTIFIABLE"
    payload["assessment"]["expectation_gap"]["status"] = "UNKNOWN"
    payload["assessment"]["expectation_gap"]["direction"] = "UNKNOWN"
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["return_metrics"]["fundamental_target_pass"] is True
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "MIE_STATUS_NOT_IDENTIFIABLE" in analysis["decision"]["gating_issues"]


def test_quote_after_date_only_cutoff_is_not_used_for_price_math(tmp_path):
    payload = _payload(cutoff="2026-10-09")
    payload["price_input"]["observation_date"] = "2026-10-09"
    payload["price_input"]["known_at"] = "2026-10-09T15:00:00+08:00"
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["price_input"]["pit_time_status"] == "PRICE_NOT_PIT_QUALIFIED"
    assert analysis["return_metrics"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"


def test_incomplete_valuation_still_produces_useful_review_report_without_inventing_returns(tmp_path):
    payload = _payload()
    payload["forecast_valuation"]["entry_value_reference_per_share"] = None
    payload["forecast_valuation"]["scenarios"]["base"]["terminal_value_per_share"] = None
    result = run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")
    analysis = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    report = (Path(result["run_dir"]) / "report.md").read_text(encoding="utf-8")
    assert analysis["return_metrics"] is None
    assert analysis["decision"]["provisional_action"] == "REVIEW_REQUIRED"
    assert "MODEL_INPUTS" in report or "计算未完成" in report or "参考价值" in report


def test_replay_recomputes_output_and_reuses_identical_input(tmp_path):
    input_path = _write_input(tmp_path)
    output_root = tmp_path / "private-runs"
    first = run_local_investment_pilot(input_path=input_path, output_root=output_root)
    replay = verify_local_pilot_bundle(first["run_dir"])
    second = run_local_investment_pilot(input_path=input_path, output_root=output_root)
    assert replay["status"] == "PILOT_REPLAY_PASS"
    assert second["status"] == "PILOT_REUSED_IDENTICAL_INPUT"
    assert second["pilot_id"] == first["pilot_id"]


def test_manual_price_cannot_be_relabelled_as_source_verified(tmp_path):
    payload = _payload()
    payload["price_input"]["assurance_label"] = "CANONICAL_PRICE_ADMISSION_VERIFIED"
    path = _write_input(tmp_path, payload)
    with pytest.raises(LocalInvestmentPilotError, match="PRICE_ASSURANCE_MUST_REMAIN"):
        run_local_investment_pilot(input_path=path, output_root=tmp_path / "private-runs")


def test_three_year_horizon_requires_explicit_allowed_override(tmp_path):
    payload = _payload()
    payload["decision_parameters"]["horizon_years"] = 3
    with pytest.raises(LocalInvestmentPilotError, match="THREE_YEAR_HORIZON_REQUIRES"):
        run_local_investment_pilot(input_path=_write_input(tmp_path, payload), output_root=tmp_path / "private-runs")


def test_pilot_output_is_private_and_receipt_never_claims_canonical_authority(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_local_investment_pilot(input_path=input_path, output_root=tmp_path / "private-runs")
    root = Path(result["run_dir"])
    receipt = json.loads((root / "pilot_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PILOT_NON_CANONICAL"
    assert receipt["formal_decision_created"] is False
    assert receipt["canonical_run_receipt_created"] is False
    assert receipt["source_origin_verified"] is False
    assert receipt["auto_execution"] is False
    if os.name != "nt":
        import stat
        assert stat.S_IMODE(root.stat().st_mode) & 0o077 == 0
        for name in ("input.json", "analysis.json", "report.md", "pilot_receipt.json"):
            assert stat.S_IMODE((root / name).stat().st_mode) & 0o077 == 0
