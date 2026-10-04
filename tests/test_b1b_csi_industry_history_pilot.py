from __future__ import annotations

import json
from pathlib import Path

from research.a02_b1b.csi_industry_history_pilot import (
    ORIGINS,
    canonical_row,
    extract_rows,
    parse_page,
)


def test_extract_rows_and_canonical_fields() -> None:
    payload = {
        "data": [
            {
                "securityCode": "300750",
                "securityName": "宁德时代",
                "cics1stCode": "10",
                "cics1stName": "工业",
                "ignored": "x",
            }
        ]
    }
    rows = extract_rows(payload)
    assert len(rows) == 1
    assert canonical_row(rows[0]) == {
        "securityCode": "300750",
        "securityName": "宁德时代",
        "cics1stCode": "10",
        "cics1stName": "工业",
    }


def test_parse_page_detects_duplicate_codes(tmp_path: Path) -> None:
    p = tmp_path / "page.json"
    p.write_text(
        json.dumps(
            {
                "data": [
                    {"securityCode": "000001", "cics1stName": "金融"},
                    {"securityCode": "000001", "cics1stName": "金融"},
                    {"securityCode": "000002", "cics1stName": "工业"},
                ],
                "size": 3,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows, stats = parse_page(p)
    assert len(rows) == 3
    assert stats["row_count"] == 3
    assert stats["security_code_count"] == 3
    assert stats["unique_security_code_count"] == 2
    assert stats["duplicate_security_codes"] == ["000001"]


def test_origin_set_is_the_frozen_a02_pit_origin_set() -> None:
    assert tuple(ORIGINS) == (
        "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
        "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1",
    )
