from __future__ import annotations

import hashlib
import json
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
        "price_sha256": "637bd885980763b1eea5ce63e7b255746e4a4c6ade4ec8981dabbad75635405b",
        "calendar_sha256": "756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7",
        "report_exact_bytes": True,
        "price_exact_bytes": True,
        "calendar_exact_bytes": True,
    },
    "decision_record": {
        "decision_id": "CN-A-002001-r001",
        "decision_series_id": "CN-A-002001",
        "revision": 1,
        "snapshot_hash": "9a9d2e23c243c86d24d3b4814b5a3fb135d759f92b243971d37020c4530b50b5",
        "revision_hash": "1fa6beffeac1251cd7ff81c45cc3ae5f81c6e0424499f6349d30fd2d450bd487",
        "run_id": "run-pilot02-xhc-001",
        "engine_version": "0.3.0",
        "contract_version": "IIOS-DECISION-LIFECYCLE-0.2",
    },
    "publication": {
        "publication_hash": "a667d4e24410a6ad685339f50df6459c5192ff06443e5429c8d6372b33346514",
        "report_hash": "3781c2df4db689c78821c3de6fb2a4241b7b6308b13f662b95804fdd554ac178",
        "qa_hash": "1cd7deafd0f6d22d34b3abb90580a4ce4fa494e70336ab0e3a061da9a80c3ad5",
        "qa_status": "PASS",
        "report_deterministic_replay": True,
    },
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
    _assert_equal(result["publication"], EXPECTED["publication"], "result.publication")
    _assert_equal(result["return_metrics"], EXPECTED["return_metrics"], "result.return_metrics")

    for key, expected in EXPECTED["evidence"].items():
        _assert_equal(receipt[key], expected, f"receipt.{key}")

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

    publication = json.loads(publication_files[0].read_text(encoding="utf-8"))
    _assert_equal(publication["publication_hash"], EXPECTED["publication"]["publication_hash"], "publication.publication_hash")
    _assert_equal(publication["decision_ref"]["revision_hash"], EXPECTED["decision_record"]["revision_hash"], "publication.decision_ref.revision_hash")
    _assert_equal(publication["decision_ref"]["snapshot_hash"], EXPECTED["decision_record"]["snapshot_hash"], "publication.decision_ref.snapshot_hash")

    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    qa = json.loads(qa_files[0].read_text(encoding="utf-8"))
    _assert_equal(report["report_hash"], EXPECTED["publication"]["report_hash"], "report.report_hash")
    _assert_equal(qa["qa_hash"], EXPECTED["publication"]["qa_hash"], "qa.qa_hash")
    _assert_equal(qa["qa_status"], EXPECTED["publication"]["qa_status"], "qa.qa_status")

    expected_result_sha = hashlib.sha256(
        (out_dir / "PILOT-02_XINHECHENG_RESULT.json").read_bytes()
    ).hexdigest()
    if not expected_result_sha:
        raise AssertionError("empty result hash")

    # Numeric invariants remain explicit rather than trusting formatting alone.
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

    print("PILOT-04_INDEPENDENT_CLEAN_REPLAY_MATCHES_ACCEPTED_PILOT-02=PASS")
    print(json.dumps({
        "decision_id": decision_record["decision_id"],
        "revision_hash": decision_record["revision_hash"],
        "publication_hash": publication["publication_hash"],
        "report_hash": report["report_hash"],
        "qa_hash": qa["qa_hash"],
        "result_sha256": expected_result_sha,
    }, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
