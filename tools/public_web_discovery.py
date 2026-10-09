from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

SCHEMA_VERSION = "IIOS-PUBLIC-WEB-DISCOVERY-RECORD-0.2"
TOOL_VERSION = "IIOS-PUBLIC-WEB-DISCOVERY-0.1"
MAX_QUERY_CHARS = 500
MAX_RESULTS = 25
REGION_RE = re.compile(r"^[a-z]{2}-[a-z]{2}$")


class PublicWebDiscoveryError(ValueError):
    """Input or discovery-record contract violation."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _public_http_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return None
        # Fragments are browser-local state, not part of the source locator.
        return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, ""))
    except (ValueError, UnicodeError):
        return None


def _ddgs_search(query: str, *, region: str, max_results: int, backend: str) -> list[dict[str, Any]]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise PublicWebDiscoveryError("PUBLIC_SEARCH_DEPENDENCY_MISSING") from exc
    # DDGS queries public search engines; it does not require an LLM provider endpoint or API key.
    # Search availability is best-effort and can be rate-limited by upstream public engines.
    return list(DDGS(timeout=8).text(
        query=query,
        region=region,
        max_results=max_results,
        backend=backend,
    ))



class _BingResultsParser(HTMLParser):
    """Best-effort parser for public Bing HTML result cards."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self.current = None
        self.in_title = False
        self.in_anchor = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if tag == "li" and "b_algo" in classes:
            self.current = {"title": [], "snippet": [], "href": ""}
            self.in_title = self.in_anchor = self.in_snippet = False
            return
        if self.current is None:
            return
        if tag == "h2":
            self.in_title = True
        elif tag == "a" and self.in_title and not self.current["href"]:
            self.current["href"] = attr.get("href") or ""
            self.in_anchor = True
        elif tag == "p":
            self.in_snippet = True

    def handle_data(self, data):
        if self.current is None:
            return
        if self.in_anchor:
            self.current["title"].append(data)
        if self.in_snippet:
            self.current["snippet"].append(data)

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == "a":
            self.in_anchor = False
        elif tag == "h2":
            self.in_title = self.in_anchor = False
        elif tag == "p":
            self.in_snippet = False
        elif tag == "li":
            title = " ".join("".join(self.current["title"]).split())
            snippet = " ".join("".join(self.current["snippet"]).split())
            href = str(self.current.get("href") or "")
            if title and href:
                self.results.append({"title": title, "href": href, "body": snippet})
            self.current = None
            self.in_title = self.in_anchor = self.in_snippet = False


def _safe_error_detail(value):
    text = " ".join(str(value or "").replace(chr(0), " ").split())
    text = re.sub(r"(?i)(api[_-]?key|token|password|secret|authorization)=([^&\\s]+)", r"\\1=[REDACTED]", text)
    return text[:240]


def _bing_html_search(query: str, *, region: str, max_results: int, backend: str = "bing-html") -> list[dict[str, Any]]:
    """No-key fallback via Bing's public HTML page; upstream may rate-limit or change markup."""
    params = urlencode({
        "q": query,
        "count": min(max_results, 25),
        "setlang": "zh-hans" if region.endswith("-zh") else "en",
        "cc": "CN" if region.startswith("cn-") else "US",
    })
    request = Request(
        "https://www.bing.com/search?" + params,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; IIOS-Public-Research/0.2)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            status = int(getattr(response, "status", getattr(response, "code", 0)))
            if status < 200 or status >= 300:
                raise PublicWebDiscoveryError(f"BING_HTTP_STATUS_{status}")
            html = response.read(2 * 1024 * 1024 + 1)
    except PublicWebDiscoveryError:
        raise
    except HTTPError as exc:
        raise PublicWebDiscoveryError(f"BING_HTTP_STATUS_{exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PublicWebDiscoveryError("BING_PUBLIC_HTML_FETCH_FAILED:" + _safe_error_detail(exc)) from exc
    if len(html) > 2 * 1024 * 1024:
        raise PublicWebDiscoveryError("BING_HTML_RESPONSE_TOO_LARGE")
    parser = _BingResultsParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    if not parser.results:
        raise PublicWebDiscoveryError("BING_HTML_NO_USABLE_RESULTS")
    return parser.results[:max_results]


def _validate_inputs(query: str, region: str, max_results: int, backend: str) -> None:
    if not isinstance(query, str) or not query.strip() or len(query.strip()) > MAX_QUERY_CHARS:
        raise PublicWebDiscoveryError("QUERY_MUST_BE_1_TO_500_CHARACTERS")
    if not isinstance(region, str) or not REGION_RE.fullmatch(region):
        raise PublicWebDiscoveryError("REGION_MUST_LOOK_LIKE_LL-LL")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= MAX_RESULTS:
        raise PublicWebDiscoveryError("MAX_RESULTS_MUST_BE_1_TO_25")
    if not isinstance(backend, str) or not backend.strip() or len(backend) > 80:
        raise PublicWebDiscoveryError("BACKEND_INVALID")


def discover_public_web(
    query: str,
    *,
    region: str = "cn-zh",
    max_results: int = 10,
    backend: str = "auto",
    search_fn: Callable[..., list[dict[str, Any]]] | None = None,
    bing_fn: Callable[..., list[dict[str, Any]]] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Discover public candidate URLs. Search results are leads, never admitted evidence."""
    _validate_inputs(query, region, max_results, backend)
    query = query.strip()
    injected_search = search_fn is not None
    primary_search = search_fn or _ddgs_search
    fallback_search = bing_fn or _bing_html_search
    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    rejected = 0
    failure_code = None
    raw_results = []
    primary_error = None
    try:
        raw_results = primary_search(query=query, region=region, max_results=max_results, backend=backend)
        if not isinstance(raw_results, list):
            raise PublicWebDiscoveryError("SEARCH_RESULT_SET_MUST_BE_A_LIST")
    except Exception as exc:
        raw_results = []
        primary_code = getattr(exc, "code", str(exc) or type(exc).__name__) if isinstance(exc, PublicWebDiscoveryError) else type(exc).__name__
        primary_error = f"{primary_code}:{_safe_error_detail(exc)}"

    backend_used = "injected_search" if injected_search else "ddgs"
    if not injected_search and not raw_results:
        try:
            raw_results = fallback_search(query=query, region=region, max_results=max_results, backend="bing-html")
            if not isinstance(raw_results, list):
                raise PublicWebDiscoveryError("SEARCH_RESULT_SET_MUST_BE_A_LIST")
            if not raw_results:
                raise PublicWebDiscoveryError("BING_HTML_NO_USABLE_RESULTS")
            backend_used = "bing_html_fallback"
        except Exception as exc:
            fallback_code = getattr(exc, "code", str(exc) or type(exc).__name__) if isinstance(exc, PublicWebDiscoveryError) else type(exc).__name__
            fallback_error = f"{fallback_code}:{_safe_error_detail(exc)}"
            raw_results = []
            failure_code = "PUBLIC_SEARCH_BACKENDS_UNAVAILABLE"
            failure_code += f";DDGS={primary_error or 'NO_RESULTS'};BING={fallback_error}"
            backend_used = "none"
    elif primary_error:
        failure_code = primary_code if "primary_code" in locals() else "PUBLIC_SEARCH_UNAVAILABLE"

    for item in raw_results:
        if not isinstance(item, Mapping):
            rejected += 1
            continue
        url = _public_http_url(item.get("href") or item.get("url"))
        if url is None or url in seen_urls:
            rejected += 1
            continue
        seen_urls.add(url)
        title = str(item.get("title") or "").strip()[:500]
        snippet = str(item.get("body") or item.get("snippet") or "").strip()[:3000]
        candidates.append({
            "rank": len(candidates) + 1,
            "title": title,
            "url": url,
            "snippet": snippet,
            "https_candidate": url.startswith("https://"),
            "discovery_only": True,
        })
        if len(candidates) >= max_results:
            break

    if candidates:
        status = "RESULTS_FOUND"
        failure_code = None
    else:
        status = "SEARCH_UNAVAILABLE" if failure_code else "NO_RESULTS"
    body = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "status": status,
        "query": query,
        "region": region,
        "backend": backend,
        "backend_used": backend_used,
        "captured_at": captured_at,
        "results": candidates,
        "discarded_candidate_count": rejected,
        "failure_code": failure_code,
        "contract": {
            "public_search_no_llm_endpoint": True,
            "provider_api_key_required": False,
            "search_results_are_source_leads_only": True,
            "source_bytes_captured": False,
            "evidence_admission": False,
            "pit_admission": False,
            "automatic_manifest_mutation": False,
        },
    }
    body["audit"] = {"record_sha256": _sha256(_canonical_bytes(body))}
    return body


def verify_discovery_record(record: Any) -> None:
    if not isinstance(record, dict):
        raise PublicWebDiscoveryError("DISCOVERY_RECORD_MUST_BE_OBJECT")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise PublicWebDiscoveryError("DISCOVERY_SCHEMA_VERSION_MISMATCH")
    if record.get("tool_version") != TOOL_VERSION:
        raise PublicWebDiscoveryError("DISCOVERY_TOOL_VERSION_MISMATCH")
    if record.get("status") not in {"RESULTS_FOUND", "NO_RESULTS", "SEARCH_UNAVAILABLE"}:
        raise PublicWebDiscoveryError("DISCOVERY_STATUS_INVALID")
    if record.get("backend_used") not in {"ddgs", "bing_html_fallback", "injected_search", "none"}:
        raise PublicWebDiscoveryError("DISCOVERY_BACKEND_USED_INVALID")
    contract = record.get("contract")
    if not isinstance(contract, dict) or contract != {
        "public_search_no_llm_endpoint": True,
        "provider_api_key_required": False,
        "search_results_are_source_leads_only": True,
        "source_bytes_captured": False,
        "evidence_admission": False,
        "pit_admission": False,
        "automatic_manifest_mutation": False,
    }:
        raise PublicWebDiscoveryError("DISCOVERY_MUST_NOT_CLAIM_ADMISSION")
    audit = record.get("audit")
    if not isinstance(audit, dict) or set(audit) != {"record_sha256"}:
        raise PublicWebDiscoveryError("DISCOVERY_AUDIT_INVALID")
    body = {key: value for key, value in record.items() if key != "audit"}
    if audit.get("record_sha256") != _sha256(_canonical_bytes(body)):
        raise PublicWebDiscoveryError("DISCOVERY_RECORD_HASH_MISMATCH")
    results = record.get("results")
    if not isinstance(results, list) or len(results) > MAX_RESULTS:
        raise PublicWebDiscoveryError("DISCOVERY_RESULTS_INVALID")
    seen: set[str] = set()
    for expected_rank, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            raise PublicWebDiscoveryError("DISCOVERY_RESULT_INVALID")
        if item.get("rank") != expected_rank or item.get("discovery_only") is not True:
            raise PublicWebDiscoveryError("DISCOVERY_RESULT_RANK_OR_SCOPE_INVALID")
        url = _public_http_url(item.get("url"))
        if url is None or url != item.get("url") or url in seen:
            raise PublicWebDiscoveryError("DISCOVERY_RESULT_URL_INVALID_OR_DUPLICATED")
        seen.add(url)
        if item.get("https_candidate") is not url.startswith("https://"):
            raise PublicWebDiscoveryError("DISCOVERY_RESULT_SCHEME_FLAG_MISMATCH")
    if record["status"] == "RESULTS_FOUND" and not results:
        raise PublicWebDiscoveryError("DISCOVERY_RESULTS_STATUS_MISMATCH")
    if record["status"] == "NO_RESULTS" and (results or record.get("failure_code")):
        raise PublicWebDiscoveryError("DISCOVERY_EMPTY_STATUS_MISMATCH")
    if record["status"] == "SEARCH_UNAVAILABLE" and not record.get("failure_code"):
        raise PublicWebDiscoveryError("DISCOVERY_FAILURE_CODE_REQUIRED")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Free-first public web search for candidate URLs; no LLM provider endpoint or API key is used."
    )
    parser.add_argument("--query", required=True, help="Company/source query; one query per run")
    parser.add_argument("--region", default="cn-zh", help="Public search region, e.g. cn-zh or us-en")
    parser.add_argument("--backend", default="auto", help="Public search engine selection passed to DDGS, default auto")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--out", required=True, help="New JSON output file; existing files are never overwritten")
    args = parser.parse_args()
    destination = Path(args.out)
    try:
        if destination.exists():
            raise PublicWebDiscoveryError("OUTPUT_FILE_ALREADY_EXISTS")
        record = discover_public_web(
            args.query,
            region=args.region,
            backend=args.backend,
            max_results=args.max_results,
        )
        verify_discovery_record(record)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except (OSError, PublicWebDiscoveryError) as exc:
        print(json.dumps({"status": "PUBLIC_DISCOVERY_BLOCKED", "error_code": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "status": record["status"],
        "results": len(record["results"]),
        "candidate_receipt": str(destination),
        "backend_used": record["backend_used"],
        "failure_code": record["failure_code"],
        "evidence_admission": False,
        "pit_admission": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if record["status"] == "RESULTS_FOUND" else 3


if __name__ == "__main__":
    raise SystemExit(main())
