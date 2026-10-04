from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from .research_intake import validate_research_case
from .value_core import scan_company_value_core

CORE_VERSION = "IIOS-COMPANY-ECONOMIC-CORE-0.1"
ASSESSMENT_VERSION = "IIOS-COMPANY-ECONOMIC-ASSESSMENT-0.1"

VALID_EVIDENCE_STATUS = {"ADMITTED", "CONDITIONAL", "UNKNOWN", "BLOCKED"}
VALID_PROVENANCE = {
    "SOURCE_VINTAGE_VERIFIED",
    "EVENT_PUBLICATION_VERIFIED",
    "VENDOR_PIT_QUERY",
    "DERIVED_FROM_ADMITTED_RAW",
    "UNKNOWN",
}
VALID_ASSESSMENT_STATUS = {"PASS", "CONDITIONAL", "UNKNOWN", "BLOCKED"}
REALITY_DOMAINS = {
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
}
TRUST_DIMENSIONS = (
    "identity",
    "disclosure_integrity",
    "governance_integrity",
    "shareholder_treatment",
)
QUALITY_DIMENSIONS = (
    "competitive_advantage",
    "incremental_return_on_capital",
    "earnings_quality",
    "cash_flow_conversion",
    "balance_sheet_resilience",
    "reinvestment_runway",
)
DOMAIN_EVIDENCE_GROUPS = {
    "corporate_disclosures": ("corporate_disclosures",),
    "business_reality": ("business_reality",),
    "financial_reality": ("financial_reality",),
    "capital_structure": ("capital_structure",),
}
TRUST_EVIDENCE_GROUPS = {
    "identity": ("security_identity",),
    "disclosure_integrity": ("corporate_disclosures",),
    "governance_integrity": ("trust_governance_events",),
    "shareholder_treatment": ("trust_governance_events",),
}
QUALITY_EVIDENCE_GROUPS = {
    "competitive_advantage": ("business_reality", "corporate_disclosures"),
    "incremental_return_on_capital": ("financial_reality",),
    "earnings_quality": ("financial_reality", "corporate_disclosures"),
    "cash_flow_conversion": ("financial_reality",),
    "balance_sheet_resilience": ("financial_reality", "capital_structure"),
    "reinvestment_runway": ("business_reality", "financial_reality"),
}

ECONOMIC_VARIABLES = {
    "volume",
    "price",
    "product_mix",
    "revenue",
    "gross_margin",
    "operating_margin",
    "opex",
    "tax",
    "working_capital",
    "capex",
    "depreciation_amortization",
    "fcf",
    "incremental_roic",
    "net_debt",
    "share_count",
    "payout",
    "other",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse_temporal(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO date/time string")
    raw = value.strip()
    try:
        if len(raw) == 10:
            d = date.fromisoformat(raw)
            return datetime(d.year, d.month, d.day, tzinfo=timezone(timedelta(hours=8)))
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return result


def _pit_qualified(evidence: dict[str, Any], cutoff_date: str) -> bool:
    known = _parse_temporal(evidence["known_at"], "known_at")
    cutoff = _parse_temporal(cutoff_date, "cutoff")
    return known <= cutoff


def _date_leq(value: Any, cutoff_date: str, field: str) -> None:
    observed = date.fromisoformat(str(value))
    cutoff = date.fromisoformat(cutoff_date)
    if observed > cutoff:
        raise ValueError(f"{field} cannot be after cutoff")


def _evidence_field_matches(evidence: dict[str, Any], field_group: str) -> bool:
    field_id = str(evidence.get("field_id", ""))
    return field_id == field_group or field_id.startswith(field_group + ".")


def _validate_evidence_record(evidence: Any, index: int) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise ValueError(f"evidence[{index}] must be an object")
    required = (
        "evidence_id",
        "subject_id",
        "field_id",
        "claim_type",
        "known_at",
        "retrieved_at",
        "source_ref",
        "artifact_id",
        "content_sha256",
        "exact_bytes",
        "provenance_class",
        "status",
    )
    missing = [field for field in required if field not in evidence]
    if missing:
        raise ValueError(f"evidence[{index}] missing required fields: {missing}")
    if evidence["status"] not in VALID_EVIDENCE_STATUS:
        raise ValueError(f"evidence[{index}].status unsupported")
    if evidence["provenance_class"] not in VALID_PROVENANCE:
        raise ValueError(f"evidence[{index}].provenance_class unsupported")
    for field in ("evidence_id", "subject_id", "field_id", "claim_type", "source_ref", "artifact_id"):
        if not str(evidence[field]).strip():
            raise ValueError(f"evidence[{index}].{field} must be non-empty")
    if evidence["status"] != "ADMITTED":
        raise ValueError(
            f"evidence[{index}].status must be ADMITTED for CORE-02: "
            f"{evidence['status']}"
        )
    if evidence["exact_bytes"] is not True:
        raise ValueError(f"evidence[{index}].exact_bytes must be true")
    sha = evidence["content_sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError(f"evidence[{index}].content_sha256 must be lowercase SHA-256")
    _parse_temporal(evidence["known_at"], f"evidence[{index}].known_at")
    retrieved = _parse_temporal(evidence["retrieved_at"], f"evidence[{index}].retrieved_at")
    known = _parse_temporal(evidence["known_at"], f"evidence[{index}].known_at")
    if retrieved < known:
        raise ValueError(f"evidence[{index}].retrieved_at cannot precede known_at")
    published = evidence.get("published_at")
    if published:
        published_dt = _parse_temporal(published, f"evidence[{index}].published_at")
        if published_dt > known:
            raise ValueError(f"evidence[{index}].published_at cannot exceed known_at")
    effective_from = evidence.get("effective_from")
    effective_to = evidence.get("effective_to")
    if effective_to and not effective_from:
        raise ValueError(f"evidence[{index}].effective_to requires effective_from")
    if effective_from and effective_to:
        start = _parse_temporal(effective_from, f"evidence[{index}].effective_from")
        end = _parse_temporal(effective_to, f"evidence[{index}].effective_to")
        if end <= start:
            raise ValueError(f"evidence[{index}].effective_to must be after effective_from")
    if evidence["provenance_class"] == "DERIVED_FROM_ADMITTED_RAW":
        parents = evidence.get("parents")
        transform = evidence.get("transformation")
        if not isinstance(parents, list) or not parents or any(not str(x).strip() for x in parents):
            raise ValueError(f"evidence[{index}].parents are required for derived evidence")
        if not isinstance(transform, dict) or transform.get("type") != "DERIVED":
            raise ValueError(f"evidence[{index}].transformation.type=DERIVED is required")
    return dict(evidence)


def _admit_evidence(case: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    case_errors = validate_research_case(case)
    if case_errors:
        raise ValueError("CORE-01 case invalid: " + "; ".join(case_errors))
    case_id = case["case_id"]
    cutoff = case["temporal_scope"]["cutoff_date"]
    raw = case["evidence"]
    if not raw:
        raise ValueError("CORE-02 requires admitted company evidence; case.evidence is empty")

    admitted: list[dict[str, Any]] = []
    ids: set[str] = set()
    for i, record in enumerate(raw):
        evidence = _validate_evidence_record(record, i)
        evidence_id = str(evidence["evidence_id"]).strip()
        if not evidence_id:
            raise ValueError(f"evidence[{i}].evidence_id must be non-empty")
        if evidence_id in ids:
            raise ValueError(f"duplicate evidence_id: {evidence_id}")
        ids.add(evidence_id)
        if evidence["subject_id"] != case_id:
            raise ValueError(
                f"evidence[{i}].subject_id must equal case_id {case_id}"
            )
        if not _pit_qualified(evidence, cutoff):
            raise ValueError(
                f"evidence[{i}] is not PIT-qualified: known_at exceeds cutoff"
            )
        admitted.append(evidence)

    for evidence in admitted:
        if evidence["provenance_class"] == "DERIVED_FROM_ADMITTED_RAW":
            unknown_parents = sorted(set(evidence["parents"]) - ids)
            if unknown_parents:
                raise ValueError(
                    f"derived evidence {evidence['evidence_id']} references unknown parents: {unknown_parents}"
                )

    missing_groups = []
    for item in case["evidence_plan"]:
        group = item["field_group"]
        if item.get("required_for_admission") and not any(
            _evidence_field_matches(e, group) for e in admitted
        ):
            missing_groups.append(group)
    if missing_groups:
        raise ValueError(
            "required evidence domains missing: " + ", ".join(missing_groups)
        )

    manifest = [
        {
            "evidence_id": e["evidence_id"],
            "field_id": e["field_id"],
            "claim_type": e["claim_type"],
            "known_at": e["known_at"],
            "retrieved_at": e["retrieved_at"],
            "source_ref": e["source_ref"],
            "artifact_id": e["artifact_id"],
            "content_sha256": e["content_sha256"],
            "provenance_class": e["provenance_class"],
        }
        for e in admitted
    ]
    manifest.sort(key=lambda x: x["evidence_id"])
    return admitted, {
        "status": "ADMITTED",
        "count": len(admitted),
        "evidence_ids": [x["evidence_id"] for x in manifest],
        "by_field_group": {
            group: [x["evidence_id"] for x in manifest if _evidence_field_matches(x, group)]
            for group, _purpose, _priority, _sources in _intake_plan(case)
        },
        "sha256": _sha(manifest),
    }


def _intake_plan(case: dict[str, Any]) -> list[tuple[str, str, str, tuple[str, ...]]]:
    return [
        (
            str(item["field_group"]),
            str(item.get("purpose", "")),
            str(item.get("priority", "")),
            tuple(item.get("source_classes", [])),
        )
        for item in case["evidence_plan"]
    ]


def _has_group_evidence(refs: list[str], evidence_by_id: dict[str, dict[str, Any]], groups: tuple[str, ...]) -> bool:
    return any(
        _evidence_field_matches(evidence_by_id[evidence_id], group)
        for evidence_id in refs
        for group in groups
    )


def _require_evidence_refs(
    refs: Any,
    evidence_ids: set[str],
    context: str,
) -> list[str]:
    if not isinstance(refs, list) or not refs:
        raise ValueError(f"{context}.evidence_ids must be a non-empty list")
    normalized = [str(x).strip() for x in refs]
    if any(not x for x in normalized):
        raise ValueError(f"{context}.evidence_ids cannot contain empty IDs")
    unknown = sorted(set(normalized) - evidence_ids)
    if unknown:
        raise ValueError(f"{context} references unknown evidence IDs: {unknown}")
    return normalized


def _validate_reality(
    reality: Any,
    evidence_ids: set[str],
    evidence_by_id: dict[str, dict[str, Any]],
    cutoff: str,
) -> dict[str, Any]:
    if not isinstance(reality, dict):
        raise ValueError("reality must be an object")
    facts = reality.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("reality.facts must be a non-empty list")

    normalized = []
    domains: set[str] = set()
    for i, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ValueError(f"reality.facts[{i}] must be an object")
        for field in ("fact_id", "domain", "field_id", "value", "unit", "basis", "observation_date", "evidence_ids", "status"):
            if field not in fact:
                raise ValueError(f"reality.facts[{i}].{field} is required")
        domain = str(fact["domain"]).strip()
        if domain not in REALITY_DOMAINS:
            raise ValueError(f"reality.facts[{i}].domain unsupported: {domain}")
        status = str(fact["status"]).strip().upper()
        if status not in {"ESTABLISHED", "CONDITIONAL", "UNKNOWN"}:
            raise ValueError(f"reality.facts[{i}].status unsupported: {status}")
        refs = _require_evidence_refs(fact["evidence_ids"], evidence_ids, f"reality.facts[{i}]")
        if not _has_group_evidence(refs, evidence_by_id, DOMAIN_EVIDENCE_GROUPS[domain]):
            raise ValueError(
                f"reality.facts[{i}] evidence does not cover domain {domain}"
            )
        _date_leq(fact["observation_date"], cutoff, f"reality.facts[{i}].observation_date")
        fact_id = str(fact["fact_id"]).strip()
        field_id = str(fact["field_id"]).strip()
        if not fact_id or not field_id:
            raise ValueError(f"reality.facts[{i}].fact_id/field_id must be non-empty")
        normalized.append({
            "fact_id": fact_id,
            "domain": domain,
            "field_id": field_id,
            "value": fact["value"],
            "unit": str(fact["unit"]),
            "basis": str(fact["basis"]),
            "observation_date": str(fact["observation_date"]),
            "evidence_ids": refs,
            "status": status,
        })
        domains.add(domain)

    missing = sorted(REALITY_DOMAINS - domains)
    if missing:
        raise ValueError("reality coverage missing domains: " + ", ".join(missing))
    fact_ids = [x["fact_id"] for x in normalized]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("reality.fact_id must be unique")

    overall = (
        "UNKNOWN"
        if any(x["status"] == "UNKNOWN" for x in normalized)
        else "CONDITIONAL"
        if any(x["status"] == "CONDITIONAL" for x in normalized)
        else "ESTABLISHED"
    )
    return {
        "status": overall,
        "fact_count": len(normalized),
        "covered_domains": sorted(domains),
        "facts": normalized,
    }


def _validate_assessment(
    payload: Any,
    key: str,
    dimensions: tuple[str, ...],
    evidence_ids: set[str],
    evidence_by_id: dict[str, dict[str, Any]],
    evidence_groups: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{key} must be an object")
    rows = payload.get("dimensions")
    if not isinstance(rows, list) or len(rows) != len(dimensions):
        raise ValueError(f"{key}.dimensions must contain exactly {len(dimensions)} rows")
    by_name = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{key}.dimensions[{i}] must be an object")
        for field in ("dimension", "status", "rationale", "evidence_ids"):
            if field not in row:
                raise ValueError(f"{key}.dimensions[{i}].{field} is required")
        dimension = str(row["dimension"]).strip()
        status = str(row["status"]).strip().upper()
        if dimension in by_name:
            raise ValueError(f"{key}.dimension duplicated: {dimension}")
        if dimension not in dimensions:
            raise ValueError(f"{key}.dimension unsupported: {dimension}")
        if status not in VALID_ASSESSMENT_STATUS:
            raise ValueError(f"{key}.{dimension}.status unsupported: {status}")
        if not str(row["rationale"]).strip():
            raise ValueError(f"{key}.{dimension}.rationale must be non-empty")
        refs = _require_evidence_refs(row["evidence_ids"], evidence_ids, f"{key}.{dimension}")
        if not _has_group_evidence(refs, evidence_by_id, evidence_groups[dimension]):
            raise ValueError(
                f"{key}.{dimension} evidence does not cover its required domain"
            )
        by_name[dimension] = {
            "dimension": dimension,
            "status": status,
            "rationale": str(row["rationale"]).strip(),
            "evidence_ids": refs,
        }
    missing = [x for x in dimensions if x not in by_name]
    if missing:
        raise ValueError(f"{key}.dimensions missing: {missing}")
    ordered = [by_name[x] for x in dimensions]
    aggregate = (
        "BLOCKED"
        if any(x["status"] == "BLOCKED" for x in ordered)
        else "CONDITIONAL"
        if any(x["status"] in {"CONDITIONAL", "UNKNOWN"} for x in ordered)
        else "PASS"
    )
    return {"status": aggregate, "dimensions": ordered}


def _validate_value_driver_ranking(
    rows: Any,
    evidence_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("value_driver_ranking must be a non-empty list")
    normalized = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"value_driver_ranking[{i}] must be an object")
        for field in ("driver_id", "name", "rank", "materiality", "mechanism", "economic_variables", "evidence_ids"):
            if field not in row:
                raise ValueError(f"value_driver_ranking[{i}].{field} is required")
        try:
            rank = int(row["rank"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"value_driver_ranking[{i}].rank must be integer") from exc
        variables = [str(v).strip() for v in row["economic_variables"]]
        if not variables or any(v not in ECONOMIC_VARIABLES for v in variables):
            raise ValueError(f"value_driver_ranking[{i}].economic_variables contains unsupported variable")
        materiality = str(row["materiality"]).strip().upper()
        if materiality not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError(f"value_driver_ranking[{i}].materiality unsupported")
        refs = _require_evidence_refs(row["evidence_ids"], evidence_ids, f"value_driver_ranking[{i}]")
        driver_id = str(row["driver_id"]).strip()
        name = str(row["name"]).strip()
        mechanism = str(row["mechanism"]).strip()
        if not driver_id or not name or not mechanism:
            raise ValueError(f"value_driver_ranking[{i}].driver_id/name/mechanism must be non-empty")
        normalized.append({
            "driver_id": driver_id,
            "name": name,
            "rank": rank,
            "materiality": materiality,
            "mechanism": mechanism,
            "economic_variables": variables,
            "evidence_ids": refs,
        })
    ranks = [x["rank"] for x in normalized]
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise ValueError("value_driver_ranking.rank must be contiguous starting at 1")
    driver_ids = [x["driver_id"] for x in normalized]
    if len(driver_ids) != len(set(driver_ids)):
        raise ValueError("value_driver_ranking.driver_id must be unique")
    if normalized[0]["materiality"] != "HIGH":
        raise ValueError("rank-1 value driver must be HIGH materiality")
    return sorted(normalized, key=lambda x: x["rank"])


def build_company_economic_core(
    case: dict[str, Any],
    reality: dict[str, Any],
    trust: dict[str, Any],
    quality: dict[str, Any],
    value_core: dict[str, Any],
    value_driver_ranking: list[dict[str, Any]],
    generated_at: Any | None = None,
) -> dict[str, Any]:
    admitted, manifest = _admit_evidence(case)
    evidence_ids = {x["evidence_id"] for x in admitted}
    evidence_by_id = {x["evidence_id"]: x for x in admitted}

    normalized_reality = _validate_reality(
        reality, evidence_ids, evidence_by_id, case["temporal_scope"]["cutoff_date"]
    )
    normalized_trust = _validate_assessment(
        trust, "trust", TRUST_DIMENSIONS, evidence_ids, evidence_by_id, TRUST_EVIDENCE_GROUPS
    )
    normalized_quality = _validate_assessment(
        quality, "quality", QUALITY_DIMENSIONS, evidence_ids, evidence_by_id, QUALITY_EVIDENCE_GROUPS
    )

    if not isinstance(value_core, dict):
        raise ValueError("value_core must be an object")
    value_nodes = value_core.get("nodes")
    if not isinstance(value_nodes, list) or not value_nodes:
        raise ValueError("value_core.nodes must be a non-empty list")
    for i, node in enumerate(value_nodes):
        refs = _require_evidence_refs(node.get("evidence_ids"), evidence_ids, f"value_core.nodes[{i}]")
        if not _has_group_evidence(refs, evidence_by_id, ("business_reality", "financial_reality", "corporate_disclosures")):
            raise ValueError(
                f"value_core.nodes[{i}] must reference business/financial/disclosure evidence"
            )
        if not str(node.get("assessment_basis", "")).strip():
            raise ValueError(f"value_core.nodes[{i}].assessment_basis is required")
    scanned_value_core = scan_company_value_core(value_core)

    drivers = _validate_value_driver_ranking(value_driver_ranking, evidence_ids)
    generated_dt = (
        datetime.now(timezone.utc)
        if generated_at is None
        else datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    )
    if generated_dt.tzinfo is None:
        raise ValueError("generated_at must include an explicit timezone")

    overall_status = (
        "BLOCKED"
        if normalized_trust["status"] == "BLOCKED"
        or normalized_quality["status"] == "BLOCKED"
        else "CONDITIONAL"
        if normalized_reality["status"] != "ESTABLISHED"
        or normalized_trust["status"] != "PASS"
        or normalized_quality["status"] != "PASS"
        else "PASS"
    )

    core_without_audit = {
        "schema_version": CORE_VERSION,
        "assessment_version": ASSESSMENT_VERSION,
        "case_id": case["case_id"],
        "market": case["request"]["market"],
        "symbol": case["request"]["symbol"],
        "as_of_date": case["temporal_scope"]["as_of_date"],
        "cutoff_date": case["temporal_scope"]["cutoff_date"],
        "status": overall_status,
        "evidence_admission": manifest,
        "reality": normalized_reality,
        "trust": normalized_trust,
        "quality": normalized_quality,
        "value_core": scanned_value_core,
        "value_driver_ranking": drivers,
        "valuation_route": {
            "status": "CANDIDATE_SET_ONLY",
            "economic_profile": scanned_value_core["overall_economic_profile"],
            "candidate_models": scanned_value_core["model_route"]["candidate_models"],
            "model_router_suggestion": scanned_value_core["model_route"]["model_router_suggestion"],
            "selection_authority": "HUMAN",
        },
    }
    audit = {
        "input_sha256": _sha({
            "case": case,
            "reality": reality,
            "trust": trust,
            "quality": quality,
            "value_core": value_core,
            "value_driver_ranking": value_driver_ranking,
        }),
        "evidence_manifest_sha256": manifest["sha256"],
        "generated_at": generated_dt.astimezone(timezone.utc).isoformat(),
    }
    output = {**core_without_audit, "audit": audit}
    output["audit"]["core_sha256"] = _sha(core_without_audit)
    return output


def validate_company_economic_core(core: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(core, dict):
        return ["CORE_TYPE:must be an object"]
    required = (
        "schema_version",
        "assessment_version",
        "case_id",
        "market",
        "symbol",
        "as_of_date",
        "cutoff_date",
        "status",
        "evidence_admission",
        "reality",
        "trust",
        "quality",
        "value_core",
        "value_driver_ranking",
        "valuation_route",
        "audit",
    )
    for field in required:
        if field not in core:
            errors.append(f"MISSING:{field}")
    if errors:
        return errors
    if core["schema_version"] != CORE_VERSION:
        errors.append("CORE_VERSION:unsupported")
    if core["assessment_version"] != ASSESSMENT_VERSION:
        errors.append("ASSESSMENT_VERSION:unsupported")
    if core["status"] not in {"PASS", "CONDITIONAL", "BLOCKED"}:
        errors.append("CORE_STATUS:invalid")
    if not isinstance(core["evidence_admission"], dict):
        errors.append("EVIDENCE_ADMISSION_TYPE:invalid")
    if not isinstance(core["audit"], dict):
        errors.append("AUDIT_TYPE:invalid")
    else:
        for field in ("input_sha256", "evidence_manifest_sha256", "generated_at", "core_sha256"):
            if field not in core["audit"]:
                errors.append(f"AUDIT_MISSING:{field}")
        for field in ("input_sha256", "evidence_manifest_sha256", "core_sha256"):
            value = core["audit"].get(field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                errors.append(f"AUDIT_{field.upper()}:invalid")
        try:
            generated = _parse_temporal(core["audit"]["generated_at"], "audit.generated_at")
            if generated.tzinfo is None:
                errors.append("AUDIT_GENERATED_AT_NO_TIMEZONE")
        except (KeyError, ValueError) as exc:
            errors.append(f"AUDIT_GENERATED_AT_INVALID:{exc}")
    try:
        as_of = date.fromisoformat(str(core["as_of_date"]))
        cutoff = date.fromisoformat(str(core["cutoff_date"]))
        if as_of != cutoff:
            errors.append("TEMPORAL_SCOPE_MISMATCH")
        if as_of > date.today():
            errors.append("FUTURE_AS_OF")
    except ValueError:
        errors.append("DATE_INVALID")
    try:
        scan = core["value_core"]
        if scan.get("schema_version") != "IIOS-VALUE-CORE-SCAN-1.0":
            errors.append("VALUE_CORE_SCHEMA_VERSION_INVALID")
        drivers = core["value_driver_ranking"]
        ranks = [int(row["rank"]) for row in drivers]
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            errors.append("VALUE_DRIVER_RANKING_INVALID")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"VALUE_CORE_INVALID:{exc}")
    if not errors:
        core_without_audit = {k: v for k, v in core.items() if k != "audit"}
        if core["audit"]["core_sha256"] != _sha(core_without_audit):
            errors.append("AUDIT_CORE_HASH_MISMATCH")
    return errors


__all__ = [
    "CORE_VERSION",
    "ASSESSMENT_VERSION",
    "build_company_economic_core",
    "validate_company_economic_core",
]
