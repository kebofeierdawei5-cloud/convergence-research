from __future__ import annotations

"""Provider-backed runtime preflight. This module never creates an IIOS decision."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any, Mapping

from iios_mvp.canonical_host_v01 import (
    HostConfigurationError, HostRequestError, _load_object_bytes,
    load_host_config, load_trusted_bundle,
)
from iios_mvp.canonical_natural_language_entry_v01 import RequestIntent
from iios_mvp.canonical_runtime_registry_v01 import validate_canonical_runtime_bindings
from iios_mvp.cli import _resolve_canonical_runtime
from iios_mvp.llm_semantic_workbench_v01 import SemanticRequest
from iios_mvp.thesis_admission_v03 import THESIS_STATUSES

_PROJECTION_FIELDS = {"status", "statement", "mechanism", "key_driver_ids", "falsifiers", "monitoring_triggers"}

VERSION = "IIOS-CANONICAL-RUNTIME-PREFLIGHT-0.1"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SAFE_REASON = re.compile(r"^[A-Z0-9_:-]{1,160}$")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _reason(exc: BaseException) -> str:
    text = str(exc)
    return text if _SAFE_REASON.fullmatch(text) else type(exc).__name__


def _case(bundle: Mapping[str, Any]) -> dict[str, str]:
    case = bundle.get("investment_case")
    if not isinstance(case, Mapping):
        raise HostRequestError("INVESTMENT_CASE_OBJECT_REQUIRED")
    required = ("case_id", "market", "symbol", "company", "cutoff_date")
    missing = [name for name in required if not str(case.get(name, "")).strip()]
    if missing:
        raise HostRequestError("PREFLIGHT_CASE_FIELDS_MISSING:" + ",".join(missing))
    return {
        "case_id": str(case["case_id"]),
        "market": str(case["market"]).upper(),
        "symbol": str(case["symbol"]).upper(),
        "company": str(case["company"]),
        "cutoff_date": str(case["cutoff_date"])[:10],
    }


def _manifest_inputs(path: str | Path, case: Mapping[str, str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    manifest = _load_object_bytes(Path(path).read_bytes(), limit=64 * 1024 * 1024, error_code="PREFLIGHT_MANIFEST_TOO_LARGE")
    rows = manifest.get("evidence")
    if not isinstance(rows, list) or not rows:
        raise HostRequestError("PREFLIGHT_MANIFEST_HAS_NO_EVIDENCE_ROWS")
    identity = (
        str(manifest.get("case_id", "")),
        str(manifest.get("market", "")).upper(),
        str(manifest.get("symbol", "")).upper(),
        str(manifest.get("company", "")),
        str(manifest.get("cutoff_date", ""))[:10],
    )
    expected = (case["case_id"], case["market"], case["symbol"], case["company"], case["cutoff_date"])
    if identity != expected:
        raise HostRequestError("PREFLIGHT_MANIFEST_CASE_IDENTITY_MISMATCH")
    refs, hashes = [], []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise HostRequestError(f"PREFLIGHT_MANIFEST_ROW_{i}_INVALID")
        ref, digest = str(row.get("evidence_id", "")).strip(), str(row.get("content_sha256", "")).strip()
        if not ref or not _SHA.fullmatch(digest):
            raise HostRequestError(f"PREFLIGHT_MANIFEST_ROW_{i}_IDENTITY_OR_HASH_INVALID")
        refs.append(ref)
        hashes.append(digest)
    return tuple(refs), tuple(hashes)


def _receipt_summaries(root: Path, prior: set[str]) -> list[dict[str, str]]:
    evidence_dir = root / "live-provider-evidence"
    if not evidence_dir.is_dir():
        return []
    summaries = []
    for path in sorted(evidence_dir.glob("*.json")):
        if path.name in prior:
            continue
        raw = path.read_bytes()
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            summaries.append({"file": path.name, "file_sha256": hashlib.sha256(raw).hexdigest(), "verification": "UNREADABLE"})
            continue
        # Report signed receipt metadata only; never copy the prompt or raw model output.
        summaries.append({
            "file": path.name,
            "file_sha256": hashlib.sha256(raw).hexdigest(),
            "attestation_hash": str(record.get("attestation_hash", "")),
            "response_sha256": str(record.get("response_sha256", "")),
            "provider_id": str(record.get("provider_id", "")),
            "provider_version": str(record.get("provider_version", "")),
            "model": str(record.get("model", "")),
            "status": str(record.get("status", "")),
        })
    return summaries


def _save(root: Path, report: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    directory = root / "runtime-preflight"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    core = dict(report)
    core.pop("report_sha256", None)
    signed = {**core, "report_sha256": hashlib.sha256(_canonical(core)).hexdigest()}
    name = hashlib.sha256(str(signed.get("run_id", "blocked")).encode()).hexdigest() + ".preflight.json"
    path = directory / name
    payload = json.dumps(signed, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise HostRequestError("PREFLIGHT_REPORT_IMMUTABLE_COLLISION") from exc
    return path, signed


def perform_callback_preflight(
    *, bundle: Mapping[str, Any], runtime: Any, output_root: str | Path,
    provider_id: str, provider_version: str, model: str, runtime_factory: str,
    run_id: str, request_id: str, created_at: str | None = None,
) -> dict[str, Any]:
    """Exercise the two real callbacks; no admission, resolver or decision call is made."""
    root = Path(output_root).resolve(strict=True)
    case = _case(bundle)
    refs, hashes = _manifest_inputs(str(bundle["evidence_manifest_path"]), case)
    if str(bundle.get("artifact_type", "")) != "THESIS_ASSESSMENT":
        raise HostRequestError("PREFLIGHT_REQUIRES_THESIS_ASSESSMENT")
    raw_request = str(bundle.get("raw_request", "")).strip()
    prompt = str(bundle.get("semantic_prompt", "")).strip()
    if not raw_request or not prompt:
        raise HostRequestError("PREFLIGHT_RAW_REQUEST_AND_SEMANTIC_PROMPT_REQUIRED")
    bindings = validate_canonical_runtime_bindings(runtime)
    created = created_at or datetime.now(timezone.utc).isoformat()
    live_root = root / "live-provider-evidence"
    prior = {p.name for p in live_root.glob("*.json")} if live_root.is_dir() else set()
    report: dict[str, Any] = {
        "schema_version": VERSION, "status": "PREFLIGHT_ONLY_IN_PROGRESS",
        "run_id": run_id, "request_id": request_id, "created_at": created, "case": case,
        "provider": {"provider_id": provider_id, "provider_version": provider_version, "model": model, "runtime_factory": runtime_factory},
        "request_callback_status": "NOT_RUN", "semantic_callback_status": "NOT_RUN",
        "request_intent": None, "semantic_projection_keys": [], "manifest_row_count": len(refs),
        "evidence_pit_admission_checked": False, "semantic_admission_checked": False,
        "decision_created": False, "publication_created": False, "run_receipt_created": False,
        "human_approval_required": True, "auto_execution": False, "signed_provider_receipts": [],
        "non_claims": [
            "Provider callback preflight only; Evidence/PIT and semantic admission were not run or granted.",
            "No Forecast, Valuation, Decision, publication, investor report or complete IIOS_RUN_RECEIPT is produced.",
            "PREFLIGHT_ONLY does not prove the HTTP Host is deployed or production-accepted.",
        ],
    }
    try:
        intent = bindings.request_interpreter.interpret(raw_request)
        if not isinstance(intent, RequestIntent):
            raise HostRequestError("REQUEST_INTERPRETER_DID_NOT_RETURN_REQUEST_INTENT")
        if (intent.market.upper(), intent.symbol.upper(), intent.as_of_date) != (case["market"], case["symbol"], case["cutoff_date"]):
            raise HostRequestError("PREFLIGHT_REQUEST_INTENT_CASE_MISMATCH")
        report["request_callback_status"] = "PASS"
        report["request_intent"] = {
            "market": intent.market, "symbol": intent.symbol, "as_of_date": intent.as_of_date,
            "request_type": intent.request_type, "current_position_pct": str(intent.current_position_pct),
        }
        request = SemanticRequest(
            request_id=request_id, run_id=run_id, case_id=case["case_id"],
            market=case["market"], symbol=case["symbol"], company=case["company"],
            cutoff_date=case["cutoff_date"], artifact_type="THESIS_ASSESSMENT",
            input_refs=refs, input_hashes=hashes, prompt=prompt, created_at=created,
        )
        result = bindings.semantic_producer.produce(request)
        if not isinstance(result, Mapping) or set(result) != {"core_projection"} or not isinstance(result.get("core_projection"), Mapping):
            raise HostRequestError("SEMANTIC_PRODUCER_OUTPUT_SCHEMA_INVALID")
        projection = result["core_projection"]
        if set(projection) != _PROJECTION_FIELDS:
            raise HostRequestError("PREFLIGHT_SEMANTIC_PROJECTION_SCHEMA_INVALID")
        if projection.get("status") not in THESIS_STATUSES:
            raise HostRequestError("PREFLIGHT_SEMANTIC_STATUS_INVALID")
        for field in ("statement", "mechanism"):
            if not isinstance(projection.get(field), str) or not projection[field].strip():
                raise HostRequestError("PREFLIGHT_SEMANTIC_TEXT_INVALID")
        for field in ("key_driver_ids", "falsifiers", "monitoring_triggers"):
            values = projection.get(field)
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise HostRequestError("PREFLIGHT_SEMANTIC_LIST_INVALID")
        report["semantic_callback_status"] = "PASS"
        report["semantic_projection_keys"] = sorted(str(k) for k in projection.keys())
        report["status"] = "PREFLIGHT_ONLY_COMPLETE"
    except Exception as exc:
        report["status"] = "PREFLIGHT_ONLY_BLOCKED"
        report["failure_stage"] = "REQUEST_CALLBACK" if report["request_callback_status"] == "NOT_RUN" else "SEMANTIC_CALLBACK"
        report["reason"] = _reason(exc)
    finally:
        report["signed_provider_receipts"] = _receipt_summaries(root, prior)
    return report


def run_from_environment(bundle_id: str) -> tuple[int, dict[str, Any]]:
    config = load_host_config()
    root = Path(config["output_root"]).resolve(strict=True)
    run_id, request_id = "runtime-preflight-" + uuid.uuid4().hex, "runtime-preflight-request-" + uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema_version": VERSION, "status": "PREFLIGHT_ONLY_BLOCKED",
        "run_id": run_id, "request_id": request_id, "created_at": created,
        "request_callback_status": "NOT_RUN", "semantic_callback_status": "NOT_RUN",
        "evidence_pit_admission_checked": False, "semantic_admission_checked": False,
        "decision_created": False, "publication_created": False, "run_receipt_created": False,
        "human_approval_required": True, "auto_execution": False,
    }
    try:
        bundle = load_trusted_bundle(bundle_id=bundle_id, bundle_root=config["bundle_root"], data_root=config["data_root"])
        bundle.update({"run_id": run_id, "request_id": request_id, "created_at": created})
        runtime = _resolve_canonical_runtime(factory_spec=str(config["factory_spec"]), bundle=bundle, output_root=str(root))
        if runtime is None:
            raise HostConfigurationError("CANONICAL_RUNTIME_NOT_REGISTERED")
        report = perform_callback_preflight(
            bundle=bundle, runtime=runtime, output_root=root,
            provider_id=str(os.environ.get("IIOS_LLM_PROVIDER_ID", "")),
            provider_version=str(os.environ.get("IIOS_LLM_PROVIDER_VERSION", "")),
            model=str(os.environ.get("IIOS_LLM_PROVIDER_MODEL", "")),
            runtime_factory=str(config["factory_spec"]), run_id=run_id,
            request_id=request_id, created_at=created,
        )
    except Exception as exc:
        report["status"] = "PREFLIGHT_ONLY_BLOCKED"
        report["reason"] = _reason(exc)
        report["failure_stage"] = "TRUSTED_BUNDLE_OR_RUNTIME_FACTORY"
        report.setdefault("signed_provider_receipts", [])
    path, saved = _save(root, report)
    result = {**saved, "report_path": str(path)}
    return (0 if saved["status"] == "PREFLIGHT_ONLY_COMPLETE" else 2), result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run trusted IIOS provider callback preflight without creating a decision")
    parser.add_argument("--bundle-id", required=True, help="operator-staged bundle ID (not a filesystem path)")
    args = parser.parse_args(argv)
    try:
        status, result = run_from_environment(args.bundle_id)
    except (HostConfigurationError, HostRequestError, OSError) as exc:
        print(json.dumps({
            "schema_version": VERSION, "status": "PREFLIGHT_ONLY_BLOCKED", "reason": _reason(exc),
            "evidence_pit_admission_checked": False, "semantic_admission_checked": False,
            "decision_created": False, "publication_created": False, "run_receipt_created": False,
            "human_approval_required": True, "auto_execution": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
