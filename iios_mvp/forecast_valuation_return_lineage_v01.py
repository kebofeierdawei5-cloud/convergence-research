from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Mapping, Protocol

from .canonical_investment_admission_v01 import (
    CanonicalInvestmentAdmissionReference,
    CanonicalInvestmentAdmissionResolver,
)
from .canonical_independent_forecast import (
    CanonicalIndependentForecastReference,
    CanonicalIndependentForecastResolver,
)

CANONICAL_VALUATION_OUTPUT_VERSION = "IIOS-VALUATION-OUTPUT-0.1"
FORECAST_VALUATION_RETURN_LINEAGE_VERSION = "IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.1"
ADMITTED_STATUS = "ADMITTED"
SCENARIOS = ("bear", "base", "bull")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _dec(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{path} must be finite")
    return result


def _date(value: Any, path: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be ISO date") from exc


def _strict_ref(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    # The B02 generic reference is the authority-bearing object for valuation.
    return CanonicalInvestmentAdmissionReference.from_mapping(value).to_dict()


def _forecast_ref(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return CanonicalIndependentForecastReference.from_mapping(value).to_dict()


def _validate_valuation_output(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "valuation_id",
        "valuation_version",
        "case_id",
        "market",
        "symbol",
        "company",
        "cutoff_date",
        "forecast_ref",
        "horizon_years",
        "reference_value_per_share",
        "scenarios",
        "evidence_ids",
        "output_hash",
    }
    if set(record) != required:
        raise ValueError("canonical valuation output fields are invalid")
    if record["schema_version"] != CANONICAL_VALUATION_OUTPUT_VERSION:
        raise ValueError("canonical valuation output version mismatch")
    for field in ("valuation_id", "valuation_version", "case_id", "market", "symbol", "company"):
        if not str(record[field]).strip():
            raise ValueError(f"canonical valuation output {field} is required")
    cutoff = _date(record["cutoff_date"], "valuation.cutoff_date")
    _ = cutoff
    _forecast_ref(record["forecast_ref"], "valuation.forecast_ref")
    horizon = _dec(record["horizon_years"], "valuation.horizon_years")
    if horizon <= 0:
        raise ValueError("canonical valuation output horizon_years must be > 0")
    reference = _dec(record["reference_value_per_share"], "valuation.reference_value_per_share")
    if reference <= 0:
        raise ValueError("canonical valuation reference value must be > 0")
    scenarios = record["scenarios"]
    if not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        raise ValueError("canonical valuation scenarios must contain Bear/Base/Bull exactly")
    probabilities: list[Decimal] = []
    for name in SCENARIOS:
        item = scenarios[name]
        if not isinstance(item, Mapping) or set(item) != {
            "probability", "value_per_share", "cash_distributions_per_share"
        }:
            raise ValueError(f"canonical valuation scenario {name} is invalid")
        p = _dec(item["probability"], f"valuation.scenarios.{name}.probability")
        value = _dec(item["value_per_share"], f"valuation.scenarios.{name}.value_per_share")
        distributions = _dec(
            item["cash_distributions_per_share"],
            f"valuation.scenarios.{name}.cash_distributions_per_share",
        )
        if p < 0 or p > 1:
            raise ValueError(f"canonical valuation scenario {name} probability is invalid")
        if value < 0 or distributions < 0:
            raise ValueError(f"canonical valuation scenario {name} values must be >= 0")
        probabilities.append(p)
    if sum(probabilities, Decimal("0")) != Decimal("1"):
        raise ValueError("canonical valuation scenario probabilities must sum exactly to 1")
    evidence_ids = record["evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("canonical valuation output evidence_ids are required")
    if len(evidence_ids) != len(set(evidence_ids)) or any(not str(x).strip() for x in evidence_ids):
        raise ValueError("canonical valuation output evidence_ids must be unique and non-empty")
    expected_hash = _sha({k: record[k] for k in required if k != "output_hash"})
    if record["output_hash"] != expected_hash:
        raise ValueError("canonical valuation output hash mismatch")


class CanonicalValuationOutputResolver(Protocol):
    def resolve_valuation_output(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ...


class InMemoryCanonicalValuationOutputResolver:
    """Test/runtime double: values are accepted only when bound to an admitted B02 VALUATION output_hash."""

    def __init__(self, admission_resolver: CanonicalInvestmentAdmissionResolver) -> None:
        self._admission_resolver = admission_resolver
        self._outputs: dict[str, dict[str, Any]] = {}

    def register_output(
        self,
        *,
        valuation_reference: Mapping[str, Any],
        valuation_output: Mapping[str, Any],
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> None:
        ref = _strict_ref(valuation_reference, "valuation_reference")
        if ref["domain"] != "VALUATION":
            raise ValueError("valuation reference must use VALUATION domain")
        admission = self._admission_resolver.resolve(
            ref,
            expected_domain="VALUATION",
            case_id=case_id,
            market=market,
            symbol=symbol,
            company=company,
            cutoff_date=cutoff_date,
        )
        output = dict(valuation_output)
        _validate_valuation_output(output)
        if output["case_id"] != case_id or output["market"] != market or output["symbol"] != symbol or output["company"] != company:
            raise ValueError("valuation output identity mismatch")
        if _date(output["cutoff_date"], "valuation.cutoff_date") != cutoff_date:
            raise ValueError("valuation output cutoff_date mismatch")
        if admission.output_hash != output["output_hash"]:
            raise ValueError("admitted VALUATION output_hash does not match materialized valuation output")
        self._outputs[ref["admission_record_hash"]] = output

    def resolve_valuation_output(
        self,
        reference: Mapping[str, Any],
        *,
        case_id: str,
        market: str,
        symbol: str,
        company: str,
        cutoff_date: date,
    ) -> dict[str, Any]:
        ref = _strict_ref(reference, "valuation_reference")
        admission = self._admission_resolver.resolve(
            ref,
            expected_domain="VALUATION",
            case_id=case_id,
            market=market,
            symbol=symbol,
            company=company,
            cutoff_date=cutoff_date,
        )
        output = self._outputs.get(admission.admission_record_hash)
        if output is None:
            raise ValueError("canonical valuation output is unavailable")
        _validate_valuation_output(output)
        if output["output_hash"] != admission.output_hash:
            raise ValueError("canonical valuation output no longer matches admitted output_hash")
        return dict(output)


def validate_forecast_valuation_return_lineage(
    *,
    return_gate: Mapping[str, Any],
    canonical_forecast_ref: Mapping[str, Any],
    canonical_valuation_ref: Mapping[str, Any],
    independent_forecast_resolver: CanonicalIndependentForecastResolver,
    valuation_output_resolver: CanonicalValuationOutputResolver,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: date,
) -> dict[str, Any]:
    if return_gate.get("lineage_version") != FORECAST_VALUATION_RETURN_LINEAGE_VERSION:
        raise ValueError("return gate lineage version mismatch")
    forecast_ref = _forecast_ref(canonical_forecast_ref, "return_gate.canonical_forecast_ref")
    valuation_ref = _strict_ref(canonical_valuation_ref, "return_gate.canonical_valuation_ref")
    if valuation_ref["domain"] != "VALUATION":
        raise ValueError("return gate canonical_valuation_ref must use VALUATION domain")

    forecast = independent_forecast_resolver.resolve_independent_forecast(
        forecast_ref,
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=cutoff_date,
    )
    valuation = valuation_output_resolver.resolve_valuation_output(
        valuation_ref,
        case_id=case_id,
        market=market,
        symbol=symbol,
        company=company,
        cutoff_date=cutoff_date,
    )
    valuation_forecast_ref = _forecast_ref(valuation["forecast_ref"], "valuation.forecast_ref")
    if valuation_forecast_ref != forecast_ref:
        raise ValueError("valuation.forecast_ref does not equal return gate canonical_forecast_ref")

    expected_horizon = _dec(return_gate["horizon_years"], "return_gate.horizon_years")
    valuation_horizon = _dec(valuation["horizon_years"], "valuation.horizon_years")
    if expected_horizon != valuation_horizon:
        raise ValueError("return gate horizon must equal canonical valuation horizon")

    expected_reference = _dec(
        return_gate["entry_value_reference"],
        "return_gate.entry_value_reference",
    )
    canonical_reference = _dec(
        valuation["reference_value_per_share"],
        "valuation.reference_value_per_share",
    )
    if expected_reference != canonical_reference:
        raise ValueError("return_gate.entry_value_reference must equal canonical valuation reference value")

    scenarios = return_gate.get("scenarios")
    if not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        raise ValueError("return_gate.scenarios must contain Bear/Base/Bull exactly")
    canonical_scenarios = valuation["scenarios"]
    for name in SCENARIOS:
        supplied = scenarios[name]
        canonical = canonical_scenarios[name]
        if not isinstance(supplied, Mapping):
            raise ValueError(f"return_gate.scenarios.{name} must be an object")
        for field in ("probability", "terminal_value_per_share", "cash_distributions_per_share"):
            if field not in supplied:
                raise ValueError(f"return_gate.scenarios.{name}.{field} is required")
        if _dec(supplied["probability"], f"return_gate.scenarios.{name}.probability") != _dec(canonical["probability"], f"valuation.scenarios.{name}.probability"):
            raise ValueError(f"return_gate.scenarios.{name}.probability is not canonical")
        if _dec(supplied["terminal_value_per_share"], f"return_gate.scenarios.{name}.terminal_value_per_share") != _dec(canonical["value_per_share"], f"valuation.scenarios.{name}.value_per_share"):
            raise ValueError(f"return_gate.scenarios.{name}.terminal_value_per_share is not canonical")
        if _dec(supplied["cash_distributions_per_share"], f"return_gate.scenarios.{name}.cash_distributions_per_share") != _dec(canonical["cash_distributions_per_share"], f"valuation.scenarios.{name}.cash_distributions_per_share"):
            raise ValueError(f"return_gate.scenarios.{name}.cash_distributions_per_share is not canonical")

    return {
        "status": "PASS",
        "lineage_version": FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
        "canonical_forecast_ref": forecast_ref,
        "canonical_valuation_ref": valuation_ref,
        "forecast_id": forecast["forecast_id"],
        "forecast_version": forecast["forecast_version"],
        "valuation_id": valuation["valuation_id"],
        "valuation_version": valuation["valuation_version"],
        "valuation_primary_model": valuation.get("primary_model"),
        "horizon_years": str(valuation_horizon),
        "reference_value_per_share": str(canonical_reference),
        "binding": "FORECAST_REF_EQUALITY_AND_CANONICAL_VALUATION_SCENARIO_EQUALITY",
    }


__all__ = [
    "CANONICAL_VALUATION_OUTPUT_VERSION",
    "FORECAST_VALUATION_RETURN_LINEAGE_VERSION",
    "CanonicalValuationOutputResolver",
    "InMemoryCanonicalValuationOutputResolver",
    "validate_forecast_valuation_return_lineage",
]
