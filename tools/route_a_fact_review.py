from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

SCHEMA = "IIOS-ROUTE-A-FACT-EXTRACTION-REVIEW-0.1"

# PDF physical pages are 1-based. These are fact candidates, not admitted evidence.
FACT_SPECS: tuple[dict[str, Any], ...] = (
    {"id":"XHC-FACT-SECURITY-001","source":"SZSE-2026-H1-SUMMARY","page":2,"printed_page":2,"field":"security_identity.issuer_security","claim":"报告摘要载明股票简称新和成、股票代码002001、上市交易所为深圳证券交易所。","terms":["股票简称新和成股票代码002001","股票上市交易所深圳证券交易所"],"candidate_date":"2026-08-20","section":"二、公司基本情况 / 1、公司简介"},
    {"id":"XHC-FACT-FIN-REVENUE-H1-001","source":"SZSE-2026-H1-SUMMARY","page":2,"printed_page":2,"field":"financial_reality.revenue_h1","claim":"2026年上半年营业收入人民币13,129,300,260.89元，同比增长18.28%。","terms":["营业收入（元）","13,129,300,260.89","18.28%"],"candidate_date":"2026-08-20","section":"二、公司基本情况 / 2、主要会计数据和财务指标 / 营业收入"},
    {"id":"XHC-FACT-FIN-NET-PROFIT-H1-001","source":"SZSE-2026-H1-SUMMARY","page":2,"printed_page":2,"field":"financial_reality.net_profit_attributable_h1","claim":"2026年上半年归属于上市公司股东的净利润人民币4,010,733,454.55元，同比增长11.31%。","terms":["归属于上市公司股东的净利润（元）","4,010,733,454.55","11.31%"],"candidate_date":"2026-08-20","section":"二、公司基本情况 / 2、主要会计数据和财务指标 / 归母净利润"},
    {"id":"XHC-FACT-FIN-ADJ-PROFIT-H1-001","source":"SZSE-2026-H1-SUMMARY","page":2,"printed_page":2,"field":"financial_reality.adjusted_net_profit_h1","claim":"2026年上半年扣非归母净利润人民币3,918,936,563.72元，同比增长6.53%。","terms":["归属于上市公司股东的扣除非经常性损益的净利润（元）","3,918,936,563.72","6.53%"],"candidate_date":"2026-08-20","section":"二、公司基本情况 / 2、主要会计数据和财务指标 / 扣非归母净利润"},
    {"id":"XHC-FACT-FIN-OCF-H1-001","source":"SZSE-2026-H1-SUMMARY","page":2,"printed_page":2,"field":"financial_reality.operating_cash_flow_h1","claim":"2026年上半年经营活动产生的现金流量净额人民币3,640,144,282.94元，同比增长12.26%。","terms":["经营活动产生的现金流量净额（元）","3,640,144,282.94","12.26%"],"candidate_date":"2026-08-20","section":"二、公司基本情况 / 2、主要会计数据和财务指标 / 经营活动现金流量净额"},
    {"id":"XHC-FACT-BUSINESS-METHIONINE-H1-001","source":"SZSE-2026-H1-FULL","page":9,"printed_page":8,"field":"business_reality.methionine_price_volume_h1","claim":"管理层报告称营养品板块主要产品蛋氨酸需求和价格显著上涨，蛋氨酸业务实现量价齐升。","terms":["公司营养品板块主要产品蛋氨酸市场需求和价格显著上涨","公司蛋氨酸业务实现量价齐升"],"candidate_date":"2026-08-20","section":"第三节 管理层讨论与分析 / 三、主营业务分析 / 概述"},
    {"id":"XHC-FACT-BUSINESS-PROJECTS-H1-001","source":"SZSE-2026-H1-FULL","page":9,"printed_page":8,"field":"business_reality.capacity_expansion_projects_h1","claim":"管理层报告称天津新材料尼龙产业链项目设备陆续到货安装，PPS四期项目落地建设，HA二期土建顺利开工。","terms":["天津新材料尼龙产业链项目土建装置基本完成交安","PPS四期项目落地建设","HA二期土建顺利开工"],"candidate_date":"2026-08-20","section":"第三节 管理层讨论与分析 / 三、主营业务分析 / 项目建设有序推进"},
    {"id":"XHC-FACT-FIN-RD-H1-001","source":"SZSE-2026-H1-FULL","page":10,"printed_page":9,"field":"financial_reality.rd_expense_h1","claim":"2026年上半年研发投入人民币605,728,077.64元，同比增长15.88%。","terms":["研发投入","605,728,077.64","15.88%"],"candidate_date":"2026-08-20","section":"第三节 管理层讨论与分析 / 主要财务数据同比变动情况 / 研发投入"},
    {"id":"XHC-FACT-FIN-SEGMENTS-H1-001","source":"SZSE-2026-H1-FULL","page":11,"printed_page":10,"field":"financial_reality.product_segment_revenue_h1","claim":"上半年营养品收入人民币8,805,591,681.68元、同比增长22.30%；香精香料收入人民币2,022,263,282.57元、同比下降3.91%；新材料收入人民币1,165,989,510.74元、同比增长12.31%。","terms":["8,805,591,681.68","2,022,263,282.57","1,165,989,510.74","22.30%","-3.91%","12.31%"],"candidate_date":"2026-08-20","section":"第三节 管理层讨论与分析 / 营业收入构成 / 分产品"},
    {"id":"XHC-FACT-FIN-ASSETS-H1-001","source":"SZSE-2026-H1-FULL","page":12,"printed_page":11,"field":"capital_structure.balance_sheet_assets_h1","claim":"2026年6月30日固定资产人民币19,538,428,936.53元，在建工程人民币1,006,512,957.55元，货币资金人民币7,458,042,805.72元。","terms":["固定资产19,538,428,936.53","在建工程1,006,512,957.55","货币资金7,458,042,805.72"],"candidate_date":"2026-08-20","section":"第三节 管理层讨论与分析 / 五、资产及负债状况分析 / 资产构成"},
    {"id":"XHC-FACT-TRUST-BUYBACK-PROGRESS-001","source":"SZSE-2026-BUYBACK-PROGRESS-SEP","page":1,"printed_page":1,"field":"trust_governance_events.issuer_buyback_progress","claim":"公告称截至2026年9月30日回购7,136,014股、占总股本0.2322%，成交额人民币199,490,835.70元（不含交易费），最高29.97元/股、最低25.24元/股。","terms":["截至2026年9月30日","7,136,014股","0.2322%","29.97元/股","25.24元/股","199,490,835.70"],"candidate_date":"2026-10-09","section":"关于回购公司股份进展的公告 / 一、截至上月末回购股份进展情况"},
)

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)

def build_review(root: Path) -> dict[str, Any]:
    receipt = json.loads((root / "COMPANY_EVIDENCE_INTAKE_RECEIPT.json").read_text(encoding="utf-8"))
    if receipt.get("case_id") != "RC-CN-A-002001-20261009":
        raise ValueError("ROUTE_A_FACT_REVIEW_CASE_MISMATCH")
    if receipt.get("status") != "PARTIAL_CAPTURE_NOT_ADMITTED":
        raise ValueError("ROUTE_A_FACT_REVIEW_EXPECTED_PARTIAL_CAPTURE_NOT_ADMITTED")
    by_id = {str(x.get("source_id")): x for x in receipt.get("sources", [])}
    loaded: dict[str, dict[str, Any]] = {}
    page_texts: dict[str, list[str]] = {}
    for spec in FACT_SPECS:
        sid = spec["source"]
        if sid in loaded:
            continue
        row = by_id.get(sid)
        if not row or row.get("capture_status") != "SUCCESS":
            raise ValueError(f"FACT_SOURCE_CAPTURE_NOT_SUCCESS:{sid}")
        relative = row.get("raw_artifact_path")
        if not isinstance(relative, str) or not relative.startswith("raw/"):
            raise ValueError(f"FACT_SOURCE_PATH_INVALID:{sid}")
        path = (root / relative).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise ValueError(f"FACT_SOURCE_MISSING_OR_ESCAPED:{sid}")
        actual_size, actual_sha = path.stat().st_size, sha256_file(path)
        if actual_size != row.get("size_bytes") or actual_sha != row.get("sha256"):
            raise ValueError(f"FACT_SOURCE_RAW_HASH_MISMATCH:{sid}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"FACT_SOURCE_NOT_PDF:{sid}")
        pages = [compact(p.extract_text() or "") for p in PdfReader(str(path)).pages]
        loaded[sid] = {
            "path": relative, "size_bytes": actual_size, "sha256": actual_sha,
            "source_url": row.get("source_url"), "retrieved_at": row.get("retrieved_at"),
            "license_status": row.get("license_status"),
        }
        page_texts[sid] = pages
    facts = []
    for spec in FACT_SPECS:
        source = loaded[spec["source"]]
        page_number = spec["page"]
        if page_number < 1 or page_number > len(page_texts[spec["source"]]):
            raise ValueError(f"FACT_PAGE_OUT_OF_RANGE:{spec['id']}")
        page_text = page_texts[spec["source"]][page_number - 1]
        missing = [term for term in spec["terms"] if compact(term) not in page_text]
        if missing:
            raise ValueError(f"FACT_PDF_TEXT_LOCATOR_MISMATCH:{spec['id']}:{missing}")
        facts.append({
            "evidence_id": spec["id"], "subject_id": receipt["case_id"],
            "field_id": spec["field"], "claim_type": "FACT_CANDIDATE",
            "claim": spec["claim"], "known_at": None,
            "known_at_candidate": spec["candidate_date"],
            "known_at_basis": "UNKNOWN_PENDING_INDEPENDENT_SOURCE_VINTAGE_ADJUDICATION",
            "retrieved_at": source["retrieved_at"], "source_ref": source["source_url"],
            "artifact_id": source["path"], "content_sha256": source["sha256"],
            "size_bytes": source["size_bytes"], "exact_bytes": True,
            "provenance_class": "UNKNOWN", "status": "UNKNOWN",
            "admission_status": "NOT_ADMITTED", "license_status": source["license_status"],
            "source_locator": {
                "artifact_path": source["path"], "pdf_page_1based": page_number,
                "printed_page": spec["printed_page"], "section": spec["section"],
                "text_match_terms": spec["terms"],
                "match_status": "PASS_TEXT_MATCH_AFTER_WHITESPACE_NORMALIZATION",
                "source_origin_review": "PENDING", "known_at_pit_review": "PENDING",
                "license_reuse_review": "PENDING",
            },
            "review_constraints": [
                "Exact bytes and a page-level text match do not prove official source origin or first-public time.",
                "The candidate publication date is not promoted to known_at.",
                "This record cannot cover a B2 required field group while status/provenance remain UNKNOWN.",
            ],
        })
    failed = [{
        "source_id": x.get("source_id"), "source_url": x.get("source_url"),
        "capture_status": x.get("capture_status"), "error_code": x.get("error_code"),
        "raw_artifact_path": x.get("raw_artifact_path"), "sha256": x.get("sha256"),
    } for x in receipt.get("sources", []) if x.get("capture_status") != "SUCCESS"]
    return {
        "schema_version": SCHEMA,
        "record_class": "FACT_LEVEL_EXTRACTION_CANDIDATES_NOT_ADMITTED",
        "case_id": receipt["case_id"], "market": receipt["market"],
        "symbol": receipt["symbol"], "company": "浙江新和成股份有限公司",
        "cutoff_date": receipt["cutoff_date"],
        "capture_run": {
            "receipt_status": receipt.get("status"),
            "manifest_sha256": receipt.get("manifest_sha256"),
            "captured_at": receipt.get("captured_at"),
            "declared_sources": len(receipt.get("sources", [])),
            "successful_raw_objects": sum(x.get("capture_status") == "SUCCESS" for x in receipt.get("sources", [])),
            "cited_pdf_bytes_reverified": True,
        },
        "fact_count": len(facts), "facts": facts, "failed_source_objects": failed,
        "b2_status": "BLOCKED_NOT_ADMITTED", "admitted_field_groups": [],
        "required_b2_field_groups": [
            "security_identity", "market_price", "corporate_disclosures", "business_reality",
            "financial_reality", "capital_structure", "trust_governance_events"
        ],
        "field_group_note": "All fact candidates remain UNKNOWN/NOT_ADMITTED. No group is admitted by PDF text matching alone.",
        "market_price_note": "No date-specific daily-close raw record has independently verified known_at. Quote/history pages remain UNKNOWN and the date-specific Eastmoney K-line source failed capture.",
        "llm_provider_required": False, "paid_search_api_required": False,
        "raw_pdf_bytes_committed_to_git": False, "decision_authorized": False,
        "next_gate": "Independent source-origin/publication-time and license review, then B2 Evidence/PIT admission for each selected fact; market price remains a separate unresolved gate.",
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract page-located candidate facts without admitting evidence.")
    parser.add_argument("--input-run-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    review = build_review(args.input_run_dir.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "FACTS_EXTRACTED_NOT_ADMITTED", "case_id": review["case_id"],
        "fact_count": review["fact_count"], "b2_status": review["b2_status"],
        "admitted_field_groups": review["admitted_field_groups"], "record": str(args.out),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
