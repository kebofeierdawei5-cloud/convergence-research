from __future__ import annotations

import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from tools.core04c_ev_ebitda import (
    d,
    market_price_from_snapshot,
    normalize_text,
    ttm,
)


def make_xlsx(path: Path, *, price_header: str = "今收") -> None:
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    ET.register_namespace("", ns_main)
    ET.register_namespace("r", ns_rel)

    workbook = ET.Element(f"{{{ns_main}}}workbook")
    sheets = ET.SubElement(workbook, f"{{{ns_main}}}sheets")
    ET.SubElement(
        sheets,
        f"{{{ns_main}}}sheet",
        {"name": "股票行情", f"{{{ns_rel}}}id": "rId1"},
    )

    rels = ET.Element(f"{{{ns_pkg}}}Relationships")
    ET.SubElement(rels, f"{{{ns_pkg}}}Relationship", {
        "Id": "rId1",
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
        "Target": "worksheets/sheet1.xml",
    })

    def row_xml(row_num: int, values: list[str]) -> ET.Element:
        row = ET.Element(f"{{{ns_main}}}row", {"r": str(row_num)})
        for idx, value in enumerate(values, start=1):
            col = chr(64 + idx)
            cell = ET.SubElement(row, f"{{{ns_main}}}c", {"r": f"{col}{row_num}"})
            ET.SubElement(cell, f"{{{ns_main}}}v").text = value
        return row

    worksheet = ET.Element(f"{{{ns_main}}}worksheet")
    data = ET.SubElement(worksheet, f"{{{ns_main}}}sheetData")
    data.append(row_xml(1, ["证券代码", "证券简称", price_header]))
    data.append(row_xml(2, ["300750", "宁德时代", "400.0"]))

    styles = b"""<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>"""
    content_types = b"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    root_rels = b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="/xl/workbook.xml"/>
</Relationships>"""

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
        z.writestr("xl/_rels/workbook.xml.rels", ET.tostring(rels, encoding="utf-8", xml_declaration=True))
        z.writestr("xl/worksheets/sheet1.xml", ET.tostring(worksheet, encoding="utf-8", xml_declaration=True))
        z.writestr("xl/styles.xml", styles)


def test_ttm_is_exact_decimal():
    assert ttm(Decimal("72998336"), Decimal("119197000"), Decimal("52744212")) == Decimal("139451124")


def test_decimal_parser_accepts_canonical_decimal_text():
    assert d("1394.5") == Decimal("1394.5")


def test_normalize_text_collapses_layout_whitespace():
    assert normalize_text("利润总额\u3000 55,766,857") == "利润总额 55,766,857"


def test_market_snapshot_parser_reads_symbol_and_close(tmp_path: Path):
    xlsx = tmp_path / "snapshot.xlsx"
    make_xlsx(xlsx)
    assert market_price_from_snapshot(xlsx, "300750") == Decimal("400.0")


def test_market_snapshot_parser_fails_closed_for_missing_symbol(tmp_path: Path):
    xlsx = tmp_path / "snapshot.xlsx"
    make_xlsx(xlsx)
    with pytest.raises(ValueError, match="security 300751 not found"):
        market_price_from_snapshot(xlsx, "300751")


def test_market_snapshot_parser_requires_close_column(tmp_path: Path):
    xlsx = tmp_path / "snapshot.xlsx"
    make_xlsx(xlsx, price_header="其他")
    with pytest.raises(ValueError, match="close-price column"):
        market_price_from_snapshot(xlsx, "300750")
