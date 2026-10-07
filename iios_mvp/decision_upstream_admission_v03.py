from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping

from .quality_gate_v03 import (
    QUALITY_GATE_VERSION,
    build_quality_gate,
    validate_quality_gate,
)
from .thesis_admission_v03 import (
    THESIS_ADMISSION_VERSION,
    admit_thesis,
    validate_thesis_admission,
)
from .canonical_investment_admission_v01 import CanonicalInvestmentAdmissionResolver
from .upstream_authority_v03 import CORE_STATUS_DOMAINS, STATUS_FIELDS, validate_core_upstream_authority

DECISION_UPSTREAM_ADMISSION_VERSION = "IIOS-CORE-04-UPSTREAM-ADMISSION-0.1"
DECISION_UPSTREAM_ADMISSION_V02 = "IIOS-CORE-04-UPSTREAM-ADMISSION-0.2"
DECISION_UPSTREAM_POLICY_VERSION = "IIOS-DECISION-UPSTREAM-POLICY-0.1"
GATE_STATES = {"PASS", "CONDITIONAL", "UNKNOWN", "BLOCKED"}
THESIS_ADMISSION_STATES = {"ADMITTED", "BLOCKED", "REVIEW_REQUIRED", "UNKNOWN"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _status(value: Any, field: str) -> str:
    result = str(value).strip().upper()
    if result not in GATE_STATES:
        raise ValueError(f"{field} has unsupported state: {result}")
    return result


def build_decision_upstream_admission(
    *,
    case_id: str,
    cutoff_date: str,
    reality_status: str,
    quality: Mapping[str, Any],
    value_driver_status: str,
    valuation_status: str,
    forecast_status: str,
    thesis: Mapping[str, Any],
) -> dict[str, Any]:
    cutoff = date.fromisoformat(str(cutoff_date))
    qg = build_quality_gate(quality, case_id=case_id, cutoff_date=cutoff.isoformat())
    ta = admit_thesis(thesis, case_id=case_id, cutoff_date=cutoff.isoformat())

    statuses = {
        "reality_status": _status(reality_status, "reality_status"),
        "quality_gate_status": _status(qg["status"], "quality_gate_status"),
        "value_driver_status": _status(value_driver_status, "value_driver_status"),
        "valuation_status": _status(valuation_status, "valuation_status"),
        "forecast_status": _status(forecast_status, "forecast_status"),
    }
    thesis_status = str(ta["status"]).upper()
    evidence_ids = sorted(
        set(
            ta["evidence_ids"]
            + [
                evidence_id
                for row in qg["dimensions"]
                for evidence_id in row["evidence_ids"]
            ]
        )
    )

    capital_ready = (
        statuses["reality_status"] == "PASS"
        and statuses["quality_gate_status"] == "PASS"
        and statuses["value_driver_status"] == "PASS"
        and statuses["valuation_status"] == "PASS"
        and statuses["forecast_status"] == "PASS"
        and ta["admission_status"] == "ADMITTED"
        and thesis_status == "INTACT"
    )

    core = {
        "schema_version": DECISION_UPSTREAM_ADMISSION_VERSION,
        "policy_version": DECISION_UPSTREAM_POLICY_VERSION,
        "case_id": str(case_id),
        "cutoff_date": cutoff.isoformat(),
        **statuses,
        "thesis_status": thesis_status,
        "thesis_admission_status": ta["admission_status"],
        "capital_admission_ready": capital_ready,
        "quality_gate": qg,
        "thesis_admission": ta,
        "evidence_ids": evidence_ids,
    }
    record_hash = _sha(core)
    return {
        **core,
        "admission_record_hash": record_hash,
    }



def build_canonical_upstream_admission_v02(
    *,
    base_record: Mapping[str, Any],
    canonical_admission_refs: Mapping[str, Mapping[str, Any]],
    resolver: CanonicalInvestmentAdmissionResolver,
    market: str,
    symbol: str,
    company: str,
) -> dict[str, Any]:
    if not isinstance(base_record, Mapping):
        raise ValueError("base_record must be an object")
    case_id = str(base_record.get("case_id", "")).strip()
    cutoff_date = str(base_record.get("cutoff_date", "")).strip()
    if not case_id or not cutoff_date:
        raise ValueError("base_record case_id and cutoff_date are required")
    result = validate_core_upstream_authority(
        admission_refs=canonical_admission_refs,
        declared_states={
            STATUS_FIELDS[domain]: base_record.get(STATUS_FIELDS[domain])
            for domain in CORE_STATUS_DOMAINS
        },
        resolver=resolver,
        case_id=case_id,
        market=market,
        symbol=symbol,
        company=company,
        cutoff_date=date.fromisoformat(cutoff_date),
    )
    core = dict(base_record)
    core["schema_version"] = DECISION_UPSTREAM_ADMISSION_V02
    core["canonical_admission_refs"] = {
        domain: dict(canonical_admission_refs[domain])
        for domain in sorted(canonical_admission_refs)
    }
    for field, state in result["resolved_states"].items():
        core[field] = state
    core["capital_admission_ready"] = (
        core["reality_status"] == "PASS"
        and core["quality_gate_status"] == "PASS"
        and core["value_driver_status"] == "PASS"
        and core["valuation_status"] == "PASS"
        and core["forecast_status"] == "PASS"
        and core["thesis_admission_status"] == "ADMITTED"
        and core["thesis_status"] == "INTACT"
    )
    core.pop("admission_record_hash", None)
    return {**core, "admission_record_hash": _sha(core)}

def validate_decision_upstream_admission(
    record: Any,
    *,
    case_id: str,
    cutoff_date: str,
) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("decision_upstream_admission must be an object")
    required = {
        "schema_version",
        "policy_version",
        "case_id",
        "cutoff_date",
        "reality_status",
        "quality_gate_status",
        "value_driver_status",
        "valuation_status",
        "forecast_status",
        "thesis_status",
        "thesis_admission_status",
        "capital_admission_ready",
        "quality_gate",
        "thesis_admission",
        "evidence_ids",
        "admission_record_hash",
    }
    is_v02 = record.get("schema_version") == DECISION_UPSTREAM_ADMISSION_V02
    if is_v02:
        required = required | {"canonical_admission_refs"}
    if set(record) != required:
        raise ValueError("decision_upstream_admission fields are invalid")
    if record["schema_version"] not in {
        DECISION_UPSTREAM_ADMISSION_VERSION,
        DECISION_UPSTREAM_ADMISSION_V02,
    }:
        raise ValueError("decision upstream admission version mismatch")
    if record["policy_version"] != DECISION_UPSTREAM_POLICY_VERSION:
        raise ValueError("decision upstream policy version mismatch")
    if record["case_id"] != case_id:
        raise ValueError("decision upstream case_id mismatch")
    cutoff = date.fromisoformat(str(cutoff_date))
    if record["cutoff_date"] != cutoff.isoformat():
        raise ValueError("decision upstream cutoff mismatch")
    for field in ("reality_status", "quality_gate_status", "value_driver_status", "valuation_status", "forecast_status"):
        _status(record[field], field)
    if record["thesis_status"] not in {"INTACT", "WATCH", "BROKEN", "UNKNOWN"}:
        raise ValueError("decision upstream thesis_status invalid")
    if record["thesis_admission_status"] not in THESIS_ADMISSION_STATES:
        raise ValueError("decision upstream thesis_admission_status invalid")
    validate_quality_gate(record["quality_gate"], case_id=case_id, cutoff_date=cutoff.isoformat())
    validate_thesis_admission(record["thesis_admission"], case_id=case_id, cutoff_date=cutoff.isoformat())
    if record["quality_gate_status"] != record["quality_gate"]["status"]:
        raise ValueError("decision upstream quality_gate_status drift")
    if record["thesis_admission_status"] != record["thesis_admission"]["admission_status"]:
        raise ValueError("decision upstream thesis_admission_status drift")
    if record["thesis_status"] != record["thesis_admission"]["status"]:
        raise ValueError("decision upstream thesis_status drift")
    expected_ready = (
        record["reality_status"] == "PASS"
        and record["quality_gate_status"] == "PASS"
        and record["value_driver_status"] == "PASS"
        and record["valuation_status"] == "PASS"
        and record["forecast_status"] == "PASS"
        and record["thesis_admission_status"] == "ADMITTED"
        and record["thesis_status"] == "INTACT"
    )
    if record["capital_admission_ready"] is not expected_ready:
        raise ValueError("decision upstream capital_admission_ready mismatch")
    if is_v02:
        canonical_refs = record["canonical_admission_refs"]
        if not isinstance(canonical_refs, Mapping):
            raise ValueError("canonical_admission_refs must be an object")
        if set(canonical_refs) != set(CORE_STATUS_DOMAINS):
            raise ValueError("canonical_admission_refs are incomplete")
        for domain, reference in canonical_refs.items():
            if not isinstance(reference, Mapping):
                raise ValueError(f"canonical admission reference for {domain} must be an object")

    refs = record["evidence_ids"]
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or any(not str(x).strip() for x in refs):
        raise ValueError("decision upstream evidence_ids invalid")
    q_refs = {
        evidence_id
        for row in record["quality_gate"]["dimensions"]
        for evidence_id in row["evidence_ids"]
    }
    t_refs = set(record["thesis_admission"]["evidence_ids"])
    if set(refs) != q_refs | t_refs:
        raise ValueError("decision upstream evidence closure mismatch")
    core = {k: record[k] for k in required if k != "admission_record_hash"}
    if record["admission_record_hash"] != _sha(core):
        raise ValueError("decision upstream admission hash mismatch")


__all__ = [
    "DECISION_UPSTREAM_ADMISSION_VERSION",
    "DECISION_UPSTREAM_POLICY_VERSION",
    "DECISION_UPSTREAM_ADMISSION_V02",
    "build_decision_upstream_admission",
    "build_canonical_upstream_admission_v02",
    "validate_decision_upstream_admission",
]
