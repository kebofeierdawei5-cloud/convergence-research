from __future__ import annotations

import json
from pathlib import Path

import pytest

from iios_mvp.operator_attested_price_input_v01 import (
    ANALYSIS_ONLY_STATUS,
    OPERATOR_PRICE_INPUT_SCHEMA,
    OperatorPriceInputError,
    build_sanitized_receipt,
    persist_operator_price_input,
    validate_operator_price_payload,
)


def _record(*, symbol="002001", exchange="SZSE", price="12.34", known_at="2026-10-09T15:04:24+08:00",
            observation_date="2026-10-09", adjustment="UNADJUSTED_CLOSE", market="CN-A"):
    return {
        "base_case_id": "RC-CN-A-002001-20261009",
        "market": market,
        "symbol": symbol,
        "exchange": exchange,
        "observation_date": observation_date,
        "price": price,
        "currency": "CNY",
        "adjustment_semantics": adjustment,
        "operator_attested_known_at": known_at,
        "sources_claimed": ["manual fixture source A", "manual fixture source B"],
        "attestation_note": "Synthetic test fixture; not a source verification claim.",
    }


def _payload(records=None, *, cutoff="2026-10-10", confirmed=True):
    return {
        "schema_version": OPERATOR_PRICE_INPUT_SCHEMA,
        "operator_confirmed": confirmed,
        "analysis_cutoff_date": cutoff,
        "batch_id": "path-a-test-20261011",
        "records": records or [_record()],
    }


def test_accepts_operator_attested_price_but_never_formal_admission():
    result = validate_operator_price_payload(_payload())
    item = result["records"][0]
    assert result["status"] == ANALYSIS_ONLY_STATUS
    assert item["price"] == "12.34"
    assert item["record_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert item["source_origin_verified"] is False
    assert item["source_vintage_verified"] is False
    assert item["source_use_rights_verified"] is False
    assert item["canonical_price_admission"] is False
    assert item["formal_evidence_pit_admission"] is False
    assert item["decision_authority"] is False
    assert result["scope_controls"]["may_feed_scenario_valuation"] is True
    assert result["scope_controls"]["may_feed_canonical_current_price_resolver"] is False


def test_multiple_current_case_prices_can_be_validated_as_separate_analysis_overlay():
    rows = [
        _record(symbol="002001", exchange="SZSE", price="12.34", known_at="2026-10-09T15:04:24+08:00"),
        _record(symbol="605016", exchange="SSE", price="23.45", known_at="2026-10-09T15:00:00+08:00"),
    ]
    # The second row is kept separate by base case id and security code.
    rows[1]["base_case_id"] = "RC-CN-A-605016-20261009"
    result = validate_operator_price_payload(_payload(rows))
    assert len(result["records"]) == 2
    assert {r["symbol"] for r in result["records"]} == {"002001", "605016"}
    assert all(not r["canonical_price_admission"] for r in result["records"])


def test_cutoff_is_start_of_day_and_known_at_must_precede_cutoff():
    row = _record(known_at="2026-10-10T00:00:00+08:00")
    with pytest.raises(OperatorPriceInputError, match="ATTESTED_KNOWN_AT_NOT_BEFORE_CUTOFF_START"):
        validate_operator_price_payload(_payload([row]))


def test_observation_after_cutoff_fails_closed():
    row = _record(observation_date="2026-10-10", known_at="2026-10-10T15:00:00+08:00")
    with pytest.raises(OperatorPriceInputError, match="OBSERVATION_DATE_AFTER_ANALYSIS_CUTOFF"):
        validate_operator_price_payload(_payload([row], cutoff="2026-10-09"))


def test_requires_explicit_operator_confirmation():
    with pytest.raises(OperatorPriceInputError, match="EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED"):
        validate_operator_price_payload(_payload(confirmed=False))


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity", True, "not-a-price"])
def test_invalid_prices_are_rejected(price):
    with pytest.raises(OperatorPriceInputError, match="PRICE_MUST_BE_POSITIVE_FINITE_NUMBER"):
        validate_operator_price_payload(_payload([_record(price=price)]))


def test_adjusted_price_is_not_silently_relabelled_as_unadjusted():
    with pytest.raises(OperatorPriceInputError, match="ONLY_EXPLICIT_UNADJUSTED_CLOSE_ACCEPTED"):
        validate_operator_price_payload(_payload([_record(adjustment="FORWARD_ADJUSTED_CLOSE")]))


def test_exchange_must_match_symbol():
    with pytest.raises(OperatorPriceInputError, match="EXCHANGE_SYMBOL_MISMATCH"):
        validate_operator_price_payload(_payload([_record(symbol="605016", exchange="SZSE")]))


def test_receipt_redacts_price_and_source_labels():
    normalized = validate_operator_price_payload(_payload())
    receipt = build_sanitized_receipt(normalized, input_sha256="a" * 64)
    encoded = json.dumps(receipt, ensure_ascii=False)
    assert receipt["quote_values_redacted"] is True
    assert receipt["private_source_labels_redacted"] is True
    assert "12.34" not in encoded
    assert "manual fixture source A" not in encoded
    assert receipt["canonical_price_admission"] is False


def test_persistence_writes_private_record_and_redacted_receipt_once(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(_payload(), sort_keys=True), encoding="utf-8")
    private_root = tmp_path / "private"
    receipt = persist_operator_price_input(input_path=input_path, private_root=private_root)
    stored = json.loads((private_root / "operator-attested-prices-path-a.json").read_text(encoding="utf-8"))
    receipt_from_disk = json.loads((private_root / "operator-attested-prices-path-a.receipt.json").read_text(encoding="utf-8"))
    assert stored["records"][0]["price"] == "12.34"
    assert receipt["quote_values_redacted"] is True
    assert receipt_from_disk["quote_values_redacted"] is True
    assert receipt_from_disk["canonical_price_admission"] is False
    with pytest.raises(OperatorPriceInputError, match="OUTPUT_EXISTS_OR_IS_SYMLINK"):
        persist_operator_price_input(input_path=input_path, private_root=private_root)


def test_public_repository_input_is_refused(tmp_path):
    private_root = tmp_path / "private"
    with pytest.raises(OperatorPriceInputError, match="INPUT_PATH_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY"):
        persist_operator_price_input(input_path=Path(__file__), private_root=private_root)


def test_duplicate_case_symbol_observation_rejected():
    row = _record()
    with pytest.raises(OperatorPriceInputError, match="DUPLICATE_CASE_SYMBOL_OBSERVATION"):
        validate_operator_price_payload(_payload([row, dict(row)]))
