from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping


class MarketModelFamily(str, Enum):
    FORWARD_PE = "forward_pe"
    PS = "ps"
    PB = "pb"
    EV_EBITDA = "ev_ebitda"
    DCF = "dcf"
    DDM = "ddm"
    SOTP = "sotp"
    RNPV = "rnpv"


class ModelFitStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    OUTSIDE_HISTORICAL_SUPPORT = "OUTSIDE_HISTORICAL_SUPPORT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTED = "CONTRADICTED"


class HistoricalSupportState(str, Enum):
    IN_RANGE = "IN_RANGE"
    BELOW_HISTORICAL_RANGE = "BELOW_HISTORICAL_RANGE"
    ABOVE_HISTORICAL_RANGE = "ABOVE_HISTORICAL_RANGE"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RegimeInterpretationState(str, Enum):
    NOT_ASSESSED = "NOT_ASSESSED"
    POSSIBLE_REGIME_SHIFT = "POSSIBLE_REGIME_SHIFT"
    VERIFIED_REGIME_SHIFT = "VERIFIED_REGIME_SHIFT"
    VERIFIED_MODEL_FAILURE = "VERIFIED_MODEL_FAILURE"


class FeasibleSolutionStatus(str, Enum):
    NONEMPTY = "NONEMPTY"
    EMPTY = "EMPTY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class IdentifiabilityState(str, Enum):
    IDENTIFIABLE = "IDENTIFIABLE"
    AMBIGUOUS = "AMBIGUOUS"
    UNIDENTIFIABLE = "UNIDENTIFIABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class StabilityState(str, Enum):
    STABLE = "STABLE"
    UNSTABLE = "UNSTABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


MODEL_SEMANTICS: Mapping[MarketModelFamily, tuple[tuple[str, ...], tuple[str, ...]]] = {
    MarketModelFamily.FORWARD_PE: (("forward_eps",), ("forward_eps",)),
    MarketModelFamily.PS: (("revenue",), ("revenue",)),
    MarketModelFamily.PB: (("book_equity",), ("book_equity",)),
    MarketModelFamily.EV_EBITDA: (("ebitda", "enterprise_value"), ("ebitda", "enterprise_value")),
    MarketModelFamily.DCF: (
        ("fcf", "growth", "margin", "reinvestment", "terminal_value"),
        ("fcf", "growth", "margin", "reinvestment", "terminal_value"),
    ),
    MarketModelFamily.DDM: (
        ("dividend", "payout", "growth", "discount_rate"),
        ("dividend", "payout", "growth", "discount_rate"),
    ),
    MarketModelFamily.SOTP: (
        ("segment_value", "residual_value"),
        ("segment_value", "residual_value"),
    ),
    MarketModelFamily.RNPV: (
        ("pipeline_value", "probability", "timing"),
        ("pipeline_value", "probability", "timing"),
    ),
}


@dataclass(frozen=True)
class MarketObservableEvidence:
    evidence_id: str
    variable: str
    unit: str
    basis: str
    observation_date: date
    known_at: datetime
    source: str
    value: Decimal | None = None
    range_low: Decimal | None = None
    range_high: Decimal | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if not self.variable:
            raise ValueError("variable is required")
        if not self.unit:
            raise ValueError("unit is required")
        if not self.basis:
            raise ValueError("basis is required")
        if not self.source:
            raise ValueError("source is required")
        if self.value is None and (self.range_low is None or self.range_high is None):
            raise ValueError("evidence must contain a point value or a complete range")
        if self.value is not None and self.range_low is not None:
            raise ValueError("point value and range cannot both be supplied")
        if self.range_low is not None and self.range_low > self.range_high:
            raise ValueError("range_low must be <= range_high")

    def validate_pit(self, cutoff_date: date) -> None:
        self.validate()
        if self.observation_date > cutoff_date:
            raise ValueError("observation_date is after cutoff")
        if self.known_at.date() > cutoff_date:
            raise ValueError("known_at is after cutoff")


@dataclass(frozen=True)
class CandidateMarketModel:
    model_id: str
    family: MarketModelFamily
    required_economic_variables: tuple[str, ...]
    required_observable_variables: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    admission_basis: str
    inverse_solvable: bool = False

    def validate(self) -> None:
        if not self.model_id:
            raise ValueError("model_id is required")
        if not self.required_economic_variables:
            raise ValueError("required_economic_variables cannot be empty")
        if not self.required_observable_variables:
            raise ValueError("required_observable_variables cannot be empty")
        if not self.admission_basis:
            raise ValueError("admission_basis is required")
        if not self.evidence_ids:
            raise ValueError(
                "candidate market model admission requires evidence_ids; inverse solvability alone is insufficient"
            )

        expected_economic, expected_observable = MODEL_SEMANTICS[self.family]
        missing_economic = set(expected_economic) - set(self.required_economic_variables)
        missing_observable = set(expected_observable) - set(self.required_observable_variables)
        if missing_economic:
            raise ValueError(
                f"{self.family.value} missing required economic variables: {sorted(missing_economic)}"
            )
        if missing_observable:
            raise ValueError(
                f"{self.family.value} missing required observable variables: {sorted(missing_observable)}"
            )


@dataclass(frozen=True)
class FitDiagnostic:
    diagnostic_id: str
    name: str
    status: str
    evidence_ids: tuple[str, ...] = ()
    notes: str = ""

    def validate(self) -> None:
        if not self.diagnostic_id or not self.name or not self.status:
            raise ValueError("diagnostic_id, name and status are required")


@dataclass(frozen=True)
class ModelFit:
    model_id: str
    status: ModelFitStatus
    diagnostics: tuple[FitDiagnostic, ...]
    evidence_ids: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    historical_support: HistoricalSupportState = HistoricalSupportState.UNKNOWN
    regime_interpretation: RegimeInterpretationState = RegimeInterpretationState.NOT_ASSESSED

    def validate(self) -> None:
        if not self.model_id:
            raise ValueError("model_id is required")
        if not self.diagnostics:
            raise ValueError("diagnostics are required")
        for diagnostic in self.diagnostics:
            diagnostic.validate()
        if self.status == ModelFitStatus.FEASIBLE and not self.evidence_ids:
            raise ValueError("FEASIBLE model fit requires evidence_ids")
        if self.status == ModelFitStatus.FEASIBLE and self.historical_support != HistoricalSupportState.IN_RANGE:
            raise ValueError("FEASIBLE model fit requires IN_RANGE historical support")
        if self.status == ModelFitStatus.OUTSIDE_HISTORICAL_SUPPORT and self.historical_support not in {
            HistoricalSupportState.BELOW_HISTORICAL_RANGE,
            HistoricalSupportState.ABOVE_HISTORICAL_RANGE,
        }:
            raise ValueError("OUTSIDE_HISTORICAL_SUPPORT requires BELOW/ABOVE historical support state")
        if self.status == ModelFitStatus.OUTSIDE_HISTORICAL_SUPPORT and self.regime_interpretation != RegimeInterpretationState.POSSIBLE_REGIME_SHIFT:
            raise ValueError("OUTSIDE_HISTORICAL_SUPPORT requires POSSIBLE_REGIME_SHIFT interpretation")


@dataclass(frozen=True)
class FeasibleSolution:
    economic_variable: str
    unit: str
    basis: str
    model_id: str
    value: Decimal | None = None
    range_low: Decimal | None = None
    range_high: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.economic_variable or not self.unit or not self.basis or not self.model_id:
            raise ValueError("economic_variable, unit, basis and model_id are required")
        if self.value is None and (self.range_low is None or self.range_high is None):
            raise ValueError("solution must contain a point value or complete range")
        if self.value is not None and self.range_low is not None:
            raise ValueError("point value and range cannot both be supplied")
        if self.range_low is not None and self.range_low > self.range_high:
            raise ValueError("range_low must be <= range_high")
        if not self.evidence_ids:
            raise ValueError("feasible solution requires evidence_ids")


@dataclass(frozen=True)
class FeasibleSolutionSet:
    model_id: str
    status: FeasibleSolutionStatus
    solutions: tuple[FeasibleSolution, ...]
    constraint_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    basis: str

    def validate(self) -> None:
        if not self.model_id or not self.basis:
            raise ValueError("model_id and basis are required")
        if self.status == FeasibleSolutionStatus.NONEMPTY and not self.solutions:
            raise ValueError("NONEMPTY solution set requires at least one solution")
        if self.status == FeasibleSolutionStatus.EMPTY and self.solutions:
            raise ValueError("EMPTY solution set cannot contain solutions")
        for solution in self.solutions:
            solution.validate()
            if solution.model_id != self.model_id:
                raise ValueError("solution model_id must match solution-set model_id")
        if self.status == FeasibleSolutionStatus.NONEMPTY and not self.evidence_ids:
            raise ValueError("NONEMPTY solution set requires evidence_ids")


@dataclass(frozen=True)
class IdentifiabilityResult:
    state: IdentifiabilityState
    feasible_model_ids: tuple[str, ...]
    selected_model_id: str | None
    competing_model_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rationale: str

    def validate(self) -> None:
        if not self.rationale:
            raise ValueError("identifiability rationale is required")
        if self.state in {
            IdentifiabilityState.AMBIGUOUS,
            IdentifiabilityState.UNIDENTIFIABLE,
            IdentifiabilityState.INSUFFICIENT_EVIDENCE,
        } and self.selected_model_id is not None:
            raise ValueError(
                f"{self.state.value} cannot force a selected market model"
            )
        if self.state == IdentifiabilityState.IDENTIFIABLE:
            if self.selected_model_id is None:
                raise ValueError("IDENTIFIABLE requires selected_model_id")
            if self.selected_model_id not in self.feasible_model_ids:
                raise ValueError("selected_model_id must be feasible")
        if self.state == IdentifiabilityState.AMBIGUOUS and len(self.feasible_model_ids) < 2:
            raise ValueError("AMBIGUOUS requires at least two feasible model explanations")
        if self.state == IdentifiabilityState.IDENTIFIABLE and self.competing_model_ids:
            raise ValueError("IDENTIFIABLE cannot retain competing model IDs")


@dataclass(frozen=True)
class StabilityObservation:
    perturbation_id: str
    perturbation: str
    resulting_state: StabilityState
    selected_model_id: str | None

    def validate(self) -> None:
        if not self.perturbation_id or not self.perturbation:
            raise ValueError("perturbation_id and perturbation are required")


@dataclass(frozen=True)
class StabilityResult:
    state: StabilityState
    assessment_method: str
    observations: tuple[StabilityObservation, ...]
    evidence_ids: tuple[str, ...]
    rationale: str

    def validate(self) -> None:
        if not self.assessment_method or not self.rationale:
            raise ValueError("assessment_method and rationale are required")
        if self.state == StabilityState.STABLE and not self.observations:
            raise ValueError("STABLE requires at least one perturbation/regime observation")
        for observation in self.observations:
            observation.validate()


def semantic_variables_for_model(
    family: MarketModelFamily,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return MODEL_SEMANTICS[family]
