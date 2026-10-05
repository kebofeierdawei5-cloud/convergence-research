from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Mapping

from .company_economic_core import build_company_economic_core, validate_company_economic_core
from .horizon_semantics import validate_horizon_selection
from .multi_model_market_implied_expectation_set import (
    MIEModelEvaluation,
    MIEModelEvaluationState,
    build_multi_model_market_implied_expectation_set,
)
from .market_implied_expectation import (
    CandidateCoverageAssessment,
    CandidateCoverageState,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyState,
)
from .p4f_mie_snapshot import (
    P4FProvenanceRecord,
    build_p4f_snapshot,
    replay_p4f_snapshot,
)
from .valuation import build_intrinsic_valuation


CORE03_VERSION = "IIOS-CORE-03-REAL-0.1"
FORECAST_VERSION = "IIOS-INDEPENDENT-FORECAST-0.1"
SCENARIOS = ("bear", "base", "bull")
FORECAST_YEARS = (2027, 2028, 2029)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _dec(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _dt(value: Any, field: str) -> datetime:
    raw = str(value).strip()
    if len(raw) == 10:
        try:
            d = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(f"{field} must be ISO date") from exc
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    try:
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _validate_evidence_record(record: Mapping[str, Any], cutoff: date, expected_id: str) -> None:
    if record.get("evidence_id") != expected_id:
        raise ValueError(f"market evidence must contain {expected_id}")
    for field in ("known_at", "retrieved_at", "content_sha256", "source_ref", "artifact_id"):
        if not str(record.get(field, "")).strip():
            raise ValueError(f"market evidence {expected_id}.{field} is required")
    if record.get("status") != "ADMITTED":
        raise ValueError(f"market evidence {expected_id} must be ADMITTED")
    if record.get("exact_bytes") is not True:
        raise ValueError(f"market evidence {expected_id}.exact_bytes must be true")
    sha = str(record["content_sha256"])
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError(f"market evidence {expected_id}.content_sha256 must be lowercase SHA-256")
    if _dt(record["known_at"], f"{expected_id}.known_at").date() > cutoff:
        raise ValueError(f"market evidence {expected_id} violates PIT")


def _validate_forecast(forecast: Mapping[str, Any], cutoff: date, evidence_ids: set[str]) -> dict[str, Any]:
    if forecast.get("version") != FORECAST_VERSION:
        raise ValueError("forecast.version mismatch")
    if forecast.get("method") != "BOTTOM_UP_DRIVER_SCENARIO":
        raise ValueError("forecast.method must be BOTTOM_UP_DRIVER_SCENARIO")
    years = tuple(int(x) for x in forecast.get("years", ()))
    if years != FORECAST_YEARS:
        raise ValueError(f"forecast.years must equal {FORECAST_YEARS}")

    probabilities = forecast.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ValueError("forecast.probabilities is required")
    total = sum((_dec(probabilities.get(s), f"forecast.probabilities.{s}") for s in SCENARIOS), Decimal("0"))
    if total != Decimal("1"):
        raise ValueError("forecast scenario probabilities must sum exactly to 1")
    for scenario in SCENARIOS:
        if _dec(probabilities[scenario], f"forecast.probabilities.{scenario}") < 0:
            raise ValueError("scenario probability cannot be negative")

    scenarios = forecast.get("scenarios")
    if not isinstance(scenarios, dict):
        raise ValueError("forecast.scenarios is required")
    normalized = {}
    for scenario in SCENARIOS:
        row = scenarios.get(scenario)
        if not isinstance(row, dict):
            raise ValueError(f"forecast.scenarios.{scenario} must be an object")
        for key in ("revenue_bn_cny", "fcf_proxy_bn_cny", "gross_margin_pct", "incremental_roic_pct"):
            values = row.get(key)
            if not isinstance(values, list) or len(values) != len(FORECAST_YEARS):
                raise ValueError(f"forecast.scenarios.{scenario}.{key} must contain three yearly values")
        refs = row.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"forecast.scenarios.{scenario}.evidence_ids is required")
        if not set(refs).issubset(evidence_ids):
            raise ValueError(f"forecast.scenarios.{scenario} references evidence outside the admitted Core-02 set")
        for key in ("revenue_bn_cny", "fcf_proxy_bn_cny", "gross_margin_pct", "incremental_roic_pct"):
            if any(_dec(v, f"forecast.scenarios.{scenario}.{key}") <= 0 for v in row[key]):
                raise ValueError(f"forecast.scenarios.{scenario}.{key} must be > 0")
        normalized[scenario] = {
            "revenue_bn_cny": [str(_dec(v, f"forecast.scenarios.{scenario}.revenue_bn_cny")) for v in row["revenue_bn_cny"]],
            "fcf_proxy_bn_cny": [str(_dec(v, f"forecast.scenarios.{scenario}.fcf_proxy_bn_cny")) for v in row["fcf_proxy_bn_cny"]],
            "gross_margin_pct": [str(_dec(v, f"forecast.scenarios.{scenario}.gross_margin_pct")) for v in row["gross_margin_pct"]],
            "incremental_roic_pct": [str(_dec(v, f"forecast.scenarios.{scenario}.incremental_roic_pct")) for v in row["incremental_roic_pct"]],
            "evidence_ids": sorted(set(refs)),
            "rationale": str(row.get("rationale", "")).strip(),
        }
        if not normalized[scenario]["rationale"]:
            raise ValueError(f"forecast.scenarios.{scenario}.rationale is required")

    horizon_selection = validate_horizon_selection(
        horizon_years=forecast.get("horizon_years"),
        horizon_override=forecast.get("horizon_override"),
        horizon_override_basis=forecast.get("horizon_override_basis"),
        horizon_selection_rationale=forecast.get("horizon_selection_rationale"),
        path="forecast",
    )
    forecast_horizon = _dec(horizon_selection["horizon_years"], "forecast.horizon_years")
    if forecast_horizon != Decimal("3") or tuple(range(2027, 2030)) != FORECAST_YEARS:
        raise ValueError("CORE-03 real case requires H=3 for the 2027-2029 forecast package")
    forecast_cutoff = _date(forecast.get("cutoff_date"), "forecast.cutoff_date")
    if forecast_cutoff != cutoff:
        raise ValueError("forecast.cutoff_date must equal case cutoff")
    return {
        "version": forecast["version"],
        "method": forecast["method"],
        "cutoff_date": forecast_cutoff.isoformat(),
        "years": list(FORECAST_YEARS),
        "probabilities": {s: str(_dec(probabilities[s], f"forecast.probabilities.{s}")) for s in SCENARIOS},
        "scenarios": normalized,
        "cash_flow_diagnostic": forecast.get("cash_flow_diagnostic") or {},
        "horizon_years": horizon_selection["horizon_years"],
        "horizon_override": horizon_selection["horizon_override"],
        "horizon_override_basis": horizon_selection["horizon_override_basis"],
        "horizon_selection_rationale": horizon_selection["horizon_selection_rationale"],
        "valuation_focus": "FCF_AND_INCREMENTAL_ROIC",
    }


def _build_dcf_input(normalized_forecast: Mapping[str, Any], valuation_assumptions: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    valuation = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "dcf",
            "secondary_models": [],
            "cross_check_models": [],
            "economic_profile": "enterprise_operating_business",
            "rationale": (
                "Human-selected DCF because the case's highest-value uncertainty is the conversion "
                "of growth and incremental CAPEX into sustainable FCF and incremental ROIC."
            ),
            "alternatives": ["ev_ebitda", "forward_pe", "sotp"],
        },
        "model_inputs": {"dcf": {}},
        "aggregation": {},
    }
    forecast = {}
    for scenario in SCENARIOS:
        row = normalized_forecast["scenarios"][scenario]
        forecast[scenario] = {
            "net_profit": Decimal("1"),
            "revenue": Decimal(row["revenue_bn_cny"][0]) * Decimal("1000000000"),
        }
        dcf_row = {
            "fcf": [Decimal(x) * Decimal("1000000000") for x in row["fcf_proxy_bn_cny"]],
            "discount_rate": _dec(valuation_assumptions[scenario]["discount_rate"], f"valuation_assumptions.{scenario}.discount_rate"),
            "terminal_growth": _dec(valuation_assumptions[scenario]["terminal_growth"], f"valuation_assumptions.{scenario}.terminal_growth"),
        }
        valuation["model_inputs"]["dcf"][scenario] = dcf_row
    valuation["model_inputs"]["net_debt"] = -_dec(valuation_assumptions["net_cash_bn_cny"], "valuation_assumptions.net_cash_bn_cny") * Decimal("1000000000")
    shares = _dec(valuation_assumptions["shares_outstanding"], "valuation_assumptions.shares_outstanding")
    return forecast, valuation, shares


def _build_blocked_p4f(
    *,
    case_id: str,
    cutoff: date,
    market_evidence: Mapping[str, Any],
    price_evidence: Mapping[str, Any],
    candidate_models: list[str],
) -> dict[str, Any]:
    e = market_evidence
    candidate_coverage = CandidateCoverageAssessment(
        status=CandidateCoverageState.INSUFFICIENT,
        scope_basis="CORE-02 valuation route candidate set; historical/current market-model identification bundle not admitted for this case",
        candidate_model_ids=tuple(candidate_models),
        evidence_ids=(str(price_evidence["evidence_id"]),),
        rationale="Only the current price observation is admitted; model-specific historical observations needed for P3/P4 candidate coverage are absent.",
    )
    evidence_sufficiency = EvidenceSufficiencyAssessment(
        status=EvidenceSufficiencyState.INSUFFICIENT,
        rationale="No PIT market-model observation history is admitted for EV/EBITDA, DCF, forward PE or SOTP.",
        evidence_ids=(str(price_evidence["evidence_id"]),),
    )
    evaluations = tuple(
        MIEModelEvaluation.blocked(
            model_id=model,
            evidence_ids=(str(price_evidence["evidence_id"]),),
            rationale="Blocked at P4-F because candidate market-model evidence/history is insufficient; no implied requirement is materialized.",
        )
        for model in candidate_models
    )
    mie_set = build_multi_model_market_implied_expectation_set(
        set_id=f"MIESET-{case_id}-P4F",
        candidate_coverage=candidate_coverage,
        evidence_sufficiency=evidence_sufficiency,
        model_evaluations=evaluations,
        qualification_rationale="CORE-03 fail-closed MIE attempt: insufficient PIT market-model evidence.",
        evidence_ids=(str(price_evidence["evidence_id"]),),
    )
    provenance = P4FProvenanceRecord(
        evidence_id=str(price_evidence["evidence_id"]),
        variable="market_price",
        unit="CNY/share",
        basis="2026-09-30 close",
        observation_date=date(2026, 9, 30),
        known_at=_dt(price_evidence["known_at"], f"{price_evidence['evidence_id']}.known_at"),
        source=str(price_evidence.get("source_ref", "SZSE:MARKET_DATA")),
        source_location=str(price_evidence.get("source_locator") or price_evidence["source_ref"]),
        content_sha256=str(price_evidence["content_sha256"]),
        captured_at=datetime(2026, 10, 4, 22, 0, tzinfo=timezone.utc),
    )
    snapshot = build_p4f_snapshot(
        case_id=case_id,
        cutoff_date=cutoff,
        created_at=datetime(2026, 10, 4, 22, 0, tzinfo=timezone.utc),
        mie_set=mie_set,
        provenance_records=(provenance,),
    )
    replay = replay_p4f_snapshot(snapshot)
    if replay["replay_status"] != "PASS":
        raise ValueError("generated blocked P4-F snapshot did not replay")
    return {"snapshot": snapshot, "replay": replay}


def build_core03_package(
    core02_input: Mapping[str, Any],
    forecast: Mapping[str, Any],
    valuation_assumptions: Mapping[str, Any],
    market_evidence: Mapping[str, Any],
    price_evidence: Mapping[str, Any],
    forecast_evidence: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    case = core02_input.get("case")
    if not isinstance(case, dict):
        raise ValueError("core02_input.case is required")
    cutoff = _date(case["temporal_scope"]["cutoff_date"], "case.cutoff_date")
    for record_id in ("E001", "E002", "E003", "E004", "E005", "E006", "E007"):
        record = next((x for x in case.get("evidence", []) if x.get("evidence_id") == record_id), None)
        if record is None:
            raise ValueError(f"Core-02 input missing {record_id}")

    core02 = build_company_economic_core(
        case,
        core02_input["reality"],
        core02_input["trust"],
        core02_input["quality"],
        core02_input["value_core"],
        core02_input["value_driver_ranking"],
        generated_at="2026-10-04T22:00:00+00:00",
    )
    core02_errors = validate_company_economic_core(core02)
    if core02_errors:
        raise ValueError("Core-02 input did not reproduce validly: " + "; ".join(core02_errors))

    _validate_evidence_record(market_evidence, cutoff, "E008")
    if market_evidence.get("variable") != "current_share_count":
        raise ValueError("E008 must be current_share_count")
    price_evidence_id = str(valuation_assumptions.get("price_evidence_id", "")).strip()
    if not price_evidence_id:
        raise ValueError("valuation price_evidence_id is required")
    _validate_evidence_record(price_evidence, cutoff, price_evidence_id)
    if str(price_evidence.get("field_id", "")) != "market_price.close.2026-09-30":
        raise ValueError(f"{price_evidence_id} must be the 2026-09-30 market close evidence")
    if _dec(price_evidence.get("value"), f"{price_evidence_id}.value") != _dec(valuation_assumptions.get("price_cny"), "valuation_assumptions.price_cny"):
        raise ValueError("valuation price must equal admitted price evidence value")
    forecast_evidence = forecast_evidence or []
    forecast_evidence_by_id = {}
    for record in forecast_evidence:
        record_id = str(record.get("evidence_id", "")).strip()
        if not record_id:
            raise ValueError("forecast evidence evidence_id is required")
        _validate_evidence_record(record, cutoff, record_id)
        forecast_evidence_by_id[record_id] = record
    if len(forecast_evidence_by_id) != len(forecast_evidence):
        raise ValueError("forecast evidence IDs must be unique")
    admissible_forecast_ids = set(core02["evidence_admission"]["evidence_ids"]) | {"E008"} | set(forecast_evidence_by_id)
    normalized_forecast = _validate_forecast(forecast, cutoff, admissible_forecast_ids)

    net_cash = _dec(valuation_assumptions.get("net_cash_bn_cny"), "valuation_assumptions.net_cash_bn_cny")
    shares = _dec(valuation_assumptions.get("shares_outstanding"), "valuation_assumptions.shares_outstanding")
    price = _dec(valuation_assumptions.get("price_cny"), "valuation_assumptions.price_cny")
    if net_cash <= 0 or shares <= 0 or price <= 0:
        raise ValueError("current market context must be positive")
    if valuation_assumptions.get("price_evidence_id") != price_evidence_id:
        raise ValueError("valuation price_evidence_id must match the admitted price evidence")
    if valuation_assumptions.get("share_count_evidence_id") != "E008":
        raise ValueError("valuation share count must bind to E008")

    # Existing valuation engine is reused; DCF stays authoritative, other models are checks only.
    forecast_payload = {}
    valuation_payload = {
        "model_selection": {
            "selection_method": "HUMAN",
            "primary_model": "dcf",
            "secondary_models": [],
            "cross_check_models": [],
            "economic_profile": "enterprise_operating_business",
            "rationale": (
                "DCF is the human-selected primary model because the principal research question "
                "is whether incremental growth and CAPEX convert into sustainable FCF and incremental ROIC."
            ),
            "alternatives": ["ev_ebitda", "forward_pe", "sotp"],
        },
        "model_inputs": {"dcf": {}},
        "aggregation": {},
    }
    for scenario in SCENARIOS:
        row = normalized_forecast["scenarios"][scenario]
        forecast_payload[scenario] = {
            "net_profit": Decimal("1"),
            "revenue": Decimal(row["revenue_bn_cny"][0]) * Decimal("1000000000"),
        }
        valuation_payload["model_inputs"]["dcf"][scenario] = {
            "fcf": [Decimal(x) * Decimal("1000000000") for x in row["fcf_proxy_bn_cny"]],
            "discount_rate": _dec(valuation_assumptions[scenario]["discount_rate"], f"valuation_assumptions.{scenario}.discount_rate"),
            "terminal_growth": _dec(valuation_assumptions[scenario]["terminal_growth"], f"valuation_assumptions.{scenario}.terminal_growth"),
        }
    valuation_payload["model_inputs"]["net_debt"] = -net_cash * Decimal("1000000000")

    intrinsic = build_intrinsic_valuation(forecast_payload, valuation_payload, shares)
    base = _dec(intrinsic["intrinsic_value_range"]["base"], "intrinsic.base")
    expected_value = sum(
        _dec(normalized_forecast["probabilities"][scenario], f"probability.{scenario}") *
        _dec(intrinsic["models"]["dcf"][scenario]["value_per_share"], f"intrinsic.dcf.{scenario}")
        for scenario in SCENARIOS
    )
    horizon = _dec(normalized_forecast["horizon_years"], "forecast.horizon_years")
    expected_cagr = (expected_value / price) ** (Decimal("1") / horizon) - Decimal("1")

    p4f = _build_blocked_p4f(
        case_id=case["case_id"],
        cutoff=cutoff,
        market_evidence=market_evidence,
        price_evidence=price_evidence,
        candidate_models=core02["value_core"]["model_route"]["candidate_models"],
    )

    core_without_audit = {
        "schema_version": CORE03_VERSION,
        "case_id": case["case_id"],
        "symbol": case["request"]["symbol"],
        "as_of_date": case["temporal_scope"]["as_of_date"],
        "cutoff_date": case["temporal_scope"]["cutoff_date"],
        "status": "CONDITIONAL",
        "research_question": (
            "Can incremental capacity investment sustain high incremental ROIC while converting "
            "earnings growth into durable FCF?"
        ),
        "core02_status": core02["status"],
        "independent_forecast": normalized_forecast,
        "company_valuation": {
            "status": "CONDITIONAL",
            "primary_model": "dcf",
            "selection_authority": "HUMAN",
            "intrinsic_value_per_share": str(base),
            "intrinsic_value_range": {
                "bear": str(intrinsic["intrinsic_value_range"]["low"]),
                "base": str(intrinsic["intrinsic_value_range"]["base"]),
                "bull": str(intrinsic["intrinsic_value_range"]["high"]),
            },
            "probability_weighted_value_per_share": str(expected_value),
            "expected_3y_cagr_at_current_price": str(expected_cagr),
            "expected_annualized_return_at_horizon": str(expected_cagr),
            "horizon_return_reference": {
                "horizon_years": normalized_forecast["horizon_years"],
                "horizon_override": normalized_forecast["horizon_override"],
                "horizon_override_basis": normalized_forecast["horizon_override_basis"],
                "horizon_selection_rationale": normalized_forecast["horizon_selection_rationale"],
                "expected_annualized_return": str(expected_cagr),
            },
            "current_price_cny": str(price),
            "base_upside_vs_price": str(base / price - Decimal("1")),
            "expected_value_upside_vs_price": str(expected_value / price - Decimal("1")),
            "engine_output": intrinsic,
        },
        "p4f_market_implied_expectation": {
            "status": "BLOCKED",
            "resolution_state": p4f["snapshot"]["mie_set"]["resolution_state"],
            "qualification": p4f["snapshot"]["mie_set"]["qualification"],
            "snapshot_hash": p4f["snapshot"]["snapshot_hash"],
            "reason": (
                "P4-F requires PIT market-model candidate coverage and sufficient historical "
                "market valuation observations; current price alone cannot support a market-implied requirement."
            ),
            "replay": p4f["replay"],
        },
        "expectation_gap": {
            "status": "BLOCKED",
            "reason": "MIE is BLOCKED, so no semantic Expectation Gap may be calculated.",
            "not_substituted_by_intrinsic_upside": True,
        },
        "b1_decision_constraint": {
            "not_a_decision": True,
            "expected_annualized_return_reference": str(expected_cagr),
            "fundamental_15pct_reference_pass": expected_cagr >= Decimal("0.15"),
        },
    }
    audit = {
        "input_sha256": _sha({
            "core02": core02,
            "forecast": normalized_forecast,
            "valuation_assumptions": valuation_assumptions,
            "market_evidence": market_evidence,
            "price_evidence": price_evidence,
            "forecast_evidence": forecast_evidence,
        }),
        "generated_at": "2026-10-04T22:00:00+00:00",
        "price_evidence": price_evidence,
    }
    result = {**core_without_audit, "audit": audit}
    result["audit"]["core_sha256"] = _sha(core_without_audit)
    return result


def validate_core03_package(package: Any) -> list[str]:
    if not isinstance(package, dict):
        return ["CORE03_TYPE:must be an object"]
    errors = []
    for field in (
        "schema_version", "case_id", "symbol", "as_of_date", "cutoff_date",
        "status", "research_question", "core02_status", "independent_forecast",
        "company_valuation", "p4f_market_implied_expectation", "expectation_gap",
        "b1_decision_constraint", "audit",
    ):
        if field not in package:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors
    if package["schema_version"] != CORE03_VERSION:
        errors.append("CORE03_VERSION_INVALID")
    if package["case_id"] != "RC-CN-A-300750-20261004" or package["symbol"] != "300750":
        errors.append("CASE_BINDING_INVALID")
    if package["status"] not in {"PASS", "CONDITIONAL", "BLOCKED"}:
        errors.append("STATUS_INVALID")
    if package["p4f_market_implied_expectation"].get("status") != "BLOCKED":
        errors.append("P4F_BASELINE_STATUS_MUST_BE_BLOCKED")
    if package["expectation_gap"].get("status") != "BLOCKED":
        errors.append("EXPECTATION_GAP_MUST_BE_BLOCKED_WHEN_MIE_BLOCKED")
    audit = package.get("audit") or {}
    if audit.get("core_sha256") != _sha({k: v for k, v in package.items() if k != "audit"}):
        errors.append("CORE03_HASH_MISMATCH")
    return errors


__all__ = ["CORE03_VERSION", "FORECAST_VERSION", "build_core03_package", "validate_core03_package"]
