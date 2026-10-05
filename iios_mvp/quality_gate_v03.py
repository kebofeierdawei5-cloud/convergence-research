from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping

QUALITY_GATE_VERSION = "IIOS-CORE-04-QUALITY-GATE-0.1"
QUALITY_GATE_POLICY_VERSION = "IIOS-QUALITY-GATE-POLICY-0.1"
QUALITY_GATE_POLICY = "ALL_CORE_DIMENSIONS_PASS_FOR_NEW_CAPITAL"
QUALITY_DIMENSIONS = (
    "competitive_advantage",
    "incremental_return_on_capital",
    "earnings_quality",
    "cash_flow_conversion",
    "balance_sheet_resilience",
    "reinvestment_runway",
)
QUALITY_STATES = {"PASS", "CONDITIONAL", "UNKNOWN", "BLOCKED"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _date(value: Any) -> date:
    return date.fromisoformat(str(value))


def build_quality_gate(
    quality: Mapping[str, Any],
    *,
    case_id: str,
    cutoff_date: str,
) -> dict[str, Any]:
    if not isinstance(quality, Mapping):
        raise ValueError("quality must be an object")
    rows = quality.get("dimensions")
    if not isinstance(rows, list) or len(rows) != len(QUALITY_DIMENSIONS):
        raise ValueError(
            f"quality.dimensions must contain exactly {len(QUALITY_DIMENSIONS)} rows"
        )
    cutoff = _date(cutoff_date)
    by_name: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"quality.dimensions[{index}] must be an object")
        required = {"dimension", "status", "rationale", "evidence_ids"}
        if set(row) < required:
            missing = sorted(required - set(row))
            raise ValueError(
                f"quality.dimensions[{index}] missing required fields: {missing}"
            )
        dimension = str(row["dimension"]).strip()
        status = str(row["status"]).strip().upper()
        if dimension in by_name:
            raise ValueError(f"quality dimension duplicated: {dimension}")
        if dimension not in QUALITY_DIMENSIONS:
            raise ValueError(f"unsupported quality dimension: {dimension}")
        if status not in QUALITY_STATES:
            raise ValueError(f"unsupported quality status: {status}")
        rationale = str(row["rationale"]).strip()
        refs = row["evidence_ids"]
        if not rationale:
            raise ValueError(f"quality.{dimension}.rationale is required")
        if not isinstance(refs, list) or not refs or any(not str(x).strip() for x in refs):
            raise ValueError(f"quality.{dimension}.evidence_ids must be non-empty")
        by_name[dimension] = {
            "dimension": dimension,
            "status": status,
            "rationale": rationale,
            "evidence_ids": [str(x).strip() for x in refs],
        }

    missing = [d for d in QUALITY_DIMENSIONS if d not in by_name]
    if missing:
        raise ValueError(f"quality dimensions missing: {missing}")

    dimensions = [by_name[d] for d in QUALITY_DIMENSIONS]
    gate_status = (
        "BLOCKED"
        if any(x["status"] == "BLOCKED" for x in dimensions)
        else "CONDITIONAL"
        if any(x["status"] in {"CONDITIONAL", "UNKNOWN"} for x in dimensions)
        else "PASS"
    )
    qualifying = gate_status == "PASS"

    core = {
        "schema_version": QUALITY_GATE_VERSION,
        "policy_version": QUALITY_GATE_POLICY_VERSION,
        "policy": QUALITY_GATE_POLICY,
        "case_id": str(case_id),
        "cutoff_date": cutoff.isoformat(),
        "status": gate_status,
        "capital_admission_pass": qualifying,
        "dimensions": dimensions,
        "blocking_dimensions": [
            x["dimension"] for x in dimensions if x["status"] != "PASS"
        ],
    }
    record_hash = _sha(core)
    return {
        **core,
        "quality_gate_id": f"{case_id}:QG:{record_hash[:16]}",
        "admission_record_hash": record_hash,
    }


def validate_quality_gate(record: Any, *, case_id: str, cutoff_date: str) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("quality_gate must be an object")
    required = {
        "schema_version",
        "policy_version",
        "policy",
        "case_id",
        "cutoff_date",
        "status",
        "capital_admission_pass",
        "dimensions",
        "blocking_dimensions",
        "quality_gate_id",
        "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("quality_gate fields are invalid")
    if record["schema_version"] != QUALITY_GATE_VERSION:
        raise ValueError("quality_gate schema version mismatch")
    if record["policy_version"] != QUALITY_GATE_POLICY_VERSION:
        raise ValueError("quality_gate policy version mismatch")
    if record["policy"] != QUALITY_GATE_POLICY:
        raise ValueError("quality_gate policy mismatch")
    if record["case_id"] != case_id:
        raise ValueError("quality_gate case_id mismatch")
    if record["cutoff_date"] != _date(cutoff_date).isoformat():
        raise ValueError("quality_gate cutoff_date mismatch")
    if record["status"] not in QUALITY_STATES:
        raise ValueError("quality_gate status invalid")
    expected_pass = record["status"] == "PASS"
    if record["capital_admission_pass"] is not expected_pass:
        raise ValueError("quality_gate capital_admission_pass mismatch")
    dimensions = record["dimensions"]
    if not isinstance(dimensions, list) or len(dimensions) != len(QUALITY_DIMENSIONS):
        raise ValueError("quality_gate dimensions cardinality mismatch")
    core = {k: record[k] for k in required if k not in {"quality_gate_id", "admission_record_hash"}}
    expected_hash = _sha(core)
    if record["admission_record_hash"] != expected_hash:
        raise ValueError("quality_gate admission hash mismatch")
    if record["quality_gate_id"] != f"{case_id}:QG:{expected_hash[:16]}":
        raise ValueError("quality_gate_id mismatch")


__all__ = [
    "QUALITY_DIMENSIONS",
    "QUALITY_GATE_POLICY",
    "QUALITY_GATE_POLICY_VERSION",
    "QUALITY_GATE_VERSION",
    "build_quality_gate",
    "validate_quality_gate",
]
