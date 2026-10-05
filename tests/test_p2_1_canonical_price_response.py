from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import pytest

from jsonschema import Draft202012Validator

from iios_mvp.canonical_independent_forecast import (
    InMemoryCanonicalIndependentForecastRegistry,
)
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
from iios_mvp.p2_1_canonical_price_response import (
    PRICE_RESPONSE_VERSION,
    build_canonical_price_response,
    replay_canonical_price_response,
)
from iios_mvp.p4f_mie_snapshot import (
    P4FProvenanceRecord,
    build_p4f_snapshot,
    validate_p4f_snapshot,
)
from iios_mvp.price_dependent_expectation_gap import combine_target_entry_price_v2


CUT = date(2026, 10, 4)
CREATED = datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc)


def _prov(
    evidence_id,
    variable,
    basis,
    *,
    value=None,
    unit="CNY",
    known_at=CREATED,
):
    return P4FProvenanceRecord(
        evidence_id=evidence_id,
        variable=variable,
        unit=unit,
        basis=basis,
        observation_date=CUT,
        known_at=known_at,
        source="fixture-source",
        source_location=f"fixture://{evidence_id}",
        content_sha256="a" * 64,
        captured_at=CREATED,
        value=None if value is None else Decimal(value),
    )


def _forecast(registry, family, variable, value, basis, unit="CNY"):
    return registry.admit_independent_forecast(
        {
            "case_id": "case-p21",
            "market": "CN",
            "symbol": "300750",
            "forecast_id": f"forecast-{family}",
            "forecast_version": "v1",
            "model_version": "fixture-model",
            "variable_id": variable,
            "value": str(value),
            "unit": unit,
            "basis": basis,
            "horizon_years": "1",
            "forecast_origin": "2026-10-01T09:00:00+00:00",
            "known_at": "2026-10-02T09:00:00+00:00",
            "prepared_without_current_price": True,
            "evidence_ids": ["forecast-evidence"],
        }
    ).to_dict()


def _price_observation():
    return {
        "price": "100",
        "price_observation_id": "price-1",
        "currency": "CNY",
        "observed_at": "2026-10-04T15:00:00+00:00",
        "adjustment_semantics": "UNADJUSTED",
    }


def _make_snapshot(family, requirement, assumptions=(), context=()):
    model_id = f"model-{family.value}"
    representation = (
        MIERepresentation.IMPLIED_RANGE
        if family == MarketModelFamily.EV_EBITDA
        else MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
        if family in {
            MarketModelFamily.DCF,
            MarketModelFamily.DDM,
            MarketModelFamily.SOTP,
            MarketModelFamily.RNPV,
        }
        else MIERepresentation.IMPLIED_POINT
    )
    qualification = (
        MIEQualification.DECISION_GRADE
        if representation != MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE
        else MIEQualification.CONDITIONAL_ONLY
    )
    coverage = CandidateCoverageAssessment(
        CandidateCoverageState.SUFFICIENT,
        "p2.1-fixture",
        (model_id,),
        ("cov",),
        "P2.1 fixture candidate coverage.",
    )
    sufficiency = EvidenceSufficiencyAssessment(
        EvidenceSufficiencyState.SUFFICIENT,
        "P2.1 fixture evidence sufficiency.",
        ("suff",),
    )
    evidence_ids = {"cov", "suff", *requirement.evidence_ids}
    for item in assumptions:
        evidence_ids.update(item.evidence_ids)
    mie = MarketImpliedExpectation(
        expectation_id=f"mie-{family.value}",
        model_id=model_id,
        market_model=family,
        identifiability=IdentifiabilityState.IDENTIFIABLE,
        stability=StabilityState.STABLE,
        candidate_coverage=coverage,
        representation=representation,
        economic_requirements=(requirement,),
        observation_basis=MIEObservationBasis(
            "price-1",
            CUT,
            CUT,
            "CNY",
            "UNADJUSTED",
        ),
        assumption_set=tuple(assumptions),
        evidence_sufficiency=sufficiency,
        evidence_ids=tuple(sorted(evidence_ids)),
        qualification=qualification,
        qualification_rationale="P2.1 fixture qualification.",
    )
    model_eval = MIEModelEvaluation.from_expectation(mie)
    mie_set = build_multi_model_market_implied_expectation_set(
        set_id=f"set-{family.value}",
        candidate_coverage=coverage,
        evidence_sufficiency=sufficiency,
        model_evaluations=(model_eval,),
        qualification_rationale="P2.1 fixture aggregate.",
        evidence_ids=tuple(sorted(evidence_ids)),
    )

    provenance = [
        _prov("price-1", "market_price", "model_context:shared:market_price"),
        _prov("cov", "candidate", "fixture"),
        _prov("suff", "sufficiency", "fixture"),
    ]
    for evidence_id in sorted(evidence_ids - {"cov", "suff"}):
        provenance.append(_prov(evidence_id, "model_input", "fixture"))
    provenance.extend(context)
    snapshot = build_p4f_snapshot(
        case_id="case-p21",
        cutoff_date=CUT,
        created_at=CREATED,
        mie_set=mie_set,
        provenance_records=provenance,
    )
    validate_p4f_snapshot(snapshot)
    return snapshot


def _req(variable, basis, *, value=None, low=None, high=None, evidence_id="req"):
    kwargs = (
        {"value": Decimal(value)}
        if value is not None
        else {"range_low": Decimal(low), "range_high": Decimal(high)}
    )
    return MIEEconomicRequirement(
        economic_variable=variable,
        unit="CNY",
        basis=basis,
        period="NTM",
        horizon="12M",
        accounting_basis="reported",
        role="IMPLIED_PRIMARY",
        evidence_ids=(evidence_id,),
        **kwargs,
    )


def test_ev_ebitda_affine_range_is_canonical_and_conservative():
    req = _req(
        "ebitda",
        "current_price_with_historical_ev_ebitda_multiple_range",
        low="8",
        high="10",
    )
    snap = _make_snapshot(
        MarketModelFamily.EV_EBITDA,
        req,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-ev_ebitda:shares_outstanding", value="10", unit="shares"),
            _prov("ctx-net-debt", "net_debt", "model_context:model-ev_ebitda:net_debt", value="100"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    forecast_ref = _forecast(
        registry,
        "ev",
        "ebitda",
        "12",
        "current_price_with_historical_ev_ebitda_multiple_range",
    )
    result = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-ev_ebitda",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert result["response_form"] == "AFFINE_RANGE"
    assert result["status"] == "PASS"
    assert Decimal(result["candidate_value_low"]) == Decimal("72") / Decimal("11")
    assert Decimal(result["candidate_value_high"]) == Decimal("90") / Decimal("11")
    assert Decimal(result["expectation_gap_price_boundary"]) == Decimal("122")
    assert "ctx-shares" in result["evidence_ids"]
    assert "ctx-net-debt" in result["evidence_ids"]


def test_dcf_affine_conditional_response_and_exact_replay():
    req = _req("fcf", "fixture-dcf", value="100")
    assumptions = (
        MIEAssumption("growth", Decimal("0.10"), "ratio", "growth", "NTM", "1Y", "reported", ("growth-e",)),
        MIEAssumption("discount_rate", Decimal("0.20"), "ratio", "discount", "NTM", "1Y", "reported", ("discount-e",)),
    )
    snap = _make_snapshot(
        MarketModelFamily.DCF,
        req,
        assumptions=assumptions,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-dcf:shares_outstanding", value="10", unit="shares"),
            _prov("ctx-net-debt", "net_debt", "model_context:model-dcf:net_debt", value="100"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    forecast_ref = _forecast(registry, "dcf", "fcf", "120", "fixture-dcf")
    result = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-dcf",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert result["qualification"] == "CONDITIONAL_ONLY"
    assert result["response_form"] == "AFFINE"
    assert Decimal(result["candidate_value_low"]) == Decimal("900") / Decimal("11")
    replay = replay_canonical_price_response(
        response=result,
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        market="CN",
        symbol="300750",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert replay["replay_status"] == "PASS"


def test_ddm_affine_response_remains_supported():
    coefficient = Decimal("0.05") / Decimal("1.03")
    req = _req("dividend", "fixture-ddm", value=coefficient * Decimal("100"))
    assumptions = (
        MIEAssumption("growth", Decimal("0.03"), "ratio", "growth", "NTM", "1Y", "reported", ("growth-e",)),
        MIEAssumption("discount_rate", Decimal("0.08"), "ratio", "discount", "NTM", "1Y", "reported", ("discount-e",)),
    )
    snap = _make_snapshot(
        MarketModelFamily.DDM,
        req,
        assumptions=assumptions,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-ddm:shares_outstanding", value="10", unit="shares"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    forecast_ref = _forecast(registry, "ddm", "dividend", "6", "fixture-ddm")
    result = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-ddm",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert result["status"] == "PASS"
    assert Decimal(result["candidate_value_low"]) < Decimal("6")


def test_sotp_affine_residual_response():
    req = _req("residual_value", "fixture-sotp", value="300")
    assumptions = (
        MIEAssumption("segment_value", Decimal("400"), "CNY", "segment:A", "NTM", "1Y", "reported", ("seg-a",)),
        MIEAssumption("segment_value", Decimal("300"), "CNY", "segment:B", "NTM", "1Y", "reported", ("seg-b",)),
    )
    snap = _make_snapshot(
        MarketModelFamily.SOTP,
        req,
        assumptions=assumptions,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-sotp:shares_outstanding", value="10", unit="shares"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    forecast_ref = _forecast(registry, "sotp", "residual_value", "450", "fixture-sotp")
    result = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-sotp",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert result["candidate_value_low"] == "100"
    assert Decimal(result["expectation_gap_price_boundary"]) == Decimal("115")


def test_rnpv_affine_response_uses_frozen_observed_risk_weight():
    assumptions = (
        MIEAssumption("pipeline_value", Decimal("600"), "CNY", "pipeline:P1:observed_composition_anchor", "NTM", "1Y", "reported", ("p1-v",)),
        MIEAssumption("probability", Decimal("0.5"), "ratio", "pipeline:P1:observed_probability_condition", "NTM", "1Y", "reported", ("p1-p",)),
        MIEAssumption("timing", Decimal("2"), "years", "pipeline:P1:observed_timing_condition", "NTM", "1Y", "reported", ("p1-t",)),
        MIEAssumption("pipeline_value", Decimal("400"), "CNY", "pipeline:P2:observed_composition_anchor", "NTM", "1Y", "reported", ("p2-v",)),
        MIEAssumption("probability", Decimal("0.8"), "ratio", "pipeline:P2:observed_probability_condition", "NTM", "1Y", "reported", ("p2-p",)),
        MIEAssumption("timing", Decimal("1"), "years", "pipeline:P2:observed_timing_condition", "NTM", "1Y", "reported", ("p2-t",)),
        MIEAssumption("discount_rate", Decimal("0.1"), "ratio", "rnpv:global_condition", "NTM", "1Y", "reported", ("disc",)),
        MIEAssumption("base_value", Decimal("200"), "CNY", "rnpv:global_condition", "NTM", "1Y", "reported", ("base",)),
    )
    avg_weight = (
        Decimal("600") * Decimal("0.5") / Decimal("1.1") ** Decimal("2")
        + Decimal("400") * Decimal("0.8") / Decimal("1.1")
    ) / Decimal("1000")
    req_value = Decimal("600") / Decimal("1000") * (
        (Decimal("100") * Decimal("10") + Decimal("100") - Decimal("200"))
        / avg_weight
    )
    req = _req(
        "pipeline_value",
        "pipeline:P1:pro_rata_observed_composition",
        value=req_value,
        evidence_id="rnpv-req",
    )
    snap = _make_snapshot(
        MarketModelFamily.RNPV,
        req,
        assumptions=assumptions,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-rnpv:shares_outstanding", value="10", unit="shares"),
            _prov("ctx-net-debt", "net_debt", "model_context:model-rnpv:net_debt", value="100"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    forecast_ref = _forecast(
        registry,
        "rnpv",
        "pipeline_value",
        "1200",
        "pipeline:P1:pro_rata_observed_composition",
    )
    result = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-rnpv",
        independent_forecast_ref=forecast_ref,
        independent_forecast_resolver=registry,
    )
    assert result["response_form"] == "AFFINE"
    assert result["status"] == "PASS"
    assert Decimal(result["candidate_value_low"]) < Decimal("1200")


def test_pit_failure_is_fail_closed():
    req = _req("ebitda", "fixture-ev", value="10")
    snapshot = _make_snapshot(
        MarketModelFamily.EV_EBITDA,
        req,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-ev_ebitda:shares_outstanding", value="10", unit="shares", known_at=datetime(2026, 10, 5, tzinfo=timezone.utc)),
            _prov("ctx-net-debt", "net_debt", "model_context:model-ev_ebitda:net_debt", value="100"),
        ),
    )
    with pytest.raises(ValueError, match="known_at is after cutoff"):
        _make_snapshot(
            MarketModelFamily.EV_EBITDA,
            req,
            context=(
                _prov("ctx-shares", "shares_outstanding", "model_context:model-ev_ebitda:shares_outstanding", value="10", unit="shares", known_at=datetime(2026, 10, 5, tzinfo=timezone.utc)),
                _prov("ctx-net-debt", "net_debt", "model_context:model-ev_ebitda:net_debt", value="100"),
            ),
        )


def test_response_schema_and_tamper_replay():
    req = _req("ebitda", "fixture-ev", value="10")
    snap = _make_snapshot(
        MarketModelFamily.EV_EBITDA,
        req,
        context=(
            _prov("ctx-shares", "shares_outstanding", "model_context:model-ev_ebitda:shares_outstanding", value="10", unit="shares"),
            _prov("ctx-net-debt", "net_debt", "model_context:model-ev_ebitda:net_debt", value="100"),
        ),
    )
    registry = InMemoryCanonicalIndependentForecastRegistry()
    ref = _forecast(registry, "evschema", "ebitda", "12", "fixture-ev")
    response = build_canonical_price_response(
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        candidate_price="80",
        cutoff_date=CUT,
        case_id="case-p21",
        market="CN",
        symbol="300750",
        market_expectation_id="mie-ev_ebitda",
        independent_forecast_ref=ref,
        independent_forecast_resolver=registry,
    )
    schema = json.loads(Path("schemas/p2_1_canonical_price_response_v0.1.schema.json").read_text())
    Draft202012Validator(schema).validate(response)
    tampered = dict(response)
    tampered["candidate_price"] = "81"
    assert replay_canonical_price_response(
        response=tampered,
        market_implied_expectation_snapshot=snap,
        current_price_observation=_price_observation(),
        market="CN",
        symbol="300750",
        independent_forecast_ref=ref,
        independent_forecast_resolver=registry,
    )["replay_status"] == "FAIL"


def test_target_entry_combine_consumes_p2_1_response_semantics():
    combined = combine_target_entry_price_v2(
        return_target_entry_price="130",
        revalidation={
            "status": "NON_POSITIVE",
            "comparison_direction": "HIGHER_IS_BETTER",
            "expectation_gap_price_boundary": "115",
            "price_constraint_type": "UPPER_BOUND_STRICT",
        },
    )
    assert combined["target_entry_price"] == Decimal("115")
    assert combined["price_constraint_type"] == "UPPER_BOUND_STRICT"
    assert PRICE_RESPONSE_VERSION == "IIOS-P2.1-CANONICAL-PRICE-RESPONSE-0.1"
