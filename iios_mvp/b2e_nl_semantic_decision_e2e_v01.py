from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from iios_mvp.canonical_natural_language_entry_v01 import (
    RequestAdmissionResult,
    RequestInterpreter,
    RequestInterpreterRegistry,
    admit_natural_language_request,
)
from iios_mvp.canonical_research_orchestrator import CanonicalResearchOrchestrator, Stage
from iios_mvp.canonical_run_authority_v01 import (
    PersistedCanonicalResearchOrchestrator,
    block_persisted_run,
    run_state_path,
)
from iios_mvp.decision_admission import admit_canonical_decision
from iios_mvp.decision_lifecycle_production import build_decision_revision, validate_decision_revision
from iios_mvp.decision_upstream_admission_v03 import DECISION_UPSTREAM_ADMISSION_V02
from iios_mvp.investment_core_contract_v03 import decide_v03
from iios_mvp.semantic_to_core_projection_v01 import project_thesis_semantic_to_core
from iios_mvp.forecast_valuation_return_lineage_v01 import validate_forecast_valuation_return_lineage, FORECAST_VALUATION_RETURN_LINEAGE_VERSION
from iios_mvp.llm_semantic_workbench_v01 import (
    LLMSemanticWorkbench,
    SemanticProducer,
    SemanticRequest,
    WorkbenchResult,
)
from iios_mvp.semantic_producer_admission_v01 import ProducerRegistry
from iios_mvp.canonical_evidence_admission_v01 import validate_company_evidence_manifest

B2E_CONTRACT_VERSION = "IIOS-B2-E-NL-SEMANTIC-DECISION-E2E-0.1"
B2E_STATUS_ADMITTED = "ADMITTED"
FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS = frozenset(
    {
        "action",
        "decision_status",
        "new_capital_allowed",
        "human_approval_required",
        "auto_execution",
        "capital_effect",
        "decision_admission",
        "decision_precedence_rule_id",
        "decision_pre_admission_action",
    }
)


class B2EE2EError(ValueError):
    """Raised when the B2-E natural-language-to-decision boundary is invalid."""


@dataclass(frozen=True)
class B2EConformanceResult:
    request_admission: RequestAdmissionResult
    semantic: WorkbenchResult
    decision_admission: Mapping[str, Any]
    decision_revision: Mapping[str, Any]
    binding_receipt: Mapping[str, Any]
    canonicality_status: str = "NON_CANONICAL_CONFORMANCE_ONLY"
    run_state_path: str | None = None


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _assert_no_authority_fields(value: Mapping[str, Any]) -> None:
    output = value.get("output")
    if not isinstance(output, Mapping):
        raise B2EE2EError("semantic artifact output must be an object")

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            present = sorted(
                FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS.intersection(node.keys())
            )
            if present:
                raise B2EE2EError(
                    "semantic producer attempted decision authority fields at "
                    f"{path}: " + ", ".join(present)
                )
            for key, child in node.items():
                walk(child, f"{path}.{key}")
            return
        if isinstance(node, (list, tuple)):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")

    walk(output, "output")


def _build_snapshot(
    *,
    case: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": dict(case),
        "decision": dict(decision),
    }
    return {**core, "snapshot_hash": sha256(core)}


def _transition_pre_decision(
    orchestrator: CanonicalResearchOrchestrator,
    *,
    run_id: str,
    case: Mapping[str, Any],
    independent_forecast_resolver: Any,
    valuation_output_resolver: Any,
    created_at: str,
) -> dict[str, Any]:
    return_gate = case.get("return_gate")
    if not isinstance(return_gate, Mapping):
        raise B2EE2EError("canonical return_gate is required for Forecast/Valuation admission")

    try:
        lineage = validate_forecast_valuation_return_lineage(
            return_gate=return_gate,
            canonical_forecast_ref=return_gate.get("canonical_forecast_ref"),
            canonical_valuation_ref=return_gate.get("canonical_valuation_ref"),
            independent_forecast_resolver=independent_forecast_resolver,
            valuation_output_resolver=valuation_output_resolver,
            case_id=str(case["case_id"]),
            market=str(case["market"]).upper(),
            symbol=str(case["symbol"]).upper(),
            company=str(case["company"]),
            cutoff_date=__import__("datetime").date.fromisoformat(str(case["cutoff_date"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise B2EE2EError(
            f"canonical Forecast/Valuation lineage admission failed: {exc}"
        ) from exc

    forecast_ref = lineage["canonical_forecast_ref"]
    valuation_ref = lineage["canonical_valuation_ref"]

    if isinstance(orchestrator, PersistedCanonicalResearchOrchestrator):
        resolve_valuation_admission = getattr(
            valuation_output_resolver, "resolve_valuation_admission", None
        )
        if not callable(resolve_valuation_admission):
            raise B2EE2EError(
                "BLOCKED: persisted canonical runs require resolver-backed valuation admission records"
            )
        valuation_admission = resolve_valuation_admission(
            valuation_ref,
            case_id=str(case["case_id"]),
            market=str(case["market"]).upper(),
            symbol=str(case["symbol"]).upper(),
            company=str(case["company"]),
            cutoff_date=__import__("datetime").date.fromisoformat(str(case["cutoff_date"])),
        )
        from iios_mvp.canonical_investment_admission_v01 import (
            validate_canonical_investment_admission_record,
        )
        validate_canonical_investment_admission_record(valuation_admission)
        if hasattr(valuation_admission, "to_dict"):
            valuation_admission = valuation_admission.to_dict()
        if (
            valuation_admission.get("status") != "ADMITTED"
            or valuation_admission.get("domain") != "VALUATION"
            or valuation_admission.get("admission_id") != valuation_ref.get("admission_id")
            or valuation_admission.get("admission_record_hash") != valuation_ref.get("admission_record_hash")
            or valuation_admission.get("output_hash") != lineage["valuation_output"].get("output_hash")
        ):
            raise B2EE2EError(
                "BLOCKED: persisted valuation output is not bound to its admitted VALUATION record"
            )
        lineage["valuation_admission_record"] = dict(valuation_admission)

    orchestrator.transition(
        run_id,
        Stage.FORECAST_PENDING,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.FORECAST_ADMITTED,
        output_refs=(forecast_ref["forecast_id"],),
        output_hashes=(forecast_ref["admission_record_hash"],),
        producer_type="CODE",
        producer_version=FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.VALUATION_PENDING,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.VALUATION_ADMITTED,
        output_refs=(valuation_ref["admission_id"],),
        output_hashes=(valuation_ref["admission_record_hash"],),
        producer_type="CODE",
        producer_version=FORECAST_VALUATION_RETURN_LINEAGE_VERSION,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.DECISION_PENDING,
        input_refs=(
            forecast_ref["forecast_id"],
            valuation_ref["admission_id"],
        ),
        input_hashes=(
            forecast_ref["admission_record_hash"],
            valuation_ref["admission_record_hash"],
        ),
        created_at=created_at,
    )
    return lineage


def _persist_blocked_on_error(function):
    from functools import wraps

    @wraps(function)
    def guarded(*args: Any, **kwargs: Any) -> B2EConformanceResult:
        run_root = kwargs.get("run_root")
        run_id = kwargs.get("run_id")
        try:
            return function(*args, **kwargs)
        except Exception as exc:
            if run_root and run_id:
                try:
                    block_persisted_run(
                        str(run_root), str(run_id),
                        f"{type(exc).__name__}: {str(exc)[:1800]}",
                    )
                except Exception:
                    # Preserve the primary exception. Without a verifiable
                    # state file, no formal writer can obtain authorization.
                    pass
            raise
    return guarded


@_persist_blocked_on_error
def run_b2e_conformance(
    *,
    raw_request: str,
    request_id: str,
    run_id: str,
    created_at: str,
    request_interpreter: RequestInterpreter,
    request_registry: RequestInterpreterRegistry,
    semantic_producer: SemanticProducer,
    producer_registry: ProducerRegistry,
    company: str,
    evidence_refs: tuple[str, ...],
    evidence_hashes: tuple[str, ...],
    artifact_type: str,
    semantic_prompt: str,
    semantic_facts: tuple[Mapping[str, Any], ...] = (),
    semantic_inferences: tuple[Mapping[str, Any], ...] = (),
    semantic_assumptions: tuple[Mapping[str, Any], ...] = (),
    semantic_uncertainties: tuple[Mapping[str, Any], ...] = (),
    decision_relevance: str,
    case: Mapping[str, Any],
    current_price_resolver: Any,
    independent_forecast_resolver: Any,
    upstream_authority_resolver: Any,
    valuation_output_resolver: Any,
    run_root: str | None = None,
    evidence_manifest: Mapping[str, Any] | None = None,
    evidence_root: str | None = None,
) -> B2EConformanceResult:
    orchestrator = (
        PersistedCanonicalResearchOrchestrator(run_root)
        if run_root is not None
        else CanonicalResearchOrchestrator()
    )
    admitted = admit_natural_language_request(
        orchestrator=orchestrator,
        registry=request_registry,
        interpreter=request_interpreter,
        request_id=request_id,
        run_id=run_id,
        raw_request=raw_request,
        created_at=created_at,
    )

    if sha256(admitted.research_case) != admitted.case_hash:
        if run_root is not None:
            orchestrator.block(run_id, "RESEARCH_CASE_HASH_BINDING_FAILED")
        raise B2EE2EError("research case hash binding failed")
    # Production-backed runs must prove source-by-source B2/PIT admission from
    # the exact raw-byte root. Caller-provided IDs/hashes alone are never admission.
    admitted_manifest: dict[str, Any] | None = None
    admitted_manifest_hash: str | None = None
    if run_root is not None:
        if not isinstance(evidence_manifest, Mapping) or not evidence_root:
            orchestrator.block(run_id, "B2_EVIDENCE_PIT_ADMISSION_REQUIRED")
            raise B2EE2EError(
                "BLOCKED: persisted canonical runs require a B2 Evidence/PIT manifest and raw_root"
            )
        admitted_manifest = dict(evidence_manifest)
        evidence_errors = validate_company_evidence_manifest(
            admitted_manifest,
            raw_root=Path(evidence_root),
            require_raw_verification=True,
        )
        if admitted_manifest.get("status") != "PASS" or admitted_manifest.get("validation_errors") not in (None, []):
            evidence_errors = list(evidence_errors) + [
                "MANIFEST_STATUS_NOT_PASS",
                *list(admitted_manifest.get("validation_errors") or []),
            ]
        manifest_identity = (
            str(admitted_manifest.get("case_id", "")),
            str(admitted_manifest.get("market", "")).upper(),
            str(admitted_manifest.get("symbol", "")).upper(),
            str(admitted_manifest.get("company", "")),
            str(admitted_manifest.get("cutoff_date", ""))[:10],
        )
        expected_identity = (
            admitted.case_id,
            str(admitted.research_case["request"]["market"]).upper(),
            str(admitted.research_case["request"]["symbol"]).upper(),
            str(company),
            str(admitted.research_case["temporal_scope"]["cutoff_date"]),
        )
        if manifest_identity != expected_identity:
            evidence_errors.append("EVIDENCE_MANIFEST_CASE_IDENTITY_OR_CUTOFF_MISMATCH")
        manifest_evidence = admitted_manifest.get("evidence") or []
        manifest_refs = tuple(str(x.get("evidence_id", "")) for x in manifest_evidence)
        manifest_hashes = tuple(str(x.get("content_sha256", "")) for x in manifest_evidence)
        if manifest_refs != tuple(evidence_refs) or manifest_hashes != tuple(evidence_hashes):
            evidence_errors.append("CALLER_EVIDENCE_REFS_HASHES_DO_NOT_MATCH_ADMITTED_MANIFEST")
        if evidence_errors:
            orchestrator.block(run_id, "B2_EVIDENCE_PIT_ADMISSION_FAILED")
            raise B2EE2EError(
                "BLOCKED: B2 Evidence/PIT admission failed: " + "; ".join(sorted(set(evidence_errors)))
            )
        admitted_manifest_hash = str((admitted_manifest.get("audit") or {}).get("manifest_sha256", ""))
        if len(admitted_manifest_hash) != 64 or any(c not in "0123456789abcdef" for c in admitted_manifest_hash):
            orchestrator.block(run_id, "B2_EVIDENCE_MANIFEST_HASH_INVALID")
            raise B2EE2EError("BLOCKED: admitted Evidence Manifest hash is invalid")
    case_identity = {
        "case_id": case.get("case_id"),
        "market": str(case.get("market", "")).upper(),
        "symbol": str(case.get("symbol", "")).upper(),
        "cutoff_date": case.get("cutoff_date"),
        "as_of_date": case.get("as_of_date"),
    }
    admitted_identity = {
        "case_id": admitted.case_id,
        "market": str(admitted.research_case["request"]["market"]).upper(),
        "symbol": str(admitted.research_case["request"]["symbol"]).upper(),
        "cutoff_date": admitted.research_case["temporal_scope"]["cutoff_date"],
        "as_of_date": admitted.research_case["request"]["as_of_date"],
    }
    if case_identity != admitted_identity:
        if run_root is not None:
            orchestrator.block(run_id, "INVESTMENT_CASE_IDENTITY_MISMATCH")
        raise B2EE2EError(
            "expanded Investment Core case identity does not match admitted Research Case"
        )

    orchestrator.transition(
        run_id,
        Stage.EVIDENCE_PENDING,
        created_at=created_at,
    )
    if len(evidence_refs) == 0 or len(evidence_refs) != len(evidence_hashes):
        if run_root is not None:
            orchestrator.block(run_id, "EVIDENCE_LINEAGE_INVALID")
        raise B2EE2EError("evidence lineage must contain matching non-empty references and hashes")
    manifest_refs = (
        (f"evidence-manifest:{admitted_manifest_hash}",) if admitted_manifest_hash else ()
    )
    manifest_hashes = (admitted_manifest_hash,) if admitted_manifest_hash else ()
    orchestrator.transition(
        run_id,
        Stage.EVIDENCE_ADMITTED,
        output_refs=manifest_refs + evidence_refs,
        output_hashes=manifest_hashes + evidence_hashes,
        created_at=created_at,
    )
    orchestrator.transition(
        run_id,
        Stage.SEMANTIC_PENDING,
        created_at=created_at,
    )

    semantic_request = SemanticRequest(
        request_id=request_id,
        run_id=run_id,
        case_id=admitted.case_id,
        market=admitted.research_case["request"]["market"],
        symbol=admitted.research_case["request"]["symbol"],
        company=company,
        cutoff_date=admitted.research_case["temporal_scope"]["cutoff_date"],
        artifact_type=artifact_type,
        input_refs=evidence_refs,
        input_hashes=evidence_hashes,
        prompt=semantic_prompt,
        created_at=created_at,
    )
    semantic = LLMSemanticWorkbench(
        orchestrator=orchestrator,
        registry=producer_registry,
    ).run(
        producer=semantic_producer,
        request=semantic_request,
        decision_relevance=decision_relevance,
        facts=semantic_facts,
        inferences=semantic_inferences,
        assumptions=semantic_assumptions,
        uncertainties=semantic_uncertainties,
    )
    _assert_no_authority_fields(semantic.artifact)

    projected_case = project_thesis_semantic_to_core(
        artifact=semantic.artifact,
        admission=semantic.admission,
        case=case,
    )
    projection = projected_case["semantic_core_projection"]

    upstream_lineage = _transition_pre_decision(
        orchestrator,
        run_id=run_id,
        case=projected_case,
        independent_forecast_resolver=independent_forecast_resolver,
        valuation_output_resolver=valuation_output_resolver,
        created_at=created_at,
    )

    canonical_decision = decide_v03(
        dict(projected_case),
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )
    snapshot = _build_snapshot(case=projected_case, decision=canonical_decision)
    decision_admission = admit_canonical_decision(
        case=projected_case,
        snapshot=snapshot,
        current_price_resolver=current_price_resolver,
        independent_forecast_resolver=independent_forecast_resolver,
        upstream_authority_resolver=upstream_authority_resolver,
        valuation_output_resolver=valuation_output_resolver,
    )

    return_metrics_hash = sha256(canonical_decision.get("return_metrics") or {})
    risk_portfolio_payload = (
        canonical_decision.get("risk_portfolio_contract")
        or canonical_decision.get("positioning_sizing")
        or {}
    )
    risk_portfolio_hash = sha256(risk_portfolio_payload)
    decision_snapshot_hash = snapshot["snapshot_hash"]
    decision_admission_hash = decision_admission["admission_record_hash"]
    decision_stage_refs = (
        "decision_snapshot",
        "decision_admission",
        "return_metrics",
        "risk_portfolio",
    )
    decision_stage_hashes = (
        decision_snapshot_hash,
        decision_admission_hash,
        return_metrics_hash,
        risk_portfolio_hash,
    )
    # The formal writer must be able to re-open every authority-bearing upstream
    # payload after restart; stage hashes alone only prove self-consistency.
    canonical_upstream_bundle: dict[str, Any] | None = None
    if run_root is not None:
        upstream_bundle_core = {
            "schema_version": "IIOS-CANONICAL-UPSTREAM-ADMISSIONS-0.1",
            "run_id": run_id,
            "case_id": str(projected_case["case_id"]),
            "market": str(projected_case["market"]).upper(),
            "symbol": str(projected_case["symbol"]).upper(),
            "company": str(projected_case["company"]),
            "cutoff_date": str(projected_case["cutoff_date"]),
            "semantic_artifact": dict(semantic.artifact),
            "semantic_producer_receipt": dict(semantic.producer_receipt),
            "semantic_admission": dict(semantic.admission.__dict__),
            "canonical_forecast_ref": dict(upstream_lineage["canonical_forecast_ref"]),
            "forecast_record": dict(upstream_lineage["forecast_record"]),
            "canonical_valuation_ref": dict(upstream_lineage["canonical_valuation_ref"]),
            "valuation_admission_record": dict(upstream_lineage["valuation_admission_record"]),
            "valuation_output": dict(upstream_lineage["valuation_output"]),
            "validated_lineage": {
                key: value for key, value in upstream_lineage.items()
                if key not in {"forecast_record", "valuation_output"}
            },
        }
        canonical_upstream_bundle = {
            **upstream_bundle_core,
            "bundle_hash": sha256(upstream_bundle_core),
        }
        canonical_upstream_bytes = _canonical(canonical_upstream_bundle)
        canonical_upstream_file_hash = hashlib.sha256(canonical_upstream_bytes).hexdigest()
        decision_stage_refs = decision_stage_refs + (
            f"canonical-upstream-admissions:{canonical_upstream_file_hash}",
        )
        decision_stage_hashes = decision_stage_hashes + (canonical_upstream_file_hash,)


    revision: Mapping[str, Any]
    if run_root is not None:
        from iios_mvp.store import (
            create_or_load_series, next_revision, write_decision_revision,
            write_snapshot,
        )
        root_path = Path(run_root)
        root_path.mkdir(parents=True, exist_ok=True)
        # Persist inspectable canonical inputs before the Decision Revision. These
        # are immutable audit artifacts; the registered validators remain the
        # authority for their semantic admission.
        artifacts = {
            "research-case": admitted.research_case,
            "investment-case": projected_case,
            "evidence-manifest": admitted_manifest,
            "semantic-artifact": dict(semantic.artifact),
            "semantic-producer-receipt": dict(semantic.producer_receipt),
            "semantic-admission": dict(semantic.admission.__dict__),
            "forecast-admission": dict(upstream_lineage["forecast_record"]),
            "valuation-admission": dict(upstream_lineage["valuation_admission_record"]),
            "valuation-output": dict(upstream_lineage["valuation_output"]),
            "decision-admission": dict(decision_admission),
            "canonical-upstream-admissions": canonical_upstream_bundle,
        }
        # Copy the already verified source bytes into the run's immutable evidence
        # root. The Decision Revision write boundary independently reopens these
        # bytes and the admitted manifest; a manifest without its raw byte bundle
        # cannot authorize a formal write.
        if not isinstance(admitted_manifest, Mapping) or not evidence_root:
            raise B2EE2EError("BLOCKED: canonical evidence manifest/raw root is absent")
        source_root = Path(evidence_root).resolve()
        canonical_evidence_root = (root_path / "canonical-evidence").resolve()
        canonical_evidence_root.mkdir(parents=True, exist_ok=True)
        for declaration in admitted_manifest.get("raw_artifacts", []):
            relative_path = declaration.get("relative_path")
            if not isinstance(relative_path, str) or not relative_path.strip():
                raise B2EE2EError("BLOCKED: raw evidence relative_path is invalid")
            source_path = (source_root / relative_path).resolve()
            destination_path = (canonical_evidence_root / relative_path).resolve()
            try:
                source_path.relative_to(source_root)
                destination_path.relative_to(canonical_evidence_root)
            except ValueError as exc:
                raise B2EE2EError("BLOCKED: raw evidence path escapes its root") from exc
            if not source_path.is_file():
                raise B2EE2EError("BLOCKED: raw evidence bytes are missing: " + relative_path)
            raw_bytes = source_path.read_bytes()
            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
            if (
                len(raw_bytes) != declaration.get("expected_size_bytes")
                or actual_hash != declaration.get("expected_sha256")
            ):
                raise B2EE2EError("BLOCKED: raw evidence bytes no longer match admitted manifest: " + relative_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if destination_path.exists():
                if destination_path.read_bytes() != raw_bytes:
                    raise B2EE2EError("immutable canonical raw evidence collision: " + relative_path)
            else:
                destination_path.write_bytes(raw_bytes)

        for artifact_name, artifact_payload in artifacts.items():
            artifact_bytes = json.dumps(
                artifact_payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()
            artifact_path = root_path / "canonical-artifacts" / f"{artifact_digest}.{artifact_name}.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            if artifact_path.exists():
                if artifact_path.read_bytes() != artifact_bytes:
                    raise B2EE2EError("immutable canonical artifact collision")
            else:
                artifact_path.write_bytes(artifact_bytes)
        write_snapshot(root_path, snapshot)
        orchestrator.transition(
            run_id,
            Stage.DECISION_ADMITTED,
            output_refs=decision_stage_refs,
            output_hashes=decision_stage_hashes,
            input_refs=(semantic.artifact["artifact_id"],),
            input_hashes=(semantic.artifact["artifact_hash"],),
            created_at=created_at,
        )
        series = create_or_load_series(
            root_path, str(projected_case["market"]), str(projected_case["symbol"]),
            str(projected_case["company"]), created_at,
        )
        revision_number = next_revision(root_path, series["decision_series_id"])
        revision_path = write_decision_revision(
            root_path,
            series["decision_series_id"],
            revision_number,
            snapshot,
            run_id=run_id,
            decision_admission=dict(decision_admission),
        )
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
    else:
        # Useful for conformance tests and diagnostics, but no persistent run
        # authority means this result is not publishable as a canonical decision.
        revision = build_decision_revision(
            revision=1,
            snapshot=snapshot,
            run_id=run_id,
            decision_admission=decision_admission,
        )
    validate_decision_revision(
        revision,
        case_id=admitted.case_id,
        cutoff_date=admitted.research_case["temporal_scope"]["cutoff_date"],
    )

    core = {
        "schema_version": B2E_CONTRACT_VERSION,
        "status": B2E_STATUS_ADMITTED,
        "run_id": run_id,
        "request_id": request_id,
        "case_id": admitted.case_id,
        "market": admitted.research_case["request"]["market"],
        "symbol": admitted.research_case["request"]["symbol"],
        "cutoff_date": admitted.research_case["temporal_scope"]["cutoff_date"],
        "raw_request_sha256": admitted.request_receipt["raw_request_sha256"],
        "request_receipt_hash": admitted.request_receipt["receipt_hash"],
        "research_case_hash": admitted.case_hash,
        "case_hash": sha256(projected_case),
        "semantic_core_projection_hash": projection["projection_hash"],
        "semantic_core_projection_hash": projection["projection_hash"],
        "semantic_artifact_hash": semantic.artifact["artifact_hash"],
        "semantic_admission_hash": semantic.admission.admission_hash,
        "decision_admission_hash": decision_admission["admission_record_hash"],
        "decision_revision_hash": revision["revision_hash"],
        "action": decision_admission["canonical_action"],
        "human_approval_required": True,
        "auto_execution": False,
        "authority_boundary": {
            "semantic_producer_can_decide": False,
            "canonical_decision_kernel_is_authoritative": True,
            "human_approval_is_required": True,
            "automatic_execution_is_forbidden": True,
        },
        "created_at": created_at,
    }
    receipt = {**core, "binding_receipt_hash": sha256(core)}

    return B2EConformanceResult(
        request_admission=admitted,
        semantic=semantic,
        decision_admission=decision_admission,
        decision_revision=revision,
        binding_receipt=receipt,
        canonicality_status=(
            "CANONICAL_RUN_IN_PROGRESS" if run_root is not None
            else "NON_CANONICAL_CONFORMANCE_ONLY"
        ),
        run_state_path=(
            str(run_state_path(run_root, run_id)) if run_root is not None else None
        ),
    )


__all__ = [
    "B2E_CONTRACT_VERSION",
    "B2EE2EError",
    "B2EConformanceResult",
    "FORBIDDEN_SEMANTIC_AUTHORITY_FIELDS",
    "run_b2e_conformance",
    "sha256",
]
