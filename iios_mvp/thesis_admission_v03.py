from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Mapping

THESIS_ADMISSION_VERSION = "IIOS-CORE-04-THESIS-ADMISSION-0.1"
THESIS_ADMISSION_POLICY_VERSION = "IIOS-THESIS-ADMISSION-POLICY-0.1"
THESIS_STATUSES = {"INTACT", "WATCH", "BROKEN", "UNKNOWN"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _dt(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("thesis known_at must be timezone-aware")
    return parsed


def admit_thesis(
    thesis: Mapping[str, Any],
    *,
    case_id: str,
    cutoff_date: str,
) -> dict[str, Any]:
    if not isinstance(thesis, Mapping):
        raise ValueError("thesis must be an object")
    required = {
        "status",
        "statement",
        "mechanism",
        "key_driver_ids",
        "falsifiers",
        "monitoring_triggers",
        "evidence_ids",
        "known_at",
        "prepared_without_current_price",
    }
    missing = sorted(required - set(thesis))
    if missing:
        raise ValueError(f"thesis missing required fields: {missing}")
    status = str(thesis["status"]).strip().upper()
    if status not in THESIS_STATUSES:
        raise ValueError("thesis.status is invalid")
    for field in ("statement", "mechanism"):
        if not str(thesis[field]).strip():
            raise ValueError(f"thesis.{field} is required")
    for field in ("key_driver_ids", "falsifiers", "monitoring_triggers", "evidence_ids"):
        value = thesis[field]
        if not isinstance(value, list) or not value or any(not str(x).strip() for x in value):
            raise ValueError(f"thesis.{field} must be a non-empty list")
    if thesis["prepared_without_current_price"] is not True:
        raise ValueError(
            "thesis must be prepared_without_current_price=true to avoid price circularity"
        )
    known_at = _dt(thesis["known_at"])
    cutoff = date.fromisoformat(str(cutoff_date))
    if known_at.date() > cutoff:
        raise ValueError("thesis known_at is after cutoff_date")

    core = {
        "schema_version": THESIS_ADMISSION_VERSION,
        "policy_version": THESIS_ADMISSION_POLICY_VERSION,
        "policy": "EXPLICIT_EVIDENCE_BOUND_PRICE_INDEPENDENT_THESIS",
        "case_id": str(case_id),
        "cutoff_date": cutoff.isoformat(),
        "status": status,
        "statement": str(thesis["statement"]).strip(),
        "mechanism": str(thesis["mechanism"]).strip(),
        "key_driver_ids": [str(x).strip() for x in thesis["key_driver_ids"]],
        "falsifiers": [str(x).strip() for x in thesis["falsifiers"]],
        "monitoring_triggers": [str(x).strip() for x in thesis["monitoring_triggers"]],
        "evidence_ids": sorted({str(x).strip() for x in thesis["evidence_ids"]}),
        "known_at": known_at.isoformat(),
        "prepared_without_current_price": True,
        "admission_status": "ADMITTED",
    }
    record_hash = _sha(core)
    return {
        **core,
        "thesis_id": f"{case_id}:THESIS:{record_hash[:16]}",
        "admission_record_hash": record_hash,
    }


def validate_thesis_admission(
    record: Any,
    *,
    case_id: str,
    cutoff_date: str,
) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("thesis_admission must be an object")
    required = {
        "schema_version",
        "policy_version",
        "policy",
        "case_id",
        "cutoff_date",
        "status",
        "statement",
        "mechanism",
        "key_driver_ids",
        "falsifiers",
        "monitoring_triggers",
        "evidence_ids",
        "known_at",
        "prepared_without_current_price",
        "admission_status",
        "thesis_id",
        "admission_record_hash",
    }
    if set(record) != required:
        raise ValueError("thesis_admission fields are invalid")
    if record["schema_version"] != THESIS_ADMISSION_VERSION:
        raise ValueError("thesis admission version mismatch")
    if record["policy_version"] != THESIS_ADMISSION_POLICY_VERSION:
        raise ValueError("thesis admission policy version mismatch")
    if record["case_id"] != case_id:
        raise ValueError("thesis admission case_id mismatch")
    if record["cutoff_date"] != date.fromisoformat(str(cutoff_date)).isoformat():
        raise ValueError("thesis admission cutoff mismatch")
    if record["status"] not in THESIS_STATUSES:
        raise ValueError("thesis admission status invalid")
    if record["admission_status"] != "ADMITTED":
        raise ValueError("thesis admission is not ADMITTED")
    if record["prepared_without_current_price"] is not True:
        raise ValueError("thesis admission is not price-independent")
    known = _dt(record["known_at"])
    if known.date() > date.fromisoformat(str(cutoff_date)):
        raise ValueError("thesis admission known_at is after cutoff")
    core = {k: record[k] for k in required if k not in {"thesis_id", "admission_record_hash"}}
    expected_hash = _sha(core)
    if record["admission_record_hash"] != expected_hash:
        raise ValueError("thesis admission hash mismatch")
    if record["thesis_id"] != f"{case_id}:THESIS:{expected_hash[:16]}":
        raise ValueError("thesis_id mismatch")


__all__ = [
    "THESIS_ADMISSION_POLICY_VERSION",
    "THESIS_ADMISSION_VERSION",
    "THESIS_STATUSES",
    "admit_thesis",
    "validate_thesis_admission",
]
