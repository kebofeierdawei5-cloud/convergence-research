from __future__ import annotations

"""Prepare a private, human-fillable C2 fact/use review packet.

This tool packages existing sanitized CI locator metadata for a separate reviewer.
It does not inspect private PDF bytes, decide rights, create signatures, or admit facts.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping


EXPECTED_CASE_ID = "RC-CN-A-002001-20261009"
EXPECTED_CUTOFF = "2026-10-09T00:00:00+08:00"
EXPECTED_FACT_COUNT = 13
REVIEW_PACKET_SCHEMA = "IIOS-C2-INDEPENDENT-FACT-USE-REVIEW-PACKET-0.1"
SOURCE_REPORT_RELATIVE = (
    "evidence/real_cases/RC-CN-A-002001-20261009/"
    "C2_P3_FACT_REVIEW_CI_RESULT_38126026797.json"
)
EXPECTED_WORKFLOW_RUN_ID = 38126026797
EXPECTED_WORKFLOW_HEAD_SHA = "dc402876288074745623eab10e67ed06252fd9ff"
EXPECTED_ARTIFACT_ZIP_SHA256 = "7d68870b2823c02f08c765fa9ed9fe015e4e47f592d8f0dc85b04f7e8245cc1e"
EXPECTED_ORIGINAL_REPORT_SHA256 = "6c8b261e9b666e9193627ef7334edc367148d998570e9c36bce577845c78a3f7"
SOURCE_URLS = {
    "SZSE-2026-H1-SUMMARY": (
        "https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/"
        "6d1ad0be-5e22-482b-a163-2ebb0b6d1d95.PDF"
    ),
    "SZSE-2026-H1-FULL": (
        "https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/"
        "83165436-1015-4d77-919c-97c8cce0c67d.PDF"
    ),
    "SZSE-2026-BUYBACK-PLAN": (
        "https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-24/"
        "53248225-c2cf-45cf-a0fd-a6c9fee4f267.PDF"
    ),
}


class ReviewPacketError(ValueError):
    pass


def _read_report(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser()
    if target.is_symlink() or not target.is_file():
        raise ReviewPacketError("SOURCE_REVIEW_REPORT_MUST_BE_REGULAR_FILE")
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewPacketError("SOURCE_REVIEW_REPORT_INVALID_JSON") from exc
    if not isinstance(document, dict):
        raise ReviewPacketError("SOURCE_REVIEW_REPORT_MUST_BE_OBJECT")
    if document.get("archive_record_schema") != "IIOS-C2-P3-CI-RESULT-ARCHIVE-0.1":
        raise ReviewPacketError("SOURCE_REVIEW_REPORT_SCHEMA_MISMATCH")
    return document


def build_review_packet(document: Mapping[str, Any], *, source_report_ref: str) -> dict[str, Any]:
    result = document.get("result")
    provenance = document.get("ci_provenance")
    if not isinstance(result, Mapping) or not isinstance(provenance, Mapping):
        raise ReviewPacketError("SOURCE_REVIEW_REPORT_RESULT_OR_PROVENANCE_MISSING")
    if (
        provenance.get("workflow_run_id") != EXPECTED_WORKFLOW_RUN_ID
        or provenance.get("workflow_head_sha") != EXPECTED_WORKFLOW_HEAD_SHA
        or provenance.get("downloaded_artifact_zip_sha256") != EXPECTED_ARTIFACT_ZIP_SHA256
        or provenance.get("original_report_json_sha256") != EXPECTED_ORIGINAL_REPORT_SHA256
    ):
        raise ReviewPacketError("SOURCE_REVIEW_PROVENANCE_MISMATCH")
    if result.get("case_id") != EXPECTED_CASE_ID or result.get("cutoff") != EXPECTED_CUTOFF:
        raise ReviewPacketError("SOURCE_REVIEW_CASE_OR_CUTOFF_MISMATCH")
    if result.get("fact_count") != EXPECTED_FACT_COUNT:
        raise ReviewPacketError("SOURCE_REVIEW_FACT_COUNT_MISMATCH")
    facts = result.get("facts")
    if not isinstance(facts, list) or len(facts) != EXPECTED_FACT_COUNT:
        raise ReviewPacketError("SOURCE_REVIEW_FACT_ROWS_MISMATCH")
    if result.get("fact_locator_pass_count") != EXPECTED_FACT_COUNT:
        raise ReviewPacketError("SOURCE_REVIEW_LOCATOR_COUNT_NOT_PASS")
    required_global_checks = (
        "all_conservative_known_at_before_cutoff",
        "all_fact_locators_pass",
        "all_source_urls_https_official_szse",
        "all_url_date_matches_intake_publication_date",
        "same_day_buyback_progress_excluded",
    )
    if any(result.get(key) is not True for key in required_global_checks):
        raise ReviewPacketError("SOURCE_REVIEW_MACHINE_CHECKS_NOT_PASS")
    if result.get("market_price_value_in_report") is not False:
        raise ReviewPacketError("SOURCE_REVIEW_MUST_NOT_INCLUDE_MARKET_PRICE")
    if result.get("formal_signed_admission_created") is not False:
        raise ReviewPacketError("SOURCE_REVIEW_ALREADY_CLAIMS_FORMAL_ADMISSION")

    packet_facts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in facts:
        if not isinstance(row, Mapping):
            raise ReviewPacketError("SOURCE_REVIEW_FACT_ROW_INVALID")
        fact_id = str(row.get("fact_id") or "")
        source_id = str(row.get("source_id") or "")
        label = str(row.get("label") or "")
        known_at = str(row.get("conservative_known_at") or "")
        source_sha = str(row.get("source_pdf_sha256") or "")
        page = row.get("physical_pdf_page")
        size = row.get("source_pdf_size_bytes")
        if not fact_id or fact_id in seen or not label:
            raise ReviewPacketError("SOURCE_REVIEW_FACT_ID_OR_LABEL_INVALID")
        seen.add(fact_id)
        if source_id not in SOURCE_URLS:
            raise ReviewPacketError("SOURCE_REVIEW_SOURCE_ID_UNMAPPED:" + source_id)
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
            raise ReviewPacketError("SOURCE_REVIEW_SOURCE_SHA256_INVALID:" + fact_id)
        if not isinstance(page, int) or page < 1:
            raise ReviewPacketError("SOURCE_REVIEW_PAGE_LOCATOR_INVALID:" + fact_id)
        if not isinstance(size, int) or size < 1:
            raise ReviewPacketError("SOURCE_REVIEW_SOURCE_SIZE_INVALID:" + fact_id)
        if not known_at:
            raise ReviewPacketError("SOURCE_REVIEW_KNOWN_AT_MISSING:" + fact_id)
        if row.get("locator_status") != "PASS" or row.get("known_at_before_cutoff") is not True:
            raise ReviewPacketError("SOURCE_REVIEW_FACT_NOT_MACHINE_PASS:" + fact_id)
        if row.get("license_status") != "PUBLIC_ACCESS_REUSE_UNKNOWN":
            raise ReviewPacketError("SOURCE_REVIEW_REUSE_STATUS_CHANGED:" + fact_id)
        if row.get("retention_permission_declared") is not False:
            raise ReviewPacketError("SOURCE_REVIEW_RETENTION_STATUS_CHANGED:" + fact_id)

        packet_facts.append({
            "fact_id": fact_id,
            "claim_label": label,
            "source_id": source_id,
            "official_source_url": SOURCE_URLS[source_id],
            "physical_pdf_page": page,
            "source_pdf_sha256": source_sha,
            "source_pdf_size_bytes": size,
            "machine_locator_result": row.get("locator_status"),
            "machine_known_at_upper_bound": known_at,
            "machine_known_at_before_cutoff": True,
            "machine_reuse_status": "PUBLIC_ACCESS_REUSE_UNKNOWN",
            "machine_retention_permission_declared": False,
            "independent_review": {
                "original_pdf_bytes_hash_rechecked": "PENDING",
                "claim_matches_original_source": "PENDING",
                "page_table_or_row_locator_rechecked": "PENDING",
                "known_at_basis_accepted": "PENDING",
                "fact_level_private_use_basis": "PENDING",
                "disposition": "PENDING",
                "reviewer_notes": "",
            },
        })
    if len(seen) != EXPECTED_FACT_COUNT:
        raise ReviewPacketError("SOURCE_REVIEW_FACT_IDS_NOT_UNIQUE")

    return {
        "schema_version": REVIEW_PACKET_SCHEMA,
        "record_class": "HUMAN_REVIEW_TEMPLATE_NOT_SIGNED_NOT_ADMITTED",
        "status": "TEMPLATE_PENDING_NOT_REVIEWED",
        "case": {
            "case_id": EXPECTED_CASE_ID,
            "cutoff": EXPECTED_CUTOFF,
            "cutoff_semantics": "date-only cutoff means local start-of-day; same-day publication/price is excluded unless independently proven available before cutoff",
            "review_scope": "13 page-located public-company disclosure facts only; market price is excluded and remains a separate unresolved source/use gate",
        },
        "machine_review_provenance": {
            "source_report_ref": source_report_ref,
            "workflow_name": provenance.get("workflow_name"),
            "workflow_run_id": provenance.get("workflow_run_id"),
            "workflow_run_url": provenance.get("workflow_run_url"),
            "workflow_head_sha": provenance.get("workflow_head_sha"),
            "artifact_zip_sha256": provenance.get("downloaded_artifact_zip_sha256"),
            "original_report_json_sha256": provenance.get("original_report_json_sha256"),
            "machine_result": "13/13 locator and conservative date-bound checks passed; this is not independent human sign-off",
        },
        "independent_review": {
            "review_status": "PENDING",
            "reviewer_identity": None,
            "reviewer_signer_key_id": None,
            "reviewer_independence_declaration": "PENDING",
            "reviewed_at": None,
            "overall_fact_review_disposition": "PENDING",
            "private_fact_level_use_disposition": "PENDING",
            "allowed_uses": {
                "private_storage": "PENDING",
                "local_computation": "PENDING",
                "internal_display": "PENDING",
                "backup_and_retention_period": "PENDING",
                "derived_research_outputs": "PENDING",
                "redistribution_or_third_party_access": "PENDING",
            },
            "permission_basis_kind": "PENDING",
            "permission_instrument_id": None,
            "permission_instrument_sha256": None,
            "limitations_and_rationale": [],
            "completed_fact_count": 0,
            "confirmed_fact_count": 0,
            "rejected_or_unknown_fact_count": 0,
            "signature_envelope_ref": None,
        },
        "facts": packet_facts,
        "non_claims": [
            "This file is a template until a genuinely separate reviewer completes it.",
            "The packet does not itself authenticate reviewer identity, grant data-use rights, or create a cryptographic signature.",
            "A review result must be reconciled into the exact case-bound manifest and rights record before the authorized signed-admission workflow.",
            "Market-price data is deliberately out of scope; operator-attested price cannot be promoted by this packet.",
            "No formal Evidence/PIT admission, Decision, Publication, Run Receipt, or execution authorization is created.",
        ],
    }


def _ensure_private_output_path(path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    if path.is_symlink():
        raise ReviewPacketError("OUTPUT_PATH_MUST_NOT_BE_SYMLINK")
    resolved = path.resolve(strict=False)
    if resolved == root or root in resolved.parents:
        raise ReviewPacketError("REVIEW_PACKET_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    if path.exists():
        raise ReviewPacketError("OUTPUT_PATH_ALREADY_EXISTS")


def prepare_review_packet(
    *, report_path: str | Path, output_path: str | Path | None = None
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    report = Path(report_path).expanduser()
    if not report.is_absolute() and not report.exists():
        report = repo_root / report
    document = _read_report(report)
    try:
        source_ref = report.resolve(strict=True).relative_to(repo_root).as_posix()
    except ValueError:
        source_ref = "operator-supplied-local-report"
    packet = build_review_packet(document, source_report_ref=source_ref)

    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = Path.home() / ".iios-private" / "reviews" / f"c2-independent-review-{stamp}.json"
    else:
        output = Path(output_path).expanduser()
    _ensure_private_output_path(output)
    parent_existed = output.parent.exists()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        if not parent_existed:
            os.chmod(output.parent, 0o700)
        elif stat.S_IMODE(output.parent.stat().st_mode) & 0o077:
            raise ReviewPacketError("OUTPUT_PARENT_PERMISSIONS_TOO_OPEN")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(packet, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    if os.name != "nt":
        os.chmod(output, 0o600)
    return {
        "status": "REVIEW_PACKET_CREATED_NOT_REVIEWED",
        "output_path": str(output),
        "case_id": EXPECTED_CASE_ID,
        "fact_count": len(packet["facts"]),
        "review_status": "PENDING",
        "formal_admission_created": False,
        "decision_created": False,
        "run_receipt_created": False,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a private C2 independent fact/use review packet.")
    parser.add_argument("--source-report", default=SOURCE_REPORT_RELATIVE)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        result = prepare_review_packet(report_path=args.source_report, output_path=args.out)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ReviewPacketError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
