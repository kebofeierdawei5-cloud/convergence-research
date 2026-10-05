from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Sequence

from .market_model_domain import (
    CandidateMarketModel,
    FeasibleSolution,
    FeasibleSolutionSet,
    FeasibleSolutionStatus,
    FitDiagnostic,
    HistoricalSupportState,
    RegimeInterpretationState,
    IdentifiabilityResult,
    IdentifiabilityState,
    MarketModelFamily,
    MarketObservableEvidence,
    ModelFit,
    ModelFitStatus,
    StabilityObservation,
    StabilityResult,
    StabilityState,
)


RATIO_FAMILIES = {
    MarketModelFamily.FORWARD_PE,
    MarketModelFamily.PS,
    MarketModelFamily.PB,
    MarketModelFamily.EV_EBITDA,
}

COMPLEX_FAMILIES = {
    MarketModelFamily.DCF,
    MarketModelFamily.DDM,
    MarketModelFamily.SOTP,
    MarketModelFamily.RNPV,
}

PRIMARY_VARIABLE = {
    MarketModelFamily.FORWARD_PE: "forward_eps",
    MarketModelFamily.PS: "revenue",
    MarketModelFamily.PB: "book_equity",
    MarketModelFamily.EV_EBITDA: "ebitda",
}


def _d(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


@dataclass(frozen=True)
class MarketValuationObservation:
    """Point-in-time observation used by the P3 market-model fitter.

    The observation is deliberately model-neutral; the fitter interprets the
    economic variable according to the candidate model family.
    """

    observation_id: str
    observation_date: date
    known_at: datetime
    price: Decimal
    shares_outstanding: Decimal
    economic_variable: str
    economic_value: Decimal
    unit: str
    basis: str
    evidence_ids: tuple[str, ...]
    source: str
    net_debt: Decimal = Decimal("0")

    def validate(self, cutoff_date: date) -> None:
        if not self.observation_id:
            raise ValueError("observation_id is required")
        if self.observation_date > cutoff_date:
            raise ValueError("observation_date is after cutoff")
        if self.known_at.date() > cutoff_date:
            raise ValueError("known_at is after cutoff")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be > 0")
        if not self.economic_variable:
            raise ValueError("economic_variable is required")
        if self.economic_value <= 0:
            raise ValueError("economic_value must be > 0")
        if not self.unit or not self.basis or not self.source:
            raise ValueError("unit, basis and source are required")
        if not self.evidence_ids:
            raise ValueError("evidence_ids are required")


@dataclass(frozen=True)
class MarketModelIdentificationInput:
    cutoff_date: date
    current_observation_id: str
    candidates: tuple[CandidateMarketModel, ...]
    observations: tuple[MarketValuationObservation, ...]
    evidence: tuple[MarketObservableEvidence, ...]
    stability_min_historical_points: int = 3

    def validate(self) -> None:
        if not self.current_observation_id:
            raise ValueError("current_observation_id is required")
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        if not self.observations:
            raise ValueError("observations are required")
        if self.stability_min_historical_points < 3:
            raise ValueError("stability_min_historical_points must be >= 3")

        candidate_ids = [candidate.model_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate model_id must be unique")

        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observation_id must be unique")
        if self.current_observation_id not in set(observation_ids):
            raise ValueError("current_observation_id not found in observations")

        evidence_ids = {item.evidence_id for item in self.evidence}
        for candidate in self.candidates:
            candidate.validate()
            missing = set(candidate.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(
                    f"candidate {candidate.model_id} references unknown evidence_ids: {sorted(missing)}"
                )
        for item in self.observations:
            item.validate(self.cutoff_date)
        for item in self.evidence:
            item.validate_pit(self.cutoff_date)


@dataclass(frozen=True)
class CandidateEvaluation:
    fit: ModelFit
    feasible_solution_set: FeasibleSolutionSet | None


def _multiple(observation: MarketValuationObservation, family: MarketModelFamily) -> Decimal:
    market_cap = observation.price * observation.shares_outstanding
    if family == MarketModelFamily.FORWARD_PE:
        return observation.price / observation.economic_value
    if family in {MarketModelFamily.PS, MarketModelFamily.PB}:
        return market_cap / observation.economic_value
    if family == MarketModelFamily.EV_EBITDA:
        return (market_cap + observation.net_debt) / observation.economic_value
    raise ValueError(f"no scalar historical multiple for {family.value}")


def _evidence_index(evidence: Iterable[MarketObservableEvidence]) -> dict[str, MarketObservableEvidence]:
    evidence_items = tuple(evidence)
    indexed = {item.evidence_id: item for item in evidence_items}
    if len(indexed) != len(evidence_items):
        raise ValueError("duplicate evidence_id")
    return indexed


def _observation_evidence_ids(
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
) -> tuple[str, ...]:
    ids: list[str] = []
    for observation in observations:
        for evidence_id in observation.evidence_ids:
            evidence = evidence_index.get(evidence_id)
            if evidence is None:
                raise ValueError(f"observation references unknown evidence_id: {evidence_id}")
            if evidence.variable != observation.economic_variable:
                raise ValueError(
                    f"observation evidence variable mismatch: {evidence_id} "
                    f"({evidence.variable} != {observation.economic_variable})"
                )
            if evidence.unit != observation.unit:
                raise ValueError(
                    f"observation evidence unit mismatch: {evidence_id} "
                    f"({evidence.unit} != {observation.unit})"
                )
            ids.append(evidence_id)
    return tuple(sorted(set(ids)))


def _candidate_observations(
    candidate: CandidateMarketModel,
    observations: Sequence[MarketValuationObservation],
) -> tuple[list[MarketValuationObservation], str | None]:
    expected = PRIMARY_VARIABLE.get(candidate.family)
    if expected is None:
        return [], None
    matched = [
        item for item in observations
        if item.economic_variable == expected
    ]
    return sorted(matched, key=lambda x: x.observation_date), expected


"""

P3-B complex-model implementation
-----------------------------------
The complex families use model-specific inverse equations against current price,
with historical implied-primary-variable ranges as the admissible constraint.

No generic implied-profit transformation is used.
"""

COMPLEX_REQUIRED_OBSERVABLES = {
    MarketModelFamily.DCF: (
        "fcf",
        "growth",
        "margin",
        "reinvestment",
        "terminal_value",
        "discount_rate",
    ),
    MarketModelFamily.DDM: (
        "dividend",
        "payout",
        "growth",
        "discount_rate",
    ),
    MarketModelFamily.SOTP: (
        "segment_value",
        "residual_value",
    ),
    MarketModelFamily.RNPV: (
        "pipeline_value",
        "probability",
        "timing",
        "discount_rate",
        "base_value",
    ),
}

COMPLEX_PRIMARY_VARIABLE = {
    MarketModelFamily.DCF: "fcf",
    MarketModelFamily.DDM: "dividend",
    MarketModelFamily.SOTP: "residual_value",
    MarketModelFamily.RNPV: "pipeline_value",
}


def _latest_by_variable(
    observations: Sequence[MarketValuationObservation],
) -> dict[str, MarketValuationObservation]:
    latest: dict[str, MarketValuationObservation] = {}
    for item in observations:
        existing = latest.get(item.economic_variable)
        if existing is None or (item.known_at, item.observation_id) > (
            existing.known_at,
            existing.observation_id,
        ):
            latest[item.economic_variable] = item
    return latest


def _ratio_in_unit_interval(value: Decimal, field: str) -> None:
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field} must be within [0,1]")


def _group_complex_observations(
    observations: Sequence[MarketValuationObservation],
) -> dict[date, tuple[MarketValuationObservation, ...]]:
    grouped: dict[date, list[MarketValuationObservation]] = {}
    for item in observations:
        grouped.setdefault(item.observation_date, []).append(item)
    return {
        observation_date: tuple(sorted(items, key=lambda x: (x.known_at, x.observation_id))
        )
        for observation_date, items in grouped.items()
    }


def _complex_groups(
    observations: Sequence[MarketValuationObservation],
    current_observation_date: date,
) -> tuple[list[tuple[date, tuple[MarketValuationObservation, ...]]], tuple[date, tuple[MarketValuationObservation, ...]] | None]:
    grouped = _group_complex_observations(observations)
    current = grouped.get(current_observation_date)
    historical = sorted(
        (
            (observation_date, items)
            for observation_date, items in grouped.items()
            if observation_date < current_observation_date
        ),
        key=lambda x: x[0],
    )
    return historical, ((current_observation_date, current) if current else None)


def _complex_evidence_ids(
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    candidate: CandidateMarketModel,
) -> tuple[str, ...]:
    observation_ids = _observation_evidence_ids(observations, evidence_index)
    return tuple(sorted(set(observation_ids).union(candidate.evidence_ids)))


def _solve_dcf_primary(
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
    latest = _latest_by_variable(items)
    required = COMPLEX_REQUIRED_OBSERVABLES[MarketModelFamily.DCF]
    missing = [name for name in required if name not in latest]
    if missing:
        raise LookupError(f"missing DCF variables: {sorted(missing)}")

    fcf = latest["fcf"]
    growth = latest["growth"].economic_value
    margin = latest["margin"].economic_value
    reinvestment = latest["reinvestment"].economic_value
    terminal_value_observation = latest["terminal_value"]
    terminal_value = terminal_value_observation.economic_value
    discount_rate = latest["discount_rate"].economic_value

    if fcf.economic_value <= 0 or terminal_value <= 0:
        raise ValueError("DCF fcf and terminal_value must be > 0")
    if growth <= Decimal("-1"):
        raise ValueError("DCF growth must be > -1")
    if discount_rate <= growth:
        raise ValueError("DCF discount_rate must be > growth")
    _ratio_in_unit_interval(margin, "DCF margin")
    _ratio_in_unit_interval(reinvestment, "DCF reinvestment")
    if fcf.unit != terminal_value_observation.unit:
        raise ValueError("DCF fcf and terminal_value units must match")
    if growth.as_tuple().exponent < -18 or discount_rate.as_tuple().exponent < -18:
        raise ValueError("DCF rate precision exceeds supported bound")

    enterprise_value = (
        latest["_price"].economic_value * latest["_shares"].economic_value
        + latest["_net_debt"].economic_value
    )
    if enterprise_value <= 0:
        raise ValueError("DCF enterprise value must be > 0")
    implied_fcf = enterprise_value * (discount_rate - growth) / (Decimal("1") + growth)
    derived_terminal_value = implied_fcf * (Decimal("1") + growth) / (discount_rate - growth)

    diagnostics = {
        "observed_fcf": fcf.economic_value,
        "observed_margin": margin,
        "observed_reinvestment": reinvestment,
        "observed_terminal_value": terminal_value,
        "derived_terminal_value": derived_terminal_value,
        "growth": growth,
        "discount_rate": discount_rate,
    }
    return implied_fcf, diagnostics, tuple(
        evidence_id
        for item in items
        for evidence_id in item.evidence_ids
    )


def _solve_ddm_primary(
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
    latest = _latest_by_variable(items)
    required = COMPLEX_REQUIRED_OBSERVABLES[MarketModelFamily.DDM]
    missing = [name for name in required if name not in latest]
    if missing:
        raise LookupError(f"missing DDM variables: {sorted(missing)}")

    dividend = latest["dividend"]
    payout = latest["payout"].economic_value
    growth = latest["growth"].economic_value
    discount_rate = latest["discount_rate"].economic_value

    if dividend.economic_value <= 0:
        raise ValueError("DDM dividend must be > 0")
    _ratio_in_unit_interval(payout, "DDM payout")
    if growth <= Decimal("-1"):
        raise ValueError("DDM growth must be > -1")
    if discount_rate <= growth:
        raise ValueError("DDM discount_rate must be > growth")
    external_items = tuple(item for item in items if not item.economic_variable.startswith("_"))
    price = _market_context(external_items)[0]
    implied_dividend = price * (discount_rate - growth) / (Decimal("1") + growth)

    diagnostics = {
        "observed_dividend": dividend.economic_value,
        "payout": payout,
        "growth": growth,
        "discount_rate": discount_rate,
        "implied_dividend": implied_dividend,
    }
    return implied_dividend, diagnostics, tuple(
        evidence_id
        for item in items
        for evidence_id in item.evidence_ids
    )


def _parse_segment_basis(basis: str) -> str:
    if not basis.startswith("segment:") or len(basis) == len("segment:"):
        raise ValueError("SOTP segment basis must use segment:<id>")
    return basis.split(":", 1)[1]


def _solve_sotp_primary(
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
    segments = [
        item for item in items
        if item.economic_variable == "segment_value"
    ]
    if not segments:
        raise LookupError("missing SOTP segment_value observations")

    seen: set[str] = set()
    segment_total = Decimal("0")
    units: set[str] = set()
    evidence_ids: list[str] = []
    for item in segments:
        segment_id = _parse_segment_basis(item.basis)
        if segment_id in seen:
            raise ValueError(f"duplicate SOTP segment: {segment_id}")
        seen.add(segment_id)
        if item.economic_value <= 0:
            raise ValueError("SOTP segment_value must be > 0")
        units.add(item.unit)
        segment_total += item.economic_value
        evidence_ids.extend(item.evidence_ids)
    if len(units) != 1:
        raise ValueError("SOTP segment units must match")

    external_items = tuple(item for item in items if not item.economic_variable.startswith("_"))
    market_price, shares_outstanding, _ = _market_context(external_items)
    market_cap = market_price * shares_outstanding
    implied_residual = market_cap - segment_total
    return implied_residual, {
        "segment_total": segment_total,
        "implied_residual": implied_residual,
    }, tuple(sorted(set(evidence_ids)))


def _parse_pipeline_basis(basis: str) -> str:
    if not basis.startswith("pipeline:") or len(basis) == len("pipeline:"):
        raise ValueError("rNPV pipeline basis must use pipeline:<id>")
    return basis.split(":", 1)[1]


def _solve_rnpv_primary(
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
    latest = _latest_by_variable(items)
    required = COMPLEX_REQUIRED_OBSERVABLES[MarketModelFamily.RNPV]
    for name in ("discount_rate", "base_value"):
        if name not in latest:
            raise LookupError(f"missing rNPV {name}")

    pipelines = [
        item for item in items
        if item.economic_variable == "pipeline_value"
    ]
    probabilities = [
        item for item in items
        if item.economic_variable == "probability"
    ]
    timings = [
        item for item in items
        if item.economic_variable == "timing"
    ]
    if not pipelines or not probabilities or not timings:
        raise LookupError("rNPV requires pipeline_value, probability and timing")
    if len(pipelines) != len(probabilities) or len(pipelines) != len(timings):
        raise ValueError("rNPV pipeline/probability/timing counts must match")

    discount_rate = latest["discount_rate"].economic_value
    base_value = latest["base_value"].economic_value
    if discount_rate <= Decimal("-1"):
        raise ValueError("rNPV discount_rate must be > -1")
    if base_value < Decimal("0"):
        raise ValueError("rNPV base_value must be >= 0")

    pipeline_total = Decimal("0")
    observed_risk_adjusted_value = Decimal("0")
    evidence_ids: list[str] = []
    for pipe, probability, timing in zip(
        sorted(pipelines, key=lambda x: _parse_pipeline_basis(x.basis)),
        sorted(probabilities, key=lambda x: _parse_pipeline_basis(x.basis)),
        sorted(timings, key=lambda x: _parse_pipeline_basis(x.basis)),
    ):
        pipeline_id = _parse_pipeline_basis(pipe.basis)
        if pipeline_id != _parse_pipeline_basis(probability.basis) or pipeline_id != _parse_pipeline_basis(timing.basis):
            raise ValueError("rNPV pipeline basis IDs must align")
        if pipe.economic_value <= 0:
            raise ValueError("rNPV pipeline_value must be > 0")
        _ratio_in_unit_interval(probability.economic_value, f"rNPV probability {pipeline_id}")
        if timing.economic_value < Decimal("0"):
            raise ValueError("rNPV timing must be >= 0")
        if pipe.unit != latest["base_value"].unit:
            raise ValueError("rNPV pipeline_value and base_value units must match")
        denominator = (Decimal("1") + discount_rate) ** timing.economic_value
        if denominator <= 0:
            raise ValueError("rNPV timing/discount rate gives invalid denominator")
        weight = probability.economic_value / denominator
        observed_risk_adjusted_value += pipe.economic_value * weight
        pipeline_total += pipe.economic_value
        evidence_ids.extend(pipe.evidence_ids)
        evidence_ids.extend(probability.evidence_ids)
        evidence_ids.extend(timing.evidence_ids)

    if observed_risk_adjusted_value <= 0 or pipeline_total <= 0:
        raise ValueError("rNPV observed risk-adjusted pipeline value must be > 0")
    external_items = tuple(item for item in items if not item.economic_variable.startswith("_"))
    market_price, shares_outstanding, net_debt = _market_context(external_items)
    enterprise_value = market_price * shares_outstanding + net_debt
    residual_value = enterprise_value - base_value
    if residual_value < Decimal("0"):
        raise ValueError("rNPV market value is below stated base_value")
    observed_composition_weight = observed_risk_adjusted_value / pipeline_total
    implied_pipeline_value = residual_value / observed_composition_weight

    return implied_pipeline_value, {
        "observed_pipeline_total": pipeline_total,
        "observed_risk_adjusted_pipeline_value": observed_risk_adjusted_value,
        "observed_composition_weight": observed_composition_weight,
        "base_value": base_value,
        "implied_pipeline_value": implied_pipeline_value,
    }, tuple(sorted(set(
        evidence_ids
        + list(latest["discount_rate"].evidence_ids)
        + list(latest["base_value"].evidence_ids)
    )))


def _model_specific_items(
    family: MarketModelFamily,
    items: Sequence[MarketValuationObservation],
) -> tuple[MarketValuationObservation, ...]:
    allowed = set(COMPLEX_REQUIRED_OBSERVABLES[family])
    if family == MarketModelFamily.SOTP:
        allowed = {"segment_value"}
    selected = tuple(
        item for item in items
        if item.economic_variable in allowed
    )
    if not selected:
        raise LookupError(f"missing {family.value} model observations")
    return selected


def _market_context(
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, Decimal, Decimal]:
    prices = {item.price for item in items}
    shares = {item.shares_outstanding for item in items}
    net_debts = {item.net_debt for item in items}
    if len(prices) != 1:
        raise ValueError("model observations at the same date must share one market price")
    if len(shares) != 1:
        raise ValueError("model observations at the same date must share one share-count anchor")
    if len(net_debts) != 1:
        raise ValueError("model observations at the same date must share one net-debt anchor")
    return next(iter(prices)), next(iter(shares)), next(iter(net_debts))


def _solve_complex_primary(
    family: MarketModelFamily,
    items: Sequence[MarketValuationObservation],
) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
    model_items = _model_specific_items(family, items)
    price, shares, net_debt = _market_context(model_items)

    # The solver helpers accept price/shares/net debt as internal entries so
    # existing typed observations remain unchanged.
    augmented = model_items + (
        MarketValuationObservation(
            observation_id="__price",
            observation_date=items[0].observation_date,
            known_at=items[0].known_at,
            price=Decimal("1"),
            shares_outstanding=Decimal("1"),
            economic_variable="_price",
            economic_value=price,
            unit="price",
            basis="internal",
            evidence_ids=(),
            source="internal",
        ),
        MarketValuationObservation(
            observation_id="__shares",
            observation_date=items[0].observation_date,
            known_at=items[0].known_at,
            price=Decimal("1"),
            shares_outstanding=Decimal("1"),
            economic_variable="_shares",
            economic_value=shares,
            unit="shares",
            basis="internal",
            evidence_ids=(),
            source="internal",
        ),
        MarketValuationObservation(
            observation_id="__net_debt",
            observation_date=items[0].observation_date,
            known_at=items[0].known_at,
            price=Decimal("1"),
            shares_outstanding=Decimal("1"),
            economic_variable="_net_debt",
            economic_value=net_debt,
            unit="CNY",
            basis="internal",
            evidence_ids=(),
            source="internal",
        ),
    )

    if family == MarketModelFamily.DCF:
        return _solve_dcf_primary(augmented)
    if family == MarketModelFamily.DDM:
        return _solve_ddm_primary(augmented)
    if family == MarketModelFamily.SOTP:
        return _solve_sotp_primary(augmented)
    if family == MarketModelFamily.RNPV:
        return _solve_rnpv_primary(augmented)
    raise ValueError(f"unsupported complex family: {family.value}")


def _fit_complex_candidate(
    candidate: CandidateMarketModel,
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    current_observation_date: date,
    required_historical_points: int = 2,
) -> CandidateEvaluation:
    # Complex-model observations must remain evidence-backed just like P3-A.
    _observation_evidence_ids(observations, evidence_index)
    historical, current_group = _complex_groups(observations, current_observation_date)
    candidate_evidence_ids = tuple(sorted(set(candidate.evidence_ids)))
    complex_required = COMPLEX_REQUIRED_OBSERVABLES[candidate.family]

    if current_group is None:
        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:current_coverage",
            name="current_complex_model_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=candidate_evidence_ids,
            notes="No current-date observation group exists.",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=candidate_evidence_ids,
            constraints=("CURRENT_OBSERVATION_REQUIRED",),
            historical_support=HistoricalSupportState.INSUFFICIENT_EVIDENCE,
        )
        return CandidateEvaluation(fit, None)

    if len(historical) < required_historical_points:
        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_coverage",
            name="historical_complex_model_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=candidate_evidence_ids,
            notes=f"requires at least {required_historical_points} historical observation dates",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=candidate_evidence_ids,
            constraints=("MIN_HISTORICAL_DATES",),
        )
        return CandidateEvaluation(fit, None)

    def solve(items: Sequence[MarketValuationObservation]) -> tuple[Decimal, dict[str, Decimal], tuple[str, ...]]:
        return _solve_complex_primary(candidate.family, items)

    historical_primary: list[Decimal] = []
    historical_evidence: list[str] = []
    diagnostics: list[FitDiagnostic] = []
    try:
        for observation_date, items in historical:
            value, detail, ids = solve(items)
            historical_primary.append(value)
            historical_evidence.extend(ids)
    except LookupError as exc:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_coverage",
            name="historical_required_variables",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            notes=str(exc),
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=tuple(diagnostics),
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            constraints=tuple(f"REQUIRES_{name.upper()}" for name in complex_required),
        )
        return CandidateEvaluation(fit, None)
    except ValueError as exc:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_constraints",
            name="historical_model_constraints",
            status="INFEASIBLE",
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            notes=str(exc),
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            constraints=("HISTORICAL_MODEL_CONSTRAINTS",),
        )
        return CandidateEvaluation(fit, None)

    try:
        current_primary, current_detail, current_ids = solve(current_group[1])
    except LookupError as exc:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:current_variables",
            name="current_required_variables",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            notes=str(exc),
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=tuple(diagnostics),
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            constraints=tuple(f"REQUIRES_{name.upper()}" for name in complex_required),
        )
        return CandidateEvaluation(fit, None)
    except ValueError as exc:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:current_constraints",
            name="current_model_constraints",
            status="INFEASIBLE",
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            notes=str(exc),
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=tuple(sorted(set(historical_evidence).union(candidate_evidence_ids))),
            constraints=("CURRENT_MODEL_CONSTRAINTS",),
        )
        return CandidateEvaluation(fit, None)

    historical_low = min(historical_primary)
    historical_high = max(historical_primary)
    within_historical_range = historical_low <= current_primary <= historical_high
    all_evidence = tuple(sorted(set(
        historical_evidence
        + list(current_ids)
        + list(candidate_evidence_ids)
    )))

    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:historical_implied_range",
        name="historical_implied_primary_range",
        status="PASS",
        evidence_ids=all_evidence,
        notes=f"range=[{historical_low},{historical_high}] from {len(historical_primary)} historical dates",
    ))
    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:current_consistency",
        name="current_complex_model_consistency",
        status="PASS" if within_historical_range else "INFEASIBLE",
        evidence_ids=all_evidence,
        notes=f"current_implied_{COMPLEX_PRIMARY_VARIABLE[candidate.family]}={current_primary}; within_historical_range={within_historical_range}",
    ))

    if not within_historical_range:
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_evidence,
            constraints=("CURRENT_IMPLIED_PRIMARY_WITHIN_HISTORICAL_RANGE",),
        )
        return CandidateEvaluation(fit, None)

    solution = FeasibleSolution(
        economic_variable=COMPLEX_PRIMARY_VARIABLE[candidate.family],
        unit=(
            current_group[1][0].unit
            if candidate.family != MarketModelFamily.DCF
            else next(item for item in current_group[1] if item.economic_variable == "fcf").unit
        ),
        basis=(
            "current_price_with_historical_dcf_implied_fcf_range"
            if candidate.family == MarketModelFamily.DCF
            else "current_price_with_historical_ddm_implied_dividend_range"
            if candidate.family == MarketModelFamily.DDM
            else "current_market_cap_with_historical_sotp_implied_residual_range"
            if candidate.family == MarketModelFamily.SOTP
            else "current_market_value_with_historical_rnpv_implied_pipeline_range"
        ),
        model_id=candidate.model_id,
        value=current_primary,
        evidence_ids=all_evidence,
    )
    solution_set = FeasibleSolutionSet(
        model_id=candidate.model_id,
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(solution,),
        constraint_ids=(
            "MODEL_SPECIFIC_INVERSE",
            "MIN_HISTORICAL_DATES",
            "CURRENT_IMPLIED_PRIMARY_WITHIN_HISTORICAL_RANGE",
        ),
        evidence_ids=all_evidence,
        basis=(
            "historical implied primary-variable range is the admissible model constraint; "
            "current price is inverted under the model's contemporaneous assumptions"
        ),
    )
    solution_set.validate()

    fit = ModelFit(
        model_id=candidate.model_id,
        status=ModelFitStatus.FEASIBLE,
        diagnostics=tuple(diagnostics),
        evidence_ids=all_evidence,
        constraints=(
            "MODEL_SPECIFIC_INVERSE",
            "MIN_HISTORICAL_DATES",
            "CURRENT_IMPLIED_PRIMARY_WITHIN_HISTORICAL_RANGE",
        ),
    )
    fit.validate()
    return CandidateEvaluation(fit, solution_set)


def _support_state(current_value: Decimal, historical_low: Decimal, historical_high: Decimal) -> HistoricalSupportState:
    if current_value < historical_low:
        return HistoricalSupportState.BELOW_HISTORICAL_RANGE
    if current_value > historical_high:
        return HistoricalSupportState.ABOVE_HISTORICAL_RANGE
    return HistoricalSupportState.IN_RANGE


def _fit_candidate(
    candidate: CandidateMarketModel,
    observations: Sequence[MarketValuationObservation],
    evidence_index: Mapping[str, MarketObservableEvidence],
    current_observation_date: date,
    required_historical_points: int = 2,
) -> CandidateEvaluation:
    if candidate.family in COMPLEX_FAMILIES:
        return _fit_complex_candidate(
            candidate,
            observations,
            evidence_index,
            current_observation_date,
            required_historical_points,
        )

        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:support",
            name="production_solver_support",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=(),
            notes="P3 baseline has no model-specific inverse solver for this family.",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=(),
            constraints=("MODEL_SPECIFIC_SOLVER_REQUIRED",),
        )
        return CandidateEvaluation(fit, None)

    matched, expected_variable = _candidate_observations(candidate, observations)
    if expected_variable is None:
        raise ValueError(f"no primary economic variable defined for {candidate.family.value}")

    current_candidates = [
        item for item in matched
        if item.observation_date == current_observation_date
    ]
    if not current_candidates:
        diagnostic = FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:current_coverage",
            name="current_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=_observation_evidence_ids(matched, evidence_index),
            notes="No current-date observation exists for the candidate's economic variable.",
        )
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=(diagnostic,),
            evidence_ids=diagnostic.evidence_ids,
            constraints=("CURRENT_OBSERVATION_REQUIRED",),
        )
        return CandidateEvaluation(fit, None)
    current = max(current_candidates, key=lambda x: (x.known_at, x.observation_id))
    historical = [item for item in matched if item.observation_date < current_observation_date]

    all_ids = _observation_evidence_ids(matched, evidence_index)
    diagnostics: list[FitDiagnostic] = []

    if len(historical) < required_historical_points:
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_coverage",
            name="historical_coverage",
            status="INSUFFICIENT_EVIDENCE",
            evidence_ids=all_ids,
            notes=f"requires at least {required_historical_points} historical observations",
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INSUFFICIENT_EVIDENCE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("MIN_HISTORICAL_POINTS",),
        )
        return CandidateEvaluation(fit, None)

    multiples = [_multiple(item, candidate.family) for item in historical]
    if any(value <= 0 for value in multiples):
        diagnostics.append(FitDiagnostic(
            diagnostic_id=f"{candidate.model_id}:historical_validity",
            name="historical_multiple_validity",
            status="INFEASIBLE",
            evidence_ids=all_ids,
            notes="historical market multiple is non-positive",
        ))
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.INFEASIBLE,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("POSITIVE_HISTORICAL_MULTIPLE",),
        )
        return CandidateEvaluation(fit, None)

    historical_low = min(multiples)
    historical_high = max(multiples)
    current_multiple = _multiple(current, candidate.family)
    support_state = _support_state(current_multiple, historical_low, historical_high)
    current_consistent = support_state == HistoricalSupportState.IN_RANGE

    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:historical_range",
        name="historical_market_multiple_range",
        status="PASS",
        evidence_ids=all_ids,
        notes=f"range=[{historical_low},{historical_high}] from {len(historical)} historical observations",
    ))
    diagnostics.append(FitDiagnostic(
        diagnostic_id=f"{candidate.model_id}:current_consistency",
        name="current_historical_support",
        status="PASS" if current_consistent else "OUTSIDE_HISTORICAL_SUPPORT",
        evidence_ids=all_ids,
        notes=(
            f"current_multiple={current_multiple}; historical_range="
            f"[{historical_low},{historical_high}]; support_state={support_state.value}"
        ),
    ))

    if not current_consistent:
        fit = ModelFit(
            model_id=candidate.model_id,
            status=ModelFitStatus.OUTSIDE_HISTORICAL_SUPPORT,
            diagnostics=tuple(diagnostics),
            evidence_ids=all_ids,
            constraints=("CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",),
            historical_support=support_state,
            regime_interpretation=RegimeInterpretationState.POSSIBLE_REGIME_SHIFT,
        )
        fit.validate()
        return CandidateEvaluation(fit, None)

    price = current.price
    if candidate.family == MarketModelFamily.FORWARD_PE:
        implied_low = price / historical_high
        implied_high = price / historical_low
    else:
        current_market_cap = current.price * current.shares_outstanding
        current_ev = current_market_cap + current.net_debt
        denominator = (historical_high, historical_low)
        implied_low = current_ev / denominator[0]
        implied_high = current_ev / denominator[1]

    solution = FeasibleSolution(
        economic_variable=expected_variable,
        unit=current.unit,
        basis=f"current_price_with_historical_{candidate.family.value}_multiple_range",
        model_id=candidate.model_id,
        range_low=implied_low,
        range_high=implied_high,
        evidence_ids=all_ids,
    )
    solution_set = FeasibleSolutionSet(
        model_id=candidate.model_id,
        status=FeasibleSolutionStatus.NONEMPTY,
        solutions=(solution,),
        constraint_ids=(
            "HISTORICAL_MULTIPLE_RANGE",
            "CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",
        ),
        evidence_ids=all_ids,
        basis=f"current market price divided by historical {candidate.family.value} multiple range",
    )
    solution_set.validate()

    fit = ModelFit(
        model_id=candidate.model_id,
        status=ModelFitStatus.FEASIBLE,
        diagnostics=tuple(diagnostics),
        evidence_ids=all_ids,
        constraints=(
            "MIN_HISTORICAL_POINTS",
            "CURRENT_MULTIPLE_WITHIN_HISTORICAL_RANGE",
        ),
    )
    fit.validate()
    return CandidateEvaluation(fit, solution_set)


def _identify(
    evaluations: Sequence[CandidateEvaluation],
) -> IdentifiabilityResult:
    feasible = tuple(sorted(
        evaluation.fit.model_id
        for evaluation in evaluations
        if evaluation.fit.status == ModelFitStatus.FEASIBLE
        and evaluation.feasible_solution_set is not None
    ))
    insufficient = any(
        evaluation.fit.status == ModelFitStatus.INSUFFICIENT_EVIDENCE
        for evaluation in evaluations
    )
    evidence_ids = tuple(sorted(set(
        evidence_id
        for evaluation in evaluations
        for evidence_id in evaluation.fit.evidence_ids
    )))

    if len(feasible) >= 2:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.AMBIGUOUS,
            feasible_model_ids=feasible,
            selected_model_id=None,
            competing_model_ids=feasible[1:],
            evidence_ids=evidence_ids,
            rationale="Multiple candidate models remain materially feasible under the same evidence boundary.",
        )
    elif len(feasible) == 1 and insufficient:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.INSUFFICIENT_EVIDENCE,
            feasible_model_ids=feasible,
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="One candidate is feasible, but another candidate remains unevaluable; uniqueness cannot be established conservatively.",
        )
    elif len(feasible) == 1:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.IDENTIFIABLE,
            feasible_model_ids=feasible,
            selected_model_id=feasible[0],
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="Exactly one candidate model has sufficient historical evidence and current consistency.",
        )
    elif insufficient:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.INSUFFICIENT_EVIDENCE,
            feasible_model_ids=(),
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="At least one candidate lacks sufficient model-specific evidence and no candidate is currently identifiable.",
        )
    else:
        result = IdentifiabilityResult(
            state=IdentifiabilityState.UNIDENTIFIABLE,
            feasible_model_ids=(),
            selected_model_id=None,
            competing_model_ids=(),
            evidence_ids=evidence_ids,
            rationale="All admitted candidates are infeasible under the current evidence and constraints.",
        )
    result.validate()
    return result


def _stability(
    inp: MarketModelIdentificationInput,
    full_evaluations: Sequence[CandidateEvaluation],
    full_ident: IdentifiabilityResult,
) -> StabilityResult:
    anchor = next(
        item for item in inp.observations
        if item.observation_id == inp.current_observation_id
    )
    current_observation_date = anchor.observation_date
    current_observations = tuple(
        item for item in inp.observations
        if item.observation_date == current_observation_date
    )
    historical = sorted(
        (item for item in inp.observations if item.observation_date < current_observation_date),
        key=lambda x: (x.observation_date, x.known_at, x.observation_id),
    )

    # Complex models are multi-variable observations: a historical date is the
    # perturbation unit. Dropping one row would create an artificial missing-
    # variable failure rather than test temporal/regime stability.
    date_grouped = any(candidate.family in COMPLEX_FAMILIES for candidate in inp.candidates)
    if date_grouped:
        grouped: dict[date, tuple[MarketValuationObservation, ...]] = {}
        for item in historical:
            grouped.setdefault(item.observation_date, tuple())
            grouped[item.observation_date] = grouped[item.observation_date] + (item,)
        perturbation_units = [
            (observation_date, items)
            for observation_date, items in sorted(grouped.items())
        ]
        unit_count = len(perturbation_units)
        full_window = historical
        if unit_count <= inp.stability_min_historical_points:
            result = StabilityResult(
                state=StabilityState.INSUFFICIENT_EVIDENCE,
                assessment_method="leave_one_out_historical_date",
                observations=(),
                evidence_ids=full_ident.evidence_ids,
                rationale=f"requires at least {inp.stability_min_historical_points} historical dates",
            )
            result.validate()
            return result
        windows = [full_window]
        window_labels = ["full historical set"]
        for observation_date, _items in perturbation_units:
            remaining = tuple(
                item for item in historical
                if item.observation_date != observation_date
            )
            if len({item.observation_date for item in remaining}) >= inp.stability_min_historical_points:
                windows.append(remaining)
                window_labels.append(f"leave out historical date {observation_date.isoformat()}")
    else:
        if len(historical) <= inp.stability_min_historical_points:
            result = StabilityResult(
                state=StabilityState.INSUFFICIENT_EVIDENCE,
                assessment_method="leave_one_out_historical_window",
                observations=(),
                evidence_ids=full_ident.evidence_ids,
                rationale=f"requires at least {inp.stability_min_historical_points} historical observations",
            )
            result.validate()
            return result
        windows = [historical]
        window_labels = ["full historical set"]
        for index in range(len(historical)):
            remaining = historical[:index] + historical[index + 1:]
            if len(remaining) >= inp.stability_min_historical_points:
                windows.append(remaining)
                window_labels.append(f"leave out {historical[index].observation_id}")

    observations: list[StabilityObservation] = []
    state_signature: list[tuple[str, tuple[str, ...]]] = [
        (full_ident.state.value, full_ident.feasible_model_ids)
    ]

    for index, historical_window in enumerate(windows):
        window_observations = tuple(historical_window) + current_observations
        evaluations = [
            _fit_candidate(candidate, window_observations, _evidence_index(inp.evidence), current_observation_date)
            for candidate in inp.candidates
        ]
        ident = _identify(evaluations)
        state_signature.append((ident.state.value, ident.feasible_model_ids))
        observations.append(StabilityObservation(
            perturbation_id=f"loo-{index}",
            perturbation="full historical set" if index == 0 else f"leave out {historical[index - 1].observation_id}",
            resulting_state=StabilityState.STABLE if (
                ident.state == full_ident.state
                and ident.feasible_model_ids == full_ident.feasible_model_ids
                and ident.selected_model_id == full_ident.selected_model_id
            ) else StabilityState.UNSTABLE,
            selected_model_id=ident.selected_model_id,
        ))

    stable = all(
        state == full_ident.state.value and feasible == full_ident.feasible_model_ids
        for state, feasible in state_signature
    )
    result = StabilityResult(
        state=StabilityState.STABLE if stable else StabilityState.UNSTABLE,
        assessment_method="leave_one_out_historical_window",
        observations=tuple(observations),
        evidence_ids=full_ident.evidence_ids,
        rationale=(
            "Market-model identifiability is invariant across the full and admissible leave-one-out historical windows."
            if stable else
            "Market-model identifiability changes under an admissible historical-window perturbation."
        ),
    )
    result.validate()
    return result


def identify_market_models(inp: MarketModelIdentificationInput) -> dict[str, object]:
    """Evidence-backed P3 identification for ratio and complex model families.

    Ratio models use historical multiple ranges; DCF/DDM/SOTP/rNPV use their
    own inverse equations with model-specific semantic variables. No generic
    implied-profit transformation, numeric score, or LLM judgment selects a
    winner.
    """

    inp.validate()
    evidence_index = _evidence_index(inp.evidence)

    evaluations = [
        _fit_candidate(
            candidate,
            inp.observations,
            evidence_index,
            next(
                item.observation_date
                for item in inp.observations
                if item.observation_id == inp.current_observation_id
            ),
        )
        for candidate in inp.candidates
    ]
    ident = _identify(evaluations)
    stability = _stability(inp, evaluations, ident)

    return {
        "status": "PASS",
        "method": "model_specific_inverse_v0.2",
        "identifiability": ident,
        "stability": stability,
        "evaluations": tuple(evaluations),
    }
