from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import re

from .market_model_identification import MarketValuationObservation


class AdmissionStatus(str, Enum):
    ADMITTED = "ADMITTED"
    BLOCKED = "BLOCKED"


class TemporalProvenance(str, Enum):
    SOURCE_VINTAGE = "SOURCE_VINTAGE"
    CONTEMPORANEOUS_PUBLICATION = "CONTEMPORANEOUS_PUBLICATION"
    RETROSPECTIVE_RECOMPUTED = "RETROSPECTIVE_RECOMPUTED"
    UNKNOWN = "UNKNOWN"


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _dec(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


@dataclass(frozen=True)
class VerifiedMarketEvidence:
    evidence_id: str
    variable: str
    unit: str
    basis: str
    observation_date: date
    known_at: datetime
    source: str
    source_location: str
    content_sha256: str
    exact_bytes: bool
    status: AdmissionStatus
    temporal_provenance: TemporalProvenance
    value: Decimal

    def validate(self, cutoff_date: date) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if not self.variable:
            raise ValueError(f"{self.evidence_id}.variable is required")
        if not self.unit:
            raise ValueError(f"{self.evidence_id}.unit is required")
        if not self.basis:
            raise ValueError(f"{self.evidence_id}.basis is required")
        if not self.source:
            raise ValueError(f"{self.evidence_id}.source is required")
        if not self.source_location:
            raise ValueError(f"{self.evidence_id}.source_location is required")
        if not _SHA256_RE.fullmatch(self.content_sha256):
            raise ValueError(
                f"{self.evidence_id}.content_sha256 must be lowercase SHA-256"
            )
        if self.exact_bytes is not True:
            raise ValueError(f"{self.evidence_id}.exact_bytes must be true")
        if self.status is not AdmissionStatus.ADMITTED:
            raise ValueError(f"{self.evidence_id} must be ADMITTED")
        if self.temporal_provenance in {
            TemporalProvenance.RETROSPECTIVE_RECOMPUTED,
            TemporalProvenance.UNKNOWN,
        }:
            raise ValueError(
                f"{self.evidence_id}.temporal_provenance is not admissible for PIT"
            )
        if self.observation_date > cutoff_date:
            raise ValueError(f"{self.evidence_id}.observation_date is after cutoff")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ValueError(f"{self.evidence_id}.known_at must be timezone-aware")
        if self.known_at.date() > cutoff_date:
            raise ValueError(f"{self.evidence_id}.known_at is after cutoff")
        if not self.value.is_finite():
            raise ValueError(f"{self.evidence_id}.value must be finite")


@dataclass(frozen=True)
class MarketObservationAdmission:
    status: AdmissionStatus
    observation: MarketValuationObservation | None
    evidence_ids: tuple[str, ...]
    blockers: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.status is AdmissionStatus.ADMITTED and self.observation is None:
            raise ValueError("ADMITTED admission requires an observation")
        if self.status is AdmissionStatus.BLOCKED and self.observation is not None:
            raise ValueError("BLOCKED admission cannot expose an observation")
        if self.status is AdmissionStatus.BLOCKED and not self.blockers:
            raise ValueError("BLOCKED admission requires blockers")


def admit_market_valuation_observation(
    *,
    cutoff_date: date,
    observation_id: str,
    price_evidence: VerifiedMarketEvidence,
    shares_evidence: VerifiedMarketEvidence,
    economic_evidence: VerifiedMarketEvidence,
    net_debt_evidence: VerifiedMarketEvidence,
) -> MarketObservationAdmission:
    evidence = (
        price_evidence,
        shares_evidence,
        economic_evidence,
        net_debt_evidence,
    )
    blockers: list[str] = []

    for item in evidence:
        try:
            item.validate(cutoff_date)
        except ValueError as exc:
            blockers.append(str(exc))

    if len({item.evidence_id for item in evidence}) != len(evidence):
        blockers.append("evidence_ids must be unique")

    if price_evidence.variable != "market_price":
        blockers.append("price_evidence.variable must be market_price")
    if shares_evidence.variable != "shares_outstanding":
        blockers.append("shares_evidence.variable must be shares_outstanding")
    if net_debt_evidence.variable != "net_debt":
        blockers.append("net_debt_evidence.variable must be net_debt")

    if price_evidence.observation_date != shares_evidence.observation_date:
        blockers.append("price/share-count observation dates must match")
    if price_evidence.observation_date != economic_evidence.observation_date:
        blockers.append("price/economic observation dates must match")
    if price_evidence.observation_date != net_debt_evidence.observation_date:
        blockers.append("price/net-debt observation dates must match")

    if price_evidence.unit != "CNY/share":
        blockers.append("market_price unit must be CNY/share")
    if shares_evidence.unit not in {"shares", "share_count"}:
        blockers.append("shares_outstanding unit must be shares/share_count")
    if price_evidence.value <= 0:
        blockers.append("market price must be > 0")
    if shares_evidence.value <= 0:
        blockers.append("shares outstanding must be > 0")
    if economic_evidence.value <= 0:
        blockers.append(
            "economic variable value must be > 0"
        )

    if blockers:
        result = MarketObservationAdmission(
            status=AdmissionStatus.BLOCKED,
            observation=None,
            evidence_ids=tuple(item.evidence_id for item in evidence),
            blockers=tuple(blockers),
        )
        result.validate()
        return result

    observation = MarketValuationObservation(
        observation_id=observation_id,
        observation_date=price_evidence.observation_date,
        known_at=max(item.known_at for item in evidence),
        price=_dec(price_evidence.value, f"{price_evidence.evidence_id}.value"),
        shares_outstanding=_dec(
            shares_evidence.value, f"{shares_evidence.evidence_id}.value"
        ),
        economic_variable=economic_evidence.variable,
        economic_value=_dec(
            economic_evidence.value, f"{economic_evidence.evidence_id}.value"
        ),
        unit=economic_evidence.unit,
        basis=economic_evidence.basis,
        evidence_ids=tuple(item.evidence_id for item in evidence),
        source=economic_evidence.source,
        net_debt=_dec(
            net_debt_evidence.value, f"{net_debt_evidence.evidence_id}.value"
        ),
    )
    observation.validate(cutoff_date)
    result = MarketObservationAdmission(
        status=AdmissionStatus.ADMITTED,
        observation=observation,
        evidence_ids=tuple(item.evidence_id for item in evidence),
    )
    result.validate()
    return result


__all__ = [
    "AdmissionStatus",
    "MarketObservationAdmission",
    "TemporalProvenance",
    "VerifiedMarketEvidence",
    "admit_market_valuation_observation",
]
