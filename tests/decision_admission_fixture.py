from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def build_fixture_admission_receipt(
    *,
    snapshot: Mapping[str, Any],
    canonical_decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = snapshot["decision"] if canonical_decision is None else canonical_decision
    core = {
        "schema_version": "IIOS-DECISION-ADMISSION-0.1",
        "status": "ADMITTED",
        "admission_method": "CANONICAL_DECIDE_V03_REEXECUTED",
        "contract_version": "IIOS-INVESTMENT-CORE-0.3",
        "engine_version": "0.3.0",
        "case_id": str(snapshot["input"]["case_id"]),
        "market": str(snapshot["input"]["market"]).upper(),
        "symbol": str(snapshot["input"]["symbol"]).upper(),
        "company": str(snapshot["input"]["company"]),
        "cutoff_date": str(snapshot["input"]["cutoff_date"]),
        "snapshot_hash": str(snapshot["snapshot_hash"]),
        "canonical_decision_keys": sorted(decision.keys()),
        "canonical_decision_projection": dict(decision),
        "canonical_decision_hash": _sha(decision),
        "canonical_action": str(decision["action"]).upper(),
        "canonical_decision_status": str(decision.get("decision_status", "READY")),
        "canonical_new_capital_allowed": bool(
            (decision.get("gates") or {}).get("new_capital_allowed", False)
        ),
    }
    return {**core, "admission_record_hash": _sha(core)}


def prepare_authorized_test_run(
    *,
    root: str,
    run_id: str,
    snapshot: Mapping[str, Any],
    decision_admission: Mapping[str, Any],
) -> None:
    """Seed a complete synthetic stage chain for downstream writer unit tests only.

    This helper never admits real evidence and MUST NOT be used by production code
    or by negative authorization tests. It tests publication/report mechanics
    after the input gates are represented as already admitted fixtures.
    """
    from iios_mvp.canonical_research_orchestrator import Stage
    from iios_mvp.canonical_run_authority_v01 import (
        PersistedCanonicalResearchOrchestrator, run_state_path,
        validate_run_state_record,
    )

    existing_path = run_state_path(root, run_id)
    if existing_path.exists():
        existing = validate_run_state_record(json.loads(existing_path.read_text(encoding="utf-8")))
        env = existing["envelope"]
        expected = snapshot["input"]
        if (
            env["case_id"] != expected["case_id"]
            or env["market"] != str(expected["market"]).upper()
            or env["symbol"] != str(expected["symbol"]).upper()
            or env["cutoff_date"] != expected["cutoff_date"]
        ):
            raise AssertionError("existing synthetic run fixture identity mismatch")
        decision_stages = [x for x in env["stage_receipts"] if x["stage_id"] == Stage.DECISION_ADMITTED.value]
        if not decision_stages or snapshot["snapshot_hash"] not in decision_stages[-1]["output_hashes"] or decision_admission["admission_record_hash"] not in decision_stages[-1]["output_hashes"]:
            raise AssertionError("existing synthetic run fixture is not bound to this snapshot/admission")
        return

    case = snapshot["input"]
    market = str(case["market"]).upper()
    symbol = str(case["symbol"]).upper()
    case_id = str(case["case_id"])
    company = str(case["company"])
    cutoff = str(case["cutoff_date"])
    as_of = str(case.get("as_of_date") or cutoff)
    request_id = f"TEST-REQUEST-{run_id}"
    raw_request = f"TEST ONLY — synthetic admitted run for {run_id}"
    raw_request_sha256 = hashlib.sha256(raw_request.encode("utf-8")).hexdigest()
    normalized_request = {
        "market": market,
        "symbol": symbol,
        "as_of_date": as_of,
        "current_position_pct": "0",
        "request_type": "INVESTMENT_DECISION",
    }
    receipt_core = {
        "schema_version": "IIOS-NL-REQUEST-ADMISSION-0.1",
        "request_id": request_id,
        "run_id": run_id,
        "raw_request_sha256": raw_request_sha256,
        "normalized_request_sha256": _sha(normalized_request),
        "normalized_request": normalized_request,
        "case_id": case_id,
        "case_hash": _sha({"test_case_id": case_id, "cutoff_date": cutoff}),
        "market": market,
        "symbol": symbol,
        "as_of_date": as_of,
        "cutoff_date": cutoff,
        "request_type": "INVESTMENT_DECISION",
        "interpreter_type": "HUMAN_EXPERT_ADJUDICATION",
        "interpreter_id": "TEST_FIXTURE_ONLY",
        "interpreter_version": "0.0-test",
        "policy_version": "TEST_ONLY",
        "orchestrator_version": "IIOS-CANONICAL-RESEARCH-ORCHESTRATOR-0.1",
        "status": "ADMITTED",
        "created_at": "2026-10-09T00:00:00+00:00",
    }
    request_receipt = {**receipt_core, "receipt_hash": _sha(receipt_core)}
    case_hash = str(request_receipt["case_hash"])
    orchestrator = PersistedCanonicalResearchOrchestrator(root)
    orchestrator.bind_request(
        run_id=run_id, raw_request=raw_request, request_receipt=request_receipt
    )
    orchestrator.start(
        run_id=run_id,
        case_id=case_id,
        market=market,
        symbol=symbol,
        cutoff_date=cutoff,
        as_of_date=as_of,
        request_type="INVESTMENT_DECISION",
        research_case_hash=case_hash,
        created_at="2026-10-09T00:00:00+00:00",
    )
    orchestrator.transition(
        run_id, Stage.REQUEST_ADMITTED,
        output_refs=(request_id,), output_hashes=(request_receipt["receipt_hash"],),
        producer_type="HUMAN_EXPERT_ADJUDICATION", producer_version="0.0-test",
        created_at="2026-10-09T00:00:01+00:00",
    )
    orchestrator.transition(
        run_id, Stage.CASE_CREATED,
        output_refs=(case_id,), output_hashes=(case_hash,),
        producer_type="CODE", producer_version="test-case",
        created_at="2026-10-09T00:00:02+00:00",
    )
    orchestrator.transition(run_id, Stage.EVIDENCE_PENDING, created_at="2026-10-09T00:00:03+00:00")
    evidence_hash = _sha({"test-evidence": case_id})
    orchestrator.transition(
        run_id, Stage.EVIDENCE_ADMITTED,
        output_refs=("test-evidence-manifest",), output_hashes=(evidence_hash,),
        producer_type="CODE", producer_version="test-evidence",
        created_at="2026-10-09T00:00:04+00:00",
    )
    orchestrator.transition(run_id, Stage.SEMANTIC_PENDING, created_at="2026-10-09T00:00:05+00:00")
    semantic_hash = _sha({"test-semantic": case_id})
    orchestrator.transition(
        run_id, Stage.SEMANTIC_ADMITTED,
        output_refs=("test-semantic-artifact",), output_hashes=(semantic_hash,),
        producer_type="LLM_SEMANTIC_PRODUCER", producer_version="0.0-test",
        created_at="2026-10-09T00:00:06+00:00",
    )
    orchestrator.transition(run_id, Stage.FORECAST_PENDING, created_at="2026-10-09T00:00:07+00:00")
    forecast_hash = _sha({"test-forecast": case_id})
    orchestrator.transition(
        run_id, Stage.FORECAST_ADMITTED,
        output_refs=("test-forecast-admission",), output_hashes=(forecast_hash,),
        producer_type="CODE", producer_version="test-forecast",
        created_at="2026-10-09T00:00:08+00:00",
    )
    orchestrator.transition(run_id, Stage.VALUATION_PENDING, created_at="2026-10-09T00:00:09+00:00")
    valuation_hash = _sha({"test-valuation": case_id})
    orchestrator.transition(
        run_id, Stage.VALUATION_ADMITTED,
        output_refs=("test-valuation-admission",), output_hashes=(valuation_hash,),
        producer_type="CODE", producer_version="test-valuation",
        created_at="2026-10-09T00:00:10+00:00",
    )
    orchestrator.transition(run_id, Stage.DECISION_PENDING, created_at="2026-10-09T00:00:11+00:00")
    decision = snapshot["decision"]
    return_hash = _sha(decision.get("return_metrics") or {})
    risk_hash = _sha(decision.get("risk_portfolio_contract") or decision.get("positioning_sizing") or {})
    orchestrator.transition(
        run_id, Stage.DECISION_ADMITTED,
        output_refs=("decision_snapshot", "decision_admission", "return_metrics", "risk_portfolio"),
        output_hashes=(
            str(snapshot["snapshot_hash"]),
            str(decision_admission["admission_record_hash"]),
            return_hash,
            risk_hash,
        ),
        producer_type="CODE", producer_version="test-decision",
        created_at="2026-10-09T00:00:12+00:00",
    )
