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
        "valid_until": "2026-10-13T18:00:00+08:00",
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
    with pytest.raises(price_input.OperatorEnteredPriceError, match="RECORD_BYTES_NONCANONICAL"):
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
    with pytest.raises(price_input.OperatorEnteredPriceError, match="RECORD_BYTES_NONCANONICAL"):
        price_input.replay_bundle(result["bundle_path"])


def test_replay_rejects_self_rehashed_source_verification_escalation(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    bundle = Path(result["bundle_path"])
    price_path = bundle / "price-input.json"
    edited = json.loads(price_path.read_text())
    edited["source_origin_verified"] = True
    record_bytes = price_input._canonical(edited) + b"\n"
    price_path.write_bytes(record_bytes)
    receipt = price_input.build_receipt(edited, record_bytes=record_bytes)
    (bundle / "receipt.json").write_bytes(price_input._canonical(receipt) + b"\n")
    renamed = root / receipt["bundle_id"]
    bundle.rename(renamed)

    with pytest.raises(
        price_input.OperatorEnteredPriceError,
        match="PROVENANCE_OR_AUTHORITY_FLAG_ESCALATED",
    ):
        price_input.replay_bundle(renamed)


def test_symbol_must_be_string_to_preserve_leading_zero_codes():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="SYMBOL_MUST_BE_NONEMPTY_STRING"):
        price_input.validate_payload(
            payload(symbol=2001), entered_at=ENTERED, decision_cutoff_at=CUTOFF
        )


def test_naive_timestamps_are_rejected():
    with pytest.raises(price_input.OperatorEnteredPriceError, match="ENTERED_AT_TIMEZONE_REQUIRED"):
        price_input.validate_payload(
            payload(), entered_at=ENTERED.replace(tzinfo=None), decision_cutoff_at=CUTOFF
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="DECISION_CUTOFF_AT_TIMEZONE_REQUIRED"):
        price_input.validate_payload(
            payload(), entered_at=ENTERED, decision_cutoff_at=CUTOFF.replace(tzinfo=None)
        )


def test_create_bundle_never_invents_a_cutoff_after_entry(tmp_path):
    with pytest.raises(price_input.OperatorEnteredPriceError, match="DECISION_CUTOFF_MUST_FOLLOW_ENTRY_TIME"):
        price_input.create_bundle(
            payload(), tmp_path / "private", entered_at=ENTERED, decision_cutoff_at=ENTERED
        )


def test_replay_rejects_noncanonical_private_record_bytes(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    price_path = Path(result["bundle_path"]) / "price-input.json"
    price_path.write_bytes(price_path.read_bytes() + b" ")
    with pytest.raises(price_input.OperatorEnteredPriceError, match="RECORD_BYTES_NONCANONICAL"):
        price_input.replay_bundle(result["bundle_path"])


def test_replay_rejects_open_permissions_on_private_input(tmp_path):
    root = private_root(tmp_path / "private")
    result = price_input.create_bundle(
        payload(), root, entered_at=ENTERED, decision_cutoff_at=CUTOFF
    )
    price_path = Path(result["bundle_path"]) / "price-input.json"
    os.chmod(price_path, 0o644)
    with pytest.raises(price_input.OperatorEnteredPriceError, match="PRICE_INPUT_FILE_PERMISSIONS_TOO_OPEN"):
        price_input.replay_bundle(result["bundle_path"])


def operator_reference(root: Path):
    bundle = price_input.create_bundle(
        payload(),
        root,
        entered_at=ENTERED,
        decision_cutoff_at=CUTOFF,
    )
    return {
        "bundle_id": bundle["bundle_id"],
        "record_sha256": bundle["record_sha256"],
        "receipt_sha256": bundle["receipt_sha256"],
    }


def test_operator_price_resolver_binds_exact_private_bundle_and_cutoff(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    cutoff = __import__("datetime").date(2026, 10, 12)
    observation = resolver.build_current_price_observation(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=cutoff,
        mie_reference_price_observation_id="official-price-ref-20261009",
    )
    bound = resolver.resolve_operator_price_input(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=cutoff,
        current_price_observation=observation,
    )
    assert bound["status"] == "OPERATOR_PRICE_INPUT_BOUND"
    assert bound["bundle_id"] == reference["bundle_id"]
    assert bound["record_sha256"] == reference["record_sha256"]
    assert bound["receipt_sha256"] == reference["receipt_sha256"]
    assert bound["price"] == "26.58"
    assert bound["record_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert bound["formal_evidence_pit_admission"] is False
    assert bound["source_origin_verified"] is False
    assert bound["source_use_rights_verified"] is False
    assert observation["price_observation_id"] == reference["bundle_id"]
    assert observation["adjustment_semantics"] == "UNADJUSTED"
    assert observation["operator_input_adjustment_semantics"] == "UNADJUSTED_CLOSE"
    assert "price_observation_admission_hash" not in observation


def test_operator_price_resolver_allows_intraday_entry_on_cutoff_date(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    result = resolver.resolve_operator_price_input(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
    )
    assert result["status"] == "OPERATOR_PRICE_INPUT_BOUND"


def test_operator_price_resolver_blocks_input_entered_after_case_cutoff_date(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    with pytest.raises(
        price_input.OperatorEnteredPriceError,
        match="OPERATOR_PRICE_ENTERED_AFTER_CUTOFF_DATE",
    ):
        resolver.resolve_operator_price_input(
            reference,
            case_id="RC-CN-A-002001-20261012",
            market="CN-A",
            symbol="002001",
            currency="CNY",
            cutoff_date=__import__("datetime").date(2026, 10, 10),
        )


def test_operator_price_resolver_rejects_wrong_case_symbol_and_ref_hash(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    with pytest.raises(price_input.OperatorEnteredPriceError, match="OPERATOR_PRICE_CASE_ID_MISMATCH"):
        resolver.resolve_operator_price_input(
            reference, case_id="WRONG-CASE", market="CN-A", symbol="002001",
            currency="CNY", cutoff_date=__import__("datetime").date(2026, 10, 12),
        )
    with pytest.raises(price_input.OperatorEnteredPriceError, match="OPERATOR_PRICE_INSTRUMENT_MISMATCH"):
        resolver.resolve_operator_price_input(
            reference, case_id="RC-CN-A-002001-20261012", market="CN-A", symbol="002353",
            currency="CNY", cutoff_date=__import__("datetime").date(2026, 10, 12),
        )
    changed = dict(reference)
    changed["record_sha256"] = "0" * 64
    with pytest.raises(price_input.OperatorEnteredPriceError, match="OPERATOR_PRICE_BUNDLE_ID_HASH_MISMATCH"):
        resolver.resolve_operator_price_input(
            changed, case_id="RC-CN-A-002001-20261012", market="CN-A", symbol="002001",
            currency="CNY", cutoff_date=__import__("datetime").date(2026, 10, 12),
        )


def test_operator_price_resolver_rejects_forged_canonical_price_flags(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    observation = resolver.build_current_price_observation(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
        mie_reference_price_observation_id="official-price-ref-20261009",
    )
    observation["price_observation_admission_hash"] = "a" * 64
    with pytest.raises(
        price_input.OperatorEnteredPriceError,
        match="OPERATOR_PRICE_MUST_NOT_CLAIM_CANONICAL_ADMISSION",
    ):
        resolver.resolve_operator_price_input(
            reference, case_id="RC-CN-A-002001-20261012", market="CN-A",
            symbol="002001", currency="CNY",
            cutoff_date=__import__("datetime").date(2026, 10, 12),
            current_price_observation=observation,
        )


def test_operator_price_resolver_rejects_every_assurance_flag_escalation(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    observation = resolver.build_current_price_observation(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
        mie_reference_price_observation_id="official-price-ref-20261009",
    )
    flags = (
        "source_claim_verified",
        "source_origin_verified",
        "source_vintage_verified",
        "source_use_rights_verified",
        "raw_source_bytes_captured",
        "canonical_exchange_price_admission",
        "canonical_price_admission",
        "formal_evidence_pit_admission",
    )
    for flag in flags:
        forged = dict(observation)
        forged[flag] = True
        with pytest.raises(
            price_input.OperatorEnteredPriceError,
            match="OPERATOR_PRICE_PROVENANCE_FLAG_ESCALATED",
        ):
            resolver.resolve_operator_price_input(
                reference,
                case_id="RC-CN-A-002001-20261012",
                market="CN-A",
                symbol="002001",
                currency="CNY",
                cutoff_date=__import__("datetime").date(2026, 10, 12),
                current_price_observation=forged,
            )


def test_operator_price_resolver_rejects_exchange_metadata_tampering(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    observation = resolver.build_current_price_observation(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
        mie_reference_price_observation_id="official-price-ref-20261009",
    )
    observation["exchange"] = "SSE"
    with pytest.raises(
        price_input.OperatorEnteredPriceError,
        match="OPERATOR_PRICE_EXCHANGE_MISMATCH",
    ):
        resolver.resolve_operator_price_input(
            reference,
            case_id="RC-CN-A-002001-20261012",
            market="CN-A",
            symbol="002001",
            currency="CNY",
            cutoff_date=__import__("datetime").date(2026, 10, 12),
            current_price_observation=observation,
        )


def test_operator_price_resolver_never_marks_unverified_mie_reference_as_price_evidence(tmp_path):
    root = private_root(tmp_path / "private")
    reference = operator_reference(root)
    resolver = price_input.FileSystemOperatorPriceInputResolver(root)
    observation = resolver.build_current_price_observation(
        reference,
        case_id="RC-CN-A-002001-20261012",
        market="CN-A",
        symbol="002001",
        currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
        mie_reference_price_observation_id="caller-provided-ref",
    )
    bound = resolver.resolve_operator_price_input(
        reference, case_id="RC-CN-A-002001-20261012", market="CN-A",
        symbol="002001", currency="CNY",
        cutoff_date=__import__("datetime").date(2026, 10, 12),
        current_price_observation=observation,
    )
    assert bound["source_origin_verified"] is False
    assert bound["source_vintage_verified"] is False
    assert bound["formal_evidence_pit_admission"] is False
    assert bound["decision_chain_bound"] is False


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


def test_unsupported_a_share_code_prefix_is_rejected():
    with pytest.raises(
        price_input.OperatorEnteredPriceError,
        match="UNSUPPORTED_A_SHARE_CODE_PREFIX",
    ):
        price_input.validate_payload(
            payload(symbol="900001", exchange="SSE"),
            entered_at=ENTERED, decision_cutoff_at=CUTOFF
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
            payload(quote_timestamp="2026-10-11T12:00:01+08:00", observation_date="2026-10-11"),
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


def test_cli_redacts_private_output_path_and_price(tmp_path, monkeypatch, capsys):
    root = private_root(tmp_path / "private")
    monkeypatch.setattr(price_input, "_prompt_payload", lambda: payload())
    assert price_input.main(["--output-root", str(root)]) == 0
    output = capsys.readouterr().out
    receipt = json.loads(output)
    assert receipt["bundle_path_redacted"] is True
    assert "bundle_path" not in receipt
    assert str(root) not in output
    assert "26.58" not in output


def test_filesystem_error_diagnostic_does_not_leak_private_path():
    error = PermissionError(13, "permission denied", "/Users/private-user/.iios-private")
    diagnostic = price_input._safe_os_error_reason(error)
    assert diagnostic == "LOCAL_IO_PERMISSION_DENIED"
    assert "/Users/private-user" not in diagnostic


def test_tilde_expansion_does_not_bypass_output_symlink_guard(tmp_path, monkeypatch):
    home = tmp_path / "home"
    private_parent = home / ".iios-private"
    private_parent.mkdir(parents=True, mode=0o700)
    target = private_root(tmp_path / "real-target")
    link = private_parent / "link"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(price_input.OperatorEnteredPriceError, match="OUTPUT_ROOT_MUST_NOT_BE_SYMLINK"):
        price_input._private_root(Path("~/.iios-private/link"))


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
