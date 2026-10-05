from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .company_evidence import REQUIRED_COMPANY_FIELD_GROUPS
from .evidence_contract import parse_temporal

PIT_BASIS_TO_CAPABILITY = {
    "SOURCE_VINTAGE": {"SOURCE_VINTAGE"},
    "EVENT_PUBLICATION": {"EVENT_PUBLICATION"},
    "TRADE_DATE": {"SOURCE_VINTAGE", "EXPLICIT_PIT_QUERY"},
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def validate_company_source_capture_plan(
    plan: Any,
    registry: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["CAPTURE_PLAN_TYPE:plan must be an object"]
    if not isinstance(registry, dict):
        return ["SOURCE_REGISTRY_TYPE:registry must be an object"]

    required = (
        "schema_version", "case_id", "market", "symbol", "company",
        "cutoff_date", "purpose", "capture_requirements", "plan_status", "audit",
    )
    for field in required:
        if field not in plan:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors

    if plan["schema_version"] != "IIOS-COMPANY-SOURCE-CAPTURE-PLAN-0.1":
        errors.append("VERSION_INVALID")
    if plan["market"] not in {"CN-A", "HK"}:
        errors.append("MARKET_INVALID")
    try:
        parse_temporal(plan["cutoff_date"], "cutoff_date")
    except ValueError as exc:
        errors.append(f"TEMPORAL:{exc}")
    if plan.get("plan_status") != "BLOCKED_PENDING_RAW":
        errors.append("PLAN_STATUS_INVALID")

    registry_sources = registry.get("sources")
    if not isinstance(registry_sources, list):
        return errors + ["SOURCE_REGISTRY_SOURCES_REQUIRED"]
    registry_by_ref = {
        str(item.get("source_ref", "")).strip(): item
        for item in registry_sources
        if isinstance(item, dict) and str(item.get("source_ref", "")).strip()
    }

    requirements = plan.get("capture_requirements")
    if not isinstance(requirements, list) or not requirements:
        return errors + ["CAPTURE_REQUIREMENTS_REQUIRED"]

    capture_ids: set[str] = set()
    covered_groups: set[str] = set()
    for item in requirements:
        if not isinstance(item, dict):
            errors.append("CAPTURE_REQUIREMENT_ENTRY_INVALID")
            continue

        capture_id = str(item.get("capture_id", "")).strip()
        if not capture_id:
            errors.append("CAPTURE_ID_REQUIRED")
        elif capture_id in capture_ids:
            errors.append(f"DUPLICATE_CAPTURE_ID:{capture_id}")
        capture_ids.add(capture_id)

        groups = item.get("field_groups")
        if not isinstance(groups, list) or not groups:
            errors.append(f"CAPTURE[{capture_id or '?'}]:FIELD_GROUPS_REQUIRED")
            groups = []
        elif len(groups) != len(set(groups)):
            errors.append(f"CAPTURE[{capture_id}]:FIELD_GROUPS_DUPLICATE")

        for group in groups:
            if group not in REQUIRED_COMPANY_FIELD_GROUPS:
                errors.append(f"CAPTURE[{capture_id or '?'}]:FIELD_GROUP_INVALID:{group}")
            else:
                covered_groups.add(group)

        source_ref = str(item.get("source_ref", "")).strip()
        source = registry_by_ref.get(source_ref)
        if source is None:
            errors.append(f"CAPTURE[{capture_id or '?'}]:SOURCE_REF_UNKNOWN:{source_ref}")

        pit_basis = item.get("pit_basis")
        if pit_basis not in PIT_BASIS_TO_CAPABILITY:
            errors.append(f"CAPTURE[{capture_id or '?'}]:PIT_BASIS_INVALID")
        elif source is not None:
            capability = str(source.get("pit_capability", ""))
            if capability not in PIT_BASIS_TO_CAPABILITY[pit_basis]:
                errors.append(
                    f"CAPTURE[{capture_id or '?'}]:PIT_CAPABILITY_MISMATCH:{pit_basis}:{capability}"
                )

        if item.get("required") is not True:
            errors.append(f"CAPTURE[{capture_id or '?'}]:REQUIRED_MUST_BE_TRUE")
        if item.get("exact_bytes_required") is not True:
            errors.append(f"CAPTURE[{capture_id or '?'}]:EXACT_BYTES_REQUIRED")
        if item.get("status") != "PENDING_RAW":
            errors.append(f"CAPTURE[{capture_id or '?'}]:STATUS_INVALID")

    missing_groups = sorted(set(REQUIRED_COMPANY_FIELD_GROUPS) - covered_groups)
    if missing_groups:
        errors.append("REQUIRED_FIELD_GROUPS_UNCOVERED:" + ",".join(missing_groups))

    audit = plan.get("audit") or {}
    body = {key: value for key, value in plan.items() if key != "audit"}
    if audit.get("plan_sha256") != _sha_json(body):
        errors.append("PLAN_HASH_MISMATCH")

    return errors


__all__ = ["PIT_BASIS_TO_CAPABILITY", "validate_company_source_capture_plan"]
