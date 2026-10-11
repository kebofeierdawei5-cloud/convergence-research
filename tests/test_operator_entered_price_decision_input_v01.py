from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
import stat

import pytest

from iios_mvp import operator_entered_price_decision_input_v01 as price_input


ENTERED = datetime.fromisoformat("2026-10-11T12:00:00+08:00")
CUTOFF = datetime.fromisoformat("2026-10-11T12:00:02+08:00")


def payload(**overrides):
    data = {
        "schema_version": price_input.SCHEMA,
        "base_case_id": "RC-CN-A-002001-20261012",
        "market": "CN-A",
        "symbol": "002001",
        "exchange": "SZSE",
        "currency": "CNY",
        "observation_date": "2026-10-09",
        "price": "26.58",
        "adjustment_semantics": "UNADJUSTED_CLOSE",
        "quote_timestamp": "2026-10-09T15:00:00+08:00",
        "valid_until": "2026-10-12T18:00:00+08:00",
        "operator_confirmed": True,
        "source_claim": None,
    }
    data.update(overrides)
    return data


def private_root(path: Path) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def test_valid_input_is_private_redacted_and_not_formal_admission(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    bundle = Path(result["bundle_path"])
    private_record = json.loads((bundle / "price-input.json").read_text())
    receipt = json.loads((bundle / "receipt.json").read_text())

    assert result["status"] == price_input.STATUS
    assert private_record["price"] == "26.58"
    assert private_record["record_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert private_record["entered_at"] == ENTERED.isoformat()
    assert private_record["decision_cutoff_at"] > private_record["entered_at"]
    assert private_record["source_origin_verified"] is False
    assert private_record["source_vintage_verified"] is False
    assert private_record["source_use_rights_verified"] is False
    assert private_record["formal_evidence_pit_admission"] is False
    assert private_record["decision_chain_bound"] is False
    assert receipt["price_value_redacted"] is True
    assert "price" not in receipt
    assert "26.58" not in (bundle / "receipt.json").read_text()
    assert stat.S_IMODE(bundle.stat().st_mode) == 0o700
    assert stat.S_IMODE((bundle / "price-input.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((bundle / "receipt.json").stat().st_mode) == 0o600
    assert result["formal_decision_authority"] is False


def test_replay_recomputes_hash_and_preserves_noncanonical_authority(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(source_claim="user says broker screen; NOT VERIFIED"),
        root,
        entered_at=ENTERED,
        decision_cutoff_at=CUTOFF,
    )
    replay = price_input.replay_bundle(result["bundle_path"])
    assert replay["status"] == "REPLAY_PASS_ANALYSIS_INPUT_ONLY"
    assert replay["bundle_id"] == result["bundle_id"]
    assert replay["formal_evidence_pit_admission"] is False
    assert replay["decision_chain_bound"] is False
    assert replay["formal_decision_authority"] is False


def test_replay_blocks_tampered_private_price_bytes(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    price_path = Path(result["bundle_path"]) / "price-input.json"
    edited = json.loads(price_path.read_text())
    edited["price"] = "99.99"
    price_path.write_text(json.dumps(edited))
    with pytest.raises(price_input.OperatorEnteredPriceError, match="RECEIPT_CONTENT_MISMATCH"):
        price_input.replay_bundle(result["bundle_path"])


def test_replay_blocks_authority_flag_escalation(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    price_path = Path(result["bundle_path"]) / "price-input.json"
    edited = json.loads(price_path.read_text())
    edited["formal_evidence_pit_admission"] = True
    price_path.write_text(json.dumps(edited))
    with pytest.raises(price_input.OperatorEnteredPriceError, match="RECEIPT_CONTENT_MISMATCH"):
        price_input.replay_bundle(result["bundle_path"])


def test_missing_confirmation_fails_closed(tmp_path):
    with pytest.raises(price_input.OperatorEnteredPriceError, match="EXPLICIT_OPERATOR_CONFIRMATION_REQUIRED"):
        price_input.create_bundle(
            payload(operator_confirmed=False),
            tmp_path / "private",
            entered_at=ENTERED,
            decision_cutoff_at=CUTOFF,
        )


def test_wrong_exchange_or_currency_fails_closed():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="EXCHANGE_SYMBOL_MISMATCH"):
        price_input.validate_payload(
            payload(exchange="SSE"), entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="CURRENCY_MUST_BE_CNY"):
        price_input.validate_payload(
            payload(currency="HKD"), entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )


def test_hong_kong_input_preserves_leading_zero_and_uses_hkd():
    hk = payload(
        base_case_id="RC-HK-0700-20261012",
        market="HK",
        symbol="0700",
        exchange="HKEX",
        currency="HKD",
        price="612.5",
        quote_timestamp=None,
    )
    normalized = price_input.validate_payload(
        hk, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    assert normalized["symbol"] == "0700"
    assert normalized["exchange"] == "HKEX"
    assert normalized["currency"] == "HKD"
    assert normalized["unit"] == "HKD/share"


def test_adjusted_price_and_invalid_decimal_fails_closed():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="ONLY_UNADJUSTED_CLOSE_SUPPORTED"):
        price_input.validate_payload(
            payload(adjustment_semantics="FORWARD_ADJUSTED"),
            entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="PRICE_MUST_BE_POSITIVE_FINITE_NUMBER"):
        price_input.validate_payload(
            payload(price="NaN"), entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="PRICE_PRECISION_EXCEEDS_SIX"):
        price_input.validate_payload(
            payload(price="1.1234567"), entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )


def test_stale_quote_and_future_timestamp_fail_closed():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="PRICE_INPUT_EXPIRED"):
        price_input.validate_payload(
            payload(valid_until="2026-10-11T12:00:01+08:00"),
            entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="QUOTE_TIMESTAMP_AFTER_ENTRY_TIME"):
        price_input.validate_payload(
            payload(quote_timestamp="2026-10-11T12:00:01+08:00"),
            entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="OBSERVATION_DATE_IN_FUTURE"):
        price_input.validate_payload(
            payload(observation_date="2026-10-12", quote_timestamp=None),
            entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )


def test_cutoff_must_strictly_follow_local_entry_time():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="DECISION_CUTOFF_MUST_FOLLOW_ENTRY_TIME"):
        price_input.validate_payload(
            payload(), entered_at=ENTERED, decision_cutoff_at=ENTERED
        )


def test_private_root_blocks_public_repository_and_open_permissions(tmp_path):
    with pytest.raises(price_input.OperatorEnteredPriceError, match="OUTSIDE_PUBLIC_REPOSITORY"):
        price_input._private_root(price_input.REPOSITORY_ROOT)
    opened = tmp_path / "opened"
    opened.mkdir(mode=0o755)
    opened.chmod(0o755)
    with pytest.raises(price_input.OperatorEnteredPriceError, match="PERMISSIONS_TOO_OPEN"):
        price_input._private_root(opened)


def test_changed_input_never_overwrites_content_addressed_bundle(tmp_path):
    root = private_root(tmp_path / "private")
    first = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="CONTENT_ADDRESSED_BUNDLE_ALREADY_EXISTS"):
        price_input.create_bundle(
            payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )
    changed = price_input.create_bundle(
        payload(price="26.59"), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    assert changed["bundle_id"] != first["bundle_id"]


def test_duplicate_json_keys_rejected(tmp_path):
    target = tmp_path / "duplicate.json"
    target.write_text('{"a": 1, "a": 2}')
    with pytest.raises(price_input.OperatorEnteredPriceError, match="DUPLICATE_JSON_KEY"):
        price_input._read_json(target)
