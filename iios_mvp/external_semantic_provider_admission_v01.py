from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from datetime import datetime, timezone
import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from iios_mvp.canonical_research_orchestrator import (
    CanonicalResearchOrchestrator,
    Stage,
    canonical_hash,
    is_sha256,
)
from iios_mvp.semantic_producer_admission_v01 import (
    ProducerRegistry,
    SemanticAdmissionContext,
    SemanticAdmissionResult,
    admit_semantic_artifact,
)

EXTERNAL_SEMANTIC_RECEIPT_SCHEMA_VERSION = "IIOS-EXTERNAL-SEMANTIC-PROVIDER-RECEIPT-0.1"
EXTERNAL_SEMANTIC_ADMISSION_VERSION = "IIOS-EXTERNAL-SEMANTIC-ADMISSION-0.1"


class ExternalSemanticAdmissionError(ValueError):
    """Raised when a signed external semantic receipt is not admissible."""


@dataclass(frozen=True)
class ExternalProviderTrustRegistration:
    public_key_id: str
    producer_id: str
    producer_type: str
    producer_version: str
    policy_version: str
    public_key_b64: str
    active: bool = True


class ExternalProviderTrustRegistry:
    def __init__(self, registrations: tuple[ExternalProviderTrustRegistration, ...] = ()) -> None:
        self._items: dict[str, ExternalProviderTrustRegistration] = {}
        for item in registrations:
            self.register(item)

    def register(self, registration: ExternalProviderTrustRegistration) -> None:
        if not registration.public_key_id.strip():
            raise ValueError("public_key_id is required")
        if registration.producer_type != "LLM_SEMANTIC_PRODUCER":
            raise ValueError("external provider must be an LLM semantic producer")
        if not registration.producer_id.strip():
            raise ValueError("producer_id is required")
        if not registration.producer_version.strip():
            raise ValueError("producer_version is required")
        if not registration.policy_version.strip():
            raise ValueError("policy_version is required")
        if registration.public_key_id in self._items:
            raise ValueError("public_key_id already registered")
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(registration.public_key_b64, validate=True))
        except Exception as exc:
            raise ValueError("public_key_b64 must contain a valid Ed25519 public key") from exc
        self._items[registration.public_key_id] = registration

    def get(self, public_key_id: str) -> ExternalProviderTrustRegistration:
        try:
            registration = self._items[public_key_id]
        except KeyError as exc:
            raise ExternalSemanticAdmissionError("external provider public key is not trusted") from exc
        if not registration.active:
            raise ExternalSemanticAdmissionError("external provider trust registration is inactive")
        return registration


@dataclass(frozen=True)
class ExternalSemanticAdmissionResult:
    status: str
    semantic_admission: SemanticAdmissionResult
    external_receipt_hash: str


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _without(value: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    excluded = set(fields)
    return {key: item for key, item in value.items() if key not in excluded}


def _attestation_payload(attestation: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(_without(attestation, "signature_b64", "attestation_hash"))


def verify_external_signed_receipt(
    *,
    artifact: Mapping[str, Any],
    attestation: Mapping[str, Any],
    registry: ExternalProviderTrustRegistry,
    run_id: str,
    request_id: str,
    raw_request_sha256: str,
    case_id: str,
    cutoff_date: str,
    input_refs: tuple[str, ...],
    input_hashes: tuple[str, ...],
) -> str:
    required = (
        "schema_version", "attestation_id", "request_id", "run_id",
        "raw_request_sha256", "case_id", "cutoff_date", "producer_type", "producer_id",
        "producer_version", "policy_version", "artifact_hash", "input_refs", "input_hashes",
        "public_key_id", "signature_algorithm", "signature_b64", "status", "created_at",
        "attestation_hash",
    )
    missing = [field for field in required if field not in attestation]
    if missing:
        raise ExternalSemanticAdmissionError(f"external receipt missing fields: {', '.join(missing)}")
    if attestation["schema_version"] != EXTERNAL_SEMANTIC_RECEIPT_SCHEMA_VERSION:
        raise ExternalSemanticAdmissionError("unsupported external semantic receipt schema")
    if attestation["request_id"] != request_id or attestation["run_id"] != run_id:
        raise ExternalSemanticAdmissionError("external receipt request/run mismatch")
    if attestation["raw_request_sha256"] != raw_request_sha256 or not is_sha256(raw_request_sha256):
        raise ExternalSemanticAdmissionError("raw request hash mismatch")
    if attestation["case_id"] != case_id:
        raise ExternalSemanticAdmissionError("external receipt case_id mismatch")
    if attestation["cutoff_date"] != cutoff_date:
        raise ExternalSemanticAdmissionError("external receipt cutoff_date mismatch")
    if tuple(attestation["input_refs"]) != input_refs:
        raise ExternalSemanticAdmissionError("external receipt input_refs mismatch")
    if tuple(attestation["input_hashes"]) != input_hashes:
        raise ExternalSemanticAdmissionError("external receipt input_hashes mismatch")
    if len(input_refs) == 0 or len(input_refs) != len(input_hashes) or any(not is_sha256(x) for x in input_hashes):
        raise ExternalSemanticAdmissionError("external receipt input lineage is invalid")
    if attestation["artifact_hash"] != artifact.get("artifact_hash") or not is_sha256(attestation["artifact_hash"]):
        raise ExternalSemanticAdmissionError("external receipt artifact_hash mismatch")
    if artifact.get("case_id") != case_id or artifact.get("cutoff_date") != cutoff_date:
        raise ExternalSemanticAdmissionError("artifact identity is not bound to external receipt")
    if tuple(artifact.get("input_refs", ())) != input_refs or tuple(artifact.get("input_hashes", ())) != input_hashes:
        raise ExternalSemanticAdmissionError("artifact lineage is not bound to external receipt")
    if attestation["producer_type"] != "LLM_SEMANTIC_PRODUCER":
        raise ExternalSemanticAdmissionError("external receipt producer_type is unauthorized")
    if attestation["signature_algorithm"] != "Ed25519":
        raise ExternalSemanticAdmissionError("unsupported external receipt signature algorithm")
    if attestation["status"] != "SIGNED":
        raise ExternalSemanticAdmissionError("external receipt is not signed")

    trusted = registry.get(attestation["public_key_id"])
    for field in ("producer_id", "producer_type", "producer_version", "policy_version"):
        if getattr(trusted, field) != attestation[field]:
            raise ExternalSemanticAdmissionError(f"trusted provider {field} mismatch")

    if not is_sha256(attestation["attestation_hash"]):
        raise ExternalSemanticAdmissionError("attestation_hash must be lowercase SHA-256")
    if canonical_hash(_without(attestation, "attestation_hash")) != attestation["attestation_hash"]:
        raise ExternalSemanticAdmissionError("external receipt integrity failure")

    try:
        signature = base64.b64decode(attestation["signature_b64"], validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(trusted.public_key_b64, validate=True))
        public_key.verify(signature, _attestation_payload(attestation))
    except (ValueError, InvalidSignature) as exc:
        raise ExternalSemanticAdmissionError("external provider signature verification failed") from exc

    return attestation["attestation_hash"]


def admit_external_signed_semantic_artifact(
    *,
    orchestrator: CanonicalResearchOrchestrator,
    artifact: Mapping[str, Any],
    attestation: Mapping[str, Any],
    run_id: str,
    request_id: str,
    raw_request_sha256: str,
    producer_registry: ProducerRegistry,
    external_registry: ExternalProviderTrustRegistry,
    facts: tuple[Mapping[str, Any], ...] = (),
    inferences: tuple[Mapping[str, Any], ...] = (),
    assumptions: tuple[Mapping[str, Any], ...] = (),
    uncertainties: tuple[Mapping[str, Any], ...] = (),
    created_at: str,
) -> ExternalSemanticAdmissionResult:
    orchestrator.authorize(run_id, Stage.SEMANTIC_PENDING)
    run = orchestrator.get(run_id)
    input_refs = tuple(artifact.get("input_refs", ()))
    input_hashes = tuple(artifact.get("input_hashes", ()))
    external_receipt_hash = verify_external_signed_receipt(
        artifact=artifact,
        attestation=attestation,
        registry=external_registry,
        run_id=run_id,
        request_id=request_id,
        raw_request_sha256=raw_request_sha256,
        case_id=run.case_id,
        cutoff_date=run.cutoff_date,
        input_refs=input_refs,
        input_hashes=input_hashes,
    )
    context = SemanticAdmissionContext(
        case_id=run.case_id,
        market=run.market,
        symbol=run.symbol,
        company=str(artifact.get("company", "")),
        cutoff_date=run.cutoff_date,
        artifact_type=str(artifact.get("artifact_type", "")),
        input_refs=input_refs,
        input_hashes=input_hashes,
        producer_id=str(attestation["producer_id"]),
        producer_version=str(attestation["producer_version"]),
        producer_type=str(attestation["producer_type"]),
        policy_version=str(attestation["policy_version"]),
    )
    from iios_mvp.semantic_producer_admission_v01 import build_producer_receipt
    local_receipt = build_producer_receipt(
        receipt_id=f"{run_id}:{request_id}:local-receipt",
        artifact=artifact,
        stage_id=context.artifact_type,
        created_at=created_at,
    )
    semantic_admission = admit_semantic_artifact(
        artifact,
        local_receipt,
        context=context,
        registry=producer_registry,
    )
    orchestrator.transition(
        run_id,
        Stage.SEMANTIC_ADMITTED,
        artifact_ref=artifact["artifact_hash"],
        input_refs=input_refs,
        input_hashes=input_hashes,
        output_hashes=(artifact["artifact_hash"],),
        producer_type=attestation["producer_type"],
        producer_version=attestation["producer_version"],
        created_at=created_at,
    )
    return ExternalSemanticAdmissionResult(
        status="ADMITTED",
        semantic_admission=semantic_admission,
        external_receipt_hash=external_receipt_hash,
    )


__all__ = [
    "EXTERNAL_SEMANTIC_RECEIPT_SCHEMA_VERSION",
    "EXTERNAL_SEMANTIC_ADMISSION_VERSION",
    "ExternalSemanticAdmissionError",
    "ExternalProviderTrustRegistration",
    "ExternalProviderTrustRegistry",
    "ExternalSemanticAdmissionResult",
    "verify_external_signed_receipt",
    "admit_external_signed_semantic_artifact",
]
