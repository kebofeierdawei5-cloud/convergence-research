import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestInterpreterRegistration,
    RequestInterpreterRegistry,
    RequestIntent,
    admit_natural_language_request,
)
from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage, canonical_hash
from iios_mvp.semantic_producer_admission_v01 import (
    ProducerRegistration,
    ProducerRegistry,
    SemanticAdmissionContext,
    build_semantic_artifact,
)
from iios_mvp.external_semantic_provider_admission_v01 import (
    EXTERNAL_SEMANTIC_RECEIPT_SCHEMA_VERSION,
    ExternalProviderTrustRegistration,
    ExternalProviderTrustRegistry,
    ExternalSemanticAdmissionError,
    admit_external_signed_semantic_artifact,
)


SEED = b"0123456789abcdef0123456789abcdef"
PRIVATE = Ed25519PrivateKey.from_private_bytes(SEED)
PUBLIC_B64 = base64.b64encode(PRIVATE.public_key().public_bytes_raw()).decode()
PRODUCER_ID = "signed-provider-fixture-0.1"
PRODUCER_VERSION = "provider-adapter-0.1"
POLICY = "IIOS-LLM-POLICY-0.1"
EVIDENCE_HASH = "a" * 64
EVIDENCE_HASH_2 = "b" * 64


class FixtureInterpreter:
    interpreter_id = "fixture-interpreter-b2c"
    interpreter_type = "LLM_REQUEST_INTERPRETER"
    interpreter_version = "interpreter-0.1"
    policy_version = "IIOS-NL-POLICY-0.1"

    def interpret(self, raw_request: str):
        return RequestIntent("CN-A", "002001", "2026-10-07", "0")


def make_registries():
    return (
        RequestInterpreterRegistry((RequestInterpreterRegistration(
            FixtureInterpreter.interpreter_id, FixtureInterpreter.interpreter_type,
            FixtureInterpreter.interpreter_version, FixtureInterpreter.policy_version
        ),)),
        ProducerRegistry((ProducerRegistration(
            PRODUCER_ID, "LLM_SEMANTIC_PRODUCER", PRODUCER_VERSION, POLICY
        ),)),
        ExternalProviderTrustRegistry((ExternalProviderTrustRegistration(
            "key-1", PRODUCER_ID, "LLM_SEMANTIC_PRODUCER", PRODUCER_VERSION, POLICY, PUBLIC_B64
        ),)),
    )


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def make_end_to_end():
    o = CanonicalResearchOrchestrator()
    iregistry, pregistry, xregistry = make_registries()
    entry = admit_natural_language_request(
        orchestrator=o, registry=iregistry, interpreter=FixtureInterpreter(),
        request_id="nl-b2c", run_id="run-b2c",
        raw_request="请判断002001是否值得买入。", created_at="2026-10-08T00:00:00+00:00",
    )
    o.transition("run-b2c", Stage.EVIDENCE_PENDING, created_at="2026-10-08T00:00:00+00:00")
    o.transition("run-b2c", Stage.EVIDENCE_ADMITTED, output_refs=("E001","E002"), output_hashes=(EVIDENCE_HASH,EVIDENCE_HASH_2), created_at="2026-10-08T00:00:00+00:00")
    o.transition("run-b2c", Stage.SEMANTIC_PENDING, created_at="2026-10-08T00:00:00+00:00")
    context = SemanticAdmissionContext(
        case_id=entry.case_id, market="CN-A", symbol="002001", company="浙江新和成股份有限公司",
        cutoff_date="2026-10-07", artifact_type="QUALITY_ASSESSMENT",
        input_refs=("E001","E002"), input_hashes=(EVIDENCE_HASH,EVIDENCE_HASH_2),
        producer_id=PRODUCER_ID, producer_version=PRODUCER_VERSION,
        producer_type="LLM_SEMANTIC_PRODUCER", policy_version=POLICY,
    )
    artifact = build_semantic_artifact(
        artifact_id="provider-artifact",
        artifact_type="QUALITY_ASSESSMENT",
        context=context,
        output={"status":"CONDITIONAL","reason":"fixture"},
        decision_relevance="test",
        created_at="2026-10-08T00:00:00+00:00",
    )
    core = {
        "schema_version": EXTERNAL_SEMANTIC_RECEIPT_SCHEMA_VERSION,
        "attestation_id": "att-1",
        "request_id": "nl-b2c",
        "run_id": "run-b2c",
        "raw_request_sha256": entry.request_receipt["raw_request_sha256"],
        "case_id": entry.case_id,
        "cutoff_date": "2026-10-07",
        "producer_type": "LLM_SEMANTIC_PRODUCER",
        "producer_id": PRODUCER_ID,
        "producer_version": PRODUCER_VERSION,
        "policy_version": POLICY,
        "artifact_hash": artifact["artifact_hash"],
        "input_refs": ["E001","E002"],
        "input_hashes": [EVIDENCE_HASH,EVIDENCE_HASH_2],
        "public_key_id": "key-1",
        "signature_algorithm": "Ed25519",
        "signature_b64": "",
        "status": "SIGNED",
        "created_at": "2026-10-08T00:00:00+00:00",
    }
    signature = PRIVATE.sign(canonical_bytes({k:v for k,v in core.items() if k!="signature_b64"}))
    attestation = {
        **core,
        "signature_b64": base64.b64encode(signature).decode(),
    }
    attestation = {
        **attestation,
        "attestation_hash": canonical_hash(attestation),
    }
    return o, pregistry, xregistry, entry, artifact, attestation


def test_signed_external_receipt_full_conformance():
    o, pregistry, xregistry, entry, artifact, attestation = make_end_to_end()
    result = admit_external_signed_semantic_artifact(
        orchestrator=o,
        artifact=artifact,
        attestation=attestation,
        run_id="run-b2c",
        request_id="nl-b2c",
        raw_request_sha256=entry.request_receipt["raw_request_sha256"],
        producer_registry=pregistry,
        external_registry=xregistry,
        created_at="2026-10-08T00:00:00+00:00",
    )
    assert result.status == "ADMITTED"
    assert result.semantic_admission.status == "ADMITTED"
    assert result.external_receipt_hash == attestation["attestation_hash"]
    assert o.get("run-b2c").stage_state == Stage.SEMANTIC_ADMITTED


def test_tampered_signature_is_blocked():
    o, pregistry, xregistry, entry, artifact, attestation = make_end_to_end()
    tampered = dict(attestation)
    tampered["signature_b64"] = base64.b64encode(b"bad").decode()
    # Re-seal attestation hash to isolate signature verification.
    tampered["attestation_hash"] = canonical_hash({k:v for k,v in tampered.items() if k!="attestation_hash"})
    with pytest.raises(ExternalSemanticAdmissionError, match="signature verification failed"):
        admit_external_signed_semantic_artifact(
            orchestrator=o, artifact=artifact, attestation=tampered,
            run_id="run-b2c", request_id="nl-b2c",
            raw_request_sha256=entry.request_receipt["raw_request_sha256"],
            producer_registry=pregistry, external_registry=xregistry,
            created_at="2026-10-08T00:00:00+00:00",
        )


def test_untrusted_key_is_blocked():
    o, pregistry, xregistry, entry, artifact, attestation = make_end_to_end()
    tampered = dict(attestation)
    tampered["public_key_id"] = "untrusted"
    tampered["attestation_hash"] = canonical_hash({k:v for k,v in tampered.items() if k!="attestation_hash"})
    with pytest.raises(ExternalSemanticAdmissionError, match="public key is not trusted"):
        admit_external_signed_semantic_artifact(
            orchestrator=o, artifact=artifact, attestation=tampered,
            run_id="run-b2c", request_id="nl-b2c",
            raw_request_sha256=entry.request_receipt["raw_request_sha256"],
            producer_registry=pregistry, external_registry=xregistry,
            created_at="2026-10-08T00:00:00+00:00",
        )


def test_raw_request_hash_binding_is_required():
    o, pregistry, xregistry, entry, artifact, attestation = make_end_to_end()
    with pytest.raises(ExternalSemanticAdmissionError, match="raw request hash mismatch"):
        admit_external_signed_semantic_artifact(
            orchestrator=o, artifact=artifact, attestation=attestation,
            run_id="run-b2c", request_id="nl-b2c",
            raw_request_sha256="c"*64,
            producer_registry=pregistry, external_registry=xregistry,
            created_at="2026-10-08T00:00:00+00:00",
        )


def test_artifact_hash_binding_is_required():
    o, pregistry, xregistry, entry, artifact, attestation = make_end_to_end()
    tampered = dict(attestation)
    tampered["artifact_hash"] = "d"*64
    tampered["attestation_hash"] = canonical_hash({k:v for k,v in tampered.items() if k!="attestation_hash"})
    with pytest.raises(ExternalSemanticAdmissionError, match="artifact_hash mismatch"):
        admit_external_signed_semantic_artifact(
            orchestrator=o, artifact=artifact, attestation=tampered,
            run_id="run-b2c", request_id="nl-b2c",
            raw_request_sha256=entry.request_receipt["raw_request_sha256"],
            producer_registry=pregistry, external_registry=xregistry,
            created_at="2026-10-08T00:00:00+00:00",
        )


def test_schema_validation():
    _, _, _, _, _, attestation = make_end_to_end()
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "external_semantic_provider_receipt_v0.1.schema.json").read_text())
    Draft202012Validator(schema).validate(attestation)


def test_non_llm_provider_cannot_register():
    with pytest.raises(ValueError, match="must be an LLM semantic producer"):
        ExternalProviderTrustRegistry((ExternalProviderTrustRegistration(
            "bad", "p", "HUMAN_EXPERT_ADJUDICATION", "v1", "p", PUBLIC_B64
        ),))
