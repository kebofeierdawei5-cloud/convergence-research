import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEAssumption,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIEQualification,
    MIERepresentation,
    qualify_market_implied_expectation,
)
from iios_mvp.market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState


def req(variable="forward_eps", value="10", unit="CNY/share"):
    return MIEEconomicRequirement(
        economic_variable=variable, unit=unit, basis="forward", period="NTM",
        horizon="12M", accounting_basis="reported", role="IMPLIED_PRIMARY",
        value=Decimal(value), evidence_ids=("ev-var",),
    )


def obs_basis(observation=date(2026, 10, 4), cutoff=date(2026, 10, 4)):
    return MIEObservationBasis(
        price_observation_id="price-1", observation_date=observation, cutoff_date=cutoff,
        currency="CNY", adjustment_semantics="UNADJUSTED"
    )


def make(**overrides):
    args = dict(
        expectation_id="mie-1", model_id="pe-1", market_model=MarketModelFamily.FORWARD_PE,
        identifiability=IdentifiabilityState.IDENTIFIABLE, stability=StabilityState.STABLE,
        candidate_coverage=CandidateCoverageAssessment(
            status=CandidateCoverageState.SUFFICIENT,
            scope_basis="admitted_ratio_candidates_v0.2",
            candidate_model_ids=("pe-1", "ps-1"),
            evidence_ids=("ev-coverage",),
            rationale="Decision scope explicitly enumerates the admitted candidate models.",
        ), representation=MIERepresentation.IMPLIED_RANGE,
        economic_requirements=(req(),), observation_basis=obs_basis(), assumption_set=(),
        evidence_sufficiency=EvidenceSufficiencyAssessment(
            status=EvidenceSufficiencyState.SUFFICIENT,
            rationale="All required MIE evidence is present.",
            evidence_ids=("ev-var", "ev-coverage"),
        ), evidence_ids=("ev-var", "ev-coverage"), qualification_rationale="valid",
    )
    args.update(overrides)
    return qualify_market_implied_expectation(**args)


def test_decision_grade_requires_full_qualification():
    assert make().qualification == MIEQualification.DECISION_GRADE


def test_conditional_inverse_cannot_be_decision_grade():
    result = make(
        market_model=MarketModelFamily.DCF, model_id="dcf-1",
        representation=MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE,
        economic_requirements=(req("fcf", "100", "CNY"),),
        assumption_set=(MIEAssumption(
            variable="growth", value=Decimal("0.05"), unit="ratio", basis="assumption",
            period="NTM", horizon="12M", accounting_basis="reported", evidence_ids=("ev-growth",)
        ),), evidence_ids=("ev-var", "ev-growth"),
    )
    assert result.qualification == MIEQualification.CONDITIONAL_ONLY


def test_ambiguous_model_is_conditional_only():
    result = make(identifiability=IdentifiabilityState.AMBIGUOUS)
    assert result.qualification == MIEQualification.CONDITIONAL_ONLY


@pytest.mark.parametrize("kwargs", [
    dict(identifiability=IdentifiabilityState.UNIDENTIFIABLE),
    dict(identifiability=IdentifiabilityState.INSUFFICIENT_EVIDENCE),
    dict(stability=StabilityState.UNSTABLE),
    dict(stability=StabilityState.INSUFFICIENT_EVIDENCE),
    dict(candidate_coverage=CandidateCoverageAssessment(status=CandidateCoverageState.INSUFFICIENT, scope_basis="insufficient-scope", candidate_model_ids=("pe-1",), evidence_ids=("ev-coverage",), rationale="Scope is known but incomplete."),
    dict(candidate_coverage=CandidateCoverageAssessment(status=CandidateCoverageState.UNASSESSED, scope_basis="unassessed-scope", candidate_model_ids=("pe-1",), evidence_ids=("ev-coverage",), rationale="Coverage has not been assessed."),
    dict(evidence_sufficiency=EvidenceSufficiencyAssessment(status=EvidenceSufficiencyState.INSUFFICIENT, rationale="Evidence set is incomplete.", evidence_ids=("ev-var",))),
])
def test_unsupported_qualification_is_blocked(kwargs):
    assert make(**kwargs).qualification == MIEQualification.BLOCKED


def test_generic_implied_net_profit_is_rejected():
    with pytest.raises(ValueError, match="generic implied net profit"):
        make(economic_requirements=(req("market_implied_net_profit"),))


def test_semantic_metadata_and_evidence_are_required():
    with pytest.raises(ValueError, match="period"):
        MIEEconomicRequirement(
            economic_variable="revenue", unit="CNY", basis="NTM", period="", horizon="12M",
            accounting_basis="reported", role="IMPLIED_PRIMARY", value=Decimal("100"), evidence_ids=("e",)
        ).validate()
    with pytest.raises(ValueError, match="evidence_ids"):
        MIEEconomicRequirement(
            economic_variable="revenue", unit="CNY", basis="NTM", period="FY", horizon="12M",
            accounting_basis="reported", role="IMPLIED_PRIMARY", value=Decimal("100"), evidence_ids=()
        ).validate()


def test_pit_observation_basis_is_enforced():
    with pytest.raises(ValueError, match="after cutoff"):
        obs_basis(date(2026, 10, 5), date(2026, 10, 4)).validate()


def test_caller_cannot_force_decision_grade_by_data_field():
    result = make(identifiability=IdentifiabilityState.AMBIGUOUS)
    assert result.qualification == MIEQualification.CONDITIONAL_ONLY


def test_missing_evidence_blocks_even_when_other_states_pass():
    assert make(evidence_sufficiency=EvidenceSufficiencyAssessment(status=EvidenceSufficiencyState.INSUFFICIENT, rationale="incomplete", evidence_ids=("ev-var",))).qualification == MIEQualification.BLOCKED


def test_requirement_point_and_range_are_mutually_exclusive():
    with pytest.raises(ValueError, match="point value and range cannot both be supplied"):
        MIEEconomicRequirement(
            economic_variable="revenue", unit="CNY", basis="NTM", period="FY", horizon="12M",
            accounting_basis="reported", role="IMPLIED_PRIMARY", value=Decimal("100"),
            range_low=Decimal("90"), range_high=Decimal("110"), evidence_ids=("e",)
        ).validate()
from jsonschema import Draft202012Validator


def test_caller_supplied_decision_grade_field_is_rejected_at_typed_boundary():
    from iios_mvp.market_implied_expectation import MarketImpliedExpectation

    result = make()
    forged = MarketImpliedExpectation(
        expectation_id=result.expectation_id,
        model_id=result.model_id,
        market_model=result.market_model,
        identifiability=IdentifiabilityState.AMBIGUOUS,
        stability=result.stability,
        candidate_coverage=result.candidate_coverage,
        representation=result.representation,
        economic_requirements=result.economic_requirements,
        observation_basis=result.observation_basis,
        assumption_set=result.assumption_set,
        evidence_sufficiency=result.evidence_sufficiency,
        evidence_ids=result.evidence_ids,
        qualification=MIEQualification.DECISION_GRADE,
        qualification_rationale="forged",
    )
    with pytest.raises(ValueError, match="qualification mismatch"):
        forged.validate()


def test_p4a_json_schema_rejects_unknown_top_level_field():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "market_implied_expectation_v0.2.schema.json"
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    base = {
        "expectation_id": "mie-schema",
        "model_id": "pe-1",
        "market_model": "forward_pe",
        "identifiability": "IDENTIFIABLE",
        "stability": "STABLE",
        "candidate_coverage": {
            "status": "SUFFICIENT",
            "scope_basis": "admitted_ratio_candidates_v0.2",
            "candidate_model_ids": ["pe-1", "ps-1"],
            "evidence_ids": ["ev-coverage"],
            "rationale": "Explicit candidate scope."
        },
        "representation": "IMPLIED_POINT",
        "economic_requirements": [{
            "economic_variable": "forward_eps",
            "unit": "CNY/share",
            "basis": "forward",
            "period": "NTM",
            "horizon": "12M",
            "accounting_basis": "reported",
            "role": "IMPLIED_PRIMARY",
            "value": "10",
            "evidence_ids": ["ev-var"]
        }],
        "observation_basis": {
            "price_observation_id": "price-1",
            "observation_date": "2026-10-04",
            "cutoff_date": "2026-10-04",
            "currency": "CNY",
            "adjustment_semantics": "UNADJUSTED"
        },
        "assumption_set": [],
        "evidence_sufficiency": {
            "status": "SUFFICIENT",
            "rationale": "All required evidence is present.",
            "evidence_ids": ["ev-var", "ev-coverage"]
        },
        "evidence_ids": ["ev-var", "ev-coverage"],
        "qualification": "DECISION_GRADE",
        "qualification_rationale": "valid schema instance"
    }
    assert list(validator.iter_errors(base)) == []
    forged = dict(base, market_implied_net_profit="forbidden")
    assert any("additional properties" in error.message.lower() for error in validator.iter_errors(forged))
