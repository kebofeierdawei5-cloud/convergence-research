from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CASE_ID = "RC-CN-A-605016-20261009"
CUTOFF_DATE = "2026-10-09"
USER_AGENT = "IIOS-free-first-source-acquisition/0.1 (public-source provenance capture)"
TIMEOUT_SECONDS = 8
MAX_BYTES = 50 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, *, referer: str, max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Referer": referer,
        "Accept-Encoding": "identity",
    })
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", 0))
            content_type = str(response.headers.get("Content-Type", ""))
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                return {
                    "url": url, "http_status": status, "content_type": content_type,
                    "status": "BLOCKED", "error": "SOURCE_EXCEEDS_MAX_BYTES",
                }
            return {
                "url": url, "http_status": status, "content_type": content_type,
                "status": "CAPTURED" if 200 <= status < 300 else "BLOCKED",
                "size_bytes": len(body), "sha256": sha256(body), "bytes": body,
            }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "url": url, "status": "BLOCKED",
            "error": type(exc).__name__ + ":" + str(exc)[:300],
        }


def save_bytes(root: Path, relative_path: str, body: bytes) -> str:
    p = root / relative_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return relative_path


def parse_json_or_jsonp(raw: bytes) -> Any:
    text = raw.decode("utf-8-sig", errors="strict").strip()
    # SSE public APIs can wrap JSON in a JSONP callback.
    if text.startswith("{") or text.startswith("["):
        return json.loads(text)
    first = text.find("(")
    last = text.rfind(")")
    if first >= 0 and last > first:
        return json.loads(text[first + 1:last])
    raise ValueError("PUBLIC_API_RESPONSE_NOT_JSON_OR_JSONP")


def walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def extract_dividend_row(payload: Any) -> dict[str, Any] | None:
    candidates = []
    for obj in walk_dicts(payload):
        flat = {str(k).upper(): v for k, v in obj.items()}
        text = " ".join(str(v) for v in obj.values() if isinstance(v, (str, int, float)))
        if ("605016" in text or "百龙创园" in text) and "权益分派实施公告" in text:
            candidates.append(obj)
        elif str(flat.get("SECURITY_CODE", "")) == "605016" and "权益分派实施公告" in str(flat.get("TITLE", "")):
            candidates.append(obj)
    return candidates[0] if candidates else None


def candidate_url(row: dict[str, Any]) -> str | None:
    for key in ("URL", "url", "PDFURL", "PDF_URL", "FILEURL", "FILE_URL", "CONTENT", "content"):
        value = row.get(key)
        if isinstance(value, str) and ".pdf" in value.lower():
            return urljoin("https://www.sse.com.cn/", value)
    for value in row.values():
        if isinstance(value, str) and ".pdf" in value.lower():
            return urljoin("https://www.sse.com.cn/", value)
    return None


def official_dividend_capture(root: Path) -> dict[str, Any]:
    params = {
        "jsonCallBack": "iiosSourceCapture",
        "isPagination": "true",
        "productId": "605016",
        "securityType": "0101,120200",
        "reportType": "ALL",
        "beginDate": "2026-09-22",
        "endDate": "2026-09-22",
        "pageHelp.pageSize": "100",
        "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.cacheSize": "1",
        "pageHelp.endPage": "1",
    }
    api_url = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do?" + urlencode(params)
    listing = fetch(api_url, referer="https://www.sse.com.cn/disclosure/listedinfo/announcement/index.shtml")
    report: dict[str, Any] = {
        "source_id": "SSE-2026-09-22-DIVIDEND-IMPLEMENTATION",
        "source_class": "OFFICIAL_EXCHANGE",
        "expected_title": "2026年半年度权益分派实施公告",
        "expected_security_code": "605016",
        "expected_listing_date": "2026-09-22",
        "listing_request": {k: v for k, v in listing.items() if k != "bytes"},
        "status": "BLOCKED",
    }
    if listing.get("status") != "CAPTURED":
        return report
    raw = listing["bytes"]
    save_bytes(root, "raw/SSE-2026-09-22-announcement-query.bin", raw)
    try:
        payload = parse_json_or_jsonp(raw)
        row = extract_dividend_row(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        report["listing_parse_error"] = str(exc)
        report["listing_payload_sha256"] = sha256(raw)
        return report
    report["listing_payload_sha256"] = sha256(raw)
    report["listing_payload_bytes"] = len(raw)
    if not row:
        # Keep a small response excerpt for diagnostics; never treat it as
        # proof that the expected notice was found.
        report["status"] = "BLOCKED_NOTICE_ROW_NOT_FOUND"
        report["rows_returned"] = [
            obj for obj in walk_dicts(payload)
            if "605016" in json.dumps(obj, ensure_ascii=False) or "百龙创园" in json.dumps(obj, ensure_ascii=False)
        ][:20]
        return report
    report["listing_row"] = row
    link = candidate_url(row)
    report["resolved_pdf_url"] = link
    if not link:
        report["status"] = "BLOCKED_PDF_URL_NOT_FOUND_IN_OFFICIAL_LISTING"
        return report
    basename = str(link).rsplit("/", 1)[-1]
    static_url = "https://static.sse.com.cn/stock/disclosure/announcement/c/202609/" + basename
    big5_url = "https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-09-22/" + basename
    report["pdf_fetch_attempts"] = []
    chosen = None
    for index, candidate_url_value in enumerate([link, static_url, big5_url]):
        response = fetch(candidate_url_value, referer="https://www.sse.com.cn/disclosure/listedinfo/announcement/index.shtml")
        report["pdf_fetch_attempts"].append({k: v for k, v in response.items() if k != "bytes"})
        if response.get("status") != "CAPTURED":
            continue
        body = response["bytes"]
        if body.startswith(b"%PDF-"):
            chosen = response
            break
        save_bytes(root, f"raw/SSE-2026-09-22-response-{index}.bin", body)
        report.setdefault("non_pdf_responses", []).append({
            "url": candidate_url_value,
            "raw_size_bytes": len(body),
            "raw_sha256": sha256(body),
            "classification": "EXPECTED_PDF_BUT_RECEIVED_NON_PDF_BYTES",
        })
    if chosen is None:
        report["status"] = "BLOCKED_NO_VERIFIED_PDF_BYTES"
        return report
    body = chosen["bytes"]
    save_bytes(root, "raw/SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf", body)
    report["final_pdf_url"] = chosen["url"]
    report["pdf_capture"] = {k: v for k, v in chosen.items() if k != "bytes"}
    report["pdf_magic"] = body[:8].decode("ascii", errors="replace")
    report["status"] = "RAW_PDF_CAPTURED_NOT_ADMITTED"
    report["important_limit"] = "Captured raw bytes still require independent body/date/fact-locator and reuse adjudication."
    return report
    body = pdf["bytes"]
    if not body.startswith(b"%PDF-"):
        save_bytes(root, "raw/SSE-2026-09-22-dividend-response-not-pdf.bin", body)
        report["status"] = "BLOCKED_EXPECTED_PDF_BYTES"
        report["actual_prefix_hex"] = body[:24].hex()
        return report
    save_bytes(root, "raw/SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf", body)
    report["final_pdf_url"] = pdf["url"]
    report["pdf_capture"] = {k: v for k, v in pdf.items() if k != "bytes"}
    report["pdf_magic"] = body[:8].decode("ascii", errors="replace")
    report["status"] = "RAW_PDF_CAPTURED_NOT_ADMITTED"
    report["important_limit"] = "Byte capture and official listing match do not alone admit implementation facts; the PDF body/date/issuer/fact locators and reuse disposition still require independent review."
    return report
    body = pdf["bytes"]
    save_bytes(root, "raw/SSE-2026-09-22-DIVIDEND-IMPLEMENTATION.pdf", body)
    if not body.startswith(b"%PDF-"):
        report["status"] = "BLOCKED_EXPECTED_PDF_BYTES"
        report["actual_prefix_hex"] = body[:24].hex()
        return report
    report["pdf_magic"] = body[:8].decode("ascii", errors="replace")
    report["status"] = "RAW_PDF_CAPTURED_NOT_ADMITTED"
    report["important_limit"] = "Byte capture and official listing match do not alone admit implementation facts; the PDF body/date/issuer/fact locators and reuse disposition still require independent review."
    return report


def official_exchange_price_capture(root: Path) -> dict[str, Any]:
    """Capture a pre-cutoff close from the official SSE service; never admit plain-HTTP bytes."""
    params = (
        "?begin=20261008&end=20261008"
        "&select=date,open,high,low,close,volume,amount"
    )
    secure_urls = [
        "https://yunhq.sse.com.cn/v1/sh1/dayk/605016" + params,
        "https://yunhq.sse.com.cn:32041/v1/sh1/dayk/605016" + params,
        "https://query.sse.com.cn/marketdata/tradedata/data/stockDailyTransData.do?"
        "isPagination=false&productId=605016&startDate=2026-10-08&endDate=2026-10-08",
    ]
    attempts: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    secure = False
    for url in secure_urls:
        candidate = fetch(url, referer="https://www.sse.com.cn/market/stockdata/overview/day/")
        attempts.append({k: v for k, v in candidate.items() if k != "bytes"})
        if candidate.get("status") == "CAPTURED":
            result = candidate
            secure = True
            break

    if result is None:
        # Diagnostic-only fallback: keep the response hash for troubleshooting,
        # but never pass an unencrypted transport payload into the B2 manifest.
        url = "http://yunhq.sse.com.cn:32041/v1/sh1/dayk/605016" + params
        candidate = fetch(url, referer="https://www.sse.com.cn/market/stockdata/overview/day/")
        attempts.append({k: v for k, v in candidate.items() if k != "bytes"})
        if candidate.get("status") == "CAPTURED":
            result = candidate
            secure = False

    record: dict[str, Any] = {
        "source_id": "PRICE-SSE-OFFICIAL-DAYK-2026-10-08",
        "source_class": "OFFICIAL_EXCHANGE_MARKET_DATA_CANDIDATE",
        "expected_observation_date": "2026-10-08",
        "status": "BLOCKED",
        "secure_transport_verified": bool(secure),
        "capture_attempts": attempts,
    }
    if result is None:
        record["capture"] = "NO_ENDPOINT_RETURNED_BYTES"
        return record

    raw = result["bytes"]
    record["url"] = result["url"]
    record["capture"] = {k: v for k, v in result.items() if k != "bytes"}
    record["saved_path"] = "raw/PRICE-SSE-DAYK-605016-2026-10-08.bin"
    save_bytes(root, record["saved_path"], raw)
    record["payload_sha256"] = sha256(raw)
    record["size_bytes"] = len(raw)
    try:
        payload = parse_json_or_jsonp(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        record["status"] = "CAPTURED_UNPARSED_OFFICIAL_RESPONSE" if secure else "BLOCKED_HTTP_TRANSPORT_NOT_ADMISSIBLE"
        record["parse_error"] = str(exc)
        record["payload_prefix"] = raw[:1000].decode("utf-8", errors="replace")
        return record

    matches: list[dict[str, Any]] = []
    target_digits = "20261008"

    def visit(node: Any, pointer: str = "$") -> None:
        if isinstance(node, dict):
            norm = {str(k).lower(): v for k, v in node.items()}
            date_value = next((norm[k] for k in ("date", "trade_date", "tradedate", "tradingdate", "dt") if k in norm), None)
            if str(date_value).replace("-", "") == target_digits:
                matches.append({"path": pointer, "row": node})
            for key, value in node.items():
                visit(value, f"{pointer}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                if isinstance(value, list) and value and str(value[0]).replace("-", "") == target_digits:
                    matches.append({
                        "path": f"{pointer}[{i}]",
                        "row": {
                            "date": value[0],
                            "open": value[1] if len(value) > 1 else None,
                            "high": value[2] if len(value) > 2 else None,
                            "low": value[3] if len(value) > 3 else None,
                            "close": value[4] if len(value) > 4 else None,
                            "volume": value[5] if len(value) > 5 else None,
                            "amount": value[6] if len(value) > 6 else None,
                            "field_order_assumption": "date,open,high,low,close,volume,amount",
                        },
                    })
                visit(value, f"{pointer}[{i}]")

    visit(payload)
    record["payload_preview"] = payload
    record["matches"] = matches
    if len(matches) != 1:
        record["status"] = "CAPTURED_NO_SINGLE_MATCHING_DATE_ROW" if secure else "BLOCKED_HTTP_TRANSPORT_NOT_ADMISSIBLE"
    elif secure:
        record["status"] = "OFFICIAL_DATE_ROW_CANDIDATE_NOT_ADMITTED"
        record["admission_note"] = "Secure official endpoint and exact date row captured; source first-public availability time and source-specific reuse conditions still require review before B2 admission."
    else:
        record["status"] = "BLOCKED_HTTP_TRANSPORT_NOT_ADMISSIBLE"
        record["admission_note"] = "The endpoint returned a matching historical row over unencrypted HTTP. The repository source-intake contract requires HTTPS, so this result is not an admissible B2 source even though the host is the official SSE domain."
    return record


def public_secondary_price_capture(root: Path) -> dict[str, Any]:
    # Free, keyless Eastmoney historical-kline endpoint is a cross-check only,
    # not an exchange-origin assertion and not automatically decision-grade.
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        "secid=1.605016&klt=101&fqt=0&lmt=120&end=20261009&beg=20260901"
        "&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6"
        "&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61"
    )
    result = fetch(url, referer="https://quote.eastmoney.com/sh605016.html")
    if result.get("status") != "CAPTURED":
        first_attempt = {k: v for k, v in result.items() if k != "bytes"}
        result = fetch(url, referer="https://quote.eastmoney.com/sh605016.html")
        result["first_attempt"] = first_attempt
    record: dict[str, Any] = {
        "source_id": "PRICE-EASTMONEY-KLINE-605016",
        "source_class": "PUBLIC_SECONDARY",
        "url": url,
        "expected_observation_date": "2026-10-09",
        "license_reuse_status": "UNKNOWN_UNTIL_TERMS_REVIEW",
        "source_authority": "SECONDARY_AGGREGATOR_NOT_EXCHANGE_ORIGIN",
        "status": "BLOCKED",
        "capture": {k: v for k, v in result.items() if k != "bytes"},
    }
    if result.get("status") != "CAPTURED":
        return record
    raw = result["bytes"]
    save_bytes(root, "raw/PRICE-EASTMONEY-KLINE-605016.json", raw)
    record["saved_path"] = "raw/PRICE-EASTMONEY-KLINE-605016.json"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        record["status"] = "BLOCKED_PRICE_RESPONSE_NOT_JSON"
        record["parse_error"] = str(exc)
        return record
    record["payload_sha256"] = sha256(raw)
    data = (payload.get("data") or {})
    klines = data.get("klines") or []
    matched = []
    for line in klines:
        if isinstance(line, str) and line.split(",", 1)[0] == "2026-10-09":
            cells = line.split(",")
            matched.append({
                "raw_kline": line,
                "date": cells[0],
                "close": cells[2] if len(cells) > 2 else None,
                "open": cells[1] if len(cells) > 1 else None,
                "high": cells[3] if len(cells) > 3 else None,
                "low": cells[4] if len(cells) > 4 else None,
                "volume": cells[5] if len(cells) > 5 else None,
                "amount": cells[6] if len(cells) > 6 else None,
            })
    record["matched_rows"] = matched
    if len(matched) != 1:
        record["status"] = "BLOCKED_EXPECTED_SINGLE_PRICE_ROW_NOT_FOUND"
    else:
        record["status"] = "CANDIDATE_CROSSCHECK_NOT_ADMITTED"
        record["admission_decision"] = "Do not promote to ADMITTED until source terms/reuse, date/field semantics and source authority are independently accepted."
    return record


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/605016-followup-capture")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit("OUTPUT_DIRECTORY_MUST_BE_EMPTY")
    report: dict[str, Any] = {
        "schema_version": "IIOS-605016-FOLLOWUP-SOURCE-CAPTURE-0.1",
        "case_id": CASE_ID,
        "case_cutoff_date": CUTOFF_DATE,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "network_calls_are_public_and_keyless": True,
        "sources": [],
        "final_status": "BLOCKED_UNTIL_INDEPENDENT_REVIEW",
        "non_claims": [
            "This acquisition does not change evidence status or B2/PIT rules.",
            "A source listing row, successful download, file magic or hash proves neither first-public time nor fact-level truth.",
            "The secondary price source is a cross-check only; underlying source authority and reuse remain unadmitted.",
            "Raw source bytes are written only to the temporary workflow artifact, never committed to Git.",
        ],
    }
    dividend = official_dividend_capture(out)
    report["sources"].append(dividend)
    official_price = official_exchange_price_capture(out)
    report["sources"].append(official_price)
    price = public_secondary_price_capture(out)
    report["sources"].append(price)
    report["raw_files"] = []
    for p in sorted((out / "raw").glob("*")) if (out / "raw").exists() else []:
        data = p.read_bytes()
        report["raw_files"].append({
            "path": str(p.relative_to(out)),
            "size_bytes": len(data),
            "sha256": sha256(data),
        })
    report_path = out / "FOLLOWUP_SOURCE_CAPTURE_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "final_status": report["final_status"],
        "dividend_status": dividend.get("status"),
        "dividend_url": dividend.get("resolved_pdf_url"),
        "dividend_final_pdf_url": dividend.get("final_pdf_url"),
        "official_price_status": official_price.get("status"),
        "official_price_matches": official_price.get("matches"),
        "price_status": price.get("status"),
        "price_rows": price.get("matched_rows"),
        "raw_files": report["raw_files"],
    }, ensure_ascii=False, indent=2))
    # Acquisition is diagnostic until independently adjudicated. An unsuccessful
    # official fetch must be visible in the artifact, not silently converted to PASS.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
