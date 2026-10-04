from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from .market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState


class MIERepresentation(str, Enum):
    FULL_FEASIBLE_SET = "FULL_FEASIBLE_SET"
    IMPLIED_POINT = "IMPLIED_POINT"
    IMPLIED_RANGE = "IMPLIED_RANGE"
    CONDITIONAL_IMPLIED_VARIABLE = "CONDITIONAL_IMPLIED_VARIABLE"


class MIEQualification(str, Enum):
    DECISION_GRADE = "DECISION_GRADE"
    CONDITIONAL_ONLY = "CONDITIONAL_ONLY"
    BLOCKED = "BLOCKED"


class CandidateCoverageState(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNASSESSED = "UNASSESSED"


@dataclass(frozen=True)
class MIEEconomicRequirement:
    economic_variable: str
    unit: str
    basis: str
    period: str
    horizon: str
    accounting_basis: str
    role: str
    value: Decimal | None = None
    range_low: Decimal | None = None
    range_high: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.economic_variable or self.economic_variable == "market_implied_net_profit":
            raise ValueError("economic_variable must be explicit and cannot be generic implied net profit")
        for name, value in (
            ("unit", self.unit),
            ("basis", self.basis),
            ("period", self.period),
            ("horizon", self.horizon),
            ("accounting_basis", self.accounting_basis),
            ("role", self.role),
        ):
            if not value:
                raise ValueError(f"{name} is required")
        if self.value is None and (self.range_low is None or self.range_high is None):
            raise ValueError("requirement must contain a point value or a complete range")
        if self.value is not None and (self.range_low is not None or self.range_high is not None):
            raise ValueError("point value and range cannot both be supplied")
        if self.range_low is not None and self.range_high is not None and self.range_low > self.range_high:
            raise ValueError("range_low must be <= range_high")
        if not self.evidence_ids:
            raise ValueError("requirement evidence_ids are required")


@dataclass(frozen=True)
class MIEAssumption:
    variable: str
    value: Decimal
    unit: str
    basis: str
    period: str
    horizon: str
    accounting_basis: str
    evidence_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.variable or self.variable == "market_implied_net_profit":
            raise ValueError("assumption variable must be explicit and cannot be generic implied net profit")
        if not self.unit or not self.basis or not self.period or not self.horizon or not self.accounting_basis:
            raise ValueError("assumption semantic metadata is required")
        if not self.evidence_ids:
            raise ValueError("assumption evidence_ids are required")


@dataclass(frozen=True)
class MIEObservationBasis:
    price_observation_id: str
    observation_date: date
    cutoff_date: date
    currency: str
    adjustment_semantics: str

    def validate(self) -> None:
        if not self.price_observation_id:
            raise ValueError("price_observation_id is required")
        if self.observation_date > self.cutoff_date:
            raise ValueError("observation_date cannot be after cutoff_date")
        if not self.currency or not self.adjustment_semantics:
            raise ValueError("currency and adjustment_semantics are required")


@dataclass(frozen=True)
class MarketImpliedExpectation:
    expectation_id: str
    model_id: str
    market_model: MarketModelFamily
    identifiability: IdentifiabilityState
    stability: StabilityState
    candidate_coverage: CandidateCoverageState
    representation: MIERepresentation
    economic_requirements: tuple[MIEEconomicRequirement, ...]
    observation_basis: MIEObservationBasis
    assumption_set: tuple[MIEAssumption, ...]
    evidence_sufficiency: bool
    evidence_ids: tuple[str, ...]
    qualification: MIEQualification
    qualification_rationale: str

    def validate(self) -> None:
        if not self.expectation_id or not self.model_id:
            raise ValueError("expectation_id and model_id are required")
        if not self.economic_requirements:
            raise ValueError("economic_requirements are required")
        self.observation_basis.validate()
        for item in self.economic_requirements:
            item.validate()
        for item in self.assumption_set:
            item.validate()
        if not self.evidence_sufficiency and self.qualification == MIEQualification.DECISION_GRADE:
            raise ValueError("evidence insufficiency cannot be decision-grade")
        if not self.evidence_ids:
            raise ValueError("MIE evidence_ids are required")
        if not self.qualification_rationale:
            raise ValueError("qualification_rationale is required")
        expected = self.expected_qualification()
        if self.qualification != expected:
            raise ValueError(f"qualification mismatch: expected {expected.value}, got {self.qualification.value}")

    def expected_qualification(self) -> MIEQualification:
        if not self.evidence_sufficiency:
            return MIEQualification.BLOCKED
        if self.candidate_coverage != CandidateCoverageState.SUFFICIENT:
            return MIEQualification.BLOCKED
        if self.identifiability in {IdentifiabilityState.UNIDENTIFIABLE, IdentifiabilityState.INSUFFICIENT_EVIDENCE}:
            return MIEQualification.BLOCKED
        if self.stability in {StabilityState.UNSTABLE, StabilityState.INSUFFICIENT_EVIDENCE}:
            return MIEQualification.BLOCKED
        if self.identifiability == IdentifiabilityState.AMBIGUOUS:
            return MIEQualification.CONDITIONAL_ONLY
        if self.representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE:
            return MIEQualification.CONDITIONAL_ONLY
        return MIEQualification.DECISION_GRADE


def qualify_market_implied_expectation(**kwargs: object) -> MarketImpliedExpectation:
    draft = MarketImpliedExpectation(
        **kwargs,
        qualification=MIEQualification.BLOCKED,
    )
    result = MarketImpliedExpectation(
        expectation_id=draft.expectation_id,
        model_id=draft.model_id,
        market_model=draft.market_model,
        identifiability=draft.identifiability,
        stability=draft.stability,
        candidate_coverage=draft.candidate_coverage,
        representation=draft.representation,
        economic_requirements=draft.economic_requirements,
        observation_basis=draft.observation_basis,
        assumption_set=draft.assumption_set,
        evidence_sufficiency=draft.evidence_sufficiency,
        evidence_ids=draft.evidence_ids,
        qualification=draft.expected_qualification(),
        qualification_rationale=draft.qualification_rationale,
    )
    result.validate()
    return result