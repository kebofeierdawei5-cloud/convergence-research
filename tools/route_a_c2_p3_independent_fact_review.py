from __future__ import annotations

"""Separate-method review of C2 Run #8 facts; never imports the candidate builder."""

import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import zipfile

from pypdf import PdfReader

ARCHIVE_SHA256 = "0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1"
CASE_ID = "RC-CN-A-002001-20261009"
CUTOFF = datetime.fromisoformat("2026-10-09T00:00:00+08:00")

# Independent review matrix, authored separately from the successor tool.
MATRIX: tuple[dict[str, Any], ...] = (
    {"id":"XHC-FACT-SECURITY-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":2,"terms":["浙江新和成股份有限公司","股票简称新和成股票代码002001","股票上市交易所深圳证券交易所"],"label":"Issuer/security identity"},
    {"id":"XHC-FACT-CORPORATE-H1-DISCLOSURE-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":1,"terms":["公告编号：2026-035","2026年半年度报告摘要"],"label":"H1 report title and announcement number"},
    {"id":"XHC-FACT-FIN-REVENUE-H1-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":2,"terms":["营业收入（元）","13,129,300,260.89","18.28%"],"label":"H1 revenue and YoY growth"},
    {"id":"XHC-FACT-FIN-NET-PROFIT-H1-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":2,"terms":["归属于上市公司股东的净利润（元）","4,010,733,454.55","11.31%"],"label":"H1 attributable net profit and YoY growth"},
    {"id":"XHC-FACT-FIN-ADJ-PROFIT-H1-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":2,"terms":["归属于上市公司股东的扣除非经常性损益的净利润（元）","3,918,936,563.72","6.53%"],"label":"H1 adjusted attributable net profit and YoY growth"},
    {"id":"XHC-FACT-FIN-OCF-H1-001","source":"SZSE-2026-H1-SUMMARY","member":"raw/SZSE-2026-H1-SUMMARY.pdf","page":2,"terms":["经营活动产生的现金流量净额（元）","3,640,144,282.94","12.26%"],"label":"H1 operating cash flow and YoY growth"},
    {"id":"XHC-FACT-BUSINESS-METHIONINE-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":9,"terms":["公司营养品板块主要产品蛋氨酸市场需求和价格显著上涨","公司蛋氨酸业务实现量价齐升"],"label":"Management statement on methionine"},
    {"id":"XHC-FACT-BUSINESS-PROJECTS-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":9,"terms":["天津新材料尼龙产业链项目土建装置基本完成交安","设备陆续到货开始安装","PPS四期项目落地建设","HA二期土建顺利开工"],"label":"Management statement on project progress"},
    {"id":"XHC-FACT-FIN-RD-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":10,"terms":["研发投入","605,728,077.64","15.88%"],"label":"H1 R&D expense and YoY growth"},
    {"id":"XHC-FACT-FIN-SEGMENTS-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":11,"terms":["8,805,591,681.68","2,022,263,282.57","1,165,989,510.74","22.30%","-3.91%","12.31%"],"label":"H1 revenue by product segment"},
    {"id":"XHC-FACT-CAPITAL-ASSETS-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":12,"terms":["货币资金","7,458,042,805.72","固定资产","19,538,428,936.53","在建工程","1,006,512,957.55"],"label":"H1-end assets"},
    {"id":"XHC-FACT-CAPITAL-DEBT-H1-001","source":"SZSE-2026-H1-FULL","member":"raw/SZSE-2026-H1-FULL.pdf","page":12,"terms":["短期借款","962,032,277.99","长期借款","3,170,163,350.48","一年内到期的非流动负债","2,745,428,550.04"],"label":"H1-end debt items"},
    {"id":"XHC-FACT-TRUST-BUYBACK-PLAN-001","source":"SZSE-2026-BUYBACK-PLAN","member":"raw/SZSE-2026-BUYBACK-PLAN.pdf","page":1,"terms":["公告编号：2026-027","30,000万元-60,000万元","45.50元/股","股权激励计划或员工持股计划"],"label":"Buyback plan amount, price cap and purpose"},
)

def compact(s: str) -> str:
    return re.sub(r"\s+", "", s)

def conservative_known_at(published_date: str) -> datetime:
    return datetime.fromisoformat(str(published_date) + "T23:59:59+08:00")

def reuse_rights_cleared(license_status: str, retention_permission: Any = None) -> bool:
    return str(license_status or "").upper() in {"PERMITTED_INTERNAL_USE", "LICENSED_INTERNAL_USE"} or (
        isinstance(retention_permission, str) and bool(retention_permission.strip())
    )

PINNED_MEMBER_SHA256 = {
    "B2_COMPANY_EVIDENCE_MANIFEST.json": "21dad3842914b10aa4e454e74c3f6fb19694844c8e9353dd4452698fac920132",
    "COMPANY_EVIDENCE_INTAKE_RECEIPT.json": "f05bf8ad72f58bfa19225afbccbe087cc3df4833e86a7c358b61243d9d97e36e",
    "COMPANY_EVIDENCE_INTAKE_VERIFICATION.json": "9ac5bc8bb4415f5dd8022ac4b4bf966aad3b153d2b02e0ddfb2cbb0ba9d017d0",
    "ROUTE_A_B2_PREFLIGHT.json": "76fb5d112fb796c256d17f9003fc6e11946906498e137d0bd75fc97fe7d6ac70",
    "intake_manifest.json": "c6ec425f3c2ef5404bbdd1868e57434c64da90e255bcde5eae24586dba1227e3",
    "raw/ISSUER-IR-PAGE-CURRENT.bin": "18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c",
    "raw/PRICE-EASTMONEY-QUOTE.html": "97bf733ac8f7d1fd14bb3377fd85041940b4ef225349bdc07710f9c22a827cfa",
    "raw/PRICE-SOHU-HISTORY.bin": "0f05a4c643ef19de9d313c4231ab200386b6946920c066fb104d23ebb683efd3",
    "raw/SZSE-2026-BUYBACK-PLAN.pdf": "e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9",
    "raw/SZSE-2026-BUYBACK-PROGRESS-SEP.pdf": "af6ad44d49b10b0f23306e0812fa64200880b29883bcaa71fecaf6b54a8ac6ed",
    "raw/SZSE-2026-H1-FULL.pdf": "ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e",
    "raw/SZSE-2026-H1-SUMMARY.pdf": "bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3",
    "raw/SZSE-2026-Q1-FULL.pdf": "facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa",
}


def _review_source_members(
    get_member,
    *,
    source_archive_sha256: str | None,
    integrity_method: str,
) -> dict[str, Any]:
    # Pin every original artifact member by SHA-256 whether the downloader
    # exposes the ZIP file or extracts its verified contents into a directory.
    for name, expected in PINNED_MEMBER_SHA256.items():
        data = get_member(name)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("C2_P3_SOURCE_MEMBER_SHA256_MISMATCH:" + name)
    intake = json.loads(get_member("intake_manifest.json").decode("utf-8"))
    receipt = json.loads(get_member("COMPANY_EVIDENCE_INTAKE_RECEIPT.json").decode("utf-8"))
    sources = {x.get("source_id"): x for x in intake.get("sources", []) if isinstance(x, dict)}
    receipt_sources = {x.get("source_id"): x for x in receipt.get("sources", []) if isinstance(x, dict)}
    facts = []
    pdfs: dict[str, tuple[bytes, PdfReader, str]] = {}
    for item in MATRIX:
        source = sources.get(item["source"])
        receipt_row = receipt_sources.get(item["source"])
        if not isinstance(source, dict) or not isinstance(receipt_row, dict):
            raise ValueError("C2_P3_SOURCE_BINDING_MISSING:" + item["source"])
        member = item["member"]
        if member not in pdfs:
            raw_pdf = get_member(member)
            pdfs[member] = (raw_pdf, PdfReader(io.BytesIO(raw_pdf)), hashlib.sha256(raw_pdf).hexdigest())
        raw_pdf, reader, pdf_sha = pdfs[member]
        page = int(item["page"])
        if page < 1 or page > len(reader.pages):
            raise ValueError("C2_P3_PAGE_OUT_OF_RANGE:" + item["id"])
        page_text = compact(reader.pages[page - 1].extract_text() or "")
        missing = [term for term in item["terms"] if compact(term) not in page_text]
        url = str(source.get("url") or "")
        published_date = str(source.get("published_at") or receipt_row.get("published_at") or "")[:10]
        match = re.search(r"/((?:20\d{2})-\d{2}-\d{2})/", url)
        url_date = match.group(1) if match else ""
        known = conservative_known_at(published_date) if published_date else None
        facts.append({
            "fact_id": item["id"], "source_id": item["source"], "physical_pdf_page": page,
            "source_pdf_sha256": pdf_sha, "source_pdf_size_bytes": len(raw_pdf),
            "locator_status": "PASS" if not missing else "FAIL", "missing_term_count": len(missing),
            "official_https_szse_url": url.startswith("https://disc.static.szse.cn/"),
            "url_date_matches_intake_publication_date": bool(url_date and published_date and url_date == published_date),
            "conservative_known_at": known.isoformat() if known else None,
            "known_at_before_cutoff": bool(known and known <= CUTOFF),
            "license_status": str(source.get("license_status") or receipt_row.get("license_status") or "UNKNOWN"),
            "retention_permission_declared": bool(source.get("retention_permission")),
            "label": item["label"],
        })
    progress = sources.get("SZSE-2026-BUYBACK-PROGRESS-SEP", {})
    progress_date = str(progress.get("known_at") or progress.get("published_at") or "")[:10]
    progress_upper = conservative_known_at(progress_date) if progress_date else None
    progress_excluded = bool(progress_upper and progress_upper > CUTOFF)
    locators = all(x["locator_status"] == "PASS" for x in facts)
    domains = all(x["official_https_szse_url"] for x in facts)
    date_matches = all(x["url_date_matches_intake_publication_date"] for x in facts)
    pit = all(x["known_at_before_cutoff"] for x in facts)
    rights = all(reuse_rights_cleared(x["license_status"], x["retention_permission_declared"]) for x in facts)
    return {
        "schema_version": "IIOS-C2-P3-INDEPENDENT-LOCAL-FACT-REVIEW-0.1",
        "record_class": "SANITIZED_INDEPENDENT_METHOD_REVIEW_NOT_EXTERNAL_SIGNOFF",
        "case_id": CASE_ID, "cutoff": CUTOFF.isoformat(),
        "pinned_original_archive_sha256_reference": ARCHIVE_SHA256,
        "observed_source_archive_sha256": source_archive_sha256,
        "original_archive_sha256_observed": source_archive_sha256 is not None,
        "source_integrity_method": integrity_method,
        "pinned_original_member_count": len(PINNED_MEMBER_SHA256),
        "fact_count": len(facts), "fact_locator_pass_count": sum(x["locator_status"] == "PASS" for x in facts),
        "all_fact_locators_pass": locators, "all_source_urls_https_official_szse": domains,
        "all_url_date_matches_intake_publication_date": date_matches,
        "all_conservative_known_at_before_cutoff": pit, "same_day_buyback_progress_excluded": progress_excluded,
        "source_reuse_rights_cleared": rights, "source_reuse_statuses": sorted({x["license_status"] for x in facts}),
        "factual_claim_review": "PASS" if locators else "BLOCKED",
        "cutoff_and_source_binding_review": "PASS" if domains and date_matches and pit and progress_excluded else "BLOCKED",
        "use_rights_review": "BLOCKED_UNKNOWN_REUSE_OR_RETENTION_RIGHTS" if not rights else "PASS",
        "independent_external_reviewer_signoff": False, "legal_opinion": False,
        "market_price_value_in_report": False, "secondary_market_price_web_audit_performed": False,
        "formal_signed_admission_created": False, "production_host_accepted": False,
        "decision_created": False, "publication_created": False, "run_receipt_created": False, "execution_authorized": False,
        "overall_status": "FACT_AND_PIT_SECOND_PASS_PASS; FORMAL_ADMISSION_BLOCKED_ON_UNKNOWN_USE_RIGHTS_AND_EXTERNAL_REVIEW",
        "facts": facts,
        "next_gate": "A separate reviewer must sign off the 13 claims and fact-level private-use boundary. Unknown source reuse/retention rights stay blocking; do not repeat market-price web search."
    }


def review_archive_bytes(raw_archive: bytes) -> dict[str, Any]:
    archive_sha = hashlib.sha256(raw_archive).hexdigest()
    if archive_sha != ARCHIVE_SHA256:
        raise ValueError("C2_P3_ARCHIVE_SHA256_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as zf:
        infos = zf.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ValueError("C2_P3_ARCHIVE_DUPLICATE_MEMBER")
        if set(names) != set(PINNED_MEMBER_SHA256):
            raise ValueError("C2_P3_ARCHIVE_MEMBER_SET_MISMATCH")
        for info in infos:
            member = PurePosixPath(info.filename)
            if member.is_absolute() or ".." in member.parts or not member.parts or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("C2_P3_ARCHIVE_UNSAFE_MEMBER")
        return _review_source_members(zf.read, source_archive_sha256=archive_sha, integrity_method="PINNED_ARCHIVE_SHA256_AND_PINNED_INNER_OBJECT_SHA256")


def review_archive_dir(root: Path, *, artifact_digest_verified_by_downloader: bool = False) -> dict[str, Any]:
    candidates = []
    for candidate in root.rglob("*.zip"):
        try:
            data = candidate.read_bytes()
        except OSError:
            continue
        if hashlib.sha256(data).hexdigest() == ARCHIVE_SHA256:
            candidates.append(data)
    if len(candidates) == 1:
        return review_archive_bytes(candidates[0])
    if candidates:
        raise ValueError("C2_P3_PINNED_ARCHIVE_CANDIDATE_COUNT:" + str(len(candidates)))
    if not artifact_digest_verified_by_downloader:
        raise ValueError("C2_P3_EXTRACTED_TREE_REQUIRES_DOWNLOADER_DIGEST_FLAG")
    manifests = list(root.rglob("intake_manifest.json"))
    if len(manifests) != 1:
        raise ValueError("C2_P3_EXTRACTED_MANIFEST_COUNT:" + str(len(manifests)))
    base = manifests[0].parent
    found = {
        item.relative_to(base).as_posix()
        for item in base.rglob("*")
        if item.is_file()
    }
    if found != set(PINNED_MEMBER_SHA256):
        raise ValueError("C2_P3_EXTRACTED_MEMBER_SET_MISMATCH")
    return _review_source_members(
        lambda name: (base / name).read_bytes(),
        source_archive_sha256=None,
        integrity_method="ACTIONS_DOWNLOAD_ARTIFACT_V4_DIGEST_PLUS_PINNED_INNER_OBJECT_SHA256",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Separate-method C2 fact/PIT review; not external sign-off.")
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--artifact-digest-verified-by-download-action", action="store_true")
    args = parser.parse_args()
    try:
        report = review_archive_dir(args.artifact_root, artifact_digest_verified_by_downloader=args.artifact_digest_verified_by_download_action)
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["overall_status"], "fact_locator_pass_count": report["fact_locator_pass_count"],
        "fact_count": report["fact_count"], "source_integrity_method": report["source_integrity_method"],
        "cutoff_and_source_binding_review": report["cutoff_and_source_binding_review"],
        "use_rights_review": report["use_rights_review"], "external_reviewer_signoff": report["independent_external_reviewer_signoff"],
        "market_price_value_in_report": report["market_price_value_in_report"]
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
