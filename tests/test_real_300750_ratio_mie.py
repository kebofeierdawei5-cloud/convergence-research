import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
)
from iios_mvp.market_model_domain import CandidateMarketModel, MarketModelFamily, MarketObservableEvidence
from iios_mvp.market_model_identification import (
    MarketModelIdentificationInput,
    MarketValuationObservation,
    identify_market_models,
)
from iios_mvp.ratio_market_implied_expectation import build_ratio_market_implied_expectations


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "examples" / "real_cases" / "RC-CN-A-300750-20261004_ratio_mie_input.json"


def _load():
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    observations = tuple(
        MarketValuationObservation(
            observation_id=item["observation_id"],
            observation_date=date.fromisoformat(item["observation_date"]),
            known_at=datetime.fromisoformat(item["known_at"]),
            price=Decimal(item["price"]),
            shares_outstanding=Decimal(item["shares_outstanding"]),
            economic_variable=item["economic_variable"],
            economic_value=Decimal(item["economic_value"]),
            unit=item["unit"],
            basis=item["basis"],
            evidence_ids=tuple(item["evidence_ids"]),
            source=item["source"],
            net_debt=Decimal(item["net_debt"]),
        )
        for item in payload["observations"]
    )
    evidence = tuple(
        MarketObservableEvidence(
            evidence_id=item["evidence_id"],
            variable=item["variable"],
            unit=item["unit"],
            basis=item["basis"],
            observation_date=date.fromisoformat(item["observation_date"]),
            known_at=datetime.fromisoformat(item["known_at"]),
            source=item["source"],
            value=Decimal(item["value"]),
            metadata=item["metadata"],
        )
        for item in payload["evidence"]
    )
    candidate_payload = payload["candidate"]
    candidate = CandidateMarketModel(
        model_id=candidate_payload["model_id"],
        family=MarketModelFamily(candidate_payload["family"]),
        required_economic_variables=tuple(candidate_payload["required_economic_variables"]),
        required_observable_variables=tuple(candidate_payload["required_observable_variables"]),
        evidence_ids=tuple(candidate_payload["evidence_ids"]),
        admission_basis=candidate_payload["admission_basis"],
        inverse_solvable=candidate_payload["inverse_solvable"],
    )
    inp = MarketModelIdentificationInput(
        cutoff_date=date.fromisoformat(payload["cutoff_date"]),
        current_observation_id="CATL-EVEBITDA-CURRENT-2026-09-30",
        candidates=(candidate,),
        observations=observations,
        evidence=evidence,
    )
    coverage_payload = payload["candidate_coverage"]
    coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState(coverage_payload["status"]),
        scope_basis=coverage_payload["scope_basis"],
        candidate_model_ids=tuple(coverage_payload["candidate_model_ids"]),
        evidence_ids=tuple(coverage_payload["evidence_ids"]),
        rationale=coverage_payload["rationale"],
    )
    evidence_payload = payload["evidence_sufficiency"]
    sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState(evidence_payload["status"]),
        rationale=evidence_payload["rationale"],
        evidence_ids=tuple(evidence_payload["evidence_ids"]),
    )
    return payload, inp, coverage, sufficiency


def test_real_core04c_observations_are_consumed_by_p3a():
    payload, inp, coverage, sufficiency = _load()
    result = identify_market_models(inp)

    evaluation = result["evaluations"][0]
    assert evaluation.fit.model_id == "real-ev-ebitda-300750"
    assert evaluation.fit.status.value == "INFEASIBLE"

    diagnostics = {item.name: item for item in evaluation.fit.diagnostics}
    assert diagnostics["historical_market_multiple_range"].status == "PASS"
    assert diagnostics["current_consistency"].status == "INFEASIBLE"
    assert "current_multiple=8.3755367867323613771955766383371182231544885817258636164299" in diagnostics["current_consistency"].notes

    ident = result["identifiability"]
    assert ident.state.value == "UNIDENTIFIABLE"
    assert ident.feasible_model_ids == ()

    stability = result["stability"]
    assert stability.state.value == "INSUFFICIENT_EVIDENCE"

    assert result["status"] == "PASS"
    assert result["method"] == "model_specific_inverse_v0.2"


def test_real_core04c_slice_fails_closed_before_mie_materialization():
    payload, inp, coverage, sufficiency = _load()
    result = identify_market_models(inp)

    with pytest.raises(ValueError, match="no feasible ratio market model"):
        build_ratio_market_implied_expectations(
            identification_input=inp,
            identification=result,
            candidate_coverage=coverage,
            evidence_sufficiency=sufficiency,
            currency="CNY",
            adjustment_semantics="UNADJUSTED_CLOSE",
            period="FY2025",
            horizon="completed_fiscal_year",
            accounting_basis="reported_completed_fiscal_year_EBITDA",
        )


def test_real_core04c_pit_and_exact_values_are_locked():
    payload, inp, coverage, sufficiency = _load()
    assert payload["source_receipt"]["artifact_sha256"] == "51e9e8c19404ef241383c99e0f9ed98bf3088fbe2b4a47778e9f5d79a26ee6c4"
    assert [item.observation_id for item in inp.observations[:3]] == [
        "CATL-EVEBITDA-2025-10-22",
        "CATL-EVEBITDA-2026-04-17",
        "CATL-EVEBITDA-2026-07-27",
    ]
    assert [item.economic_value for item in inp.observations[:3]] == [
        Decimal("91999043000"),
        Decimal("119197217000"),
        Decimal("119197217000"),
    ]
    assert all(item.known_at.date() <= item.observation_date for item in inp.observations)
    assert all(item.known_at.date() <= inp.cutoff_date for item in inp.observations)


def test_current_multiple_uses_the_existing_core03_market_context_without_vendor_backfill():
    _, inp, _, _ = _load()
    current = next(item for item in inp.observations if item.observation_id == inp.current_observation_id)
    current_multiple = (current.price * current.shares_outstanding + current.net_debt) / current.economic_value
    assert current_multiple == Decimal("8.3755367867323613771955766383371182231544885817258636164299037283731213288310246")
