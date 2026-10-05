import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.company_evidence_quality_integration import (
    COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION,
    integrate_company_evidence_into_quality,
    validate_company_evidence_quality_integration,
)

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "RC-CN-A-300750-20261004"
CUTOFF = "2026-10-04"


def _real_core02_inputs():
    payload = json.loads(
        (
            ROOT
            / "examples/real_cases/RC-CN-A-300750-20261004_core03_input.json"
        ).read_text(encoding="utf-8")
    )
    return payload["core02_input"]["quality"], payload["core02_input"]["trust"]


def _bridges(*, roic_status="CONDITIONAL", interpretation="CONDITIONAL", capital_status="CONDITIONAL"):
    economic = {
        "schema_version": "IIOS-COMPANY-ECONOMIC-BRIDGE-0.1",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF,
        "interpretation_status": interpretation,
        "incremental_roic": {
            "status": roic_status,
            "value": None if roic_status == "UNKNOWN" else 0.857,
            "basis": "fixture",
            "reason": "fixture",
        },
        "periods": {
            "prior": {"evidence_ids": ["E005", "E012_A1"]},
            "current": {"evidence_ids": ["E005", "E010", "E013_A1"]},
        },
    }
    capital = {
        "schema_version": "IIOS-COMPANY-CAPITAL-TRUST-BRIDGE-0.1",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF,
        "evidence_admission": {
            "status": "ADMITTED",
            "evidence_ids": ["E014_A1", "E015_A1", "E016_A1", "E017_A1"],
        },
        "capital_allocation": {"status": capital_status},
        "trust_revalidation": {
            "status": "CONDITIONAL",
            "governance_integrity": {"status": "CONDITIONAL"},
            "shareholder_treatment": {"status": "PASS"},
        },
    }
    return economic, capital


def test_real_300750_evidence_closes_roic_unknown_but_not_to_pass():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges()

    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )

    assert result["schema_version"] == COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION

    quality_by_dim = {
        row["dimension"]: row for row in result["quality"]["dimensions"]
    }
    assert quality_by_dim["incremental_return_on_capital"]["status"] == "CONDITIONAL"
    assert quality_by_dim["cash_flow_conversion"]["status"] == "CONDITIONAL"
    assert quality_by_dim["reinvestment_runway"]["status"] == "CONDITIONAL"
    assert quality_by_dim["balance_sheet_resilience"]["status"] == "PASS"

    assert result["quality_gate"]["status"] == "CONDITIONAL"
    assert result["quality_gate"]["capital_admission_pass"] is False

    trust_by_dim = {row["dimension"]: row for row in result["trust"]["dimensions"]}
    assert trust_by_dim["governance_integrity"]["status"] == "CONDITIONAL"
    assert trust_by_dim["shareholder_treatment"]["status"] == "CONDITIONAL"
    assert result["trust"]["status"] == "CONDITIONAL"
    assert result["decision_effect"] == "NO_DIRECT_GATE_EFFECT"

    validate_company_evidence_quality_integration(
        result,
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
    )


def test_evidence_closes_missing_unknown_but_does_not_upgrade_known_conditional():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges(
        roic_status="PASS",
        interpretation="PASS",
        capital_status="PASS",
    )
    quality["dimensions"] = [
        dict(row) if row["dimension"] != "incremental_return_on_capital"
        else {**row, "status": "UNKNOWN"}
        for row in quality["dimensions"]
    ]
    trust["dimensions"] = [
        dict(row) if row["dimension"] != "governance_integrity"
        else {**row, "status": "UNKNOWN"}
        for row in trust["dimensions"]
    ]

    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )

    q = {row["dimension"]: row["status"] for row in result["quality"]["dimensions"]}
    t = {row["dimension"]: row["status"] for row in result["trust"]["dimensions"]}
    assert q["incremental_return_on_capital"] == "PASS"
    assert t["governance_integrity"] == "PASS"

    quality, trust = _real_core02_inputs()
    economic, capital = _bridges(
        roic_status="PASS",
        interpretation="PASS",
        capital_status="PASS",
    )
    quality["dimensions"] = [
        dict(row) if row["dimension"] != "cash_flow_conversion"
        else {**row, "status": "CONDITIONAL"}
        for row in quality["dimensions"]
    ]
    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )
    q = {row["dimension"]: row["status"] for row in result["quality"]["dimensions"]}
    assert q["cash_flow_conversion"] == "CONDITIONAL"


def test_blocked_evidence_caps_the_affected_quality_dimension_only():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges(roic_status="BLOCKED")
    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )
    q = {row["dimension"]: row["status"] for row in result["quality"]["dimensions"]}
    assert q["incremental_return_on_capital"] == "BLOCKED"
    assert q["cash_flow_conversion"] == "CONDITIONAL"
    assert result["quality_gate"]["status"] == "BLOCKED"


def test_bridge_case_or_cutoff_mismatch_fails_closed():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges()
    economic["case_id"] = "OTHER"
    with pytest.raises(ValueError, match="case_id mismatch"):
        integrate_company_evidence_into_quality(
            case_id=CASE_ID,
            cutoff_date=CUTOFF,
            quality=quality,
            trust=trust,
            economic_bridge=economic,
            capital_trust_bridge=capital,
        )

    economic, capital = _bridges()
    capital["cutoff_date"] = "2026-10-05"
    with pytest.raises(ValueError, match="cutoff_date mismatch"):
        integrate_company_evidence_into_quality(
            case_id=CASE_ID,
            cutoff_date=CUTOFF,
            quality=quality,
            trust=trust,
            economic_bridge=economic,
            capital_trust_bridge=capital,
        )


def test_duplicate_quality_or_trust_dimensions_fail_closed():
    quality, trust = _real_core02_inputs()
    quality["dimensions"] = quality["dimensions"] + [dict(quality["dimensions"][0])]
    economic, capital = _bridges()
    with pytest.raises(ValueError, match="cardinality"):
        integrate_company_evidence_into_quality(
            case_id=CASE_ID,
            cutoff_date=CUTOFF,
            quality=quality,
            trust=trust,
            economic_bridge=economic,
            capital_trust_bridge=capital,
        )


def test_audit_hash_tampering_is_detected():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges()
    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )
    result["quality"]["dimensions"][0]["rationale"] += " tampered"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_company_evidence_quality_integration(
            result,
            case_id=CASE_ID,
            cutoff_date=CUTOFF,
        )


def test_schema_accepts_real_300750_integration_result():
    quality, trust = _real_core02_inputs()
    economic, capital = _bridges()
    result = integrate_company_evidence_into_quality(
        case_id=CASE_ID,
        cutoff_date=CUTOFF,
        quality=quality,
        trust=trust,
        economic_bridge=economic,
        capital_trust_bridge=capital,
    )
    schema = json.loads(
        (
            ROOT
            / "schemas/company_evidence_quality_integration_v0.1.schema.json"
        ).read_text(encoding="utf-8")
    )
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result)
    )
    assert errors == []
