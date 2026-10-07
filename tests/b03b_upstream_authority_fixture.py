from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Any, Mapping

from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.quality_gate_v03 import build_quality_gate
from iios_mvp.decision_upstream_admission_v03 import (
    build_canonical_upstream_admission_v02,
    build_decision_upstream_admission,
)


CORE_DOMAINS = ("REALITY", "QUALITY", "VALUE_DRIVER", "VALUATION", "FORECAST")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _evidence_ids(output: Any) -> list[str]:
    ids: set[str] = set()
    if isinstance(output, list):
        for row in output:
            if isinstance(row, Mapping):
                ids.update(str(x) for x in row.get("evidence_ids", []) if str(x).strip())
        return sorted(ids) or ["B03B-FIXTURE-EVIDENCE"]
    if not isinstance(output, Mapping):
        return ["B03B-FIXTURE-EVIDENCE"]
    direct = output.get("evidence_ids")
    if isinstance(direct, list):
        ids.update(str(x) for x in direct if str(x).strip())
    facts = output.get("facts")
    if isinstance(facts, list):
        for row in facts:
            if isinstance(row, Mapping):
                ids.update(str(x) for x in row.get("evidence_ids", []) if str(x).strip())
    dimensions = output.get("dimensions")
    if isinstance(dimensions, list):
        for row in dimensions:
            if isinstance(row, Mapping):
                ids.update(str(x) for x in row.get("evidence_ids", []) if str(x).strip())
    return sorted(ids) or ["B03B-FIXTURE-EVIDENCE"]


def build_runtime_upstream_authority(
    *,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: date,
    reality: Mapping[str, Any],
    quality: Mapping[str, Any],
    value_driver: Mapping[str, Any],
    valuation: Mapping[str, Any],
    forecast: Mapping[str, Any],
    thesis: Mapping[str, Any],
    declared_statuses: Mapping[str, str] | None = None,
    registry: InMemoryCanonicalInvestmentAdmissionRegistry | None = None,
) -> tuple[InMemoryCanonicalInvestmentAdmissionRegistry, dict[str, Any]]:
    statuses = {
        "REALITY": "PASS",
        "QUALITY": "PASS",
        "VALUE_DRIVER": "PASS",
        "VALUATION": "PASS",
        "FORECAST": "PASS",
    }
    if declared_statuses:
        statuses.update({str(k).upper(): str(v).upper() for k, v in declared_statuses.items()})

    quality_gate = build_quality_gate(
        quality,
        case_id=case_id,
        cutoff_date=cutoff_date.isoformat(),
    )
    statuses["QUALITY"] = quality_gate["status"]
    outputs = {
        "REALITY": reality,
        "QUALITY": quality_gate,
        "VALUE_DRIVER": value_driver,
        "VALUATION": valuation,
        "FORECAST": forecast,
    }
    registry = registry or InMemoryCanonicalInvestmentAdmissionRegistry()
    refs: dict[str, dict[str, Any]] = {}

    for domain in CORE_DOMAINS:
        output = outputs[domain]
        output_hash = _sha(output)
        record = build_canonical_investment_admission(
            admission_id=f"B03B-{domain}-{symbol}",
            domain=domain,
            case_id=case_id,
            market=market,
            symbol=symbol,
            company=company,
            cutoff_date=cutoff_date.isoformat(),
            domain_status=statuses[domain],
            source_record_id=f"{domain}-DOMAIN-OUTPUT-{symbol}",
            source_record_hash=_sha({"domain": domain, "output": output}),
            output_hash=output_hash,
            producer_version=f"B03B-{domain}-PRODUCER-0.1",
            evidence_ids=_evidence_ids(output),
            admitted_at="2026-10-07T00:00:00+00:00",
        )
        refs[domain] = registry.admit(record).to_dict()

    base = build_decision_upstream_admission(
        case_id=case_id,
        cutoff_date=cutoff_date.isoformat(),
        reality_status=statuses["REALITY"],
        quality=quality,
        value_driver_status=statuses["VALUE_DRIVER"],
        valuation_status=statuses["VALUATION"],
        forecast_status=statuses["FORECAST"],
        thesis=thesis,
    )
    v02 = build_canonical_upstream_admission_v02(
        base_record=base,
        canonical_admission_refs=refs,
        resolver=registry,
        market=market,
        symbol=symbol,
        company=company,
    )
    return registry, v02
