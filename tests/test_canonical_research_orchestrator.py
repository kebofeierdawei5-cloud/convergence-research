from datetime import datetime, timezone

import pytest

from iios_mvp.canonical_research_orchestrator import (
    CanonicalResearchOrchestrator,
    RunStatus,
    Stage,
    canonical_hash,
)

SHA = "a" * 64


def test_stage_bypass_is_rejected():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="r1",
        case_id="c1",
        market="CN-A",
        symbol="002001.SZ",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        created_at="2026-10-07T00:00:00+00:00",
    )
    with pytest.raises(ValueError, match="stage bypass forbidden"):
        o.transition("r1", Stage.EVIDENCE_ADMITTED, artifact_ref="e1")


def test_semantic_admission_requires_authorized_producer_and_artifact():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="r2",
        case_id="c2",
        market="CN-A",
        symbol="300750.SZ",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        created_at="2026-10-07T00:00:00+00:00",
    )
    o.transition("r2", Stage.REQUEST_ADMITTED)
    o.transition("r2", Stage.CASE_CREATED)
    o.transition("r2", Stage.EVIDENCE_PENDING)
    o.transition(
        "r2",
        Stage.EVIDENCE_ADMITTED,
        artifact_ref="evidence-manifest",
        output_hashes=(SHA,),
    )
    o.transition("r2", Stage.SEMANTIC_PENDING)
    with pytest.raises(ValueError, match="authorized semantic producer"):
        o.transition("r2", Stage.SEMANTIC_ADMITTED, artifact_ref="semantic-1", producer_type="EXTERNAL_JSON")

    state = o.transition(
        "r2",
        Stage.SEMANTIC_ADMITTED,
        artifact_ref="semantic-1",
        output_hashes=(SHA,),
        producer_type="LLM_SEMANTIC_PRODUCER",
        producer_version="llm-adapter-0.1",
    )
    assert state.stage_state == Stage.SEMANTIC_ADMITTED
    assert state.stage_receipts[-1].producer_type == "LLM_SEMANTIC_PRODUCER"


def test_canonical_stage_chain_and_receipt_complete():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="r3",
        case_id="c3",
        market="CN-A",
        symbol="002001.SZ",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        research_case_hash=SHA,
        created_at="2026-10-07T00:00:00+00:00",
    )
    o.transition("r3", Stage.REQUEST_ADMITTED)
    o.transition("r3", Stage.CASE_CREATED)
    o.transition("r3", Stage.EVIDENCE_PENDING)
    o.transition("r3", Stage.EVIDENCE_ADMITTED, artifact_ref="evidence", output_hashes=(SHA,))
    o.transition("r3", Stage.SEMANTIC_PENDING)
    o.transition(
        "r3",
        Stage.SEMANTIC_ADMITTED,
        artifact_ref="semantic",
        output_hashes=(SHA,),
        producer_type="LLM_SEMANTIC_PRODUCER",
        producer_version="adapter-0.1",
    )
    o.transition("r3", Stage.FORECAST_PENDING)
    o.transition("r3", Stage.FORECAST_ADMITTED, artifact_ref="forecast", output_hashes=(SHA,))
    o.transition("r3", Stage.VALUATION_PENDING)
    o.transition("r3", Stage.VALUATION_ADMITTED, artifact_ref="valuation", output_hashes=(SHA,))
    o.transition("r3", Stage.DECISION_PENDING)
    o.transition("r3", Stage.DECISION_ADMITTED, artifact_ref="decision", output_hashes=(SHA,))
    o.transition("r3", Stage.HUMAN_APPROVAL_PENDING)
    o.transition("r3", Stage.PUBLISHED, artifact_ref="publication", output_hashes=(SHA,))
    o.transition("r3", Stage.REPORTED, artifact_ref="report", output_hashes=(SHA,))
    state = o.transition("r3", Stage.COMPLETE)

    assert state.run_status == RunStatus.COMPLETE
    assert len(state.stage_receipts) == 16
    receipt = o.build_run_receipt(
        "r3",
        evidence_manifest_hash=SHA,
        semantic_artifact_hashes=(SHA,),
        forecast_admission_hash=SHA,
        valuation_admission_hash=SHA,
        return_hash=SHA,
        risk_portfolio_hash=SHA,
        decision_admission_hash=SHA,
        decision_revision=1,
        publication_hash=SHA,
        report_hash=SHA,
    )
    assert receipt["schema_version"] == "IIOS-RUN-RECEIPT-0.1"
    assert receipt["run_status"] == "COMPLETE"
    assert len(receipt["receipt_hash"]) == 64


def test_exact_stage_authorization_prevents_direct_decision_execution():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="r4",
        case_id="c4",
        market="HK",
        symbol="700",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    with pytest.raises(ValueError, match="stage authorization failed"):
        o.authorize("r4", Stage.DECISION_PENDING)


def test_non_canonical_direct_execution_is_explicit():
    o = CanonicalResearchOrchestrator()
    o.start(
        run_id="r5",
        case_id="c5",
        market="HK",
        symbol="700",
        cutoff_date="2026-10-07",
        as_of_date="2026-10-07",
        created_at="2026-10-07T00:00:00+00:00",
    )
    state = o.classify_direct_execution_as_non_canonical(
        run_id="r5",
        reason="direct lower-level engine invocation",
    )
    assert state.stage_state == Stage.NON_CANONICAL
    assert state.run_status == RunStatus.NON_CANONICAL


def test_canonical_hash_is_stable():
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})
