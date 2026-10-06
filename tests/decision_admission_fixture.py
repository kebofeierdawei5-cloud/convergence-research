from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def build_fixture_admission_receipt(
    *,
    snapshot: Mapping[str, Any],
    canonical_decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = snapshot["decision"] if canonical_decision is None else canonical_decision
    core = {
        "schema_version": "IIOS-DECISION-ADMISSION-0.1",
        "status": "ADMITTED",
        "admission_method": "CANONICAL_DECIDE_V03_REEXECUTED",
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "engine_version": "0.3.0",
        "case_id": str(snapshot["input"]["case_id"]),
        "market": str(snapshot["input"]["market"]).upper(),
        "symbol": str(snapshot["input"]["symbol"]).upper(),
        "company": str(snapshot["input"]["company"]),
        "cutoff_date": str(snapshot["input"]["cutoff_date"]),
        "snapshot_hash": str(snapshot["snapshot_hash"]),
        "canonical_decision_hash": _sha(decision),
        "canonical_action": str(decision["action"]).upper(),
        "canonical_decision_status": str(decision.get("decision_status", "READY")),
        "canonical_new_capital_allowed": bool(
            (decision.get("gates") or {}).get("new_capital_allowed", False)
        ),
    }
    return {**core, "admission_record_hash": _sha(core)}
