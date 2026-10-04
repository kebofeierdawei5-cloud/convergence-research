from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .engine import replay, render_markdown, run_case
from .store import (
    approve_revision,
    create_or_load_series,
    load_series,
    next_revision,
    read_snapshot,
    write_decision_revision,
    write_human_approval,
    write_snapshot,
    write_trigger_contract,
    write_trigger_event,
)


def load_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd_run(args: argparse.Namespace) -> int:
    case = load_json(args.case)
    snapshot, snapshot_hash = run_case(case)
    out = write_snapshot(args.out, snapshot)
    series = create_or_load_series(
        args.out, args.market, case["symbol"], case["company"], now_iso()
    )
    revision = next_revision(args.out, series["decision_series_id"])
    decision_path = write_decision_revision(
        args.out, series["decision_series_id"], revision, snapshot,
        run_id=snapshot_hash[:16], trigger_event_id=args.trigger_event_id,
    )
    index_path = Path(args.out) / f"{series['decision_series_id']}.index.json"
    index_path.write_text(
        json.dumps({"next_revision": revision + 1}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n"
    )
    if args.format == "markdown":
        print(render_markdown(snapshot))
    else:
        print(json.dumps({
            "snapshot": str(out), "snapshot_hash": snapshot_hash,
            "decision_id": f"{series['decision_series_id']}-r{revision:03d}",
            "decision": snapshot["decision"]["decision"]["action"],
            "decision_revision": str(decision_path),
            "engine_version": snapshot["engine_version"],
        }, ensure_ascii=False, indent=2))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    print(json.dumps(replay(snapshot), ensure_ascii=False, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    series = load_series(args.out, args.series_id) if args.series_id else {}
    decision_id = args.decision_id
    if not decision_id and series:
        raise ValueError("decision_id is required when approving a revision")
    if not decision_id:
        raise ValueError("decision_id is required")
    result = approve_revision(args.out, decision_id, snapshot, args.approved, args.note)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_trigger_contract(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    path = write_trigger_contract(args.out, args.decision_id, contract)
    print(json.dumps({"trigger_contract": str(path), "trigger_hash": contract.get("trigger_hash")}, ensure_ascii=False, indent=2))
    return 0


def cmd_trigger_event(args: argparse.Namespace) -> int:
    event = load_json(args.event)
    path = write_trigger_event(args.out, event)
    print(json.dumps({"trigger_event": str(path), "trigger_event_hash": event.get("trigger_event_hash")}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iios-mvp", description="IIOS v0.1.1 investment-decision kernel")
    sub = p.add_subparsers(dest="command", required=True)

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
