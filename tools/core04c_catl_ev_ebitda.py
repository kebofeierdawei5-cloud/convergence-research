from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import subprocess
import unicodedata
from xml.etree import ElementTree as ET

import fitz


_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
_CELL_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_NUM_RE = re.compile(r"-?[0-9][0-9,]*(?:\.[0-9]+)?")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _column_number(ref: str) -> int:
    letters = _CELL_RE.match(ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - ord("A") + 1
    return n


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        raw = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    result = []
    for item in root.findall("main:si", _NS):
        result.append("".join(item.itertext()))
    return result


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    v = cell.find("main:v", _NS)
    if kind == "s" and v is not None:
        return shared[int(v.text)]
    if kind == "inlineStr":
        return "".join(cell.itertext())
    return v.text if v is not None else "".join(cell.itertext())


def parse_szse_market_snapshot(
    path: Path,
    *,
    expected_date: str,
    symbol: str = "300750",
) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        sheet = archive.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(sheet)

    header: dict[str, int] | None = None
    rows: list[dict[int, str]] = []
    for row in root.findall(".//main:row", _NS):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", _NS):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            values[_column_number(ref)] = _cell_value(cell, shared)
        rows.append(values)
        if "证券代码" in values.values() and "今收" in values.values():
            header = {value.strip(): col for col, value in values.items()}

    if header is None:
        raise ValueError(f"{path.name}: SZSE market header not found")

    required = ("交易日期", "证券代码", "证券简称", "今收", "涨跌幅（%）")
    missing = [name for name in required if name not in header]
    if missing:
        raise ValueError(f"{path.name}: missing SZSE headers: {missing}")

    for values in rows:
        row_date = values.get(header["交易日期"])
        row_symbol = values.get(header["证券代码"])
        if row_symbol == symbol and row_date == expected_date:
            return {
                "observation_date": row_date,
                "symbol": row_symbol,
                "company": values.get(header["证券简称"], ""),
                "close_cny": values[header["今收"]],
                "close_change_pct": values.get(header["涨跌幅（%）"], ""),
            }

    raise ValueError(f"{path.name}: {symbol} on {expected_date} not found")


def _report_text(path: Path, pages_1based: tuple[int, ...] | None = None) -> str:
    try:
        rendered = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        doc = fitz.open(path)
        rendered = "\n".join(page.get_text("text") for page in doc)

    # pdftotext gives more stable Chinese table text on these CNINFO PDFs.
    rendered = unicodedata.normalize("NFKC", rendered)
    rendered = re.sub(r"(?<=[\u4e00-\u9fff])\\s+(?=[\u4e00-\u9fff])", "", rendered)

    if not pages_1based:
        return rendered

    doc = fitz.open(path)
    page_numbers = pages_1based
    parts = []
    for page_no in page_numbers:
        if not 1 <= page_no <= doc.page_count:
            raise ValueError(f"{path.name}: page {page_no} outside 1..{doc.page_count}")
        parts.append(doc[page_no - 1].get_text("text"))
    return "\n".join(parts)


def _row_first_number(
    text: str,
    *,
    labels: tuple[str, ...],
    section_start: str | None = None,
    section_end: str | None = None,
) -> Decimal:
    if section_start:
        start = text.find(section_start)
        if start < 0:
            raise ValueError(f"section start not found: {section_start}")
        text = text[start:]
    if section_end:
        end = text.find(section_end)
        if end >= 0:
            text = text[:end]

    for label in labels:
        label_pattern = r"".join(
            re.escape(ch) + r"\s*" for ch in label
            if not ch.isspace()
        )
        match = re.search(label_pattern, text)
        if not match:
            continue

        # The first numeric cell after a statement-row label is the current
        # fiscal-period value; preserve whitespace so adjacent year columns
        # cannot concatenate.
        following = text[match.end():]
        for line in following.splitlines()[:4]:
            number = re.search(_NUM_RE.pattern, line)
            if number:
                return Decimal(number.group(0).replace(",", ""))

    raise ValueError(f"row not found for labels: {labels}")


def _statement_section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"statement section start not found: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    return text[start:end if end >= 0 else len(text)]


def _balance_sheet_section(text: str) -> str:
    start = text.find("2、合并资产负债表")
    if start < 0:
        start = text.find("合并资产负债表")
    if start < 0:
        raise ValueError("consolidated balance-sheet section not found")

    end = text.find("3、合并利润表", start + 1)
    return text[start:end if end >= 0 else len(text)]


def parse_balance_sheet(
    path: Path,
    *,
    pages_1based: tuple[int, ...],
    market_date: str,
    known_at: str,
) -> dict[str, object]:
    text = _balance_sheet_section(_report_text(path, pages_1based))
    values_k = {
        "cash": _row_first_number(text, labels=("货币资金",)),
        "short_term_debt": _row_first_number(text, labels=("短期借款",)),
        "current_portion_noncurrent": _row_first_number(
            text, labels=("一年内到期的非流动负债",)
        ),
        "long_term_debt": _row_first_number(text, labels=("长期借款",)),
        "bonds": _row_first_number(text, labels=("应付债券",)),
        "lease_liabilities": _row_first_number(text, labels=("租赁负债",)),
        "long_term_payables": _row_first_number(text, labels=("长期应付款",)),
        "share_capital_k": _row_first_number(text, labels=("股本",)),
    }
    debt_k = (
        values_k["short_term_debt"]
        + values_k["current_portion_noncurrent"]
        + values_k["long_term_debt"]
        + values_k["bonds"]
        + values_k["lease_liabilities"]
        + values_k["long_term_payables"]
    )
    net_debt_k = debt_k - values_k["cash"]
    shares = values_k["share_capital_k"] * Decimal("1000")
    return {
        "observation_date": market_date,
        "known_at": known_at,
        "share_count": shares,
        "cash_cny": values_k["cash"] * Decimal("1000"),
        "interest_bearing_debt_cny": debt_k * Decimal("1000"),
        "net_debt_cny": net_debt_k * Decimal("1000"),
        "debt_components_cny": {
            key: val * Decimal("1000")
            for key, val in values_k.items()
            if key in {
                "short_term_debt",
                "current_portion_noncurrent",
                "long_term_debt",
                "bonds",
                "lease_liabilities",
                "long_term_payables",
            }
        },
    }


def parse_exact_h1_share_capital(path: Path) -> Decimal:
    text = _report_text(path, (3,))
    match = re.search(r"现有总股本\s*([0-9][0-9,]+)\s*股", text)
    if not match:
        raise ValueError("H1 exact total share capital not found")
    return Decimal(match.group(1).replace(",", ""))


def parse_annual_ebitda(
    path: Path,
    *,
    pages_income: tuple[int, ...],
    pages_cashflow: tuple[int, ...],
    fiscal_year: int,
    known_at: str,
) -> dict[str, object]:
    full_text = _report_text(path, None)
    income = _statement_section(full_text, "3、合并利润表", "5、合并现金流量表")
    cashflow = _statement_section(full_text, "5、合并现金流量表", "7、合并所有者权益变动表")
    profit_total = _row_first_number(income, labels=("四、利润总额",))
    interest_expense = _row_first_number(income, labels=("利息费用",))
    fixed_dep = _row_first_number(
        cashflow, labels=("固定资产折旧", "固定资产折旧、油气资产折耗、生产性生物资产折旧")
    )
    rou_dep = _row_first_number(cashflow, labels=("使用权资产折旧",))
    intangible = _row_first_number(cashflow, labels=("无形资产摊销",))
    long_deferred = _row_first_number(cashflow, labels=("长期待摊费用摊销",))
    ebitda_k = profit_total + interest_expense + fixed_dep + rou_dep + intangible + long_deferred
    return {
        "fiscal_year": fiscal_year,
        "known_at": known_at,
        "profit_total_cny": profit_total * Decimal("1000"),
        "interest_expense_cny": interest_expense * Decimal("1000"),
        "fixed_depreciation_cny": fixed_dep * Decimal("1000"),
        "right_of_use_depreciation_cny": rou_dep * Decimal("1000"),
        "intangible_amortization_cny": intangible * Decimal("1000"),
        "long_deferred_amortization_cny": long_deferred * Decimal("1000"),
        "ebitda_cny": ebitda_k * Decimal("1000"),
        "formula": "profit_total + interest_expense + fixed_asset_depreciation + right_of_use_depreciation + intangible_amortization + long_deferred_amortization",
    }


def money(value: Decimal) -> str:
    return format(value, "f")


def build_observation(
    *,
    observation_id: str,
    market_path: Path,
    market_data: dict[str, str],
    market_known_at: str,
    financial_path: Path,
    financial_data: dict[str, object],
    financial_known_at: str,
    ebitda_path: Path,
    ebitda_data: dict[str, object],
    ebitda_known_at: str,
    source_hashes: dict[str, str],
    market_prior_hash: str | None,
) -> dict[str, object]:
    market_date = market_data["observation_date"]
    if Decimal(market_data["close_cny"]) <= 0:
        raise ValueError("market close must be positive")
    close = Decimal(market_data["close_cny"])
    shares = Decimal(financial_data["share_count"])
    net_debt = Decimal(financial_data["net_debt_cny"])
    ebitda = Decimal(ebitda_data["ebitda_cny"])
    if financial_known_at > market_date + "T23:59:59+08:00":
        raise ValueError(f"financial evidence known_at after market date: {financial_known_at}")
    if ebitda_known_at > market_date + "T23:59:59+08:00":
        raise ValueError(f"EBITDA evidence known_at after market date: {ebitda_known_at}")
    market_cap = close * shares
    enterprise_value = market_cap + net_debt
    multiple = enterprise_value / ebitda
    return {
        "observation_id": observation_id,
        "observation_date": market_date,
        "known_at": max(market_known_at, financial_known_at, ebitda_known_at),
        "market_price_cny_per_share": money(close),
        "shares_outstanding": money(shares),
        "net_debt_cny": money(net_debt),
        "ebitda_cny": money(ebitda),
        "market_cap_cny": money(market_cap),
        "enterprise_value_cny": money(enterprise_value),
        "ev_ebitda": money(multiple),
        "basis": "historical_market_date / latest_known_financial_vintage / latest_known_completed_fiscal_year_EBITDA",
        "source_hashes": source_hashes,
        "market_source_row": {
            "symbol": market_data["symbol"],
            "company": market_data["company"],
            "close_cny": market_data["close_cny"],
        },
        "prior_market_capture_hash": market_prior_hash,
        "prior_market_capture_status": (
            "BYTES_DIFFER_FROM_PRIOR_CAPTURE"
            if market_prior_hash and market_prior_hash != source_hashes[market_path.name]
            else "NO_PRIOR_HASH"
        ),
        "admission_status": "ADMITTED",
        "economic_variable": "ebitda",
        "economic_unit": "CNY",
        "economic_basis": f"FY{ebitda_data['fiscal_year']} completed fiscal-year EBITDA",
        "net_debt_basis": "interest_bearing_debt_less_cash",
        "share_count_basis": "reported_total_share_capital",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    raw = Path(args.raw)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    config = [
        {
            "market_date": "2025-10-22",
            "market": "SZSE-MKT-2025-10-22.xlsx",
            "financial": "CNINFO-Q3-2025.pdf",
            "financial_pages": (),
            "financial_known_at": "2025-10-21T23:59:59+08:00",
            "ebitda": "CNINFO-FY2024-2025-03-15.pdf",
            "ebitda_income_pages": (),
            "ebitda_cashflow_pages": (),
            "ebitda_year": 2024,
            "ebitda_known_at": "2025-03-15T23:59:59+08:00",
        },
        {
            "market_date": "2026-04-17",
            "market": "SZSE-MKT-2026-04-17.xlsx",
            "financial": "CNINFO-Q1-2026.pdf",
            "financial_pages": (),
            "financial_known_at": "2026-04-16T23:59:59+08:00",
            "ebitda": "CNINFO-FY2025-2026-03-10.pdf",
            "ebitda_income_pages": (),
            "ebitda_cashflow_pages": (),
            "ebitda_year": 2025,
            "ebitda_known_at": "2026-03-10T23:59:59+08:00",
        },
        {
            "market_date": "2026-07-27",
            "market": "SZSE-MKT-2026-07-27.xlsx",
            "financial": "CNINFO-H1-2026.pdf",
            "financial_pages": (),
            "financial_known_at": "2026-07-24T23:59:59+08:00",
            "ebitda": "CNINFO-FY2025-2026-03-10.pdf",
            "ebitda_income_pages": (116,),
            "ebitda_cashflow_pages": (200,),
            "ebitda_year": 2025,
            "ebitda_known_at": "2026-03-10T23:59:59+08:00",
        },
    ]

    prior = {
        "SZSE-MKT-2025-10-22.xlsx": "dfe49f5fade60087e5118f17446bbf55161c4cd7d765dd81155edb10ccdd6ba9",
        "SZSE-MKT-2026-04-17.xlsx": "bd5875b4294e3acdcca6aeddf42dd65d8284a15e5a29d6290308c65973b49a0d",
        "SZSE-MKT-2026-07-27.xlsx": "ab420679237525a7e6846ffa49a3ef8115e4d64d6bc97f63319f5ee9c333e568",
    }

    all_hashes = {p.name: sha256(p) for p in raw.glob("*") if p.is_file() and p.suffix in {".xlsx", ".pdf"}}
    observations = []

    for item in config:
        market_path = raw / item["market"]
        financial_path = raw / item["financial"]
        ebitda_path = raw / item["ebitda"]
        market_data = parse_szse_market_snapshot(
            market_path, expected_date=item["market_date"]
        )
        fin = parse_balance_sheet(
            financial_path,
            pages_1based=item["financial_pages"],
            market_date=item["market_date"],
            known_at=item["financial_known_at"],
        )
        if item["market_date"] == "2026-07-27":
            fin["share_count"] = parse_exact_h1_share_capital(financial_path)
        ebitda = parse_annual_ebitda(
            ebitda_path,
            pages_income=item["ebitda_income_pages"],
            pages_cashflow=item["ebitda_cashflow_pages"],
            fiscal_year=item["ebitda_year"],
            known_at=item["ebitda_known_at"],
        )
        observations.append(
            build_observation(
                observation_id=f"CATL-EVEBITDA-{item['market_date']}",
                market_path=market_path,
                market_data=market_data,
                market_known_at=item["market_date"] + "T23:59:59+08:00",
                financial_path=financial_path,
                financial_data=fin,
                financial_known_at=item["financial_known_at"],
                ebitda_path=ebitda_path,
                ebitda_data=ebitda,
                ebitda_known_at=item["ebitda_known_at"],
                source_hashes={
                    market_path.name: all_hashes[market_path.name],
                    financial_path.name: all_hashes[financial_path.name],
                    ebitda_path.name: all_hashes[ebitda_path.name],
                },
                market_prior_hash=prior.get(market_path.name),
            )
        )

    output = {
        "schema_version": "IIOS-CORE04C-CATL-EVEBITDA-0.1",
        "case_id": "RC-CN-A-300750-20261004",
        "status": "PASS / HISTORICAL OBSERVATIONS ADMITTED",
        "observations": observations,
        "pit_rule": "All financial and EBITDA vintages known_at <= observation market date; market price is observed on the market date.",
        "ev_formula": "market_price * reported_total_share_capital + (interest_bearing_debt - cash)",
        "ev_ebitda_formula": "enterprise_value / latest_known_completed_fiscal_year_EBITDA",
    }
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=money) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
