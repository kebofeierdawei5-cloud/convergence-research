from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

TIMEOUT_SECONDS = 4
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "IIOS-official-endpoint-discovery/0.1"


class HttpsOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() != "https":
            raise URLError("HTTPS_REDIRECT_DOWNGRADE_BLOCKED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_https(url: str, *, referer: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return {"url": url, "status": "BLOCKED", "error": "HTTPS_URL_REQUIRED"}
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/javascript,*/*",
        "Referer": referer,
        "Accept-Encoding": "identity",
        "Connection": "close",
    })
    try:
        opener = build_opener(HttpsOnlyRedirectHandler())
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            final_url = str(response.geturl())
            if urlparse(final_url).scheme.lower() != "https":
                return {"url": url, "status": "BLOCKED", "error": "HTTPS_REDIRECT_DOWNGRADE_BLOCKED"}
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(64 * 1024, MAX_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    return {
                        "url": url, "status": "BLOCKED", "error": "DISCOVERY_RESOURCE_TOO_LARGE",
                        "http_status": int(getattr(response, "status", 0)),
                    }
                chunks.append(chunk)
            body = b"".join(chunks)
            return {
                "url": url, "final_url": final_url, "status": "CAPTURED",
                "http_status": int(getattr(response, "status", 0)),
                "content_type": str(response.headers.get("Content-Type", "")),
                "size_bytes": len(body), "sha256": sha256(body), "body": body,
            }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {"url": url, "status": "BLOCKED", "error": type(exc).__name__ + ":" + str(exc)[:240]}


def endpoint_candidates(payload: str, source_url: str) -> list[dict[str, str]]:
    patterns = [
        r"(?i)(?:https?:)?//[^\s\"'<>]{0,240}(?:query\.sse\.com\.cn|yunhq\.sse\.com\.cn)[^\s\"'<>]{0,240}",
        r"(?i)[A-Za-z0-9_./-]*(?:queryTradingByStockCodeData|stockDailyTransData|queryStockDaily|dayk|marketdata/tradedata)[A-Za-z0-9_./?=&%-]*",
        r"(?i)[A-Za-z0-9_./-]+\.do(?:\?[^\s\"'<>]{0,240})?",
    ]
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, payload):
            candidate = unescape(match.group(0)).replace("\\/", "/")
            candidate = candidate.rstrip(");,]")
            if len(candidate) > 400:
                candidate = candidate[:400]
            if candidate in seen:
                continue
            if not any(token in candidate.lower() for token in (
                "query.sse.com.cn", "yunhq.sse.com.cn", "querytrading", "stockdaily",
                "marketdata/tradedata", "dayk", "stockdata"
            )):
                continue
            seen.add(candidate)
            found.append({
                "source_url": source_url,
                "candidate": candidate,
                "candidate_type": "ENDPOINT_OR_API_PATH_NOT_FETCHED",
            })
            if len(found) >= 200:
                return found
    return found


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/605016-endpoint-discovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise SystemExit("OUTPUT_DIRECTORY_MUST_BE_EMPTY")

    urls = [
        "https://www.sse.com.cn/market/stockdata/overview/day/",
        "https://www.sse.com.cn/market/stockdata/overview/",
        "https://www.sse.com.cn/market/price/report/",
    ]
    report: dict[str, Any] = {
        "schema_version": "IIOS-SSE-OFFICIAL-HTTPS-ENDPOINT-DISCOVERY-0.1",
        "case_id": "RC-CN-A-605016-20261009",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "intent": "Discover the documented/actual same-origin HTTPS API used by official SSE pages for historical daily prices; no stock-price values are captured or emitted.",
        "https_only": True,
        "raw_html_or_javascript_persisted": False,
        "raw_market_price_values_captured": False,
        "pages": [],
        "scripts": [],
        "candidate_endpoints": [],
        "limitations": [
            "Endpoint strings discovered in page source are candidates only until response schema, date and quote fields are verified.",
            "This job does not download or persist daily price rows.",
            "Market-price admission remains BLOCKED until an authorized HTTPS path is independently verified and run through the unchanged B2/PIT validator.",
        ],
    }
    page_bodies: list[tuple[str, str]] = []
    script_urls: list[tuple[str, str]] = []
    for url in urls:
        response = fetch_https(url, referer="https://www.sse.com.cn/")
        report["pages"].append({k: v for k, v in response.items() if k != "body"})
        if response.get("status") != "CAPTURED":
            continue
        body_text = response["body"].decode("utf-8", errors="replace")
        page_bodies.append((url, body_text))
        for src in re.findall(r"<script\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", body_text, flags=re.I):
            script_url = urljoin(url, unescape(src.strip()))
            parsed = urlparse(script_url)
            if parsed.scheme.lower() != "https" or not parsed.hostname:
                continue
            if parsed.hostname == "www.sse.com.cn" or parsed.hostname.endswith(".sse.com.cn"):
                if script_url not in {x[0] for x in script_urls}:
                    script_urls.append((script_url, url))

    for script_url, referer in script_urls[:8]:
        response = fetch_https(script_url, referer=referer)
        item = {k: v for k, v in response.items() if k != "body"}
        item["resource_type"] = "JAVASCRIPT"
        report["scripts"].append(item)
        if response.get("status") == "CAPTURED":
            page_bodies.append((script_url, response["body"].decode("utf-8", errors="replace")))

    candidates: list[dict[str, str]] = []
    for source_url, payload in page_bodies:
        candidates.extend(endpoint_candidates(payload, source_url))
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in candidates:
        key = (row["source_url"], row["candidate"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
        if len(deduped) >= 250:
            break
    report["candidate_endpoints"] = deduped
    report["candidate_endpoint_count"] = len(deduped)
    report["status"] = "ENDPOINT_CANDIDATES_FOUND_NEED_VALIDATION" if deduped else "NO_OFFICIAL_ENDPOINT_FOUND"
    report_path = out_dir / "SSE_HTTPS_ENDPOINT_DISCOVERY_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "pages_captured": sum(1 for x in report["pages"] if x.get("status") == "CAPTURED"),
        "scripts_captured": sum(1 for x in report["scripts"] if x.get("status") == "CAPTURED"),
        "candidate_endpoint_count": report["candidate_endpoint_count"],
        "raw_html_or_javascript_persisted": False,
        "raw_market_price_values_captured": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
