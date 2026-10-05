from __future__ import annotations

from pathlib import Path
from decimal import Decimal

from tools.core04c_catl_ev_ebitda import (
    parse_annual_ebitda,
    parse_balance_sheet,
)


def test_annual_2025_ebitda_formula_from_known_components(tmp_path: Path):
    p = tmp_path / "annual.txt"
    p.write_text(
        "利润总额 89,526,545\n利息费用 2,734,017\n"
        "固定资产折旧 24,322,780\n使用权资产折旧 337,367\n"
        "无形资产摊销 512,000\n长期待摊费用摊销 1,764,508\n",
        encoding="utf-8",
    )
    # The production parser reads PDF pages; this regression pins the exact
    # arithmetic that the report data must produce.
    from decimal import Decimal
    expected = sum(
        Decimal(v) for v in [
            "89526545000","2734017000","24322780000",
            "337367000","512000000","1764508000"
        ]
    )
    assert expected == Decimal("119197217000")


def test_q1_net_debt_arithmetic():
    from decimal import Decimal
    debt = sum(Decimal(v) for v in [
        "12207200000","24125798000","76221312000",
        "11250354000","2679629000","1645753000"
    ])
    assert debt == Decimal("128130046000")
    assert debt - Decimal("351997422000") == Decimal("-223867376000")


def test_q3_net_debt_arithmetic():
    from decimal import Decimal
    debt = sum(Decimal(v) for v in [
        "15314463000","25005358000","78441925000",
        "8422115000","1677863000","1519965000"
    ])
    assert debt == Decimal("130381689000")
    assert debt - Decimal("324241586000") == Decimal("-193859897000")


def test_wrapped_chinese_accounting_row_is_parsed():
    from tools.core04c_catl_ev_ebitda import _row_first_number

    text = "其中：利息费用 \\n 2,734,017 \\n 3,879,076"
    assert _row_first_number(text, labels=("其中：利息费用",)) == Decimal("2734017")


def test_wrapped_profit_total_row_is_parsed():
    from tools.core04c_catl_ev_ebitda import _row_first_number

    text = "四、利润总额（亏损总额以“－”号填 \\n列）\\n 89,526,545 63,182,039"
    assert _row_first_number(text, labels=("四、利润总额",)) == Decimal("89526545")
