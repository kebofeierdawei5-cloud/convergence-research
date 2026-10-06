from __future__ import annotations

import json

from tests.test_c5_positioning_sizing_production import (
    test_c5_deterministic_replay_and_tamper_detection,
    test_c5_favorable_snapshot_produces_target_sizing_band,
    test_c5_missing_portfolio_package_blocks_sizing_without_affecting_factors,
    test_c5_missing_positioning_is_explicitly_blocked,
    test_c5_neutral_snapshot_limits_new_sizing_to_initial,
    test_c5_schema_accepts_record,
    test_c5_stale_positioning_known_at_is_fail_closed,
    test_c5_unknown_or_ambiguous_positioning_fails_closed_for_sizing,
    test_c5_unfavorable_snapshot_stops_adds_but_does_not_rewrite_decision,
)


def run() -> dict[str, object]:
    checks = (
        ("favorable_target_band", test_c5_favorable_snapshot_produces_target_sizing_band),
        ("neutral_initial_band", test_c5_neutral_snapshot_limits_new_sizing_to_initial),
        ("unfavorable_no_add", test_c5_unfavorable_snapshot_stops_adds_but_does_not_rewrite_decision),
        ("unknown_ambiguous_fail_closed", test_c5_unknown_or_ambiguous_positioning_fails_closed_for_sizing),
        ("stale_pit_fail_closed", test_c5_stale_positioning_known_at_is_fail_closed),
        ("missing_positioning_blocked", test_c5_missing_positioning_is_explicitly_blocked),
        ("missing_package_blocked", test_c5_missing_portfolio_package_blocks_sizing_without_affecting_factors),
        ("replay_and_tamper", test_c5_deterministic_replay_and_tamper_detection),
        ("schema_validation", test_c5_schema_accepts_record),
    )
    completed: list[str] = []
    for name, check in checks:
        check()
        completed.append(name)
    return {
        "status": "PASS",
        "checks_passed": completed,
        "check_count": len(completed),
        "policy_version": "IIOS-C5-POSITIONING-POLICY-0.1",
        "policy_effect": "TIMING_AND_SIZING_ONLY_NO_FUNDAMENTAL_DECISION_MUTATION",
        "automatic_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
