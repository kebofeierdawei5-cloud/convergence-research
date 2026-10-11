from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
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



def _batch2_q8(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP), "f")


def _batch2_pct4(value: Decimal) -> str:
    return format((value * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), "f")


def test_batch2_independent_fixed_profile_math_matches_machine_json(tmp_path):
    # Independent constants intentionally do not read _SCENARIO_PROFILES:
    # the test must be able to catch a changed or internally self-consistent
    # but unintended profile as well as arithmetic defects.
    fixed_profiles = {
        "002001": {
            "price": Decimal("26.58"),
            "scenarios": {
                "bear": (Decimal("2.10"), Decimal("9.5"), Decimal("0.30")),
                "base": (Decimal("2.80"), Decimal("11.5"), Decimal("0.50")),
                "bull": (Decimal("3.50"), Decimal("13.0"), Decimal("0.20")),
            },
        },
        "605016": {
            "price": Decimal("20.28"),
            "scenarios": {
                "bear": (Decimal("0.80"), Decimal("17"), Decimal("0.25")),
                "base": (Decimal("1.10"), Decimal("22"), Decimal("0.50")),
                "bull": (Decimal("1.30"), Decimal("25"), Decimal("0.25")),
            },
        },
    }
    target = Decimal("0.15")
    max_bear_loss = Decimal("0.25")
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(
        input_path=input_path,
        output_root=tmp_path / "batch2-math-audit",
    )
    machine = json.loads((Path(result["run_dir"]) / "analysis.json").read_text(encoding="utf-8"))
    companies = {row["case"]["symbol"]: row for row in machine["company_analyses"]}
    assert set(companies) == set(fixed_profiles)

    for symbol, fixed in fixed_profiles.items():
        company = companies[symbol]
        profile = company["scenario_profile"]
        returns = company["return_and_entry_evaluation"]
        assert Decimal(company["case"]["current_price_cny"]) == fixed["price"]
        assert profile["probabilities_calibrated"] is False
        assert int(profile["horizon_years"]) == 1
        assert Decimal(profile["target_annualized_return_pct"]) == Decimal("15.0000")
        assert Decimal(profile["maximum_bear_loss_pct"]) == Decimal("25.0000")

        expected_wealth = Decimal("0")
        bear_wealth = Decimal("0")
        assert set(profile["scenarios"]) == {"bear", "base", "bull"}
        for name, (eps, multiple, probability) in fixed["scenarios"].items():
            actual = profile["scenarios"][name]
            assert Decimal(actual["eps_cny"]) == eps
            assert Decimal(actual["multiple"]) == multiple
            assert Decimal(actual["probability"]) == probability
            assert Decimal(actual["cash_distributions_per_share_cny"]) == 0
            scenario_value = eps * multiple
            assert Decimal(actual["value_per_share_cny"]) == scenario_value
            terminal_wealth = scenario_value
            expected_wealth += probability * terminal_wealth
            if name == "bear":
                bear_wealth = terminal_wealth

        assert sum((row[2] for row in fixed["scenarios"].values()), Decimal("0")) == Decimal("1")
        expected_total_return = expected_wealth / fixed["price"] - Decimal("1")
        # This profile set is H=1Y, so the annualized return must equal total return.
        expected_annualized_return = expected_total_return
        hurdle_ceiling = expected_wealth / ((Decimal("1") + target) ** 1)
        bear_ceiling = bear_wealth / (Decimal("1") - max_bear_loss)
        binding_ceiling = min(hurdle_ceiling, bear_ceiling)
        headroom = binding_ceiling - fixed["price"]
        bear_return = bear_wealth / fixed["price"] - Decimal("1")

        assert returns["expected_terminal_wealth_per_share_cny"] == _batch2_q8(expected_wealth)
        assert returns["expected_total_return_pct"] == _batch2_pct4(expected_total_return)
        assert returns["expected_annualized_return_pct"] == _batch2_pct4(expected_annualized_return)
        assert returns["return_hurdle_entry_price_ceiling_cny"] == _batch2_q8(hurdle_ceiling)
        assert returns["bear_terminal_wealth_per_share_cny"] == _batch2_q8(bear_wealth)
        assert returns["bear_return_at_current_price_pct"] == _batch2_pct4(bear_return)
        assert returns["entry_price_ceiling_from_max_bear_loss_cny"] == _batch2_q8(bear_ceiling)
        assert returns["binding_conditional_entry_price_ceiling_cny"] == _batch2_q8(binding_ceiling)
        assert returns["headroom_to_binding_ceiling_cny"] == _batch2_q8(headroom)
        assert returns["conditional_price_screen"] == (
            "PRICE_AT_OR_BELOW_CONDITIONAL_ENTRY_CEILING"
            if fixed["price"] <= binding_ceiling
            else "PRICE_ABOVE_CONDITIONAL_ENTRY_CEILING"
        )


def test_batch2_rendered_report_matches_machine_json_and_retains_caveats(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(
        input_path=input_path,
        output_root=tmp_path / "batch2-report-audit",
    )
    bundle = Path(result["run_dir"])
    machine = json.loads((bundle / "analysis.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")

    for company in machine["company_analyses"]:
        case = company["case"]
        profile = company["scenario_profile"]
        returns = company["return_and_entry_evaluation"]
        assert f"## {case['company']}（{case['symbol']}.{case['exchange']}）" in report
        assert f"人工输入价格：**¥{case['current_price_cny']}** / 股" in report
        assert f"假设版本：`{profile['profile_id']}`" in report
        assert f"假设性质：{profile['assumption_class']}" in report
        assert "概率是否校准：否" in report
        assert f"| 概率加权终值（含本模型现金分配假设） | ¥{returns['expected_terminal_wealth_per_share_cny']} |" in report
        assert f"| 预期总回报 | {returns['expected_total_return_pct']}% |" in report
        assert f"| 预期年化回报（H={profile['horizon_years']}Y） | {returns['expected_annualized_return_pct']}% |" in report
        assert f"| 满足 15% 年化门槛的入场价上限 | ¥{returns['return_hurdle_entry_price_ceiling_cny']} |" in report
        assert f"| Bear 损失上限约束下的价格上限 | ¥{returns['entry_price_ceiling_from_max_bear_loss_cny']} |" in report
        assert f"**两项约束共同决定的条件性入场价上限** | **¥{returns['binding_conditional_entry_price_ceiling_cny']}**" in report
        assert f"`{returns['conditional_price_screen']}`" in report

    for caveat in (
        "不是市场一致预期",
        "不是 IIOS BUY/ADD/NO-BUY/Decision",
        "不创建正式投资 Decision",
        "不是新 Case PIT",
    ):
        assert caveat in report
    assert machine["governance"]["formal_decision_created"] is False
    assert machine["governance"]["execution_authorized"] is False


def test_batch2_independently_recomputes_receipt_file_hashes(tmp_path):
    input_path = _write_input(tmp_path)
    result = run_private_scenario_analysis(
        input_path=input_path,
        output_root=tmp_path / "batch2-hash-audit",
    )
    bundle = Path(result["run_dir"])
    receipt = json.loads((bundle / "receipt.json").read_text(encoding="utf-8"))
    input_bytes = (bundle / "input.json").read_bytes()
    analysis_bytes = (bundle / "analysis.json").read_bytes()
    report_bytes = (bundle / "report.md").read_bytes()
    machine = json.loads(analysis_bytes.decode("utf-8"))

    assert receipt["input_sha256"] == hashlib.sha256(input_bytes).hexdigest()
    assert receipt["analysis_file_sha256"] == hashlib.sha256(analysis_bytes).hexdigest()
    assert receipt["report_file_sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert machine["input_sha256"] == hashlib.sha256(input_bytes).hexdigest()

    # Independently reconstitute the exact canonical analysis body whose digest
    # is embedded inside analysis.json, omitting only that digest field.
    body = {key: value for key, value in machine.items() if key != "analysis_content_sha256"}
    canonical_body = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert machine["analysis_content_sha256"] == hashlib.sha256(canonical_body).hexdigest()
    assert receipt["integrity_scope"] == "EXACT_PRIVATE_FILE_BYTES_ONLY_NOT_EXTERNAL_SOURCE_AUTHENTICATION"
    assert receipt["source_origin_verified"] is False
    assert receipt["source_use_rights_verified"] is False
    assert receipt["formal_decision_created"] is False
    assert receipt["execution_authorized"] is False
