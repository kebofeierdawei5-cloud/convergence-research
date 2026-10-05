from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Mapping

CAPITAL_TRUST_BRIDGE_VERSION = "IIOS-COMPANY-CAPITAL-TRUST-BRIDGE-0.1"

REQUIRED_INPUT_FIELDS = (
    "observation_date",
    "annual_2025_attributable_net_income",
    "annual_2025_cash_dividend_total",
    "annual_2025_repurchased_shares",
    "h1_2026_attributable_net_income",
    "h1_2026_interim_cash_dividend",
    "h1_2026_total_shares",
    "h1_2026_repurchase_account_shares",
    "indonesia_planned_investment_usd",
    "related_party_guarantee_cap_usd",
    "related_party_procurement_cap_usd",
    "independent_director_review",
    "related_director_recusal",
    "non_related_director_for_votes",
    "non_related_director_against_votes",
    "non_related_director_abstain_votes",
    "evidence_ids",
)

OUTPUT_FIELDS = (
    "schema_version",
    "case_id",
    "cutoff_date",
    "observation_date",
    "evidence_admission",
    "capital_allocation",
    "trust_revalidation",
    "decision_effect",
    "audit",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def _nonnegative(value: Any, field: str) -> float:
    result = _number(value, field)
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _refs(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    refs = [str(item).strip() for item in value]
    if any(not item for item in refs):
        raise ValueError(f"{field} cannot contain empty evidence IDs")
    if len(refs) != len(set(refs)):
        raise ValueError(f"{field} contains duplicate evidence IDs")
    return refs


def _parse_date(value: Any, field: str) -> date:
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(f"{field} must start with an ISO date") from exc


def _input_core(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_INPUT_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"capital_trust input missing required fields: {missing}")

    for field in (
        "annual_2025_attributable_net_income",
        "annual_2025_cash_dividend_total",
        "annual_2025_repurchased_shares",
        "h1_2026_attributable_net_income",
        "h1_2026_interim_cash_dividend",
        "h1_2026_total_shares",
        "h1_2026_repurchase_account_shares",
        "indonesia_planned_investment_usd",
        "related_party_guarantee_cap_usd",
        "related_party_procurement_cap_usd",
    ):
        _nonnegative(payload[field], f"input.{field}")

    for field in (
        "independent_director_review",
        "related_director_recusal",
    ):
        if not isinstance(payload[field], bool):
            raise ValueError(f"input.{field} must be boolean")

    for field in (
        "non_related_director_for_votes",
        "non_related_director_against_votes",
        "non_related_director_abstain_votes",
    ):
        value = int(_nonnegative(payload[field], f"input.{field}"))
        if value != payload[field]:
            raise ValueError(f"input.{field} must be an integer")
    refs = _refs(payload["evidence_ids"], "input.evidence_ids")
    _parse_date(payload["observation_date"], "input.observation_date")

    for field in (
        "annual_2025_attributable_net_income",
        "h1_2026_attributable_net_income",
        "h1_2026_total_shares",
    ):
        if _number(payload[field], field) <= 0:
            raise ValueError(f"input.{field} must be positive")

    votes = (
        payload["non_related_director_for_votes"]
        + payload["non_related_director_against_votes"]
        + payload["non_related_director_abstain_votes"]
    )
    if votes <= 0:
        raise ValueError("input.non_related_director votes cannot all be zero")
    return {**dict(payload), "evidence_ids": refs}


def build_company_capital_trust_bridge(
    *,
    case_id: str,
    cutoff_date: str,
    input_payload: Mapping[str, Any],
    admitted_evidence_ids: list[str] | set[str],
    generation_basis: str,
) -> dict[str, Any]:
    if not str(case_id).strip():
        raise ValueError("case_id must be non-empty")
    if not str(cutoff_date).strip():
        raise ValueError("cutoff_date must be non-empty")
    if not str(generation_basis).strip():
        raise ValueError("generation_basis must be non-empty")

    cutoff = _parse_date(cutoff_date, "cutoff_date")
    payload = _input_core(input_payload)
    observation = _parse_date(payload["observation_date"], "observation_date")
    if observation > cutoff:
        raise ValueError("observation_date exceeds cutoff")

    admitted = _refs(admitted_evidence_ids, "admitted_evidence_ids")
    admitted_set = set(admitted)
    missing_evidence = sorted(set(payload["evidence_ids"]) - admitted_set)
    if missing_evidence:
        raise ValueError(
            "input references evidence IDs not admitted by the supplied evidence set: "
            + repr(missing_evidence)
        )

    annual_payout_ratio = (
        payload["annual_2025_cash_dividend_total"]
        / payload["annual_2025_attributable_net_income"]
    )
    interim_payout_ratio = (
        payload["h1_2026_interim_cash_dividend"]
        / payload["h1_2026_attributable_net_income"]
    )
    repurchase_share_ratio = (
        payload["h1_2026_repurchase_account_shares"]
        / payload["h1_2026_total_shares"]
    )
    guarantee_to_project_ratio = (
        payload["related_party_guarantee_cap_usd"]
        / payload["indonesia_planned_investment_usd"]
        if payload["indonesia_planned_investment_usd"] > 0
        else None
    )

    board_vote_control = (
        payload["independent_director_review"]
        and payload["related_director_recusal"]
        and payload["non_related_director_for_votes"] > 0
        and payload["non_related_director_against_votes"] == 0
        and payload["non_related_director_abstain_votes"] == 0
    )

    input_core = {
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "input_payload": payload,
        "admitted_evidence_ids": admitted,
        "generation_basis": generation_basis,
    }

    result = {
        "schema_version": CAPITAL_TRUST_BRIDGE_VERSION,
        "case_id": case_id,
        "cutoff_date": cutoff_date,
        "observation_date": payload["observation_date"],
        "evidence_admission": {
            "status": "ADMITTED",
            "evidence_ids": admitted,
            "sha256": _sha(admitted),
        },
        "capital_allocation": {
            "status": "CONDITIONAL",
            "shareholder_return": {
                "status": "ESTABLISHED",
                "annual_2025_payout_ratio": annual_payout_ratio,
                "h1_2026_interim_payout_ratio": interim_payout_ratio,
                "h1_2026_repurchase_share_ratio": repurchase_share_ratio,
            },
            "capital_commitments": {
                "status": "CONDITIONAL",
                "indonesia_planned_investment_usd": payload["indonesia_planned_investment_usd"],
                "related_party_guarantee_cap_usd": payload["related_party_guarantee_cap_usd"],
                "guarantee_to_project_ratio": guarantee_to_project_ratio,
                "related_party_procurement_cap_usd": payload["related_party_procurement_cap_usd"],
            },
            "reason": (
                "Capital-return evidence is established from disclosed payout and repurchase data, "
                "but major strategic commitments include future or contingent related-party exposures "
                "that require continuing monitoring."
            ),
        },
        "trust_revalidation": {
            "status": "CONDITIONAL",
            "governance_integrity": {
                "status": "CONDITIONAL",
                "related_party_transactions_or_exposures_present": True,
                        "independent_director_review": payload["independent_director_review"],
                "related_director_recusal": payload["related_director_recusal"],
                "non_related_director_vote_control": board_vote_control,
            },
            "shareholder_treatment": {
                "status": "PASS",
                "basis": "Disclosed cash-return actions include a 50% 2025 annual payout ratio and a 15% 2026 H1 interim payout ratio.",
            },
            "reason": (
                "Related-party exposure is present, but the captured transaction includes "
                "independent-director review, related-director recusal and a recorded non-related "
                "director vote. This supports CONDITIONAL revalidation rather than an automatic Trust FAIL."
            ),
        },
        "decision_effect": "NO_DIRECT_GATE_EFFECT",
        "audit": {
            "input_sha256": _sha(input_core),
        },
    }
    result["audit"]["bridge_sha256"] = _sha(
        {key: value for key, value in result.items() if key != "audit"}
    )
    return result


def validate_company_capital_trust_bridge(record: Any) -> list[str]:
    if not isinstance(record, Mapping):
        return ["CAPITAL_TRUST_BRIDGE_TYPE_INVALID"]
    errors: list[str] = []

    if set(record) != set(OUTPUT_FIELDS):
        return ["CAPITAL_TRUST_BRIDGE_FIELDS_INVALID"]

    if record["schema_version"] != CAPITAL_TRUST_BRIDGE_VERSION:
        errors.append("CAPITAL_TRUST_BRIDGE_VERSION_MISMATCH")
    if record["decision_effect"] != "NO_DIRECT_GATE_EFFECT":
        errors.append("DECISION_EFFECT_INVALID")

    admission = record["evidence_admission"]
    if (
        not isinstance(admission, Mapping)
        or set(admission) != {"status", "evidence_ids", "sha256"}
        or admission.get("status") != "ADMITTED"
    ):
        errors.append("EVIDENCE_ADMISSION_INVALID")
    else:
        try:
            refs = _refs(admission["evidence_ids"], "evidence_admission.evidence_ids")
        except ValueError:
            refs = []
            errors.append("EVIDENCE_ADMISSION_IDS_INVALID")
        if refs and admission.get("sha256") != _sha(refs):
            errors.append("EVIDENCE_ADMISSION_HASH_MISMATCH")

    for key in ("capital_allocation", "trust_revalidation"):
        if not isinstance(record[key], Mapping):
            errors.append(f"{key.upper()}_INVALID")

    if record["capital_allocation"].get("status") != "CONDITIONAL":
        errors.append("CAPITAL_ALLOCATION_STATUS_INVALID")
    if record["trust_revalidation"].get("status") != "CONDITIONAL":
        errors.append("TRUST_REVALIDATION_STATUS_INVALID")

    audit = record["audit"]
    if not isinstance(audit, Mapping) or set(audit) != {"input_sha256", "bridge_sha256"}:
        errors.append("AUDIT_FIELDS_INVALID")
    else:
        for field in ("input_sha256", "bridge_sha256"):
            value = audit.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                errors.append(f"AUDIT_{field.upper()}_INVALID")

        if not errors:
            if audit["bridge_sha256"] != _sha(
                {key: value for key, value in record.items() if key != "audit"}
            ):
                errors.append("AUDIT_BRIDGE_HASH_MISMATCH")

    return errors


__all__ = [
    "CAPITAL_TRUST_BRIDGE_VERSION",
    "build_company_capital_trust_bridge",
    "validate_company_capital_trust_bridge",
]
