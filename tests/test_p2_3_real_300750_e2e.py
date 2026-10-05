
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from tools.p2_3_real_300750_e2e import P23_VERSION, run_real_case


REAL_INPUT = Path(
    "examples/real_cases/RC-CN-A-300750-20261004_ratio_mie_input.json"
)


def test_p2_3_real_300750_replays_fail_closed_without_fabricating_mie(tmp_path: Path):
    result = run_real_case(REAL_INPUT, tmp_path / "p2_3_result.json")

    assert result["schema_version"] == P23_VERSION
    assert result["core04c_receipt"]["status"] == "ADMITTED"
    assert result["real_current_observation"]["price"] == "291.11"
    assert Decimal(result["real_current_observation"]["ev_ebitda"]) == Decimal(
        "8.375536786732361377"
    )

    assert result["p3a"]["evaluation_status"] == "INFEASIBLE"
    assert result["p3a"]["identifiability"] == "UNIDENTIFIABLE"
    assert result["p3a"]["stability"] == "INSUFFICIENT_EVIDENCE"
    assert result["p3a"]["feasible_model_ids"] == []
    assert Decimal(result["p3a"]["historical_range"]["low"]) == Decimal(
        "13.6686920853194080865159796474107277185842350664948830139214"
    )
    assert Decimal(result["p3a"]["historical_range"]["high"]) == Decimal(
        "16.3854513730104779459499377618525879665943916394869455326834"
    )

    assert result["p4b"]["status"] == "BLOCKED"
    assert result["p4b"]["mie_materialized"] is False
    assert result["p4f"]["status"] == "BLOCKED"
    assert result["p4f"]["qualification"] == "BLOCKED"
    assert result["p4f"]["resolution_state"] == "NO_FEASIBLE_MODEL"
    assert result["p4f"]["replay_status"] == "PASS"

    assert result["p2_1"]["status"] == "BLOCKED"
    assert result["p2_2"]["canonical_entry_evaluation"]["status"] == "REVIEW_REQUIRED"
    assert result["final_state"] == "REVIEW_REQUIRED"
    assert result["capital_admitted"] is False
    assert result["non_claims"] == [
        "EV/EBITDA is not established as the true market model.",
        "No Market Implied Expectation is materialized.",
        "No Expectation Gap is calculated.",
        "No BUY/ADD decision is issued.",
    ]


def test_p2_3_real_300750_result_is_written_as_replayable_json(tmp_path: Path):
    out = tmp_path / "p2_3_result.json"
    result = run_real_case(REAL_INPUT, out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload == result
    assert payload["case_id"] == "RC-CN-A-300750-20261004"
    assert payload["p4f"]["snapshot_hash"]


def test_p2_3_current_multiple_is_materially_below_historical_lower_bound(tmp_path: Path):
    result = run_real_case(REAL_INPUT, tmp_path / "p2_3_result.json")
    current = Decimal(result["real_current_observation"]["ev_ebitda"])
    historical_low = Decimal(result["p3a"]["historical_range"]["low"])
    discount = Decimal("1") - current / historical_low
    assert discount > Decimal("0.38")
