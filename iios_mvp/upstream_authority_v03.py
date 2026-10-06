from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .canonical_investment_admission_v01 import (
    ADMISSION_DOMAINS,
    CanonicalInvestmentAdmissionRecord,
    CanonicalInvestmentAdmissionResolver,
)

CORE_STATUS_DOMAINS = (
    "REALITY",
    "QUALITY",
    "VALUE_DRIVER",
    "VALUATION",
    "FORECAST",
)

STATUS_FIELDS = {
    "REALITY": "reality_status",
    "QUALITY": "quality_gate_status",
    "VALUE_DRIVER": "value_driver_status",
    "VALUATION": "valuation_status",
    "FORECAST": "forecast_status",
}


def resolve_core_upstream_authority(
    *,
    admission_refs: Mapping[str, Mapping[str, Any]],
    resolver: CanonicalInvestmentAdmissionResolver,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: date,
) -> dict[str, Any]:
    if set(admission_refs) != set(CORE_STATUS_DOMAINS):
        missing = sorted(set(CORE_STATUS_DOMAINS) - set(admission_refs))
        extra = sorted(set(admission_refs) - set(CORE_STATUS_DOMAINS))
        parts = []
        if missing:
            parts.append(f"missing domains: {missing}")
        if extra:
            parts.append(f"unsupported domains: {extra}")
        raise ValueError("canonical upstream admission refs are incomplete; " + "; ".join(parts))

    resolved_records: dict[str, CanonicalInvestmentAdmissionRecord] = {}
    resolved_states: dict[str, str] = {}

    for domain in CORE_STATUS_DOMAINS:
        if domain not in ADMISSION_DOMAINS:
            raise ValueError(f"unsupported core admission domain: {domain}")
        record = resolver.resolve(
            admission_refs[domain],
            expected_domain=domain,
            case_id=case_id,
            market=market,
            symbol=symbol,
            company=company,
            cutoff_date=cutoff_date,
        )
        resolved_records[domain] = record
        resolved_states[STATUS_FIELDS[domain]] = record.domain_status

    return {
        "resolved_records": resolved_records,
        "resolved_states": resolved_states,
    }


def validate_core_upstream_authority(
    *,
    admission_refs: Mapping[str, Mapping[str, Any]],
    declared_states: Mapping[str, Any],
    resolver: CanonicalInvestmentAdmissionResolver,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: date,
) -> dict[str, Any]:
    result = resolve_core_upstream_authority(
        admission_refs=admission_refs,
        resolver=resolver,
        case_id=case_id,
        market=market,
        symbol=symbol,
        company=company,
        cutoff_date=cutoff_date,
    )

    for field, resolved in result["resolved_states"].items():
        declared = str(declared_states.get(field, "")).strip().upper()
        if declared != resolved:
            raise ValueError(
                f"canonical upstream authority {field} drift: "
                f"declared={declared!r} resolved={resolved!r}"
            )

    return result


__all__ = [
    "CORE_STATUS_DOMAINS",
    "STATUS_FIELDS",
    "resolve_core_upstream_authority",
    "validate_core_upstream_authority",
]
