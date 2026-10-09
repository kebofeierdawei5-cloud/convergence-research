from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

SCHEMA_VERSION = "IIOS-PUBLIC-WEB-DISCOVERY-RECORD-0.1"
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
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Discover public candidate URLs. Search results are leads, never admitted evidence."""
    _validate_inputs(query, region, max_results, backend)
    query = query.strip()
    search_fn = search_fn or _ddgs_search
    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    rejected = 0
    failure_code = None
    try:
        raw_results = search_fn(query=query, region=region, max_results=max_results, backend=backend)
        if not isinstance(raw_results, list):
            raise PublicWebDiscoveryError("SEARCH_RESULT_SET_MUST_BE_A_LIST")
    except Exception as exc:
        raw_results = []
        failure_code = exc.code if isinstance(exc, PublicWebDiscoveryError) else type(exc).__name__

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

    status = "SEARCH_UNAVAILABLE" if failure_code else ("RESULTS_FOUND" if candidates else "NO_RESULTS")
    body = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "status": status,
        "query": query,
        "region": region,
        "backend": backend,
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
    if record.get("status") not in {"RESULTS_FOUND", "NO_RESULTS", "SEARCH_UNAVAILABLE"}:
        raise PublicWebDiscoveryError("DISCOVERY_STATUS_INVALID")
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
        "evidence_admission": False,
        "pit_admission": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if record["status"] == "RESULTS_FOUND" else 3


if __name__ == "__main__":
    raise SystemExit(main())
