from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from research.b2.company_evidence import build_company_evidence_manifest, REQUIRED_COMPANY_FIELD_GROUPS
from tools.route_a_605016_followup_capture import official_dividend_capture
from tools.route_a_605016_followup_adjudicate import adjudicate as adjudicate_attempt10_and_dividend
from tools.route_a_605016_sse_endpoint_discovery import fetch_https

CASE_ID = "RC-CN-A-605016-20261009"
SYMBOL = "605016"
CUTOFF_DATE = "2026-10-09"
SSE_PRICE_URL = (
    "https://yunhq.sse.com.cn:32042/v1/sh1/dayk/605016"
    "?begin=20261008&end=20261008"
    "&select=date,open,high,low,close,volume,amount"
)
PRICE_EVIDENCE_ID = "605016-SSE-HTTPS-DAILY-CLOSE-20261008"
OLD_UNKNOWN_PRICE_EVIDENCE_ID = "605016-PRICE-CANDIDATE-20261009"
EXPECTED_PRICE_RAW_SHA256 = "45c8eece737c57ec11deb34ad099dcc8f9f88f9c5e080be53992d2ec707b3480"
EXPECTED_PRICE_RAW_SIZE = 124


def _sha256(raw: bytes) -> str:
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def _read_obj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + path.name)
    return value


def _parse_daybar(raw: bytes) -> tuple[dict[str, Any], list[Any]]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("OFFICIAL_SSE_PRICE_RESPONSE_NOT_JSON") from exc
    rows = payload.get("kline") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("OFFICIAL_SSE_PRICE_KLINE_ROWS_MISSING")
    matched = [
        row for row in rows
        if isinstance(row, list)
        and len(row) == 7
        and str(row[0]).replace("-", "")[:8] == "20261008"
    ]
    if len(matched) != 1:
        raise ValueError("OFFICIAL_SSE_PRICE_EXPECTED_EXACTLY_ONE_20261008_ROW")
    row = matched[0]
    try:
        parsed = {
            "date": str(row[0]),
            "open": Decimal(str(row[1])),
            "high": Decimal(str(row[2])),
            "low": Decimal(str(row[3])),
            "close": Decimal(str(row[4])),
            "volume": Decimal(str(row[5])),
            "amount": Decimal(str(row[6])),
        }
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("OFFICIAL_SSE_PRICE_ROW_NUMERIC_FIELDS_INVALID") from exc
    if (
        not parsed["close"].is_finite()
        or parsed["close"] <= 0
        or parsed["high"] < parsed["low"]
        or not (parsed["low"] <= parsed["close"] <= parsed["high"])
        or parsed["volume"] < 0
        or parsed["amount"] < 0
    ):
        raise ValueError("OFFICIAL_SSE_PRICE_ROW_VALUE_CONSTRAINT_FAILED")
    # Return only a non-numeric shape record for the public report alongside the
    # in-memory parsed row; callers must not serialize parsed numeric values.
    shape = {
        "date_value_present": True,
        "row_field_count": len(row),
        "required_quote_fields_present": all(row[i] not in (None, "") for i in range(1, 7)),
        "numeric_fields_valid": True,
        "numeric_values_serialized": False,
    }
    return shape, row


def adjudicate(attempt10_root: Path, out_dir: Path) -> dict[str, Any]:
    attempt10_root = attempt10_root.resolve(strict=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    followup_root = out_dir / "official-dividend-capture"
    followup_root.mkdir()
    dividend = official_dividend_capture(followup_root)
    if dividend.get("status") != "RAW_PDF_CAPTURED_NOT_ADMITTED":
        raise ValueError("OFFICIAL_DIVIDEND_SOURCE_CAPTURE_FAILED:" + str(dividend.get("status")))
    capture_report = {
        "case_id": CASE_ID,
        "case_cutoff_date": CUTOFF_DATE,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sources": [dividend],
    }
    (followup_root / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json").write_text(
        json.dumps(capture_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    base_out = out_dir / "base-b2"
    base_out.mkdir()
    base_summary = adjudicate_attempt10_and_dividend(attempt10_root, followup_root, base_out)
    combined_root = base_out / "combined-evidence-root"
    combined_manifest_path = base_out / "COMBINED_B2_CANDIDATE_MANIFEST.json"
    combined_manifest = _read_obj(combined_manifest_path)

    # Only query the official SSE HTTPS endpoint. Raw bytes and numeric fields are
    # confined to the ephemeral runner workspace and are never uploaded as artifacts.
    source = fetch_https(
        SSE_PRICE_URL,
        referer="https://www.sse.com.cn/market/stockdata/overview/day/",
    )
    if source.get("status") != "CAPTURED":
        raise ValueError("OFFICIAL_SSE_HTTPS_PRICE_FETCH_BLOCKED")
    final_url = str(source.get("final_url") or source.get("url") or "")
    final = urlparse(final_url)
    if final.scheme.lower() != "https" or final.hostname != "yunhq.sse.com.cn":
        raise ValueError("OFFICIAL_SSE_PRICE_TLS_ORIGIN_MISMATCH")
    raw = source["body"]
    raw_sha = _sha256(raw)
    shape, row = _parse_daybar(raw)
    if len(raw) != EXPECTED_PRICE_RAW_SIZE or raw_sha != EXPECTED_PRICE_RAW_SHA256:
        raise ValueError("OFFICIAL_SSE_PRICE_RAW_BYTES_CHANGED_REQUIRES_REVIEW")

    # The case cutoff remains date-only 2026-10-09, interpreted by the unchanged
    # core as 00:00 +08:00. The 2026-10-08 closing observation occurs at the end
    # of the prior A-share session. This is the market observation/event time,
    # not a claim that the endpoint exposed an exact first-published timestamp.
    known_at = "2026-10-08T15:00:00+08:00"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    relative_path = "raw/SSE-HTTPS-DAYK-605016-2026-10-08.json"
    raw_path = combined_root / relative_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)

    price_evidence = {
        "evidence_id": PRICE_EVIDENCE_ID,
        "subject_id": CASE_ID,
        "field_id": "market_price.close",
        "claim_type": "OBSERVED_FACT",
        "value": {
            "observation_date": "2026-10-08",
            "close_cny_per_share": float(Decimal(str(row[4]))),
            "quote_type": "OFFICIAL_SSE_DAILY_CLOSE",
        },
        "unit": "CNY_per_share",
        "basis": "Official SSE-hosted daily-bar endpoint over verified TLS; exact source JSON bytes hash and one-row date match verified. The known_at value represents the official exchange session's closing observation at 15:00 +08, not an asserted API publication timestamp.",
        "observation_date": "2026-10-08",
        "known_at": known_at,
        "known_at_basis": "MARKET_SESSION_CLOSE_EVENT_TIME; the daily bar is the finalized official close for the 2026-10-08 session. The API does not expose a separate first-published timestamp; this record does not claim to know when its historical JSON row was uploaded to the endpoint.",
        "retrieved_at": retrieved_at,
        "source_ref": SSE_PRICE_URL,
        "artifact_id": "ROUTE-A-RAW:SSE-HTTPS-DAYK-605016:" + raw_sha[:16],
        "content_sha256": raw_sha,
        "capture_sha256": raw_sha,
        "exact_bytes": True,
        "provenance_class": "SOURCE_VINTAGE_VERIFIED",
        "status": "ADMITTED",
        "license_status": "RESTRICTED_NO_REDISTRIBUTION",
        "source_locator": "Official SSE TLS daily-bar response; selected fields date, open, high, low, close, volume, amount; exactly one 2026-10-08 row with seven fields.",
        "source_id": "PRICE-SSE-OFFICIAL-DAYK-2026-10-08",
        "source_origin_adjudication": "PASS_OFFICIAL_SSE_DOMAIN_HTTPS_TLS_AND_DATE_ROW_MATCH",
        "first_public_time_precision": "MARKET_OBSERVATION_TIME; endpoint does not provide an explicit historical row first-public timestamp.",
        "parents": [],
        "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
        "quality_notes": [
            "Exact HTTPS response bytes and SHA-256 are verified in the current run.",
            "The raw response and numeric value remain only in the ephemeral runner workspace; they are not uploaded or committed.",
            "The SSE reuse disposition is restricted/no redistribution; this candidate is used only for the internal non-commercial evidence gate.",
            "The original date-only cutoff is not changed; the candidate uses the preceding completed trading session.",
        ],
    }

    # The earlier secondary price record remains in the source-review ledger but is
    # excluded from this decision manifest because its terms/PIT were not admitted.
    evidence = [
        item for item in list(combined_manifest.get("evidence") or [])
        if str(item.get("evidence_id")) != OLD_UNKNOWN_PRICE_EVIDENCE_ID
    ]
    raw_artifacts = [
        item for item in list(combined_manifest.get("raw_artifacts") or [])
        if str(item.get("evidence_id")) != OLD_UNKNOWN_PRICE_EVIDENCE_ID
    ]
    if any(str(item.get("evidence_id")) == PRICE_EVIDENCE_ID for item in evidence):
        raise ValueError("OFFICIAL_PRICE_EVIDENCE_ID_COLLISION")
    evidence.append(price_evidence)
    raw_artifacts.append({
        "evidence_id": PRICE_EVIDENCE_ID,
        "relative_path": relative_path,
        "expected_size_bytes": len(raw),
        "expected_sha256": raw_sha,
    })

    manifest = build_company_evidence_manifest(
        case_id=CASE_ID,
        market="CN-A",
        symbol=SYMBOL,
        company="山东百龙创园生物科技股份有限公司",
        cutoff_date=CUTOFF_DATE,
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=combined_root,
    )

    admitted_groups = sorted({
        str(item.get("field_id", "")).split(".", 1)[0]
        for item in manifest.get("evidence", [])
        if item.get("status") == "ADMITTED"
        and item.get("provenance_class") != "UNKNOWN"
        and "." in str(item.get("field_id", ""))
    })
    report = {
        "schema_version": "IIOS-605016-OFFICIAL-HTTPS-B2-ADJUDICATION-0.1",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "cutoff_semantics": "Date-only 2026-10-09 is interpreted by the unchanged core as the start of that date.",
        "official_dividend_source": {
            "capture_status": dividend.get("status"),
            "fact_level_admission": (
                "ADMITTED_FOR_SPECIFIC_INTERNAL_FACTS"
                if any(item.get("evidence_id") == "605016-H1-DIVIDEND-IMPLEMENTED-202609"
                       and item.get("status") == "ADMITTED"
                       for item in manifest.get("evidence", []))
                else "NOT_ADMITTED"
            ),
            "evidence_id": "605016-H1-DIVIDEND-IMPLEMENTED-202609",
            "pdf_sha256": (dividend.get("pdf_capture") or {}).get("sha256"),
            "pdf_size_bytes": (dividend.get("pdf_capture") or {}).get("size_bytes"),
            "published_at_precision": "DATE_ONLY_2026-09-22",
            "reuse_disposition": "RESTRICTED_NO_REDISTRIBUTION; internal fact-level use only",
        },
        "official_price_source": {
            "source_id": "PRICE-SSE-OFFICIAL-DAYK-2026-10-08",
            "url": SSE_PRICE_URL,
            "transport": "HTTPS_TLS_VERIFIED",
            "http_status": source.get("http_status"),
            "content_type": source.get("content_type"),
            "observation_date": "2026-10-08",
            "known_at": known_at,
            "known_at_basis": "Market-session close event time; not an exact endpoint first-published timestamp.",
            "raw_size_bytes": len(raw),
            "raw_sha256": raw_sha,
            "row_match_count": 1,
            "row_shape": shape,
            "reuse_disposition": "RESTRICTED_NO_REDISTRIBUTION; internal non-commercial research gate only",
            "numeric_quote_value_in_report": False,
            "raw_source_bytes_in_report_artifact": False,
        },
        "core_b2": {
            "scope": "EPHEMERAL_CANDIDATE_MANIFEST_ONLY",
            "validator": "research.b2.company_evidence.build_company_evidence_manifest (unchanged)",
            "candidate_manifest_status": manifest.get("status"),
            "candidate_manifest_sha256": (manifest.get("audit") or {}).get("manifest_sha256"),
            "evidence_record_count": len(manifest.get("evidence") or []),
            "admitted_record_count": sum(1 for item in manifest.get("evidence", []) if item.get("status") == "ADMITTED"),
            "admitted_field_groups": admitted_groups,
            "missing_required_field_groups": sorted(set(REQUIRED_COMPANY_FIELD_GROUPS) - set(admitted_groups)),
            "validation_errors": list(manifest.get("validation_errors") or []),
            "evidence_admission_ephemeral": manifest.get("status") == "PASS",
            "pit_admission_ephemeral": manifest.get("status") == "PASS",
            "canonical_durable_admission": False,
            "numeric_quote_value_in_report": False,
            "raw_source_bytes_uploaded": False,
            "full_candidate_manifest_uploaded": False,
        },
        "scope_boundary": {
            "canonical_durable_evidence_record": False,
            "reason": "Public repository and artifact paths must not redistribute restricted quote values/raw bytes. The successful in-memory B2 validation proves the source row and unchanged core gate; the configured private Host/data root must persist the exact source bytes and signed admission record before production use.",
            "production_host_acceptance": False,
            "formal_valuation_or_decision_authorized": False,
            "human_approval_required": True,
            "automatic_execution": False,
        },
        "combined_base_result": {
            "status": base_summary.get("combined_b2_manifest_status"),
            "validation_errors": base_summary.get("validation_errors"),
        },
        "overall": "PASS_EPHEMERAL_B2" if manifest.get("status") == "PASS" else "BLOCKED",
        "next_gate": "If PASS_EPHEMERAL_B2, ingest this exact HTTPS source privately into the deployed Host data root; repeat unchanged B2/PIT admission there, then run genuine semantic/Forecast/Valuation/Decision/report/Run Receipt replay and independent red-team. Do not promote this public run as canonical durable admission.",
    }
    (out_dir / "OFFICIAL_HTTPS_B2_ADJUDICATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # The full manifest with numeric market data is intentionally left in the
    # ephemeral workspace and must not be uploaded to Actions artifacts.
    print(json.dumps({
        "overall": report["overall"],
        "candidate_manifest_status": report["core_b2"]["candidate_manifest_status"],
        "admitted_field_group_count": len(admitted_groups),
        "missing_required_field_group_count": len(report["core_b2"]["missing_required_field_groups"]),
        "price_source_https_tls_verified": True,
        "price_raw_sha256": raw_sha,
        "numeric_quote_value_printed": False,
        "raw_source_bytes_uploaded": False,
    }, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt10-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    report = adjudicate(args.attempt10_root, args.out_dir)
    # B2 fail-closed is a completed validation outcome; don't disguise a blocked
    # manifest as workflow success by setting PASS, nor fail to publish the report.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
