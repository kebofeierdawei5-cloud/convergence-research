from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "driver_series.schema.json"


class DriverSeriesError(ValueError):
    pass


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _quarter_key(period: str) -> tuple[int, int]:
    try:
        return int(period[:4]), int(period[-1])
    except Exception as exc:
        raise DriverSeriesError(f"invalid quarter period: {period!r}") from exc


def validate_record(record: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record), key=lambda e: list(e.path))
    findings = [f"SCHEMA: {'.'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors]
    if findings:
        return findings

    try:
        known_at = _parse_dt(record["known_at"])
        published_at = _parse_dt(record["published_at"])
    except Exception as exc:
        return [f"TIME: invalid datetime: {exc}"]

    if known_at < published_at:
        findings.append("PIT-001: known_at must not precede published_at")

    status = record["status"]
    provenance = record["provenance"]
    transform = record["transformation_type"]
    inputs = record.get("input_record_ids", [])
    formula = record.get("formula")
    value = record["value"]

    if provenance == "DIRECT_PERIODIC_FILING":
        if transform != "NONE":
            findings.append("PROV-001: direct filing must use transformation_type=NONE")
        if inputs:
            findings.append("PROV-002: direct filing cannot declare input_record_ids")
        if formula is not None:
            findings.append("PROV-003: direct filing cannot declare a derivation formula")
        if record["quality_status"] not in {"VERIFIED", "CONFLICT", "UNKNOWN"}:
            findings.append("PROV-004: direct filing quality_status invalid")
    else:
        expected = {
            "DERIVED_H1_MINUS_Q1": "H1_MINUS_Q1",
            "DERIVED_ANNUAL_MINUS_Q1_Q2_Q3": "ANNUAL_MINUS_Q1_Q2_Q3",
            "OTHER_DERIVED": "OTHER_DETERMINISTIC",
        }[provenance]
        if transform != expected:
            findings.append(f"PROV-005: provenance {provenance} requires transformation_type={expected}")
        if not inputs:
            findings.append("PROV-006: derived record must declare input_record_ids")
        if not formula:
            findings.append("PROV-007: derived record must declare formula")
        if record["quality_status"] not in {"DERIVED_VERIFIED", "CONFLICT", "UNKNOWN"}:
            findings.append("PROV-008: derived quality_status invalid")

    if status in {"VALID", "INVALID"} and value is None:
        findings.append("DATA-001: VALID/INVALID record must retain an explicit numeric value")
    if status == "UNKNOWN" and value is not None:
        findings.append("DATA-002: UNKNOWN record must use value=null")

    if status == "INVALID" and record["quality_status"] == "VERIFIED":
        findings.append("DATA-003: INVALID record cannot claim VERIFIED quality")

    # Security / identity is part of the historical series key and must not be inferred.
    if not record.get("security_id") or not record.get("driver_id"):
        findings.append("ID-001: security_id and driver_id are mandatory")

    return findings


def validate_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(records)
    findings: list[dict[str, Any]] = []
    for record in rows:
        for message in validate_record(record):
            findings.append({"record_id": record.get("record_id"), "code": message.split(":", 1)[0], "message": message})

    # Exact duplicate revision snapshot with divergent values is a conflict, not a silent overwrite.
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for record in rows:
        key = (
            record.get("security_id", ""), record.get("driver_id", ""), record.get("period", ""),
            record.get("revision", {}).get("revision_id", ""), record.get("known_at", "")
        )
        groups.setdefault(key, []).append(record)
    for key, group in groups.items():
        values = {r.get("value") for r in group if r.get("status") == "VALID"}
        if len(values) > 1:
            findings.append({
                "record_id": ",".join(str(r.get("record_id")) for r in group),
                "code": "PIT-002",
                "message": "conflicting values share the same security/driver/period/revision/known_at snapshot"
            })

    return findings



def _require_parent(records_by_id: dict[str, dict[str, Any]], record_id: str) -> dict[str, Any]:
    parent = records_by_id.get(record_id)
    if parent is None:
        raise DriverSeriesError(f"PROV-009 missing parent record: {record_id}")
    if parent.get("status") != "VALID":
        raise DriverSeriesError(f"PROV-010 parent record is not VALID: {record_id}")
    return parent


def derive_h1_minus_q1(*, h1: dict[str, Any], q1: dict[str, Any], target_period: str, record_id: str, source_ref: str, known_at: str, published_at: str) -> dict[str, Any]:
    """Create one deterministic Q2 observation from H1 and Q1 parents.

    The caller must supply the exact source observations; this function performs only
    the declared arithmetic transformation and preserves parent lineage.
    """
    if h1.get("value") is None or q1.get("value") is None:
        raise DriverSeriesError("PROV-011 cannot derive from null parent value")
    if h1.get("security_id") != q1.get("security_id") or h1.get("driver_id") != q1.get("driver_id"):
        raise DriverSeriesError("PROV-012 parent identity mismatch")
    value = h1["value"] - q1["value"]
    return {
        "schema_version": "IIOS-DRIVER-SERIES-0.1",
        "record_id": record_id,
        "security_id": h1["security_id"],
        "driver_id": h1["driver_id"],
        "period": target_period,
        "value": value,
        "unit": h1["unit"],
        "source_type": "COMPANY_DISCLOSURE",
        "source_ref": source_ref,
        "source_date": published_at[:10],
        "known_at": known_at,
        "published_at": published_at,
        "transformation_type": "H1_MINUS_Q1",
        "provenance": "DERIVED_H1_MINUS_Q1",
        "revision": {"revision_id": f"{target_period}-DERIVED-R1", "sequence": 1},
        "supersedes_record_id": None,
        "input_record_ids": [h1["record_id"], q1["record_id"]],
        "formula": "H1_value - Q1_value",
        "status": "VALID",
        "quality_status": "DERIVED_VERIFIED",
    }


def derive_annual_minus_q1_q2_q3(*, annual: dict[str, Any], q1: dict[str, Any], q2: dict[str, Any], q3: dict[str, Any], target_period: str, record_id: str, source_ref: str, known_at: str, published_at: str) -> dict[str, Any]:
    """Create Q4 from annual cumulative value minus Q1/Q2/Q3.

    Parent identities must match. No fallback or imputation is performed.
    """
    parents = [annual, q1, q2, q3]
    first = parents[0]
    if any(p.get("value") is None for p in parents):
        raise DriverSeriesError("PROV-013 cannot derive from null parent value")
    if any((p.get("security_id"), p.get("driver_id"), p.get("unit")) != (first.get("security_id"), first.get("driver_id"), first.get("unit")) for p in parents[1:]):
        raise DriverSeriesError("PROV-014 parent identity/unit mismatch")
    value = annual["value"] - q1["value"] - q2["value"] - q3["value"]
    return {
        "schema_version": "IIOS-DRIVER-SERIES-0.1",
        "record_id": record_id,
        "security_id": first["security_id"],
        "driver_id": first["driver_id"],
        "period": target_period,
        "value": value,
        "unit": first["unit"],
        "source_type": "COMPANY_DISCLOSURE",
        "source_ref": source_ref,
        "source_date": published_at[:10],
        "known_at": known_at,
        "published_at": published_at,
        "transformation_type": "ANNUAL_MINUS_Q1_Q2_Q3",
        "provenance": "DERIVED_ANNUAL_MINUS_Q1_Q2_Q3",
        "revision": {"revision_id": f"{target_period}-DERIVED-R1", "sequence": 1},
        "supersedes_record_id": None,
        "input_record_ids": [annual["record_id"], q1["record_id"], q2["record_id"], q3["record_id"]],
        "formula": "Annual_value - Q1_value - Q2_value - Q3_value",
        "status": "VALID",
        "quality_status": "DERIVED_VERIFIED",
    }


def build_derived_records(records: Iterable[dict[str, Any]], recipes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute only explicit derivation recipes against exact parent IDs."""
    records_by_id = {r["record_id"]: r for r in records}
    output = []
    for recipe in recipes:
        kind = recipe.get("type")
        if kind == "H1_MINUS_Q1":
            h1 = _require_parent(records_by_id, recipe["h1_record_id"])
            q1 = _require_parent(records_by_id, recipe["q1_record_id"])
            derived = derive_h1_minus_q1(h1=h1, q1=q1, **{k: recipe[k] for k in ("target_period", "record_id", "source_ref", "known_at", "published_at")})
        elif kind == "ANNUAL_MINUS_Q1_Q2_Q3":
            annual = _require_parent(records_by_id, recipe["annual_record_id"])
            q1 = _require_parent(records_by_id, recipe["q1_record_id"])
            q2 = _require_parent(records_by_id, recipe["q2_record_id"])
            q3 = _require_parent(records_by_id, recipe["q3_record_id"])
            derived = derive_annual_minus_q1_q2_q3(annual=annual, q1=q1, q2=q2, q3=q3, **{k: recipe[k] for k in ("target_period", "record_id", "source_ref", "known_at", "published_at")})
        else:
            raise DriverSeriesError(f"PROV-015 unsupported derivation recipe: {kind!r}")
        findings = validate_record(derived)
        if findings:
            raise DriverSeriesError("derived record failed validation: " + "; ".join(findings))
        output.append(derived)
    return output

def resolve_at_cutoff(records: Iterable[dict[str, Any]], *, security_id: str, driver_id: str, period: str, cutoff: str) -> dict[str, Any] | None:
    cutoff_dt = _parse_dt(cutoff)
    candidates = []
    for record in records:
        if record.get("security_id") != security_id or record.get("driver_id") != driver_id or record.get("period") != period:
            continue
        if record.get("status") != "VALID":
            continue
        if _parse_dt(record["known_at"]) <= cutoff_dt:
            candidates.append(record)

    if not candidates:
        return None

    candidates.sort(key=lambda r: (_parse_dt(r["known_at"]), r["revision"]["sequence"], r["record_id"]))
    latest_known = _parse_dt(candidates[-1]["known_at"])
    same_known = [r for r in candidates if _parse_dt(r["known_at"]) == latest_known]
    values = {r["value"] for r in same_known}
    if len(values) > 1:
        raise DriverSeriesError(
            f"PIT-002 conflict at cutoff: {security_id}/{driver_id}/{period}; multiple values at known_at={latest_known.isoformat()}"
        )
    # Highest revision sequence wins only after same-known-time values are proven identical.
    same_known.sort(key=lambda r: (r["revision"]["sequence"], r["record_id"]))
    return same_known[-1]


def resolve_series(records: Iterable[dict[str, Any]], *, security_id: str, driver_id: str, periods: Iterable[str], cutoff: str) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    statuses: dict[str, str] = {}
    for period in sorted(periods, key=_quarter_key):
        record = resolve_at_cutoff(records, security_id=security_id, driver_id=driver_id, period=period, cutoff=cutoff)
        if record is None:
            statuses[period] = "UNKNOWN"
        else:
            resolved[period] = record
            statuses[period] = "VALID"
    return {"security_id": security_id, "driver_id": driver_id, "cutoff": cutoff, "records": resolved, "status_by_period": statuses}


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise DriverSeriesError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return rows
