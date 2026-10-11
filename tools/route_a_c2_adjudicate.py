from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile
from typing import Any

# Direct script execution sets sys.path[0] to tools/. Add the repository root
# explicitly so the canonical Core/B2 validator imports work from any cwd.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from jsonschema import Draft202012Validator
from pypdf import PdfReader
from referencing import Registry, Resource

from research.b2.company_evidence import (
    REQUIRED_COMPANY_FIELD_GROUPS,
    build_company_evidence_manifest,
)
from research.b2.evidence_contract import assert_pit, validate_evidence_record
from tools.verify_company_evidence_intake import IndependentVerificationError, verify_intake


CASE_ID = "RC-CN-A-002001-20261009"
CUTOFF_INSTANT = "2026-10-09T00:00:00+08:00"
EXPECTED_ARCHIVE_SHA256 = "0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1"
REPORT_SCHEMA = "IIOS-ROUTE-A-C2-SUCCESSOR-ADJUDICATION-REPORT-0.1"

# The upper bound deliberately uses end-of-publication-day for already-published
# documents. Every bound is before the date-only case cutoff at 2026-10-09 00:00
# +08. These are conservative bounds, not exact first-public timestamps.
SOURCE_VINTAGE = {
    "SZSE-2026-H1-FULL": {
        "known_at": "2026-08-20T23:59:59+08:00",
        "publication_date": "2026-08-20",
    },
    "SZSE-2026-H1-SUMMARY": {
        "known_at": "2026-08-20T23:59:59+08:00",
        "publication_date": "2026-08-20",
    },
    "SZSE-2026-BUYBACK-PLAN": {
        "known_at": "2026-06-24T23:59:59+08:00",
        "publication_date": "2026-06-24",
    },
}

FACT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "XHC-FACT-SECURITY-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 2,
        "printed_page": 2,
        "field": "security_identity.issuer_security",
        "claim_type": "DIRECT_DISCLOSURE_FACT",
        "claim": "报告摘要载明发行人浙江新和成股份有限公司、股票简称新和成、股票代码002001、上市交易所为深圳证券交易所。",
        "value": {"issuer": "浙江新和成股份有限公司", "symbol": "002001", "exchange": "深圳证券交易所"},
        "terms": ["股票简称新和成股票代码002001", "股票上市交易所深圳证券交易所"],
        "observation_date": None,
        "period": None,
        "section": "二、公司基本情况 / 1、公司简介",
    },
    {
        "id": "XHC-FACT-CORPORATE-H1-DISCLOSURE-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 1,
        "printed_page": 1,
        "field": "corporate_disclosures.h1_report_summary",
        "claim_type": "DIRECT_DISCLOSURE_FACT",
        "claim": "深圳证券交易所官方归档文件为新和成2026年半年度报告摘要，公告编号2026-035。",
        "value": {"document": "2026年半年度报告摘要", "announcement_no": "2026-035"},
        "terms": ["公告编号：2026-035", "2026年半年度报告摘要"],
        "observation_date": "2026-08-20",
        "period": "2026H1",
        "section": "封面 / 报告标题与公告编号",
    },
    {
        "id": "XHC-FACT-FIN-REVENUE-H1-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 2,
        "printed_page": 2,
        "field": "financial_reality.revenue_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "2026年上半年营业收入人民币13,129,300,260.89元，同比增长18.28%。",
        "value": {"amount": "13129300260.89", "currency": "CNY", "yoy_growth": "18.28%"},
        "terms": ["营业收入（元）", "13,129,300,260.89", "18.28%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "二、公司基本情况 / 2、主要会计数据和财务指标 / 营业收入",
    },
    {
        "id": "XHC-FACT-FIN-NET-PROFIT-H1-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 2,
        "printed_page": 2,
        "field": "financial_reality.net_profit_attributable_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "2026年上半年归属于上市公司股东的净利润人民币4,010,733,454.55元，同比增长11.31%。",
        "value": {"amount": "4010733454.55", "currency": "CNY", "yoy_growth": "11.31%"},
        "terms": ["归属于上市公司股东的净利润（元）", "4,010,733,454.55", "11.31%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "二、公司基本情况 / 2、主要会计数据和财务指标 / 归母净利润",
    },
    {
        "id": "XHC-FACT-FIN-ADJ-PROFIT-H1-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 2,
        "printed_page": 2,
        "field": "financial_reality.adjusted_net_profit_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "2026年上半年扣非归母净利润人民币3,918,936,563.72元，同比增长6.53%。",
        "value": {"amount": "3918936563.72", "currency": "CNY", "yoy_growth": "6.53%"},
        "terms": ["归属于上市公司股东的扣除非经常性损益的净利润（元）", "3,918,936,563.72", "6.53%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "二、公司基本情况 / 2、主要会计数据和财务指标 / 扣非归母净利润",
    },
    {
        "id": "XHC-FACT-FIN-OCF-H1-001",
        "source": "SZSE-2026-H1-SUMMARY",
        "page": 2,
        "printed_page": 2,
        "field": "financial_reality.operating_cash_flow_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "2026年上半年经营活动产生的现金流量净额人民币3,640,144,282.94元，同比增长12.26%。",
        "value": {"amount": "3640144282.94", "currency": "CNY", "yoy_growth": "12.26%"},
        "terms": ["经营活动产生的现金流量净额（元）", "3,640,144,282.94", "12.26%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "二、公司基本情况 / 2、主要会计数据和财务指标 / 经营活动现金流量净额",
    },
    {
        "id": "XHC-FACT-BUSINESS-METHIONINE-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 9,
        "printed_page": 8,
        "field": "business_reality.methionine_price_volume_h1",
        "claim_type": "MANAGEMENT_DISCUSSION_FACT",
        "claim": "管理层报告称营养品板块主要产品蛋氨酸需求和价格显著上涨，蛋氨酸业务实现量价齐升。",
        "value": {"management_assessment": "蛋氨酸市场需求和价格显著上涨；蛋氨酸业务量价齐升"},
        "terms": ["公司营养品板块主要产品蛋氨酸市场需求和价格显著上涨", "公司蛋氨酸业务实现量价齐升"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "第三节 管理层讨论与分析 / 三、主营业务分析 / 概述",
    },
    {
        "id": "XHC-FACT-BUSINESS-PROJECTS-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 9,
        "printed_page": 8,
        "field": "business_reality.capacity_expansion_projects_h1",
        "claim_type": "MANAGEMENT_DISCUSSION_FACT",
        "claim": "管理层报告称天津新材料尼龙产业链项目设备陆续到货安装，PPS四期项目落地建设，HA二期土建顺利开工。",
        "value": {"projects": ["天津新材料尼龙产业链项目", "PPS四期项目", "HA二期"]},
        "terms": ["天津新材料尼龙产业链项目土建装置基本完成交安", "PPS四期项目落地建设", "HA二期土建顺利开工"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "第三节 管理层讨论与分析 / 三、主营业务分析 / 项目建设有序推进",
    },
    {
        "id": "XHC-FACT-FIN-RD-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 10,
        "printed_page": 9,
        "field": "financial_reality.rd_expense_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "2026年上半年研发投入人民币605,728,077.64元，同比增长15.88%。",
        "value": {"amount": "605728077.64", "currency": "CNY", "yoy_growth": "15.88%"},
        "terms": ["研发投入", "605,728,077.64", "15.88%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "第三节 管理层讨论与分析 / 主要财务数据同比变动情况 / 研发投入",
    },
    {
        "id": "XHC-FACT-FIN-SEGMENTS-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 11,
        "printed_page": 10,
        "field": "financial_reality.product_segment_revenue_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "上半年营养品、香精香料、新材料分产品收入分别为人民币8,805,591,681.68元、2,022,263,282.57元和1,165,989,510.74元。",
        "value": {
            "nutritional_cny": "8805591681.68",
            "flavors_fragrances_cny": "2022263282.57",
            "new_materials_cny": "1165989510.74",
            "yoy_growth": {"nutritional": "22.30%", "flavors_fragrances": "-3.91%", "new_materials": "12.31%"},
        },
        "terms": ["8,805,591,681.68", "2,022,263,282.57", "1,165,989,510.74", "22.30%", "-3.91%", "12.31%"],
        "observation_date": "2026-06-30",
        "period": "2026H1",
        "section": "第三节 管理层讨论与分析 / 营业收入构成 / 分产品",
    },
    {
        "id": "XHC-FACT-CAPITAL-ASSETS-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 12,
        "printed_page": 11,
        "field": "capital_structure.assets_cash_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "截至2026年6月30日，货币资金人民币7,458,042,805.72元、固定资产人民币19,538,428,936.53元、在建工程人民币1,006,512,957.55元。",
        "value": {
            "cash_cny": "7458042805.72",
            "fixed_assets_cny": "19538428936.53",
            "construction_in_progress_cny": "1006512957.55",
        },
        "terms": ["货币资金", "7,458,042,805.72", "固定资产", "19,538,428,936.53", "在建工程", "1,006,512,957.55"],
        "observation_date": "2026-06-30",
        "period": "2026-06-30",
        "section": "第三节 管理层讨论与分析 / 五、资产及负债状况分析 / 资产构成",
    },
    {
        "id": "XHC-FACT-CAPITAL-DEBT-H1-001",
        "source": "SZSE-2026-H1-FULL",
        "page": 12,
        "printed_page": 11,
        "field": "capital_structure.interest_bearing_debt_h1",
        "claim_type": "FINANCIAL_STATEMENT_FACT",
        "claim": "截至2026年6月30日，短期借款人民币962,032,277.99元、长期借款人民币3,170,163,350.48元、一年内到期非流动负债人民币2,745,428,550.04元。",
        "value": {
            "short_term_borrowings_cny": "962032277.99",
            "long_term_borrowings_cny": "3170163350.48",
            "current_portion_noncurrent_liabilities_cny": "2745428550.04",
        },
        "terms": ["短期借款", "962,032,277.99", "长期借款", "3,170,163,350.48", "一年内到期的非流动负债", "2,745,428,550.04"],
        "observation_date": "2026-06-30",
        "period": "2026-06-30",
        "section": "第三节 管理层讨论与分析 / 五、资产及负债状况分析 / 资产构成",
    },
    {
        "id": "XHC-FACT-TRUST-BUYBACK-PLAN-001",
        "source": "SZSE-2026-BUYBACK-PLAN",
        "page": 1,
        "printed_page": 1,
        "field": "trust_governance_events.issuer_buyback_plan",
        "claim_type": "CORPORATE_GOVERNANCE_FACT",
        "claim": "公司2026年6月公告拟以自有资金回购股份，用于股权激励计划或员工持股计划，回购金额区间为人民币3亿至6亿元，回购价格不超过人民币45.50元/股。",
        "value": {
            "repurchase_min_cny": "300000000",
            "repurchase_max_cny": "600000000",
            "price_cap_cny_per_share": "45.50",
            "purpose": "股权激励计划或员工持股计划",
        },
        "terms": ["公告编号：2026-027", "30,000万元-60,000万元", "45.50元/股", "股权激励计划或员工持股计划"],
        "observation_date": "2026-06-24",
        "period": None,
        "section": "关于回购公司股份方案的公告 / 重要内容提示",
    },
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("C2_JSON_INPUT_NOT_OBJECT")
    return value


def _safe_extract_pinned_archive(archive: Path, destination: Path) -> None:
    actual_sha = sha256_file(archive)
    if actual_sha != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("C2_ARCHIVE_SHA256_MISMATCH")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        names = [info.filename for info in zf.infolist()]
        if len(names) != len(set(names)):
            raise ValueError("C2_ARCHIVE_DUPLICATE_MEMBER")
        for info in zf.infolist():
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError("C2_ARCHIVE_UNSAFE_MEMBER")
            # The archive digest is pinned before extraction; still reject links.
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("C2_ARCHIVE_SYMLINK_MEMBER")
        zf.extractall(destination)


def _normalize_legacy_payload_defaults(
    receipt: dict[str, Any],
    intake_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Create an in-memory compatibility projection for Run #8's pre-field receipt."""
    source_specs = {
        item.get("source_id"): item
        for item in intake_manifest.get("sources", [])
        if isinstance(item, dict)
    }
    rows = receipt.get("sources")
    if not isinstance(rows, list) or len(rows) != len(source_specs):
        raise ValueError("C2_LEGACY_RECEIPT_SOURCE_SET_MISMATCH")
    normalized = json.loads(json.dumps(receipt))
    for row in normalized["sources"]:
        if not isinstance(row, dict):
            raise ValueError("C2_LEGACY_RECEIPT_ROW_INVALID")
        spec = source_specs.get(row.get("source_id"))
        if spec is None:
            raise ValueError("C2_LEGACY_RECEIPT_SOURCE_SPEC_MISSING")
        expected = str(spec.get("expected_payload_type") or "ANY").strip().upper()
        if expected != "ANY":
            raise ValueError("C2_LEGACY_PAYLOAD_TYPE_NOT_DEFAULT_ANY")
        # Only add defaults when the old manifest/receipt omitted the later,
        # optional payload-contract fields. Never erase a recorded non-default.
        old_expected = row.get("expected_payload_type")
        old_status = row.get("payload_contract_status")
        old_error = row.get("payload_contract_error")
        if old_expected not in (None, "", "ANY"):
            raise ValueError("C2_LEGACY_PAYLOAD_TYPE_NOT_DEFAULT_ANY")
        if old_status not in (None, "", "NOT_CHECKED"):
            raise ValueError("C2_LEGACY_PAYLOAD_STATUS_NOT_DEFAULT")
        if old_error not in (None, ""):
            raise ValueError("C2_LEGACY_PAYLOAD_ERROR_PRESENT")
        row["expected_payload_type"] = "ANY"
        row["payload_contract_status"] = "NOT_CHECKED"
        row["payload_contract_error"] = None
    return normalized


def _verify_intake_with_legacy_defaults(
    root: Path,
    receipt: dict[str, Any],
    intake_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Verify the original first; support only missing optional defaults in a temp copy."""
    try:
        result = verify_intake(root)
        result["raw_receipt_verification_method"] = "CURRENT_RECEIPT_CONTRACT"
        return result
    except IndependentVerificationError as exc:
        if str(exc) != "EXPECTED_PAYLOAD_TYPE_BINDING_MISMATCH":
            raise

    normalized_receipt = _normalize_legacy_payload_defaults(receipt, intake_manifest)
    with tempfile.TemporaryDirectory(prefix="iios-c2-legacy-receipt-view-") as temporary:
        view_root = Path(temporary) / "run8"
        shutil.copytree(root, view_root)
        (view_root / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json").write_text(
            json.dumps(normalized_receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        # intake_manifest.json remains byte-identical, so its pinned manifest hash
        # and every source_spec_sha256 contract continue to be checked unchanged.
        result = verify_intake(view_root)
    result["raw_receipt_verification_method"] = (
        "LEGACY_OPTIONAL_PAYLOAD_DEFAULTS_NORMALIZED_IN_TEMPORARY_COPY"
    )
    return result


def _verify_receipt_and_raw(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    receipt = _load_json(root / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json")
    intake_manifest = _load_json(root / "intake_manifest.json")
    if receipt.get("case_id") != CASE_ID or intake_manifest.get("case_id") != CASE_ID:
        raise ValueError("C2_CASE_ID_MISMATCH")
    if receipt.get("cutoff_date") != "2026-10-09" or intake_manifest.get("cutoff_date") != "2026-10-09":
        raise ValueError("C2_CUTOFF_DATE_MISMATCH")
    if receipt.get("status") != "PARTIAL_CAPTURE_NOT_ADMITTED":
        raise ValueError("C2_EXPECTED_PARTIAL_CAPTURE_RECEIPT")
    rows = receipt.get("sources")
    if not isinstance(rows, list) or len(rows) != 9:
        raise ValueError("C2_SOURCE_RECEIPT_SET_MISMATCH")
    by_id = {str(row.get("source_id")): row for row in rows}
    integrity = _verify_intake_with_legacy_defaults(root, receipt, intake_manifest)
    if integrity.get("status") != "INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION":
        raise ValueError("C2_RAW_INTEGRITY_NOT_PASS")
    if integrity.get("raw_bytes_verified") != 8:
        raise ValueError("C2_EXPECTED_EIGHT_CAPTURED_RAW_OBJECTS")
    return receipt, by_id, integrity


def _load_and_verify_pdf(
    *,
    root: Path,
    source_id: str,
    receipt_row: dict[str, Any],
    page_cache: dict[str, list[str]],
) -> tuple[Path, list[str]]:
    if receipt_row.get("capture_status") != "SUCCESS":
        raise ValueError(f"C2_SOURCE_CAPTURE_NOT_SUCCESS:{source_id}")
    relative = receipt_row.get("raw_artifact_path")
    if not isinstance(relative, str) or not relative.startswith("raw/"):
        raise ValueError(f"C2_RAW_PATH_INVALID:{source_id}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise ValueError(f"C2_RAW_PATH_MISSING_OR_ESCAPED:{source_id}")
    if path.stat().st_size != receipt_row.get("size_bytes"):
        raise ValueError(f"C2_RAW_SIZE_MISMATCH:{source_id}")
    if sha256_file(path) != receipt_row.get("sha256"):
        raise ValueError(f"C2_RAW_SHA256_MISMATCH:{source_id}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"C2_SOURCE_NOT_PDF:{source_id}")
    if source_id not in page_cache:
        page_cache[source_id] = [compact(p.extract_text() or "") for p in PdfReader(str(path)).pages]
    return path, page_cache[source_id]




def _append_operator_market_price_attestation(
    *,
    root: Path,
    bundle_dir: Path,
    evidence: list[dict[str, Any]],
    raw_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind an explicit operator attestation to this exact C2 case without network retrieval."""
    bundle_root = Path(bundle_dir).resolve()
    payload_path = bundle_root / "raw" / "operator_market_price_attestation.json"
    evidence_path = bundle_root / "evidence_record.json"
    declaration_path = bundle_root / "raw_artifact_declaration.json"
    if not payload_path.is_file() or not evidence_path.is_file() or not declaration_path.is_file():
        raise ValueError("C2_OPERATOR_PRICE_BUNDLE_INCOMPLETE")
    raw_bytes = payload_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
        record = _load_json(evidence_path)
        declaration = _load_json(declaration_path)
    except (UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as exc:
        raise ValueError("C2_OPERATOR_PRICE_BUNDLE_INVALID_JSON") from exc
    if not isinstance(payload, dict) or not isinstance(record, dict) or not isinstance(declaration, dict):
        raise ValueError("C2_OPERATOR_PRICE_BUNDLE_INVALID_SHAPE")
    expected = {
        "case_id": CASE_ID,
        "market": "CN-A",
        "symbol": "002001",
        "company": "浙江新和成股份有限公司",
        "cutoff_date": CUTOFF_INSTANT,
        "observation_date": "2026-10-08",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"C2_OPERATOR_PRICE_BINDING_MISMATCH:{key}")
    if payload.get("record_class") != "OPERATOR_ATTESTED_MARKET_PRICE_NOT_SOURCE_BYTE_VERIFIED":
        raise ValueError("C2_OPERATOR_PRICE_RECORD_CLASS_INVALID")
    if payload.get("operator_confirmed") is not True or payload.get("secondary_web_audit_performed") is not False:
        raise ValueError("C2_OPERATOR_PRICE_CONFIRMATION_INVALID")
    if payload.get("original_vendor_bytes_received") is not False:
        raise ValueError("C2_OPERATOR_PRICE_VENDOR_BYTES_MUST_NOT_BE_CLAIMED")
    if declaration.get("expected_sha256") != digest or declaration.get("expected_size_bytes") != len(raw_bytes):
        raise ValueError("C2_OPERATOR_PRICE_BUNDLE_RAW_HASH_MISMATCH")
    if record.get("content_sha256") != digest or record.get("capture_sha256") != digest:
        raise ValueError("C2_OPERATOR_PRICE_EVIDENCE_HASH_MISMATCH")
    if declaration.get("evidence_id") != record.get("evidence_id"):
        raise ValueError("C2_OPERATOR_PRICE_EVIDENCE_ID_MISMATCH")
    attestation = record.get("operator_attestation")
    if not isinstance(attestation, dict):
        raise ValueError("C2_OPERATOR_PRICE_ATTESTATION_METADATA_MISSING")
    for key in (
        "policy_id", "operator_confirmed", "secondary_web_audit_performed",
        "case_id", "market", "symbol", "company", "observation_date",
        "close_price", "currency", "source_ref", "known_at", "known_at_basis",
        "attested_at", "original_vendor_bytes_received",
    ):
        if attestation.get(key) != payload.get(key):
            raise ValueError(f"C2_OPERATOR_PRICE_METADATA_MISMATCH:{key}")
    if record.get("subject_id") != CASE_ID or record.get("field_id") != "market_price.close_price":
        raise ValueError("C2_OPERATOR_PRICE_EVIDENCE_BINDING_MISMATCH")
    if record.get("provenance_class") != "OPERATOR_ATTESTED_MARKET_DATA" or record.get("status") != "ADMITTED":
        raise ValueError("C2_OPERATOR_PRICE_PROVENANCE_INVALID")
    try:
        assert_pit(record, CUTOFF_INSTANT)
    except ValueError as exc:
        raise ValueError("C2_OPERATOR_PRICE_PIT_INVALID:" + str(exc)) from exc

    relative_path = "operator_attestations/operator_market_price_attestation.json"
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise ValueError("C2_OPERATOR_PRICE_TARGET_ALREADY_EXISTS")
    target.write_bytes(raw_bytes)
    if target.stat().st_size != len(raw_bytes) or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise ValueError("C2_OPERATOR_PRICE_PRIVATE_COPY_INTEGRITY_FAILURE")

    bound_record = dict(record)
    bound_record["artifact_id"] = relative_path
    bound_record["source_locator"] = "private operator-attestation JSON / close_price"
    errors = validate_evidence_record(bound_record)
    if errors:
        raise ValueError("C2_OPERATOR_PRICE_EVIDENCE_RECORD_INVALID:" + ";".join(errors))
    evidence.append(bound_record)
    raw_artifacts.append({
        "evidence_id": bound_record["evidence_id"],
        "relative_path": relative_path,
        "expected_size_bytes": len(raw_bytes),
        "expected_sha256": digest,
    })
    return bound_record


def build_successor_manifest(root: Path, *, archive_verification_method: str, operator_market_price_attestation_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt, by_id, integrity = _verify_receipt_and_raw(root)
    page_cache: dict[str, list[str]] = {}
    evidence: list[dict[str, Any]] = []
    raw_artifacts: list[dict[str, Any]] = []
    locator_results: list[dict[str, Any]] = []
    verified_sources: dict[str, dict[str, Any]] = {}

    for spec in FACT_SPECS:
        source_id = spec["source"]
        row = by_id.get(source_id)
        if row is None:
            raise ValueError(f"C2_SOURCE_ID_NOT_IN_RECEIPT:{source_id}")
        path, pages = _load_and_verify_pdf(root=root, source_id=source_id, receipt_row=row, page_cache=page_cache)
        page = int(spec["page"])
        if page < 1 or page > len(pages):
            raise ValueError(f"C2_PDF_PAGE_OUT_OF_RANGE:{spec['id']}")
        page_text = pages[page - 1]
        missing_terms = [term for term in spec["terms"] if compact(term) not in page_text]
        if missing_terms:
            raise ValueError(f"C2_PAGE_LOCATOR_MISMATCH:{spec['id']}:{','.join(missing_terms)}")

        vintage = SOURCE_VINTAGE[source_id]
        known_at = vintage["known_at"]
        retrieved_at = row.get("retrieved_at")
        if not isinstance(retrieved_at, str) or not retrieved_at:
            raise ValueError(f"C2_RETRIEVED_AT_MISSING:{source_id}")
        if retrieved_at.endswith("Z"):
            retrieved_at = retrieved_at[:-1] + "+00:00"

        source_url = row.get("source_url")
        if not isinstance(source_url, str) or not source_url.startswith("https://disc.static.szse.cn/"):
            raise ValueError(f"C2_NON_OFFICIAL_SOURCE_URL:{source_id}")
        verified_sources[source_id] = {
            "source_id": source_id,
            "relative_path": row["raw_artifact_path"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
            "publication_date": vintage["publication_date"],
            "known_at_upper_bound": known_at,
            "exact_first_public_timestamp_verified": False,
        }
        locator = (
            f"raw_path={row['raw_artifact_path']};pdf_page_1based={page};"
            f"printed_page={spec['printed_page']};section={spec['section']};"
            f"text_terms={json.dumps(spec['terms'], ensure_ascii=False, separators=(',', ':'))}"
        )
        quality_notes = [
            "SOURCE_VINTAGE_BOUNDED_BY_OFFICIAL_SZSE_PUBLICATION_DATE_UPPER_BOUND",
            "EXACT_FIRST_PUBLIC_TIMESTAMP_VERIFIED=FALSE",
            "KNOWN_AT_IS_CONSERVATIVE_END_OF_PUBLICATION_DAY_BOUND_NOT_EXACT_INTRADAY_TIME",
            "PRIVATE_INTERNAL_FACT_LEVEL_USE_ONLY_NO_RAW_PDF_OR_BULK_REDISTRIBUTION",
            "NO_UNRESTRICTED_REUSE_OR_LEGAL_LICENSE_OPINION_CLAIMED",
        ]
        item: dict[str, Any] = {
            "evidence_id": spec["id"],
            "subject_id": CASE_ID,
            "field_id": spec["field"],
            "claim_type": spec["claim_type"],
            "value": spec["value"],
            "observation_date": spec["observation_date"],
            "period": spec["period"],
            "published_at": vintage["publication_date"],
            "known_at": known_at,
            "retrieved_at": retrieved_at,
            "effective_from": None,
            "effective_to": None,
            "source_ref": source_url,
            "source_version": f"SZSE archive publication date {vintage['publication_date']}",
            "source_locator": locator,
            "artifact_id": row["raw_artifact_path"],
            "content_sha256": row["sha256"],
            "capture_sha256": row["sha256"],
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
            "parents": [],
            "quality_notes": quality_notes,
            "license_status": "KNOWN_RESTRICTED",
        }
        evidence.append(item)
        raw_artifacts.append({
            "evidence_id": spec["id"],
            "relative_path": row["raw_artifact_path"],
            "expected_size_bytes": row["size_bytes"],
            "expected_sha256": row["sha256"],
        })
        locator_results.append({
            "evidence_id": spec["id"],
            "source_id": source_id,
            "page": page,
            "page_terms_match": True,
            "exact_raw_bytes_verified": True,
            "known_at_upper_bound": known_at,
        })

    operator_price_record = None
    if operator_market_price_attestation_dir is not None:
        operator_price_record = _append_operator_market_price_attestation(
            root=root,
            bundle_dir=operator_market_price_attestation_dir,
            evidence=evidence,
            raw_artifacts=raw_artifacts,
        )

    manifest = build_company_evidence_manifest(
        case_id=CASE_ID,
        market="CN-A",
        symbol="002001",
        company="浙江新和成股份有限公司",
        cutoff_date=CUTOFF_INSTANT,
        evidence=evidence,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=root,
    )

    repo_root = Path(__file__).resolve().parents[1]
    manifest_schema = _load_json(repo_root / "schemas" / "company_evidence_manifest_v0.1.schema.json")
    evidence_schema = _load_json(repo_root / "schemas" / "evidence_record_v0.1.schema.json")
    registry = Registry().with_resource(evidence_schema["$id"], Resource.from_contents(evidence_schema))
    validator = Draft202012Validator(manifest_schema, registry=registry)
    validator.check_schema(manifest_schema)
    validator.validate(manifest)

    errors = manifest.get("validation_errors", [])
    missing_groups: list[str] = []
    for error in errors:
        if error.startswith("REQUIRED_FIELD_GROUPS_UNCOVERED:"):
            missing_groups = error.split(":", 1)[1].split(",")
            break
    if operator_price_record is None:
        expected_admitted = sorted(set(REQUIRED_COMPANY_FIELD_GROUPS) - {"market_price"})
        if manifest.get("status") != "BLOCKED" or missing_groups != ["market_price"]:
            raise ValueError("C2_UNEXPECTED_CORE_RESULT")
        if "market_price" in [x["field_id"].split(".", 1)[0] for x in evidence]:
            raise ValueError("C2_MARKET_PRICE_MUST_NOT_BE_SYNTHESIZED")
    else:
        expected_admitted = sorted(REQUIRED_COMPANY_FIELD_GROUPS)
        if manifest.get("status") != "PASS" or missing_groups:
            raise ValueError("C2_OPERATOR_ATTESTED_PRICE_CORE_RESULT_NOT_PASS")
        if len([x for x in evidence if x.get("provenance_class") == "OPERATOR_ATTESTED_MARKET_DATA"]) != 1:
            raise ValueError("C2_OPERATOR_PRICE_MULTIPLICITY_INVALID")
    if any(x["id"] == "XHC-FACT-TRUST-BUYBACK-PROGRESS-001" for x in FACT_SPECS):
        raise ValueError("C2_CUTOFF_EXCLUDED_SAME_DAY_BUYBACK_NOTICE")

    report = {
        "schema_version": REPORT_SCHEMA,
        "record_class": "C2_SUCCESSOR_CORE_VALIDATION_REPORT_NOT_FORMAL_SIGNED_ADMISSION",
        "case_id": CASE_ID,
        "cutoff_date": CUTOFF_INSTANT,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "archive_sha256_verification_method": archive_verification_method,
        "archive_raw_integrity_status": integrity["status"],
        "raw_receipt_verification_method": integrity.get("raw_receipt_verification_method", "UNSPECIFIED"),
        "captured_raw_object_count_verified": integrity["raw_bytes_verified"],
        "fact_locator_count": len(locator_results),
        "official_pdf_source_count": len(verified_sources),
        "verified_fact_ids": [x["evidence_id"] for x in locator_results],
        "verified_source_ids": sorted(verified_sources),
        "source_vintage": {
            "status": "CONSERVATIVE_PUBLICATION_DATE_UPPER_BOUNDS",
            "exact_first_public_timestamp_verified": False,
            "supporting_resolution_bytes_in_original_capture": False,
        },
        "use_boundary": {
            "status": "PRIVATE_INTERNAL_FACT_LEVEL_ONLY",
            "raw_pdf_or_bulk_redistribution": False,
            "unrestricted_reuse_claimed": False,
        },
        "b2_manifest_status": manifest["status"],
        "b2_manifest_sha256": manifest["audit"]["manifest_sha256"],
        "candidate_fact_count": len(evidence),
        "admitted_field_groups": expected_admitted,
        "missing_required_field_groups": missing_groups,
        "b2_validation_errors": errors,
        "market_price": (
            {
                "status": "OPERATOR_ATTESTED_CORE_PIT_PASS_NOT_SOURCE_VERIFIED",
                "required_observation_date": "2026-10-08",
                "evidence_id": operator_price_record["evidence_id"],
                "known_at": operator_price_record["known_at"],
                "secondary_web_audit_performed": False,
                "original_vendor_bytes_received": False,
                "numeric_price_in_report": False,
                "source_verified_by_system": False,
            }
            if operator_price_record is not None
            else {
                "status": "BLOCKED_UNKNOWN",
                "required_observation_date": "2026-10-08",
                "reason": "No operator-attested price bundle was supplied; no secondary-web lookup is required by this path.",
                "fake_or_inferred_record_created": False,
            }
        ),
        "excluded_sources": [
            {"source_id": "SZSE-2026-BUYBACK-PROGRESS-SEP", "reason": "Same-day 2026-10-09 publication is after the start-of-day cutoff."},
            {"source_id": "ISSUER-IR-PAGE-CURRENT", "reason": "Dynamic page has no historical publication time."},
            {"source_id": "PRICE-SOHU-HISTORY", "reason": "No admitted date-specific known_at or reuse disposition."},
            {"source_id": "PRICE-EASTMONEY-QUOTE", "reason": "No admitted date-specific known_at or reuse disposition."},
            {"source_id": "PRICE-EASTMONEY-KLINE-API", "reason": "Capture failed; no bytes and no hash."},
        ],
        "formal_signed_admission_created": False,
        "production_host_accepted": False,
        "decision_created": False,
        "publication_created": False,
        "run_receipt_created": False,
        "execution_authorized": False,
        "independent_review": "PENDING",
    }
    return manifest, report


def run(
    archive_dir: Path,
    out_dir: Path,
    *,
    artifact_digest_verified_by_downloader: bool = False,
    operator_market_price_attestation_dir: Path | None = None,
) -> dict[str, Any]:
    candidates = sorted(archive_dir.glob("route-a-xinhecheng-run8.zip"))
    has_extracted_receipt = (archive_dir / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json").is_file()
    has_extracted_manifest = (archive_dir / "intake_manifest.json").is_file()
    out_dir.mkdir(parents=True, exist_ok=True)

    if len(candidates) == 1 and not (has_extracted_receipt or has_extracted_manifest):
        with tempfile.TemporaryDirectory(prefix="iios-c2-run8-") as temporary:
            raw_root = Path(temporary) / "run8"
            _safe_extract_pinned_archive(candidates[0], raw_root)
            manifest, report = build_successor_manifest(
                raw_root,
                archive_verification_method="INDEPENDENT_REHASHED_PINNED_ZIP_BEFORE_EXTRACTION",
                operator_market_price_attestation_dir=operator_market_price_attestation_dir,
            )
    elif (
        not candidates
        and has_extracted_receipt
        and has_extracted_manifest
        and artifact_digest_verified_by_downloader
    ):
        # actions/download-artifact verifies the original archived payload SHA-256
        # before extracting it. Its exact digest check is visible in the workflow
        # log; this branch then independently replays every receipt-bound raw file.
        manifest, report = build_successor_manifest(
            archive_dir,
            archive_verification_method="ACTIONS_DOWNLOAD_ARTIFACT_PINNED_SHA256_VERIFIED_BEFORE_EXTRACTION",
            operator_market_price_attestation_dir=operator_market_price_attestation_dir,
        )
    else:
        raise ValueError("C2_CAPTURE_ARCHIVE_NOT_FOUND_OR_AMBIGUOUS_OR_UNVERIFIED_LAYOUT")

    # The candidate manifest contains financial facts and stays ephemeral/private.
    # The workflow is configured to upload only the sanitized status report.
    (out_dir / "B2_COMPANY_EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "C2_SOURCE_ADJUDICATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and Core-validate the cutoff-safe C2 successor from the pinned Run #8 capture.")
    parser.add_argument("--archive-dir", required=True, help="Directory containing route-a-xinhecheng-run8.zip")
    parser.add_argument("--out-dir", required=True, help="Temporary output directory; do not commit B2 manifest")
    parser.add_argument(
        "--artifact-digest-verified-by-download-action",
        action="store_true",
        help="Assert the flattened directory was produced by actions/download-artifact after its pinned SHA-256 verification",
    )
    parser.add_argument(
        "--operator-market-price-attestation-dir",
        default=None,
        help="Private local bundle created by tools/iios_operator_market_price_attestation_v01.py; do not upload its value-bearing files to public GitHub",
    )
    args = parser.parse_args()
    try:
        report = run(
            Path(args.archive_dir),
            Path(args.out_dir),
            artifact_digest_verified_by_downloader=args.artifact_digest_verified_by_download_action,
            operator_market_price_attestation_dir=(
                Path(args.operator_market_price_attestation_dir)
                if args.operator_market_price_attestation_dir
                else None
            ),
        )
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({
            "status": "C2_SOURCE_ADJUDICATION_FAILED_CLOSED",
            "error_code": code,
            "formal_signed_admission_created": False,
            "decision_created": False,
        }, sort_keys=True))
        return 1
    print(json.dumps({
        "status": report["b2_manifest_status"],
        "case_id": report["case_id"],
        "cutoff_date": report["cutoff_date"],
        "archive_raw_integrity_status": report["archive_raw_integrity_status"],
        "captured_raw_object_count_verified": report["captured_raw_object_count_verified"],
        "candidate_fact_count": report["candidate_fact_count"],
        "admitted_field_groups": report["admitted_field_groups"],
        "missing_required_field_groups": report["missing_required_field_groups"],
        "b2_manifest_sha256": report["b2_manifest_sha256"],
        "formal_signed_admission_created": report["formal_signed_admission_created"],
        "decision_created": report["decision_created"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
