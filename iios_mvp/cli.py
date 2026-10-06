from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .company_economic_core import build_company_economic_core, validate_company_economic_core
from .core03_market_expectation import build_core03_package, validate_core03_package
from .engine import replay, render_markdown, run_case
from .research_intake import build_research_case
from .machine_publication import write_machine_publication
from .human_report import write_human_report
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


def cmd_run(args: argparse.Namespace) -> int:
    case = load_json(args.case)
    snapshot, snapshot_hash = run_case(case)
    out = write_snapshot(args.out, snapshot)
    series = create_or_load_series(
        args.out, args.market, case["symbol"], case["company"], now_iso()
    )
    revision = next_revision(args.out, series["decision_series_id"])
    decision_path = write_decision_revision(
        args.out,
        series["decision_series_id"],
        revision,
        snapshot,
        run_id=snapshot_hash[:16],
        trigger_event_id=args.trigger_event_id,
    )
    if args.format == "markdown":
        print(render_markdown(snapshot))
    else:
        print(json.dumps({
            "snapshot": str(out),
            "snapshot_hash": snapshot_hash,
            "decision_id": f"{series['decision_series_id']}-r{revision:03d}",
            "decision": snapshot["decision"]["decision"]["action"],
            "decision_revision": str(decision_path),
            "next_revision": next_revision(args.out, series["decision_series_id"]),
            "engine_version": snapshot["engine_version"],
        }, ensure_ascii=False, indent=2))
    return 0


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
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0



def cmd_lifecycle_replay(args: argparse.Namespace) -> int:
    result = replay_decision_lifecycle(args.out, args.decision_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
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
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
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

    rep = sub.add_parser("report", help="render a canonical machine publication into an immutable human-readable report and run the report quality gate")
    rep.add_argument("publication", help="canonical Machine Publication JSON")
    rep.add_argument("--generated-at", required=True)
    rep.add_argument("--out", default="runs")
    rep.set_defaults(func=cmd_report)


    ap = sub.add_parser("approve", help="record separate human approval")
    ap.add_argument("snapshot")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--decision-id", required=True)
    ap.add_argument("--series-id")
    ap.add_argument("--approved", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--note", required=True)
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
