from __future__ import annotations

import argparse
import importlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .company_economic_core import build_company_economic_core, validate_company_economic_core
from .core03_market_expectation import build_core03_package, validate_core03_package
from .engine import replay, render_markdown, run_case
from .b2e_nl_semantic_decision_e2e_v01 import run_b2e_conformance
from .canonical_runtime_registry_v01 import CanonicalRuntimeBindings, get_canonical_runtime
from .decision_admission import admit_canonical_decision
from .research_intake import build_research_case
from .machine_publication import write_machine_publication
from .human_report import write_human_report
from .investor_review_report import write_investor_review_report
from .investor_review_report_v02 import write_investor_review_report_v02
from .store import (
    approve_revision,
    create_or_load_series,
    load_series,
    next_revision,
    read_snapshot,
    replay_decision_lifecycle,
    write_decision_revision,
    write_human_approval,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
    initialize_monitoring_state,
    apply_monitoring_event,
    replay_monitoring_state,
    write_monitoring_validation,
    replay_monitoring_validation,
)


def load_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd_intake(args: argparse.Namespace) -> int:
    case = build_research_case(
        args.symbol,
        args.as_of,
        args.position,
        market=args.market,
        generated_at=args.generated_at,
    )
    payload = json.dumps(case, ensure_ascii=False, indent=2)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": "CREATED", "research_case": str(path), "case_id": case["case_id"]}, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0


def cmd_economic_core(args: argparse.Namespace) -> int:
    payload = load_json(args.input)
    required = ("case", "reality", "trust", "quality", "value_core", "value_driver_ranking")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"economic-core input missing required fields: {missing}")
    core = build_company_economic_core(
        payload["case"],
        payload["reality"],
        payload["trust"],
        payload["quality"],
        payload["value_core"],
        payload["value_driver_ranking"],
        generated_at=args.generated_at,
    )
    errors = validate_company_economic_core(core)
    if errors:
        raise ValueError("generated CORE-02 result failed validation: " + "; ".join(errors))
    output = json.dumps(core, ensure_ascii=False, indent=2)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "status": core["status"],
            "company_economic_core": str(path),
            "case_id": core["case_id"],
            "valuation_route": core["valuation_route"]["candidate_models"],
        }, ensure_ascii=False, indent=2))
    else:
        print(output)
    return 0


def cmd_core03(args: argparse.Namespace) -> int:
    payload = load_json(args.input)
    required = ("core02_input", "forecast", "valuation_assumptions", "market_evidence", "price_evidence")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"core03 input missing required fields: {missing}")
    result = build_core03_package(
        payload["core02_input"],
        payload["forecast"],
        payload["valuation_assumptions"],
        payload["market_evidence"],
        payload["price_evidence"],
        payload.get("forecast_evidence"),
    )
    errors = validate_core03_package(result)
    if errors:
        raise ValueError("generated CORE-03 result failed validation: " + "; ".join(errors))
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "status": result["status"],
            "core03": str(path),
            "case_id": result["case_id"],
            "valuation_status": result["company_valuation"]["status"],
            "mie_status": result["p4f_market_implied_expectation"]["status"],
            "expectation_gap_status": result["expectation_gap"]["status"],
        }, ensure_ascii=False, indent=2))
    else:
        print(output)
    return 0


def _resolve_canonical_runtime(*, factory_spec: str | None, bundle: dict, output_root: str):
    """Resolve a host-approved runtime; never import code named by request data.

    A deployment may pre-register CanonicalRuntimeBindings in its host process,
    or provide a trusted module:factory through --runtime-factory /
    IIOS_CANONICAL_RUNTIME_FACTORY. The factory receives the loaded request
    bundle and output path and must return CanonicalRuntimeBindings. No test
    fixture is installed as a production default.
    """
    registered = get_canonical_runtime()
    if registered is not None:
        return registered
    if not factory_spec:
        return None
    spec = str(factory_spec).strip()
    if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", spec):
        raise ValueError("runtime factory must use trusted module:callable syntax")
    module_name, factory_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise ValueError("runtime factory callable is missing or not callable")
    runtime = factory(bundle=bundle, output_root=output_root)
    if not isinstance(runtime, CanonicalRuntimeBindings):
        raise ValueError("runtime factory must return CanonicalRuntimeBindings")
    required = (
        "request_interpreter", "request_registry", "semantic_producer",
        "producer_registry", "current_price_resolver",
        "independent_forecast_resolver", "upstream_authority_resolver",
        "valuation_output_resolver",
    )
    missing = [name for name in required if getattr(runtime, name, None) is None]
    if missing:
        raise ValueError("runtime factory has missing bindings: " + ", ".join(missing))
    return runtime


def cmd_canonical_run(args: argparse.Namespace) -> int:
    """Official natural-language investment entry. No fallback to free-form run_case."""
    try:
        bundle = load_json(args.request_bundle)
        try:
            runtime = _resolve_canonical_runtime(
                factory_spec=getattr(args, "runtime_factory", None),
                bundle=bundle,
                output_root=str(args.out),
            )
        except Exception as exc:
            print(json.dumps({
                "status": "BLOCKED",
                "canonical_decision_created": False,
                "reason": "CANONICAL_RUNTIME_FACTORY_INVALID",
                "detail": f"{type(exc).__name__}: {str(exc)[:1200]}",
                "formal_artifacts_created": False,
            }, ensure_ascii=False, indent=2))
            return 2
        if runtime is None:
            print(json.dumps({
                "status": "BLOCKED",
                "canonical_decision_created": False,
                "reason": "CANONICAL_RUNTIME_NOT_REGISTERED",
                "required": "pre-register CanonicalRuntimeBindings in the trusted host or specify --runtime-factory module:callable / IIOS_CANONICAL_RUNTIME_FACTORY",
            }, ensure_ascii=False, indent=2))
            return 2

        required = (
            "raw_request", "request_id", "run_id", "company",
            "investment_case", "evidence_manifest_path", "evidence_root",
            "artifact_type", "semantic_prompt", "decision_relevance",
        )
        missing = [key for key in required if key not in bundle or bundle[key] in (None, "")]
        if missing:
            raise ValueError("BLOCKED: canonical request bundle missing " + ", ".join(missing))

        manifest = load_json(str(bundle["evidence_manifest_path"]))
        manifest_evidence = manifest.get("evidence")
        if not isinstance(manifest_evidence, list) or not manifest_evidence:
            raise ValueError("BLOCKED: evidence manifest has no source-level evidence rows")
        evidence_refs = tuple(str(item.get("evidence_id", "")) for item in manifest_evidence)
        evidence_hashes = tuple(str(item.get("content_sha256", "")) for item in manifest_evidence)
        if any(not ref for ref in evidence_refs) or any(not digest for digest in evidence_hashes):
            raise ValueError("BLOCKED: evidence manifest rows lack evidence_id/content_sha256")

        result = run_b2e_conformance(
            raw_request=str(bundle["raw_request"]),
            request_id=str(bundle["request_id"]),
            run_id=str(bundle["run_id"]),
            created_at=str(bundle.get("created_at") or now_iso()),
            request_interpreter=runtime.request_interpreter,
            request_registry=runtime.request_registry,
            semantic_producer=runtime.semantic_producer,
            producer_registry=runtime.producer_registry,
            company=str(bundle["company"]),
            evidence_refs=evidence_refs,
            evidence_hashes=evidence_hashes,
            artifact_type=str(bundle["artifact_type"]),
            semantic_prompt=str(bundle["semantic_prompt"]),
            semantic_facts=tuple(bundle.get("semantic_facts") or ()),
            semantic_inferences=tuple(bundle.get("semantic_inferences") or ()),
            semantic_assumptions=tuple(bundle.get("semantic_assumptions") or ()),
            semantic_uncertainties=tuple(bundle.get("semantic_uncertainties") or ()),
            decision_relevance=str(bundle["decision_relevance"]),
            case=bundle["investment_case"],
            current_price_resolver=runtime.current_price_resolver,
            independent_forecast_resolver=runtime.independent_forecast_resolver,
            upstream_authority_resolver=runtime.upstream_authority_resolver,
            valuation_output_resolver=runtime.valuation_output_resolver,
            run_root=args.out,
            evidence_manifest=manifest,
            evidence_root=str(bundle["evidence_root"]),
        )
        print(json.dumps({
            "status": result.canonicality_status,
            "run_id": result.request_admission.run_id,
            "case_id": result.request_admission.case_id,
            "decision_id": result.decision_revision.get("decision_id"),
            "action": result.decision_admission.get("canonical_action"),
            "human_approval_required": True,
            "auto_execution": False,
            "run_state": result.run_state_path,
            "publication_required": True,
            "human_report_required": True,
            "message": "AI proposal only; this command does not publish a report or authorize capital execution.",
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "canonical_decision_created": False,
            "reason": str(exc),
        }, ensure_ascii=False, indent=2))
        return 2


def cmd_run(args: argparse.Namespace) -> int:
    # The legacy case-file CLI is intentionally diagnostic-only. It cannot
    # establish a raw-request Run Envelope, B2 Evidence/PIT Admission, or the
    # authorized semantic producer lineage; therefore it must not call run_case
    # or write a Decision Revision.
    try:
        case = load_json(args.case)
        identity = {
            "case_id": case.get("case_id"),
            "market": case.get("market"),
            "symbol": case.get("symbol"),
            "cutoff_date": case.get("cutoff_date"),
        }
    except Exception:
        identity = {}
    print(json.dumps({
        "status": "NON_CANONICAL",
        "canonical_decision_created": False,
        "decision_revision_created": False,
        "publication_created": False,
        "reason": "direct CLI run bypasses the canonical natural-language entry and persisted Run Envelope",
        "required_entry": "run_b2e_conformance(..., run_root=...) with registered request/semantic producers and admitted Evidence/PIT + Forecast/Valuation lineage",
        "case_identity": identity,
    }, ensure_ascii=False, indent=2))
    return 2

def cmd_replay(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    print(json.dumps(replay(snapshot), ensure_ascii=False, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    if args.series_id:
        load_series(args.out, args.series_id)
    result = approve_revision(
        args.out,
        args.decision_id,
        snapshot,
        args.approved,
        args.note,
        actor_identity=args.actor_identity,
        authorization_method=args.authorization_method,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0



def cmd_lifecycle_replay(args: argparse.Namespace) -> int:
    result = replay_decision_lifecycle(args.out, args.decision_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    try:
        path = write_machine_publication(
            args.out,
            decision_id=args.decision_id,
            published_at=args.published_at,
        )
        record = load_json(str(path))
        print(json.dumps({
            "status": "PUBLISHED",
            "publication": str(path),
            "publication_id": record["publication_id"],
            "publication_hash": record["publication_hash"],
            "decision_id": record["decision_ref"]["decision_id"],
            "revision": record["decision_ref"]["revision"],
            "currentness": record["current_projection"]["status"],
            "run_id": record["canonical_run_ref"]["run_id"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "artifact_created": False,
            "reason": str(exc),
        }, ensure_ascii=False, indent=2))
        return 2

def cmd_report(args: argparse.Namespace) -> int:
    try:
        report_path, qa_path = write_human_report(
            args.out,
            publication_path=args.publication,
            generated_at=args.generated_at,
        )
        report = load_json(str(report_path))
        qa = load_json(str(qa_path))
        print(json.dumps({
            "status": "REPORT_PUBLISHED",
            "report": str(report_path),
            "markdown": str(report_path).replace(".report.json", ".report.md"),
            "qa": str(qa_path),
            "report_id": report["report_id"],
            "report_hash": report["report_hash"],
            "qa_status": qa["qa_status"],
            "qa_hash": qa["qa_hash"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "artifact_created": False, "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2

def cmd_investor_report(args: argparse.Namespace) -> int:
    try:
        report_path, qa_path = write_investor_review_report(
            args.out,
            publication_path=args.publication,
            generated_at=args.generated_at,
        )
        report = load_json(str(report_path))
        qa = load_json(str(qa_path))
        print(json.dumps({
            "status": "INVESTOR_REVIEW_REPORT_PUBLISHED",
            "report": str(report_path),
            "markdown": str(report_path).replace(".investor-review.json", ".investor-review.md"),
            "qa": str(qa_path),
            "report_id": report["report_id"],
            "report_hash": report["report_hash"],
            "qa_status": qa["qa_status"],
            "qa_hash": qa["qa_hash"],
            "machine_publication_hash": report["publication_hash"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "artifact_created": False, "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2

def cmd_investor_report_v02(args: argparse.Namespace) -> int:
    try:
        report_path, machine_path, markdown_path, qa_path = write_investor_review_report_v02(
            args.out,
            publication_path=args.publication,
            generated_at=args.generated_at,
        )
        report = load_json(str(report_path))
        qa = load_json(str(qa_path))
        run_id = str(report["machine_report"].get("run_id") or "")
        print(json.dumps({
            "status": "INVESTOR_REVIEW_REPORT_V02_PUBLISHED",
            "report": str(report_path),
            "machine": str(machine_path),
            "markdown": str(markdown_path),
            "qa": str(qa_path),
            "report_id": report["report_id"],
            "report_hash": report["report_hash"],
            "machine_report_hash": report["machine_report_hash"],
            "human_report_hash": report["human_report_hash"],
            "qa_status": qa["qa_status"],
            "qa_hash": qa["qa_hash"],
            "run_id": run_id or None,
            "canonical_run_receipt": "issued_by_report_writer",
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "artifact_created": False, "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2

def cmd_trigger_contract(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    path = write_trigger_contract(args.out, args.decision_id, contract)
    persisted = load_json(str(path))
    print(json.dumps({"trigger_contract": str(path), "trigger_hash": persisted["trigger_hash"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_trigger_event(args: argparse.Namespace) -> int:
    event = load_json(args.event)
    path = write_trigger_event(args.out, event)
    persisted = load_json(str(path))
    print(json.dumps({"trigger_event": str(path), "trigger_event_hash": persisted["trigger_event_hash"], "trigger_state": persisted["trigger_state"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_monitor_init(args: argparse.Namespace) -> int:
    path = initialize_monitoring_state(
        args.out,
        args.trigger_id,
        args.monitor_id,
        lifecycle_status=args.lifecycle_status,
        next_due_at=args.next_due_at,
        evaluation_reference_at=args.evaluation_reference_at,
    )
    persisted = load_json(str(path))
    print(json.dumps({
        "monitoring_state": str(path),
        "state_hash": persisted["state_hash"],
        "due_state": persisted["due_state"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_monitor_apply(args: argparse.Namespace) -> int:
    path = apply_monitoring_event(args.out, args.trigger_event_id, next_due_at=args.next_due_at)
    persisted = load_json(str(path))
    print(json.dumps({
        "monitoring_state": str(path),
        "state_hash": persisted["state_hash"],
        "last_event_id": persisted["last_event_id"],
        "last_trigger_state": persisted["last_trigger_state"],
        "evaluation_status": persisted["evaluation_status"],
        "due_state": persisted["due_state"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_monitor_replay(args: argparse.Namespace) -> int:
    print(json.dumps(replay_monitoring_state(args.out, args.trigger_id), ensure_ascii=False, indent=2))
    return 0


def cmd_monitor_validate(args: argparse.Namespace) -> int:
    path = write_monitoring_validation(
        args.out,
        args.trigger_id,
        args.validation_cutoff_at,
        validation_id=args.validation_id,
    )
    persisted = load_json(str(path))
    print(json.dumps({
        "validation_record": str(path),
        "validation_id": persisted["validation_id"],
        "validation_status": persisted["validation_status"],
        "event_count": persisted["event_count"],
        "validation_hash": persisted["validation_hash"],
        "issues": persisted["issues"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_monitor_validation_replay(args: argparse.Namespace) -> int:
    print(json.dumps(
        replay_monitoring_validation(args.out, args.validation_id),
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iios-mvp", description="IIOS v0.1.1 investment-decision kernel")
    sub = p.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("intake", help="create one single-company research case from minimal input")
    intake.add_argument("symbol")
    intake.add_argument("--market", default="CN-A")
    intake.add_argument("--as-of", required=True)
    intake.add_argument("--position", required=True)
    intake.add_argument("--generated-at")
    intake.add_argument("--out")
    intake.set_defaults(func=cmd_intake)

    economic_core = sub.add_parser("economic-core", help="build Company Economic Core from admitted evidence and explicit assessments")
    economic_core.add_argument("input", help="JSON containing case + reality + trust + quality + value_core + value_driver_ranking")
    economic_core.add_argument("--generated-at")
    economic_core.add_argument("--out")
    economic_core.set_defaults(func=cmd_economic_core)

    core03 = sub.add_parser("core03", help="run real-company CORE-03 forecast, valuation and P4-F MIE boundary")
    core03.add_argument("input", help="JSON containing Core-02 input, independent forecast, valuation assumptions and market evidence")
    core03.add_argument("--out")
    core03.set_defaults(func=cmd_core03)

    run = sub.add_parser("run", help="run one investment case")
    run.add_argument("case")
    run.add_argument("--out", default="runs")
    run.add_argument("--market", default="CN-A")
    run.add_argument("--trigger-event-id")
    run.add_argument("--format", choices=("json", "markdown"), default="json")
    run.set_defaults(func=cmd_run)

    canonical_run = sub.add_parser(
        "canonical-run",
        help="official NL -> admitted evidence/semantics -> canonical Decision Kernel entry",
    )
    canonical_run.add_argument(
        "request_bundle",
        help="JSON object containing raw request, admitted-company case, evidence manifest path/root, and semantic request metadata",
    )
    canonical_run.add_argument("--out", default="runs")
    canonical_run.add_argument(
        "--runtime-factory",
        default=os.environ.get("IIOS_CANONICAL_RUNTIME_FACTORY"),
        help="trusted deployment factory as module:callable; callable(bundle=..., output_root=...) must return CanonicalRuntimeBindings",
    )
    canonical_run.set_defaults(func=cmd_canonical_run)

    rp = sub.add_parser("replay", help="replay a frozen snapshot")
    rp.add_argument("snapshot")
    rp.set_defaults(func=cmd_replay)

    lr = sub.add_parser("lifecycle-replay", help="replay and audit one canonical decision lifecycle")
    lr.add_argument("decision_id")
    lr.add_argument("--out", default="runs")
    lr.set_defaults(func=cmd_lifecycle_replay)

    pub = sub.add_parser("publish", help="publish one canonical decision revision as immutable machine-readable projection")
    pub.add_argument("decision_id")
    pub.add_argument("--published-at", required=True)
    pub.add_argument("--out", default="runs")
    pub.set_defaults(func=cmd_publish)

    rep = sub.add_parser("report", help="render the canonical Machine Publication into the compact machine/archive report and run its report quality gate")
    rep.add_argument("publication", help="canonical Machine Publication JSON")
    rep.add_argument("--generated-at", required=True)
    rep.add_argument("--out", default="runs")
    rep.set_defaults(func=cmd_report)


    inv = sub.add_parser(
        "investor-report",
        help="render the canonical Machine Publication into the Chinese investor-facing review report",
    )
    inv.add_argument("publication", help="canonical Machine Publication JSON")
    inv.add_argument("--generated-at", required=True)
    inv.add_argument("--out", default="runs")
    inv.set_defaults(func=cmd_investor_report)

    inv2 = sub.add_parser(
        "investor-report-v02",
        help="render the fail-closed dual-surface Investor Review Report v0.2",
    )
    inv2.add_argument("publication", help="canonical Machine Publication JSON")
    inv2.add_argument("--generated-at", required=True)
    inv2.add_argument("--out", default="runs")
    inv2.set_defaults(func=cmd_investor_report_v02)

    ap = sub.add_parser("approve", help="record separate human approval")
    ap.add_argument("snapshot")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--decision-id", required=True)
    ap.add_argument("--series-id")
    ap.add_argument("--approved", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--actor-identity", required=True)
    ap.add_argument("--authorization-method", default="HUMAN_AUTHENTICATED", choices=("HUMAN_AUTHENTICATED",))
    ap.set_defaults(func=cmd_approve)

    tc = sub.add_parser("trigger-contract", help="persist a reusable trigger contract")
    tc.add_argument("contract")
    tc.add_argument("--decision-id", required=True)
    tc.add_argument("--out", default="runs")
    tc.set_defaults(func=cmd_trigger_contract)

    te = sub.add_parser("trigger-event", help="persist a normalized external trigger event")
    te.add_argument("event")
    te.add_argument("--out", default="runs")
    te.set_defaults(func=cmd_trigger_event)

    mi = sub.add_parser("monitor-init", help="initialize canonical monitoring state for a trigger")
    mi.add_argument("trigger_id")
    mi.add_argument("--monitor-id", required=True)
    mi.add_argument("--lifecycle-status", choices=("ACTIVE", "DISABLED", "RETIRED"), default="ACTIVE")
    mi.add_argument("--next-due-at")
    mi.add_argument("--evaluation-reference-at")
    mi.add_argument("--out", default="runs")
    mi.set_defaults(func=cmd_monitor_init)

    ma = sub.add_parser("monitor-apply", help="apply one canonical trigger event to monitoring state")
    ma.add_argument("trigger_event_id")
    ma.add_argument("--next-due-at")
    ma.add_argument("--out", default="runs")
    ma.set_defaults(func=cmd_monitor_apply)

    mr = sub.add_parser("monitor-replay", help="replay monitoring state from canonical trigger events")
    mr.add_argument("trigger_id")
    mr.add_argument("--out", default="runs")
    mr.set_defaults(func=cmd_monitor_replay)

    mv = sub.add_parser(
        "monitor-validate",
        help="validate and persist the monitoring transition/replay evidence chain",
    )
    mv.add_argument("trigger_id")
    mv.add_argument("--validation-cutoff-at", required=True)
    mv.add_argument("--validation-id")
    mv.add_argument("--out", default="runs")
    mv.set_defaults(func=cmd_monitor_validate)

    mvr = sub.add_parser(
        "monitor-validation-replay",
        help="replay a persisted monitoring validation record from source state",
    )
    mvr.add_argument("validation_id")
    mvr.add_argument("--out", default="runs")
    mvr.set_defaults(func=cmd_monitor_validation_replay)
    return p


def main() -> int:
    args = parser()
    ns = args.parse_args()
    try:
        return ns.func(ns)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
