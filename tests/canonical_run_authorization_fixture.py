"""Test-only helper to synthesize a complete run authorization for unit fixtures.

This helper is intentionally located under tests/. It creates no source evidence
and must never be imported by production package code.
"""
from __future__ import annotations

from typing import Any, Mapping

from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.canonical_run_authorization import canonical_hash, write_run_authorization


def authorize_test_run(
    root,
    *,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
    run_id: str,
) -> None:
    if snapshot.get("snapshot_schema") != "IIOS-MVP-SNAPSHOT-0.3.0":
        return
    input_data = snapshot.get("input")
    if not isinstance(input_data, Mapping):
        raise ValueError("test fixture snapshot input is required")
    case_id = str(input_data["case_id"])
    market = str(input_data["market"])
    symbol = str(input_data["symbol"])
    cutoff_date = str(input_data["cutoff_date"])
    as_of_date = str(input_data.get("as_of_date") or cutoff_date)
    case_hash = canonical_hash(dict(input_data))

    orchestrator = CanonicalResearchOrchestrator()
    orchestrator.start(
        run_id=run_id,
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=cutoff_date,
        as_of_date=as_of_date,
        research_case_hash=case_hash,
        created_at="2026-10-09T15:00:00+00:00",
    )
    stages = [
        (Stage.REQUEST_ADMITTED, "CODE"),
        (Stage.CASE_CREATED, "CODE"),
        (Stage.EVIDENCE_PENDING, "CODE"),
        (Stage.EVIDENCE_ADMITTED, "B2_EVIDENCE_PIT_VALIDATOR"),
        (Stage.SEMANTIC_PENDING, "CODE"),
        (Stage.SEMANTIC_ADMITTED, "LLM_SEMANTIC_PRODUCER"),
        (Stage.FORECAST_PENDING, "CODE"),
        (Stage.FORECAST_ADMITTED, "INDEPENDENT_FORECAST_ADMISSION"),
        (Stage.VALUATION_PENDING, "CODE"),
        (Stage.VALUATION_ADMITTED, "VALUATION_ADMISSION"),
        (Stage.DECISION_PENDING, "CODE"),
        (Stage.DECISION_ADMITTED, "DECISION_ADMISSION_VALIDATOR"),
    ]
    previous_hash = None
    for index, (stage, producer) in enumerate(stages, start=1):
        if stage == Stage.CASE_CREATED:
            output_hash = case_hash
        elif stage == Stage.DECISION_ADMITTED:
            output_hash = canonical_hash(dict(decision_admission))
        else:
            output_hash = canonical_hash(
                {"test_fixture_only": True, "run_id": run_id, "stage": stage.value, "ordinal": index}
            )
        orchestrator.transition(
            run_id,
            stage,
            input_refs=() if previous_hash is None else (f"test-fixture-stage-output:{index-1}",),
            input_hashes=() if previous_hash is None else (previous_hash,),
            output_refs=(f"test-fixture-stage-output:{index}",),
            output_hashes=(output_hash,),
            producer_type=producer,
            producer_version=f"TEST_FIXTURE_PRODUCER_{index}",
            status="PASS",
            created_at="2026-10-09T15:00:00+00:00",
        )
        previous_hash = output_hash

    write_run_authorization(
        root,
        envelope=orchestrator.get(run_id),
        snapshot=snapshot,
        decision_admission=decision_admission,
        issued_at="2026-10-09T15:01:00+00:00",
    )
