import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from calc.company_capital_trust_bridge import (
    CAPITAL_TRUST_BRIDGE_VERSION,
    build_company_capital_trust_bridge,
    validate_company_capital_trust_bridge,
)

ROOT = Path(__file__).resolve().parents[1]

ADMITTED = ["E014_A1", "E015_A1", "E016_A1", "E017_A1"]

CATL_INPUT = {
    "observation_date": "2026-09-30",
    "annual_2025_attributable_net_income": 72_201_282,
    "annual_2025_cash_dividend_total": 36_100_640.88392,
    "annual_2025_repurchased_shares": 31_982_306,
    "h1_2026_attributable_net_income": 43_284_002,
    "h1_2026_interim_cash_dividend": 6_492_600.30764,
    "h1_2026_total_shares": 4_626_654_919,
    "h1_2026_repurchase_account_shares": 28_319_044,
    "indonesia_planned_investment_usd": 5_968_000_000,
    "related_party_guarantee_cap_usd": 130_000_000,
    "related_party_procurement_cap_usd": 320_000_000,
    "independent_director_review": True,
    "related_director_recusal": True,
    "non_related_director_for_votes": 8,
    "non_related_director_against_votes": 0,
    "non_related_director_abstain_votes": 0,
    "evidence_ids": ADMITTED,
}


def _build(**overrides):
    payload = dict(CATL_INPUT)
    payload.update(overrides)
    return build_company_capital_trust_bridge(
        case_id="RC-CN-A-300750-20261004",
        cutoff_date="2026-10-04T23:59:59+08:00",
        input_payload=payload,
        admitted_evidence_ids=ADMITTED,
        generation_basis="Official CATL 2025 annual report, 2026 H1 report, and 2026-09-30 related-party announcements.",
    )


def test_catl_capital_and_trust_bridge_is_deterministic_and_auditable():
    result = _build()
    assert result["schema_version"] == CAPITAL_TRUST_BRIDGE_VERSION
    assert result["capital_allocation"]["status"] == "CONDITIONAL"
    assert result["trust_revalidation"]["status"] == "CONDITIONAL"
    assert result["decision_effect"] == "NO_DIRECT_GATE_EFFECT"
    assert validate_company_capital_trust_bridge(result) == []

    assert result["capital_allocation"]["shareholder_return"]["annual_2025_payout_ratio"] == pytest.approx(0.50)
    assert result["capital_allocation"]["shareholder_return"]["h1_2026_interim_payout_ratio"] == pytest.approx(0.15)
    assert result["capital_allocation"]["shareholder_return"]["h1_2026_repurchase_share_ratio"] == pytest.approx(
        28_319_044 / 4_626_654_919
    )

    assert result["capital_allocation"]["capital_commitments"]["guarantee_to_project_ratio"] == pytest.approx(
        130_000_000 / 5_968_000_000
    )
    assert result["trust_revalidation"]["governance_integrity"]["non_related_director_vote_control"] is True
    assert result["trust_revalidation"]["shareholder_treatment"]["status"] == "PASS"


def test_related_party_exposure_does_not_auto_fail_trust():
    result = _build()
    assert result["trust_revalidation"]["status"] == "CONDITIONAL"
    assert result["trust_revalidation"]["governance_integrity"]["status"] == "CONDITIONAL"
    assert result["decision_effect"] == "NO_DIRECT_GATE_EFFECT"


def test_unadmitted_evidence_fails_closed():
    payload = dict(CATL_INPUT)
    payload["evidence_ids"] = ADMITTED + ["NOT_ADMITTED"]
    with pytest.raises(ValueError, match="not admitted"):
        build_company_capital_trust_bridge(
            case_id="CASE",
            cutoff_date="2026-10-04",
            input_payload=payload,
            admitted_evidence_ids=ADMITTED,
            generation_basis="fixture",
        )


def test_post_cutoff_observation_fails_closed():
    with pytest.raises(ValueError, match="exceeds cutoff"):
        _build(observation_date="2026-10-05")


def test_missing_control_fails_closed():
    with pytest.raises(ValueError, match="must be true"):
        _build(independent_director_review=False)


def test_vote_control_requires_zero_against_and_abstain():
    with pytest.raises(ValueError):
        _build(non_related_director_against_votes=1)
    with pytest.raises(ValueError):
        _build(non_related_director_abstain_votes=1)


def test_zero_project_investment_fails_closed():
    with pytest.raises(ValueError, match="positive"):
        _build(indonesia_planned_investment_usd=0)


def test_hash_tampering_is_detected():
    result = _build()
    result["capital_allocation"]["shareholder_return"]["annual_2025_payout_ratio"] += 0.01
    assert "AUDIT_BRIDGE_HASH_MISMATCH" in validate_company_capital_trust_bridge(result)


def test_schema_accepts_built_bridge():
    result = _build()
    schema = json.loads(
        (ROOT / "schemas" / "company_capital_trust_bridge_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result)
    )
    assert errors == []
