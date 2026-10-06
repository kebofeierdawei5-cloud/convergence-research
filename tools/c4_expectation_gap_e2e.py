from __future__ import annotations

import json

from tests.test_c4_expectation_gap_production import (
    test_c4_ambiguous_market_interpretation_has_no_scalar_gap,
    test_c4_expectation_gap_evaluation_is_bound_into_canonical_decision,
    test_c4_incompatible_semantics_never_materialize_a_scalar_gap,
    test_c4_no_feasible_solution_is_not_promoted_to_a_gap,
    test_c4_nonpositive_gap_is_a_real_calculation_but_remains_advisory,
    test_c4_positive_compatible_gap_is_materialized_and_replayable,
    test_c4_schema_accepts_real_evaluation,
)


def run() -> dict[str, object]:
    checks = (
        (
            "positive_compatible_gap_materializes",
            test_c4_positive_compatible_gap_is_materialized_and_replayable,
        ),
        (
            "nonpositive_gap_remains_advisory",
            test_c4_nonpositive_gap_is_a_real_calculation_but_remains_advisory,
        ),
        (
            "incompatible_semantics_no_scalar",
            test_c4_incompatible_semantics_never_materialize_a_scalar_gap,
        ),
        (
            "ambiguous_market_no_scalar",
            test_c4_ambiguous_market_interpretation_has_no_scalar_gap,
        ),
        (
            "no_feasible_model_no_scalar",
            test_c4_no_feasible_solution_is_not_promoted_to_a_gap,
        ),
        (
            "decision_binding",
            test_c4_expectation_gap_evaluation_is_bound_into_canonical_decision,
        ),
        (
            "schema_validation",
            test_c4_schema_accepts_real_evaluation,
        ),
    )
    completed: list[str] = []
    for name, check in checks:
        check()
        completed.append(name)
    return {
        "status": "PASS",
        "checks_passed": completed,
        "check_count": len(completed),
        "policy_effect": "ADVISORY_ONLY_NO_ADDITIVE_RETURN_THRESHOLD",
        "automatic_execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
