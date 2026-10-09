from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .evidence_contract import assert_pit, validate_evidence_record

REQUIRED_COMPANY_FIELD_GROUPS = (
    "security_identity",
    "market_price",
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
    "trust_governance_events",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _resolve_contained_path(root: Path, relative_path: str) -> Path | None:
    root_resolved = root.resolve()
    if not root_resolved.is_dir():
        return None
    path = (root_resolved / relative_path).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError:
        return None
    return path


def verify_raw_artifact(root: Path, declaration: Mapping[str, Any]) -> dict[str, Any]:
    relative_path = str(declaration.get("relative_path", "")).strip()
    expected_sha256 = str(declaration.get("expected_sha256", "")).strip()
    expected_size = declaration.get("expected_size_bytes")
    if not relative_path or not expected_sha256 or not isinstance(expected_size, int):
        return {
            "status": "BLOCKED",
            "reason": "RAW_ARTIFACT_DECLARATION_INCOMPLETE",
            "relative_path": relative_path,
        }

    path = _resolve_contained_path(root, relative_path)
    if path is None:
        return {
            "status": "BLOCKED",
            "reason": "RAW_ARTIFACT_PATH_ESCAPE",
            "relative_path": relative_path,
            "size_bytes": None,
            "sha256": None,
        }
    if not path.is_file():
        return {
            "status": "BLOCKED",
            "reason": "RAW_ARTIFACT_MISSING",
            "relative_path": relative_path,
            "size_bytes": None,
            "sha256": None,
        }

    size = path.stat().st_size
    sha256 = _sha_bytes(path)
    exact = size == expected_size and sha256 == expected_sha256
    return {
        "status": "PASS" if exact else "BLOCKED",
        "reason": "EXACT_BYTES_VERIFIED" if exact else "EXACT_BYTES_MISMATCH",
        "relative_path": relative_path,
        "size_bytes": size,
        "sha256": sha256,
        "expected_size_bytes": expected_size,
        "expected_sha256": expected_sha256,
        "size_match": size == expected_size,
        "sha256_match": sha256 == expected_sha256,
    }


def validate_company_evidence_manifest(
    manifest: Any,
    *,
    raw_root: Path | None = None,
    require_raw_verification: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["COMPANY_EVIDENCE_TYPE:manifest must be an object"]

    required = (
        "schema_version", "case_id", "market", "symbol", "company",
        "cutoff_date", "required_field_groups", "evidence", "raw_artifacts", "audit",
    )
    for field in required:
        if field not in manifest:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors

    if manifest["schema_version"] != "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1":
        errors.append("VERSION_INVALID")
    if manifest["market"] not in {"CN-A", "HK"}:
        errors.append("MARKET_INVALID")

    groups = manifest.get("required_field_groups")
    if not isinstance(groups, list) or not groups:
        errors.append("FIELD_GROUPS_REQUIRED")
        groups = []
    if len(groups) != len(set(groups)):
        errors.append("FIELD_GROUPS_DUPLICATE")
    if any(group not in REQUIRED_COMPANY_FIELD_GROUPS for group in groups):
        errors.append("FIELD_GROUP_INVALID")

    evidence = manifest.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("EVIDENCE_REQUIRED")
        evidence = []

    evidence_ids: set[str] = set()
    covered_groups: set[str] = set()
    for item in evidence:
        item_errors = validate_evidence_record(item)
        errors.extend(f"EVIDENCE[{item.get('evidence_id', '?')}]:{x}" for x in item_errors)
        evidence_id = str(item.get("evidence_id", "")).strip()
        if str(item.get("subject_id", "")).strip() != str(manifest["case_id"]).strip():
            errors.append(f"EVIDENCE[{evidence_id or '?'}]:SUBJECT_CASE_MISMATCH")
        if evidence_id in evidence_ids and evidence_id:
            errors.append(f"DUPLICATE_EVIDENCE_ID:{evidence_id}")
        evidence_ids.add(evidence_id)
        field_id = str(item.get("field_id", ""))
        pit_passed = False
        if evidence_id:
            try:
                assert_pit(item, manifest["cutoff_date"])
                pit_passed = True
            except ValueError as exc:
                errors.append(f"EVIDENCE[{evidence_id}]:PIT:{exc}")
        # Group coverage is a permission-bearing conclusion. UNKNOWN, BLOCKED,
        # structurally invalid, or non-ADMITTED records cannot satisfy it.
        if (
            "." in field_id
            and not item_errors
            and evidence_id
            and str(item.get("subject_id", "")).strip() == str(manifest["case_id"]).strip()
            and item.get("status") == "ADMITTED"
            and item.get("provenance_class") != "UNKNOWN"
            and pit_passed
        ):
            covered_groups.add(field_id.split(".", 1)[0])

    missing_groups = sorted(set(groups) - covered_groups)
    if missing_groups:
        errors.append("REQUIRED_FIELD_GROUPS_UNCOVERED:" + ",".join(missing_groups))

    raw_artifacts = manifest.get("raw_artifacts")
    if not isinstance(raw_artifacts, list):
        errors.append("RAW_ARTIFACTS_REQUIRED")
        raw_artifacts = []

    declared_ids: set[str] = set()
    for declaration in raw_artifacts:
        if not isinstance(declaration, dict):
            errors.append("RAW_ARTIFACT_ENTRY_INVALID")
            continue
        evidence_id = str(declaration.get("evidence_id", "")).strip()
        if evidence_id in declared_ids and evidence_id:
            errors.append(f"DUPLICATE_RAW_ARTIFACT_EVIDENCE_ID:{evidence_id}")
        declared_ids.add(evidence_id)
        if evidence_id and evidence_id not in evidence_ids:
            errors.append(f"RAW_ARTIFACT_WITHOUT_EVIDENCE:{evidence_id}")
        matching = next(
            (
                item
                for item in evidence
                if str(item.get("evidence_id", "")).strip() == evidence_id
            ),
            None,
        )
        if (
            matching is not None
            and str(declaration.get("expected_sha256", "")).strip()
            != str(matching.get("content_sha256", "")).strip()
        ):
            errors.append(f"RAW_ARTIFACT[{evidence_id}]:EVIDENCE_HASH_MISMATCH")
        if require_raw_verification:
            if raw_root is None:
                errors.append("RAW_VERIFICATION_ROOT_REQUIRED")
            else:
                result = verify_raw_artifact(raw_root, declaration)
                if result["status"] != "PASS":
                    errors.append(f"RAW_ARTIFACT[{evidence_id}]:{result['reason']}")

    if require_raw_verification and evidence_ids != declared_ids:
        missing = sorted(evidence_ids - declared_ids)
        if missing:
            errors.append("EVIDENCE_WITHOUT_RAW_ARTIFACT:" + ",".join(missing))

    audit = manifest.get("audit") or {}
    body = {
        key: value
        for key, value in manifest.items()
        if key not in {"audit", "status", "validation_errors"}
    }
    if audit.get("manifest_sha256") != _sha_json(body):
        errors.append("MANIFEST_HASH_MISMATCH")

    return errors


def build_company_evidence_manifest(
    *,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: str,
    evidence: list[dict[str, Any]],
    raw_artifacts: list[dict[str, Any]],
    required_field_groups: list[str] | None = None,
    raw_root: Path | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "IIOS-COMPANY-EVIDENCE-MANIFEST-0.1",
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "company": company,
        "cutoff_date": cutoff_date,
        "required_field_groups": required_field_groups or list(REQUIRED_COMPANY_FIELD_GROUPS),
        "evidence": evidence,
        "raw_artifacts": raw_artifacts,
    }
    manifest["audit"] = {"manifest_sha256": _sha_json(manifest)}
    errors = validate_company_evidence_manifest(
        manifest,
        raw_root=raw_root,
        require_raw_verification=True,
    )
    manifest["status"] = "PASS" if not errors else "BLOCKED"
    manifest["validation_errors"] = errors
    return manifest


__all__ = [
    "REQUIRED_COMPANY_FIELD_GROUPS",
    "verify_raw_artifact",
    "validate_company_evidence_manifest",
    "build_company_evidence_manifest",
]
