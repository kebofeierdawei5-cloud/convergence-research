from __future__ import annotations

"""Private, analysis-only intake for operator-attested prices.

This lane is deliberately separate from canonical market-price admission. It
lets an operator supply a typed close for valuation/scenario work while
preserving an explicit non-canonical label. It does not verify source origin,
source-vintage, data-use rights, or a frozen case's Evidence/PIT admissibility.
No LLM or external model/provider is used.
"""

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping

OPERATOR_PRICE_INPUT_SCHEMA = "IIOS-OPERATOR-ATTESTED-PRICE-INPUT-0.1"
OPERATOR_PRICE_RECORD_SCHEMA = "IIOS-OPERATOR-ATTESTED-PRICE-ANALYSIS-RECORD-0.1"
OPERATOR_PRICE_RECEIPT_SCHEMA = "IIOS-OPERATOR-ATTESTED-PRICE-RECEIPT-0.1"
ANALYSIS_ONLY_STATUS = "ACCEPTED_FOR_ANALYSIS_ONLY"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

_TOP_LEVEL_FIELDS = {"schema_version", "operator_confirmed", "analysis_cutoff_date", "batch_id", "records"}
_RECORD_FIELDS = {
    "base_case_id", "market", "symbol", "exchange", "observation_date", "price",
    "currency", "adjustment_semantics", "operator_attested_known_at",
    "sources_claimed", "attestation_note",
}
_EXPECTED_EXCHANGE = {"CN-A": {"SH": "SSE", "SZ": "SZSE"}}


class OperatorPriceInputError(ValueError):
    """Raised when a private operator price input fails the analysis-only contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_object(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise OperatorPriceInputError("INPUT_MUST_BE_REGULAR_FILE_NOT_SYMLINK")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OperatorPriceInputError("INPUT_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise OperatorPriceInputError("INPUT_JSON_MUST_BE_OBJECT")
    return value, raw


def _reject_constant(value: str) -> None:
    raise ValueError(f"NON_FINITE_JSON_NUMBER:{value}")


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise OperatorPriceInputError(f"{field}_MUST_BE_ISO_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OperatorPriceInputError(f"{field}_MUST_BE_ISO_DATE") from exc


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OperatorPriceInputError(f"{field}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperatorPriceInputError(f"{field}_MUST_BE_ISO_DATETIME") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperatorPriceInputError(f"{field}_MUST_INCLUDE_TIMEZONE")
    return parsed.astimezone(SHANGHAI)


def _parse_price(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise OperatorPriceInputError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER")
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise OperatorPriceInputError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER") from exc
    if not price.is_finite() or price <= 0:
        raise OperatorPriceInputError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER")
    if price.as_tuple().exponent < -6:
        raise OperatorPriceInputError("PRICE_PRECISION_EXCEEDS_SIX_DECIMAL_PLACES")
    return price


def _must_be_outside_repository(path: Path, field: str) -> Path:
    if path.is_symlink():
        raise OperatorPriceInputError(f"{field}_MUST_NOT_BE_SYMLINK")
    resolved = path.expanduser().resolve(strict=False)
    repo = REPOSITORY_ROOT.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise OperatorPriceInputError(f"{field}_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY")
    return resolved


def _validate_record(record: Any, cutoff_date: date) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise OperatorPriceInputError("RECORD_MUST_BE_OBJECT")
    missing = sorted(_RECORD_FIELDS - set(record))
    extra = sorted(set(record) - _RECORD_FIELDS)
    if missing:
        raise OperatorPriceInputError("RECORD_MISSING_FIELDS:" + ",".join(missing))
    if extra:
        raise OperatorPriceInputError("RECORD_UNSUPPORTED_FIELDS:" + ",".join(extra))

    base_case_id = record.get("base_case_id")
    market = record.get("market")
    symbol = str(record.get("symbol", "")).strip()
    exchange = record.get("exchange")
    currency = record.get("currency")
    adjustment = record.get("adjustment_semantics")
    if not isinstance(base_case_id, str) or not base_case_id.strip():
        raise OperatorPriceInputError("BASE_CASE_ID_REQUIRED")
    if market != "CN-A":
        raise OperatorPriceInputError("ONLY_CN_A_SHARE_MARKET_SUPPORTED_IN_V01")
    if not re.fullmatch(r"\d{6}", symbol):
        raise OperatorPriceInputError("SYMBOL_MUST_BE_SIX_DIGIT_A_SHARE_CODE")
    suffix = "SH" if symbol.startswith(("60", "68", "90")) else "SZ"
    expected_exchange = _EXPECTED_EXCHANGE["CN-A"][suffix]
    if exchange != expected_exchange:
        raise OperatorPriceInputError("EXCHANGE_SYMBOL_MISMATCH")
    if currency != "CNY":
        raise OperatorPriceInputError("CURRENCY_MUST_BE_CNY")
    if adjustment != "UNADJUSTED_CLOSE":
        raise OperatorPriceInputError("ONLY_EXPLICIT_UNADJUSTED_CLOSE_ACCEPTED_IN_V01")

    observation_date = _parse_date(record.get("observation_date"), "OBSERVATION_DATE")
    known_at = _parse_datetime(record.get("operator_attested_known_at"), "OPERATOR_ATTESTED_KNOWN_AT")
    cutoff_start = datetime.combine(cutoff_date, time.min, tzinfo=SHANGHAI)
    if observation_date > cutoff_date:
        raise OperatorPriceInputError("OBSERVATION_DATE_AFTER_ANALYSIS_CUTOFF")
    if observation_date != known_at.date():
        raise OperatorPriceInputError("ATTESTED_KNOWN_AT_DATE_MUST_MATCH_OBSERVATION_DATE")
    if known_at >= cutoff_start:
        raise OperatorPriceInputError("ATTESTED_KNOWN_AT_NOT_BEFORE_CUTOFF_START")

    sources = record.get("sources_claimed")
    if (
        not isinstance(sources, list) or not sources
        or any(not isinstance(source, str) or not source.strip() for source in sources)
    ):
        raise OperatorPriceInputError("SOURCES_CLAIMED_MUST_BE_NONEMPTY_STRINGS")
    if len(set(sources)) != len(sources):
        raise OperatorPriceInputError("SOURCES_CLAIMED_DUPLICATE")
    note = record.get("attestation_note")
    if not isinstance(note, str) or not note.strip():
        raise OperatorPriceInputError("ATTESTATION_NOTE_REQUIRED")

    price = _parse_price(record.get("price"))
    return {
        "record_schema": OPERATOR_PRICE_RECORD_SCHEMA,
        "record_class": "OPERATOR_ATTESTED_MARKET_DATA",
        "analysis_only_status": ANALYSIS_ONLY_STATUS,
        "base_case_id": base_case_id.strip(),
        "market": market,
        "symbol": symbol,
        "exchange": exchange,
        "observation_date": observation_date.isoformat(),
        "price": format(price, "f"),
        "currency": currency,
        "unit": "CNY/share",
        "adjustment_semantics": adjustment,
        "operator_attested_known_at": known_at.isoformat(),
        "sources_claimed": [source.strip() for source in sources],
        "attestation_note": note.strip(),
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "raw_source_bytes_captured": False,
        "exact_original_source_timestamp_verified": False,
        "canonical_price_admission": False,
        "formal_evidence_pit_admission": False,
        "decision_authority": False,
        "use_scope": "PRIVATE_ANALYSIS_AND_SCENARIO_VALUATION_ONLY",
    }


def validate_operator_price_payload(payload: Any) -> dict[str, Any]:
    """Return normalized analysis-only record. Never returns canonical admission."""
    if not isinstance(payload, Mapping):
        raise OperatorPriceInputError("INPUT_MUST_BE_OBJECT")
    missing = sorted(_TOP_LEVEL_FIELDS - set(payload))
    extra = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    if missing:
        raise OperatorPriceInputError("INPUT_MISSING_FIELDS:" + ",".join(missing))
    if extra:
        raise OperatorPriceInputError("INPUT_UNSUPPORTED_FIELDS:" + ",".join(extra))
    if payload.get("schema_version") != OPERATOR_PRICE_INPUT_SCHEMA:
        raise OperatorPriceInputError("INPUT_SCHEMA_VERSION_INVALID")
    if payload.get("operator_confirmed") is not True:
        raise OperatorPriceInputError("EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED")
    cutoff_date = _parse_date(payload.get("analysis_cutoff_date"), "ANALYSIS_CUTOFF_DATE")
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,99}", batch_id):
        raise OperatorPriceInputError("BATCH_ID_INVALID")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise OperatorPriceInputError("RECORDS_REQUIRED")
    normalized = [_validate_record(item, cutoff_date) for item in records]
    keys = [(item["base_case_id"], item["symbol"], item["observation_date"]) for item in normalized]
    if len(set(keys)) != len(keys):
        raise OperatorPriceInputError("DUPLICATE_CASE_SYMBOL_OBSERVATION")
    return {
        "record_schema": OPERATOR_PRICE_RECORD_SCHEMA,
        "record_class": "OPERATOR_ATTESTED_PRICE_ANALYSIS_ONLY",
        "status": ANALYSIS_ONLY_STATUS,
        "batch_id": batch_id,
        "analysis_cutoff_date": cutoff_date.isoformat(),
        "date_cutoff_semantics": "START_OF_DAY_ASIA_SHANGHAI",
        "records": normalized,
        "scope_controls": {
            "may_feed_scenario_valuation": True,
            "may_feed_canonical_current_price_resolver": False,
            "canonical_price_admission": False,
            "formal_evidence_pit_admission": False,
            "source_origin_verified": False,
            "source_vintage_verified": False,
            "source_use_rights_verified": False,
            "decision_authority": False,
            "frozen_base_case_mutated": False,
            "note": "This is an operator-attested analysis overlay, not source-verified market evidence.",
        },
    }


def build_sanitized_receipt(normalized: Mapping[str, Any], *, input_sha256: str) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(input_sha256):
        raise OperatorPriceInputError("INPUT_SHA256_INVALID")
    rows = []
    for item in normalized["records"]:
        rows.append({
            "base_case_id": item["base_case_id"],
            "market": item["market"],
            "symbol": item["symbol"],
            "exchange": item["exchange"],
            "observation_date": item["observation_date"],
            "currency": item["currency"],
            "unit": item["unit"],
            "adjustment_semantics": item["adjustment_semantics"],
            "price_value_present": True,
            "operator_attested_known_at_present": True,
            "sources_claimed_count": len(item["sources_claimed"]),
            "source_origin_verified": False,
            "source_vintage_verified": False,
            "source_use_rights_verified": False,
            "canonical_price_admission": False,
            "formal_evidence_pit_admission": False,
        })
    private_record_sha = _sha256(_canonical(normalized))
    return {
        "receipt_schema": OPERATOR_PRICE_RECEIPT_SCHEMA,
        "status": ANALYSIS_ONLY_STATUS,
        "batch_id": normalized["batch_id"],
        "analysis_cutoff_date": normalized["analysis_cutoff_date"],
        "record_count": len(rows),
        "records": rows,
        "input_sha256": input_sha256,
        "private_record_sha256": private_record_sha,
        "quote_values_redacted": True,
        "private_source_labels_redacted": True,
        "public_upload_allowed": False,
        "canonical_price_admission": False,
        "formal_evidence_pit_admission": False,
        "decision_authority": False,
    }


def _write_new_private_file(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise OperatorPriceInputError("OUTPUT_EXISTS_OR_IS_SYMLINK")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        path.unlink(missing_ok=True)
        raise OperatorPriceInputError("OUTPUT_PERMISSIONS_TOO_OPEN")


def persist_operator_price_input(
    *,
    input_path: str | Path,
    private_root: str | Path,
    output_name: str = "operator-attested-prices-path-a.json",
    receipt_name: str = "operator-attested-prices-path-a.receipt.json",
) -> dict[str, Any]:
    """Persist normalized values and a price-redacted receipt under private local storage."""
    input_file = Path(input_path).expanduser()
    input_path_resolved = _must_be_outside_repository(input_file, "INPUT_PATH")
    input_file = input_path_resolved.resolve(strict=True)
    private_root_resolved = _must_be_outside_repository(Path(private_root).expanduser(), "PRIVATE_ROOT")
    root = private_root_resolved
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise OperatorPriceInputError("PRIVATE_ROOT_MUST_BE_REAL_DIRECTORY")
    if hasattr(os, "getuid") and root.stat().st_uid != os.getuid():
        raise OperatorPriceInputError("PRIVATE_ROOT_OWNER_MISMATCH")
    if os.name != "nt":
        os.chmod(root, 0o700)
        if stat.S_IMODE(root.stat().st_mode) & 0o077:
            raise OperatorPriceInputError("PRIVATE_ROOT_PERMISSIONS_TOO_OPEN")
    if Path(output_name).name != output_name or Path(receipt_name).name != receipt_name:
        raise OperatorPriceInputError("OUTPUT_NAMES_MUST_BE_FILENAMES")
    if output_name == receipt_name:
        raise OperatorPriceInputError("OUTPUT_NAMES_MUST_DIFFER")

    payload, input_raw = _read_object(input_file)
    normalized = validate_operator_price_payload(payload)
    # Hashes here bind only the submitted JSON bytes; they are not source-origin or license proof.
    input_sha = _sha256(input_raw)
    receipt = build_sanitized_receipt(normalized, input_sha256=input_sha)
    private_path = root / output_name
    receipt_path = root / receipt_name
    _write_new_private_file(private_path, _canonical(normalized) + b"\n")
    try:
        _write_new_private_file(receipt_path, _canonical(receipt) + b"\n")
    except Exception:
        private_path.unlink(missing_ok=True)
        raise
    return receipt


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and privately store operator-attested share prices for analysis-only use."
    )
    parser.add_argument("--input", required=True, help="Private JSON supplied by the operator; keep it outside the public repo")
    parser.add_argument("--private-root", required=True, help="Private local root outside the repository")
    parser.add_argument("--output-name", default="operator-attested-prices-path-a.json")
    parser.add_argument("--receipt-name", default="operator-attested-prices-path-a.receipt.json")
    args = parser.parse_args(argv)
    try:
        receipt = persist_operator_price_input(
            input_path=args.input,
            private_root=args.private_root,
            output_name=args.output_name,
            receipt_name=args.receipt_name,
        )
        # Deliberately print only the sanitized receipt, never the price values.
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    except (OperatorPriceInputError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
