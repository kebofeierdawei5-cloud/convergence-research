"""Durable, case-bound authorization for formal IIOS write operations.

This record is distinct from a completed IIOS_RUN_RECEIPT: it authorizes the
Decision Revision -> Machine Publication -> read-only report path only after
all upstream admission stages have passed. Missing or mismatched records fail
closed. Synthetic/test records prove control wiring, never source admission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_research_orchestrator import (
    REQUIRED_PREDECESSOR,
    ARTIFACT_GATED,
    SEMANTIC_PRODUCER_TYPES,
    RunStatus,
    Stage,
    canonical_hash,
    is_sha256,
)

AUTHORIZATION_SCHEMA = "IIOS-CANONICAL-RUN-AUTHORIZATION-0.1"
AUTHORIZED_STAGE_SEQUENCE = (
    "REQUEST_ADMITTED",
    "CASE_CREATED",
    "EVIDENCE_PENDING",
    "EVIDENCE_ADMITTED",
    "SEMANTIC_PENDING",
    "SEMANTIC_ADMITTED",
    "FORECAST_PENDING",
    "FORECAST_ADMITTED",
    "VALUATION_PENDING",
    "VALUATION_ADMITTED",
    "DECISION_PENDING",
    "DECISION_ADMITTED",
)
ADMISSION_PRODUCERS = {
    "EVIDENCE_ADMITTED": {"B2_EVIDENCE_PIT_VALIDATOR"},
    "SEMANTIC_ADMITTED": SEMANTIC_PRODUCER_TYPES,
    "FORECAST_ADMITTED": {"INDEPENDENT_FORECAST_ADMISSION"},
    "VALUATION_ADMITTED": {"VALUATION_ADMISSION"},
    "DECISION_ADMITTED": {"DECISION_ADMISSION_VALIDATOR"},
}


def _field(value: Any, name: str) -> str:
    result = str(value if value is not None else "").strip()
    if not result:
        raise ValueError(f"{name} is required")
    return result


def authorization_path(root: str | Path, run_id: str) -> Path:
    run_id = _field(run_id, "run_id")
    key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    return Path(root) / ".iios" / "canonical-run-authorizations" / f"{key}.json"


def _stage_record(receipt: Any) -> dict[str, Any]:
    if hasattr(receipt, "as_mapping"):
        result = receipt.as_mapping()
    elif isinstance(receipt, Mapping):
        result = dict(receipt)
    else:
        raise ValueError("stage receipt must be a StageReceipt or object")
    required = {
        "stage_id", "stage_version", "input_refs", "input_hashes",
        "output_refs", "output_hashes", "producer_type", "producer_version",
        "status", "cutoff_date", "created_at",
    }
    if set(result) != required:
        raise ValueError("stage receipt fields are invalid")
    for name in ("input_refs", "input_hashes", "output_refs", "output_hashes"):
        if not isinstance(result[name], (list, tuple)):
            raise ValueError(f"stage receipt {name} must be a list")
        result[name] = list(result[name])
    for h in result["input_hashes"] + result["output_hashes"]:
        if not is_sha256(h):
            raise ValueError("stage receipt contains an invalid SHA-256")
    if result["status"] != "PASS":
        raise ValueError(f"stage {result['stage_id']} did not pass")
    if result["stage_id"] in {s.value for s in ARTIFACT_GATED}:
        if not result["output_refs"] or not result["output_hashes"]:
            raise ValueError(f"stage {result['stage_id']} lacks admitted output bindings")
        if len(result["output_refs"]) != len(result["output_hashes"]):
            raise ValueError(f"stage {result['stage_id']} output refs/hashes do not align")
    expected_producers = ADMISSION_PRODUCERS.get(result["stage_id"])
    if expected_producers and result["producer_type"] not in expected_producers:
        raise ValueError(
            f"stage {result['stage_id']} producer is not authorized: {result['producer_type']}"
        )
    if result["cutoff_date"] == "":
        raise ValueError("stage receipt cutoff_date is required")
    return result


def _snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    required = {"snapshot_schema", "engine_version", "input", "decision", "snapshot_hash"}
    if not required.issubset(snapshot):
        raise ValueError("snapshot is missing required fields for canonical authorization")
    core = {key: snapshot[key] for key in ("snapshot_schema", "engine_version", "input", "decision")}
    expected = canonical_hash(core)
    if snapshot["snapshot_hash"] != expected:
        raise ValueError("snapshot hash mismatch")
    if snapshot["snapshot_schema"] != "IIOS-MVP-SNAPSHOT-0.3.0":
        raise ValueError("only IIOS v0.3 snapshots can receive canonical write authorization")
    return expected


def build_run_authorization(
    *,
    envelope: Any,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Create an authorization receipt only from a completed upstream admission chain."""
    if getattr(envelope, "run_status", None) != RunStatus.IN_PROGRESS:
        raise ValueError("canonical write authorization requires an active run")
    if getattr(envelope, "stage_state", None) != Stage.DECISION_ADMITTED:
        raise ValueError("canonical write authorization requires DECISION_ADMITTED")
    run_id = _field(getattr(envelope, "run_id", None), "run_id")
    case_id = _field(getattr(envelope, "case_id", None), "case_id")
    market = _field(getattr(envelope, "market", None), "market").upper()
    symbol = _field(getattr(envelope, "symbol", None), "symbol").upper()
    cutoff_date = _field(getattr(envelope, "cutoff_date", None), "cutoff_date")
    as_of_date = _field(getattr(envelope, "as_of_date", None), "as_of_date")
    research_case_hash = _field(getattr(envelope, "research_case_hash", None), "research_case_hash")
    if not is_sha256(research_case_hash):
        raise ValueError("research_case_hash must be lowercase SHA-256")
    stage_records = [_stage_record(x) for x in getattr(envelope, "stage_receipts", ())]
    stage_sequence = tuple(x["stage_id"] for x in stage_records)
    if stage_sequence != AUTHORIZED_STAGE_SEQUENCE:
        raise ValueError("canonical write authorization requires the exact monotonic stage sequence")
    if any(x["cutoff_date"] != cutoff_date for x in stage_records):
        raise ValueError("stage receipt cutoff does not match Run Envelope")
    for previous, current in zip(stage_records, stage_records[1:]):
        if previous["output_hashes"] and not set(previous["output_hashes"]).intersection(current["input_hashes"]):
            raise ValueError(
                f"stage receipt lineage broken between {previous['stage_id']} and {current['stage_id']}"
            )

    snapshot_hash = _snapshot_hash(snapshot)
    input_data = snapshot["input"]
    if not isinstance(input_data, Mapping):
        raise ValueError("snapshot.input must be an object")
    expected_identity = {
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "cutoff_date": cutoff_date,
        "as_of_date": as_of_date,
    }
    for field, expected in expected_identity.items():
        actual = input_data.get(field)
        if field in {"market", "symbol"}:
            actual = str(actual or "").upper()
        if str(actual or "") != expected:
            raise ValueError(f"snapshot identity does not match Run Envelope: {field}")
    if canonical_hash(dict(input_data)) != research_case_hash:
        raise ValueError("snapshot Research Case hash does not match Run Envelope")

    from .decision_admission import validate_decision_admission_receipt
    validate_decision_admission_receipt(dict(decision_admission), snapshot=dict(snapshot))
    decision_admission_hash = canonical_hash(dict(decision_admission))
    decision_stage = stage_records[-1]
    if decision_admission_hash not in decision_stage["output_hashes"]:
        raise ValueError("DECISION_ADMITTED receipt does not bind the actual Decision Admission")
    evidence_stage = next(x for x in stage_records if x["stage_id"] == "EVIDENCE_ADMITTED")
    semantic_stage = next(x for x in stage_records if x["stage_id"] == "SEMANTIC_ADMITTED")
    forecast_stage = next(x for x in stage_records if x["stage_id"] == "FORECAST_ADMITTED")
    valuation_stage = next(x for x in stage_records if x["stage_id"] == "VALUATION_ADMITTED")

    core = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "run_id": run_id,
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "cutoff_date": cutoff_date,
        "as_of_date": as_of_date,
        "orchestrator_version": getattr(envelope, "orchestrator_version", ""),
        "research_case_hash": research_case_hash,
        "snapshot_hash": snapshot_hash,
        "decision_admission_hash": decision_admission_hash,
        "evidence_manifest_hashes": list(evidence_stage["output_hashes"]),
        "semantic_artifact_hashes": list(semantic_stage["output_hashes"]),
        "forecast_admission_hashes": list(forecast_stage["output_hashes"]),
        "valuation_admission_hashes": list(valuation_stage["output_hashes"]),
        "stage_sequence": list(stage_sequence),
        "stage_receipts": stage_records,
        "stage_chain_hash": canonical_hash(stage_records),
        "issued_at": _field(issued_at or getattr(envelope, "created_at", None), "issued_at"),
        "authorization_status": "AUTHORIZED",
    }
    return {**core, "authorization_hash": canonical_hash(core)}


def _verify_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "run_id", "case_id", "market", "symbol",
        "cutoff_date", "as_of_date", "orchestrator_version",
        "research_case_hash", "snapshot_hash", "decision_admission_hash",
        "evidence_manifest_hashes", "semantic_artifact_hashes",
        "forecast_admission_hashes", "valuation_admission_hashes",
        "stage_sequence", "stage_receipts", "stage_chain_hash",
        "issued_at", "authorization_status", "authorization_hash",
    }
    if set(record) != required:
        raise ValueError("canonical run authorization fields are invalid")
    if record["schema_version"] != AUTHORIZATION_SCHEMA or record["authorization_status"] != "AUTHORIZED":
        raise ValueError("canonical run authorization status/schema is invalid")
    if record["stage_sequence"] != list(AUTHORIZED_STAGE_SEQUENCE):
        raise ValueError("canonical run authorization stage sequence is invalid")
    if len(record["stage_receipts"]) != len(AUTHORIZED_STAGE_SEQUENCE):
        raise ValueError("canonical run authorization stage receipt count is invalid")
    for h in (record["research_case_hash"], record["snapshot_hash"], record["decision_admission_hash"], record["stage_chain_hash"]):
        if not is_sha256(h):
            raise ValueError("canonical run authorization contains invalid hashes")
    stage_records = [_stage_record(x) for x in record["stage_receipts"]]
    if [x["stage_id"] for x in stage_records] != list(AUTHORIZED_STAGE_SEQUENCE):
        raise ValueError("canonical run authorization stage records mismatch")
    if canonical_hash(stage_records) != record["stage_chain_hash"]:
        raise ValueError("canonical run authorization stage-chain hash mismatch")
    core = {key: record[key] for key in required if key != "authorization_hash"}
    if canonical_hash(core) != record["authorization_hash"]:
        raise ValueError("canonical run authorization hash mismatch")


def write_run_authorization(
    root: str | Path,
    *,
    envelope: Any,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
    issued_at: str | None = None,
) -> Path:
    record = build_run_authorization(
        envelope=envelope,
        snapshot=snapshot,
        decision_admission=decision_admission,
        issued_at=issued_at,
    )
    _verify_record(record)
    path = authorization_path(root, record["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError("immutable canonical run authorization already exists with different content")
        return path
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8", newline="\n")
    tmp.replace(path)
    return path


def verify_run_authorization(
    root: str | Path,
    *,
    run_id: str,
    snapshot_hash: str,
    decision_admission: Mapping[str, Any],
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: str,
) -> dict[str, Any]:
    path = authorization_path(root, run_id)
    if not path.is_file():
        raise ValueError("CANONICAL_RUN_AUTHORIZATION_BLOCKED: no persisted orchestrator authorization for run_id")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("CANONICAL_RUN_AUTHORIZATION_BLOCKED: authorization record is unreadable") from exc
    if not isinstance(record, dict):
        raise ValueError("CANONICAL_RUN_AUTHORIZATION_BLOCKED: authorization record is not an object")
    try:
        _verify_record(record)
    except ValueError as exc:
        raise ValueError(f"CANONICAL_RUN_AUTHORIZATION_BLOCKED: {exc}") from exc
    expected = {
        "run_id": run_id,
        "snapshot_hash": snapshot_hash,
        "case_id": case_id,
        "market": str(market).upper(),
        "symbol": str(symbol).upper(),
        "company": company,
        "cutoff_date": cutoff_date,
        "decision_admission_hash": canonical_hash(dict(decision_admission)),
    }
    for field in ("run_id", "snapshot_hash", "case_id", "market", "symbol", "cutoff_date", "decision_admission_hash"):
        if record.get(field) != expected[field]:
            raise ValueError(f"CANONICAL_RUN_AUTHORIZATION_BLOCKED: {field} binding mismatch")
    # Company is bound through the snapshot/Research Case hash and Decision Admission;
    # repeat the explicit check via the signed stage chain's root Research Case identity.
    from .decision_admission import validate_decision_admission_receipt
    if (
        str(decision_admission.get("company", "")) != company
        or decision_admission.get("case_id") != case_id
    ):
        raise ValueError("CANONICAL_RUN_AUTHORIZATION_BLOCKED: Decision Admission identity mismatch")
    return record


def persist_run_envelope(root: str | Path, envelope: Any) -> Path:
    """Persist stage receipts append-only and update a non-authoritative envelope projection."""
    run_id = _field(getattr(envelope, "run_id", None), "run_id")
    run_dir = Path(root) / ".iios" / "canonical-runs" / hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_receipts = [_stage_record(x) for x in getattr(envelope, "stage_receipts", ())]
    for idx, receipt in enumerate(stage_receipts, start=1):
        path = run_dir / f"stage-{idx:02d}-{receipt['stage_id'].lower()}.json"
        payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != payload:
            raise ValueError("append-only stage receipt conflict")
        if not path.exists():
            path.write_text(payload, encoding="utf-8", newline="\n")
    stage_state = getattr(envelope, "stage_state", None)
    run_status = getattr(envelope, "run_status", None)
    record = {
        "run_id": run_id,
        "case_id": getattr(envelope, "case_id", ""),
        "market": getattr(envelope, "market", ""),
        "symbol": getattr(envelope, "symbol", ""),
        "cutoff_date": getattr(envelope, "cutoff_date", ""),
        "as_of_date": getattr(envelope, "as_of_date", ""),
        "request_type": getattr(envelope, "request_type", ""),
        "orchestrator_version": getattr(envelope, "orchestrator_version", ""),
        "research_case_hash": getattr(envelope, "research_case_hash", None),
        "stage_state": getattr(stage_state, "value", str(stage_state)),
        "run_status": getattr(run_status, "value", str(run_status)),
        "stage_receipt_count": len(stage_receipts),
        "stage_chain_hash": canonical_hash(stage_receipts),
        "non_canonical_reason": getattr(envelope, "non_canonical_reason", None),
        "created_at": getattr(envelope, "created_at", ""),
    }
    record["envelope_hash"] = canonical_hash(record)
    path = run_dir / "envelope.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)
    return path


__all__ = [
    "AUTHORIZATION_SCHEMA",
    "authorization_path",
    "build_run_authorization",
    "write_run_authorization",
    "verify_run_authorization",
    "persist_run_envelope",
]
