from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from research.b2.company_evidence import (
    REQUIRED_COMPANY_FIELD_GROUPS,
    build_company_evidence_manifest,
    verify_raw_artifact,
)
from tools.route_a_605016_adjudicate import adjudicate as adjudicate_attempt10

CASE_ID = "RC-CN-A-605016-20261009"
DIVIDEND_SOURCE_ID = "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION"
DIVIDEND_PDF_SHA256 = "1a153c20f908abbd48fdd63a651ecb0edde269f3e7dd0ea27a0b8ce420e5ea8c"
DIVIDEND_PDF_SIZE = 146499
LISTING_SHA256 = "8c7f84e0161d4db6162c1af4ec32cd29092a3e515435c46887419f6dd2909aa0"
LISTING_SIZE = 3079
UNKNOWN_PRICE_ID = "605016-PRICE-CANDIDATE-20261009"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_obj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def adjudicate(attempt10_root: Path, followup_root: Path, out_dir: Path) -> dict[str, Any]:
    attempt10_root = attempt10_root.resolve(strict=True)
    followup_root = followup_root.resolve(strict=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_out = out_dir / "base-attempt10"
    base_out.mkdir()
    base_report = adjudicate_attempt10(attempt10_root, base_out)
    base_manifest = _read_obj(base_out / "SOURCE_ADJUDICATED_B2_CANDIDATE_MANIFEST.json")

    capture_report = _read_obj(followup_root / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json")
    if capture_report.get("case_id") != CASE_ID or capture_report.get("case_cutoff_date") != "2026-10-09":
        raise ValueError("FOLLOWUP_CAPTURE_CASE_OR_CUTOFF_MISMATCH")
    source_rows = capture_report.get("sources")
    if not isinstance(source_rows, list):
        raise ValueError("FOLLOWUP_SOURCE_ROWS_REQUIRED")
    dividend = next((x for x in source_rows if x.get("source_id") == DIVIDEND_SOURCE_ID), None)
    if not isinstance(dividend, dict) or dividend.get("status") != "RAW_PDF_CAPTURED_NOT_ADMITTED":
        raise ValueError("OFFICIAL_DIVIDEND_PDF_NOT_CAPTURED")

    raw_dir = followup_root / "raw"
    listing_path = raw_dir / "SSE-2026-09-22-announcement-query.bin"
    pdf_path = raw_dir / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    listing_raw = listing_path.read_bytes()
    pdf_raw = pdf_path.read_bytes()
    if len(listing_raw) != LISTING_SIZE or _sha(listing_raw) != LISTING_SHA256:
        raise ValueError("OFFICIAL_SSE_LISTING_BYTES_HASH_OR_SIZE_MISMATCH")
    if len(pdf_raw) != DIVIDEND_PDF_SIZE or _sha(pdf_raw) != DIVIDEND_PDF_SHA256:
        raise ValueError("OFFICIAL_DIVIDEND_PDF_BYTES_HASH_OR_SIZE_MISMATCH")
    pdf_capture = dividend.get("pdf_capture") or {}
    if (
        pdf_capture.get("sha256") != DIVIDEND_PDF_SHA256
        or pdf_capture.get("size_bytes") != DIVIDEND_PDF_SIZE
        or pdf_capture.get("content_type") != "application/pdf"
        or not str(dividend.get("final_pdf_url", "")).startswith("https://big5.sse.com.cn/")
    ):
        raise ValueError("OFFICIAL_DIVIDEND_PDF_RECEIPT_BINDING_MISMATCH")

    row = dividend.get("listing_row") or {}
    if (
        row.get("SECURITY_CODE") != "605016"
        or row.get("SECURITY_NAME") != "百龙创园"
        or row.get("SSEDATE") != "2026-09-22"
        or row.get("TITLE") != "2026年半年度权益分派实施公告"
        or row.get("URL") != "/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf"
    ):
        raise ValueError("OFFICIAL_SSE_LISTING_BODY_BINDING_MISMATCH")

    reader = PdfReader(str(pdf_path), strict=True)
    if len(reader.pages) != 3:
        raise ValueError("OFFICIAL_DIVIDEND_PDF_PAGE_COUNT_MISMATCH")
    page_texts = [page.extract_text() or "" for page in reader.pages]
    text = re.sub(r"\s+", "", "\n".join(page_texts))
    required_text = (
        "证券代码：605016",
        "证券简称：百龙创园",
        "公告编号：2026-043",
        "2026年半年度权益分派实施公告",
        "A股每股现金红利0.075元",
        "2026/9/28",
        "2026/9/29",
        "420,012,320股",
        "31,500,924元",
    )
    missing_text = [needle for needle in required_text if needle not in text]
    if missing_text:
        raise ValueError("OFFICIAL_DIVIDEND_PDF_BODY_MISMATCH:" + ",".join(missing_text))
    metadata = reader.metadata
    created = str(getattr(metadata, "creation_date", "") or "")
    creation_date = created or None

    # Preserve the original Attempt 10 input bytes unchanged; stage the supplemental
    # official PDF in a separate combined root and re-run the core-owned validator.
    combined_root = out_dir / "combined-evidence-root"
    shutil.copytree(attempt10_root, combined_root)
    supplemental_relative = "raw/SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    supplemental_target = combined_root / supplemental_relative
    if supplemental_target.exists():
        raise ValueError("SUPPLEMENTAL_RAW_PATH_COLLISION")
    supplemental_target.write_bytes(pdf_raw)

    evidence = list(base_manifest["evidence"])
    raw_artifacts = list(base_manifest["raw_artifacts"])
    dividend_evidence = {
        "evidence_id": "605016-H1-DIVIDEND-IMPLEMENTED-202609",
        "subject_id": CASE_ID,
        "field_id": "capital_structure.dividend_implementation_2026H1",
        "claim_type": "OBSERVED_FACT",
        "value": {
            "announcement_no": "2026-043",
            "period": "2026H1",
            "cash_dividend_cny_per_share_gross": "0.075",
            "shareholder_record_date": "2026-09-28",
            "ex_dividend_date": "2026-09-29",
            "cash_payment_date": "2026-09-29",
            "total_shares_basis": 420012320,
            "aggregate_cash_dividend_cny_gross": 31500924,
            "implementation_status": "IMPLEMENTATION_ANNOUNCEMENT",
        },
        "unit": "CNY_per_share_and_total_CNY",
        "basis": "Official SSE-hosted implementation notice. PDF body identifies issuer/code and announcement no. 2026-043; page 1 gives 0.075 CNY per A share, 420,012,320-share basis and aggregate 31,500,924 CNY; pages 1-2 give 2026-09-28 record date and 2026-09-29 ex-date/payment date.",
        "observation_date": "2026-09-29",
        "known_at": "2026-09-22",
        "published_at": "2026-09-22",
        "known_at_basis": "Official SSE query API listing row: ADDDATE=2026-09-21 16:44:10, SSEDATE=2026-09-22, matching title/code/PDF URL; the PDF footer is dated 2026-09-22 and metadata creation date is recorded separately. To avoid asserting undocumented ADDDATE semantics as an exact first-public instant, known_at/published_at retain date precision.",
        "retrieved_at": str(capture_report["captured_at"]),
        "effective_from": "2026-09-29",
        "source_ref": str(dividend["final_pdf_url"]),
        "artifact_id": "ROUTE-A-FOLLOWUP:SSE-2026-09-22-DIVIDEND-IMPLEMENTATION:" + DIVIDEND_PDF_SHA256[:16],
        "content_sha256": DIVIDEND_PDF_SHA256,
        "capture_sha256": DIVIDEND_PDF_SHA256,
        "exact_bytes": True,
        "provenance_class": "SOURCE_VINTAGE_VERIFIED",
        "status": "ADMITTED",
        "license_status": "RESTRICTED_NO_REDISTRIBUTION",
        "source_locator": "PDF p.1: key information and distribution basis; pp.1-2: record/ex-dividend/payment dates; p.3 footer: issuer board and 2026-09-22 date.",
        "source_id": DIVIDEND_SOURCE_ID,
        "source_origin_adjudication": "PASS_OFFICIAL_SSE_LISTING_AND_OFFICIAL_BIG5_PDF_HOST_BODY_MATCH",
        "first_public_time_precision": "DATE_PRECISION; official listing ADDDATE has an intraday value but its exact field semantics were not formally documented.",
        "parents": [],
        "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
        "quality_notes": [
            "Exact raw PDF size/SHA-256 verified.",
            "Issuer, security code, announcement number, document title and distribution values visually and textually reviewed.",
            "Official SSE legal/reuse disposition is restricted to internal non-redistributive research; do not commit or redistribute the PDF.",
            "This is the implemented distribution notice, not the earlier dividend proposal.",
        ],
    }
    evidence.append(dividend_evidence)
    raw_artifacts.append({
        "evidence_id": dividend_evidence["evidence_id"],
        "relative_path": supplemental_relative,
        "expected_size_bytes": DIVIDEND_PDF_SIZE,
        "expected_sha256": DIVIDEND_PDF_SHA256,
    })

    combined_manifest = build_company_evidence_manifest(
        case_id=str(base_manifest["case_id"]),
        market=str(base_manifest["market"]),
        symbol=str(base_manifest["symbol"]),
        company=str(base_manifest["company"]),
        cutoff_date=str(base_manifest["cutoff_date"]),
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=combined_root,
    )
    errors = list(combined_manifest.get("validation_errors") or [])
    missing = sorted(
        set(REQUIRED_COMPANY_FIELD_GROUPS)
        - {
            str(item["field_id"]).split(".", 1)[0]
            for item in evidence
            if item.get("status") == "ADMITTED" and item.get("provenance_class") != "UNKNOWN"
            and not any(item_error.startswith("EVIDENCE:") for item_error in [])
        }
    )
    expected_errors = [
        "EVIDENCE[605016-PRICE-CANDIDATE-20261009]:PIT:PIT_UNKNOWN: source availability/provenance is not established",
        "REQUIRED_FIELD_GROUPS_UNCOVERED:market_price",
    ]
    if combined_manifest.get("status") != "BLOCKED":
        raise AssertionError(f"COMBINED_B2_MUST_REMAIN_BLOCKED_FOR_PRICE:{combined_manifest.get('status')}")
    if errors != expected_errors:
        raise AssertionError(f"UNEXPECTED_COMBINED_B2_ERRORS:{errors}")
    if "market_price" not in missing:
        raise AssertionError("MARKET_PRICE_MUST_REMAIN_MISSING")

    ledger = {
        "schema_version": "IIOS-605016-DIVIDEND-IMPLEMENTATION-ADJUDICATION-0.1",
        "case_id": CASE_ID,
        "cutoff_date": "2026-10-09",
        "source": {
            "source_id": DIVIDEND_SOURCE_ID,
            "classification": "OFFICIAL_EXCHANGE",
            "listing_sha256": LISTING_SHA256,
            "listing_size_bytes": LISTING_SIZE,
            "listing_adddate_candidate": row.get("ADDDATE"),
            "listing_date": row.get("SSEDATE"),
            "listing_title": row.get("TITLE"),
            "pdf_url": dividend["final_pdf_url"],
            "pdf_sha256": DIVIDEND_PDF_SHA256,
            "pdf_size_bytes": DIVIDEND_PDF_SIZE,
            "pdf_creation_date_metadata": creation_date,
            "pdf_pages": len(reader.pages),
            "body_checks_passed": list(required_text),
            "reuse_status": "RESTRICTED_NO_REDISTRIBUTION",
            "adjudication_status": "SOURCE_AND_FACT_CONTENT_VERIFIED_FOR_INTERNAL_FACT_LEVEL_USE",
            "raw_pdf_is_committed_to_git": False,
        },
        "fact_record": dividend_evidence,
        "combined_b2_result": {
            "manifest_status": combined_manifest["status"],
            "evidence_record_count": len(combined_manifest["evidence"]),
            "admitted_record_count": sum(1 for x in combined_manifest["evidence"] if x.get("status") == "ADMITTED"),
            "admitted_field_groups": sorted(
                {str(x["field_id"]).split(".", 1)[0] for x in combined_manifest["evidence"]
                 if x.get("status") == "ADMITTED" and x.get("provenance_class") != "UNKNOWN"}
            ),
            "missing_required_field_groups": ["market_price"],
            "validation_errors": errors,
            "evidence_admission": False,
            "pit_admission": False,
        },
        "non_claims": [
            "The official dividend fact does not close the market_price group.",
            "The 2026-10-09 close remains outside the original date-only cutoff interpreted at start of day.",
            "The 20.28 CNY 2026-10-09 secondary quote remains UNKNOWN and is not used to force manifest PASS.",
            "Production Host acceptance and real semantic/Forecast/Valuation are not established by this evidence run.",
        ],
    }
    (out_dir / "DIVIDEND_IMPLEMENTATION_ADJUDICATION.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "COMBINED_B2_CANDIDATE_MANIFEST.json").write_text(
        json.dumps(combined_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "schema_version": "IIOS-605016-FOLLOWUP-ADJUDICATION-RUN-0.1",
        "case_id": CASE_ID,
        "input_attempt10_manifest_sha256": base_report["capture_manifest_sha256"],
        "input_followup_pdf_sha256": DIVIDEND_PDF_SHA256,
        "official_dividend_fact": "ADMITTED_FOR_SPECIFIC_INTERNAL_FACTS",
        "combined_b2_manifest_status": combined_manifest["status"],
        "combined_evidence_record_count": len(combined_manifest["evidence"]),
        "field_groups_admitted": ["security_identity", "corporate_disclosures", "business_reality", "financial_reality", "capital_structure", "trust_governance_events"],
        "missing_required_field_groups": ["market_price"],
        "validation_errors": errors,
        "evidence_admission": False,
        "pit_admission": False,
        "core_validator_unchanged": "research.b2.company_evidence.build_company_evidence_manifest",
        "formal_decision_and_report_authorized": False,
        "output_note": "Only JSON adjudication outputs are uploaded by the follow-up adjudication workflow; raw source PDFs remain in the separate, time-limited capture artifact.",
    }
    (out_dir / "COMBINED_B2_RUN_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt10-root", required=True, type=Path)
    parser.add_argument("--followup-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    report = adjudicate(args.attempt10_root, args.followup_root, args.out_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
