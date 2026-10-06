from __future__ import annotations

import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tests import test_c8_final_redteam as suite


SAFE = (
    ("real_company_fixture_set", suite.test_c8_real_company_fixture_set_contains_catl_and_kolun),
    ("current_price_pit", suite.test_c8_current_price_pit_leak_is_rejected),
    ("independent_forecast_pit", suite.test_c8_independent_forecast_pit_leak_is_rejected),
    ("expectation_gap_unit", suite.test_c8_expectation_gap_unit_mismatch_refuses_scalar_gap),
    ("mie_non_unique", suite.test_c8_mie_non_unique_refuses_scalar_gap),
    ("return_required_return", suite.test_c8_return_and_required_return_fail_closed),
    ("revision_immutability", suite.test_c8_revision_overwrite_is_rejected),
    ("approval_binding", suite.test_c8_approval_cross_revision_mismatch_is_rejected),
    ("monitoring_tamper", suite.test_c8_monitoring_history_tamper_is_detected),
    ("publication_report_drift", suite.test_c8_publication_report_drift_is_detected),
    ("execution_human_boundary", suite.test_c8_execution_receipt_requires_human_approved),
)

FINDINGS = (
    (
        "C8-AUTH-001",
        "CRITICAL",
        "Decision Revision persistence accepts a caller-crafted BUY snapshot without canonical Decision Kernel provenance.",
        suite.test_c8_crafted_revision_can_bypass_kernel,
    ),
    (
        "C8-AUTH-002",
        "CRITICAL",
        "Decision Revision persistence accepts a CATL snapshot inside the 科伦药业 decision series; series identity is not enforced against snapshot identity.",
        suite.test_c8_cross_company_revision_coupling_can_bypass_identity,
    ),
    (
        "C8-AUTH-003",
        "HIGH",
        "Human Approval binding has no actor-identity field; human-vs-LLM authorization remains an external boundary.",
        suite.test_c8_human_approval_has_no_actor_identity_boundary,
    ),
)


def _run(fn):
    if len(inspect.signature(fn).parameters) == 0:
        fn()
        return
    with TemporaryDirectory(prefix="iios-c8-fixture-") as tmp:
        fn(Path(tmp))


def run() -> dict[str, object]:
    safe = []
    for name, fn in SAFE:
        _run(fn)
        safe.append(name)

    findings = []
    for finding_id, severity, description, fn in FINDINGS:
        _run(fn)
        findings.append(
            {
                "finding_id": finding_id,
                "severity": severity,
                "description": description,
                "reproduced": True,
            }
        )

    return {
        "status": "BLOCKED",
        "acceptance": "C8_FINAL_MVP_ACCEPTANCE_BLOCKED",
        "real_company_set": [suite.CATL_CASE, suite.KOLUN_CASE],
        "safe_control_count": len(safe),
        "safe_controls_passed": safe,
        "finding_count": len(findings),
        "findings_reproduced": findings,
        "critical_finding_count": 2,
        "high_finding_count": 1,
        "production_fix_applied": False,
        "next_boundary": "REMEDIATE_C8-AUTH-001_002_003_THEN_RE-RUN_C8",
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
