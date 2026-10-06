from __future__ import annotations

import json
from inspect import signature
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_c7_full_lifecycle_e2e import (
    test_c7_changed_decision_requires_new_run_and_revision,
    test_c7_full_operating_loop,
    test_c7_monitoring_cannot_mutate_decision_revision,
    test_c7_publication_and_report_are_projections,
)


def run() -> dict[str, object]:
    checks = (
        ("full_operating_loop", test_c7_full_operating_loop),
        ("monitoring_no_decision_mutation", test_c7_monitoring_cannot_mutate_decision_revision),
        ("new_run_new_revision", test_c7_changed_decision_requires_new_run_and_revision),
        ("publication_report_projection_only", test_c7_publication_and_report_are_projections),
    )
    completed = []
    for name, check in checks:
        if len(signature(check).parameters) == 0:
            check()
        else:
            with TemporaryDirectory() as tmp:
                check(Path(tmp))
        completed.append(name)
    return {
        "status": "PASS",
        "checks_passed": completed,
        "check_count": len(completed),
        "policy_effect": "E2E_ORCHESTRATION_ONLY_NO_NEW_INVESTMENT_POLICY",
        "automatic_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
