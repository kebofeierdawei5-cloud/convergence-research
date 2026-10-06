from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Protocol

CANONICAL_INVESTMENT_ADMISSION_VERSION = "IIOS-CANONICAL-INVESTMENT-ADMISSION-0.1"
ADMITTED_STATUS = "ADMITTED"
ADMISSION_RECORD_STATUSES = {"ADMITTED", "BLOCKED"}
DOMAIN_STATUSES = {"PASS", "CONDITIONAL", "BLOCKED", "UNKNOWN"}

ADMISSION_DOMAINS = {
    "REALITY",
    "QUALITY",
    "VALUE_DRIVER",
    "VALUATION",
    "FORECAST",
    "THESIS",
    "RETURN",
    "RISK",
    "PORTFOLIO",
}

_REFERENCE_FIELDS = {
    "admission_id",
    "admission_record_hash",
    "contract_version",
    "domain",
    "case_id",
    "market",
    "symbol",
    "company",
    "cutoff_date",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _datetime(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


@dataclass(frozen=True)
class CanonicalInvestmentAdmissionReference:
    admission_id: str
    admission_record_hash: str
    contract_version: str
    domain: str
    case_id: str
    market: str
    symbol: str
    company: str
    cutoff_date: str

    def validate(self) -> None:
        _text(self.admission_id, "admission_id")
        if not _SHA256_RE.fullmatch(self.admission_record_hash):
            raise ValueError("admission_record_hash must be 64 lowercase hex characters")
        if self.contract_version != CANONICAL_INVESTMENT_ADMISSION_VERSION:
            raise ValueError("canonical admission reference version mismatch")
        if self.domain not in ADMISSION_DOMAINS:
            raise ValueError(f"unsupported admission domain: {self.domain}")
        _text(self.case_id, "case_id")
        _text(self.market, "market")
        _text(self.symbol, "symbol")
        _text(self.company, "company")
        _date(self.cutoff_date, "cutoff_date")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "admission_id": self.admission_id,
            "admission_record_hash": self.admission_record_hash,
            "contract_version": self.contract_version,
            "domain": self.domain,
            "case_id": self.case_id,
            "market": self.market,
            "symbol": self.symbol,
            "company": self.company,
            "cutoff_date": self.cutoff_date,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CanonicalInvestmentAdmissionReference":
        if not isinstance(value, Mapping):
            raise ValueError("canonical admission reference must be an object")
        if set(value) != _REFERENCE_FIELDS:
            extras = sorted(set(value) - _REFERENCE_FIELDS)
            missing = sorted(_REFERENCE_FIELDS - set(value))
            parts = []
            if extras:
                parts.append(f"unsupported fields: {extras}")
            if missing:
                parts.append(f"missing fields: {missing}")
            raise ValueError("invalid canonical admission reference; " + "; ".join(parts))
        ref = cls(
            admission_id=str(value["admission_id"]),
            admission_record_hash=str(value["admission_record_hash"]),
            contract_version=str(value["contract_version"]),
            domain=str(value["domain"]).upper(),
            case_id=str(value["case_id"]),
            market=str(value["market"]).upper(),
            symbol=str(value["symbol"]).upper(),
            company=str(value["company"]),
            cutoff_date=str(value["cutoff_date"]),
        )
        ref.validate()
        return ref


@dataclass(frozen=True)
class CanonicalInvestmentAdmissionRecord:
    admission_id: str
    contract_version: str
    domain: str
    case_id: str
    market: str
    symbol: str
    company: str
    cutoff_date: str
    status: str
    domain_status: str
    source_record_id: str
    source_record_hash: str
    output_hash: str
    producer_version: str
    evidence_ids: tuple[str, ...]
    admitted_at: str
    admission_record_hash: str

    def to_core_dict(self) -> dict[str, Any]:
        return {
            "admission_id": self.admission_id,
            "contract_version": self.contract_version,
            "domain": self.domain,
            "case_id": self.case_id,
            "market": self.market,
            "symbol": self.symbol,
            "company": self.company,
            "cutoff_date": self.cutoff_date,
            "status": self.status,
            "domain_status": self.domain_status,
            "source_record_id": self.source_record_id,
            "source_record_hash": self.source_record_hash,
            "output_hash": self.output_hash,
            "producer_version": self.producer_version,
            "evidence_ids": list(self.evidence_ids),
            "admitted_at": self.admitted_at,
        }

    def to_dict(self) -> dict[str, Any]:
        core = self.to_core_dict()
        return {**core, "admission_record_hash": self.admission_record_hash}

    def reference(self) -> CanonicalInvestmentAdmissionReference:
        return CanonicalInvestmentAdmissionReference(
            admission_id=self.admission_id,
            admission_record_hash=self.admission_record_hash,
            contract_version=self.contract_version,
            domain=self.domain,
            case_id=self.case_id,
            market=self.market,
            symbol=self.symbol,
            company=self.company,
            cutoff_date=self.cutoff_date,
        )


def build_canonical_investment_admission(
    *,
    admission_id: str,
    domain: str,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: str,
    domain_status: str,
    source_record_id: str,
    source_record_hash: str,
    output_hash: str,
    producer_version: str,
    evidence_ids: list[str] | tuple[str, ...],
    admitted_at: str | None = None,
) -> CanonicalInvestmentAdmissionRecord:
    if admitted_at is None:
        admitted_at = datetime.now(timezone.utc).isoformat()
    values = {
        "admission_id": _text(admission_id, "admission_id"),
        "contract_version": CANONICAL_INVESTMENT_ADMISSION_VERSION,
        "domain": str(domain).strip().upper(),
        "case_id": _text(case_id, "case_id"),
        "market": _text(market, "market").upper(),
        "symbol": _text(symbol, "symbol").upper(),
        "company": _text(company, "company"),
        "cutoff_date": _date(cutoff_date, "cutoff_date").isoformat(),
        "status": ADMITTED_STATUS,
        "domain_status": str(domain_status).strip().upper(),
        "source_record_id": _text(source_record_id, "source_record_id"),
        "source_record_hash": _text(source_record_hash, "source_record_hash"),
        "output_hash": _text(output_hash, "output_hash"),
        "producer_version": _text(producer_version, "producer_version"),
        "evidence_ids": sorted({str(x).strip() for x in evidence_ids if str(x).strip()}),
        "admitted_at": str(admitted_at),
    }
    if values["domain"] not in ADMISSION_DOMAINS:
        raise ValueError(f"unsupported admission domain: {values['domain']}")
    if values["domain_status"] not in DOMAIN_STATUSES:
        raise ValueError(f"unsupported domain status: {values['domain_status']}")
    if not _SHA256_RE.fullmatch(values["source_record_hash"]):
        raise ValueError("source_record_hash must be 64 lowercase hex characters")
    if not _SHA256_RE.fullmatch(values["output_hash"]):
        raise ValueError("output_hash must be 64 lowercase hex characters")
    if not values["evidence_ids"]:
        raise ValueError("evidence_ids must contain at least one evidence id")
    _datetime(values["admitted_at"], "admitted_at")
    core = {**values}
    record_hash = _sha(core)
    record = CanonicalInvestmentAdmissionRecord(
        **core,
        evidence_ids=tuple(core["evidence_ids"]),
        admission_record_hash=record_hash,
    )
    validate_canonical_investment_admission_record(record)
    return record


def validate_canonical_investment_admission_record(
    record: CanonicalInvestmentAdmissionRecord | Mapping[str, Any],
) -> None:
    data = record.to_dict() if isinstance(record, CanonicalInvestmentAdmissionRecord) else dict(record)
    required = {
        "admission_id",
        "contract_version",
        "domain",
        "case_id",
        "market",
        "symbol",
        "company",
        "cutoff_date",
        "status",
        "domain_status",
        "source_record_id",
        "source_record_hash",
        "output_hash",
        "producer_version",
        "evidence_ids",
        "admitted_at",
        "admission_record_hash",
    }
    if set(data) != required:
        raise ValueError("canonical investment admission record fields are invalid")
    if data["contract_version"] != CANONICAL_INVESTMENT_ADMISSION_VERSION:
        raise ValueError("canonical investment admission record version mismatch")
    if data["status"] not in ADMISSION_RECORD_STATUSES:
        raise ValueError("canonical investment admission record status is invalid")
    if data["domain"] not in ADMISSION_DOMAINS:
        raise ValueError("canonical investment admission record domain is invalid")
    if data["domain_status"] not in DOMAIN_STATUSES:
        raise ValueError("canonical investment admission domain status is invalid")
    _text(data["admission_id"], "admission_id")
    _text(data["case_id"], "case_id")
    _text(data["market"], "market")
    _text(data["symbol"], "symbol")
    _text(data["company"], "company")
    _date(data["cutoff_date"], "cutoff_date")
    _text(data["source_record_id"], "source_record_id")
    _text(data["producer_version"], "producer_version")
    if not _SHA256_RE.fullmatch(str(data["source_record_hash"])):
        raise ValueError("source_record_hash is invalid")
    if not _SHA256_RE.fullmatch(str(data["output_hash"])):
        raise ValueError("output_hash is invalid")
    if not isinstance(data["evidence_ids"], list) or not data["evidence_ids"]:
        raise ValueError("evidence_ids must be a non-empty list")
    if len(data["evidence_ids"]) != len(set(data["evidence_ids"])):
        raise ValueError("evidence_ids must be unique")
    _datetime(data["admitted_at"], "admitted_at")
    if not _SHA256_RE.fullmatch(str(data["admission_record_hash"])):
        raise ValueError("admission_record_hash is invalid")
    core = {key: data[key] for key in required if key != "admission_record_hash"}
    if data["admission_record_hash"] != _sha(core):
        raise ValueError("canonical investment admission record hash mismatch")


class CanonicalInvestmentAdmissionResolver(Protocol):
    def resolve(
        self,
        reference: Mapping[str, Any],
        *,
        expected_domain: str,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> CanonicalInvestmentAdmissionRecord:
        ...


class InMemoryCanonicalInvestmentAdmissionRegistry:
    """Test/runtime resolver; B03 must supply domain-owned production producers."""

    def __init__(self) -> None:
        self._records: dict[str, CanonicalInvestmentAdmissionRecord] = {}

    def admit(self, record: CanonicalInvestmentAdmissionRecord) -> CanonicalInvestmentAdmissionReference:
        validate_canonical_investment_admission_record(record)
        if record.status != ADMITTED_STATUS:
            raise ValueError("only ADMITTED records can enter the canonical admission registry")
        existing = self._records.get(record.admission_record_hash)
        if existing is not None and existing.to_dict() != record.to_dict():
            raise ValueError("admission registry already contains conflicting record hash")
        self._records[record.admission_record_hash] = record
        return record.reference()

    def resolve(
        self,
        reference: Mapping[str, Any],
        *,
        expected_domain: str,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> CanonicalInvestmentAdmissionRecord:
        ref = CanonicalInvestmentAdmissionReference.from_mapping(reference)
        if ref.domain != str(expected_domain).strip().upper():
            raise ValueError("canonical admission domain mismatch")
        expected = {
            "case_id": _text(case_id, "case_id"),
            "market": _text(market, "market").upper(),
            "symbol": _text(symbol, "symbol").upper(),
            "company": _text(company, "company"),
            "cutoff_date": _date(cutoff_date, "cutoff_date").isoformat(),
        }
        if ref.case_id != expected["case_id"]:
            raise ValueError("canonical admission case_id mismatch")
        if ref.market != expected["market"]:
            raise ValueError("canonical admission market mismatch")
        if ref.symbol != expected["symbol"]:
            raise ValueError("canonical admission symbol mismatch")
        if ref.company != expected["company"]:
            raise ValueError("canonical admission company mismatch")
        if ref.cutoff_date != expected["cutoff_date"]:
            raise ValueError("canonical admission cutoff_date mismatch")

        record = self._records.get(ref.admission_record_hash)
        if record is None:
            raise ValueError("canonical admission record is unknown or not admitted")
        validate_canonical_investment_admission_record(record)
        if record.reference().to_dict() != ref.to_dict():
            raise ValueError("canonical admission reference does not match admitted record")
        if record.status != ADMITTED_STATUS:
            raise ValueError("canonical admission record is not ADMITTED")
        return record


def validate_canonical_investment_admission_reference(
    reference: Mapping[str, Any],
    *,
    expected_domain: str,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: date,
) -> None:
    ref = CanonicalInvestmentAdmissionReference.from_mapping(reference)
    if ref.domain != str(expected_domain).strip().upper():
        raise ValueError("canonical admission domain mismatch")
    if ref.case_id != str(case_id):
        raise ValueError("canonical admission case_id mismatch")
    if ref.market != str(market).strip().upper():
        raise ValueError("canonical admission market mismatch")
    if ref.symbol != str(symbol).strip().upper():
        raise ValueError("canonical admission symbol mismatch")
    if ref.company != str(company):
        raise ValueError("canonical admission company mismatch")
    if ref.cutoff_date != _date(cutoff_date, "cutoff_date").isoformat():
        raise ValueError("canonical admission cutoff_date mismatch")


__all__ = [
    "ADMISSION_DOMAINS",
    "ADMITTED_STATUS",
    "CANONICAL_INVESTMENT_ADMISSION_VERSION",
    "CanonicalInvestmentAdmissionAdmissionReference",
    "CanonicalInvestmentAdmissionReference",
    "CanonicalInvestmentAdmissionRecord",
    "CanonicalInvestmentAdmissionResolver",
    "InMemoryCanonicalInvestmentAdmissionRegistry",
    "build_canonical_investment_admission",
    "validate_canonical_investment_admission_record",
    "validate_canonical_investment_admission_reference",
]
