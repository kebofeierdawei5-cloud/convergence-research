from __future__ import annotations

"""Private interactive intake for operator-entered A/H share prices.

This creates a typed, replayable, value-redacted receipt. It is not market-data
source verification, formal Evidence/PIT admission, or Decision-chain binding.
"""

import argparse
import errno
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

SCHEMA = "IIOS-OPERATOR-ENTERED-PRICE-INPUT-0.1"
RECEIPT_SCHEMA = "IIOS-OPERATOR-ENTERED-PRICE-RECEIPT-0.1"
STATUS = "ACCEPTED_OPERATOR_INPUT_NOT_EVIDENCE_ADMISSION"
SHANGHAI = timezone(timedelta(hours=8))
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FIELDS = {
    "schema_version", "base_case_id", "market", "symbol", "exchange", "currency",
    "observation_date", "price", "adjustment_semantics", "quote_timestamp",
    "valid_until", "operator_confirmed", "source_claim",
}


class OperatorEnteredPriceError(ValueError):
    """A fail-closed operator-entered price validation or storage error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"NON_FINITE_JSON_NUMBER:{value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise OperatorEnteredPriceError("DUPLICATE_JSON_KEY")
        output[key] = value
    return output


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise OperatorEnteredPriceError("INPUT_MUST_BE_REGULAR_FILE_NOT_SYMLINK")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant, object_pairs_hook=_unique_pairs)
    except OperatorEnteredPriceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OperatorEnteredPriceError("INPUT_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise OperatorEnteredPriceError("INPUT_JSON_MUST_BE_OBJECT")
    return value, raw


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise OperatorEnteredPriceError(f"{field}_MUST_BE_ISO_DATE")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise OperatorEnteredPriceError(f"{field}_MUST_BE_ISO_DATE") from exc
    if parsed.isoformat() != value:
        raise OperatorEnteredPriceError(f"{field}_MUST_BE_CANONICAL_ISO_DATE")
    return parsed


def _parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OperatorEnteredPriceError(f"{field}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperatorEnteredPriceError(f"{field}_MUST_BE_ISO8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperatorEnteredPriceError(f"{field}_TIMEZONE_REQUIRED")
    return parsed.astimezone(SHANGHAI)


def _now_shanghai() -> datetime:
    return datetime.now(timezone.utc).astimezone(SHANGHAI)


def _as_shanghai(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise OperatorEnteredPriceError(f"{field}_TIMEZONE_REQUIRED")
    return value.astimezone(SHANGHAI)


def _parse_price(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise OperatorEnteredPriceError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OperatorEnteredPriceError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise OperatorEnteredPriceError("PRICE_MUST_BE_POSITIVE_FINITE_NUMBER")
    if parsed.as_tuple().exponent < -6:
        raise OperatorEnteredPriceError("PRICE_PRECISION_EXCEEDS_SIX_DECIMAL_PLACES")
    return parsed


def validate_payload(payload: Any, *, entered_at: datetime, decision_cutoff_at: datetime) -> dict[str, Any]:
    """Normalize a user-confirmed payload without claiming external source truth."""
    if not isinstance(payload, Mapping):
        raise OperatorEnteredPriceError("INPUT_MUST_BE_OBJECT")
    missing = sorted(_FIELDS - set(payload))
    extra = sorted(set(payload) - _FIELDS)
    if missing:
        raise OperatorEnteredPriceError("INPUT_MISSING_FIELDS:" + ",".join(missing))
    if extra:
        raise OperatorEnteredPriceError("INPUT_UNSUPPORTED_FIELDS:" + ",".join(extra))
    if payload.get("schema_version") != SCHEMA:
        raise OperatorEnteredPriceError("SCHEMA_VERSION_INVALID")
    if payload.get("operator_confirmed") is not True:
        raise OperatorEnteredPriceError("EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED")

    case_id = payload.get("base_case_id")
    market = payload.get("market")
    raw_symbol = payload.get("symbol")
    if not isinstance(raw_symbol, str) or not raw_symbol.strip():
        raise OperatorEnteredPriceError("SYMBOL_MUST_BE_NONEMPTY_STRING")
    symbol = raw_symbol.strip()
    exchange = payload.get("exchange")
    currency = payload.get("currency")
    if not isinstance(case_id, str) or not case_id.strip():
        raise OperatorEnteredPriceError("BASE_CASE_ID_REQUIRED")
    if market == "CN-A":
        if not re.fullmatch(r"\d{6}", symbol):
            raise OperatorEnteredPriceError("A_SHARE_SYMBOL_MUST_BE_SIX_DIGITS")
        expected_exchange = "SSE" if symbol.startswith(("60", "68", "90")) else "SZSE"
        if exchange != expected_exchange:
            raise OperatorEnteredPriceError("EXCHANGE_SYMBOL_MISMATCH")
        if currency != "CNY":
            raise OperatorEnteredPriceError("CURRENCY_MUST_BE_CNY")
    elif market == "HK":
        if not re.fullmatch(r"\d{1,5}", symbol):
            raise OperatorEnteredPriceError("HK_SYMBOL_MUST_BE_ONE_TO_FIVE_DIGITS")
        if exchange != "HKEX":
            raise OperatorEnteredPriceError("HK_EXCHANGE_MUST_BE_HKEX")
        if currency != "HKD":
            raise OperatorEnteredPriceError("CURRENCY_MUST_BE_HKD")
    else:
        raise OperatorEnteredPriceError("UNSUPPORTED_MARKET")

    if payload.get("adjustment_semantics") != "UNADJUSTED_CLOSE":
        raise OperatorEnteredPriceError("ONLY_UNADJUSTED_CLOSE_SUPPORTED_IN_V01")
    price = _parse_price(payload.get("price"))
    observation_date = _parse_date(payload.get("observation_date"), "OBSERVATION_DATE")

    entry = _as_shanghai(entered_at, "ENTERED_AT")
    cutoff = _as_shanghai(decision_cutoff_at, "DECISION_CUTOFF_AT")
    if cutoff <= entry:
        raise OperatorEnteredPriceError("DECISION_CUTOFF_MUST_FOLLOW_ENTRY_TIME")
    if observation_date > entry.date():
        raise OperatorEnteredPriceError("OBSERVATION_DATE_IN_FUTURE")
    if payload.get("quote_timestamp") is not None:
        quote_ts = _parse_timestamp(payload.get("quote_timestamp"), "QUOTE_TIMESTAMP")
        if quote_ts.date() != observation_date:
            raise OperatorEnteredPriceError("QUOTE_TIMESTAMP_DATE_MISMATCH")
        if quote_ts > entry:
            raise OperatorEnteredPriceError("QUOTE_TIMESTAMP_AFTER_ENTRY_TIME")
        quote_timestamp = quote_ts.isoformat()
    else:
        quote_timestamp = None

    valid_until = _parse_timestamp(payload.get("valid_until"), "VALID_UNTIL")
    if valid_until <= cutoff:
        raise OperatorEnteredPriceError("PRICE_INPUT_EXPIRED_OR_EXPIRY_NOT_AFTER_CUTOFF")
    source_claim = payload.get("source_claim")
    if source_claim is not None and (not isinstance(source_claim, str) or not source_claim.strip()):
        raise OperatorEnteredPriceError("SOURCE_CLAIM_MUST_BE_NONEMPTY_IF_PRESENT")

    return {
        "schema_version": SCHEMA,
        "record_class": "OPERATOR_ATTESTED_MARKET_DATA",
        "status": STATUS,
        "base_case_id": case_id.strip(),
        "market": market,
        "symbol": symbol,
        "exchange": exchange,
        "currency": currency,
        "unit": f"{currency}/share",
        "observation_date": observation_date.isoformat(),
        "price": format(price, "f"),
        "adjustment_semantics": "UNADJUSTED_CLOSE",
        "quote_timestamp": quote_timestamp,
        "entered_at": entry.isoformat(),
        "decision_cutoff_at": cutoff.isoformat(),
        "valid_until": valid_until.isoformat(),
        "local_clock_is_cryptographically_verified": False,
        "operator_confirmed": True,
        "source_claim": source_claim.strip() if isinstance(source_claim, str) else None,
        "source_claim_verified": False,
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "raw_source_bytes_captured": False,
        "canonical_exchange_price_admission": False,
        "formal_evidence_pit_admission": False,
        "decision_chain_bound": False,
        "formal_decision_authority": False,
        "automatic_execution_authority": False,
    }


def _private_root(path: Path) -> Path:
    if path.is_symlink():
        raise OperatorEnteredPriceError("OUTPUT_ROOT_MUST_NOT_BE_SYMLINK")
    resolved = path.expanduser().resolve(strict=False)
    repo = REPOSITORY_ROOT.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise OperatorEnteredPriceError("OUTPUT_ROOT_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY")
    if not resolved.exists():
        resolved.mkdir(parents=True, mode=0o700)
    if resolved.is_symlink() or not resolved.is_dir():
        raise OperatorEnteredPriceError("OUTPUT_ROOT_MUST_BE_DIRECTORY_NOT_SYMLINK")
    if hasattr(os, "getuid") and resolved.stat().st_uid != os.getuid():
        raise OperatorEnteredPriceError("OUTPUT_ROOT_OWNER_MISMATCH")
    if stat.S_IMODE(resolved.stat().st_mode) & 0o077:
        raise OperatorEnteredPriceError("OUTPUT_ROOT_PERMISSIONS_TOO_OPEN")
    return resolved


def _assert_private_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise OperatorEnteredPriceError(f"{label}_MUST_BE_REGULAR_FILE_NOT_SYMLINK")
    metadata = path.stat()
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise OperatorEnteredPriceError(f"{label}_OWNER_MISMATCH")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise OperatorEnteredPriceError(f"{label}_PERMISSIONS_TOO_OPEN")


def _write_exclusive(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def build_receipt(record: Mapping[str, Any], *, record_bytes: bytes) -> dict[str, Any]:
    digest = _sha(record_bytes)
    return {
        "receipt_schema": RECEIPT_SCHEMA,
        "status": STATUS,
        "record_class": "OPERATOR_ATTESTED_MARKET_DATA",
        "bundle_id": f"operator-price-{digest[:24]}",
        "record_sha256": digest,
        "price_value_present": True,
        "price_value_redacted": True,
        "source_claim_present": record.get("source_claim") is not None,
        "source_claim_redacted": True,
        "source_claim_verified": False,
        "source_origin_verified": False,
        "source_vintage_verified": False,
        "source_use_rights_verified": False,
        "raw_source_bytes_captured": False,
        "canonical_exchange_price_admission": False,
        "formal_evidence_pit_admission": False,
        "decision_chain_bound": False,
        "formal_decision_authority": False,
        "automatic_execution_authority": False,
        "public_upload_allowed": False,
    }


def create_bundle(payload: Mapping[str, Any], output_root: str | Path, *, entered_at: datetime | None = None, decision_cutoff_at: datetime | None = None) -> dict[str, Any]:
    entry = _as_shanghai(entered_at if entered_at is not None else _now_shanghai(), "ENTERED_AT")
    if decision_cutoff_at is None:
        cutoff = _as_shanghai(_now_shanghai(), "DECISION_CUTOFF_AT")
        if cutoff <= entry:
            cutoff = _as_shanghai(_now_shanghai(), "DECISION_CUTOFF_AT")
    else:
        cutoff = _as_shanghai(decision_cutoff_at, "DECISION_CUTOFF_AT")
    if cutoff <= entry:
        raise OperatorEnteredPriceError("DECISION_CUTOFF_MUST_FOLLOW_ENTRY_TIME")
    normalized = validate_payload(payload, entered_at=entry, decision_cutoff_at=cutoff)
    record_bytes = _canonical(normalized) + b"\n"
    digest = _sha(record_bytes)
    receipt = build_receipt(normalized, record_bytes=record_bytes)
    receipt_bytes = _canonical(receipt) + b"\n"
    root = _private_root(Path(output_root))
    bundle_id = f"operator-price-{digest[:24]}"
    bundle_dir = root / bundle_id
    try:
        bundle_dir.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise OperatorEnteredPriceError("CONTENT_ADDRESSED_BUNDLE_ALREADY_EXISTS") from exc
    try:
        _write_exclusive(bundle_dir / "price-input.json", record_bytes)
        _write_exclusive(bundle_dir / "receipt.json", receipt_bytes)
    except Exception:
        # Preserve any partial directory for safe inspection; never overwrite or silently repair it.
        raise
    return {
        "status": STATUS,
        "bundle_id": bundle_id,
        "bundle_path": str(bundle_dir),
        "record_sha256": digest,
        "quote_values_redacted": True,
        "formal_evidence_pit_admission": False,
        "decision_chain_bound": False,
        "formal_decision_authority": False,
    }


def replay_bundle(bundle_path: str | Path) -> dict[str, Any]:
    directory = Path(bundle_path)
    if directory.is_symlink() or not directory.is_dir():
        raise OperatorEnteredPriceError("BUNDLE_MUST_BE_DIRECTORY_NOT_SYMLINK")
    resolved = directory.resolve(strict=True)
    repo = REPOSITORY_ROOT.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise OperatorEnteredPriceError("BUNDLE_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY")
    metadata = directory.stat()
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise OperatorEnteredPriceError("BUNDLE_OWNER_MISMATCH")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise OperatorEnteredPriceError("BUNDLE_PERMISSIONS_TOO_OPEN")
    _assert_private_file(directory / "price-input.json", "PRICE_INPUT_FILE")
    _assert_private_file(directory / "receipt.json", "RECEIPT_FILE")
    record, record_raw = _read_json(directory / "price-input.json")
    receipt, receipt_raw = _read_json(directory / "receipt.json")
    if _canonical(record) + b"\n" != record_raw:
        raise OperatorEnteredPriceError("RECORD_BYTES_NONCANONICAL")
    expected = build_receipt(record, record_bytes=record_raw)
    if receipt != expected:
        raise OperatorEnteredPriceError("RECEIPT_CONTENT_MISMATCH")
    if directory.name != expected["bundle_id"]:
        raise OperatorEnteredPriceError("BUNDLE_ID_MISMATCH")
    if _canonical(receipt) + b"\n" != receipt_raw:
        raise OperatorEnteredPriceError("RECEIPT_BYTES_NONCANONICAL")
    if record.get("status") != STATUS or record.get("record_class") != "OPERATOR_ATTESTED_MARKET_DATA":
        raise OperatorEnteredPriceError("RECORD_STATUS_OR_CLASS_INVALID")
    if any(record.get(key) is not False for key in (
        "local_clock_is_cryptographically_verified", "source_claim_verified",
        "source_origin_verified", "source_vintage_verified", "source_use_rights_verified",
        "raw_source_bytes_captured", "canonical_exchange_price_admission",
        "formal_evidence_pit_admission", "decision_chain_bound", "formal_decision_authority",
        "automatic_execution_authority",
    )):
        raise OperatorEnteredPriceError("PROVENANCE_OR_AUTHORITY_FLAG_ESCALATED")
    # Re-run the full schema/time validation using the immutable recorded timestamps.
    payload = {
        "schema_version": SCHEMA,
        "base_case_id": record.get("base_case_id"),
        "market": record.get("market"),
        "symbol": record.get("symbol"),
        "exchange": record.get("exchange"),
        "currency": record.get("currency"),
        "observation_date": record.get("observation_date"),
        "price": record.get("price"),
        "adjustment_semantics": record.get("adjustment_semantics"),
        "quote_timestamp": record.get("quote_timestamp"),
        "valid_until": record.get("valid_until"),
        "operator_confirmed": record.get("operator_confirmed"),
        "source_claim": record.get("source_claim"),
    }
    validated = validate_payload(
        payload,
        entered_at=_parse_timestamp(record.get("entered_at"), "ENTERED_AT"),
        decision_cutoff_at=_parse_timestamp(record.get("decision_cutoff_at"), "DECISION_CUTOFF_AT"),
    )
    if validated != record:
        raise OperatorEnteredPriceError("RECOMPUTED_RECORD_MISMATCH")
    return {
        "status": "REPLAY_PASS_ANALYSIS_INPUT_ONLY",
        "bundle_id": expected["bundle_id"],
        "record_sha256": expected["record_sha256"],
        "quote_values_redacted": True,
        "formal_evidence_pit_admission": False,
        "decision_chain_bound": False,
        "formal_decision_authority": False,
    }


def _prompt_payload() -> dict[str, Any]:
    print("IIOS 手动股价录入（仅本地存储；不验证来源，也不创建正式决策）")
    case_id = input("现有 Case ID / 新运行标签: ").strip()
    market = input("市场 [CN-A/HK]: ").strip().upper()
    symbol = input("证券代码（A 股六位；港股保留前导零）: ").strip()
    if market == "CN-A":
        exchange = "SSE" if symbol.startswith(("60", "68", "90")) else "SZSE"
        currency = "CNY"
    elif market == "HK":
        exchange, currency = "HKEX", "HKD"
    else:
        raise OperatorEnteredPriceError("UNSUPPORTED_MARKET")
    observation_date = input("行情观察日期 YYYY-MM-DD: ").strip()
    price = input(f"未复权收盘价（{currency}/股）: ").strip()
    quote_timestamp = input("报价时间（含时区；不知道则留空）: ").strip() or None
    valid_until = input("此价格允许本次分析使用至何时（ISO8601 含时区）: ").strip()
    source_claim = input("来源标签（可留空，仅记录为未验证声明）: ").strip() or None
    confirm = input("确认以上手动输入用于分析？输入 YES 继续: ").strip()
    return {
        "schema_version": SCHEMA,
        "base_case_id": case_id,
        "market": market,
        "symbol": symbol,
        "exchange": exchange,
        "currency": currency,
        "observation_date": observation_date,
        "price": price,
        "adjustment_semantics": "UNADJUSTED_CLOSE",
        "quote_timestamp": quote_timestamp,
        "valid_until": valid_until,
        "operator_confirmed": confirm == "YES",
        "source_claim": source_claim,
    }


def _safe_os_error_reason(exc: OSError) -> str:
    """Map filesystem failures to non-path-bearing diagnostics."""
    if exc.errno in {errno.EACCES, errno.EPERM}:
        return "LOCAL_IO_PERMISSION_DENIED"
    if exc.errno == errno.ENOSPC:
        return "LOCAL_IO_NO_SPACE"
    if exc.errno == errno.EEXIST:
        return "LOCAL_IO_PATH_EXISTS"
    if exc.errno == errno.ENOENT:
        return "LOCAL_IO_PATH_NOT_FOUND"
    return "LOCAL_IO_ERROR"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private operator-entered A/H price intake (not formal source admission)")
    parser.add_argument("--output-root", default="~/.iios-private/operator-entered-prices")
    parser.add_argument("--replay-run", help="Replay a saved private bundle")
    args = parser.parse_args(argv)
    try:
        if args.replay_run:
            result = replay_bundle(args.replay_run)
        else:
            payload = _prompt_payload()
            result = create_bundle(payload, args.output_root)
        if "bundle_path" in result:
            result = dict(result)
            result.pop("bundle_path", None)
            result["bundle_path_redacted"] = True
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except OperatorEnteredPriceError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 4
    except OSError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": _safe_os_error_reason(exc)}, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
