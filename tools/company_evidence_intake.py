from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

TOOL_VERSION = "IIOS-COMPANY-EVIDENCE-INTAKE-0.1"
MANIFEST_SCHEMA = "IIOS-COMPANY-EVIDENCE-INTAKE-MANIFEST-0.1"
RECEIPT_SCHEMA = "IIOS-COMPANY-EVIDENCE-INTAKE-RECEIPT-0.1"
MAX_SOURCE_BYTES = 50 * 1024 * 1024
MAX_SOURCES = 100
UTC_PLUS_8 = timezone(timedelta(hours=8))
SOURCE_CLASSES = {
    "OFFICIAL_EXCHANGE",
    "ISSUER_PRIMARY",
    "REGULATOR_PRIMARY",
    "OFFICIAL_DATABASE",
    "PUBLIC_SECONDARY",
    "OPERATOR_SUPPLIED",
}
LICENSE_STATUSES = {
    "REDISTRIBUTION_ALLOWED",
    "PUBLIC_ACCESS_REUSE_UNKNOWN",
    "OPERATOR_SUPPLIED_RIGHTS_CONFIRMED",
    "RESTRICTED_NO_REDISTRIBUTION",
    "UNKNOWN",
}
FIELD_GROUPS = (
    "security_identity",
    "market_price",
    "corporate_disclosures",
    "business_reality",
    "financial_reality",
    "capital_structure",
    "trust_governance_events",
)
SAFE_SUFFIXES = {".pdf", ".xls", ".xlsx", ".csv", ".json", ".html", ".htm", ".xml", ".doc", ".docx", ".zip", ".txt", ".parquet"}
SENSITIVE_QUERY_KEYS = {
    "access_token", "token", "api_key", "apikey", "authorization",
    "signature", "sig", "password", "secret", "x-amz-credential",
    "x-amz-signature",
}


class IntakeError(ValueError):
    """Invalid intake contract or unsafe input; no evidence is admitted."""


class SourceCaptureError(RuntimeError):
    """An external or local source could not be captured safely."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _HTTPSOnlyRedirectHandler(HTTPRedirectHandler):
    """Follow HTTPS redirects but reject protocol downgrade."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() != "https":
            raise SourceCaptureError("HTTPS_REDIRECT_DOWNGRADE_BLOCKED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IntakeError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _load_json_strict(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(IntakeError("NONFINITE_JSON_NUMBER")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeError("INVALID_UTF8_JSON") from exc


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise IntakeError(f"INVALID_{label.upper()}_DATE") from exc


def _parse_known_at(value: Any):
    """Return a date or timezone-aware datetime. Date-only values retain day precision."""
    raw = _text(value)
    if not raw:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return _parse_date(raw, "known_at")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntakeError("KNOWN_AT_MUST_BE_ISO_DATE_OR_TIMEZONE_AWARE_DATETIME") from exc
    if parsed.tzinfo is None:
        raise IntakeError("KNOWN_AT_DATETIME_MUST_INCLUDE_TIMEZONE")
    return parsed


def _validate_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise IntakeError("SOURCE_URL_MUST_USE_HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise IntakeError("SOURCE_URL_USERINFO_FORBIDDEN")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            raise IntakeError("POSSIBLE_CREDENTIAL_IN_SOURCE_URL")


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise IntakeError("MANIFEST_MUST_BE_OBJECT")
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise IntakeError("UNSUPPORTED_MANIFEST_SCHEMA")
    market = manifest.get("market")
    symbol = _text(manifest.get("symbol")).upper()
    if market not in {"CN-A", "HK"}:
        raise IntakeError("MARKET_MUST_BE_CN_A_OR_HK")
    if market == "CN-A" and not re.fullmatch(r"\d{6}(?:\.(?:SH|SZ|BJ))?", symbol):
        raise IntakeError("INVALID_CN_A_SYMBOL")
    if market == "HK" and not re.fullmatch(r"\d{4,5}(?:\.HK)?", symbol):
        raise IntakeError("INVALID_HK_SYMBOL")
    cutoff = _parse_date(manifest.get("cutoff_date"), "cutoff")
    if cutoff > date.today():
        raise IntakeError("FUTURE_CUTOFF_NOT_ALLOWED")
    expected_case_id = f"RC-{market}-{symbol.replace('.', '-')}-{cutoff.strftime('%Y%m%d')}"
    if manifest.get("case_id") != expected_case_id:
        raise IntakeError("CASE_ID_MARKET_SYMBOL_CUTOFF_MISMATCH")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources or len(sources) > MAX_SOURCES:
        raise IntakeError("SOURCES_MUST_CONTAIN_1_TO_100_ITEMS")
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise IntakeError("SOURCE_SPEC_MUST_BE_OBJECT")
        source_id = _text(source.get("source_id"))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", source_id):
            raise IntakeError("INVALID_SOURCE_ID")
        if source_id in seen:
            raise IntakeError("DUPLICATE_SOURCE_ID")
        seen.add(source_id)
        if source.get("field_group") not in FIELD_GROUPS:
            raise IntakeError("INVALID_FIELD_GROUP")
        if not _text(source.get("source_ref")):
            raise IntakeError("SOURCE_REF_REQUIRED")
        if source.get("source_class") not in SOURCE_CLASSES:
            raise IntakeError("INVALID_SOURCE_CLASS")
        if source.get("license_status") not in LICENSE_STATUSES:
            raise IntakeError("INVALID_OR_MISSING_LICENSE_STATUS")
        remote = _text(source.get("url"))
        local = _text(source.get("local_path"))
        if bool(remote) == bool(local):
            raise IntakeError("EXACTLY_ONE_OF_URL_OR_LOCAL_PATH_REQUIRED")
        if remote:
            _validate_source_url(remote)
        else:
            normal = local.replace("\\", "/")
            p = PurePosixPath(normal)
            if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
                raise IntakeError("LOCAL_PATH_MUST_BE_SAFE_RELATIVE_PATH")
        if _text(source.get("known_at")):
            _parse_known_at(source["known_at"])
        if _text(source.get("published_at")):
            _parse_known_at(source["published_at"])
        for field in ("observation_date", "effective_from", "effective_to"):
            if _text(source.get(field)):
                _parse_date(source[field], field)
        effective_from = _text(source.get("effective_from"))
        effective_to = _text(source.get("effective_to"))
        if effective_from and effective_to and _parse_date(effective_from, "effective_from") >= _parse_date(effective_to, "effective_to"):
            raise IntakeError("INVALID_EFFECTIVE_INTERVAL")
    return manifest


def _pit_candidate_status(source: Mapping[str, Any], cutoff: date) -> str:
    known_at = _parse_known_at(source.get("known_at"))
    if known_at is None:
        return "UNKNOWN_NO_KNOWN_AT"
    if not _text(source.get("known_at_basis")):
        return "UNKNOWN_NO_KNOWN_AT_BASIS"
    if isinstance(known_at, datetime):
        cutoff_end = datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=UTC_PLUS_8)
        if known_at.astimezone(timezone.utc) >= cutoff_end.astimezone(timezone.utc):
            return "BLOCKED_KNOWN_AFTER_CUTOFF"
    elif known_at > cutoff:
        return "BLOCKED_KNOWN_AFTER_CUTOFF"
    return "PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"


def _load_source_refs(repo_root: Path) -> set[str]:
    try:
        registry = _load_json_strict((repo_root / "configs/source_registry_v0.1.json").read_bytes())
        rows = registry.get("sources", [])
        return {str(row["source_ref"]) for row in rows if isinstance(row, dict) and row.get("source_ref")}
    except (OSError, IntakeError, AttributeError, TypeError):
        return set()


def _read_local_source(input_root: Path | None, relative_path: str) -> bytes:
    if input_root is None:
        raise SourceCaptureError("LOCAL_INPUT_ROOT_REQUIRED")
    root = input_root.resolve()
    candidate = (root / relative_path.replace("\\", "/")).resolve()
    if candidate == root or root not in candidate.parents:
        raise SourceCaptureError("LOCAL_PATH_ESCAPES_INPUT_ROOT")
    try:
        if not candidate.is_file():
            raise SourceCaptureError("LOCAL_SOURCE_FILE_NOT_FOUND")
        with candidate.open("rb") as stream:
            content = stream.read(MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise SourceCaptureError("LOCAL_SOURCE_READ_FAILED") from exc
    if len(content) > MAX_SOURCE_BYTES:
        raise SourceCaptureError("SOURCE_EXCEEDS_MAX_BYTES")
    return content


def _fetch_url(url: str) -> tuple[bytes, int, str]:
    _validate_source_url(url)
    request = Request(
        url,
        headers={"User-Agent": "IIOS-company-evidence-intake/0.1", "Accept": "*/*"},
        method="GET",
    )
    try:
        opener = build_opener(_HTTPSOnlyRedirectHandler())
        with opener.open(request, timeout=30) as response:
            status = int(getattr(response, "status", getattr(response, "code", 0)))
            if status < 200 or status >= 300:
                raise SourceCaptureError("UNEXPECTED_HTTP_STATUS")
            chunks = []
            total = 0
            while True:
                block = response.read(min(1024 * 1024, MAX_SOURCE_BYTES + 1 - total))
                if not block:
                    break
                total += len(block)
                if total > MAX_SOURCE_BYTES:
                    raise SourceCaptureError("SOURCE_EXCEEDS_MAX_BYTES")
                chunks.append(block)
            return b"".join(chunks), status, str(response.headers.get("Content-Type", ""))
    except SourceCaptureError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        if isinstance(exc, HTTPError):
            raise SourceCaptureError("HTTP_REQUEST_FAILED") from exc
        raise SourceCaptureError("SOURCE_FETCH_FAILED") from exc


def _safe_suffix(source: Mapping[str, Any]) -> str:
    locator = _text(source.get("local_path"))
    if not locator:
        locator = urlparse(_text(source.get("url"))).path
    suffix = Path(locator).suffix.lower()
    return suffix if suffix in SAFE_SUFFIXES else ".bin"


def capture_sources(
    manifest_path: str | Path,
    *,
    out_dir: str | Path,
    input_root: str | Path | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest_raw = manifest_path.read_bytes()
    manifest = validate_manifest(_load_json_strict(manifest_raw))
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise IntakeError("OUTPUT_DIRECTORY_MUST_BE_EMPTY_APPEND_ONLY_RUN")
    repo_root = Path(__file__).resolve().parents[1]
    registered_refs = _load_source_refs(repo_root)
    local_root = Path(input_root) if input_root is not None else None
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (output / "intake_manifest.json").write_bytes(manifest_raw)
    cutoff = _parse_date(manifest["cutoff_date"], "cutoff")
    receipt_sources = []
    failures = 0
    group_capture_counts = {group: 0 for group in FIELD_GROUPS}

    for source in manifest["sources"]:
        attempted_at = datetime.now(timezone.utc).isoformat()
        row = {
            "source_id": source["source_id"],
            "source_spec_sha256": sha256_bytes(canonical_json_bytes(source)),
            "field_group": source["field_group"],
            "source_ref": source["source_ref"],
            "source_class_claim": source["source_class"],
            "source_registry_status": "REGISTERED" if source["source_ref"] in registered_refs else "UNREGISTERED",
            "source_url": source.get("url"),
            "operator_local_path": source.get("local_path"),
            "published_at": source.get("published_at"),
            "known_at": source.get("known_at"),
            "known_at_basis": source.get("known_at_basis"),
            "observation_date": source.get("observation_date"),
            "effective_from": source.get("effective_from"),
            "effective_to": source.get("effective_to"),
            "license_status": source["license_status"],
            "attempted_at": attempted_at,
            "capture_status": "FAILED",
            "raw_artifact_path": None,
            "size_bytes": None,
            "sha256": None,
            "http_status": None,
            "content_type": None,
            "pit_status": "UNKNOWN_NO_BYTES",
            "source_authenticity_status": "UNVERIFIED",
            "admission_status": "NOT_ADMITTED",
            "error_code": None,
        }
        try:
            if _text(source.get("url")):
                content, http_status, content_type = _fetch_url(source["url"])
            else:
                content = _read_local_source(local_root, source["local_path"])
                http_status, content_type = None, "OPERATOR_SUPPLIED_FILE"
            raw_relative = f"raw/{source['source_id']}{_safe_suffix(source)}"
            target = output / raw_relative
            with target.open("xb") as stream:
                stream.write(content)
            row.update({
                "capture_status": "SUCCESS",
                "raw_artifact_path": raw_relative,
                "size_bytes": len(content),
                "sha256": sha256_bytes(content),
                "http_status": http_status,
                "content_type": content_type,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "pit_status": _pit_candidate_status(source, cutoff),
            })
            group_capture_counts[source["field_group"]] += 1
        except (SourceCaptureError, OSError) as exc:
            failures += 1
            row["error_code"] = exc.code if isinstance(exc, SourceCaptureError) else "RAW_ARTIFACT_WRITE_FAILED"
        receipt_sources.append(row)

    all_success = failures == 0 and len(receipt_sources) > 0
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "tool_version": TOOL_VERSION,
        "case_id": manifest["case_id"],
        "market": manifest["market"],
        "symbol": manifest["symbol"],
        "cutoff_date": manifest["cutoff_date"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": "intake_manifest.json",
        "manifest_sha256": sha256_bytes(manifest_raw),
        "max_source_bytes": MAX_SOURCE_BYTES,
        "status": "CAPTURED_NOT_ADMITTED" if all_success else "PARTIAL_CAPTURE_NOT_ADMITTED",
        "admission_status": "NOT_ADMITTED",
        "capture_coverage": {
            "field_groups_with_captured_bytes": [group for group, count in group_capture_counts.items() if count],
            "field_groups_without_captured_bytes": [group for group, count in group_capture_counts.items() if not count],
            "group_capture_counts": group_capture_counts,
            "coverage_is_not_evidence_admission": True,
        },
        "rules": {
            "paid_data_mandatory": False,
            "https_required_for_remote_sources": True,
            "retrieved_at_substitutes_for_known_at": False,
            "source_claims_are_not_self_authenticating": True,
            "pit_candidate_is_not_admission": True,
            "raw_bytes_are_retained": True,
        },
        "sources": receipt_sources,
    }
    receipt_path = output / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Free-first raw evidence capture for a user-selected IIOS company case.")
    parser.add_argument("--manifest", required=True, help="JSON manifest with a canonical case identity and source locators")
    parser.add_argument("--input-root", help="Root directory for operator-supplied files referenced by local_path")
    parser.add_argument("--out", required=True, help="New, empty run output directory; raw files are retained here")
    parser.add_argument("--validate-only", action="store_true", help="Validate manifest without downloading or copying source bytes")
    args = parser.parse_args()
    try:
        raw = Path(args.manifest).read_bytes()
        manifest = validate_manifest(_load_json_strict(raw))
        if args.validate_only:
            print(json.dumps({"status": "MANIFEST_VALID", "case_id": manifest["case_id"], "source_count": len(manifest["sources"])}, sort_keys=True))
            return 0
        receipt = capture_sources(args.manifest, out_dir=args.out, input_root=args.input_root)
    except (OSError, IntakeError) as exc:
        code = str(exc) if isinstance(exc, IntakeError) else "INPUT_FILE_UNAVAILABLE"
        print(json.dumps({"status": "INTAKE_BLOCKED", "error_code": code}, sort_keys=True))
        return 2
    rows = receipt["sources"]
    failed_sources = [
        {"source_id": row["source_id"], "error_code": row.get("error_code")}
        for row in rows if row.get("capture_status") == "FAILED"
    ]
    unregistered_sources = [
        {"source_id": row["source_id"], "source_ref": row.get("source_ref")}
        for row in rows if row.get("source_registry_status") == "UNREGISTERED"
    ]
    print(json.dumps({
        "status": receipt["status"],
        "admission_status": receipt["admission_status"],
        "case_id": receipt["case_id"],
        "sources": len(rows),
        "failed": len(failed_sources),
        "failed_sources": failed_sources,
        "unregistered_sources": unregistered_sources,
        "receipt": str(Path(args.out) / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json"),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] == "CAPTURED_NOT_ADMITTED" else 4


if __name__ == "__main__":
    raise SystemExit(main())
