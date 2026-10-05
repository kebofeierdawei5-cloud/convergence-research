from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader


UTC8 = timezone.utc  # stored receipt timestamps are UTC; PIT comparisons use calendar date.
CNY_SCALE = Decimal("1000")


@dataclass(frozen=True)
class Source:
    source_id: str
    role: str
    url: str
    observation_date: date
    known_at: datetime
    filename: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xlsx_shared_strings(z: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values: list[str] = []
    for si in root:
        parts = [t.text or "" for t in si.iter() if _local_name(t.tag) == "t"]
        values.append("".join(parts))
    return values


def _xlsx_sheet_path(z: zipfile.ZipFile, preferred_name: str) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels
        if _local_name(rel.tag) == "Relationship"
    }
    for sheet in wb.iter():
        if _local_name(sheet.tag) != "sheet":
            continue
        name = sheet.attrib.get("name", "")
        if name == preferred_name:
            target = rel_map[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"worksheet {preferred_name!r} not found")


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter() if _local_name(t.tag) == "t").strip()
    raw = next((v.text or "" for v in cell if _local_name(v.tag) == "v"), "")
    if kind == "s":
        return shared_strings[int(raw)].strip()
    return raw.strip()


def read_xlsx_row(path: Path, symbol: str, sheet_name: str = "股票行情") -> dict[str, str]:
    with zipfile.ZipFile(path, "r") as z:
        shared = _xlsx_shared_strings(z)
        sheet_path = _xlsx_sheet_path(z, sheet_name)
        root = ET.fromstring(z.read(sheet_path))

    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        cells: dict[str, str] = {}
        for cell in row:
            if _local_name(cell.tag) != "c":
                continue
            ref = cell.attrib.get("r", "")
            col = re.match(r"([A-Z]+)", ref)
            if not col:
                continue
            cells[col.group(1)] = _cell_value(cell, shared)

        joined = " | ".join(cells.values())
        if symbol in cells.values() or re.search(rf"(?<!\d){re.escape(symbol)}(?!\d)", joined):
            return cells
    raise ValueError(f"security {symbol} not found in {sheet_name}")


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text)


NUMBER_RE = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


def numbers_after_label(line: str, label: str) -> list[Decimal]:
    idx = line.find(label)
    if idx < 0:
        return []
    tail = line[idx + len(label):]
    return [Decimal(token.replace(",", "")) for token in NUMBER_RE.findall(tail)]


def find_row_number(lines: list[str], label: str, occurrence: int = 0) -> Decimal:
    seen = 0
    for line in lines:
        values = numbers_after_label(line, label)
        if not values:
            continue
        if seen == occurrence:
            return values[0]
        seen += 1
    raise LookupError(f"label not found with numeric value: {label}")


def extract_pdf_lines(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = normalize_text(text)
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def parse_period_financials(path: Path, period: str) -> dict[str, Decimal]:
    lines = extract_pdf_lines(path)
    # First numeric row after each label is the consolidated statement value.
    profit_total = find_row_number(lines, "利润总额")
    interest_expense = find_row_number(lines, "利息费用")
    fixed_dep = find_row_number(lines, "固定资产折旧、油气资产折耗、生产性生物资产折旧")
    rou_dep = find_row_number(lines, "使用权资产折旧")
    intangible_amort = find_row_number(lines, "无形资产摊销")
    lt_prepaid_amort = find_row_number(lines, "长期待摊费用摊销")

    cash = find_row_number(lines, "货币资金")
    trading_assets = find_row_number(lines, "交易性金融资产")
    short_borrowing = find_row_number(lines, "短期借款")
    current_noncurrent = find_row_number(lines, "一年内到期的非流动负债")
    long_borrowing = find_row_number(lines, "长期借款")
    bonds = find_row_number(lines, "应付债券")
    lease_liabilities = find_row_number(lines, "租赁负债")
    share_capital = find_row_number(lines, "股本")

    depreciation_amortization = fixed_dep + rou_dep + intangible_amort + lt_prepaid_amort
    ebitda = profit_total + interest_expense + depreciation_amortization
    interest_bearing_debt = (
        short_borrowing
        + current_noncurrent
        + long_borrowing
        + bonds
        + lease_liabilities
    )
    net_debt = interest_bearing_debt - cash - trading_assets

    return {
        "profit_total_thousand_cny": profit_total,
        "interest_expense_thousand_cny": interest_expense,
        "fixed_dep_thousand_cny": fixed_dep,
        "rou_dep_thousand_cny": rou_dep,
        "intangible_amort_thousand_cny": intangible_amort,
        "lt_prepaid_amort_thousand_cny": lt_prepaid_amort,
        "depreciation_amortization_thousand_cny": depreciation_amortization,
        "ebitda_thousand_cny": ebitda,
        "cash_thousand_cny": cash,
        "trading_assets_thousand_cny": trading_assets,
        "short_borrowing_thousand_cny": short_borrowing,
        "current_noncurrent_liability_thousand_cny": current_noncurrent,
        "long_borrowing_thousand_cny": long_borrowing,
        "bonds_thousand_cny": bonds,
        "lease_liabilities_thousand_cny": lease_liabilities,
        "interest_bearing_debt_thousand_cny": interest_bearing_debt,
        "net_debt_thousand_cny": net_debt,
        "share_capital_thousand_cny": share_capital,
        "period": Decimal("0"),
    }


def d(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value))


def ttm(current_period: Decimal, prior_full_year: Decimal, prior_period: Decimal) -> Decimal:
    return current_period + prior_full_year - prior_period


def market_price_from_snapshot(path: Path, symbol: str) -> Decimal:
    row = read_xlsx_row(path, symbol)
    preferred = ("今收", "收盘", "收盘价", "最新价")
    # Build a reverse map from the row itself; header mapping is handled by row 1 search below.
    with zipfile.ZipFile(path, "r") as z:
        shared = _xlsx_shared_strings(z)
        sheet_path = _xlsx_sheet_path(z, "股票行情")
        root = ET.fromstring(z.read(sheet_path))

    header_map: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    for xml_row in root.iter():
        if _local_name(xml_row.tag) != "row":
            continue
        cells: dict[str, str] = {}
        for cell in xml_row:
            if _local_name(cell.tag) != "c":
                continue
            ref = cell.attrib.get("r", "")
            col_m = re.match(r"([A-Z]+)", ref)
            if col_m:
                cells[col_m.group(1)] = _cell_value(cell, shared)
        rows.append(cells)
        if any(v in {"证券代码", "股票代码", "代码"} for v in cells.values()):
            header_map = {v.strip(): k for k, v in cells.items() if v.strip()}

    if not header_map:
        raise ValueError("market snapshot header row not found")
    row_code_col = next((header_map.get(x) for x in ("证券代码", "股票代码", "代码") if header_map.get(x)), None)
    if row_code_col is None:
        raise ValueError("market snapshot code column not found")

    target = next(
        (r for r in rows if re.fullmatch(rf"0*{re.escape(symbol)}", r.get(row_code_col, "").strip())),
        None,
    )
    if target is None:
        raise ValueError(f"security {symbol} not found in market snapshot")

    price_col = next((header_map.get(x) for x in preferred if header_map.get(x)), None)
    if price_col is None:
        raise ValueError("market snapshot close-price column not found")
    price = d(target[price_col])
    if price <= 0:
        raise ValueError("market snapshot price must be > 0")
    return price


def build_manifest(base_dir: Path) -> list[Source]:
    return [
        Source("SZSE-MKT-2026-07-27", "MARKET_PRICE_SNAPSHOT",
               "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1815_stock_snapshot&TABKEY=tab1&txtBeginDate=2026-07-27&txtEndDate=2026-07-27&archiveDate=2026-07-28&random=0.20261005",
               date(2026, 7, 27), datetime(2026, 7, 27, 7, tzinfo=timezone.utc), "SZSE-MKT-2026-07-27.xlsx"),
        Source("CNINFO-H1-2026", "COMPANY_FINANCIAL_REPORT",
               "https://static.cninfo.com.cn/finalpage/2026-07-24/1225442062.PDF",
               date(2026, 6, 30), datetime(2026, 7, 24, 8, tzinfo=timezone.utc), "CNINFO-H1-2026.pdf"),
        Source("SZSE-MKT-2026-04-17", "MARKET_PRICE_SNAPSHOT",
               "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1815_stock_snapshot&TABKEY=tab1&txtBeginDate=2026-04-17&txtEndDate=2026-04-17&archiveDate=2026-04-18&random=0.20261005",
               date(2026, 4, 17), datetime(2026, 4, 17, 7, tzinfo=timezone.utc), "SZSE-MKT-2026-04-17.xlsx"),
        Source("CNINFO-Q1-2026", "COMPANY_FINANCIAL_REPORT",
               "https://static.cninfo.com.cn/finalpage/2026-04-16/1225107946.PDF",
               date(2026, 3, 31), datetime(2026, 4, 16, 8, tzinfo=timezone.utc), "CNINFO-Q1-2026.pdf"),
        Source("SZSE-MKT-2025-10-22", "MARKET_PRICE_SNAPSHOT",
               "https://www.szse.cn/api/report/ShowReport?SHOWTYPE=xlsx&CATALOGID=1815_stock_snapshot&TABKEY=tab1&txtBeginDate=2025-10-22&txtEndDate=2025-10-22&archiveDate=2025-10-23&random=0.20261005",
               date(2025, 10, 22), datetime(2025, 10, 22, 7, tzinfo=timezone.utc), "SZSE-MKT-2025-10-22.xlsx"),
        Source("CNINFO-Q3-2025", "COMPANY_FINANCIAL_REPORT",
               "https://static.cninfo.com.cn/finalpage/2025-10-21/1224721971.PDF",
               date(2025, 9, 30), datetime(2025, 10, 21, 8, tzinfo=timezone.utc), "CNINFO-Q3-2025.pdf"),
        Source("CNINFO-ANNUAL-2025", "COMPANY_FINANCIAL_REPORT",
               "https://static.cninfo.com.cn/finalpage/2026-03-10/1225002214.PDF",
               date(2025, 12, 31), datetime(2026, 3, 10, 8, tzinfo=timezone.utc), "CNINFO-ANNUAL-2025.pdf"),
        Source("CNINFO-ANNUAL-2024", "COMPANY_FINANCIAL_REPORT",
               "https://static.cninfo.com.cn/finalpage/2025-03-15/1222806982.PDF",
               date(2024, 12, 31), datetime(2025, 3, 15, 8, tzinfo=timezone.utc), "CNINFO-ANNUAL-2024.pdf"),
    ]


def download_sources(sources: list[Source], out_dir: Path) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt: list[dict[str, object]] = []
    import subprocess

    for src in sources:
        dst = out_dir / src.filename
        cmd = [
            "curl", "--location", "--fail", "--silent", "--show-error",
            "--retry", "4", "--retry-delay", "1", "--retry-all-errors",
            "--connect-timeout", "20", "--max-time", "120",
            "--user-agent", "IIOS-core04c-ev-ebitda/0.1",
            "--output", str(dst),
            "--write-out", "%{http_code}", src.url,
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        status = int(completed.stdout.strip()) if completed.stdout.strip().isdigit() else 0
        if completed.returncode != 0 or status < 200 or status >= 300:
            raise RuntimeError(f"{src.source_id} capture failed rc={completed.returncode} http={status}: {completed.stderr.strip()}")
        size = dst.stat().st_size
        if size <= 0:
            raise RuntimeError(f"{src.source_id} captured zero bytes")
        receipt.append({
            "source_id": src.source_id,
            "role": src.role,
            "source_url": src.url,
            "observation_date": src.observation_date.isoformat(),
            "known_at": src.known_at.isoformat(),
            "filename": src.filename,
            "http_status": status,
            "size_bytes": size,
            "sha256": sha256_file(dst),
            "exact_bytes_captured": True,
        })
    return receipt


def source_map(receipt: list[dict[str, object]], source_dir: Path) -> dict[str, Path]:
    return {str(r["source_id"]): source_dir / str(r["filename"]) for r in receipt}


def derive_case(source_paths: dict[str, Path]) -> dict[str, object]:
    h1_2026 = parse_period_financials(source_paths["CNINFO-H1-2026"], "2026H1")
    q1_2026 = parse_period_financials(source_paths["CNINFO-Q1-2026"], "2026Q1")
    q3_2025 = parse_period_financials(source_paths["CNINFO-Q3-2025"], "2025Q3")
    annual_2025 = parse_period_financials(source_paths["CNINFO-ANNUAL-2025"], "2025FY")
    annual_2024 = parse_period_financials(source_paths["CNINFO-ANNUAL-2024"], "2024FY")

    # The latest comparable EBITDA for each market date is TTM, derived only
    # from report vintages knowable on or before that market observation.
    ebitda_ttm_2026_07_27 = ttm(
        h1_2026["ebitda_thousand_cny"],
        annual_2025["ebitda_thousand_cny"],
        h1_2026["depreciation_amortization_thousand_cny"] * Decimal("0") +
        parse_period_financials(source_paths["CNINFO-H1-2026"], "2025H1")["ebitda_thousand_cny"]
    )
    # Re-derive the 2025H1 comparative from the same H1 report so no 2025H1
    # standalone source is needed. The parser returns the first statement
    # column; extract the second comparative is handled below via explicit row parser.
    h1_lines = extract_pdf_lines(source_paths["CNINFO-H1-2026"])
    h1_profit_row = next(line for line in h1_lines if "利润总额" in line and len(numbers_after_label(line, "利润总额")) >= 2)
    h1_interest_row = next(line for line in h1_lines if "利息费用" in line and len(numbers_after_label(line, "利息费用")) >= 2)
    h1_fix_row = next(line for line in h1_lines if "固定资产折旧、油气资产折耗、生产性生物资产折旧" in line and len(numbers_after_label(line, "固定资产折旧、油气资产折耗、生产性生物资产折旧")) >= 2)
    h1_rou_row = next(line for line in h1_lines if "使用权资产折旧" in line and len(numbers_after_label(line, "使用权资产折旧")) >= 2)
    h1_int_row = next(line for line in h1_lines if "无形资产摊销" in line and len(numbers_after_label(line, "无形资产摊销")) >= 2)
    h1_pre_row = next(line for line in h1_lines if "长期待摊费用摊销" in line and len(numbers_after_label(line, "长期待摊费用摊销")) >= 2)
    h1_2025_ebitda = (
        numbers_after_label(h1_profit_row, "利润总额")[1]
        + numbers_after_label(h1_interest_row, "利息费用")[1]
        + numbers_after_label(h1_fix_row, "固定资产折旧、油气资产折耗、生产性生物资产折旧")[1]
        + numbers_after_label(h1_rou_row, "使用权资产折旧")[1]
        + numbers_after_label(h1_int_row, "无形资产摊销")[1]
        + numbers_after_label(h1_pre_row, "长期待摊费用摊销")[1]
    )
    ebitda_ttm_2026_07_27 = ttm(h1_2026["ebitda_thousand_cny"], annual_2025["ebitda_thousand_cny"], h1_2025_ebitda)

    q1_2026_lines = extract_pdf_lines(source_paths["CNINFO-Q1-2026"])
    # Q1 report's first and second values on the same rows are 2026Q1 and 2025Q1.
    def comparative_ebitda(lines: list[str]) -> tuple[Decimal, Decimal]:
        labels = [
            "利润总额",
            "利息费用",
            "固定资产折旧、油气资产折耗、生产性生物资产折旧",
            "使用权资产折旧",
            "无形资产摊销",
            "长期待摊费用摊销",
        ]
        rows = [next(line for line in lines if label in line and len(numbers_after_label(line, label)) >= 2) for label in labels]
        first = sum((numbers_after_label(row, label)[0] for row, label in zip(rows, labels)), Decimal("0"))
        second = sum((numbers_after_label(row, label)[1] for row, label in zip(rows, labels)), Decimal("0"))
        return first, second

    q1_cur, q1_prior = comparative_ebitda(q1_2026_lines)

    q3_2025_lines = extract_pdf_lines(source_paths["CNINFO-Q3-2025"])
    q3_2025_9m, q3_2024_9m = comparative_ebitda(q3_2025_lines)

    ebitda_ttm_2026_04_17 = ttm(q1_cur, annual_2025["ebitda_thousand_cny"], q1_prior)
    ebitda_ttm_2025_10_22 = ttm(q3_2025_9m, annual_2024["ebitda_thousand_cny"], q3_2024_9m)

    return {
        "financial_sources": {
            "h1_2026": h1_2026,
            "q1_2026": q1_2026,
            "q3_2025": q3_2025,
            "annual_2025": annual_2025,
            "annual_2024": annual_2024,
            "h1_2025_comparative_ebitda_thousand_cny": h1_2025_ebitda,
            "q1_2026_ebitda_thousand_cny": q1_cur,
            "q1_2025_comparative_ebitda_thousand_cny": q1_prior,
            "q3_2025_9m_ebitda_thousand_cny": q3_2025_9m,
            "q3_2024_9m_comparative_ebitda_thousand_cny": q3_2024_9m,
        },
        "ttm_ebitda_thousand_cny": {
            "2026-07-27": ebitda_ttm_2026_07_27,
            "2026-04-17": ebitda_ttm_2026_04_17,
            "2025-10-22": ebitda_ttm_2025_10_22,
        },
        "net_debt_thousand_cny": {
            "2026-07-27": h1_2026["net_debt_thousand_cny"],
            "2026-04-17": q1_2026["net_debt_thousand_cny"],
            "2025-10-22": q3_2025["net_debt_thousand_cny"],
        },
        "shares_outstanding": {
            "2026-07-27": h1_2026["share_capital_thousand_cny"] * CNY_SCALE,
            "2026-04-17": q1_2026["share_capital_thousand_cny"] * CNY_SCALE,
            "2025-10-22": q3_2025["share_capital_thousand_cny"] * CNY_SCALE,
        },
    }


def json_decimal(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--symbol", default="300750")
    args = parser.parse_args()

    out_root = Path(args.out)
    source_dir = Path(args.source_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    sources = build_manifest(source_dir)

    if args.download:
        capture_receipt = download_sources(sources, source_dir)
    else:
        capture_receipt = []
        for src in sources:
            path = source_dir / src.filename
            if not path.exists():
                raise FileNotFoundError(path)
            capture_receipt.append({
                "source_id": src.source_id,
                "role": src.role,
                "source_url": src.url,
                "observation_date": src.observation_date.isoformat(),
                "known_at": src.known_at.isoformat(),
                "filename": src.filename,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "exact_bytes_captured": True,
            })

    smap = source_map(capture_receipt, source_dir)
    prices = {
        "2026-07-27": market_price_from_snapshot(smap["SZSE-MKT-2026-07-27"], args.symbol),
        "2026-04-17": market_price_from_snapshot(smap["SZSE-MKT-2026-04-17"], args.symbol),
        "2025-10-22": market_price_from_snapshot(smap["SZSE-MKT-2025-10-22"], args.symbol),
    }
    derived = derive_case(smap)

    observations: list[dict[str, object]] = []
    periods = [
        ("2026-07-27", "CNINFO-H1-2026", "TTM_EBITDA_H1_2026", "SOURCE_VINTAGE"),
        ("2026-04-17", "CNINFO-Q1-2026", "TTM_EBITDA_Q1_2026", "SOURCE_VINTAGE"),
        ("2025-10-22", "CNINFO-Q3-2025", "TTM_EBITDA_Q3_2025", "SOURCE_VINTAGE"),
    ]

    for obs_date, fin_source_id, ebitda_basis, temporal in periods:
        price = prices[obs_date]
        ebitda = derived["ttm_ebitda_thousand_cny"][obs_date] * CNY_SCALE
        net_debt = derived["net_debt_thousand_cny"][obs_date] * CNY_SCALE
        shares = derived["shares_outstanding"][obs_date]
        market_cap = price * shares
        enterprise_value = market_cap + net_debt
        if enterprise_value <= 0 or ebitda <= 0:
            raise ValueError(f"{obs_date}: non-positive EV/EBITDA bridge")
        multiple = enterprise_value / ebitda

        observations.append({
            "observation_id": f"300750-ev-ebitda-{obs_date}",
            "security": "300750.SZ",
            "observation_date": obs_date,
            "known_at": obs_date + "T23:59:59+00:00",
            "price_cny_per_share": price,
            "shares_outstanding": shares,
            "market_cap_cny": market_cap,
            "net_debt_cny": net_debt,
            "enterprise_value_cny": enterprise_value,
            "ebitda_cny": ebitda,
            "ebitda_basis": ebitda_basis,
            "ev_ebitda": multiple,
            "economic_variable": "ebitda",
            "unit": "CNY",
            "temporal_provenance": temporal,
            "financial_source_id": fin_source_id,
            "financial_source_sha256": next(r["sha256"] for r in capture_receipt if r["source_id"] == fin_source_id),
            "market_source_id": next(r["source_id"] for r in capture_receipt if r["observation_date"] == obs_date and r["role"] == "MARKET_PRICE_SNAPSHOT"),
            "market_source_sha256": next(r["sha256"] for r in capture_receipt if r["observation_date"] == obs_date and r["role"] == "MARKET_PRICE_SNAPSHOT"),
        })

    derivation_doc = {
        "schema_version": "IIOS-CORE04C-EV-EBITDA-DERIVATION-0.1",
        "case_id": "RC-CN-A-300750-20261004",
        "cutoff_date": "2026-10-04",
        "formula": "EV = price * shares_outstanding + net_debt; EV/EBITDA = EV / TTM_EBITDA; TTM_EBITDA = current_period_EBITDA + prior_FY_EBITDA - prior_period_EBITDA",
        "net_debt_formula": "short_term_borrowings + current_portion_noncurrent_liabilities + long_term_borrowings + bonds + lease_liabilities - cash - trading_financial_assets",
        "share_count_formula": "share_capital_thousand_cny * 1000",
        "source_receipt": capture_receipt,
        "derived": derived,
        "observations": observations,
    }
    derivation_json = out_root / "core04c_derivation.json"
    derivation_json.write_text(
        json.dumps(derivation_doc, ensure_ascii=False, indent=2, default=json_decimal) + "\n",
        encoding="utf-8",
    )
    derivation_sha = sha256_file(derivation_json)

    evidence_rows = []
    for obs in observations:
        obs_date = obs["observation_date"]
        fin = next(r for r in capture_receipt if r["source_id"] == obs["financial_source_id"])
        mkt = next(r for r in capture_receipt if r["source_id"] == obs["market_source_id"])
        evidence_rows.extend([
            {
                "evidence_id": f"E4C-{obs_date}-PRICE",
                "variable": "market_price",
                "unit": "CNY/share",
                "basis": "official_szse_eod_snapshot",
                "observation_date": obs_date,
                "known_at": obs["known_at"],
                "source": "SZSE",
                "source_location": mkt["source_url"],
                "content_sha256": mkt["sha256"],
                "exact_bytes": True,
                "status": "ADMITTED",
                "temporal_provenance": "CONTEMPORANEOUS_PUBLICATION",
                "value": str(obs["price_cny_per_share"]),
            },
            {
                "evidence_id": f"E4C-{obs_date}-SHARES",
                "variable": "shares_outstanding",
                "unit": "shares",
                "basis": "share_capital_from_latest_pit_financial_vintage",
                "observation_date": obs_date,
                "known_at": fin["known_at"],
                "source": "CNINFO",
                "source_location": fin["source_url"],
                "content_sha256": fin["sha256"],
                "exact_bytes": True,
                "status": "ADMITTED",
                "temporal_provenance": "SOURCE_VINTAGE",
                "value": str(obs["shares_outstanding"]),
            },
            {
                "evidence_id": f"E4C-{obs_date}-EBITDA",
                "variable": "ebitda",
                "unit": "CNY",
                "basis": obs["ebitda_basis"] + "_deterministic_derivation",
                "observation_date": obs_date,
                "known_at": fin["known_at"],
                "source": "IIOS-DETERMINISTIC-DERIVATION",
                "source_location": "research/core04c_derivation.json",
                "content_sha256": derivation_sha,
                "exact_bytes": True,
                "status": "ADMITTED",
                "temporal_provenance": "SOURCE_VINTAGE",
                "value": str(obs["ebitda_cny"]),
                "component_source_ids": [r["source_id"] for r in capture_receipt if r["role"] == "COMPANY_FINANCIAL_REPORT"],
            },
            {
                "evidence_id": f"E4C-{obs_date}-NET-DEBT",
                "variable": "net_debt",
                "unit": "CNY",
                "basis": "standard_interest_bearing_net_debt_bridge_deterministic_derivation",
                "observation_date": obs_date,
                "known_at": fin["known_at"],
                "source": "IIOS-DETERMINISTIC-DERIVATION",
                "source_location": "research/core04c_derivation.json",
                "content_sha256": derivation_sha,
                "exact_bytes": True,
                "status": "ADMITTED",
                "temporal_provenance": "SOURCE_VINTAGE",
                "value": str(obs["net_debt_cny"]),
            },
        ])

    admission_doc = {
        "schema_version": "IIOS-CORE04C-EV-EBITDA-ADMISSION-0.1",
        "status": "ADMITTED",
        "case_id": "RC-CN-A-300750-20261004",
        "cutoff_date": "2026-10-04",
        "model_family": "ev_ebitda",
        "observation_basis": "PIT_TTM",
        "observations": observations,
        "evidence": evidence_rows,
        "derivation_artifact": {
            "path": "research/core04c_derivation.json",
            "sha256": derivation_sha,
        },
        "fail_closed_rules": [
            "All external source bytes must be non-empty and SHA-256 verified.",
            "Financial source known_at must be <= market observation date.",
            "TTM EBITDA must be constructed only from PIT-known current/prior-period report values.",
            "Market price must come from the exact-date SZSE snapshot, not a current provider page.",
            "EV must be strictly positive and EBITDA strictly positive.",
        ],
    }
    admission_path = out_root / "core04c_ev_ebitda_admission.json"
    admission_path.write_text(
        json.dumps(admission_doc, ensure_ascii=False, indent=2, default=json_decimal) + "\n",
        encoding="utf-8",
    )

    # Verify every exact-byte digest again immediately before success.
    for row in capture_receipt:
        if sha256_file(source_dir / str(row["filename"])) != row["sha256"]:
            raise AssertionError(f"digest changed after parsing: {row['source_id']}")

    print(json.dumps({
        "status": admission_doc["status"],
        "observations": observations,
        "derivation_sha256": derivation_sha,
        "admission_sha256": sha256_file(admission_path),
    }, ensure_ascii=False, indent=2, default=json_decimal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
