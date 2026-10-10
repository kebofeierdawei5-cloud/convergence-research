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

CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA = (
    "IIOS-INDEPENDENT-FORECAST-ADMISSION-0.1"
)
ADMITTED_STATUS = "ADMITTED"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REFERENCE_FIELDS = {"forecast_id", "admission_record_hash"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _parse_decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
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


def _parse_horizon_years(value: Any, field: str) -> Decimal:
    result = _parse_decimal(value, field)
    if result <= 0:
        raise ValueError(f"{field} must be > 0")
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON non-finite constant is not allowed: {value}")


@dataclass(frozen=True)
class CanonicalIndependentForecastReference:
    forecast_id: str
    admission_record_hash: str

    def validate(self) -> None:
        if not self.forecast_id.strip():
            raise ValueError("forecast_id is required")
        if not _SHA256_RE.fullmatch(self.admission_record_hash):
            raise ValueError(
                "forecast admission_record_hash must be 64 lowercase hex characters"
            )

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "forecast_id": self.forecast_id,
            "admission_record_hash": self.admission_record_hash,
        }

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, Any]
    ) -> "CanonicalIndependentForecastReference":
        if not isinstance(value, Mapping):
            raise ValueError("independent forecast reference must be an object")
        if set(value) != _ALLOWED_REFERENCE_FIELDS:
            extras = sorted(set(value) - _ALLOWED_REFERENCE_FIELDS)
            missing = sorted(_ALLOWED_REFERENCE_FIELDS - set(value))
            parts = []
            if extras:
                parts.append(f"unsupported fields: {extras}")
            if missing:
                parts.append(f"missing fields: {missing}")
            raise ValueError(
                "invalid independent forecast reference; " + "; ".join(parts)
            )
        ref = cls(
            forecast_id=str(value["forecast_id"]),
            admission_record_hash=str(value["admission_record_hash"]),
        )
        ref.validate()
        return ref


class CanonicalIndependentForecastResolver(Protocol):
    def resolve_independent_forecast(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ...


def _validate_record(record: Mapping[str, Any]) -> None:
    required = {
        "admission_schema",
        "status",
        "case_id",
        "market",
        "symbol",
        "cutoff_date",
        "forecast_id",
        "forecast_version",
        "model_version",
        "variable_id",
        "value",
        "unit",
        "basis",
        "horizon_years",
        "forecast_origin",
        "known_at",
        "prepared_without_current_price",
        "evidence_ids",
        "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("canonical independent forecast admission record fields are invalid")
    if record["admission_schema"] != CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA:
        raise ValueError("canonical independent forecast admission schema/version mismatch")
    if record["status"] != ADMITTED_STATUS:
        raise ValueError("canonical independent forecast is not ADMITTED")
    for field in ("case_id", "market", "symbol", "forecast_id", "forecast_version",
                  "model_version", "variable_id", "unit", "basis"):
        if not str(record[field]).strip():
            raise ValueError(f"canonical independent forecast {field} is required")
    cutoff = _parse_date(record["cutoff_date"], "cutoff_date")
    origin = _parse_datetime(record["forecast_origin"], "forecast_origin")
    known_at = _parse_datetime(record["known_at"], "known_at")
    if origin.date() > cutoff:
        raise ValueError("canonical independent forecast origin is after cutoff")
    if known_at.date() > cutoff:
        raise ValueError("canonical independent forecast known_at is after cutoff")
    value = _parse_decimal(record["value"], "value")
    _parse_horizon_years(record["horizon_years"], "horizon_years")
    if record["prepared_without_current_price"] is not True:
        raise ValueError(
            "canonical independent forecast must be prepared without current price"
        )
    evidence_ids = record["evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("canonical independent forecast evidence_ids are required")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("canonical independent forecast evidence_ids must be unique")
    if any(not str(item).strip() for item in evidence_ids):
        raise ValueError("canonical independent forecast evidence_ids must be non-empty")
    expected_hash = hashlib.sha256(
        _canonical_json(
            {
                k: record[k]
                for k in required
                if k != "admission_record_hash"
            }
        ).encode("utf-8")
    ).hexdigest()
    if expected_hash != record["admission_record_hash"]:
        raise ValueError("canonical independent forecast admission record hash mismatch")


def _build_record(forecast: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "case_id", "market", "symbol", "cutoff_date", "forecast_id",
        "forecast_version", "model_version", "variable_id", "value", "unit",
        "basis", "horizon_years", "forecast_origin", "known_at",
        "prepared_without_current_price", "evidence_ids",
    }
    missing = sorted(required - set(forecast))
    if missing:
        raise ValueError(f"independent forecast missing required fields: {missing}")
    record = {
        "admission_schema": CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA,
        "status": ADMITTED_STATUS,
        "case_id": str(forecast["case_id"]),
        "market": str(forecast["market"]),
        "symbol": str(forecast["symbol"]),
        "cutoff_date": _parse_date(
            forecast["cutoff_date"], "cutoff_date"
        ).isoformat(),
        "forecast_id": str(forecast["forecast_id"]),
        "forecast_version": str(forecast["forecast_version"]),
        "model_version": str(forecast["model_version"]),
        "variable_id": str(forecast["variable_id"]),
        "value": str(_parse_decimal(forecast["value"], "value")),
        "unit": str(forecast["unit"]),
        "basis": str(forecast["basis"]),
        "horizon_years": str(
            _parse_horizon_years(forecast["horizon_years"], "horizon_years")
        ),
        "forecast_origin": _parse_datetime(
            forecast["forecast_origin"], "forecast_origin"
        ).isoformat(),
        "known_at": _parse_datetime(
            forecast["known_at"], "known_at"
        ).isoformat(),
        "prepared_without_current_price": forecast["prepared_without_current_price"],
        "evidence_ids": [str(item) for item in forecast["evidence_ids"]],
    }
    record["admission_record_hash"] = hashlib.sha256(
        _canonical_json(record).encode("utf-8")
    ).hexdigest()
    _validate_record(record)
    return record


class FileSystemCanonicalIndependentForecastRegistry:
    """Trusted immutable store for canonical independent forecast records."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.records_dir = self.root / "independent_forecast_admissions"
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, forecast_id: str) -> Path:
        safe = hashlib.sha256(forecast_id.encode("utf-8")).hexdigest()
        return self.records_dir / f"{safe}.forecast.json"

    def admit_independent_forecast(
        self, forecast: Mapping[str, Any]
    ) -> CanonicalIndependentForecastReference:
        record = _build_record(forecast)
        path = self._path(record["forecast_id"])
        payload = _pretty_json_bytes(record)
        if path.exists():
            existing = path.read_bytes()
            if existing != payload:
                raise ValueError(
                    "canonical independent forecast admission already exists with different bytes"
                )
            try:
                parsed = json.loads(
                    existing.decode("utf-8"), parse_constant=_reject_json_constant
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(
                    "canonical independent forecast admission is unreadable"
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(
                    "canonical independent forecast admission must be an object"
                )
            _validate_record(parsed)
        else:
            try:
                with path.open("xb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise ValueError(
                    "canonical independent forecast admission raced with another writer"
                ) from exc
        return CanonicalIndependentForecastReference(
            record["forecast_id"], record["admission_record_hash"]
        )

    def resolve_independent_forecast(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = CanonicalIndependentForecastReference.from_mapping(reference)
        path = self._path(ref.forecast_id)
        if not path.exists():
            raise ValueError("canonical independent forecast admission is unknown")
        raw = path.read_bytes()
        try:
            record = json.loads(
                raw.decode("utf-8"), parse_constant=_reject_json_constant
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                "canonical independent forecast admission is unreadable"
            ) from exc
        if not isinstance(record, dict):
            raise ValueError("canonical independent forecast admission must be an object")
        _validate_record(record)
        if record["forecast_id"] != ref.forecast_id:
            raise ValueError("canonical independent forecast ID mismatch")
        if record["admission_record_hash"] != ref.admission_record_hash:
            raise ValueError("canonical independent forecast admission hash mismatch")
        if (
            record["case_id"] != case_id
            or record["market"] != market
            or record["symbol"] != symbol
        ):
            raise ValueError(
                "canonical independent forecast instrument identity mismatch"
            )
        if _parse_date(record["cutoff_date"], "cutoff_date") != cutoff_date:
            raise ValueError("canonical independent forecast cutoff_date mismatch")
        return record


class InMemoryCanonicalIndependentForecastRegistry:
    """Deterministic resolver double using the same canonical record contract."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def admit_independent_forecast(
        self, forecast: Mapping[str, Any]
    ) -> CanonicalIndependentForecastReference:
        record = _build_record(forecast)
        existing = self._records.get(record["forecast_id"])
        if existing is not None:
            if _canonical_json(existing) != _canonical_json(record):
                raise ValueError(
                    "canonical independent forecast admission already exists with different bytes"
                )
            _validate_record(existing)
        else:
            self._records[record["forecast_id"]] = record
        return CanonicalIndependentForecastReference(
            record["forecast_id"], record["admission_record_hash"]
        )

    def resolve_independent_forecast(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = CanonicalIndependentForecastReference.from_mapping(reference)
        record = self._records.get(ref.forecast_id)
        if record is None:
            raise ValueError("canonical independent forecast admission is unknown")
        _validate_record(record)
        if record["forecast_id"] != ref.forecast_id:
            raise ValueError("canonical independent forecast ID mismatch")
        if record["admission_record_hash"] != ref.admission_record_hash:
            raise ValueError("canonical independent forecast admission hash mismatch")
        if (
            record["case_id"] != case_id
            or record["market"] != market
            or record["symbol"] != symbol
        ):
            raise ValueError(
                "canonical independent forecast instrument identity mismatch"
            )
        if _parse_date(record["cutoff_date"], "cutoff_date") != cutoff_date:
            raise ValueError("canonical independent forecast cutoff_date mismatch")
        return dict(record)


def validate_canonical_independent_forecast_admission(record: Mapping[str, Any]) -> None:
    """Public, deterministic validator for a persisted admitted forecast record."""
    if not isinstance(record, Mapping):
        raise ValueError("canonical independent forecast admission must be an object")
    _validate_record(record)


def canonical_independent_expectation_from_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_record(record)
    return {
        "variable_id": record["variable_id"],
        "value": _parse_decimal(record["value"], "forecast.value"),
        "unit": record["unit"],
        "basis": record["basis"],
        "horizon_years": _parse_decimal(
            record["horizon_years"], "forecast.horizon_years"
        ),
        "evidence_ids": tuple(str(item) for item in record["evidence_ids"]),
    }


__all__ = [
    "ADMITTED_STATUS",
    "CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA",
    "CanonicalIndependentForecastReference",
    "CanonicalIndependentForecastResolver",
    "FileSystemCanonicalIndependentForecastRegistry",
    "InMemoryCanonicalIndependentForecastRegistry",
    "canonical_independent_expectation_from_record",
]
