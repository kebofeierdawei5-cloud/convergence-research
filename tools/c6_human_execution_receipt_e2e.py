from __future__ import annotations

import json
from inspect import signature
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_c6_execution_receipt_production import (
    test_c6_invalid_execution_timestamp_or_negative_amount_fails_closed,
    test_c6_not_executed_receipt_can_be_recorded_without_fake_quantity,
    test_c6_persisted_receipt_is_immutable_and_does_not_mutate_lifecycle,
    test_c6_persisted_replay_reconstructs_receipt,
    test_c6_receipt_binds_exact_approved_revision_and_action,
    test_c6_receipt_tampering_is_detected,
    test_c6_rejected_approval_cannot_create_execution_receipt,
    test_c6_schema_accepts_receipt,
)


def run() -> dict[str, object]:
    checks = (
        ("exact_approved_binding", test_c6_receipt_binds_exact_approved_revision_and_action),
        ("rejected_approval_blocked", test_c6_rejected_approval_cannot_create_execution_receipt),
        ("receipt_immutable_no_lifecycle_mutation", test_c6_persisted_receipt_is_immutable_and_does_not_mutate_lifecycle),
        ("tamper_detection", test_c6_receipt_tampering_is_detected),
        ("not_executed_without_fake_quantity", test_c6_not_executed_receipt_can_be_recorded_without_fake_quantity),
        ("persisted_replay", test_c6_persisted_replay_reconstructs_receipt),
        ("schema_validation", test_c6_schema_accepts_receipt),
        ("invalid_input_fail_closed", test_c6_invalid_execution_timestamp_or_negative_amount_fails_closed),
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
        "policy_effect": "POST_APPROVAL_RECORD_ONLY_NO_DECISION_MUTATION",
        "automatic_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
