from __future__ import annotations

import json
from pathlib import Path
import stat

import pytest

from iios_mvp.operator_attested_price_input_v01 import (
    OPERATOR_PRICE_INPUT_SCHEMA,
    validate_operator_price_payload,
)
from iios_mvp.private_scenario_analysis_v01 import (
    PrivateScenarioAnalysisError,
    SCENARIO_ONLY_STATUS,
    _SCENARIO_PROFILES,
    _validate_profile,
    run_private_scenario_analysis,
    verify_private_scenario_bundle,
)


def _row(*, case_id: str, symbol: str, exchange: str, price: str, known_at: str) -> dict:
    return {
        "base_case_id": case_id,
        "market": "CN-A",
        "symbol": symbol,
        "exchange": exchange,
        "observation_date": "2026-10-09",
        "price": price,
        "currency": "CNY",
        "adjustment_semantics": "UNADJUSTED_CLOSE",
        "operator_attested_known_at": known_at,
        "sources_claimed": ["synthetic source A", "synthetic source B"],
        "attestation_note": "Synthetic test fixture only; not source verification.",
    }


def _normalized_price_record() -> dict:
    payload = {
        "schema_version": OPERATOR_PRICE_INPUT_SCHEMA,
        "operator_confirmed": True,
        "analysis_cutoff_date": "2026-10-10",
        "batch_id": "path-a-scenario-test-20261011",
        "records": [
            _row(
                case_id="RC-CN-A-002001-20261009",
                symbol="002001",
                exchange="SZSE",
                price="26.58",
                known_at="2026-10-09T15:04:24+08:00",
            ),
            _row(
                case_id="RC-CN-A-605016-20261009",
                symbol="605016",
                exchange="SSE",
                price="20.28",
                known_at="2026-10-09T15:00:00+08:00",
            ),
        ],
    }
    return validate_operator_price_payload(payload)


def _write_input(tmp_path: Path, *, normalized: dict | None = None) -> Path:
    path = tmp_path / "private-prices.json"
    data = normalized if normalized is not None else _normalized_price_record()
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_runs_both_existing_cases_and_calculates_binding_entry_prices(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(
        input_path=input_path,
        output_root=tmp_path / "private-scenario-output",
    )
    assert result["status"] == "SCENARIO_ANALYSIS_CREATED"
    assert result["status"] != "BLOCKED"
    assert result["replay_status"] == "REPLAY_PASS"
    assert result["company_count"] == 2
    bundle = Path(result["run_dir"])
    machine = json.loads((bundle / "analysis.json").read_text(encoding="utf-8"))
    companies = {row["case"]["symbol"]: row for row in machine["company_analyses"]}
    assert companies["002001"]["return_and_entry_evaluation"]["expected_terminal_wealth_per_share_cny"] == "31.18500000"
    assert companies["002001"]["return_and_entry_evaluation"]["binding_conditional_entry_price_ceiling_cny"] == "26.60000000"
    assert companies["605016"]["return_and_entry_evaluation"]["expected_terminal_wealth_per_share_cny"] == "23.62500000"
    assert companies["605016"]["return_and_entry_evaluation"]["entry_price_ceiling_from_max_bear_loss_cny"] == "18.13333333"
    assert companies["605016"]["return_and_entry_evaluation"]["conditional_price_screen"] == "PRICE_ABOVE_CONDITIONAL_ENTRY_CEILING"
    assert machine["governance"]["formal_decision_created"] is False
    assert machine["governance"]["decision_authority"] is False
    assert machine["governance"]["canonical_price_admission"] is False


def test_repeat_run_reuses_immutable_identical_bundle_without_overwrite(tmp_path):
    input_path = _write_input(tmp_path)
    out = tmp_path / "private-scenario-output"
    first = run_private_scenario_analysis(input_path=input_path, output_root=out)
    first_report = (Path(first["run_dir"]) / "report.md").read_bytes()
    second = run_private_scenario_analysis(input_path=input_path, output_root=out)
    assert second["status"] == "SCENARIO_ANALYSIS_REUSED_IDENTICAL"
    assert second["analysis_id"] == first["analysis_id"]
    assert second["report_file_sha256"] == first["report_file_sha256"]
    assert (Path(first["run_dir"]) / "report.md").read_bytes() == first_report
    assert len(list(out.glob("patha-scenario-*"))) == 1


def test_replay_passes_for_untampered_bundle_and_blocks_modified_report(tmp_path):
    input_path = _write_input(tmp_path)
    first = run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")
    bundle = Path(first["run_dir"])
    assert verify_private_scenario_bundle(bundle)["status"] == "REPLAY_PASS"
    report_path = bundle / "report.md"
    report_path.write_text(report_path.read_text(encoding="utf-8") + "\nTampered.\n", encoding="utf-8")
    with pytest.raises(PrivateScenarioAnalysisError, match="BUNDLE_REPORT_REPLAY_MISMATCH"):
        verify_private_scenario_bundle(bundle)


def test_replay_detects_private_input_tampering(tmp_path):
    input_path = _write_input(tmp_path)
    first = run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")
    bundle = Path(first["run_dir"])
    stored = json.loads((bundle / "input.json").read_text(encoding="utf-8"))
    stored["records"][0]["price"] = "99.99"
    (bundle / "input.json").write_text(json.dumps(stored, sort_keys=True), encoding="utf-8")
    with pytest.raises(PrivateScenarioAnalysisError, match="BUNDLE_ANALYSIS_REPLAY_MISMATCH|BUNDLE_RECEIPT_BINDING_MISMATCH"):
        verify_private_scenario_bundle(bundle)


def test_report_and_receipt_keep_source_claim_labels_and_price_values_out_of_receipt(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")
    bundle = Path(result["run_dir"])
    receipt_text = (bundle / "receipt.json").read_text(encoding="utf-8")
    report_text = (bundle / "report.md").read_text(encoding="utf-8")
    assert "synthetic source A" not in receipt_text
    assert "synthetic source B" not in receipt_text
    assert "26.58" not in receipt_text
    assert "20.28" not in receipt_text
    assert "26.58" in report_text
    assert "20.28" in report_text
    receipt = json.loads(receipt_text)
    assert receipt["quote_values_redacted"] is True
    assert receipt["private_source_labels_redacted"] is True
    assert receipt["public_upload_allowed"] is False
    assert receipt["decision_authority"] is False
    assert receipt["formal_decision_created"] is False


def test_output_files_and_directory_are_private(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "private-out")
    bundle = Path(result["run_dir"])
    if hasattr(stat, "S_IMODE"):
        assert stat.S_IMODE(bundle.stat().st_mode) == 0o700
        for name in ("input.json", "analysis.json", "report.md", "receipt.json"):
            assert stat.S_IMODE((bundle / name).stat().st_mode) == 0o600


def test_public_repository_input_is_refused(tmp_path):
    with pytest.raises(PrivateScenarioAnalysisError, match="INPUT_PATH_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY"):
        run_private_scenario_analysis(input_path=Path(__file__), output_root=tmp_path / "out")


def test_public_repository_output_is_refused(tmp_path):
    input_path = _write_input(tmp_path)
    from iios_mvp.private_scenario_analysis_v01 import REPOSITORY_ROOT
    with pytest.raises(PrivateScenarioAnalysisError, match="OUTPUT_ROOT_MUST_BE_OUTSIDE_PUBLIC_REPOSITORY"):
        run_private_scenario_analysis(input_path=input_path, output_root=REPOSITORY_ROOT / "private-output-test")


def test_wrong_case_or_symbol_fails_closed(tmp_path):
    normalized = _normalized_price_record()
    normalized["records"][0]["base_case_id"] = "RC-CN-A-999999-20261009"
    input_path = _write_input(tmp_path, normalized=normalized)
    with pytest.raises(PrivateScenarioAnalysisError, match="UNSUPPORTED_SCENARIO_PROFILE_FOR_CASE"):
        run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")


@pytest.mark.parametrize("flag", [
    "source_origin_verified",
    "source_vintage_verified",
    "source_use_rights_verified",
    "canonical_price_admission",
    "formal_evidence_pit_admission",
    "decision_authority",
])
def test_forbidden_price_authority_flags_must_stay_false(tmp_path, flag):
    normalized = _normalized_price_record()
    normalized["records"][0][flag] = True
    input_path = _write_input(tmp_path, normalized=normalized)
    with pytest.raises(PrivateScenarioAnalysisError, match="FORBIDDEN_PRICE_AUTHORITY_FLAG_NOT_FALSE"):
        run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")


def test_probability_integrity_is_exact_and_fail_closed():
    profile = dict(_SCENARIO_PROFILES["RC-CN-A-002001-20261009"])
    profile["scenarios"] = {key: dict(value) for key, value in profile["scenarios"].items()}
    profile["scenarios"]["bull"]["probability"] = "0.21"
    with pytest.raises(PrivateScenarioAnalysisError, match="SCENARIO_PROBABILITIES_MUST_SUM_TO_ONE"):
        _validate_profile(profile)


def test_input_changes_create_new_content_addressed_run_not_overwrite(tmp_path):
    input_path = _write_input(tmp_path)
    out = tmp_path / "out"
    first = run_private_scenario_analysis(input_path=input_path, output_root=out)
    altered = _normalized_price_record()
    altered["records"][0]["price"] = "26.59"
    input2 = tmp_path / "private-prices-2.json"
    input2.write_text(json.dumps(altered, sort_keys=True), encoding="utf-8")
    input2.chmod(0o600)
    second = run_private_scenario_analysis(input_path=input2, output_root=out)
    assert first["analysis_id"] != second["analysis_id"]
    assert Path(first["run_dir"]).is_dir()
    assert Path(second["run_dir"]).is_dir()
    assert len(list(out.glob("patha-scenario-*"))) == 2


def test_analysis_cutoff_and_observation_time_are_revalidated(tmp_path):
    normalized = _normalized_price_record()
    normalized["analysis_cutoff_date"] = "2026-10-09"
    input_path = _write_input(tmp_path, normalized=normalized)
    with pytest.raises(PrivateScenarioAnalysisError, match="PRICE_KNOWN_AT_NOT_BEFORE_CUTOFF_START"):
        run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")


def test_private_output_root_with_open_permissions_is_not_mutated(tmp_path):
    input_path = _write_input(tmp_path)
    out = tmp_path / "open-root"
    out.mkdir(mode=0o755)
    out.chmod(0o755)
    with pytest.raises(PrivateScenarioAnalysisError, match="OUTPUT_ROOT_PERMISSIONS_TOO_OPEN"):
        run_private_scenario_analysis(input_path=input_path, output_root=out)
    assert stat.S_IMODE(out.stat().st_mode) == 0o755


def test_private_receipt_binds_exact_input_and_output_hashes(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")
    bundle = Path(result["run_dir"])
    receipt = json.loads((bundle / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["input_sha256"] != ""
    assert receipt["analysis_file_sha256"] == result["analysis_file_sha256"]
    assert receipt["report_file_sha256"] == result["report_file_sha256"]
    assert receipt["integrity_scope"] == "EXACT_PRIVATE_FILE_BYTES_ONLY_NOT_EXTERNAL_SOURCE_AUTHENTICATION"


def test_unknown_top_level_scope_flag_or_wrong_schema_blocks(tmp_path):
    normalized = _normalized_price_record()
    normalized["scope_controls"]["may_feed_canonical_current_price_resolver"] = True
    input_path = _write_input(tmp_path, normalized=normalized)
    with pytest.raises(PrivateScenarioAnalysisError, match="FORBIDDEN_SCOPE_FLAG_NOT_FALSE"):
        run_private_scenario_analysis(input_path=input_path, output_root=tmp_path / "out")
