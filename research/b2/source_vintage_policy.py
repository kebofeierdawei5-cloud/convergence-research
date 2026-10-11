from __future__ import annotations

"""Deterministic, rule-bounded PIT adjudication for the 605016 official close.

This policy does not claim the SSE historical JSON endpoint's exact first-upload
timestamp. It records a conservative upper bound grounded in the official SSE
trading rules that say the closing price is included in real-time quote during
the post-market fixed-price session. Rule-page bytes were not materialized as a
hashed raw artifact in the original 605016 capture; the source URL, rule version,
issue/effective dates, and clauses are explicit so that this limitation remains
auditable rather than silently fabricated.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping
from urllib.parse import urlparse

CASE_ID = "RC-CN-A-605016-20261009"
CUTOFF_DATE = "2026-10-09"
PRICE_EVIDENCE_ID = "605016-SSE-HTTPS-DAILY-CLOSE-20261008"
PRICE_OBSERVATION_DATE = "2026-10-08"
PRICE_EVENT_AT = "2026-10-08T15:00:00+08:00"
PUBLIC_AVAILABILITY_UPPER_BOUND = "2026-10-08T15:30:00+08:00"
POLICY_ID = "IIOS-CN-A-605016-SOURCE-VINTAGE-BOUND-0.1"
RULE_URL = "https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml"
RULE_TITLE = "上海证券交易所交易规则（2026年修订）"
RULE_DOCUMENT_NO = "上证发〔2026〕41号"
RULE_PUBLISHED_ON = "2026-04-24"
RULE_EFFECTIVE_ON = "2026-07-06"
RULE_SECTIONS = {
    "3.7.2": "盘后固定价格交易以当日收盘价成交，交易时段为15:05至15:30。",
    "3.7.9": "15:05至15:30盘后固定价格交易阶段纳入即时行情，行情内容包括收盘价。",
    "5.1.1": "上交所每个交易日实时发布证券交易即时行情。",
}
BOUND_BASIS = (
    "OFFICIAL_SSE_PUBLIC_AVAILABILITY_UPPER_BOUND; under 上海证券交易所交易规则"
    "（2026年修订） sections 3.7.2, 3.7.9 and 5.1.1, the official closing price"
    " is included in real-time quote during the 15:05-15:30 post-market fixed-price"
    " session. 15:30 is used as a conservative availability upper bound, not as the"
    " endpoint's exact historical first-public timestamp."
)


class SourceVintageAdjudicationError(ValueError):
    """A bounded PIT decision cannot be established from the existing exact bytes."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cutoff_datetime(cutoff_date: str) -> datetime:
    try:
        parsed = datetime.strptime(cutoff_date, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_CUTOFF_DATE_INVALID") from exc
    return parsed.replace(tzinfo=timezone(timedelta(hours=8)))


def _safe_relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\\\\" in value:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_PATH_INVALID")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or (path.parts and ":" in path.parts[0])
    ):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_PATH_INVALID")
    return path


def _price_binding(manifest: Mapping[str, Any], expected_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if manifest.get("case_id") != CASE_ID or manifest.get("cutoff_date") != CUTOFF_DATE:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_CASE_OR_CUTOFF_MISMATCH")
    evidence = manifest.get("evidence")
    declarations = manifest.get("raw_artifacts")
    if not isinstance(evidence, list) or not isinstance(declarations, list):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_EVIDENCE_OR_RAW_LIST_INVALID")
    records = [
        item for item in evidence
        if isinstance(item, Mapping) and item.get("evidence_id") == PRICE_EVIDENCE_ID
    ]
    raw_refs = [
        item for item in declarations
        if isinstance(item, Mapping) and item.get("evidence_id") == PRICE_EVIDENCE_ID
    ]
    if len(records) != 1 or len(raw_refs) != 1:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PRICE_BINDING_MISSING_OR_DUPLICATED")
    price = dict(records[0])
    raw_ref = dict(raw_refs[0])
    if (
        price.get("field_id") != "market_price.close"
        or price.get("observation_date") != PRICE_OBSERVATION_DATE
        or not isinstance(price.get("value"), Mapping)
        or price["value"].get("observation_date") != PRICE_OBSERVATION_DATE
        or price["value"].get("quote_type") != "OFFICIAL_SSE_DAILY_CLOSE"
        or price.get("status") != "ADMITTED"
        or price.get("provenance_class") != "SOURCE_VINTAGE_VERIFIED"
        or price.get("exact_bytes") is not True
        or price.get("content_sha256") != expected_sha256
        or raw_ref.get("expected_sha256") != expected_sha256
        or price.get("content_sha256") != raw_ref.get("expected_sha256")
    ):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PRICE_SOURCE_CONTRACT_MISMATCH")
    parsed_source = urlparse(str(price.get("source_ref") or ""))
    if (
        parsed_source.scheme.lower() != "https"
        or parsed_source.hostname != "yunhq.sse.com.cn"
        or parsed_source.port not in {None, 443, 32041, 32042}
    ):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PRICE_SOURCE_ORIGIN_MISMATCH")
    expected_event = price.get("known_at")
    if expected_event not in {PRICE_EVENT_AT, PUBLIC_AVAILABILITY_UPPER_BOUND}:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PREVIOUS_KNOWN_AT_UNEXPECTED")
    return price, raw_ref


def _materialized_raw_bytes(raw_root: Path, raw_ref: Mapping[str, Any], expected_sha256: str) -> bytes:
    relative = _safe_relative_path(raw_ref.get("relative_path"))
    unresolved = raw_root
    for part in relative.parts:
        unresolved = unresolved / part
        if unresolved.is_symlink():
            raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_SYMLINK_FORBIDDEN")
    try:
        root_resolved = raw_root.resolve(strict=True)
        source = unresolved.resolve(strict=True)
    except OSError as exc:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_SOURCE_MISSING") from exc
    try:
        source.relative_to(root_resolved)
    except ValueError as exc:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_PATH_ESCAPE") from exc
    if not source.is_file():
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_SOURCE_NOT_FILE")
    raw = source.read_bytes()
    expected_size = raw_ref.get("expected_size_bytes")
    if type(expected_size) is not int or len(raw) != expected_size:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_SIZE_MISMATCH")
    if _sha256(raw) != expected_sha256:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RAW_SHA256_MISMATCH")
    return raw


def _adjudication_body(adjudication: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in adjudication.items() if key != "adjudication_sha256"}


def validate_source_vintage_adjudication(
    manifest: Mapping[str, Any],
    *,
    raw_root: Path,
    expected_price_sha256: str,
) -> dict[str, Any]:
    """Replay policy, rule identity, time-bound, record binding, and original bytes."""
    adjudication = manifest.get("source_vintage_adjudication")
    if not isinstance(adjudication, Mapping):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATION_MISSING")
    if _sha256(_canonical_bytes(_adjudication_body(adjudication))) != adjudication.get("adjudication_sha256"):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATION_HASH_MISMATCH")
    expected = {
        "schema_version": "IIOS-SOURCE-VINTAGE-ADJUDICATION-0.1",
        "policy_id": POLICY_ID,
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "decision": "BOUNDED_PUBLIC_AVAILABILITY_ACCEPTED_FOR_PIT",
        "price_evidence_id": PRICE_EVIDENCE_ID,
        "price_observation_date": PRICE_OBSERVATION_DATE,
        "price_content_sha256": expected_price_sha256,
        "public_availability_upper_bound": PUBLIC_AVAILABILITY_UPPER_BOUND,
        "exact_first_public_timestamp_verified": False,
        "source_endpoint_first_public_timestamp_verified": False,
        "source_vintage_review_required": False,
        "rule_source": {
            "authority": "上海证券交易所",
            "title": RULE_TITLE,
            "document_no": RULE_DOCUMENT_NO,
            "source_url": RULE_URL,
            "published_on": RULE_PUBLISHED_ON,
            "effective_on": RULE_EFFECTIVE_ON,
            "applicable_on_observation_date": True,
            "sections": RULE_SECTIONS,
            "raw_rule_bytes_materialized": False,
            "raw_rule_bytes_sha256": None,
        },
    }
    for field, value in expected.items():
        if adjudication.get(field) != value:
            raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATION_CONTRACT_MISMATCH:" + field)
    if not isinstance(adjudication.get("previous_known_at"), str):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PREVIOUS_KNOWN_AT_MISSING")
    if not isinstance(adjudication.get("adjudicated_at"), str) or not adjudication.get("adjudicated_at"):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATED_AT_MISSING")
    price, raw_ref = _price_binding(manifest, expected_price_sha256)
    _materialized_raw_bytes(raw_root, raw_ref, expected_price_sha256)
    if (
        price.get("known_at") != PUBLIC_AVAILABILITY_UPPER_BOUND
        or price.get("known_at_basis") != BOUND_BASIS
        or price.get("source_vintage_adjudication_id") != POLICY_ID
        or price.get("first_public_time_precision")
        != "OFFICIAL_RULE_UPPER_BOUND_15_30; EXACT_ENDPOINT_FIRST_PUBLIC_TIMESTAMP_UNVERIFIED"
    ):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PRICE_RECORD_BOUND_MISMATCH")
    bound = datetime.fromisoformat(PUBLIC_AVAILABILITY_UPPER_BOUND)
    cutoff = _cutoff_datetime(CUTOFF_DATE)
    if bound >= cutoff:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_BOUND_NOT_BEFORE_CUTOFF")
    return {
        "source_vintage_status": "BOUNDED_PUBLIC_AVAILABILITY_ACCEPTED_FOR_PIT",
        "source_vintage_review_required": False,
        "exact_first_public_timestamp_verified": False,
        "public_availability_upper_bound": PUBLIC_AVAILABILITY_UPPER_BOUND,
        "adjudication_sha256": str(adjudication["adjudication_sha256"]),
    }


def adjudicate_605016_source_vintage(
    manifest: Mapping[str, Any],
    *,
    raw_root: Path,
    expected_price_sha256: str,
    adjudicated_at: str,
) -> dict[str, Any]:
    """Return a new, Core-validated manifest using a conservative publication bound."""
    if manifest.get("source_vintage_adjudication") is not None:
        validate_source_vintage_adjudication(
            manifest, raw_root=raw_root, expected_price_sha256=expected_price_sha256
        )
        return deepcopy(dict(manifest))

    result = deepcopy(dict(manifest))
    price, raw_ref = _price_binding(result, expected_price_sha256)
    _materialized_raw_bytes(raw_root, raw_ref, expected_price_sha256)
    if not adjudicated_at or not isinstance(adjudicated_at, str):
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATED_AT_INVALID")
    try:
        parsed_adjudicated_at = datetime.fromisoformat(adjudicated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATED_AT_INVALID") from exc
    if parsed_adjudicated_at.tzinfo is None:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_ADJUDICATED_AT_MUST_BE_TIMEZONE_AWARE")

    bound = datetime.fromisoformat(PUBLIC_AVAILABILITY_UPPER_BOUND)
    cutoff = _cutoff_datetime(str(result.get("cutoff_date")))
    if bound >= cutoff:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_BOUND_NOT_BEFORE_CUTOFF")
    observation_day = datetime.fromisoformat(PRICE_OBSERVATION_DATE).date()
    if datetime.fromisoformat(PUBLIC_AVAILABILITY_UPPER_BOUND).date() != observation_day:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_BOUND_OBSERVATION_DATE_MISMATCH")
    if datetime.fromisoformat(RULE_EFFECTIVE_ON).date() > observation_day:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RULE_NOT_EFFECTIVE_ON_OBSERVATION_DATE")
    if datetime.fromisoformat(RULE_PUBLISHED_ON).date() > datetime.fromisoformat(RULE_EFFECTIVE_ON).date():
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_RULE_PUBLICATION_DATE_INVALID")

    previous_known_at = str(price.get("known_at"))
    adjudication_body = {
        "schema_version": "IIOS-SOURCE-VINTAGE-ADJUDICATION-0.1",
        "policy_id": POLICY_ID,
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_DATE,
        "decision": "BOUNDED_PUBLIC_AVAILABILITY_ACCEPTED_FOR_PIT",
        "price_evidence_id": PRICE_EVIDENCE_ID,
        "price_observation_date": PRICE_OBSERVATION_DATE,
        "price_content_sha256": expected_price_sha256,
        "previous_known_at": previous_known_at,
        "public_availability_upper_bound": PUBLIC_AVAILABILITY_UPPER_BOUND,
        "cutoff_comparison": "PASS_UPPER_BOUND_STRICTLY_BEFORE_DATE_ONLY_CUTOFF_START",
        "exact_first_public_timestamp_verified": False,
        "source_endpoint_first_public_timestamp_verified": False,
        "source_vintage_review_required": False,
        "rule_source": {
            "authority": "上海证券交易所",
            "title": RULE_TITLE,
            "document_no": RULE_DOCUMENT_NO,
            "source_url": RULE_URL,
            "published_on": RULE_PUBLISHED_ON,
            "effective_on": RULE_EFFECTIVE_ON,
            "applicable_on_observation_date": True,
            "sections": RULE_SECTIONS,
            "raw_rule_bytes_materialized": False,
            "raw_rule_bytes_sha256": None,
            "raw_rule_bytes_limitation": (
                "Official page content and rule clauses were reviewed; the HTML/DOCX source bytes were "
                "not materialized into the private evidence store in this run, so no rule-byte SHA-256 is claimed."
            ),
        },
        "reasoning": (
            "The official SSE rule places the closing price in real-time quote during the 15:05-15:30 "
            "post-market fixed-price session. Use 15:30 as the conservative public-availability upper bound. "
            "This bounds PIT knowledge without asserting the historical daily-bar endpoint's exact upload time."
        ),
        "adjudicated_at": adjudicated_at,
        "non_claims": [
            "exact_first_public_timestamp_not_verified",
            "historical_endpoint_upload_time_not_verified",
            "raw_rule_source_bytes_not_materialized_or_hashed",
            "not_formal_signed_admission",
            "not_production_host_acceptance",
            "not_decision_or_trade_authority",
        ],
    }
    adjudication = dict(adjudication_body)
    adjudication["adjudication_sha256"] = _sha256(_canonical_bytes(adjudication_body))

    evidence_list = result.get("evidence")
    price_items = [
        item for item in evidence_list
        if isinstance(item, dict) and item.get("evidence_id") == PRICE_EVIDENCE_ID
    ]
    if len(price_items) != 1:
        raise SourceVintageAdjudicationError("SOURCE_VINTAGE_PRICE_RECORD_MISSING_OR_DUPLICATED")
    price_record = price_items[0]
    price_record["known_at"] = PUBLIC_AVAILABILITY_UPPER_BOUND
    price_record["known_at_basis"] = BOUND_BASIS
    price_record["source_vintage_adjudication_id"] = POLICY_ID
    price_record["first_public_time_precision"] = (
        "OFFICIAL_RULE_UPPER_BOUND_15_30; EXACT_ENDPOINT_FIRST_PUBLIC_TIMESTAMP_UNVERIFIED"
    )
    result["source_vintage_adjudication"] = adjudication

    # The manifest audit digest binds the adjudication and time-bound evidence,
    # following the original manifest builder's pre-status/pre-audit convention.
    audit_payload = {
        key: value for key, value in result.items()
        if key not in {"audit", "status", "validation_errors"}
    }
    result["audit"] = {"manifest_sha256": _sha256(_canonical_bytes(audit_payload))}

    # Reuse the unchanged Investment Core contract. This gate does not relax it.
    from research.b2.company_evidence import validate_company_evidence_manifest

    errors = validate_company_evidence_manifest(
        result, raw_root=raw_root, require_raw_verification=True
    )
    result["status"] = "PASS" if not errors else "BLOCKED"
    result["validation_errors"] = errors
    if errors:
        raise SourceVintageAdjudicationError(
            "SOURCE_VINTAGE_SUCCESSOR_CORE_VALIDATOR_BLOCKED:" + ",".join(errors[:8])
        )
    validate_source_vintage_adjudication(
        result, raw_root=raw_root, expected_price_sha256=expected_price_sha256
    )
    return result


__all__ = [
    "POLICY_ID",
    "PUBLIC_AVAILABILITY_UPPER_BOUND",
    "RULE_URL",
    "SourceVintageAdjudicationError",
    "adjudicate_605016_source_vintage",
    "validate_source_vintage_adjudication",
]
