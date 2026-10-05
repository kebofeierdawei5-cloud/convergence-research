from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json
import os
import re
from typing import Any, Mapping, Protocol

from .market_observation_admission import (
    AdmissionStatus,
    MarketObservationAdmission,
    TemporalProvenance,
    VerifiedMarketEvidence,
)

CANONICAL_CURRENT_PRICE_ADMISSION_SCHEMA = "IIOS-CURRENT-PRICE-OBSERVATION-ADMISSION-0.1"
ADMITTED_STATUS = "ADMITTED"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REFERENCE_FIELDS = {"price_observation_id", "admission_record_hash"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _dec(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _parse_datetime(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON non-finite constant is not allowed: {value}")


@dataclass(frozen=True)
class CanonicalCurrentPriceObservationReference:
    price_observation_id: str
    admission_record_hash: str

    def validate(self) -> None:
        if not self.price_observation_id:
            raise ValueError("price_observation_id is required")
        if not _SHA256_RE.fullmatch(self.admission_record_hash):
            raise ValueError(
                "price observation admission_record_hash must be 64 lowercase hex characters"
            )

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "price_observation_id": self.price_observation_id,
            "admission_record_hash": self.admission_record_hash,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CanonicalCurrentPriceObservationReference":
        if not isinstance(value, Mapping):
            raise ValueError("price observation admission reference must be an object")
        if set(value) != _ALLOWED_REFERENCE_FIELDS:
            extras = sorted(set(value) - _ALLOWED_REFERENCE_FIELDS)
            missing = sorted(_ALLOWED_REFERENCE_FIELDS - set(value))
            parts = []
            if extras:
                parts.append(f"unsupported fields: {extras}")
            if missing:
                parts.append(f"missing fields: {missing}")
            raise ValueError("invalid price observation admission reference; " + "; ".join(parts))
        ref = cls(
            price_observation_id=str(value["price_observation_id"]),
            admission_record_hash=str(value["admission_record_hash"]),
        )
        ref.validate()
        return ref


class CanonicalCurrentPriceResolver(Protocol):
    def resolve_current_price(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ...


def _admission_core(
    *,
    case_id: str,
    market: str,
    symbol: str,
    cutoff_date: date,
    admission: MarketObservationAdmission,
    price_evidence: VerifiedMarketEvidence,
    observed_at: datetime,
    currency: str,
    adjustment_semantics: str,
) -> dict[str, Any]:
    if admission.status is not AdmissionStatus.ADMITTED or admission.observation is None:
        raise ValueError("canonical current price requires an ADMITTED market observation")
    observation = admission.observation
    if price_evidence.variable != "market_price":
        raise ValueError("price_evidence.variable must be market_price")
    if price_evidence.status is not AdmissionStatus.ADMITTED:
        raise ValueError("price_evidence must be ADMITTED")
    if price_evidence.temporal_provenance in {
        TemporalProvenance.RETROSPECTIVE_RECOMPUTED,
        TemporalProvenance.UNKNOWN,
    }:
        raise ValueError("price_evidence.temporal_provenance is not admissible for PIT")
    if price_evidence.exact_bytes is not True:
        raise ValueError("price_evidence.exact_bytes must be true")
    price_evidence.validate(cutoff_date)
    observation.validate(cutoff_date)
    if price_evidence.evidence_id not in admission.evidence_ids:
        raise ValueError("price_evidence.evidence_id is not part of admitted observation")
    if _dec(price_evidence.value, "price_evidence.value") != observation.price:
        raise ValueError("admitted observation price does not equal price_evidence.value")
    if price_evidence.observation_date != observation.observation_date:
        raise ValueError("price evidence and admitted observation dates do not match")
    if observed_at.date() != observation.observation_date:
        raise ValueError("observed_at date does not equal admitted observation date")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    if observed_at.date() > cutoff_date:
        raise ValueError("observed_at is after cutoff")
    if not currency or not adjustment_semantics:
        raise ValueError("currency and adjustment_semantics are required")
    if price_evidence.unit != f"{currency}/share":
        raise ValueError("price evidence unit must equal <currency>/share")
    if not case_id or not market or not symbol:
        raise ValueError("case_id, market and symbol are required")

    return {
        "admission_schema": CANONICAL_CURRENT_PRICE_ADMISSION_SCHEMA,
        "status": ADMITTED_STATUS,
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "cutoff_date": cutoff_date.isoformat(),
        "price_observation_id": price_evidence.evidence_id,
        "market_observation_id": observation.observation_id,
        "price": str(observation.price),
        "currency": currency,
        "observed_at": observed_at.isoformat(),
        "known_at": observation.known_at.isoformat(),
        "source": price_evidence.source,
        "source_location": price_evidence.source_location,
        "adjustment_semantics": adjustment_semantics,
        "price_evidence_content_sha256": price_evidence.content_sha256,
        "price_evidence_exact_bytes": True,
        "price_evidence_temporal_provenance": price_evidence.temporal_provenance.value,
        "market_observation_evidence_ids": list(admission.evidence_ids),
    }


def _with_hash(core: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(core)
    value["admission_record_hash"] = hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()
    return value


def _validate_record(record: Mapping[str, Any]) -> None:
    required = {
        "admission_schema", "status", "case_id", "market", "symbol", "cutoff_date",
        "price_observation_id", "market_observation_id", "price", "currency",
        "observed_at", "known_at", "source", "source_location", "adjustment_semantics",
        "price_evidence_content_sha256", "price_evidence_exact_bytes",
        "price_evidence_temporal_provenance", "market_observation_evidence_ids",
        "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("canonical current price admission record fields are invalid")
    if record["admission_schema"] != CANONICAL_CURRENT_PRICE_ADMISSION_SCHEMA:
        raise ValueError("canonical current price admission schema/version mismatch")
    if record["status"] != ADMITTED_STATUS:
        raise ValueError("canonical current price is not ADMITTED")
    if not str(record["case_id"]).strip() or not str(record["market"]).strip() or not str(record["symbol"]).strip():
        raise ValueError("canonical current price case/instrument identity is required")
    cutoff = _parse_date(record["cutoff_date"], "cutoff_date")
    _parse_datetime(record["observed_at"], "observed_at")
    known_at = _parse_datetime(record["known_at"], "known_at")
    if known_at.date() > cutoff:
        raise ValueError("canonical current price known_at is after cutoff")
    if _dec(record["price"], "price") <= 0:
        raise ValueError("canonical current price must be > 0")
    if not str(record["price_observation_id"]).strip():
        raise ValueError("canonical current price price_observation_id is required")
    if not str(record["market_observation_id"]).strip():
        raise ValueError("canonical current price market_observation_id is required")
    if not str(record["currency"]).strip() or not str(record["source"]).strip() or not str(record["source_location"]).strip():
        raise ValueError("canonical current price source/currency metadata is required")
    if not str(record["adjustment_semantics"]).strip():
        raise ValueError("canonical current price adjustment_semantics is required")
    if record["price_evidence_exact_bytes"] is not True:
        raise ValueError("canonical current price price evidence must be exact bytes")
    if record["price_evidence_temporal_provenance"] not in {
        TemporalProvenance.SOURCE_VINTAGE.value,
        TemporalProvenance.CONTEMPORANEOUS_PUBLICATION.value,
    }:
        raise ValueError("canonical current price temporal provenance is not PIT-admissible")
    if not _SHA256_RE.fullmatch(str(record["price_evidence_content_sha256"])):
        raise ValueError("canonical current price evidence SHA-256 is invalid")
    evidence_ids = record["market_observation_evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("canonical current price evidence IDs are required")
    expected = _with_hash(
        {k: record[k] for k in required if k != "admission_record_hash"}
    )
    if expected["admission_record_hash"] != record["admission_record_hash"]:
        raise ValueError("canonical current price admission record hash mismatch")


def _validate_binding(
    case_observation: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    ref = CanonicalCurrentPriceObservationReference.from_mapping({
        "price_observation_id": case_observation.get("price_observation_id", ""),
        "admission_record_hash": case_observation.get("price_observation_admission_hash", ""),
    })
    if ref.price_observation_id != record["price_observation_id"]:
        raise ValueError("current price price_observation_id does not match canonical admission")
    if ref.admission_record_hash != record["admission_record_hash"]:
        raise ValueError("current price admission hash does not match canonical admission")
    if _dec(case_observation.get("price"), "current_price_observation.price") != _dec(record["price"], "canonical.price"):
        raise ValueError("current_price_observation.price does not match canonical admitted price")
    if str(case_observation.get("currency", "")) != record["currency"]:
        raise ValueError("current price currency does not match canonical admission")
    if str(case_observation.get("source", "")) != record["source"]:
        raise ValueError("current price source does not match canonical admission")
    if str(case_observation.get("adjustment_semantics", "")) != record["adjustment_semantics"]:
        raise ValueError("current price adjustment_semantics does not match canonical admission")
    if _parse_datetime(case_observation.get("observed_at"), "current_price_observation.observed_at") != _parse_datetime(record["observed_at"], "canonical.observed_at"):
        raise ValueError("current price observed_at does not match canonical admission")
    if _parse_datetime(case_observation.get("known_at"), "current_price_observation.known_at") != _parse_datetime(record["known_at"], "canonical.known_at"):
        raise ValueError("current price known_at does not match canonical admission")


class FileSystemCanonicalCurrentPriceRegistry:
    """Trusted immutable store for admitted current-price observations."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.records_dir = self.root / "current_price_admissions"
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, price_observation_id: str) -> Path:
        safe = hashlib.sha256(price_observation_id.encode("utf-8")).hexdigest()
        return self.records_dir / f"{safe}.price.json"

    def admit_current_price(
        self,
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
        admission: MarketObservationAdmission,
        price_evidence: VerifiedMarketEvidence,
        observed_at: datetime,
        currency: str,
        adjustment_semantics: str,
    ) -> CanonicalCurrentPriceObservationReference:
        core = _admission_core(
            case_id=case_id, market=market, symbol=symbol, cutoff_date=cutoff_date,
            admission=admission, price_evidence=price_evidence, observed_at=observed_at,
            currency=currency, adjustment_semantics=adjustment_semantics,
        )
        record = _with_hash(core)
        path = self._path(record["price_observation_id"])
        data = _pretty_json_bytes(record)
        if path.exists():
            existing = path.read_bytes()
            if existing != data:
                raise ValueError("canonical current price admission already exists with different bytes")
            parsed = json.loads(existing.decode("utf-8"), parse_constant=_reject_json_constant)
            _validate_record(parsed)
            return CanonicalCurrentPriceObservationReference(
                record["price_observation_id"], record["admission_record_hash"]
            )
        try:
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise ValueError("canonical current price admission raced with another writer") from exc
        return CanonicalCurrentPriceObservationReference(
            record["price_observation_id"], record["admission_record_hash"]
        )

    def resolve_current_price(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = CanonicalCurrentPriceObservationReference.from_mapping(reference)
        path = self._path(ref.price_observation_id)
        if not path.exists():
            raise ValueError("canonical current price admission is unknown")
        raw = path.read_bytes()
        if _sha256_bytes(raw) != _sha256_bytes(_pretty_json_bytes(json.loads(raw.decode("utf-8")))):
            raise ValueError("canonical current price admission bytes are not canonical")
        try:
            record = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("canonical current price admission is unreadable") from exc
        if not isinstance(record, dict):
            raise ValueError("canonical current price admission record must be an object")
        _validate_record(record)
        if record["price_observation_id"] != ref.price_observation_id:
            raise ValueError("canonical current price observation ID mismatch")
        if record["admission_record_hash"] != ref.admission_record_hash:
            raise ValueError("canonical current price admission hash mismatch")
        if record["case_id"] != case_id or record["market"] != market or record["symbol"] != symbol:
            raise ValueError("canonical current price instrument identity mismatch")
        if _parse_date(record["cutoff_date"], "cutoff_date") != cutoff_date:
            raise ValueError("canonical current price cutoff_date mismatch")
        return record


class InMemoryCanonicalCurrentPriceRegistry:
    """Deterministic resolver double using the same canonical record contract."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def admit_current_price(
        self,
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
        admission: MarketObservationAdmission,
        price_evidence: VerifiedMarketEvidence,
        observed_at: datetime,
        currency: str,
        adjustment_semantics: str,
    ) -> CanonicalCurrentPriceObservationReference:
        record = _with_hash(_admission_core(
            case_id=case_id, market=market, symbol=symbol, cutoff_date=cutoff_date,
            admission=admission, price_evidence=price_evidence, observed_at=observed_at,
            currency=currency, adjustment_semantics=adjustment_semantics,
        ))
        existing = self._records.get(record["price_observation_id"])
        if existing is not None:
            if _canonical_json(existing) != _canonical_json(record):
                raise ValueError("canonical current price admission already exists with different bytes")
        else:
            self._records[record["price_observation_id"]] = record
        return CanonicalCurrentPriceObservationReference(
            record["price_observation_id"], record["admission_record_hash"]
        )

    def resolve_current_price(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = CanonicalCurrentPriceObservationReference.from_mapping(reference)
        record = self._records.get(ref.price_observation_id)
        if record is None:
            raise ValueError("canonical current price admission is unknown")
        _validate_record(record)
        if record["price_observation_id"] != ref.price_observation_id:
            raise ValueError("canonical current price observation ID mismatch")
        if record["admission_record_hash"] != ref.admission_record_hash:
            raise ValueError("canonical current price admission hash mismatch")
        if record["case_id"] != case_id or record["market"] != market or record["symbol"] != symbol:
            raise ValueError("canonical current price instrument identity mismatch")
        if _parse_date(record["cutoff_date"], "cutoff_date") != cutoff_date:
            raise ValueError("canonical current price cutoff_date mismatch")
        return dict(record)


def admit_from_verified_market_observation(
    *,
    case_id: str,
    market: str,
    symbol: str,
    cutoff_date: date,
    admission: MarketObservationAdmission,
    price_evidence: VerifiedMarketEvidence,
    observed_at: datetime,
    currency: str,
    adjustment_semantics: str,
    registry: InMemoryCanonicalCurrentPriceRegistry | FileSystemCanonicalCurrentPriceRegistry,
) -> CanonicalCurrentPriceObservationReference:
    return registry.admit_current_price(
        case_id=case_id, market=market, symbol=symbol, cutoff_date=cutoff_date,
        admission=admission, price_evidence=price_evidence, observed_at=observed_at,
        currency=currency, adjustment_semantics=adjustment_semantics,
    )


__all__ = [
    "CANONICAL_CURRENT_PRICE_ADMISSION_SCHEMA",
    "CanonicalCurrentPriceObservationReference",
    "CanonicalCurrentPriceResolver",
    "FileSystemCanonicalCurrentPriceRegistry",
    "InMemoryCanonicalCurrentPriceRegistry",
    "admit_from_verified_market_observation",
    "_validate_binding",
]
