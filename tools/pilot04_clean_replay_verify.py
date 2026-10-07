from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path


EXPECTED = {
    "case_id": "RC-CN-A-002001-20261007",
    "company": "浙江新和成股份有限公司",
    "symbol": "002001",
    "cutoff_date": "2026-10-07",
    "latest_tradable_date": "2026-09-30",
    "current_price": "25.95",
    "security_classification": "NON_FINANCIAL",
    "research_weighting": {
        "cyclical": "0.70",
        "growth": "0.30",
        "financial_sector_inclusion": False,
        "classification": "USER_REQUESTED_RESEARCH_WEIGHTING_NOT_EVIDENCE",
    },
    "quality_gate_status": "CONDITIONAL",
    "trust_status": "REVALIDATION",
    "decision": {
        "action": "REVIEW_REQUIRED",
        "decision_status": "REVIEW_REQUIRED",
        "primary_reason": "TRUST_NOT_PASS_REQUIRES_REVIEW",
        "new_capital_allowed": False,
        "human_approval_required": True,
        "auto_execution": False,
    },
    "return_metrics": {
        "entry_return_cushion": "0.240847784200385356454720617",
        "margin_of_safety": "0.1940993788819875776397515528",
        "expected_total_return": "0.201734104046242774566473988",
        "expected_annualized_return": "0.201734104046242774566473988",
        "fundamental_target_pass": True,
        "required_return_pass": True,
        "risk_pass": True,
        "target_entry_price": "26.6",
    },
    "lifecycle": {
        "decision_revision": 1,
        "decision_replay_status": "PASS",
        "monitoring_evaluation_status": "VALID",
        "validation_status": "PASS",
    },
    "evidence": {
        "report_sha256": "ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e",
        "calendar_sha256": "756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7",
        "report_exact_bytes": True,
        "price_exact_bytes": True,
        "calendar_exact_bytes": True,
        "price_projection_sha256": "cdbe0bfc375a5d84ed99d59a3ca925e4488607d8ad3d4df57f7b5d88962473be",
    },
    "decision_record": {
        "decision_id": "CN-A-002001-r001",
        "decision_series_id": "CN-A-002001",
        "revision": 1,
        "run_id": "run-pilot02-xhc-001",
        "engine_version": "0.3.0",
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.2",
    },
    "canonical_semantic_fingerprint": "acd3943850ed38ca001e4a636ba8fea6e5cf69e23b0cfb820a8ad2e398408af2",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_equal(actual: object, expected: object, path: str) -> None:
    if actual != expected:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def _stable_semantic_subset(result: dict) -> dict:
    return {
        "case_id": result["case_id"],
        "company": result["company"],
        "symbol": result["symbol"],
        "cutoff_date": result["cutoff_date"],
        "latest_tradable_date": result["latest_tradable_date"],
        "current_price": result["current_price"],
        "security_classification": result["security_classification"],
        "research_weighting": result["research_weighting"],
        "quality_gate_status": result["quality_gate_status"],
        "trust_status": result["trust_status"],
        "decision": result["decision"],
        "return_metrics": result["return_metrics"],
        "lifecycle": result["lifecycle"],
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: pilot04_clean_replay_verify.py <out_dir> <receipt.json>")

    out_dir = Path(sys.argv[1])
    receipt_path = Path(sys.argv[2])
    result = json.loads((out_dir / "PILOT-02_XINHECHENG_RESULT.json").read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    for key in (
        "case_id",
        "company",
        "symbol",
        "cutoff_date",
        "latest_tradable_date",
        "current_price",
        "security_classification",
        "quality_gate_status",
        "trust_status",
    ):
        _assert_equal(result[key], EXPECTED[key], f"result.{key}")

    _assert_equal(result["research_weighting"], EXPECTED["research_weighting"], "result.research_weighting")
    _assert_equal(result["decision"], EXPECTED["decision"], "result.decision")
    _assert_equal(result["lifecycle"], EXPECTED["lifecycle"], "result.lifecycle")
    _assert_equal(result["return_metrics"], EXPECTED["return_metrics"], "result.return_metrics")

    semantic_bytes = json.dumps(
        _stable_semantic_subset(result),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    semantic_hash = hashlib.sha256(semantic_bytes).hexdigest()
    _assert_equal(semantic_hash, EXPECTED["canonical_semantic_fingerprint"], "canonical_semantic_fingerprint")

    _assert_equal(receipt["report_sha256"], EXPECTED["evidence"]["report_sha256"], "receipt.report_sha256")
    _assert_equal(receipt["calendar_sha256"], EXPECTED["evidence"]["calendar_sha256"], "receipt.calendar_sha256")
    _assert_equal(receipt["report_exact_bytes"], True, "receipt.report_exact_bytes")
    _assert_equal(receipt["price_exact_bytes"], True, "receipt.price_exact_bytes")
    _assert_equal(receipt["calendar_exact_bytes"], True, "receipt.calendar_exact_bytes")
    _assert_equal(receipt["price_projection_sha256"], EXPECTED["evidence"]["price_projection_sha256"], "receipt.price_projection_sha256")
    _assert_equal(
        receipt["price_source_ref"],
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz002001,day,2026-09-30,2026-09-30,5,",
        "receipt.price_source_ref",
    )

    price_sha = receipt.get("price_sha256")
    if not isinstance(price_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", price_sha):
        raise AssertionError("receipt.price_sha256 must be a 64-character raw-byte SHA-256")
    if price_sha == "":
        raise AssertionError("receipt.price_sha256 must not be empty")

    decision_files = sorted(out_dir.glob("*.decision.json"))
    publication_files = sorted(out_dir.glob("*.publication.json"))
    report_files = sorted(out_dir.glob("*.report.json"))
    qa_files = sorted(out_dir.glob("*.report-qa.json"))
    _assert_equal(len(decision_files), 1, "decision_file_count")
    _assert_equal(len(publication_files), 1, "publication_file_count")
    _assert_equal(len(report_files), 1, "report_file_count")
    _assert_equal(len(qa_files), 1, "qa_file_count")

    decision_record = json.loads(decision_files[0].read_text(encoding="utf-8"))
    for key, expected in EXPECTED["decision_record"].items():
        _assert_equal(decision_record[key], expected, f"decision_record.{key}")

    snapshot_hash = decision_record.get("snapshot_hash")
    revision_hash = decision_record.get("revision_hash")
    for label, value in (("snapshot_hash", snapshot_hash), ("revision_hash", revision_hash)):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise AssertionError(f"decision_record.{label} must be a 64-character SHA-256")

    publication = json.loads(publication_files[0].read_text(encoding="utf-8"))
    _assert_equal(publication["case"]["case_id"], EXPECTED["case_id"], "publication.case.case_id")
    _assert_equal(publication["case"]["symbol"], EXPECTED["symbol"], "publication.case.symbol")
    _assert_equal(publication["decision_ref"]["decision_id"], decision_record["decision_id"], "publication.decision_ref.decision_id")
    _assert_equal(publication["decision_ref"]["revision_hash"], revision_hash, "publication.decision_ref.revision_hash")
    _assert_equal(publication["decision_ref"]["snapshot_hash"], snapshot_hash, "publication.decision_ref.snapshot_hash")

    publication_hash = publication["publication_hash"]
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    qa = json.loads(qa_files[0].read_text(encoding="utf-8"))
    _assert_equal(report["report_hash"], result["publication"]["report_hash"], "report.report_hash")
    _assert_equal(qa["qa_hash"], result["publication"]["qa_hash"], "qa.qa_hash")
    _assert_equal(qa["qa_status"], "PASS", "qa.qa_status")
    _assert_equal(result["publication"]["publication_hash"], publication_hash, "result.publication.publication_hash")
    _assert_equal(result["publication"]["qa_status"], "PASS", "result.publication.qa_status")
    _assert_equal(result["publication"]["report_deterministic_replay"], True, "result.publication.report_deterministic_replay")

    _assert_equal(
        report_files[0].stem,
        f"{report['report_hash']}.report",
        "report filename/content hash binding",
    )
    _assert_equal(
        qa_files[0].stem,
        f"{qa['qa_hash']}.report-qa",
        "qa filename/content hash binding",
    )

    _assert_equal(
        Decimal(result["return_metrics"]["expected_annualized_return"]) > Decimal("0.15"),
        True,
        "return_metrics.expected_annualized_return_gt_15pct",
    )
    _assert_equal(
        Decimal(result["return_metrics"]["target_entry_price"]),
        Decimal("26.6"),
        "return_metrics.target_entry_price",
    )

    print("PILOT-04_INDEPENDENT_CLEAN_REPLAY_SEMANTIC_MATCH=PASS")
    print(json.dumps({
        "decision_id": decision_record["decision_id"],
        "snapshot_hash": snapshot_hash,
        "revision_hash": revision_hash,
        "publication_hash": publication_hash,
        "report_hash": report["report_hash"],
        "qa_hash": qa["qa_hash"],
        "fresh_price_sha256": price_sha,
        "price_projection_sha256": receipt["price_projection_sha256"],
        "canonical_semantic_fingerprint": semantic_hash,
    }, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
