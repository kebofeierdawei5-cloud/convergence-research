import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from calc.company_economic_bridge import (
    ECONOMIC_BRIDGE_VERSION,
    build_company_economic_bridge,
    validate_company_economic_bridge,
)

ROOT = Path(__file__).resolve().parents[1]


def _catl_period(
    *,
    period_id,
    period_start,
    period_end,
    evidence_ids,
    revenue,
    operating_profit,
    profit_before_tax,
    income_tax,
    net_income,
    attributable_net_income,
    operating_cash_flow,
    capex_cash,
    depreciation_ppe,
    depreciation_rou,
    amortization_intangible,
    ar,
    ar_financing,
    prepayments,
    inventory,
    contract_assets,
    notes_payable,
    accounts_payable,
    contract_liabilities,
    employee_benefits_payable,
    tax_payable,
    other_payables,
    fixed_assets,
    construction_in_progress,
    rou_assets,
    intangible_assets,
    wc_cash_inventory,
    wc_cash_receivables,
    wc_cash_payables,
):
    return locals()


CATL_H1_2025 = _catl_period(
    period_id="CATL-2025-H1",
    period_start="2025-01-01",
    period_end="2025-06-30",
    evidence_ids=["E005", "E012_A1", "E013_A1"],
    revenue=178_886_253,
    operating_profit=38_820_520,
    profit_before_tax=38_812_500,
    income_tax=6_447_053,
    net_income=32_365_447,
    attributable_net_income=30_485_139,
    operating_cash_flow=58_687_066,
    capex_cash=20_212_919,
    depreciation_ppe=11_355_579,
    depreciation_rou=105_656,
    amortization_intangible=244_874,
    ar=63_800_375,
    ar_financing=36_388_212,
    prepayments=9_752_799,
    inventory=72_272_139,
    contract_assets=346_467,
    notes_payable=76_968_647,
    accounts_payable=133_420_147,
    contract_liabilities=36_641_662,
    employee_benefits_payable=20_115_797,
    tax_payable=8_643_847,
    other_payables=11_481_854,
    fixed_assets=118_696_651,
    construction_in_progress=35_086_190,
    rou_assets=1_047_592,
    intangible_assets=14_684_829,
    wc_cash_inventory=-13_622_417,
    wc_cash_receivables=12_126_707,
    wc_cash_payables=19_114_641,
)

CATL_H1_2026 = _catl_period(
    period_id="CATL-2026-H1",
    period_start="2026-01-01",
    period_end="2026-06-30",
    evidence_ids=["E005", "E010", "E013_A1"],
    revenue=276_916_580,
    operating_profit=55_664_757,
    profit_before_tax=55_766_857,
    income_tax=8_736_218,
    net_income=47_030_638,
    attributable_net_income=43_284_002,
    operating_cash_flow=60_216_851,
    capex_cash=25_072_772,
    depreciation_ppe=14_282_273,
    depreciation_rou=276_258,
    amortization_intangible=258_901,
    ar=88_417_984,
    ar_financing=51_923_468,
    prepayments=22_793_180,
    inventory=130_819_205,
    contract_assets=338_742,
    notes_payable=152_977_931,
    accounts_payable=202_508_781,
    contract_liabilities=36_482_664,
    employee_benefits_payable=23_099_804,
    tax_payable=9_502_483,
    other_payables=9_598_945,
    fixed_assets=169_381_820,
    construction_in_progress=33_025_296,
    rou_assets=3_900_575,
    intangible_assets=15_378_514,
    wc_cash_inventory=-37_859_085,
    wc_cash_receivables=-33_026_925,
    wc_cash_payables=71_690_439,
)


ADMITTED = sorted(set(CATL_H1_2025["evidence_ids"] + CATL_H1_2026["evidence_ids"]))


def test_catl_h1_bridge_is_deterministic_and_auditable():
    result = build_company_economic_bridge(
        case_id="RC-CN-A-300750-20261004",
        cutoff_date="2026-10-04T23:59:59+08:00",
        prior_period=CATL_H1_2025,
        current_period=CATL_H1_2026,
        generation_basis="Official CATL H1 2025/H1 2026 filings; comparable six-month periods; consolidated statements.",
    admitted_evidence_ids=ADMITTED,
    )

    assert result["schema_version"] == ECONOMIC_BRIDGE_VERSION
    assert result["interpretation_status"] == "CONDITIONAL"
    assert result["investment_decision_effect"] == "NO_DIRECT_GATE_EFFECT"
    assert validate_company_economic_bridge(result) == []

    assert result["periods"]["prior"]["core_depreciation_amortization"] == pytest.approx(11_706_109)
    assert result["periods"]["current"]["core_depreciation_amortization"] == pytest.approx(14_817_432)

    assert result["periods"]["prior"]["fcf_after_capex"] == pytest.approx(38_474_147)
    assert result["periods"]["current"]["fcf_after_capex"] == pytest.approx(35_144_079)

    assert result["periods"]["prior"]["working_capital_cash_bridge"]["net_cash_contribution"] == pytest.approx(17_618_931)
    assert result["periods"]["current"]["working_capital_cash_bridge"]["net_cash_contribution"] == pytest.approx(804_429)

    assert result["periods"]["prior"]["operating_working_capital_snapshot"]["core_operating_nwc"] == pytest.approx(-104_711_962)
    assert result["periods"]["current"]["operating_working_capital_snapshot"]["core_operating_nwc"] == pytest.approx(-139_878_029)

    assert result["periods"]["prior"]["invested_capital_proxy"] == pytest.approx(64_803_300)
    assert result["periods"]["current"]["invested_capital_proxy"] == pytest.approx(81_808_176)

    assert result["deltas"]["invested_capital_proxy"] == pytest.approx(17_004_876)
    assert result["deltas"]["nopat_proxy"] == pytest.approx(14_572_398.770530317)
    assert result["incremental_roic"]["status"] == "CONDITIONAL"
    assert result["incremental_roic"]["value"] == pytest.approx(0.856954133069263)


def test_bridge_uses_consolidated_net_income_as_primary_cash_conversion_base():
    result = build_company_economic_bridge(
        case_id="CASE",
        cutoff_date="2026-10-04T23:59:59+08:00",
        prior_period=CATL_H1_2025,
        current_period=CATL_H1_2026,
        generation_basis="fixture",
    admitted_evidence_ids=ADMITTED,
    )
    assert result["periods"]["current"]["ocf_to_net_income"] == pytest.approx(60_216_851 / 47_030_638)
    assert result["periods"]["current"]["fcf_to_net_income"] == pytest.approx(35_144_079 / 47_030_638)


def test_incremental_roic_does_not_divide_by_non_positive_incremental_capital():
    prior = dict(CATL_H1_2025)
    current = dict(CATL_H1_2026)
    current["fixed_assets"] = prior["fixed_assets"]
    current["construction_in_progress"] = prior["construction_in_progress"]
    current["rou_assets"] = prior["rou_assets"]
    current["intangible_assets"] = prior["intangible_assets"]
    current["ar"] = prior["ar"]
    current["ar_financing"] = prior["ar_financing"]
    current["prepayments"] = prior["prepayments"]
    current["inventory"] = prior["inventory"]
    current["contract_assets"] = prior["contract_assets"]
    current["notes_payable"] = prior["notes_payable"]
    current["accounts_payable"] = prior["accounts_payable"]
    current["contract_liabilities"] = prior["contract_liabilities"]
    current["employee_benefits_payable"] = prior["employee_benefits_payable"]
    current["tax_payable"] = prior["tax_payable"]
    current["other_payables"] = prior["other_payables"]
    result = build_company_economic_bridge(
        case_id="CASE",
        cutoff_date="2026-10-04T23:59:59+08:00",
        prior_period=prior,
        current_period=current,
        generation_basis="fixture",
    admitted_evidence_ids=ADMITTED,
    )
    assert result["incremental_roic"]["status"] == "UNKNOWN"
    assert result["incremental_roic"]["value"] is None


def test_missing_period_field_fails_closed():
    period = dict(CATL_H1_2026)
    del period["capex_cash"]
    with pytest.raises(ValueError, match="missing required fields"):
        build_company_economic_bridge(
            case_id="CASE",
            cutoff_date="2026-10-04T23:59:59+08:00",
            prior_period=CATL_H1_2025,
            current_period=period,
            generation_basis="fixture",
        admitted_evidence_ids=ADMITTED,
        )


def test_duplicate_evidence_ids_fail_closed():
    period = dict(CATL_H1_2026)
    period["evidence_ids"] = ["E005", "E005"]
    with pytest.raises(ValueError, match="duplicate evidence IDs"):
        build_company_economic_bridge(
            case_id="CASE",
            cutoff_date="2026-10-04T23:59:59+08:00",
            prior_period=CATL_H1_2025,
            current_period=period,
            generation_basis="fixture",
        admitted_evidence_ids=ADMITTED,
        )


def test_hash_tampering_is_detected():
    result = build_company_economic_bridge(
        case_id="CASE",
        cutoff_date="2026-10-04T23:59:59+08:00",
        prior_period=CATL_H1_2025,
        current_period=CATL_H1_2026,
        generation_basis="fixture",
    admitted_evidence_ids=ADMITTED,
    )
    result["periods"]["current"]["fcf_after_capex"] += 1
    assert "AUDIT_BRIDGE_HASH_MISMATCH" in validate_company_economic_bridge(result)


def test_schema_accepts_built_bridge():
    result = build_company_economic_bridge(
        case_id="RC-CN-A-300750-20261004",
        cutoff_date="2026-10-04T23:59:59+08:00",
        prior_period=CATL_H1_2025,
        current_period=CATL_H1_2026,
        generation_basis="fixture",
    admitted_evidence_ids=ADMITTED,
    )
    schema = json.loads(
        (ROOT / "schemas" / "company_economic_bridge_v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result)
    )
    assert errors == []


def test_unadmitted_evidence_reference_fails_closed():
    current = dict(CATL_H1_2026)
    current["evidence_ids"] = current["evidence_ids"] + ["NOT-ADMITTED"]
    with pytest.raises(ValueError, match="not admitted"):
        build_company_economic_bridge(
            case_id="CASE",
            cutoff_date="2026-10-04T23:59:59+08:00",
            prior_period=CATL_H1_2025,
            current_period=current,
            generation_basis="fixture",
            admitted_evidence_ids=ADMITTED,
        )
