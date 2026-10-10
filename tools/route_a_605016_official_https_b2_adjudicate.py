from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from pypdf import PdfReader
from typing import Any
from urllib.parse import urlparse

from research.b2.company_evidence import build_company_evidence_manifest, REQUIRED_COMPANY_FIELD_GROUPS
from tools.route_a_605016_followup_capture import official_dividend_capture
from tools.route_a_605016_followup_adjudicate import adjudicate as adjudicate_attempt10_and_dividend
from tools.route_a_605016_adjudicate import adjudicate as adjudicate_attempt10
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
EXPECTED_DIVIDEND_PDF_SHA256 = "1a153c20f908abbd48fdd63a651ecb0edde269f3e7dd0ea27a0b8ce420e5ea8c"
EXPECTED_DIVIDEND_PDF_SIZE = 146499
EXPECTED_DIVIDEND_LISTING_SHA256 = "8c7f84e0161d4db6162c1af4ec32cd29092a3e515435c46887419f6dd2909aa0"
EXPECTED_DIVIDEND_LISTING_SIZE = 3079
EXPECTED_DIVIDEND_PDF_URL = "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf"
# Fixed official SSE HTTPS candidates for the exact same announcement path. The
# fallback is transport-only: every successful response must still match the
# canonical PDF's previously admitted exact size/SHA-256 and three-page shape.
DIVIDEND_PDF_HTTPS_URLS = (
    EXPECTED_DIVIDEND_PDF_URL,
    "https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf",
    "https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf",
)
DIVIDEND_PDF_ALLOWED_FINAL_URLS = frozenset(DIVIDEND_PDF_HTTPS_URLS)
DIVIDEND_LEDGER_RELATIVE = Path(
    "evidence/real_cases/RC-CN-A-605016-20261009/DIVIDEND_IMPLEMENTATION_ADJUDICATION_20261010.json"
)
MAX_DIVIDEND_CURL_BYTES = 8 * 1024 * 1024
DIVIDEND_REFERER = "https://www.sse.com.cn/disclosure/listedinfo/announcement/index.shtml"


class OfficialDividendPdfFetchBlocked(ValueError):
    """All pinned official HTTPS candidates failed; diagnostics contain no URLs or raw errors."""

    def __init__(self, diagnostics: list[dict[str, str]]) -> None:
        self.safe_diagnostics = diagnostics
        super().__init__("OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED")


def _safe_transport_outcome(response: dict[str, Any]) -> str:
    status = response.get("http_status")
    if isinstance(status, int) and not 200 <= status < 300:
        return f"HTTP_{status}"
    error = str(response.get("error", "")).upper()
    http_match = re.search(r"HTTP ERROR (\d{3})", error)
    if http_match:
        return "HTTP_" + http_match.group(1)
    curl_match = re.search(r"CURL_EXIT_(\d+)", error)
    if curl_match:
        return {
            "6": "DNS_FAILURE",
            "7": "CONNECTION_FAILURE",
            "22": "HTTP_FAILURE",
            "28": "TIMEOUT",
            "35": "TLS_HANDSHAKE_FAILURE",
            "60": "TLS_CERTIFICATE_FAILURE",
            "63": "RESPONSE_TOO_LARGE",
        }.get(curl_match.group(1), "CURL_FAILURE")
    low = error.lower()
    if "temporary failure in name resolution" in low or "name or service not known" in low or "nodename nor servname" in low or "getaddrinfo failed" in low:
        return "DNS_FAILURE"
    if "timed out" in low or "timeout" in low:
        return "TIMEOUT"
    if "certificate_verify_failed" in low or "certificate" in low or "ssl:" in low or "tls" in low:
        return "TLS_FAILURE"
    if "connection refused" in low:
        return "CONNECTION_REFUSED"
    if "connection reset" in low:
        return "CONNECTION_RESET"
    if "network is unreachable" in low:
        return "NETWORK_UNREACHABLE"
    if "http error" in low:
        return "HTTP_FAILURE"
    if "curl unavailable" in low:
        return "CURL_UNAVAILABLE"
    return "FETCH_BLOCKED"


def _safe_fetch_diagnostic(url: str, transport: str, response: dict[str, Any]) -> dict[str, str]:
    host = urlparse(url).hostname or ""
    endpoint = {
        "big5.sse.com.cn": "BIG5",
        "static.sse.com.cn": "STATIC",
        "www.sse.com.cn": "WWW",
    }.get(host, "UNRECOGNIZED_HOST")
    return {
        "endpoint": endpoint,
        "transport": transport,
        "outcome": _safe_transport_outcome(response),
    }


def _fetch_official_pdf_via_curl(url: str, *, referer: str) -> dict[str, Any]:
    """Second HTTPS transport only; URL/redirect allowlists and exact bytes remain mandatory."""
    if url not in DIVIDEND_PDF_HTTPS_URLS or urlparse(url).scheme.lower() != "https":
        return {"url": url, "status": "BLOCKED", "error": "CURL_URL_NOT_ALLOWLISTED"}
    curl = shutil.which("curl")
    if not curl:
        return {"url": url, "status": "BLOCKED", "error": "CURL_UNAVAILABLE"}
    with tempfile.TemporaryDirectory(prefix="iios-605016-official-pdf-") as temp_dir:
        body_path = Path(temp_dir) / "response.pdf"
        command = [
            curl,
            "--location",
            "--max-redirs", "5",
            "--connect-timeout", "4",
            "--max-time", "9",
            "--proto", "=https",
            "--proto-redir", "=https",
            "--fail",
            "--silent",
            "--show-error",
            "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
            "--referer", referer,
            "--header", "Accept: application/pdf,*/*",
            "--header", "Accept-Encoding: identity",
            "--max-filesize", str(MAX_DIVIDEND_CURL_BYTES),
            "--output", str(body_path),
            "--write-out", "%{http_code}\n%{url_effective}\n%{content_type}\n",
            url,
        ]
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            return {"url": url, "status": "BLOCKED", "error": "CURL_TIMEOUT"}
        except OSError:
            return {"url": url, "status": "BLOCKED", "error": "CURL_EXEC_FAILED"}

        metadata = (completed.stdout or b"").decode("utf-8", errors="replace").splitlines()
        try:
            http_status = int(metadata[0]) if metadata and metadata[0].isdigit() else 0
        except (TypeError, ValueError):
            http_status = 0
        final_url = metadata[1] if len(metadata) > 1 else url
        content_type = metadata[2] if len(metadata) > 2 else ""
        if completed.returncode != 0:
            error = "CURL_EXIT_" + str(completed.returncode)
            if http_status:
                return {
                    "url": url, "final_url": final_url, "status": "BLOCKED",
                    "error": error, "http_status": http_status,
                }
            return {"url": url, "final_url": final_url, "status": "BLOCKED", "error": error}
        if not 200 <= http_status < 300:
            return {
                "url": url, "final_url": final_url, "status": "BLOCKED",
                "error": "CURL_HTTP_RESPONSE_NOT_SUCCESS", "http_status": http_status,
            }
        if not body_path.is_file():
            return {
                "url": url, "final_url": final_url, "status": "BLOCKED",
                "error": "CURL_BODY_MISSING", "http_status": http_status,
            }
        size = body_path.stat().st_size
        if size > MAX_DIVIDEND_CURL_BYTES:
            return {
                "url": url, "final_url": final_url, "status": "BLOCKED",
                "error": "CURL_RESPONSE_TOO_LARGE", "http_status": http_status,
            }
        body = body_path.read_bytes()
        return {
            "url": url,
            "final_url": final_url,
            "status": "CAPTURED",
            "http_status": http_status,
            "content_type": content_type,
            "size_bytes": len(body),
            "body": body,
        }


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




def _recover_dividend_from_prior_canonical_adjudication(
    followup_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recover the known official PDF without repeating the flaky SSE listing API call.

    The source listing row and fact-level decision already exist in the canonical
    case ledger. This path revalidates that ledger's pinned identity, fetches the
    exact official PDF URL over HTTPS, and re-hashes/rechecks the PDF bytes. It
    explicitly does not claim that the original listing response bytes were
    reacquired in this run.
    """
    ledger_path = Path(__file__).resolve().parents[1] / DIVIDEND_LEDGER_RELATIVE
    ledger_raw = ledger_path.read_bytes()
    ledger = _read_obj(ledger_path)
    source = ledger.get("source")
    fact = ledger.get("evidence_record")
    expected_row = {
        "SECURITY_CODE": "605016",
        "SECURITY_NAME": "百龙创园",
        "SSEDATE": "2026-09-22",
        "TITLE": "2026年半年度权益分派实施公告",
        "URL": "/disclosure/listedinfo/announcement/c/new/2026-09-22/605016_20260922_1YLT.pdf",
    }
    if ledger.get("schema_version") != "IIOS-605016-DIVIDEND-IMPLEMENTATION-ADJUDICATION-0.1":
        raise ValueError("CANONICAL_DIVIDEND_LEDGER_SCHEMA_MISMATCH")
    if ledger.get("case_id") != CASE_ID or ledger.get("cutoff_date") != CUTOFF_DATE:
        raise ValueError("CANONICAL_DIVIDEND_LEDGER_CASE_OR_CUTOFF_MISMATCH")
    if not isinstance(source, dict) or not isinstance(fact, dict):
        raise ValueError("CANONICAL_DIVIDEND_LEDGER_SOURCE_OR_FACT_MISSING")
    row = source.get("listing_row")
    if any(not isinstance(row, dict) or row.get(key) != value for key, value in expected_row.items()):
        raise ValueError("CANONICAL_DIVIDEND_LISTING_IDENTITY_MISMATCH")
    if (
        source.get("listing_sha256") != EXPECTED_DIVIDEND_LISTING_SHA256
        or source.get("listing_size_bytes") != EXPECTED_DIVIDEND_LISTING_SIZE
        or source.get("pdf_url") != EXPECTED_DIVIDEND_PDF_URL
        or source.get("pdf_sha256") != EXPECTED_DIVIDEND_PDF_SHA256
        or source.get("pdf_size_bytes") != EXPECTED_DIVIDEND_PDF_SIZE
        or source.get("pdf_page_count") != 3
        or ledger.get("reuse", {}).get("status") != "RESTRICTED_NO_REDISTRIBUTION"
    ):
        raise ValueError("CANONICAL_DIVIDEND_SOURCE_PIN_MISMATCH")
    if (
        fact.get("evidence_id") != "605016-H1-DIVIDEND-IMPLEMENTED-202609"
        or fact.get("content_sha256") != EXPECTED_DIVIDEND_PDF_SHA256
        or fact.get("status") != "ADMITTED"
        or fact.get("provenance_class") != "SOURCE_VINTAGE_VERIFIED"
        or fact.get("known_at") != "2026-09-22"
        or fact.get("field_id") != "capital_structure.dividend_implementation_2026H1"
    ):
        raise ValueError("CANONICAL_DIVIDEND_FACT_RECORD_BINDING_MISMATCH")

    response = None
    requested_url = None
    fetch_diagnostics: list[dict[str, str]] = []
    for candidate_url in DIVIDEND_PDF_HTTPS_URLS:
        candidate = fetch_https(candidate_url, referer=DIVIDEND_REFERER)
        # A captured response is validated immediately below. We never hide a
        # wrong-origin/hash/PDF response by falling through to another endpoint.
        if candidate.get("status") == "CAPTURED":
            response = candidate
            requested_url = candidate_url
            break
        fetch_diagnostics.append(_safe_fetch_diagnostic(candidate_url, "PYTHON_HTTPS", candidate))

    # A second, standard macOS HTTPS client handles cases where urllib's proxy,
    # TLS, or HTTP negotiation is blocked. It uses only the same fixed HTTPS
    # candidates and refuses HTTPS-to-HTTP redirects. The bytes still have to
    # pass the canonical URL/origin, exact size/SHA-256 and PDF structure gates.
    if response is None:
        for candidate_url in DIVIDEND_PDF_HTTPS_URLS:
            candidate = _fetch_official_pdf_via_curl(candidate_url, referer=DIVIDEND_REFERER)
            if candidate.get("status") == "CAPTURED":
                response = candidate
                requested_url = candidate_url
                break
            fetch_diagnostics.append(_safe_fetch_diagnostic(candidate_url, "CURL_HTTPS", candidate))

    if response is None or requested_url is None:
        raise OfficialDividendPdfFetchBlocked(fetch_diagnostics)

    final_url = str(response.get("final_url") or response.get("url") or requested_url)
    final = urlparse(final_url)
    if (
        final.scheme.lower() != "https"
        or final_url.split("#", 1)[0] not in DIVIDEND_PDF_ALLOWED_FINAL_URLS
        or final.hostname not in {"big5.sse.com.cn", "static.sse.com.cn", "www.sse.com.cn"}
    ):
        raise ValueError("OFFICIAL_DIVIDEND_PDF_TLS_ORIGIN_MISMATCH")
    raw_pdf = response.get("body")
    if not isinstance(raw_pdf, bytes):
        raise ValueError("OFFICIAL_DIVIDEND_PDF_BYTES_MISSING")
    if (
        len(raw_pdf) != EXPECTED_DIVIDEND_PDF_SIZE
        or _sha256(raw_pdf) != EXPECTED_DIVIDEND_PDF_SHA256
        or not raw_pdf.startswith(b"%PDF-")
    ):
        raise ValueError("OFFICIAL_DIVIDEND_PDF_EXACT_BYTES_MISMATCH")

    followup_root.mkdir(parents=True, exist_ok=True)
    raw_dir = followup_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = raw_dir / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    pdf_path.write_bytes(raw_pdf)
    reader = PdfReader(str(pdf_path), strict=True)
    if len(reader.pages) != 3:
        raise ValueError("OFFICIAL_DIVIDEND_PDF_PAGE_COUNT_MISMATCH")

    dividend = {
        "source_id": source["source_id"],
        "source_class": "OFFICIAL_EXCHANGE",
        "expected_title": expected_row["TITLE"],
        "expected_security_code": "605016",
        "expected_listing_date": "2026-09-22",
        "status": "RAW_PDF_CAPTURED_NOT_ADMITTED",
        "listing_row": row,
        "final_pdf_url": final_url,
        "pdf_capture": {
            "url": final_url,
            "final_url": final_url,
            "requested_url": requested_url,
            "canonical_url": EXPECTED_DIVIDEND_PDF_URL,
            "status": "CAPTURED",
            "http_status": response.get("http_status"),
            "content_type": response.get("content_type"),
            "size_bytes": len(raw_pdf),
            "sha256": _sha256(raw_pdf),
        },
        "prior_adjudication": {
            "ledger_path": DIVIDEND_LEDGER_RELATIVE.as_posix(),
            "ledger_sha256": _sha256(ledger_raw),
            "listing_sha256": EXPECTED_DIVIDEND_LISTING_SHA256,
            "listing_size_bytes": EXPECTED_DIVIDEND_LISTING_SIZE,
            "listing_bytes_reverified_in_current_run": False,
            "fact_level_status": "ADMITTED_IN_CANONICAL_SOURCE_LEDGER",
        },
        "capture_mode": "PRIOR_CANONICAL_LISTING_ADJUDICATION_PLUS_CURRENT_OFFICIAL_HTTPS_CANDIDATE_PDF_REHASH",
    }
    capture_report = {
        "schema_version": "IIOS-605016-FOLLOWUP-SOURCE-CAPTURE-0.1",
        "case_id": CASE_ID,
        "case_cutoff_date": CUTOFF_DATE,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "capture_mode": dividend["capture_mode"],
        "prior_listing_bytes_reverified_in_current_run": False,
        "sources": [dividend],
    }
    (followup_root / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json").write_text(
        json.dumps(capture_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dividend, ledger


def _build_base_manifest_from_prior_dividend(
    attempt10_root: Path,
    base_out: Path,
    followup_root: Path,
    dividend: dict[str, Any],
    ledger: dict[str, Any],
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    """Repeat the unchanged B2 builder using the already-adjudicated dividend fact."""
    base_out.mkdir(parents=True, exist_ok=True)
    base_report = adjudicate_attempt10(attempt10_root, base_out)
    base_manifest = _read_obj(base_out / "SOURCE_ADJUDICATED_B2_CANDIDATE_MANIFEST.json")
    combined_root = base_out / "combined-evidence-root"
    shutil.copytree(attempt10_root, combined_root)
    pdf_raw = (followup_root / "raw" / "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf").read_bytes()
    pdf_sha = _sha256(pdf_raw)
    if len(pdf_raw) != EXPECTED_DIVIDEND_PDF_SIZE or pdf_sha != EXPECTED_DIVIDEND_PDF_SHA256:
        raise ValueError("OFFICIAL_DIVIDEND_PDF_CHANGED_BEFORE_B2")
    supplemental_relative = "raw/SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf"
    supplemental_target = combined_root / supplemental_relative
    if supplemental_target.exists():
        raise ValueError("SUPPLEMENTAL_RAW_PATH_COLLISION")
    supplemental_target.parent.mkdir(parents=True, exist_ok=True)
    supplemental_target.write_bytes(pdf_raw)

    source = ledger["source"]
    dividend_evidence = dict(ledger["evidence_record"])
    dividend_evidence.update({
        "basis": "Official SSE implementation notice: the exact PDF bytes were re-fetched from an allowlisted official SSE HTTPS URL and matched the SHA-256 already recorded in the canonical source adjudication. Source-listing row identity and date are reused from that prior canonical adjudication; its original raw listing bytes were not re-fetched in this run.",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_ref": final_url,
        "artifact_id": "ROUTE-A-FOLLOWUP:SSE-2026-09-22-DIVIDEND-IMPLEMENTATION:" + pdf_sha[:16],
        "capture_sha256": pdf_sha,
        "exact_bytes": True,
        "effective_from": "2026-09-29",
        "source_id": str(source["source_id"]),
        "source_origin_adjudication": "PASS_PRIOR_CANONICAL_SSE_LISTING_AND_CURRENT_ALLOWLISTED_OFFICIAL_HTTPS_EXACT_PDF_REHASH",
        "parents": [],
        "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
        "quality_notes": [
            "Exact raw PDF size/SHA-256 were reverified during this local run from the captured official SSE HTTPS endpoint.",
            "The original official listing row and its raw-byte hash come from the canonical prior adjudication; listing raw bytes were not reacquired because the query API was blocked.",
            "Official SSE source reuse remains restricted to non-redistributive internal fact-level use.",
            "The exact intraday first-public timestamp is not asserted; known_at remains date-only 2026-09-22.",
        ],
    })
    evidence = list(base_manifest.get("evidence") or [])
    if any(item.get("evidence_id") == dividend_evidence["evidence_id"] for item in evidence if isinstance(item, dict)):
        raise ValueError("CANONICAL_DIVIDEND_EVIDENCE_ID_COLLISION")
    evidence.append(dividend_evidence)
    raw_artifacts = list(base_manifest.get("raw_artifacts") or [])
    raw_artifacts.append({
        "evidence_id": dividend_evidence["evidence_id"],
        "relative_path": supplemental_relative,
        "expected_size_bytes": len(pdf_raw),
        "expected_sha256": pdf_sha,
    })
    combined_manifest = build_company_evidence_manifest(
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
    combined_manifest_path = base_out / "COMBINED_B2_CANDIDATE_MANIFEST.json"
    combined_manifest_path.write_text(
        json.dumps(combined_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "combined_b2_manifest_status": combined_manifest.get("status"),
        "validation_errors": list(combined_manifest.get("validation_errors") or []),
        "source_mode": "PRIOR_CANONICAL_DIVIDEND_ADJUDICATION_PLUS_CURRENT_DIRECT_PDF_REHASH",
        "prior_listing_bytes_reverified_in_current_run": False,
    }
    return summary, combined_root, combined_manifest


def adjudicate(attempt10_root: Path, out_dir: Path) -> dict[str, Any]:
    attempt10_root = attempt10_root.resolve(strict=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    followup_root = out_dir / "official-dividend-capture"
    followup_root.mkdir()
    dividend = official_dividend_capture(followup_root)
    base_out = out_dir / "base-b2"
    if dividend.get("status") == "RAW_PDF_CAPTURED_NOT_ADMITTED":
        capture_report = {
            "case_id": CASE_ID,
            "case_cutoff_date": CUTOFF_DATE,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "sources": [dividend],
        }
        (followup_root / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json").write_text(
            json.dumps(capture_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        base_out.mkdir()
        base_summary = adjudicate_attempt10_and_dividend(attempt10_root, followup_root, base_out)
        combined_root = base_out / "combined-evidence-root"
        combined_manifest_path = base_out / "COMBINED_B2_CANDIDATE_MANIFEST.json"
        combined_manifest = _read_obj(combined_manifest_path)
    elif (
        dividend.get("status") == "BLOCKED"
        and isinstance(dividend.get("listing_request"), dict)
        and dividend["listing_request"].get("status") == "BLOCKED"
    ):
        # The SSE listing API can be unreachable from some personal networks.
        # Reuse the repository's previously adjudicated listing/fact record while
        # re-fetching and exact-hash-verifying the official PDF directly over HTTPS.
        dividend, prior_ledger = _recover_dividend_from_prior_canonical_adjudication(followup_root)
        base_summary, combined_root, combined_manifest = _build_base_manifest_from_prior_dividend(
            attempt10_root, base_out, followup_root, dividend, prior_ledger
        )
        combined_manifest_path = base_out / "COMBINED_B2_CANDIDATE_MANIFEST.json"
    else:
        raise ValueError("OFFICIAL_DIVIDEND_SOURCE_CAPTURE_FAILED:" + str(dividend.get("status")))

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
            "capture_mode": dividend.get("capture_mode", "CURRENT_RUN_OFFICIAL_LISTING_AND_PDF_CAPTURE"),
            "listing_bytes_reverified_in_current_run": bool(
                (dividend.get("prior_adjudication") or {}).get("listing_bytes_reverified_in_current_run", True)
            ),
            "prior_dividend_ledger_sha256": (dividend.get("prior_adjudication") or {}).get("ledger_sha256"),
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
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
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
    try:
        report = adjudicate(args.attempt10_root, args.out_dir)
    except OfficialDividendPdfFetchBlocked as exc:
        # Source unavailability is a completed fail-closed outcome, not a PASS
        # and not an unhandled workflow crash. Publish only sanitized transport
        # categories so operators can distinguish DNS/TLS/HTTP failures.
        args.out_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "schema_version": "IIOS-605016-OFFICIAL-HTTPS-B2-ADJUDICATION-0.1",
            "case_id": CASE_ID,
            "cutoff_date": CUTOFF_DATE,
            "overall_status": "BLOCKED_SOURCE_FETCH",
            "reason": str(exc),
            "candidate_manifest_status": "NOT_CREATED",
            "source_fetch_diagnostics": exc.safe_diagnostics,
            "raw_source_bytes_uploaded": False,
            "numeric_quote_values_printed": False,
            "formal_signed_admission_created": False,
            "production_host_accepted": False,
            "decision_created": False,
            "human_approval_required": True,
            "auto_execution": False,
        }
        (args.out_dir / "OFFICIAL_HTTPS_B2_ADJUDICATION_REPORT.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({
            "status": "BLOCKED",
            "reason": str(exc),
            "source_fetch_diagnostics": exc.safe_diagnostics,
            "candidate_manifest_status": "NOT_CREATED",
            "raw_source_bytes_uploaded": False,
        }, ensure_ascii=False, indent=2))
        # The report itself is a blocked result. Workflow success means only
        # that the fail-closed adjudication outcome was recorded and sanitized.
        return 0
    # B2 fail-closed is a completed validation outcome; don't disguise a blocked
    # manifest as workflow success by setting PASS, nor fail to publish the report.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
