from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping

DECISION_ADMISSION_SCHEMA_VERSION = "IIOS-DECISION-ADMISSION-0.1"
DECISION_ADMISSION_METHOD = "CANONICAL_DECIDE_V03_REEXECUTED"
DECISION_ADMISSION_STATUS = "ADMITTED"
CANONICAL_INVESTMENT_CORE_VERSION = "IIOS-INVESTMENT-CORE-0.3"
CANONICAL_DECISION_ENGINE_VERSION = "0.3.0"
DECISION_ACTIONS = {"BUY", "ADD", "HOLD", "REDUCE", "EXIT", "NO-BUY", "WATCH", "REVIEW_REQUIRED"}

CANONICAL_DECISION_FIELDS = (
    "contract_version",
    "decision_status",
    "investability_status",
    "action",
    "primary_reason",
    "human_approval_required",
    "auto_execution",
    "gates",
    "decision_upstream_admission",
    "position_package_complete",
    "target_entry_price",
    "target_entry_price_return_only",
    "target_entry_price_semantics",
    "target_entry_price_requires_gap_revalidation",
    "target_entry_price_v2_version",
    "target_entry_price_v2",
    "target_entry_price_gap_revalidation",
    "target_entry_price_p2_1_version",
    "target_entry_price_p2_1",
    "target_entry_price_p2_1_price_response",
    "canonical_entry_evaluation_version",
    "canonical_entry_evaluation",
    "decision_pre_admission_action",
    "decision_admission_version",
    "decision_admission",
    "decision_admission_status",
    "decision_admission_rule_id",
    "current_price",
    "mie_policy",
    "mie_material_contradiction",
    "decision_precedence_version",
    "decision_precedence_rule_id",
    "decision_precedence_rank",
    "decision_scope",
    "capital_effect",
    "risk_portfolio_contract",
    "expectation_gap_evaluation",
    "positioning_sizing",
    "return_metrics",
)
CANONICAL_DECISION_REQUIRED_FIELDS = (
    "action",
    "decision_status",
    "gates",
    "human_approval_required",
    "auto_execution",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{field} is required")
    return result


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date") from exc


def _identity_from_input(input_data: Mapping[str, Any]) -> dict[str, str]:
    return {
        "case_id": _text(input_data.get("case_id"), "snapshot.input.case_id"),
        "market": _text(input_data.get("market"), "snapshot.input.market").upper(),
        "symbol": _text(input_data.get("symbol"), "snapshot.input.symbol").upper(),
        "company": _text(input_data.get("company"), "snapshot.input.company"),
        "cutoff_date": _text(input_data.get("cutoff_date"), "snapshot.input.cutoff_date"),
    }


def _snapshot_core(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    required = {"snapshot_schema", "engine_version", "input", "decision", "snapshot_hash"}
    if not required.issubset(set(snapshot)):
        raise ValueError("snapshot is missing required fields for Decision Admission")
    core = {k: snapshot[k] for k in ("snapshot_schema", "engine_version", "input", "decision")}
    if _sha(core) != snapshot["snapshot_hash"]:
        raise ValueError("snapshot hash mismatch at Decision Admission")
    if snapshot["snapshot_schema"] != "IIOS-MVP-SNAPSHOT-0.3.0":
        raise ValueError("canonical Decision Admission requires IIOS-MVP-SNAPSHOT-0.3.0")
    return core


def _decision_action(decision: Mapping[str, Any]) -> str:
    nested = decision.get("decision") if isinstance(decision.get("decision"), Mapping) else decision
    action = str((nested or {}).get("action", "")).strip().upper()
    if action not in DECISION_ACTIONS:
        raise ValueError(f"canonical decision action invalid: {action}")
    return action


def _build_receipt_from_canonical(
    *,
    snapshot: Mapping[str, Any],
    canonical_decision: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot_core = _snapshot_core(snapshot)
    identity = _identity_from_input(snapshot_core["input"])
    if _decision_action(snapshot_core["decision"]) != _decision_action(canonical_decision):
        raise ValueError("snapshot decision action does not equal canonical Decision Kernel action")
    missing = [key for key in CANONICAL_DECISION_REQUIRED_FIELDS if key not in canonical_decision]
    if missing:
        raise ValueError("canonical Decision Kernel result missing required fields: " + ", ".join(missing))
    projection = {
        key: canonical_decision[key]
        for key in CANONICAL_DECISION_FIELDS
        if key in canonical_decision
    }
    snapshot_decision = snapshot_core["decision"]
    for key in projection:
        if key not in snapshot_decision or snapshot_decision[key] != projection[key]:
            raise ValueError("snapshot decision does not equal canonical Decision Kernel result")
    core = {
        "schema_version": DECISION_ADMISSION_SCHEMA_VERSION,
        "status": DECISION_ADMISSION_STATUS,
        "admission_method": DECISION_ADMISSION_METHOD,
        "contract_version": CANONICAL_INVESTMENT_CORE_VERSION,
        "engine_version": CANONICAL_DECISION_ENGINE_VERSION,
        **identity,
        "snapshot_hash": snapshot["snapshot_hash"],
        "canonical_decision_keys": sorted(projection.keys()),
        "canonical_decision_projection": projection,
        "canonical_decision_hash": _sha(projection),
        "canonical_action": _decision_action(canonical_decision),
        "canonical_decision_status": _text(
            canonical_decision.get("decision_status", "REVIEW_REQUIRED"),
            "canonical_decision.decision_status",
        ),
        "canonical_new_capital_allowed": bool(
            (canonical_decision.get("gates") or {}).get("new_capital_allowed", False)
        ),
    }
    return {**core, "admission_record_hash": _sha(core)}


def admit_canonical_decision(
    *,
    case: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    evidence_root_resolver: Any | None = None,
    current_price_resolver: Any | None = None,
    independent_forecast_resolver: Any | None = None,
    upstream_authority_resolver: Any | None = None,
    valuation_output_resolver: Any | None = None,
) -> dict[str, Any]:
    """Re-run the canonical v0.3 Decision Kernel and issue a binding admission receipt."""
    from .investment_core_contract_v03 import decide_v03, validate_case_v03

    validation = validate_case_v03(
        case,
        evidence_root_resolver=evidence_root_resolver,
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )
    if validation["status"] != "PASS":
        raise ValueError(
            "canonical Decision Admission requires a PASS validated case: "
            + "; ".join(err["message"] for err in validation["errors"])
        )
    canonical_decision = decide_v03(
        dict(case),
        evidence_root_resolver=evidence_root_resolver,
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )
    snapshot_core = _snapshot_core(snapshot)
    snapshot_identity = _identity_from_input(snapshot_core["input"])
    case_identity = _identity_from_input(case)
    if snapshot_identity != case_identity:
        raise ValueError("snapshot and canonical case identity mismatch")
    cutoff = _date(case_identity["cutoff_date"], "case.cutoff_date")
    if cutoff != _date(snapshot_identity["cutoff_date"], "snapshot.input.cutoff_date"):
        raise ValueError("snapshot/case cutoff mismatch")
    required_fields = [key for key in CANONICAL_DECISION_REQUIRED_FIELDS if key not in canonical_decision]
    if required_fields:
        raise ValueError("canonical Decision Kernel result missing required fields: " + ", ".join(required_fields))
    projection = {
        key: canonical_decision[key]
        for key in CANONICAL_DECISION_FIELDS
        if key in canonical_decision
    }
    snapshot_decision = snapshot_core["decision"]
    mismatched_keys = [
        key
        for key in projection
        if key not in snapshot_decision or snapshot_decision[key] != projection[key]
    ]
    if mismatched_keys:
        raise ValueError(
            "snapshot decision does not equal freshly re-executed canonical Decision Kernel result"
            f"; mismatched keys={mismatched_keys}"
        )
    return _build_receipt_from_canonical(
        snapshot=snapshot,
        canonical_decision=canonical_decision,
    )


def validate_decision_admission_receipt(
    record: Any,
    *,
    snapshot: Mapping[str, Any],
) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("decision_admission must be an object")
    required = {
        "schema_version",
        "status",
        "admission_method",
        "contract_version",
        "engine_version",
        "case_id",
        "market",
        "symbol",
        "company",
        "cutoff_date",
        "snapshot_hash",
        "canonical_decision_keys",
        "canonical_decision_projection",
        "canonical_decision_hash",
        "canonical_action",
        "canonical_decision_status",
        "canonical_new_capital_allowed",
        "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("decision_admission fields are invalid")
    if record["schema_version"] != DECISION_ADMISSION_SCHEMA_VERSION:
        raise ValueError("decision_admission schema/version mismatch")
    if record["status"] != DECISION_ADMISSION_STATUS:
        raise ValueError("decision_admission is not ADMITTED")
    if record["admission_method"] != DECISION_ADMISSION_METHOD:
        raise ValueError("decision_admission method is not canonical")
    if record["contract_version"] != CANONICAL_INVESTMENT_CORE_VERSION:
        raise ValueError("decision_admission contract version mismatch")
    if record["engine_version"] != CANONICAL_DECISION_ENGINE_VERSION:
        raise ValueError("decision_admission engine version mismatch")
    identity = _identity_from_input(snapshot["input"])
    for key in ("case_id", "market", "symbol", "company", "cutoff_date"):
        if record[key] != identity[key]:
            raise ValueError(f"decision_admission {key} does not match snapshot identity")
    if record["snapshot_hash"] != snapshot["snapshot_hash"]:
        raise ValueError("decision_admission snapshot binding mismatch")
    projection = record["canonical_decision_projection"]
    if not isinstance(projection, Mapping):
        raise ValueError("decision_admission canonical_decision_projection is invalid")
    keys = record["canonical_decision_keys"]
    if (
        not isinstance(keys, list)
        or keys != sorted(set(keys))
        or any(not isinstance(key, str) or not key for key in keys)
        or "action" not in keys
        or sorted(projection.keys()) != keys
    ):
        raise ValueError("decision_admission canonical decision projection is invalid")
    if record["canonical_decision_hash"] != _sha(projection):
        raise ValueError("decision_admission canonical_decision_hash does not match canonical projection")
    snapshot_decision = snapshot["decision"]
    if any(key not in snapshot_decision for key in keys):
        raise ValueError("decision_admission canonical decision keys are not present in snapshot")
    if any(snapshot_decision[key] != projection[key] for key in keys):
        raise ValueError("decision_admission canonical decision projection does not match snapshot")
    if record["canonical_action"] != _decision_action(projection):
        raise ValueError("decision_admission canonical_action does not match canonical projection")
    if record["canonical_action"] not in DECISION_ACTIONS:
        raise ValueError("decision_admission canonical_action is invalid")
    if not isinstance(record["canonical_decision_status"], str) or not record["canonical_decision_status"].strip():
        raise ValueError("decision_admission canonical_decision_status is required")
    if not isinstance(record["canonical_new_capital_allowed"], bool):
        raise ValueError("decision_admission canonical_new_capital_allowed must be boolean")
    core = {k: record[k] for k in required if k != "admission_record_hash"}
    if record["admission_record_hash"] != _sha(core):
        raise ValueError("decision_admission admission_record_hash mismatch")


__all__ = [
    "DECISION_ADMISSION_SCHEMA_VERSION",
    "DECISION_ADMISSION_METHOD",
    "DECISION_ADMISSION_STATUS",
    "admit_canonical_decision",
    "validate_decision_admission_receipt",
]