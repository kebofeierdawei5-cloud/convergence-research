from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .quality_gate_v03 import build_quality_gate, validate_quality_gate

COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION = "IIOS-COMPANY-EVIDENCE-QUALITY-INTEGRATION-0.1"

QUALITY_DIMENSIONS = (
    "competitive_advantage",
    "incremental_return_on_capital",
    "earnings_quality",
    "cash_flow_conversion",
    "balance_sheet_resilience",
    "reinvestment_runway",
)

TRUST_DIMENSIONS = (
    "identity",
    "disclosure_integrity",
    "governance_integrity",
    "shareholder_treatment",
)

STATUS_SEVERITY = {
    "PASS": 0,
    "CONDITIONAL": 1,
    "UNKNOWN": 2,
    "BLOCKED": 3,
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _status(value: Any, field: str) -> str:
    result = str(value).strip().upper()
    if result not in STATUS_SEVERITY:
        raise ValueError(f"{field} has unsupported status: {result}")
    return result


def _integrate_status(base_status: str, evidence_status: str) -> str:
    """Resolve evidence-missing UNKNOWN, otherwise apply fail-closed cap.

    UNKNOWN may be resolved only because the mapped A1 company evidence slice
    exists. Known PASS / CONDITIONAL analytical states cannot be upgraded by
    this integration layer.
    """
    base = _status(base_status, "base_status")
    evidence = _status(evidence_status, "evidence_status")

    if base == "UNKNOWN" and evidence in {"PASS", "CONDITIONAL"}:
        return evidence
    return max((base, evidence), key=lambda value: STATUS_SEVERITY[value])


def _refs(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    refs = [str(item).strip() for item in value]
    if any(not item for item in refs):
        raise ValueError(f"{field} contains an empty evidence ID")
    if len(refs) != len(set(refs)):
        raise ValueError(f"{field} contains duplicate evidence IDs")
    return refs


def _validate_bridge(
    bridge: Mapping[str, Any],
    *,
    version: str,
    case_id: str,
    cutoff_date: str,
    field: str,
) -> None:
    if not isinstance(bridge, Mapping):
        raise ValueError(f"{field} must be an object")
    if bridge.get("schema_version") != version:
        raise ValueError(f"{field}.schema_version mismatch")
    if bridge.get("case_id") != case_id:
        raise ValueError(f"{field}.case_id mismatch")
    if str(bridge.get("cutoff_date")) != str(cutoff_date):
        raise ValueError(f"{field}.cutoff_date mismatch")


def _normalize_quality(quality: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(quality, Mapping):
        raise ValueError("quality must be an object")
    rows = quality.get("dimensions")
    if not isinstance(rows, list) or len(rows) != len(QUALITY_DIMENSIONS):
        raise ValueError("quality dimensions cardinality mismatch")

    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("quality dimension must be an object")
        name = str(row.get("dimension", "")).strip()
        if name in by_name:
            raise ValueError(f"quality dimension duplicated: {name}")
        if name not in QUALITY_DIMENSIONS:
            raise ValueError(f"unsupported quality dimension: {name}")
        rationale = str(row.get("rationale", "")).strip()
        if not rationale:
            raise ValueError(f"quality.{name}.rationale is required")
        by_name[name] = {
            "dimension": name,
            "status": _status(row.get("status"), f"quality.{name}.status"),
            "rationale": rationale,
            "evidence_ids": _refs(row.get("evidence_ids"), f"quality.{name}.evidence_ids"),
        }

    missing = [name for name in QUALITY_DIMENSIONS if name not in by_name]
    if missing:
        raise ValueError(f"quality dimensions missing: {missing}")
    return {"dimensions": [by_name[name] for name in QUALITY_DIMENSIONS]}


def _normalize_trust(trust: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(trust, Mapping):
        raise ValueError("trust must be an object")
    rows = trust.get("dimensions")
    if not isinstance(rows, list) or len(rows) != len(TRUST_DIMENSIONS):
        raise ValueError("trust dimensions cardinality mismatch")

    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("trust dimension must be an object")
        name = str(row.get("dimension", "")).strip()
        if name in by_name:
            raise ValueError(f"trust dimension duplicated: {name}")
        if name not in TRUST_DIMENSIONS:
            raise ValueError(f"unsupported trust dimension: {name}")
        rationale = str(row.get("rationale", "")).strip()
        if not rationale:
            raise ValueError(f"trust.{name}.rationale is required")
        by_name[name] = {
            "dimension": name,
            "status": _status(row.get("status"), f"trust.{name}.status"),
            "rationale": rationale,
            "evidence_ids": _refs(row.get("evidence_ids"), f"trust.{name}.evidence_ids"),
        }

    missing = [name for name in TRUST_DIMENSIONS if name not in by_name]
    if missing:
        raise ValueError(f"trust dimensions missing: {missing}")
    return {"dimensions": [by_name[name] for name in TRUST_DIMENSIONS]}


def _add_bridge_evidence(row: dict[str, Any], bridge_refs: list[str], suffix: str) -> dict[str, Any]:
    refs = list(dict.fromkeys(row["evidence_ids"] + bridge_refs))
    row["evidence_ids"] = refs
    row["rationale"] = f"{row['rationale']} [{suffix}]"
    return row


def integrate_company_evidence_into_quality(
    *,
    case_id: str,
    cutoff_date: str,
    quality: Mapping[str, Any],
    trust: Mapping[str, Any],
    economic_bridge: Mapping[str, Any],
    capital_trust_bridge: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_bridge(
        economic_bridge,
        version="IIOS-COMPANY-ECONOMIC-BRIDGE-0.1",
        case_id=case_id,
        cutoff_date=cutoff_date,
        field="economic_bridge",
    )
    _validate_bridge(
        capital_trust_bridge,
        version="IIOS-COMPANY-CAPITAL-TRUST-BRIDGE-0.1",
        case_id=case_id,
        cutoff_date=cutoff_date,
        field="capital_trust_bridge",
    )

    normalized_quality = _normalize_quality(quality)
    normalized_trust = _normalize_trust(trust)

    eco_refs = _refs(
        list(dict.fromkeys(
            economic_bridge["periods"]["current"]["evidence_ids"]
            + economic_bridge["periods"]["prior"]["evidence_ids"]
        )),
        "economic_bridge evidence IDs",
    )
    cap_refs = _refs(
        capital_trust_bridge["evidence_admission"]["evidence_ids"],
        "capital_trust_bridge evidence IDs",
    )

    evidence_roic_status = _status(
        economic_bridge["incremental_roic"]["status"],
        "economic_bridge.incremental_roic.status",
    )
    evidence_cash_status = _status(
        economic_bridge["interpretation_status"],
        "economic_bridge.interpretation_status",
    )
    evidence_reinvestment_status = _status(
        capital_trust_bridge["capital_allocation"]["status"],
        "capital_trust_bridge.capital_allocation.status",
    )
    evidence_governance_status = _status(
        capital_trust_bridge["trust_revalidation"]["governance_integrity"]["status"],
        "capital_trust_bridge.trust_revalidation.governance_integrity.status",
    )
    evidence_shareholder_status = _status(
        capital_trust_bridge["trust_revalidation"]["shareholder_treatment"]["status"],
        "capital_trust_bridge.trust_revalidation.shareholder_treatment.status",
    )
    evidence_trust_status = _status(
        capital_trust_bridge["trust_revalidation"]["status"],
        "capital_trust_bridge.trust_revalidation.status",
    )

    quality_rows = {row["dimension"]: dict(row) for row in normalized_quality["dimensions"]}
    quality_rows["incremental_return_on_capital"] = _add_bridge_evidence(
        {
            **quality_rows["incremental_return_on_capital"],
            "status": _integrate_status(
                quality_rows["incremental_return_on_capital"]["status"],
                evidence_roic_status,
            ),
        },
        eco_refs,
        "A1-01 economic evidence cap",
    )
    quality_rows["cash_flow_conversion"] = _add_bridge_evidence(
        {
            **quality_rows["cash_flow_conversion"],
            "status": _integrate_status(
                quality_rows["cash_flow_conversion"]["status"],
                evidence_cash_status,
            ),
        },
        eco_refs,
        "A1-01 cash-conversion evidence cap",
    )
    quality_rows["reinvestment_runway"] = _add_bridge_evidence(
        {
            **quality_rows["reinvestment_runway"],
            "status": _integrate_status(
                quality_rows["reinvestment_runway"]["status"],
                evidence_reinvestment_status,
            ),
        },
        cap_refs,
        "A1-02 capital-allocation evidence cap",
    )
    integrated_quality = {
        "dimensions": [quality_rows[name] for name in QUALITY_DIMENSIONS]
    }
    quality_gate = build_quality_gate(
        integrated_quality,
        case_id=case_id,
        cutoff_date=cutoff_date,
    )
    validate_quality_gate(
        quality_gate,
        case_id=case_id,
        cutoff_date=cutoff_date,
    )

    trust_rows = {row["dimension"]: dict(row) for row in normalized_trust["dimensions"]}
    trust_rows["governance_integrity"] = _add_bridge_evidence(
        {
            **trust_rows["governance_integrity"],
            "status": _integrate_status(
                trust_rows["governance_integrity"]["status"],
                evidence_governance_status,
            ),
        },
        cap_refs,
        "A1-02 governance evidence cap",
    )
    trust_rows["shareholder_treatment"] = _add_bridge_evidence(
        {
            **trust_rows["shareholder_treatment"],
            "status": _integrate_status(
                trust_rows["shareholder_treatment"]["status"],
                evidence_shareholder_status,
            ),
        },
        cap_refs,
        "A1-02 shareholder-treatment evidence cap",
    )
    trust_dimensions = [trust_rows[name] for name in TRUST_DIMENSIONS]
    trust_status = (
        "BLOCKED"
        if any(row["status"] == "BLOCKED" for row in trust_dimensions)
        else "CONDITIONAL"
        if any(row["status"] in {"CONDITIONAL", "UNKNOWN"} for row in trust_dimensions)
        else "PASS"
    )
    trust_status = _integrate_status(trust_status, evidence_trust_status)

    input_core = {
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "quality": normalized_quality,
        "trust": normalized_trust,
        "economic_bridge": economic_bridge,
        "capital_trust_bridge": capital_trust_bridge,
    }
    core = {
        "schema_version": COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION,
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "economic_bridge_status": {
            "incremental_roic": evidence_roic_status,
            "interpretation": evidence_cash_status,
        },
        "capital_trust_bridge_status": {
            "capital_allocation": evidence_reinvestment_status,
            "governance_integrity": evidence_governance_status,
            "shareholder_treatment": evidence_shareholder_status,
            "trust_revalidation": evidence_trust_status,
        },
        "quality": integrated_quality,
        "quality_gate": quality_gate,
        "trust": {
            "status": trust_status,
            "dimensions": trust_dimensions,
        },
        "decision_effect": "NO_DIRECT_GATE_EFFECT",
        "audit": {
            "input_sha256": _sha(input_core),
        },
    }
    core["audit"]["integration_sha256"] = _sha(
        {key: value for key, value in core.items() if key != "audit"}
    )
    return core


def validate_company_evidence_quality_integration(
    record: Any,
    *,
    case_id: str,
    cutoff_date: str,
) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("company_evidence_quality_integration must be an object")
    required = {
        "schema_version",
        "case_id",
        "cutoff_date",
        "economic_bridge_status",
        "capital_trust_bridge_status",
        "quality",
        "quality_gate",
        "trust",
        "decision_effect",
        "audit",
    }
    if set(record) != required:
        raise ValueError("company_evidence_quality_integration fields are invalid")
    if record["schema_version"] != COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION:
        raise ValueError("company evidence integration version mismatch")
    if record["case_id"] != case_id:
        raise ValueError("company evidence integration case_id mismatch")
    if record["cutoff_date"] != cutoff_date:
        raise ValueError("company evidence integration cutoff mismatch")
    if record["decision_effect"] != "NO_DIRECT_GATE_EFFECT":
        raise ValueError("company evidence integration decision effect invalid")

    validate_quality_gate(
        record["quality_gate"],
        case_id=case_id,
        cutoff_date=cutoff_date,
    )

    audit = record["audit"]
    if not isinstance(audit, Mapping) or set(audit) != {"input_sha256", "integration_sha256"}:
        raise ValueError("company evidence integration audit invalid")
    for field in ("input_sha256", "integration_sha256"):
        value = audit.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError(f"company evidence integration audit {field} invalid")

    expected_integration_hash = _sha(
        {key: value for key, value in record.items() if key != "audit"}
    )
    if audit["integration_sha256"] != expected_integration_hash:
        raise ValueError("company evidence integration hash mismatch")

    if record["quality_gate"]["dimensions"] != record["quality"]["dimensions"]:
        raise ValueError("company evidence quality/quality-gate drift")

    trust = record["trust"]
    if not isinstance(trust, Mapping) or not isinstance(trust.get("dimensions"), list):
        raise ValueError("company evidence integration trust invalid")
    if len(trust["dimensions"]) != len(TRUST_DIMENSIONS):
        raise ValueError("company evidence integration trust cardinality invalid")

    if record["economic_bridge_status"]["incremental_roic"] not in STATUS_SEVERITY:
        raise ValueError("economic bridge incremental_roic status invalid")
    if record["economic_bridge_status"]["interpretation"] not in STATUS_SEVERITY:
        raise ValueError("economic bridge interpretation status invalid")

    for field in (
        "capital_allocation",
        "governance_integrity",
        "shareholder_treatment",
        "trust_revalidation",
    ):
        if record["capital_trust_bridge_status"][field] not in STATUS_SEVERITY:
            raise ValueError(f"capital trust bridge {field} status invalid")





__all__ = [
    "COMPANY_EVIDENCE_QUALITY_INTEGRATION_VERSION",
    "integrate_company_evidence_into_quality",
    "validate_company_evidence_quality_integration",
]
