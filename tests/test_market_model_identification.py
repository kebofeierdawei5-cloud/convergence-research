from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from iios_mvp.market_model_domain import (
    CandidateMarketModel,
    MarketModelFamily,
    MarketObservableEvidence,
)
from iios_mvp.market_model_identification import (
    MarketModelIdentificationInput,
    MarketValuationObservation,
    identify_market_models,
)


CUTOFF = date(2026, 10, 4)
KNOWN = datetime(2026, 10, 4, 2, tzinfo=timezone.utc)


def ev(eid: str, variable: str) -> MarketObservableEvidence:
    return MarketObservableEvidence(
        evidence_id=eid,
        variable=variable,
        unit="CNY/share" if variable == "forward_eps" else "CNY",
        basis="historical_market_observation",
        observation_date=CUTOFF,
        known_at=KNOWN,
        source="test-fixture",
        value=Decimal("1"),
    )


def candidate(model_id: str, family: MarketModelFamily, variable: str) -> CandidateMarketModel:
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=(variable,),
        required_observable_variables=(variable,),
        evidence_ids=("e1",),
        admission_basis="test evidence-backed candidate",
        inverse_solvable=True,
    )


def obs(oid: str, day: int, price: str, economic: str, variable: str, shares: str = "100") -> MarketValuationObservation:
    return MarketValuationObservation(
        observation_id=oid,
        observation_date=date(2026, 9, day),
        known_at=datetime(2026, 9, day, 2, tzinfo=timezone.utc),
        price=Decimal(price),
        shares_outstanding=Decimal(shares),
        economic_variable=variable,
        economic_value=Decimal(economic),
        unit="CNY/share" if variable == "forward_eps" else "CNY",
        basis="forward",
        evidence_ids=("e1",),
        source="test-fixture",
    )


def base_input(candidates, observations, evidence=None):
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id="current",
        candidates=tuple(candidates),
        observations=tuple(observations),
        evidence=tuple(evidence or [
            ev("e1", "forward_eps"),
        ]),
    )


def test_unique_feasible_model_is_identifiable_and_solution_is_model_semantic():
    candidate_pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        obs("h4", 29, "130", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([candidate_pe], observations))
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["identifiability"].selected_model_id == "pe-1"
    solution = result["evaluations"][0].feasible_solution_set.solutions[0]
    assert solution.economic_variable == "forward_eps"
    assert solution.range_low == Decimal("4.464285714285714285714285714")
    assert solution.range_high == Decimal("6.25")
    assert result["stability"].state.value == "STABLE", result["stability"].observations
    assert len(result["stability"].observations) >= 2


def test_multiple_feasible_models_are_ambiguous():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    ps = candidate("ps-1", MarketModelFamily.PS, "revenue")
    obs_pe = (
        obs("pe-h1", 1, "100", "5", "forward_eps"),
        obs("pe-h2", 15, "120", "5", "forward_eps"),
        obs("pe-h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    obs_rev = (
        MarketValuationObservation(
            observation_id="r1",
            observation_date=date(2026, 9, 1),
            known_at=datetime(2026, 9, 1, 2, tzinfo=timezone.utc),
            price=Decimal("10"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="r2",
            observation_date=date(2026, 9, 15),
            known_at=datetime(2026, 9, 15, 2, tzinfo=timezone.utc),
            price=Decimal("12"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="r3",
            observation_date=date(2026, 9, 30),
            known_at=datetime(2026, 9, 30, 2, tzinfo=timezone.utc),
            price=Decimal("14"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
        MarketValuationObservation(
            observation_id="current-revenue",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("13"),
            shares_outstanding=Decimal("100"),
            economic_variable="revenue",
            economic_value=Decimal("1000"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e2",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input(
        [pe, ps],
        obs_pe + obs_rev,
        [ev("e1", "forward_eps"), ev("e2", "revenue")]
    ))
    assert result["identifiability"].state.value == "AMBIGUOUS"
    assert result["identifiability"].selected_model_id is None


def test_no_feasible_model_is_unidentifiable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("500"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "UNIDENTIFIABLE"
    assert result["stability"].state.value == "INSUFFICIENT_EVIDENCE"


def test_insufficient_history_is_not_called_unidentifiable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "INSUFFICIENT_EVIDENCE"


def test_dcf_without_required_history_and_assumptions_is_insufficient():
    dcf = CandidateMarketModel(
        model_id="dcf-1",
        family=MarketModelFamily.DCF,
        required_economic_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        required_observable_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        evidence_ids=("e1",),
        admission_basis="test evidence-backed DCF candidate",
        inverse_solvable=True,
    )
    observations = (
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("100"),
            shares_outstanding=Decimal("100"),
            economic_variable="fcf",
            economic_value=Decimal("10"),
            unit="CNY",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([dcf], observations, [ev("e1", "fcf")]))
    evaluation = result["evaluations"][0]
    assert evaluation.fit.status.value == "INSUFFICIENT_EVIDENCE"


def test_historical_window_perturbation_can_make_model_unstable():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "10", "forward_eps"),
        obs("h2", 15, "200", "10", "forward_eps"),
        obs("h3", 30, "300", "10", "forward_eps"),
        obs("h4", 30, "300", "10", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("100"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("10"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["stability"].state.value == "UNSTABLE"


def test_candidate_unknown_provenance_is_rejected():
    bad = CandidateMarketModel(
        model_id="pe-1",
        family=MarketModelFamily.FORWARD_PE,
        required_economic_variables=("forward_eps",),
        required_observable_variables=("forward_eps",),
        evidence_ids=("missing",),
        admission_basis="bad provenance",
        inverse_solvable=True,
    )
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    with pytest.raises(ValueError, match="unknown evidence_ids"):
        identify_market_models(base_input([bad], observations))

def test_stability_observation_can_be_stable_without_selected_model():
    from iios_mvp.market_model_domain import StabilityObservation, StabilityState
    observation = StabilityObservation(
        perturbation_id="p1",
        perturbation="full historical set",
        resulting_state=StabilityState.STABLE,
        selected_model_id=None,
    )
    observation.validate()

def test_one_feasible_model_plus_unevaluable_competitor_is_insufficient_evidence():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    dcf = CandidateMarketModel(
        model_id="dcf-1",
        family=MarketModelFamily.DCF,
        required_economic_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        required_observable_variables=(
            "fcf", "growth", "margin", "reinvestment", "terminal_value",
        ),
        evidence_ids=("e2",),
        admission_basis="candidate DCF evidence exists but solver is not implemented",
        inverse_solvable=True,
    )
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(
        base_input(
            [pe, dcf],
            observations,
            [ev("e1", "forward_eps"), ev("e2", "fcf")],
        )
    )
    assert result["identifiability"].state.value == "INSUFFICIENT_EVIDENCE"
    assert result["identifiability"].selected_model_id is None

def test_three_historical_points_without_leave_one_out_window_are_insufficient_for_stability():
    pe = candidate("pe-1", MarketModelFamily.FORWARD_PE, "forward_eps")
    observations = (
        obs("h1", 1, "100", "5", "forward_eps"),
        obs("h2", 15, "120", "5", "forward_eps"),
        obs("h3", 30, "140", "5", "forward_eps"),
        MarketValuationObservation(
            observation_id="current",
            observation_date=CUTOFF,
            known_at=KNOWN,
            price=Decimal("125"),
            shares_outstanding=Decimal("100"),
            economic_variable="forward_eps",
            economic_value=Decimal("5"),
            unit="CNY/share",
            basis="forward",
            evidence_ids=("e1",),
            source="test-fixture",
        ),
    )
    result = identify_market_models(base_input([pe], observations))
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    assert result["stability"].state.value == "INSUFFICIENT_EVIDENCE"


def complex_evidence(eid: str, variable: str, unit: str = "CNY") -> MarketObservableEvidence:
    return MarketObservableEvidence(
        evidence_id=eid,
        variable=variable,
        unit=unit,
        basis="complex-model-fixture",
        observation_date=CUTOFF,
        known_at=KNOWN,
        source="test-fixture",
        value=Decimal("1"),
    )


def complex_candidate(model_id: str, family: MarketModelFamily, variables: tuple[str, ...], evidence_ids: tuple[str, ...]) -> CandidateMarketModel:
    return CandidateMarketModel(
        model_id=model_id,
        family=family,
        required_economic_variables=variables,
        required_observable_variables=variables,
        evidence_ids=evidence_ids,
        admission_basis="test evidence-backed complex-model candidate",
        inverse_solvable=True,
    )


def cobs(
    oid: str,
    day: int | None,
    price: str,
    variable: str,
    value: str,
    basis: str,
    unit: str = "CNY",
    shares: str = "1",
    net_debt: str = "0",
) -> MarketValuationObservation:
    obs_date = CUTOFF if day is None else date(2026, 9, day)
    known_at = KNOWN if day is None else datetime(2026, 9, day, 2, tzinfo=timezone.utc)
    return MarketValuationObservation(
        observation_id=oid,
        observation_date=obs_date,
        known_at=known_at,
        price=Decimal(price),
        shares_outstanding=Decimal(shares),
        economic_variable=variable,
        economic_value=Decimal(value),
        unit=unit,
        basis=basis,
        evidence_ids=(f"e-{variable}",),
        source="test-fixture",
        net_debt=Decimal(net_debt),
    )


def complex_input(
    candidate_item: CandidateMarketModel,
    observations: tuple[MarketValuationObservation, ...],
    evidence: tuple[MarketObservableEvidence, ...],
    anchor: str,
    *additional_candidates: CandidateMarketModel,
) -> MarketModelIdentificationInput:
    return MarketModelIdentificationInput(
        cutoff_date=CUTOFF,
        current_observation_id=anchor,
        candidates=(candidate_item,) + additional_candidates,
        observations=observations,
        evidence=evidence,
    )


def dcf_fixture(prices: tuple[str, ...]) -> tuple[tuple[MarketValuationObservation, ...], tuple[MarketObservableEvidence, ...]]:
    variables = {
        "fcf": "CNY",
        "growth": "ratio",
        "margin": "ratio",
        "reinvestment": "ratio",
        "terminal_value": "CNY",
        "discount_rate": "ratio",
    }
    evidence = tuple(complex_evidence(f"e-{name}", name, unit) for name, unit in variables.items())
    historical_days = (1, 8, 15, 22)
    rows: list[MarketValuationObservation] = []
    for day, price in zip(historical_days, prices[:-1]):
        for variable, value, unit, basis in (
            ("fcf", "100", "CNY", "fcff"),
            ("growth", "0.05", "ratio", "assumption"),
            ("margin", "0.40", "ratio", "assumption"),
            ("reinvestment", "0.25", "ratio", "assumption"),
            ("terminal_value", "2100", "CNY", "terminal"),
            ("discount_rate", "0.10", "ratio", "assumption"),
        ):
            rows.append(cobs(f"h{day}-{variable}", day, price, variable, value, basis, unit))
    current_price = prices[-1]
    for variable, value, unit, basis in (
        ("fcf", "100", "CNY", "fcff"),
        ("growth", "0.05", "ratio", "assumption"),
        ("margin", "0.40", "ratio", "assumption"),
        ("reinvestment", "0.25", "ratio", "assumption"),
        ("terminal_value", "2100", "CNY", "terminal"),
        ("discount_rate", "0.10", "ratio", "assumption"),
    ):
        rows.append(cobs(f"current-{variable}", None, current_price, variable, value, basis, unit))
    return tuple(rows), evidence


def test_p3b_dcf_model_specific_inverse_is_identifiable_and_stable():
    candidate_item = complex_candidate(
        "dcf-1",
        MarketModelFamily.DCF,
        ("fcf", "growth", "margin", "reinvestment", "terminal_value", "discount_rate"),
        ("candidate-dcf",),
    )
    observations, evidence = dcf_fixture(("2100", "2100", "2100", "2100", "2100"))
    evidence = evidence + (complex_evidence("candidate-dcf", "dcf_candidate"),)
    result = identify_market_models(
        complex_input(candidate_item, observations, evidence, "current-fcf")
    )
    evaluation = result["evaluations"][0]
    assert evaluation.fit.status.value == "FEASIBLE"
    assert result["identifiability"].state.value == "IDENTIFIABLE"
    solution = evaluation.feasible_solution_set.solutions[0]
    assert solution.economic_variable == "fcf"
    assert solution.value == Decimal("100")
    assert result["stability"].state.value == "STABLE", result["stability"]


def test_p3b_ddm_model_specific_inverse_is_identifiable():
    candidate_item = complex_candidate(
        "ddm-1",
        MarketModelFamily.DDM,
        ("dividend", "payout", "growth", "discount_rate"),
        ("candidate-ddm",),
    )
    evidence = tuple(
        complex_evidence("e-" + name, name, "CNY/share" if name == "dividend" else "ratio")
        for name in ("dividend", "payout", "growth", "discount_rate")
    )
    evidence = evidence + (complex_evidence("candidate-ddm", "ddm_candidate"),)
    rows: list[MarketValuationObservation] = []
    for day in (1, 8, 15, 22):
        for variable, value, unit in (
            ("dividend", "5", "CNY/share"),
            ("payout", "0.40", "ratio"),
            ("growth", "0.05", "ratio"),
            ("discount_rate", "0.10", "ratio"),
        ):
            rows.append(cobs(f"{day}-{variable}", day, "105", variable, value, "assumption", unit))
    for variable, value, unit in (
        ("dividend", "5", "CNY/share"),
        ("payout", "0.40", "ratio"),
        ("growth", "0.05", "ratio"),
        ("discount_rate", "0.10", "ratio"),
    ):
        rows.append(cobs(f"current-{variable}", None, "105", variable, value, "assumption", unit))
    result = identify_market_models(
        complex_input(candidate_item, tuple(rows), evidence, "current-dividend")
    )
    assert result["evaluations"][0].fit.status.value == "FEASIBLE"
    assert result["evaluations"][0].feasible_solution_set.solutions[0].value == Decimal("5")
    assert result["identifiability"].state.value == "IDENTIFIABLE"


def test_p3b_sotp_model_specific_inverse_preserves_segment_residual_semantics():
    candidate_item = complex_candidate(
        "sotp-1",
        MarketModelFamily.SOTP,
        ("segment_value", "residual_value"),
        ("candidate-sotp",),
    )
    evidence = (
        complex_evidence("e-segment_value", "segment_value", "CNY"),
        complex_evidence("e-residual_value", "residual_value", "CNY"),
        complex_evidence("candidate-sotp", "sotp_candidate"),
    )
    rows: list[MarketValuationObservation] = []
    for day in (1, 8, 15, 22):
        rows.extend((
            cobs(f"{day}-seg-a", day, "110", "segment_value", "60", "segment:A"),
            cobs(f"{day}-seg-b", day, "110", "segment_value", "40", "segment:B"),
        ))
    rows.extend((
        cobs("current-seg-a", None, "110", "segment_value", "60", "segment:A"),
        cobs("current-seg-b", None, "110", "segment_value", "40", "segment:B"),
    ))
    result = identify_market_models(
        complex_input(candidate_item, tuple(rows), evidence, "current-seg-a")
    )
    evaluation = result["evaluations"][0]
    assert evaluation.fit.status.value == "FEASIBLE"
    solution = evaluation.feasible_solution_set.solutions[0]
    assert solution.economic_variable == "residual_value"
    assert solution.value == Decimal("10")
    assert result["stability"].state.value == "STABLE"


def test_p3b_rnpv_model_specific_inverse_preserves_pipeline_probability_timing():
    candidate_item = complex_candidate(
        "rnpv-1",
        MarketModelFamily.RNPV,
        ("pipeline_value", "probability", "timing", "discount_rate", "base_value"),
        ("candidate-rnpv",),
    )
    evidence = tuple(
        complex_evidence("e-" + name, name, "CNY" if name in {"pipeline_value", "base_value"} else "ratio")
        for name in ("pipeline_value", "probability", "timing", "discount_rate", "base_value")
    )
    evidence = evidence + (complex_evidence("candidate-rnpv", "rnpv_candidate"),)
    price = "92.7272727272727272727272727273"
    rows: list[MarketValuationObservation] = []
    for day in (1, 8, 15, 22):
        rows.extend((
            cobs(f"{day}-pipeline", day, price, "pipeline_value", "100", "pipeline:P1"),
            cobs(f"{day}-probability", day, price, "probability", "0.80", "pipeline:P1", "ratio"),
            cobs(f"{day}-timing", day, price, "timing", "1", "pipeline:P1", "years"),
            cobs(f"{day}-discount", day, price, "discount_rate", "0.10", "assumption", "ratio"),
            cobs(f"{day}-base", day, price, "base_value", "20", "base", "CNY"),
        ))
    rows.extend((
        cobs("current-pipeline", None, price, "pipeline_value", "100", "pipeline:P1"),
        cobs("current-probability", None, price, "probability", "0.80", "pipeline:P1", "ratio"),
        cobs("current-timing", None, price, "timing", "1", "pipeline:P1", "years"),
        cobs("current-discount", None, price, "discount_rate", "0.10", "assumption", "ratio"),
        cobs("current-base", None, price, "base_value", "20", "base", "CNY"),
    ))
    result = identify_market_models(
        complex_input(candidate_item, tuple(rows), evidence, "current-pipeline")
    )
    evaluation = result["evaluations"][0]
    assert evaluation.fit.status.value == "FEASIBLE"
    assert evaluation.feasible_solution_set.solutions[0].economic_variable == "pipeline_value"
    assert evaluation.feasible_solution_set.solutions[0].value == Decimal("100.0000000000000000000000000000")
    assert result["identifiability"].state.value == "IDENTIFIABLE"


def test_p3b_dcf_and_ddm_both_feasible_are_ambiguous():
    dcf = complex_candidate(
        "dcf-1",
        MarketModelFamily.DCF,
        ("fcf", "growth", "margin", "reinvestment", "terminal_value", "discount_rate"),
        ("candidate-dcf",),
    )
    ddm = complex_candidate(
        "ddm-1",
        MarketModelFamily.DDM,
        ("dividend", "payout", "growth", "discount_rate"),
        ("candidate-ddm",),
    )
    dcf_obs, dcf_evidence = dcf_fixture(("2100", "2100", "2100", "2100", "2100"))
    rows = list(dcf_obs)
    for day in (1, 8, 15, 22):
        rows.extend((
            cobs(f"ddm-{day}-dividend", day, "2100", "dividend", "100", "assumption", "CNY/share"),
            cobs(f"ddm-{day}-payout", day, "2100", "payout", "0.40", "assumption", "ratio"),
            cobs(f"ddm-{day}-growth", day, "2100", "growth", "0.05", "assumption", "ratio"),
            cobs(f"ddm-{day}-discount", day, "2100", "discount_rate", "0.10", "assumption", "ratio"),
        ))
    rows.extend((
        cobs("ddm-current-dividend", None, "2100", "dividend", "100", "assumption", "CNY/share"),
        cobs("ddm-current-payout", None, "2100", "payout", "0.40", "assumption", "ratio"),
        cobs("ddm-current-growth", None, "2100", "growth", "0.05", "assumption", "ratio"),
        cobs("ddm-current-discount", None, "2100", "discount_rate", "0.10", "assumption", "ratio"),
    ))
    evidence = tuple(dcf_evidence) + (
        complex_evidence("e-dividend", "dividend", "CNY/share"),
        complex_evidence("e-payout", "payout", "ratio"),
        complex_evidence("candidate-dcf", "dcf_candidate"),
        complex_evidence("candidate-ddm", "ddm_candidate"),
    )
    result = identify_market_models(
        MarketModelIdentificationInput(
            cutoff_date=CUTOFF,
            current_observation_id="current-fcf",
            candidates=(dcf, ddm),
            observations=tuple(rows),
            evidence=evidence,
        )
    )
    assert result["evaluations"][0].fit.status.value == "FEASIBLE"
    assert result["evaluations"][1].fit.status.value == "FEASIBLE"
    assert result["identifiability"].state.value == "AMBIGUOUS"
    assert result["identifiability"].selected_model_id is None


def test_p3b_invalid_dcf_discount_rate_vs_growth_is_infeasible():
    candidate_item = complex_candidate(
        "dcf-1",
        MarketModelFamily.DCF,
        ("fcf", "growth", "margin", "reinvestment", "terminal_value", "discount_rate"),
        ("candidate-dcf",),
    )
    observations, evidence = dcf_fixture(("2100", "2100", "2100", "2100", "2100"))
    invalid_rows = tuple(
        item if item.economic_variable != "discount_rate"
        else cobs(
            item.observation_id,
            None if item.observation_date == CUTOFF else item.observation_date.day,
            str(item.price),
            "discount_rate",
            "0.03",
            "assumption",
            "ratio",
        )
        for item in observations
    )
    evidence = evidence + (complex_evidence("candidate-dcf", "dcf_candidate"),)
    result = identify_market_models(
        complex_input(candidate_item, invalid_rows, evidence, "current-fcf")
    )
    assert result["evaluations"][0].fit.status.value == "INFEASIBLE"


def test_p3b_missing_complex_input_is_insufficient_evidence():
    candidate_item = complex_candidate(
        "ddm-1",
        MarketModelFamily.DDM,
        ("dividend", "payout", "growth", "discount_rate"),
        ("candidate-ddm",),
    )
    evidence = (
        complex_evidence("e-dividend", "dividend", "CNY/share"),
        complex_evidence("e-payout", "payout", "ratio"),
        complex_evidence("e-growth", "growth", "ratio"),
        complex_evidence("candidate-ddm", "ddm_candidate"),
    )
    rows = (
        cobs("h1-dividend", 1, "2100", "dividend", "100", "assumption", "CNY/share"),
        cobs("h1-payout", 1, "2100", "payout", "0.40", "assumption", "ratio"),
        cobs("h1-growth", 1, "2100", "growth", "0.05", "assumption", "ratio"),
        cobs("current-dividend", None, "2100", "dividend", "100", "assumption", "CNY/share"),
        cobs("current-payout", None, "2100", "payout", "0.40", "assumption", "ratio"),
        cobs("current-growth", None, "2100", "growth", "0.05", "assumption", "ratio"),
    )
    result = identify_market_models(
        complex_input(candidate_item, rows, evidence, "current-dividend")
    )
    assert result["identifiability"].state.value == "INSUFFICIENT_EVIDENCE"


def test_p3b_sotp_duplicate_segment_is_infeasible():
    candidate_item = complex_candidate(
        "sotp-1",
        MarketModelFamily.SOTP,
        ("segment_value", "residual_value"),
        ("candidate-sotp",),
    )
    evidence = (
        complex_evidence("e-segment_value", "segment_value"),
        complex_evidence("candidate-sotp", "sotp_candidate"),
    )
    rows = (
        cobs("h1-a", 1, "110", "segment_value", "60", "segment:A"),
        cobs("h1-a-dup", 1, "110", "segment_value", "40", "segment:A"),
        cobs("h2-a", 15, "110", "segment_value", "60", "segment:A"),
        cobs("h2-b", 15, "110", "segment_value", "40", "segment:B"),
        cobs("current-a", None, "110", "segment_value", "60", "segment:A"),
        cobs("current-b", None, "110", "segment_value", "40", "segment:B"),
    )
    result = identify_market_models(
        complex_input(candidate_item, rows, evidence, "current-a")
    )
    assert result["evaluations"][0].fit.status.value == "INFEASIBLE"


def test_p3b_rnpv_multi_pipeline_inverse_uses_observed_composition():
    candidate_item = complex_candidate(
        "rnpv-2",
        MarketModelFamily.RNPV,
        ("pipeline_value", "probability", "timing", "discount_rate", "base_value"),
        ("candidate-rnpv-2",),
    )
    evidence = tuple(
        complex_evidence("e-" + name, name, "CNY" if name in {"pipeline_value", "base_value"} else "ratio")
        for name in ("pipeline_value", "probability", "timing", "discount_rate", "base_value")
    ) + (complex_evidence("candidate-rnpv-2", "rnpv_candidate"),)

    risk_adjusted = (
        Decimal("60") * Decimal("0.80") / (Decimal("1.10") ** Decimal("1"))
        + Decimal("40") * Decimal("0.50") / (Decimal("1.10") ** Decimal("2"))
    )
    price = str(Decimal("20") + risk_adjusted)
    rows: list[MarketValuationObservation] = []
    for day in (1, 8, 15, 22):
        rows.extend((
            cobs(f"{day}-p1-value", day, price, "pipeline_value", "60", "pipeline:P1"),
            cobs(f"{day}-p1-prob", day, price, "probability", "0.80", "pipeline:P1", "ratio"),
            cobs(f"{day}-p1-time", day, price, "timing", "1", "pipeline:P1", "years"),
            cobs(f"{day}-p2-value", day, price, "pipeline_value", "40", "pipeline:P2"),
            cobs(f"{day}-p2-prob", day, price, "probability", "0.50", "pipeline:P2", "ratio"),
            cobs(f"{day}-p2-time", day, price, "timing", "2", "pipeline:P2", "years"),
            cobs(f"{day}-discount", day, price, "discount_rate", "0.10", "assumption", "ratio"),
            cobs(f"{day}-base", day, price, "base_value", "20", "base", "CNY"),
        ))
    rows.extend((
        cobs("current-p1-value", None, price, "pipeline_value", "60", "pipeline:P1"),
        cobs("current-p1-prob", None, price, "probability", "0.80", "pipeline:P1", "ratio"),
        cobs("current-p1-time", None, price, "timing", "1", "pipeline:P1", "years"),
        cobs("current-p2-value", None, price, "pipeline_value", "40", "pipeline:P2"),
        cobs("current-p2-prob", None, price, "probability", "0.50", "pipeline:P2", "ratio"),
        cobs("current-p2-time", None, price, "timing", "2", "pipeline:P2", "years"),
        cobs("current-discount", None, price, "discount_rate", "0.10", "assumption", "ratio"),
        cobs("current-base", None, price, "base_value", "20", "base", "CNY"),
    ))
    result = identify_market_models(
        complex_input(candidate_item, tuple(rows), evidence, "current-p1-value")
    )
    solution = result["evaluations"][0].feasible_solution_set.solutions[0]
    assert result["evaluations"][0].fit.status.value == "FEASIBLE"
    assert solution.value == Decimal("100")
    assert result["identifiability"].state.value == "IDENTIFIABLE"


def test_p3b_unknown_observation_evidence_id_is_rejected():
    candidate_item = complex_candidate(
        "ddm-unknown",
        MarketModelFamily.DDM,
        ("dividend", "payout", "growth", "discount_rate"),
        ("candidate-ddm",),
    )
    evidence = (
        complex_evidence("e-dividend", "dividend", "CNY/share"),
        complex_evidence("e-payout", "payout", "ratio"),
        complex_evidence("e-growth", "growth", "ratio"),
        complex_evidence("e-discount_rate", "discount_rate", "ratio"),
        complex_evidence("candidate-ddm", "ddm_candidate"),
    )
    rows = (
        cobs("h1-dividend", 1, "105", "dividend", "5", "assumption", "CNY/share"),
        cobs("h1-payout", 1, "105", "payout", "0.40", "assumption", "ratio"),
        cobs("h1-growth", 1, "105", "growth", "0.05", "assumption", "ratio"),
        cobs("h1-discount", 1, "105", "discount_rate", "0.10", "assumption", "ratio"),
        cobs("h2-dividend", 15, "105", "dividend", "5", "assumption", "CNY/share"),
        cobs("h2-payout", 15, "105", "payout", "0.40", "assumption", "ratio"),
        cobs("h2-growth", 15, "105", "growth", "0.05", "assumption", "ratio"),
        MarketValuationObservation(
            observation_id="h2-discount",
            observation_date=date(2026, 9, 15),
            known_at=datetime(2026, 9, 15, 2, tzinfo=timezone.utc),
            price=Decimal("105"),
            shares_outstanding=Decimal("1"),
            economic_variable="discount_rate",
            economic_value=Decimal("0.10"),
            unit="ratio",
            basis="assumption",
            evidence_ids=("missing-evidence",),
            source="test-fixture",
        ),
        cobs("current-dividend", None, "105", "dividend", "5", "assumption", "CNY/share"),
        cobs("current-payout", None, "105", "payout", "0.40", "assumption", "ratio"),
        cobs("current-growth", None, "105", "growth", "0.05", "assumption", "ratio"),
        cobs("current-discount", None, "105", "discount_rate", "0.10", "assumption", "ratio"),
    )
    with pytest.raises(ValueError, match="unknown evidence_id"):
        identify_market_models(
            complex_input(candidate_item, rows, evidence, "current-dividend")
        )
