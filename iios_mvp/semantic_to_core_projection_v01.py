from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
import hashlib
import json

from .decision_upstream_admission_v03 import validate_decision_upstream_admission
from .semantic_producer_admission_v01 import SemanticAdmissionResult
from .thesis_admission_v03 import admit_thesis, THESIS_STATUSES


SEMANTIC_CORE_PROJECTION_VERSION = "IIOS-SEMANTIC-CORE-PROJECTION-0.1"
THESIS_PROJECTION_FIELDS = {
    "status",
    "statement",
    "mechanism",
    "key_driver_ids",
    "falsifiers",
    "monitoring_triggers",
}


class SemanticCoreProjectionError(ValueError):
    """Raised when an admitted semantic artifact cannot become canonical core input."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticCoreProjectionError(f"{path} must be a non-empty string")
    return value.strip()


def _require_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise SemanticCoreProjectionError(f"{path} must be a non-empty string list")
    return [item.strip() for item in value]


def _validate_admitted_semantic(
    artifact: Mapping[str, Any],
    admission: SemanticAdmissionResult | Mapping[str, Any],
) -> None:
    if not isinstance(artifact, Mapping):
        raise SemanticCoreProjectionError("semantic artifact must be an object")
    if artifact.get("artifact_type") != "THESIS_ASSESSMENT":
        raise SemanticCoreProjectionError(
            "B2-E semantic-to-core projection currently supports THESIS_ASSESSMENT only"
        )
    if not artifact.get("artifact_hash"):
        raise SemanticCoreProjectionError("semantic artifact hash is required")
    admission_status = (
        admission.status
        if isinstance(admission, SemanticAdmissionResult)
        else admission.get("status")
    )
    admission_hash = (
        admission.artifact_hash
        if isinstance(admission, SemanticAdmissionResult)
        else admission.get("artifact_hash")
    )
    if admission_status != "ADMITTED":
        raise SemanticCoreProjectionError("semantic artifact must be ADMITTED before core projection")
    if admission_hash != artifact.get("artifact_hash"):
        raise SemanticCoreProjectionError(
            "semantic admission artifact_hash does not match semantic artifact"
        )


def _validate_identity(artifact: Mapping[str, Any], case: Mapping[str, Any]) -> None:
    pairs = (
        ("case_id", "case_id"),
        ("market", "market"),
        ("symbol", "symbol"),
        ("company", "company"),
        ("cutoff_date", "cutoff_date"),
    )
    for field, case_field in pairs:
        left = str(artifact.get(field, "")).strip()
        right = str(case.get(case_field, "")).strip()
        if field in {"market", "symbol"}:
            left, right = left.upper(), right.upper()
        if left != right:
            raise SemanticCoreProjectionError(
                f"semantic-to-core identity mismatch: {field}"
            )


def project_thesis_semantic_to_core(
    *,
    artifact: Mapping[str, Any],
    admission: SemanticAdmissionResult | Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert admitted THESIS_ASSESSMENT into typed, deterministic Core thesis input.

    The semantic producer proposes thesis content only. Evidence IDs and known_at are
    derived from the already-admitted semantic artifact lineage, never supplied by
    the producer inside the projection.
    """
    _validate_admitted_semantic(artifact, admission)
    _validate_identity(artifact, case)

    output = artifact.get("output")
    if not isinstance(output, Mapping):
        raise SemanticCoreProjectionError("semantic artifact output must be an object")
    if set(output) != {"core_projection"}:
        raise SemanticCoreProjectionError(
            "THESIS_ASSESSMENT output must contain exactly core_projection"
        )
    projection = output["core_projection"]
    if not isinstance(projection, Mapping):
        raise SemanticCoreProjectionError("core_projection must be an object")
    if set(projection) != THESIS_PROJECTION_FIELDS:
        extras = sorted(set(projection) - THESIS_PROJECTION_FIELDS)
        missing = sorted(THESIS_PROJECTION_FIELDS - set(projection))
        raise SemanticCoreProjectionError(
            f"core_projection fields invalid; extras={extras}; missing={missing}"
        )

    status = str(projection["status"]).strip().upper()
    if status not in THESIS_STATUSES:
        raise SemanticCoreProjectionError("core_projection.status is invalid")

    statement = _require_text(projection["statement"], "core_projection.statement")
    mechanism = _require_text(projection["mechanism"], "core_projection.mechanism")
    key_driver_ids = _require_list(
        projection["key_driver_ids"], "core_projection.key_driver_ids"
    )
    falsifiers = _require_list(
        projection["falsifiers"], "core_projection.falsifiers"
    )
    monitoring_triggers = _require_list(
        projection["monitoring_triggers"], "core_projection.monitoring_triggers"
    )

    try:
        created_at = datetime.fromisoformat(
            str(artifact["created_at"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticCoreProjectionError(
            "semantic artifact created_at must be an ISO datetime"
        ) from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise SemanticCoreProjectionError("semantic artifact created_at must be timezone-aware")
    cutoff = date.fromisoformat(str(case["cutoff_date"]))
    if created_at.date() > cutoff:
        raise SemanticCoreProjectionError(
            "semantic artifact created_at is after case cutoff_date"
        )

    input_refs = artifact.get("input_refs")
    if not isinstance(input_refs, list) or not input_refs:
        raise SemanticCoreProjectionError(
            "semantic artifact input_refs must be non-empty for core projection"
        )
    evidence_ids = sorted({str(ref).strip() for ref in input_refs if str(ref).strip()})
    if not evidence_ids:
        raise SemanticCoreProjectionError(
            "semantic artifact input_refs must provide non-empty evidence IDs"
        )

    thesis = {
        "status": status,
        "statement": statement,
        "mechanism": mechanism,
        "key_driver_ids": key_driver_ids,
        "falsifiers": falsifiers,
        "monitoring_triggers": monitoring_triggers,
        "evidence_ids": evidence_ids,
        # Semantic reasoning may be generated after the historical cutoff.
        # Its effective economic knowledge date is bounded by the admitted case cutoff;
        # the actual reasoning creation time remains preserved in the projection receipt.
        "known_at": f"{cutoff.isoformat()}T23:59:59+00:00",
        "prepared_without_current_price": True,
    }
    thesis_admission = admit_thesis(
        thesis,
        case_id=str(case["case_id"]),
        cutoff_date=cutoff.isoformat(),
    )

    upstream_raw = case.get("decision_upstream_admission")
    if not isinstance(upstream_raw, Mapping):
        raise SemanticCoreProjectionError("canonical decision_upstream_admission is required")
    upstream = dict(upstream_raw)
    if upstream.get("schema_version") != "IIOS-CORE-04-UPSTREAM-ADMISSION-0.2":
        raise SemanticCoreProjectionError(
            "B2-E semantic-to-core projection requires upstream admission v0.2"
        )

    quality_refs = {
        evidence_id
        for row in upstream["quality_gate"]["dimensions"]
        for evidence_id in row["evidence_ids"]
    }
    upstream["thesis_status"] = thesis_admission["status"]
    upstream["thesis_admission_status"] = thesis_admission["admission_status"]
    upstream["thesis_admission"] = thesis_admission
    upstream["evidence_ids"] = sorted(quality_refs | set(evidence_ids))
    upstream["capital_admission_ready"] = bool(
        upstream["reality_status"] == "PASS"
        and upstream["quality_gate_status"] == "PASS"
        and upstream["value_driver_status"] == "PASS"
        and upstream["valuation_status"] == "PASS"
        and upstream["forecast_status"] == "PASS"
        and upstream["thesis_admission_status"] == "ADMITTED"
        and upstream["thesis_status"] == "INTACT"
    )
    upstream.pop("admission_record_hash", None)
    upstream["admission_record_hash"] = _sha(upstream)
    try:
        validate_decision_upstream_admission(
            upstream,
            case_id=str(case["case_id"]),
            cutoff_date=cutoff.isoformat(),
        )
    except (TypeError, ValueError) as exc:
        raise SemanticCoreProjectionError(
            f"projected canonical upstream admission is invalid: {exc}"
        ) from exc

    projection_core = {
        "projection_version": SEMANTIC_CORE_PROJECTION_VERSION,
        "projection_type": "THESIS_ASSESSMENT_TO_CANONICAL_THESIS",
        "semantic_artifact_id": str(artifact["artifact_id"]),
        "semantic_artifact_hash": str(artifact["artifact_hash"]),
        "semantic_admission_hash": (
            admission.admission_hash
            if isinstance(admission, SemanticAdmissionResult)
            else str(admission.get("admission_hash", ""))
        ),
        "case_id": str(case["case_id"]),
        "market": str(case["market"]).upper(),
        "symbol": str(case["symbol"]).upper(),
        "cutoff_date": cutoff.isoformat(),
        "semantic_reasoning_created_at": created_at.isoformat(),
        "input_evidence_ids": evidence_ids,
        "thesis_admission_hash": thesis_admission["admission_record_hash"],
    }
    projection_receipt = {
        **projection_core,
        "projection_hash": _sha(projection_core),
    }

    projected = dict(case)
    projected["thesis"] = thesis
    projected["decision_upstream_admission"] = upstream
    projected["semantic_core_projection"] = projection_receipt
    return projected


__all__ = [
    "SEMANTIC_CORE_PROJECTION_VERSION",
    "THESIS_PROJECTION_FIELDS",
    "SemanticCoreProjectionError",
    "project_thesis_semantic_to_core",
]
