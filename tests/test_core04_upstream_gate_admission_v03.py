from iios_mvp.decision_upstream_admission_v03 import (
    DECISION_UPSTREAM_ADMISSION_VERSION,
    build_decision_upstream_admission,
    validate_decision_upstream_admission,
)
from iios_mvp.quality_gate_v03 import build_quality_gate
from iios_mvp.thesis_admission_v03 import admit_thesis


CASE_ID = "V03-001"
CUTOFF = "2026-10-04"

QUALITY = {
    "dimensions": [
        {"dimension": "competitive_advantage", "status": "PASS", "rationale": "r", "evidence_ids": ["e1"]},
        {"dimension": "incremental_return_on_capital", "status": "CONDITIONAL", "rationale": "r", "evidence_ids": ["e2"]},
        {"dimension": "earnings_quality", "status": "PASS", "rationale": "r", "evidence_ids": ["e3"]},
        {"dimension": "cash_flow_conversion", "status": "PASS", "rationale": "r", "evidence_ids": ["e3"]},
        {"dimension": "balance_sheet_resilience", "status": "PASS", "rationale": "r", "evidence_ids": ["e4"]},
        {"dimension": "reinvestment_runway", "status": "PASS", "rationale": "r", "evidence_ids": ["e5"]},
    ]
}

THESIS = {
    "status": "INTACT",
    "statement": "The operating platform can convert scale, unit economics and reinvestment into durable economic profit.",
    "mechanism": "Volume and mix drive margins and FCF; disciplined reinvestment must generate adequate incremental ROIC.",
    "key_driver_ids": ["D1", "D2", "D3"],
    "falsifiers": ["persistent margin deterioration", "incremental ROIC below required return", "structural FCF conversion failure"],
    "monitoring_triggers": ["quarterly margin", "FCF conversion", "incremental ROIC"],
    "evidence_ids": ["e1", "e2", "e3", "e4", "e5"],
    "known_at": "2026-10-04T12:00:00+00:00",
    "prepared_without_current_price": True,
}


def test_quality_gate_is_strict_for_capital_admission():
    q = build_quality_gate(QUALITY, case_id=CASE_ID, cutoff_date=CUTOFF)
    assert q["status"] == "CONDITIONAL"
    assert q["capital_admission_pass"] is False
    assert "incremental_return_on_capital" in q["blocking_dimensions"]


def test_thesis_admission_is_structural_not_a_hidden_buy_signal():
    t = admit_thesis(THESIS, case_id=CASE_ID, cutoff_date=CUTOFF)
    assert t["admission_status"] == "ADMITTED"
    assert t["status"] == "INTACT"
    assert t["prepared_without_current_price"] is True


def test_upstream_bundle_requires_all_core_domains_for_capital_readiness():
    bundle = build_decision_upstream_admission(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        reality_status="PASS",
        quality=QUALITY,
        value_driver_status="PASS",
        valuation_status="PASS",
        forecast_status="PASS",
        thesis=THESIS,
    )
    assert bundle["schema_version"] == DECISION_UPSTREAM_ADMISSION_VERSION
    assert bundle["quality_gate_status"] == "CONDITIONAL"
    assert bundle["thesis_admission_status"] == "ADMITTED"
    assert bundle["capital_admission_ready"] is False
    validate_decision_upstream_admission(bundle, case_id=CASE_ID, cutoff_date=CUTOFF)


def test_thesis_known_after_cutoff_is_rejected():
    bad = dict(THESIS)
    bad["known_at"] = "2026-10-05T00:00:00+00:00"
    try:
        admit_thesis(bad, case_id=CASE_ID, cutoff_date=CUTOFF)
    except ValueError as exc:
        assert "after cutoff" in str(exc)
    else:
        raise AssertionError("expected PIT thesis admission failure")
