from decimal import Decimal
from datetime import datetime
import base64
import hashlib
import json
from jsonschema import Draft202012Validator
from pathlib import Path
import pytest

from iios_mvp import operator_entered_price_decision_input_v01 as operator_price_input
from iios_mvp.b2e_nl_semantic_decision_e2e_v01 import (
    B2EE2EError,
    run_b2e_conformance,
)
from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestInterpreterRegistration,
    RequestInterpreterRegistry,
    RequestIntent,
)
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistration, ProducerRegistry
from iios_mvp.decision_admission import validate_decision_admission_receipt
from tools.core04_final_300750_decision_e2e import build_case, load_inputs, admit_price
from research.b2.company_evidence import REQUIRED_COMPANY_FIELD_GROUPS, build_company_evidence_manifest
from iios_mvp.canonical_run_authority_v01 import run_state_path, CanonicalRunAuthorizationError, _validate_decision_pending_input_refs
from iios_mvp.machine_publication import write_machine_publication
from iios_mvp.investor_review_report_v02 import write_investor_review_report_v02

CREATED = "2026-10-08T00:00:00+00:00"
RAW = "请对宁德时代进行投资决策分析，给出当前价格下是否可买。"
E1 = "a" * 64
E2 = "b" * 64


class FixtureInterpreter:
    interpreter_id = "fixture-b2e-interpreter"
    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = "b2e-fixture-interpreter-0.1"
    policy_version = "IIOS-NL-POLICY-0.1"

    def interpret(self, raw_request: str):
        assert raw_request == RAW
        return RequestIntent("CN-A", "300750", "2026-10-04", "0")


class FixtureSemanticProducer:
    producer_id = "fixture-b2e-semantic"
    producer_type = "LLM_SEMANTIC_PRODUCER"
    producer_version = "b2e-fixture-producer-0.1"
    policy_version = "IIOS-LLM-POLICY-0.1"

    thesis_status = "INTACT"

    def produce(self, request):
        return {
            "core_projection": {
                "status": self.thesis_status,
                "statement": "Semantic-proposed thesis statement.",
                "mechanism": "Semantic-proposed economic mechanism.",
                "key_driver_ids": ["D1", "D2", "D3"],
                "falsifiers": ["driver failure"],
                "monitoring_triggers": ["quarterly review"],
            }
        }


class ForbiddenSemanticProducer(FixtureSemanticProducer):
    producer_id = "fixture-b2e-forbidden"

    def produce(self, request):
        return {"action": "BUY", "semantic_assessment": {"status": "PASS"}}


class NestedForbiddenSemanticProducer(FixtureSemanticProducer):
    producer_id = "fixture-b2e-nested-forbidden"

    def produce(self, request):
        return {
            "semantic_assessment": {
                "thesis": {
                    "decision": {"action": "BUY"},
                    "review": [{"human_approval_required": False}],
                },
                "items": [{"capital_effect": "BUY"}],
            }
        }


def _registries():
    return (
        RequestInterpreterRegistry((
            RequestInterpreterRegistration(
                FixtureInterpreter.interpreter_id,
                FixtureInterpreter.interpreter_type,
                FixtureInterpreter.interpreter_version,
                FixtureInterpreter.policy_version,
            ),
        )),
        ProducerRegistry((
            ProducerRegistration(
                FixtureSemanticProducer.producer_id,
                FixtureSemanticProducer.producer_type,
                FixtureSemanticProducer.producer_version,
                FixtureSemanticProducer.policy_version,
            ),
            ProducerRegistration(
                ForbiddenSemanticProducer.producer_id,
                ForbiddenSemanticProducer.producer_type,
                ForbiddenSemanticProducer.producer_version,
                ForbiddenSemanticProducer.policy_version,
            ),
            ProducerRegistration(
                NestedForbiddenSemanticProducer.producer_id,
                NestedForbiddenSemanticProducer.producer_type,
                NestedForbiddenSemanticProducer.producer_version,
                NestedForbiddenSemanticProducer.policy_version,
            ),
        )),
    )


def _case_and_resolvers():
    core03, core02 = load_inputs()
    price_registry, price_ref = admit_price()
    case = build_case(
        core03=core03,
        core02=core02,
        price_ref=price_ref,
        trust_status="PASS",
        horizon_years="3",
        horizon_override=True,
        horizon_override_basis=["MAJOR_INDUSTRY_LEADER", "MAJOR_INVESTMENT_CYCLE_OR_MAJOR_CAPEX"],
        horizon_rationale="B2-E fixture uses the existing canonical 300750 3Y override.",
    )
    mod = __import__("tools.core04_final_300750_decision_e2e", fromlist=["UPSTREAM_AUTHORITY_REGISTRY", "FORECAST_REGISTRY", "VALUATION_OUTPUT_RESOLVER"])
    return case, price_registry, mod.FORECAST_REGISTRY, mod.UPSTREAM_AUTHORITY_REGISTRY, mod.VALUATION_OUTPUT_RESOLVER


def test_b2e_full_control_plane_e2e():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    result = run_b2e_conformance(
        raw_request=RAW,
        request_id="b2e-request-1",
        run_id="b2e-run-1",
        created_at=CREATED,
        request_interpreter=FixtureInterpreter(),
        request_registry=_registries()[0],
        semantic_producer=FixtureSemanticProducer(),
        producer_registry=_registries()[1],
        company="宁德时代",
        evidence_refs=("E011", "E008"),
        evidence_hashes=(E1, E2),
        artifact_type="THESIS_ASSESSMENT",
        semantic_prompt="Assess the investment thesis from admitted evidence. Do not issue a decision.",
        decision_relevance="Provides semantic thesis context only; canonical Decision Kernel remains authoritative.",
        semantic_facts=({"evidence_id":"E011","statement":"Admitted market evidence exists."},),
        semantic_inferences=({"text":"Thesis context remains subject to canonical gating."},),
        case=case,
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=upstream_registry,
        valuation_output_resolver=valuation_resolver,
    )
    assert result.binding_receipt["status"] == "ADMITTED"
    assert result.binding_receipt["research_case_hash"] == result.request_admission.case_hash
    assert result.binding_receipt["case_hash"] != result.request_admission.case_hash
    assert result.semantic.admission.status == "ADMITTED"
    assert result.binding_receipt["action"] == result.decision_admission["canonical_action"]
    assert result.binding_receipt["human_approval_required"] is True
    assert result.binding_receipt["auto_execution"] is False
    assert result.decision_revision["decision_status"] == "AI_PROPOSED"
    validate_decision_admission_receipt(
        result.decision_admission,
        snapshot={
            "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
            "engine_version": "0.3.0",
            "input": dict(case),
            "decision": result.decision_admission["canonical_decision_projection"],
            "snapshot_hash": result.decision_admission["snapshot_hash"],
        },
    )
    schema = __import__("json").loads((Path(__file__).parents[1] / "schemas/b2e_nl_semantic_decision_e2e_v0.1.schema.json").read_text())
    Draft202012Validator(schema).validate(result.binding_receipt)


def test_persisted_b2e_binds_private_operator_price_reference_and_replays_hashes(tmp_path):
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    evidence_root, manifest, _manifest_path = _admitted_synthetic_manifest(tmp_path, case)
    private_root = tmp_path / "operator-price-private"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    bundle = operator_price_input.create_bundle(
        {
            "schema_version": operator_price_input.SCHEMA,
            "base_case_id": case["case_id"],
            "market": "CN-A",
            "symbol": "300750",
            "exchange": "SZSE",
            "currency": "CNY",
            "observation_date": "2026-09-30",
            "price": "270.00",
            "adjustment_semantics": "UNADJUSTED_CLOSE",
            "quote_timestamp": "2026-09-30T15:00:00+08:00",
            "valid_until": "2026-10-05T18:00:00+08:00",
            "operator_confirmed": True,
            "source_claim": "operator-supplied close; not source verified",
        },
        private_root,
        entered_at=datetime.fromisoformat("2026-10-04T10:00:00+08:00"),
        decision_cutoff_at=datetime.fromisoformat("2026-10-04T10:01:00+08:00"),
    )
    reference = {
        "bundle_id": bundle["bundle_id"],
        "record_sha256": bundle["record_sha256"],
        "receipt_sha256": bundle["receipt_sha256"],
    }
    input_resolver = operator_price_input.FileSystemOperatorPriceInputResolver(private_root)
    run_root = tmp_path / "operator-price-run"
    evidences = manifest["evidence"]
    result = run_b2e_conformance(
        raw_request=RAW,
        request_id="b2e-operator-price-request",
        run_id="b2e-operator-price-run",
        created_at=CREATED,
        request_interpreter=FixtureInterpreter(),
        request_registry=_registries()[0],
        semantic_producer=FixtureSemanticProducer(),
        producer_registry=_registries()[1],
        company="宁德时代",
        evidence_refs=tuple(row["evidence_id"] for row in evidences),
        evidence_hashes=tuple(row["content_sha256"] for row in evidences),
        artifact_type="THESIS_ASSESSMENT",
        semantic_prompt="Assess the thesis from admitted evidence. Do not issue a decision.",
        semantic_facts=tuple({
            "evidence_id": row["evidence_id"],
            "statement": "SYNTHETIC_TEST_ONLY",
        } for row in evidences),
        decision_relevance="Synthetic test of private operator price binding only.",
        case=case,
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=upstream_registry,
        valuation_output_resolver=valuation_resolver,
        operator_price_input_resolver=input_resolver,
        operator_price_input_ref=reference,
        run_root=str(run_root),
        evidence_manifest=manifest,
        evidence_root=str(evidence_root),
    )
    projection = result.decision_admission["canonical_decision_projection"]
    assert result.canonicality_status == "CANONICAL_RUN_IN_PROGRESS"
    assert projection["current_price"] == "270.00"
    assert projection["current_price_input_class"] == "OPERATOR_ATTESTED_MARKET_DATA"
    assert projection["current_price_assurance"] == "OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED"
    assert projection["operator_price_input_ref"] == reference
    assert projection["mie_reference_price_observation_id"] == case["current_price_observation"]["price_observation_id"]
    assert result.binding_receipt["human_approval_required"] is True
    assert result.binding_receipt["auto_execution"] is False

    state = json.loads(run_state_path(run_root, "b2e-operator-price-run").read_text(encoding="utf-8"))
    decision_pending = next(
        row for row in state["envelope"]["stage_receipts"]
        if row["stage_id"] == "DECISION_PENDING"
    )
    assert decision_pending["input_refs"][-2:] == [
        f"operator-price-input-record:{reference['bundle_id']}",
        f"operator-price-input-receipt:{reference['bundle_id']}",
    ]
    assert decision_pending["input_hashes"][-2:] == [
        reference["record_sha256"],
        reference["receipt_sha256"],
    ]


def test_b2e_rejects_operator_price_reference_without_trusted_resolver():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    fake_ref = {
        "bundle_id": "operator-price-" + "a" * 24,
        "record_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
    }
    with pytest.raises(B2EE2EError, match="operator price input reference supplied without trusted resolver"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-no-operator-resolver",
            run_id="b2e-no-operator-resolver",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=FixtureSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011", "E008"),
            evidence_hashes=(E1, E2),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="test",
            decision_relevance="Synthetic negative test.",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
            operator_price_input_ref=fake_ref,
        )


def test_b2e_rejects_conflicting_case_and_request_operator_price_refs(tmp_path):
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    _private_root, reference, resolver = _private_operator_price_bundle(tmp_path, case)
    case["current_price_observation"] = resolver.build_current_price_observation(
        reference,
        case_id=case["case_id"],
        market=case["market"],
        symbol=case["symbol"],
        currency="CNY",
        cutoff_date=__import__("datetime").date.fromisoformat(case["cutoff_date"]),
        mie_reference_price_observation_id=case["current_price_observation"]["price_observation_id"],
    )
    conflict = dict(reference)
    conflict["receipt_sha256"] = "c" * 64

    with pytest.raises(B2EE2EError, match="top-level operator price reference conflicts with case input"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-conflicting-operator-ref",
            run_id="b2e-conflicting-operator-ref",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=FixtureSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011", "E008"),
            evidence_hashes=(E1, E2),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="test",
            decision_relevance="Synthetic negative test.",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
            operator_price_input_resolver=resolver,
            operator_price_input_ref=conflict,
        )


def test_persisted_b2e_blocks_forged_operator_receipt_hash_before_decision(tmp_path):
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    evidence_root, manifest, _manifest_path = _admitted_synthetic_manifest(tmp_path, case)
    _private_root, reference, resolver = _private_operator_price_bundle(tmp_path, case)
    forged = dict(reference)
    forged["receipt_sha256"] = "0" * 64
    run_root = tmp_path / "forged-operator-price-run"
    evidences = manifest["evidence"]

    with pytest.raises(B2EE2EError, match="cannot materialize private operator price input: OPERATOR_PRICE_RECEIPT_SHA256_MISMATCH"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-forged-operator-receipt",
            run_id="b2e-forged-operator-receipt",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=FixtureSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=tuple(row["evidence_id"] for row in evidences),
            evidence_hashes=tuple(row["content_sha256"] for row in evidences),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="test",
            semantic_facts=tuple({"evidence_id": row["evidence_id"], "statement": "SYNTHETIC_TEST_ONLY"} for row in evidences),
            decision_relevance="Synthetic negative test.",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
            operator_price_input_resolver=resolver,
            operator_price_input_ref=forged,
            run_root=str(run_root),
            evidence_manifest=manifest,
            evidence_root=str(evidence_root),
        )

    state = json.loads(run_state_path(run_root, "b2e-forged-operator-receipt").read_text(encoding="utf-8"))
    assert state["envelope"]["run_status"] == "BLOCKED"
    stage_ids = [row["stage_id"] for row in state["envelope"]["stage_receipts"]]
    assert "DECISION_PENDING" not in stage_ids
    assert "DECISION_ADMITTED" not in stage_ids
    assert not list((run_root / "canonical-artifacts").glob("*.canonical-upstream-admissions.json")) if (run_root / "canonical-artifacts").exists() else True


def test_run_authority_rejects_malformed_operator_price_stage_pairs():
    base_refs = ["forecast-id", "valuation-id"]
    base_hashes = ["a" * 64, "b" * 64]
    assert _validate_decision_pending_input_refs({
        "input_refs": base_refs, "input_hashes": base_hashes
    }) == (base_refs, base_hashes)

    bundle_id = "operator-price-" + "c" * 24
    valid_refs = base_refs + [
        f"operator-price-input-record:{bundle_id}",
        f"operator-price-input-receipt:{bundle_id}",
    ]
    valid_hashes = base_hashes + ["c" * 64, "d" * 64]
    assert _validate_decision_pending_input_refs({
        "input_refs": valid_refs, "input_hashes": valid_hashes
    }) == (valid_refs, valid_hashes)

    bad_pairs = [
        (base_refs + [f"operator-price-input-record:{bundle_id}"], base_hashes + ["c" * 64]),
        (base_refs + [f"operator-price-input-record:{bundle_id}", "operator-price-input-receipt:" + "d" * 24], valid_hashes),
        (valid_refs, base_hashes + ["not-a-sha256", "d" * 64]),
    ]
    for refs, hashes in bad_pairs:
        with pytest.raises(CanonicalRunAuthorizationError):
            _validate_decision_pending_input_refs({"input_refs": refs, "input_hashes": hashes})


def test_b2e_nested_semantic_authority_is_blocked_recursively():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    with pytest.raises(B2EE2EError, match="authority fields at output"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-f003-nested",
            run_id="b2e-f003-nested",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=NestedForbiddenSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011",),
            evidence_hashes=(E1,),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="Do not issue a decision.",
            decision_relevance="test",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
        )


def test_b2e_forbidden_semantic_authority_is_blocked():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    with pytest.raises(B2EE2EError, match="decision authority fields"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-request-2",
            run_id="b2e-run-2",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=ForbiddenSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011",),
            evidence_hashes=(E1,),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="Do not issue a decision.",
            decision_relevance="test",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
        )


def test_b2e_semantic_projection_changes_canonical_decision():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    case = dict(case)
    case["trust"] = {"status": "PASS"}

    intact = FixtureSemanticProducer()
    intact.thesis_status = "INTACT"
    broken = FixtureSemanticProducer()
    broken.thesis_status = "BROKEN"

    def run(producer, run_id):
        return run_b2e_conformance(
            raw_request=RAW,
            request_id=run_id,
            run_id=run_id,
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=producer,
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011", "E008"),
            evidence_hashes=(E1, E2),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="Assess thesis.",
            decision_relevance="Semantic thesis proposal only.",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
        )

    intact_result = run(intact, "b2e-causal-intact")
    broken_result = run(broken, "b2e-causal-broken")
    assert intact_result.binding_receipt["semantic_core_projection_hash"]
    assert broken_result.binding_receipt["semantic_core_projection_hash"]
    assert intact_result.binding_receipt["action"] == "REVIEW_REQUIRED"
    assert broken_result.binding_receipt["action"] == "NO-BUY"
    assert intact_result.binding_receipt["action"] != broken_result.binding_receipt["action"]


def test_b2e_forecast_valuation_admission_is_canonical_and_tamper_evident():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    tampered = dict(case)
    tampered["return_gate"] = dict(case["return_gate"])
    tampered["return_gate"]["scenarios"] = dict(case["return_gate"]["scenarios"])
    tampered["return_gate"]["scenarios"]["base"] = dict(case["return_gate"]["scenarios"]["base"])
    tampered["return_gate"]["scenarios"]["base"]["terminal_value_per_share"] = "999.99"

    with pytest.raises(B2EE2EError, match="canonical Forecast/Valuation lineage admission failed"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="b2e-f002-tamper",
            run_id="b2e-f002-tamper",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=FixtureSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011", "E008"),
            evidence_hashes=(E1, E2),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="Assess thesis.",
            decision_relevance="Semantic thesis proposal only.",
            case=tampered,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
        )


def test_b2e_semantic_lineage_is_required():
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    with pytest.raises(ValueError, match="semantic input lineage"):
        from iios_mvp.llm_semantic_workbench_v01 import LLMSemanticWorkbench, SemanticRequest
        from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
        o = CanonicalResearchOrchestrator()
        o.start(run_id="b2e-lineage",case_id=case["case_id"],market=case["market"],symbol=case["symbol"],cutoff_date=case["cutoff_date"],as_of_date=case["as_of_date"],created_at=CREATED)
        o.transition("b2e-lineage", Stage.REQUEST_ADMITTED)
        o.transition("b2e-lineage", Stage.CASE_CREATED)
        o.transition("b2e-lineage", Stage.EVIDENCE_PENDING)
        o.transition("b2e-lineage", Stage.EVIDENCE_ADMITTED, output_refs=("E011",), output_hashes=(E1,))
        o.transition("b2e-lineage", Stage.SEMANTIC_PENDING)
        LLMSemanticWorkbench(orchestrator=o, registry=_registries()[1]).run(
            producer=FixtureSemanticProducer(),
            request=SemanticRequest(
                request_id="bad",run_id="b2e-lineage",case_id=case["case_id"],market="CN-A",symbol="300750",
                company="宁德时代",cutoff_date=case["cutoff_date"],artifact_type="THESIS_ASSESSMENT",
                input_refs=("E011","E008"),input_hashes=(E1,E2),prompt="bad",created_at=CREATED),
            decision_relevance="test",
        )


def _admitted_synthetic_manifest(tmp_path, case):
    """Synthetic exact-byte manifest for control-plane tests only; no real-company claim."""
    root = tmp_path / "evidence-root"
    (root / "raw").mkdir(parents=True)
    rows = []
    raw_artifacts = []
    for index, group in enumerate(REQUIRED_COMPANY_FIELD_GROUPS):
        payload = f"SYNTHETIC_TEST_ONLY:{case['case_id']}:{group}:{index}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        relpath = f"raw/{group}.bin"
        (root / relpath).write_bytes(payload)
        rows.append({
            "evidence_id": f"SYNTH-{group.upper()}",
            "subject_id": case["case_id"],
            "field_id": f"{group}.test_anchor",
            "claim_type": "OBSERVED_FACT",
            "value": "SYNTHETIC_TEST_ONLY_NOT_REAL_FACT",
            "observation_date": "2026-09-30",
            "period": "TEST_PERIOD",
            "published_at": "2026-09-30T15:00:00+08:00",
            "known_at": "2026-09-30T16:00:00+08:00",
            "retrieved_at": CREATED,
            "effective_from": "2026-09-01",
            "effective_to": None,
            "source_ref": f"SYNTHETIC_TEST_ONLY:{group}",
            "source_version": "fixture-v1",
            "source_locator": "test fixture bytes",
            "artifact_id": f"fixture:{group}:{digest[:16]}",
            "content_sha256": digest,
            "capture_sha256": digest,
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
            "transformation": {"type": "DIRECT", "code_ref": None, "code_sha256": None, "formula_id": None},
            "parents": [],
            "quality_notes": ["SYNTHETIC_TEST_ONLY"],
            "license_status": "TEST_ONLY",
        })
        raw_artifacts.append({
            "evidence_id": f"SYNTH-{group.upper()}",
            "relative_path": relpath,
            "expected_size_bytes": len(payload),
            "expected_sha256": digest,
        })
    manifest = build_company_evidence_manifest(
        case_id=str(case["case_id"]),
        market=str(case["market"]),
        symbol=str(case["symbol"]),
        company=str(case["company"]),
        cutoff_date=str(case["cutoff_date"]),
        evidence=rows,
        raw_artifacts=raw_artifacts,
        required_field_groups=list(REQUIRED_COMPANY_FIELD_GROUPS),
        raw_root=root,
    )
    assert manifest["status"] == "PASS", manifest.get("validation_errors")
    path = tmp_path / "B2_COMPANY_EVIDENCE_MANIFEST.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return root, manifest, path


def _private_operator_price_bundle(tmp_path, case):
    root = tmp_path / "operator-price-private"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    bundle = operator_price_input.create_bundle(
        {
            "schema_version": operator_price_input.SCHEMA,
            "base_case_id": case["case_id"],
            "market": "CN-A",
            "symbol": "300750",
            "exchange": "SZSE",
            "currency": "CNY",
            "observation_date": "2026-09-30",
            "price": "270.00",
            "adjustment_semantics": "UNADJUSTED_CLOSE",
            "quote_timestamp": "2026-09-30T15:00:00+08:00",
            "valid_until": "2026-10-05T18:00:00+08:00",
            "operator_confirmed": True,
            "source_claim": "SYNTHETIC_TEST_ONLY_NOT_SOURCE_VERIFIED",
        },
        root,
        entered_at=datetime.fromisoformat("2026-10-04T10:00:00+08:00"),
        decision_cutoff_at=datetime.fromisoformat("2026-10-04T10:01:00+08:00"),
    )
    reference = {
        "bundle_id": bundle["bundle_id"],
        "record_sha256": bundle["record_sha256"],
        "receipt_sha256": bundle["receipt_sha256"],
    }
    resolver = operator_price_input.FileSystemOperatorPriceInputResolver(root)
    return root, reference, resolver


def test_p0_persisted_b2e_blocks_without_b2_evidence_pit_admission(tmp_path):
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    root = tmp_path / "runs"
    with pytest.raises(B2EE2EError, match="B2 Evidence/PIT manifest and raw_root"):
        run_b2e_conformance(
            raw_request=RAW,
            request_id="p0-no-evidence-request",
            run_id="p0-no-evidence-run",
            created_at=CREATED,
            request_interpreter=FixtureInterpreter(),
            request_registry=_registries()[0],
            semantic_producer=FixtureSemanticProducer(),
            producer_registry=_registries()[1],
            company="宁德时代",
            evidence_refs=("E011", "E008"),
            evidence_hashes=(E1, E2),
            artifact_type="THESIS_ASSESSMENT",
            semantic_prompt="test",
            decision_relevance="test",
            case=case,
            current_price_resolver=price_registry,
            independent_forecast_resolver=forecast_registry,
            upstream_authority_resolver=upstream_registry,
            valuation_output_resolver=valuation_resolver,
            run_root=str(root),
        )
    state = json.loads(run_state_path(root, "p0-no-evidence-run").read_text(encoding="utf-8"))
    assert state["envelope"]["run_status"] == "BLOCKED"
    assert not list(root.glob("*.decision.json"))


def test_p0_persisted_b2e_requires_exact_admitted_manifest_and_completes_run(tmp_path):
    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    evidence_root, manifest, manifest_path = _admitted_synthetic_manifest(tmp_path, case)
    evidences = manifest["evidence"]
    refs = tuple(x["evidence_id"] for x in evidences)
    hashes = tuple(x["content_sha256"] for x in evidences)
    run_root = tmp_path / "runs"
    result = run_b2e_conformance(
        raw_request=RAW,
        request_id="p0-full-request",
        run_id="p0-full-run",
        created_at=CREATED,
        request_interpreter=FixtureInterpreter(),
        request_registry=_registries()[0],
        semantic_producer=FixtureSemanticProducer(),
        producer_registry=_registries()[1],
        company="宁德时代",
        evidence_refs=refs,
        evidence_hashes=hashes,
        artifact_type="THESIS_ASSESSMENT",
        semantic_prompt="Assess thesis using admitted evidence. Do not issue a decision.",
        semantic_facts=tuple({"evidence_id": x["evidence_id"], "statement": "SYNTHETIC_TEST_ONLY"} for x in evidences),
        decision_relevance="Synthetic control-plane test only.",
        case=case,
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=upstream_registry,
        valuation_output_resolver=valuation_resolver,
        run_root=str(run_root),
        evidence_manifest=manifest,
        evidence_root=str(evidence_root),
    )
    assert result.canonicality_status == "CANONICAL_RUN_IN_PROGRESS"
    assert result.decision_revision["run_authority_ref"]["run_id"] == "p0-full-run"
    publication_path = write_machine_publication(
        run_root, decision_id=result.decision_revision["decision_id"],
        published_at="2026-10-08T01:00:00+00:00",
    )
    report_paths = write_investor_review_report_v02(
        run_root, publication_path=publication_path,
        generated_at="2026-10-08T02:00:00+00:00",
    )
    receipt_path = run_root / "p0-full-run.run-receipt.json"
    assert all(path.is_file() for path in report_paths)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["run_id"] == "p0-full-run"
    assert receipt["run_status"] == "COMPLETE"
    assert receipt["evidence_manifest_hash"] == manifest["audit"]["manifest_sha256"]
    assert len(receipt["receipt_hash"]) == 64
    from iios_mvp.canonical_run_authority_v01 import validate_complete_run_receipt
    replayed = validate_complete_run_receipt(run_root, "p0-full-run")
    assert replayed == receipt
    receipt_schema = json.loads((Path(__file__).parents[1] / "schemas/iios_run_receipt_v0.2.schema.json").read_text())
    Draft202012Validator(receipt_schema).validate(receipt)
    run_receipt_schema = json.loads((Path(__file__).parents[1] / "schemas/iios_run_receipt_v0.2.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(run_receipt_schema).validate(receipt)


def test_p0_real_catl_manifest_runs_through_revision_publication_report_and_receipt(tmp_path):
    """Positive P0 regression using the repository's real admitted CATL capture bundle.

    The LLM-semantic producer remains a deterministic test double; the case
    identity, B2 manifest, captured bytes, PIT timestamps, market/forecast/
    valuation resolvers and Decision Kernel inputs are the existing real case.
    This verifies persistence/auth plumbing, not semantic model quality.
    """
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (
        repo_root / "evidence" / "real_cases" / "RC-CN-A-300750-20261004"
        / "b2_company_evidence_manifest_v0.1.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # This legacy canonical manifest predates the explicit status envelope.
    # Materialize a fresh admission result from the current independent validator
    # instead of editing the tracked evidence artifact or trusting caller status.
    manifest = dict(manifest)
    manifest["status"] = "PASS"
    manifest["validation_errors"] = []
    from iios_mvp.canonical_evidence_admission_v01 import validate_company_evidence_manifest
    manifest_errors = validate_company_evidence_manifest(
        manifest, raw_root=repo_root, require_raw_verification=True
    )
    assert manifest_errors == [], "; ".join(manifest_errors)

    case, price_registry, forecast_registry, upstream_registry, valuation_resolver = _case_and_resolvers()
    rows = manifest["evidence"]
    refs = tuple(str(x["evidence_id"]) for x in rows)
    hashes = tuple(str(x["content_sha256"]) for x in rows)
    run_root = tmp_path / "runs-real-catl"
    result = run_b2e_conformance(
        raw_request=RAW,
        request_id="p0-real-catl-request",
        run_id="p0-real-catl-run",
        created_at=CREATED,
        request_interpreter=FixtureInterpreter(),
        request_registry=_registries()[0],
        semantic_producer=FixtureSemanticProducer(),
        producer_registry=_registries()[1],
        company="宁德时代",
        evidence_refs=refs,
        evidence_hashes=hashes,
        artifact_type="THESIS_ASSESSMENT",
        semantic_prompt="Assess the admitted CATL evidence. Do not issue an action.",
        semantic_facts=tuple({
            "evidence_id": row["evidence_id"],
            "statement": f"Admitted source-record anchor for {row['field_id']}.",
        } for row in rows),
        decision_relevance="Existing real-case evidence manifest and current PIT admission only.",
        case=case,
        current_price_resolver=price_registry,
        independent_forecast_resolver=forecast_registry,
        upstream_authority_resolver=upstream_registry,
        valuation_output_resolver=valuation_resolver,
        run_root=str(run_root),
        evidence_manifest=manifest,
        evidence_root=str(repo_root),
    )
    assert result.canonicality_status == "CANONICAL_RUN_IN_PROGRESS"
    assert result.request_admission.case_id == manifest["case_id"]
    assert result.decision_revision["run_authority_ref"]["run_id"] == "p0-real-catl-run"
    for declaration in manifest["raw_artifacts"]:
        persisted_raw = run_root / "canonical-evidence" / declaration["relative_path"]
        assert persisted_raw.is_file()
        assert hashlib.sha256(persisted_raw.read_bytes()).hexdigest() == declaration["expected_sha256"]

    publication_path = write_machine_publication(
        run_root,
        decision_id=result.decision_revision["decision_id"],
        published_at="2026-10-08T03:00:00+00:00",
    )
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    assert publication["canonical_run_ref"]["run_id"] == "p0-real-catl-run"
    report_paths = write_investor_review_report_v02(
        run_root,
        publication_path=publication_path,
        generated_at="2026-10-08T04:00:00+00:00",
    )
    assert all(path.is_file() for path in report_paths)
    from iios_mvp.canonical_run_authority_v01 import validate_complete_run_receipt
    receipt = validate_complete_run_receipt(run_root, "p0-real-catl-run")
    assert receipt["run_status"] == "COMPLETE"
    assert receipt["case_id"] == manifest["case_id"]
    assert receipt["evidence_manifest_hash"] == manifest["audit"]["manifest_sha256"]
    assert receipt["publication_hash"] == publication["publication_hash"]
