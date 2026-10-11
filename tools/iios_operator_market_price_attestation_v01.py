from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from research.b2.evidence_contract import assert_pit, parse_temporal, validate_evidence_record

POLICY_ID = "IIOS-OPERATOR-MARKET-PRICE-ATTESTATION-0.1"
ARTIFACT_NAME = "operator_market_price_attestation.json"
RELATIVE_RAW_PATH = f"raw/{ARTIFACT_NAME}"


class OperatorMarketPriceAttestationError(ValueError):
    """Invalid or cutoff-incompatible operator-attested market-price input."""


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _cutoff_instant(value: str) -> str:
    try:
        return parse_temporal(value, "cutoff_date").isoformat()
    except ValueError as exc:
        raise OperatorMarketPriceAttestationError("CUTOFF_INVALID") from exc


def _close_decimal(value: Any) -> Decimal:
    try:
        close = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OperatorMarketPriceAttestationError("CLOSE_PRICE_INVALID") from exc
    if not close.is_finite() or close <= 0 or close.as_tuple().exponent < -4:
        raise OperatorMarketPriceAttestationError("CLOSE_PRICE_INVALID")
    return close


def build_operator_market_price_bundle(
    *,
    case_id: str,
    market: str,
    symbol: str,
    company: str,
    cutoff_date: str,
    observation_date: str,
    close_price: str | int | float | Decimal,
    currency: str,
    source_ref: str,
    out_dir: Path,
    operator_confirmed: bool,
    known_by_cutoff_confirmed: bool,
    known_at: str | None = None,
    attested_at: str | None = None,
) -> dict[str, Any]:
    """Write a private, hash-bound operator attestation; never fetch the cited URL."""
    if operator_confirmed is not True:
        raise OperatorMarketPriceAttestationError("OPERATOR_CONFIRMATION_REQUIRED")
    if known_by_cutoff_confirmed is not True:
        raise OperatorMarketPriceAttestationError("KNOWN_BY_CUTOFF_ATTESTATION_REQUIRED")
    for name, value in (
        ("case_id", case_id), ("symbol", symbol), ("company", company), ("source_ref", source_ref)
    ):
        if not isinstance(value, str) or not value.strip():
            raise OperatorMarketPriceAttestationError(f"{name.upper()}_REQUIRED")
    if market not in {"CN-A", "HK"}:
        raise OperatorMarketPriceAttestationError("MARKET_INVALID")
    if currency not in {"CNY", "HKD"}:
        raise OperatorMarketPriceAttestationError("CURRENCY_INVALID")
    try:
        observed = date.fromisoformat(observation_date)
    except (TypeError, ValueError) as exc:
        raise OperatorMarketPriceAttestationError("OBSERVATION_DATE_INVALID") from exc
    if observed.isoformat() != observation_date:
        raise OperatorMarketPriceAttestationError("OBSERVATION_DATE_INVALID")

    cutoff = _cutoff_instant(cutoff_date)
    cutoff_dt = parse_temporal(cutoff, "cutoff_date")
    known = known_at or f"{observation_date}T23:59:59+08:00"
    try:
        known_dt = parse_temporal(known, "known_at")
    except ValueError as exc:
        raise OperatorMarketPriceAttestationError("KNOWN_AT_INVALID") from exc
    if known_dt > cutoff_dt:
        raise OperatorMarketPriceAttestationError("KNOWN_AT_AFTER_CUTOFF")
    if known_dt.date().isoformat() != observation_date:
        raise OperatorMarketPriceAttestationError("KNOWN_AT_MUST_BIND_TO_OBSERVATION_DATE")
    if currency == "CNY" and market != "CN-A":
        raise OperatorMarketPriceAttestationError("CURRENCY_MARKET_MISMATCH")
    if currency == "HKD" and market != "HK":
        raise OperatorMarketPriceAttestationError("CURRENCY_MARKET_MISMATCH")

    close = _close_decimal(close_price)
    close_text = format(close, "f")
    if attested_at is None:
        attested_at = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    try:
        parse_temporal(attested_at, "attested_at")
    except ValueError as exc:
        raise OperatorMarketPriceAttestationError("ATTESTED_AT_INVALID") from exc

    artifact = {
        "schema_version": POLICY_ID,
        "policy_id": POLICY_ID,
        "record_class": "OPERATOR_ATTESTED_MARKET_PRICE_NOT_SOURCE_BYTE_VERIFIED",
        "operator_confirmed": True,
        "secondary_web_audit_performed": False,
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "company": company,
        "cutoff_date": cutoff,
        "observation_date": observation_date,
        "close_price": close_text,
        "currency": currency,
        "source_ref": source_ref.strip(),
        "known_at": known,
        "known_at_basis": "OPERATOR_ATTESTS_AVAILABLE_BY_END_OF_OBSERVATION_DATE",
        "attested_at": attested_at,
        "original_vendor_bytes_received": False,
        "admission_boundary": "Human-attested value only. The source URL is recorded for lineage but is not fetched or independently verified.",
    }
    raw_bytes = _canonical_bytes(artifact)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    evidence_id = f"OPERATOR-PRICE-{symbol}-{observation_date.replace('-', '')}"
    evidence = {
        "evidence_id": evidence_id,
        "subject_id": case_id,
        "field_id": "market_price.close_price",
        "claim_type": "OPERATOR_ATTESTED_MARKET_PRICE",
        "value": float(close),
        "unit": f"{currency}/share",
        "currency": currency,
        "observation_date": observation_date,
        "period": None,
        "published_at": None,
        "known_at": known,
        "retrieved_at": attested_at,
        "effective_from": observation_date,
        "effective_to": None,
        "source_ref": source_ref.strip(),
        "source_version": "Operator attestation v0.1; original vendor bytes not received",
        "source_locator": "private operator attestation JSON / close_price",
        "artifact_id": RELATIVE_RAW_PATH,
        "content_sha256": digest,
        "capture_sha256": digest,
        "exact_bytes": True,
        "provenance_class": "OPERATOR_ATTESTED_MARKET_DATA",
        "status": "ADMITTED",
        "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
        "parents": [],
        "quality_notes": [
            "OPERATOR_ATTESTED_NOT_INDEPENDENTLY_SOURCE_VERIFIED",
            "SECONDARY_WEB_AUDIT_PERFORMED=FALSE",
            "ORIGINAL_VENDOR_BYTES_RECEIVED=FALSE",
            "KNOWN_AT_IS_OPERATOR_ATTESTATION_NOT_SOURCE_TIMESTAMP_VERIFICATION",
        ],
        "license_status": "UNKNOWN",
        "operator_attestation": {
            "policy_id": POLICY_ID,
            "operator_confirmed": True,
            "secondary_web_audit_performed": False,
            "case_id": case_id,
            "market": market,
            "symbol": symbol,
            "company": company,
            "observation_date": observation_date,
            "close_price": close_text,
            "currency": currency,
            "source_ref": source_ref.strip(),
            "known_at": known,
            "known_at_basis": "OPERATOR_ATTESTS_AVAILABLE_BY_END_OF_OBSERVATION_DATE",
            "attested_at": attested_at,
            "original_vendor_bytes_received": False,
        },
    }
    errors = validate_evidence_record(evidence)
    if errors:
        raise OperatorMarketPriceAttestationError("EVIDENCE_RECORD_INVALID:" + ";".join(errors))
    try:
        assert_pit(evidence, cutoff)
    except ValueError as exc:
        raise OperatorMarketPriceAttestationError("EVIDENCE_PIT_INVALID:" + str(exc)) from exc

    raw_declaration = {
        "evidence_id": evidence_id,
        "relative_path": RELATIVE_RAW_PATH,
        "expected_size_bytes": len(raw_bytes),
        "expected_sha256": digest,
    }

    output = Path(out_dir)
    if output.exists() and any(output.iterdir()):
        raise OperatorMarketPriceAttestationError("OUTPUT_DIRECTORY_MUST_BE_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(output, 0o700)
    except OSError:
        pass
    raw_path = output / RELATIVE_RAW_PATH
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_bytes)
    (output / "evidence_record.json").write_bytes(_canonical_bytes(evidence))
    (output / "raw_artifact_declaration.json").write_bytes(_canonical_bytes(raw_declaration))
    for path in (raw_path, output / "evidence_record.json", output / "raw_artifact_declaration.json"):
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    return {
        "status": "OPERATOR_ATTESTATION_CREATED_NOT_SOURCE_VERIFIED",
        "policy_id": POLICY_ID,
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "observation_date": observation_date,
        "known_at": known,
        "known_at_before_or_at_cutoff": True,
        "secondary_web_audit_performed": False,
        "original_vendor_bytes_received": False,
        "private_artifact_written": True,
        "private_artifact_sha256": digest,
        "private_artifact_size_bytes": len(raw_bytes),
        "close_price_in_summary": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a private, explicitly operator-attested market-price evidence bundle. Does not fetch the source URL."
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--market", choices=["CN-A", "HK"], required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--cutoff-date", required=True)
    parser.add_argument("--observation-date", required=True)
    parser.add_argument("--close-price", required=True)
    parser.add_argument("--currency", choices=["CNY", "HKD"], required=True)
    parser.add_argument("--source-ref", required=True, help="User-provided source URL or operator-declared source description")
    parser.add_argument("--out-dir", required=True, help="Private local directory; never upload to public GitHub")
    parser.add_argument("--known-at", default=None, help="Defaults to 23:59:59 +08 on the observation date; operator attests this is cutoff-safe")
    parser.add_argument("--attested-at", default=None)
    parser.add_argument("--confirm-operator-attestation", action="store_true", help="Confirm that the operator is supplying and accepts responsibility for this value")
    parser.add_argument("--confirm-known-by-cutoff", action="store_true", help="Confirm value was available by the declared known_at, which must not exceed cutoff")
    args = parser.parse_args()
    try:
        result = build_operator_market_price_bundle(
            case_id=args.case_id,
            market=args.market,
            symbol=args.symbol,
            company=args.company,
            cutoff_date=args.cutoff_date,
            observation_date=args.observation_date,
            close_price=args.close_price,
            currency=args.currency,
            source_ref=args.source_ref,
            out_dir=Path(args.out_dir),
            operator_confirmed=args.confirm_operator_attestation,
            known_by_cutoff_confirmed=args.confirm_known_by_cutoff,
            known_at=args.known_at,
            attested_at=args.attested_at,
        )
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({
            "status": "BLOCKED",
            "error_code": code,
            "private_artifact_written": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
