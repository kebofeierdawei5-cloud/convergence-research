from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator

from iios_mvp.expectation_gap_production import (
    C4_EXPECTATION_GAP_VERSION,
    C4_POLICY_EFFECT,
    build_expectation_gap_evaluation,
    replay_expectation_gap_evaluation,
    validate_expectation_gap_evaluation,
)
from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
    MIEEconomicRequirement,
    MIEObservationBasis,
    MIEQualification,
    MIERepresentation,
    MarketImpliedExpectation,
)
from iios_mvp.market_model_domain import (
    IdentifiabilityState,
    MarketModelFamily,
    StabilityState,
)
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation,
    build_multi_model_market_implied_expectation_set,
)
from iios_mvp.p4f_mie_snapshot import P4FProvenanceRecord, build_p4f_snapshot
from iios_mvp.engine import decide
from tests.test_investment_core_v03 import (
    CURRENT_PRICE_REGISTRY,
    EVIDENCE_ROOT_REGISTRY,
    INDEPENDENT_FORECAST_REGISTRY,
    case,
    independent_forecast_ref,
    market_implied_expectation_snapshot,
    UPSTREAM_AUTHORITY_REGISTRY,
    VALUATION_OUTPUT_RESOLVER,
)


ROOT = Path(__file__).resolve().parents[1]


def _register_snapshot(snapshot: dict) -> dict:
    return EVIDENCE_ROOT_REGISTRY.admit_p4f_snapshot(snapshot).to_dict()


def _provenance_from_fixture(snapshot: dict) -> list[P4FProvenanceRecord]:
    records = []
    for item in snapshot["provenance_manifest"]:
        records.append(
            P4FProvenanceRecord(
                evidence_id=item["evidence_id"],
                variable=item["variable"],
                unit=item["unit"],
                basis=item["basis"],
                observation_date=datetime.fromisoformat(
                    item["observation_date"] + "T00:00:00+00:00"
                ).date(),
                known_at=datetime.fromisoformat(item["known_at"]),
                source=item["source"],
                source_location=item["source_location"],
                content_sha256=item["content_sha256"],
                captured_at=datetime.fromisoformat(item["captured_at"]),
                value=(
                    None
                    if item.get("value") is None
                    else Decimal(str(item["value"]))
                ),
            )
        )
    return records


def _resolution_snapshot(state: str) -> dict:
    base = market_implied_expectation_snapshot()
    cutoff = datetime.fromisoformat(base["created_at"]).date()

    coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.SUFFICIENT,
        scope_basis="C4 test candidate coverage",
        candidate_model_ids=("pe-1", "pe-2"),
        evidence_ids=("cov-pe-1",),
        rationale="C4 test candidate set is explicitly enumerated.",
    )
    sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.SUFFICIENT,
        rationale="C4 test evidence is complete.",
        evidence_ids=("suff-pe-1",),
    )

    requirement_1 = MIEEconomicRequirement(
        economic_variable="forward_eps",
        unit="CNY/share",
        basis="2026A_to_2028E",
        period="2028E",
        horizon="24M",
        accounting_basis="reported",
        role="IMPLIED_PRIMARY",
        value=Decimal("10"),
        evidence_ids=("req-pe-1",),
    )
    def _mie(model_id: str, expectation_id: str) -> MarketImpliedExpectation:
        return MarketImpliedExpectation(
            expectation_id=expectation_id,
            model_id=model_id,
            market_model=MarketModelFamily.FORWARD_PE,
            identifiability=IdentifiabilityState.IDENTIFIABLE,
            stability=StabilityState.STABLE,
            candidate_coverage=coverage,
            representation=MIERepresentation.IMPLIED_POINT,
            economic_requirements=(requirement_1,),
            observation_basis=MIEObservationBasis(
                price_observation_id="price-1",
                observation_date=cutoff,
                cutoff_date=cutoff,
                currency="CNY",
                adjustment_semantics="UNADJUSTED",
            ),
            assumption_set=(),
            evidence_sufficiency=sufficiency,
            evidence_ids=("req-pe-1", "cov-pe-1", "suff-pe-1"),
            qualification=MIEQualification.DECISION_GRADE,
            qualification_rationale="C4 test MIE is decision-grade at model level.",
        )

    if state == "AMBIGUOUS":
        evaluations = (
            MIEModelEvaluation.from_expectation(_mie("pe-1", "mie-pe-1")),
            MIEModelEvaluation.from_expectation(_mie("pe-2", "mie-pe-2")),
        )
    elif state == "NO_FEASIBLE_MODEL":
        coverage = CandidateCoverageAssessment(
            status=CandidateCoverageState.SUFFICIENT,
            scope_basis="C4 test candidate coverage",
            candidate_model_ids=("pe-1",),
            evidence_ids=("cov-pe-1",),
            rationale="C4 test candidate set is explicitly enumerated.",
        )
        evaluations = (
            MIEModelEvaluation.no_feasible_solution(
                model_id="pe-1",
                evidence_ids=("cov-pe-1", "suff-pe-1"),
                rationale="No feasible model admitted for this test.",
            ),
        )
    else:
        raise ValueError(state)

    mie_set = build_multi_model_market_implied_expectation_set(
        set_id=f"set-c4-{state.lower()}",
        candidate_coverage=coverage,
        evidence_sufficiency=sufficiency,
        model_evaluations=evaluations,
        qualification_rationale=f"C4 {state} resolution fixture.",
        evidence_ids=("cov-pe-1", "suff-pe-1", "req-pe-1"),
    )
    return build_p4f_snapshot(
        case_id="V03-001",
        cutoff_date=cutoff,
        created_at=datetime(2026, 10, 4, 17, 10, tzinfo=timezone.utc),
        mie_set=mie_set,
        provenance_records=_provenance_from_fixture(base),
    )


def _case_with_snapshot(snapshot: dict) -> dict:
    c = case()
    ref = _register_snapshot(snapshot)
    c["market_implied_expectation_snapshot_ref"] = ref
    c["expectation_gap"]["mie_snapshot_hash"] = snapshot["snapshot_hash"]
    return c


def test_c4_positive_compatible_gap_is_materialized_and_replayable():
    c = case()
    evaluation = build_expectation_gap_evaluation(
        case=c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert evaluation["evaluation_version"] == C4_EXPECTATION_GAP_VERSION
    assert evaluation["status"] == "PASS"
    assert evaluation["resolution_state"] == "UNIQUE_MODEL"
    assert evaluation["qualification"] == "DECISION_GRADE"
    assert evaluation["gap_absolute"] is not None
    assert evaluation["gap_relative"] is not None
    assert evaluation["comparison"]["comparison_direction"] == "HIGHER_IS_BETTER"
    assert evaluation["policy_effect"] == C4_POLICY_EFFECT

    validate_expectation_gap_evaluation(evaluation)
    replay = replay_expectation_gap_evaluation(evaluation)
    assert replay["replay_status"] == "PASS"
    assert replay["deterministic_replay"] is True


def test_c4_nonpositive_gap_is_a_real_calculation_but_remains_advisory():
    c = case()
    c["expectation_gap"]["independent_forecast_ref"] = independent_forecast_ref(
        value="8", forecast_id="forecast-v03-c4-negative"
    )
    evaluation = build_expectation_gap_evaluation(
        case=c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert evaluation["status"] == "PASS"
    assert Decimal(evaluation["gap_relative"]) < 0

    result = decide(
        c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
        upstream_authority_resolver=UPSTREAM_AUTHORITY_REGISTRY,
    )
    assert result["decision"]["action"] == "BUY"
    assert result["gates"]["expectation_gap_required_for_buy_add"] is False
    assert result["decision"]["expectation_gap_evaluation"]["status"] == "PASS"


def test_c4_incompatible_semantics_never_materialize_a_scalar_gap():
    c = case()
    # Admit a fresh, immutable forecast whose basis is intentionally incompatible.
    incompatible_ref = INDEPENDENT_FORECAST_REGISTRY.admit_independent_forecast({
        "case_id": "V03-001",
        "market": "CN-A",
        "symbol": "300750",
        "cutoff_date": "2026-10-04",
        "forecast_id": "forecast-v03-c4-incompatible",
        "forecast_version": "TEST-FORECAST-0.1",
        "model_version": "TEST-MODEL-0.1",
        "variable_id": "forward_eps",
        "value": "12",
        "unit": "CNY/share",
        "basis": "2027A_to_2028E",
        "horizon_years": "2",
        "forecast_origin": "2026-10-04T12:00:00+00:00",
        "known_at": "2026-10-04T15:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": ["ev-forecast-incompatible"],
    })
    c["expectation_gap"]["independent_forecast_ref"] = incompatible_ref.to_dict()

    evaluation = build_expectation_gap_evaluation(
        case=c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert evaluation["status"] == "INCOMPATIBLE"
    assert evaluation["market_required_value"] is None
    assert evaluation["gap_absolute"] is None
    assert evaluation["gap_relative"] is None
    assert evaluation["comparison"]["basis"] == "2027A_to_2028E"


def test_c4_ambiguous_market_interpretation_has_no_scalar_gap():
    snapshot = _resolution_snapshot("AMBIGUOUS")
    c = _case_with_snapshot(snapshot)
    evaluation = build_expectation_gap_evaluation(
        case=c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert evaluation["status"] == "AMBIGUOUS"
    assert evaluation["resolution_state"] == "AMBIGUOUS"
    assert evaluation["market_required_value"] is None
    assert evaluation["gap_absolute"] is None
    assert evaluation["gap_relative"] is None


def test_c4_no_feasible_solution_is_not_promoted_to_a_gap():
    snapshot = _resolution_snapshot("NO_FEASIBLE_MODEL")
    c = _case_with_snapshot(snapshot)
    evaluation = build_expectation_gap_evaluation(
        case=c,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    assert evaluation["status"] == "NO_FEASIBLE_SOLUTION"
    assert evaluation["resolution_state"] == "NO_FEASIBLE_MODEL"
    assert evaluation["market_required_value"] is None
    assert evaluation["gap_absolute"] is None
    assert evaluation["gap_relative"] is None


def test_c4_expectation_gap_evaluation_is_bound_into_canonical_decision():
    canonical_case = case()
    result = decide(
        canonical_case,
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        current_price_resolver=CURRENT_PRICE_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
        valuation_output_resolver=VALUATION_OUTPUT_RESOLVER,
    )
    evaluation = result["decision"]["expectation_gap_evaluation"]
    assert evaluation["evaluation_version"] == C4_EXPECTATION_GAP_VERSION
    assert evaluation["evaluation_hash"]
    assert evaluation["mie_snapshot_hash"] == canonical_case["expectation_gap"]["mie_snapshot_hash"]
    assert evaluation["market_expectation_id"] == "mie-pe-1"
    assert evaluation["independent_forecast_id"] == "forecast-v03-001"


def test_c4_schema_accepts_real_evaluation():
    evaluation = build_expectation_gap_evaluation(
        case=case(),
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    schema = json.loads(
        (ROOT / "schemas/c4_expectation_gap_evaluation_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(evaluation)


def test_c4_v03_nested_schema_rejects_malformed_evaluation():
    evaluation = build_expectation_gap_evaluation(
        case=case(),
        evidence_root_resolver=EVIDENCE_ROOT_REGISTRY,
        independent_forecast_resolver=INDEPENDENT_FORECAST_REGISTRY,
    )
    schema = json.loads(
        (ROOT / "schemas/investment_core_case_v0.3.schema.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = deepcopy(case())
    candidate["decision"] = {
        "action": "BUY",
        "decision_status": "READY",
        "investability_status": "INVESTABLE",
        "primary_reason": "C4 schema test",
        "human_approval_required": True,
        "auto_execution": False,
        "expectation_gap_evaluation": evaluation,
    }

    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(candidate)) == []

    malformed = deepcopy(candidate)
    del malformed["decision"]["expectation_gap_evaluation"]["evaluation_hash"]
    errors = list(validator.iter_errors(malformed))
    assert errors, "nested C4 evaluation must be schema-enforced"
