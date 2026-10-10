from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
    decision = snapshot["decision"]
    # Synthetic exact-byte B2 manifest for lifecycle writer tests. These bytes
    # are explicitly not company facts and MUST NOT be used outside tests.
    from research.b2.company_evidence import (
        REQUIRED_COMPANY_FIELD_GROUPS,
        build_company_evidence_manifest,
    )
    root_path = Path(root).resolve()
    evidence_root = root_path / "canonical-evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    synthetic_evidence = []
    synthetic_raw_artifacts = []
    for index, group in enumerate(REQUIRED_COMPANY_FIELD_GROUPS):
        raw_bytes = f"SYNTHETIC_TEST_ONLY:{run_id}:{case['case_id']}:{group}:{index}".encode("utf-8")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        relative_path = f"raw/{run_id}/{group}.bin"
        raw_path = evidence_root / relative_path
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_path.exists():
            if raw_path.read_bytes() != raw_bytes:
                raise AssertionError("synthetic raw evidence fixture collision")
        else:
            raw_path.write_bytes(raw_bytes)
        synthetic_evidence.append({
            "evidence_id": f"TEST-{run_id}-{group}",
            "subject_id": str(case["case_id"]),
            "field_id": f"{group}.test_anchor",
            "claim_type": "OBSERVED_FACT",
            "value": "SYNTHETIC_TEST_ONLY_NOT_REAL_FACT",
            "observation_date": "2026-09-30",
            "period": "TEST_PERIOD",
            "published_at": "2026-09-30T15:00:00+08:00",
            "known_at": "2026-09-30T16:00:00+08:00",
            "retrieved_at": "2026-10-09T00:00:00+00:00",
            "effective_from": "2026-09-01",
            "effective_to": None,
            "source_ref": f"SYNTHETIC_TEST_ONLY:{group}",
            "source_version": "test-fixture-v1",
            "source_locator": "Synthetic test fixture bytes",
            "artifact_id": f"synthetic-test:{group}:{digest[:16]}",
            "content_sha256": digest,
            "capture_sha256": digest,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
            "parents": [],
            "quality_notes": ["SYNTHETIC_TEST_ONLY_NOT_COMPANY_EVIDENCE"],
            "license_status": "TEST_ONLY",
        })
        synthetic_raw_artifacts.append({
            "evidence_id": f"TEST-{run_id}-{group}",
            "relative_path": relative_path,
            "expected_size_bytes": len(raw_bytes),
            "expected_sha256": digest,
        })
    manifest = build_company_evidence_manifest(
        case_id=str(case["case_id"]),
        market=str(case["market"]).upper(),
        symbol=str(case["symbol"]),
        company=str(case["company"]),
        cutoff_date=str(case["cutoff_date"]),
        evidence=synthetic_evidence,
        raw_artifacts=synthetic_raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=evidence_root,
    )
    if manifest.get("status") != "PASS":
        raise AssertionError("synthetic B2 manifest fixture failed: " + "; ".join(manifest.get("validation_errors") or []))
    manifest_hash = str(manifest["audit"]["manifest_sha256"])
    manifest_path = root_path / "canonical-artifacts" / f"{_sha(manifest)}.evidence-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    if manifest_path.exists():
        if manifest_path.read_bytes() != manifest_bytes:
            raise AssertionError("synthetic Evidence Manifest fixture collision")
    else:
        manifest_path.write_bytes(manifest_bytes)

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
    evidence_ids = [str(x["evidence_id"]) for x in manifest["evidence"]]
    evidence_hashes = [str(x["content_sha256"]) for x in manifest["evidence"]]
    orchestrator.transition(
        run_id, Stage.EVIDENCE_ADMITTED,
        output_refs=(f"evidence-manifest:{manifest_hash}", *evidence_ids),
        output_hashes=(manifest_hash, *evidence_hashes),
        producer_type="CODE", producer_version="test-evidence",
        created_at="2026-10-09T00:00:04+00:00",
    )
    orchestrator.transition(run_id, Stage.SEMANTIC_PENDING, created_at="2026-10-09T00:00:05+00:00")
    from iios_mvp.semantic_producer_admission_v01 import (
        ProducerRegistration, ProducerRegistry, SemanticAdmissionContext,
        build_semantic_artifact, build_producer_receipt, admit_semantic_artifact,
    )
    from iios_mvp.canonical_investment_admission_v01 import (
        build_canonical_investment_admission,
    )
    from iios_mvp.forecast_valuation_return_lineage_v01 import (
        CANONICAL_VALUATION_OUTPUT_VERSION,
    )

    # These objects are valid, fully bound TEST-ONLY records. They are persisted
    # so downstream writer tests exercise byte reopening, schema checks and hash
    # binding instead of relying on stage-ID/hash strings alone.
    producer_id = "TEST_FIXTURE_ONLY"
    producer_version = "0.0-test"
    policy_version = "TEST_ONLY"
    artifact_type = "THESIS_ASSESSMENT"
    semantic_context = SemanticAdmissionContext(
        case_id=case_id,
        market=market,
        symbol=symbol,
        company=company,
        cutoff_date=cutoff,
        artifact_type=artifact_type,
        input_refs=tuple(evidence_ids),
        input_hashes=tuple(evidence_hashes),
        producer_id=producer_id,
        producer_version=producer_version,
        producer_type="LLM_SEMANTIC_PRODUCER",
        policy_version=policy_version,
    )
    semantic_artifact = build_semantic_artifact(
        artifact_id=f"TEST-SEMANTIC-{run_id}",
        artifact_type=artifact_type,
        context=semantic_context,
        output={"summary": "SYNTHETIC_TEST_ONLY_NOT_A_COMPANY_FACT"},
        decision_relevance="TEST_ONLY_AUTHORIZATION_MECHANICS",
        created_at=f"{cutoff}T00:00:05+00:00",
    )
    semantic_producer_receipt = build_producer_receipt(
        receipt_id=f"TEST-SEMANTIC-RECEIPT-{run_id}",
        artifact=semantic_artifact,
        stage_id=artifact_type,
        created_at=f"{cutoff}T00:00:05+00:00",
    )
    semantic_registry = ProducerRegistry((
        ProducerRegistration(
            producer_id=producer_id,
            producer_type="LLM_SEMANTIC_PRODUCER",
            producer_version=producer_version,
            policy_version=policy_version,
        ),
    ))
    semantic_admission_obj = admit_semantic_artifact(
        semantic_artifact,
        semantic_producer_receipt,
        context=semantic_context,
        registry=semantic_registry,
    )
    semantic_admission = dict(semantic_admission_obj.__dict__)
    orchestrator.transition(
        run_id, Stage.SEMANTIC_ADMITTED,
        output_refs=(semantic_artifact["artifact_id"],),
        output_hashes=(semantic_artifact["artifact_hash"],),
        input_refs=tuple(evidence_ids),
        input_hashes=tuple(evidence_hashes),
        producer_type="LLM_SEMANTIC_PRODUCER",
        producer_version=producer_version,
        created_at=f"{cutoff}T00:00:06+00:00",
    )

    from iios_mvp.canonical_independent_forecast import (
        CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA,
    )
    forecast_core = {
        "admission_schema": CANONICAL_INDEPENDENT_FORECAST_ADMISSION_SCHEMA,
        "status": "ADMITTED",
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "cutoff_date": cutoff,
        "forecast_id": f"TEST-FORECAST-{run_id}",
        "forecast_version": "test-fixture-v1",
        "model_version": "test-fixture-model-v1",
        "variable_id": "intrinsic_value_growth_proxy",
        "value": "0.1",
        "unit": "fraction",
        "basis": "SYNTHETIC_TEST_ONLY",
        "horizon_years": "1",
        "forecast_origin": f"{cutoff}T00:00:00+00:00",
        "known_at": f"{cutoff}T00:00:00+00:00",
        "prepared_without_current_price": True,
        "evidence_ids": list(evidence_ids),
    }
    forecast_record = {
        **forecast_core,
        "admission_record_hash": _sha(forecast_core),
    }
    forecast_ref = {
        "forecast_id": forecast_record["forecast_id"],
        "admission_record_hash": forecast_record["admission_record_hash"],
    }
    orchestrator.transition(run_id, Stage.FORECAST_PENDING, created_at=f"{cutoff}T00:00:07+00:00")
    orchestrator.transition(
        run_id, Stage.FORECAST_ADMITTED,
        output_refs=(forecast_ref["forecast_id"],),
        output_hashes=(forecast_ref["admission_record_hash"],),
        producer_type="CODE",
        producer_version="IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.1",
        created_at=f"{cutoff}T00:00:08+00:00",
    )

    valuation_output_core = {
        "schema_version": CANONICAL_VALUATION_OUTPUT_VERSION,
        "valuation_id": f"TEST-VALUATION-OUTPUT-{run_id}",
        "valuation_version": "test-fixture-v1",
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "company": company,
        "cutoff_date": cutoff,
        "forecast_ref": forecast_ref,
        "horizon_years": "1",
        "reference_value_per_share": "10",
        "scenarios": {
            "bear": {"probability": "0.25", "value_per_share": "8", "cash_distributions_per_share": "0"},
            "base": {"probability": "0.50", "value_per_share": "10", "cash_distributions_per_share": "0"},
            "bull": {"probability": "0.25", "value_per_share": "14", "cash_distributions_per_share": "0"},
        },
        "evidence_ids": list(evidence_ids),
    }
    valuation_output = {
        **valuation_output_core,
        "output_hash": _sha(valuation_output_core),
    }
    valuation_admission_obj = build_canonical_investment_admission(
        admission_id=f"TEST-VALUATION-ADMISSION-{run_id}",
        domain="VALUATION",
        case_id=case_id,
        market=market,
        symbol=symbol,
        company=company,
        cutoff_date=cutoff,
        domain_status="PASS",
        source_record_id=valuation_output["valuation_id"],
        source_record_hash=valuation_output["output_hash"],
        output_hash=valuation_output["output_hash"],
        producer_version="test-fixture-v1",
        evidence_ids=evidence_ids,
        admitted_at=f"{cutoff}T00:00:09+00:00",
    )
    valuation_admission = valuation_admission_obj.to_dict()
    valuation_ref = valuation_admission_obj.reference().to_dict()
    orchestrator.transition(run_id, Stage.VALUATION_PENDING, created_at=f"{cutoff}T00:00:09+00:00")
    orchestrator.transition(
        run_id, Stage.VALUATION_ADMITTED,
        output_refs=(valuation_ref["admission_id"],),
        output_hashes=(valuation_ref["admission_record_hash"],),
        producer_type="CODE",
        producer_version="IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.1",
        created_at=f"{cutoff}T00:00:10+00:00",
    )
    orchestrator.transition(
        run_id, Stage.DECISION_PENDING,
        input_refs=(forecast_ref["forecast_id"], valuation_ref["admission_id"]),
        input_hashes=(forecast_ref["admission_record_hash"], valuation_ref["admission_record_hash"]),
        created_at=f"{cutoff}T00:00:11+00:00",
    )

    def persist_artifact(suffix, payload):
        raw = _canonical(payload).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        path = root_path / "canonical-artifacts" / f"{digest}.{suffix}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != raw:
            raise AssertionError(f"synthetic {suffix} artifact collision")
        if not path.exists():
            path.write_bytes(raw)
        return digest

    for suffix, payload in (
        ("semantic-artifact", semantic_artifact),
        ("semantic-producer-receipt", semantic_producer_receipt),
        ("semantic-admission", semantic_admission),
        ("forecast-admission", forecast_record),
        ("valuation-admission", valuation_admission),
        ("valuation-output", valuation_output),
    ):
        persist_artifact(suffix, payload)

    return_metrics = decision.get("return_metrics") or {}
    risk_portfolio = decision.get("risk_portfolio_contract") or decision.get("positioning_sizing") or {}
    validated_lineage = {
        "status": "PASS",
        "lineage_version": "IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.1",
        "canonical_forecast_ref": forecast_ref,
        "canonical_valuation_ref": valuation_ref,
        "forecast_id": forecast_record["forecast_id"],
        "forecast_version": forecast_record["forecast_version"],
        "valuation_id": valuation_output["valuation_id"],
        "valuation_version": valuation_output["valuation_version"],
        "valuation_primary_model": "TEST_FIXTURE_ONLY",
        "horizon_years": "1",
        "reference_value_per_share": "10",
        "binding": "FORECAST_REF_EQUALITY_AND_CANONICAL_VALUATION_SCENARIO_EQUALITY",
        "valuation_admission_record": valuation_admission,
    }
    upstream_core = {
        "schema_version": "IIOS-CANONICAL-UPSTREAM-ADMISSIONS-0.1",
        "run_id": run_id,
        "case_id": case_id,
        "market": market,
        "symbol": symbol,
        "company": company,
        "cutoff_date": cutoff,
        "semantic_artifact": semantic_artifact,
        "semantic_producer_receipt": semantic_producer_receipt,
        "semantic_admission": semantic_admission,
        "canonical_forecast_ref": forecast_ref,
        "forecast_record": forecast_record,
        "canonical_valuation_ref": valuation_ref,
        "valuation_admission_record": valuation_admission,
        "valuation_output": valuation_output,
        "validated_lineage": validated_lineage,
    }
    upstream_bundle = {**upstream_core, "bundle_hash": _sha(upstream_core)}
    bundle_bytes = _canonical(upstream_bundle).encode("utf-8")
    bundle_digest = hashlib.sha256(bundle_bytes).hexdigest()
    bundle_path = root_path / "canonical-artifacts" / f"{bundle_digest}.canonical-upstream-admissions.json"
    if bundle_path.exists() and bundle_path.read_bytes() != bundle_bytes:
        raise AssertionError("synthetic upstream admission bundle collision")
    if not bundle_path.exists():
        bundle_path.write_bytes(bundle_bytes)

    orchestrator.transition(
        run_id, Stage.DECISION_ADMITTED,
        output_refs=(
            "decision_snapshot", "decision_admission", "return_metrics", "risk_portfolio",
            f"canonical-upstream-admissions:{bundle_digest}",
        ),
        output_hashes=(
            str(snapshot["snapshot_hash"]),
            str(decision_admission["admission_record_hash"]),
            _sha(return_metrics),
            _sha(risk_portfolio),
            bundle_digest,
        ),
        input_refs=(semantic_artifact["artifact_id"],),
        input_hashes=(semantic_artifact["artifact_hash"],),
        producer_type="CODE",
        producer_version="test-decision",
        created_at=f"{cutoff}T00:00:12+00:00",
    )
