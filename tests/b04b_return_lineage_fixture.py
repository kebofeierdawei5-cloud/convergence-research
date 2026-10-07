from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from iios_mvp.canonical_independent_forecast import (
    CanonicalIndependentForecastResolver,
    InMemoryCanonicalIndependentForecastRegistry,
)
from iios_mvp.canonical_investment_admission_v01 import (
    InMemoryCanonicalInvestmentAdmissionRegistry,
    build_canonical_investment_admission,
)
from iios_mvp.forecast_valuation_return_lineage_v01 import (
    FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
    InMemoryCanonicalValuationOutputResolver,
    build_canonical_valuation_output,
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def bind_return_lineage(
    case: dict[str, Any],
    *,
    independent_forecast_resolver: CanonicalIndependentForecastResolver | None = None,
    valuation_admission_registry: InMemoryCanonicalInvestmentAdmissionRegistry | None = None,
    valuation_output_resolver: InMemoryCanonicalValuationOutputResolver | None = None,
) -> tuple[
    dict[str, Any],
    InMemoryCanonicalIndependentForecastRegistry | CanonicalIndependentForecastResolver,
    InMemoryCanonicalValuationOutputResolver,
]:
    cutoff = date.fromisoformat(str(case["cutoff_date"]))
    forecast_registry = independent_forecast_resolver or InMemoryCanonicalIndependentForecastRegistry()
    gap = case.get("expectation_gap")
    if isinstance(gap, Mapping) and isinstance(gap.get("independent_forecast_ref"), Mapping):
        forecast_ref = dict(gap["independent_forecast_ref"])
    else:
        horizon_token = str(case["return_gate"]["horizon_years"]).replace(".", "_")
        forecast_ref = forecast_registry.admit_independent_forecast({
            "case_id": case["case_id"],
            "market": case["market"],
            "symbol": case["symbol"],
            "cutoff_date": cutoff.isoformat(),
            "forecast_id": f"B04B-{case['symbol']}-FORECAST-H{horizon_token}",
            "forecast_version": "B04B-FIXTURE-FORECAST-0.1",
            "model_version": "B04B-FIXTURE-MODEL-0.1",
            "variable_id": "forward_eps",
            "value": "1",
            "unit": "CNY/share",
            "basis": "B04B fixture",
            "horizon_years": str(case["return_gate"]["horizon_years"]),
            "forecast_origin": f"{cutoff.isoformat()}T12:00:00+00:00",
            "known_at": f"{cutoff.isoformat()}T15:00:00+00:00",
            "prepared_without_current_price": True,
            "evidence_ids": ["B04B-FORECAST-EVIDENCE"],
        }).to_dict()

    gate = case["return_gate"]
    valuation_output = build_canonical_valuation_output({
        "valuation_id": f"B04B-{case['symbol']}-VALUATION-{_sha(gate)[:12]}",
        "valuation_version": "B04B-FIXTURE-VALUATION-0.1",
        "case_id": case["case_id"],
        "market": case["market"],
        "symbol": case["symbol"],
        "company": case["company"],
        "cutoff_date": cutoff.isoformat(),
        "forecast_ref": forecast_ref,
        "horizon_years": str(gate["horizon_years"]),
        "reference_value_per_share": str(gate["entry_value_reference"]),
        "scenarios": {
            name: {
                "probability": str(gate["scenarios"][name]["probability"]),
                "value_per_share": str(gate["scenarios"][name]["terminal_value_per_share"]),
                "cash_distributions_per_share": str(gate["scenarios"][name]["cash_distributions_per_share"]),
            }
            for name in ("bear", "base", "bull")
        },
        "evidence_ids": ["B04B-VALUATION-EVIDENCE"],
    })

    admissions = valuation_admission_registry or InMemoryCanonicalInvestmentAdmissionRegistry()
    admission = build_canonical_investment_admission(
        admission_id=valuation_output["valuation_id"] + "-ADMISSION",
        domain="VALUATION",
        case_id=case["case_id"],
        market=case["market"],
        symbol=case["symbol"],
        company=case["company"],
        cutoff_date=cutoff.isoformat(),
        domain_status="PASS",
        source_record_id=valuation_output["valuation_id"],
        source_record_hash=_sha({"valuation": valuation_output}),
        output_hash=valuation_output["output_hash"],
        producer_version="B04B-VALUATION-PRODUCER-0.1",
        evidence_ids=["B04B-VALUATION-EVIDENCE"],
        admitted_at=f"{cutoff.isoformat()}T16:00:00+00:00",
    )
    valuation_ref = admissions.admit(admission).to_dict()
    valuation_resolver = valuation_output_resolver or InMemoryCanonicalValuationOutputResolver(admissions)
    valuation_resolver.register_output(
        valuation_reference=valuation_ref,
        valuation_output=valuation_output,
        case_id=case["case_id"],
        market=case["market"],
        symbol=case["symbol"],
        company=case["company"],
        cutoff_date=cutoff,
    )

    result = dict(case)
    result["return_gate"] = dict(gate)
    result["return_gate"]["lineage_version"] = FORECAST_VALUATION_RETURN_LINEAGE_VERSION
    result["return_gate"]["canonical_forecast_ref"] = forecast_ref
    result["return_gate"]["canonical_valuation_ref"] = valuation_ref
    return result, forecast_registry, valuation_resolver


__all__ = ["bind_return_lineage"]
