from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping

ECONOMIC_BRIDGE_VERSION = "IIOS-COMPANY-ECONOMIC-BRIDGE-0.1"

REQUIRED_PERIOD_FIELDS = (
    "period_id",
    "period_start",
    "period_end",
    "evidence_ids",
    "revenue",
    "operating_profit",
    "profit_before_tax",
    "income_tax",
    "net_income",
    "attributable_net_income",
    "operating_cash_flow",
    "capex_cash",
    "depreciation_ppe",
    "depreciation_rou",
    "amortization_intangible",
    "ar",
    "ar_financing",
    "prepayments",
    "inventory",
    "contract_assets",
    "notes_payable",
    "accounts_payable",
    "contract_liabilities",
    "employee_benefits_payable",
    "tax_payable",
    "other_payables",
    "fixed_assets",
    "construction_in_progress",
    "rou_assets",
    "intangible_assets",
    "wc_cash_inventory",
    "wc_cash_receivables",
    "wc_cash_payables",
)

EVIDENCE_ID_REQUIRED_FIELDS = ("evidence_ids",)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def _nonnegative(value: Any, field: str) -> float:
    result = _number(value, field)
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _refs(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    result = [str(item).strip() for item in value]
    if any(not item for item in result):
        raise ValueError(f"{field} cannot contain empty evidence IDs")
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate evidence IDs")
    return result


def _parse_date(value: Any, field: str) -> date:
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(f"{field} must start with an ISO date") from exc


def _period_core(period: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_PERIOD_FIELDS if field not in period]
    if missing:
        raise ValueError(f"period missing required fields: {missing}")

    if not str(period["period_id"]).strip():
        raise ValueError("period_id must be non-empty")
    if not str(period["period_start"]).strip() or not str(period["period_end"]).strip():
        raise ValueError("period_start and period_end must be non-empty")

    refs = _refs(period["evidence_ids"], "period.evidence_ids")
    start = _parse_date(period["period_start"], "period.period_start")
    end = _parse_date(period["period_end"], "period.period_end")
    if end < start:
        raise ValueError("period_end cannot precede period_start")
    for field in REQUIRED_PERIOD_FIELDS:
        if field in {"period_id", "period_start", "period_end", "evidence_ids", "wc_cash_inventory",
                     "wc_cash_receivables", "wc_cash_payables"}:
            continue
        _nonnegative(period[field], f"period.{field}")

    for field in ("wc_cash_inventory", "wc_cash_receivables", "wc_cash_payables"):
        _number(period[field], f"period.{field}")

    if _number(period["profit_before_tax"], "period.profit_before_tax") == 0:
        raise ValueError("period.profit_before_tax cannot be zero")

    if _number(period["net_income"], "period.net_income") == 0:
        raise ValueError("period.net_income cannot be zero")

    if _number(period["attributable_net_income"], "period.attributable_net_income") == 0:
        raise ValueError("period.attributable_net_income cannot be zero")

    return {
        **dict(period),
        "evidence_ids": refs,
    }


def _operating_nwc(period: Mapping[str, Any]) -> dict[str, float]:
    operating_current_assets = (
        period["ar"]
        + period["ar_financing"]
        + period["prepayments"]
        + period["inventory"]
        + period["contract_assets"]
    )
    operating_current_liabilities = (
        period["notes_payable"]
        + period["accounts_payable"]
        + period["contract_liabilities"]
        + period["employee_benefits_payable"]
        + period["tax_payable"]
        + period["other_payables"]
    )
    return {
        "operating_current_assets": operating_current_assets,
        "operating_current_liabilities": operating_current_liabilities,
        "core_operating_nwc": operating_current_assets - operating_current_liabilities,
    }


def _invested_capital_proxy(period: Mapping[str, Any]) -> float:
    nwc = _operating_nwc(period)["core_operating_nwc"]
    return (
        nwc
        + period["fixed_assets"]
        + period["construction_in_progress"]
        + period["rou_assets"]
        + period["intangible_assets"]
    )


def _period_metrics(period: Mapping[str, Any]) -> dict[str, Any]:
    p = _period_core(period)
    tax_rate = p["income_tax"] / p["profit_before_tax"]
    nopat_proxy = p["operating_profit"] * (1.0 - tax_rate)
    core_da = p["depreciation_ppe"] + p["depreciation_rou"] + p["amortization_intangible"]
    fcf_after_capex = p["operating_cash_flow"] - p["capex_cash"]
    wc_cash_contribution = (
        p["wc_cash_inventory"]
        + p["wc_cash_receivables"]
        + p["wc_cash_payables"]
    )
    nwc = _operating_nwc(p)
    invested_capital = _invested_capital_proxy(p)

    return {
        "period_id": p["period_id"],
        "period_start": p["period_start"],
        "period_end": p["period_end"],
        "evidence_ids": p["evidence_ids"],
        "reported_revenue": p["revenue"],
        "reported_operating_profit": p["operating_profit"],
        "reported_profit_before_tax": p["profit_before_tax"],
        "reported_income_tax": p["income_tax"],
        "reported_net_income": p["net_income"],
        "reported_attributable_net_income": p["attributable_net_income"],
        "reported_operating_cash_flow": p["operating_cash_flow"],
        "capex_cash_paid": p["capex_cash"],
        "core_depreciation_amortization": core_da,
        "fcf_after_capex": fcf_after_capex,
        "ocf_to_net_income": p["operating_cash_flow"] / p["net_income"],
        "fcf_to_net_income": fcf_after_capex / p["net_income"],
        "ocf_to_attributable_net_income": p["operating_cash_flow"] / p["attributable_net_income"],
        "fcf_to_attributable_net_income": fcf_after_capex / p["attributable_net_income"],
        "effective_tax_rate": tax_rate,
        "nopat_proxy": nopat_proxy,
        "working_capital_cash_bridge": {
            "inventory": p["wc_cash_inventory"],
            "receivables": p["wc_cash_receivables"],
            "payables": p["wc_cash_payables"],
            "net_cash_contribution": wc_cash_contribution,
        },
        "operating_working_capital_snapshot": {
            **nwc,
        },
        "invested_capital_proxy": invested_capital,
    }


def build_company_economic_bridge(
    *,
    case_id: str,
    cutoff_date: str,
    prior_period: Mapping[str, Any],
    current_period: Mapping[str, Any],
    generation_basis: str,
    admitted_evidence_ids: list[str] | set[str],
) -> dict[str, Any]:
    if not str(case_id).strip():
        raise ValueError("case_id must be non-empty")
    if not str(cutoff_date).strip():
        raise ValueError("cutoff_date must be non-empty")
    if not str(generation_basis).strip():
        raise ValueError("generation_basis must be non-empty")

    admitted_refs = _refs(admitted_evidence_ids, "admitted_evidence_ids")
    admitted_set = set(admitted_refs)
    prior = _period_metrics(prior_period)
    current = _period_metrics(current_period)

    if prior["period_start"] == current["period_start"] and prior["period_end"] == current["period_end"]:
        raise ValueError("prior_period and current_period cannot have identical period bounds")

    cutoff_day = _parse_date(cutoff_date, "cutoff_date")
    for name, period in (("prior_period", prior), ("current_period", current)):
        if _parse_date(period["period_end"], f"{name}.period_end") > cutoff_day:
            raise ValueError(f"{name}.period_end exceeds cutoff")
        missing_evidence = sorted(set(period["evidence_ids"]) - admitted_set)
        if missing_evidence:
            raise ValueError(
                f"{name} references evidence IDs not admitted by the supplied evidence set: {missing_evidence}"
            )

    if _parse_date(prior["period_end"], "prior_period.period_end") >= _parse_date(
        current["period_end"], "current_period.period_end"
    ):
        raise ValueError("current_period must end after prior_period")

    delta_nopat = current["nopat_proxy"] - prior["nopat_proxy"]
    delta_invested_capital = current["invested_capital_proxy"] - prior["invested_capital_proxy"]

    if delta_invested_capital > 0:
        incremental_roic_proxy = delta_nopat / delta_invested_capital
        incremental_roic_status = "CONDITIONAL"
        incremental_roic_reason = (
            "Computed from comparable reported periods, but this is a proxy: "
            "NOPAT uses the period effective tax rate and invested capital excludes "
            "financial investments, goodwill, deferred tax balances and other non-operating items."
        )
    else:
        incremental_roic_proxy = None
        incremental_roic_status = "UNKNOWN"
        incremental_roic_reason = (
            "Incremental invested capital is not positive; a standard delta-NOPAT / "
            "delta-invested-capital interpretation is not permitted."
        )

    input_payload = {
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "prior_period": prior,
        "current_period": current,
        "generation_basis": generation_basis,
        "admitted_evidence_ids": admitted_refs,
    }

    core = {
        "schema_version": ECONOMIC_BRIDGE_VERSION,
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "generation_basis": generation_basis,
        "evidence_admission": {
            "status": "ADMITTED",
            "evidence_ids": admitted_refs,
            "sha256": _sha(admitted_refs),
        },
        "periods": {
            "prior": prior,
            "current": current,
        },
        "deltas": {
            "nopat_proxy": delta_nopat,
            "invested_capital_proxy": delta_invested_capital,
            "fcf_after_capex": current["fcf_after_capex"] - prior["fcf_after_capex"],
            "core_depreciation_amortization": (
                current["core_depreciation_amortization"]
                - prior["core_depreciation_amortization"]
            ),
            "working_capital_cash_contribution": (
                current["working_capital_cash_bridge"]["net_cash_contribution"]
                - prior["working_capital_cash_bridge"]["net_cash_contribution"]
            ),
        },
        "incremental_roic": {
            "value": incremental_roic_proxy,
            "status": incremental_roic_status,
            "basis": "delta_nopat_proxy / delta_invested_capital_proxy",
            "reason": incremental_roic_reason,
        },
        "interpretation_status": "CONDITIONAL",
        "investment_decision_effect": "NO_DIRECT_GATE_EFFECT",
        "audit": {
            "input_sha256": _sha(input_payload),
        },
    }
    core["audit"]["bridge_sha256"] = _sha(
        {key: value for key, value in core.items() if key != "audit"}
    )
    return core


def validate_company_economic_bridge(record: Any) -> list[str]:
    if not isinstance(record, Mapping):
        return ["ECONOMIC_BRIDGE_TYPE_INVALID"]

    errors: list[str] = []
    required = {
        "schema_version",
        "case_id",
        "cutoff_date",
        "generation_basis",
        "evidence_admission",
        "periods",
        "deltas",
        "incremental_roic",
        "interpretation_status",
        "investment_decision_effect",
        "audit",
    }
    if set(record) != required:
        errors.append("ECONOMIC_BRIDGE_FIELDS_INVALID")
        return errors

    if record["schema_version"] != ECONOMIC_BRIDGE_VERSION:
        errors.append("ECONOMIC_BRIDGE_VERSION_MISMATCH")
    if record["interpretation_status"] != "CONDITIONAL":
        errors.append("INTERPRETATION_STATUS_INVALID")
    if record["investment_decision_effect"] != "NO_DIRECT_GATE_EFFECT":
        errors.append("INVESTMENT_DECISION_EFFECT_INVALID")

    if isinstance(evidence_admission, Mapping):
        evidence_ids = evidence_admission.get("evidence_ids")
        if (
            not isinstance(evidence_ids, list)
            or any(not isinstance(x, str) or not x.strip() for x in evidence_ids)
            or len(evidence_ids) != len(set(evidence_ids))
        ):
            errors.append("EVIDENCE_ADMISSION_IDS_INVALID")
        else:
            expected_evidence_hash = _sha(evidence_ids)
            if evidence_admission.get("sha256") != expected_evidence_hash:
                errors.append("EVIDENCE_ADMISSION_HASH_MISMATCH")

    evidence_admission = record["evidence_admission"]
    if (
        not isinstance(evidence_admission, Mapping)
        or set(evidence_admission) != {"status", "evidence_ids", "sha256"}
        or evidence_admission.get("status") != "ADMITTED"
    ):
        errors.append("EVIDENCE_ADMISSION_INVALID")

    periods = record["periods"]
    if not isinstance(periods, Mapping) or set(periods) != {"prior", "current"}:
        errors.append("PERIODS_INVALID")
    else:
        for name in ("prior", "current"):
            period = periods[name]
            try:
                _period_core(period)
            except ValueError as exc:
                errors.append(f"{name.upper()}:{exc}")

    incremental = record["incremental_roic"]
    if not isinstance(incremental, Mapping):
        errors.append("INCREMENTAL_ROIC_INVALID")
    else:
        required_incremental = {"value", "status", "basis", "reason"}
        if set(incremental) != required_incremental:
            errors.append("INCREMENTAL_ROIC_FIELDS_INVALID")
        if incremental.get("status") not in {"CONDITIONAL", "UNKNOWN"}:
            errors.append("INCREMENTAL_ROIC_STATUS_INVALID")
        if incremental.get("status") == "UNKNOWN" and incremental.get("value") is not None:
            errors.append("INCREMENTAL_ROIC_UNKNOWN_VALUE_MUST_BE_NULL")

    audit = record["audit"]
    if not isinstance(audit, Mapping) or set(audit) != {"input_sha256", "bridge_sha256"}:
        errors.append("AUDIT_FIELDS_INVALID")
    else:
        for field in ("input_sha256", "bridge_sha256"):
            value = audit.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                errors.append(f"AUDIT_{field.upper()}_INVALID")

        if not errors:
            recomputed_bridge_hash = _sha({key: value for key, value in record.items() if key != "audit"})
            if audit["bridge_sha256"] != recomputed_bridge_hash:
                errors.append("AUDIT_BRIDGE_HASH_MISMATCH")

    if not errors and isinstance(record["periods"], Mapping):
        expected_input = {
            "case_id": record["case_id"],
            "cutoff_date": record["cutoff_date"],
            "prior_period": record["periods"]["prior"],
            "current_period": record["periods"]["current"],
            "generation_basis": record["generation_basis"],
            "admitted_evidence_ids": record["evidence_admission"]["evidence_ids"],
        }
        if record["audit"]["input_sha256"] != _sha(expected_input):
            errors.append("AUDIT_INPUT_HASH_MISMATCH")

    return errors


__all__ = [
    "ECONOMIC_BRIDGE_VERSION",
    "build_company_economic_bridge",
    "validate_company_economic_bridge",
]
