from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import replay, render_markdown, run_case
from .store import read_snapshot, write_human_approval, write_snapshot


def load_json(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def cmd_run(args: argparse.Namespace) -> int:
    case = load_json(args.case)
    snapshot, snapshot_hash = run_case(case)
    out = write_snapshot(args.out, snapshot)
    if args.format == "markdown":
        print(render_markdown(snapshot))
    else:
        print(json.dumps({"snapshot": str(out), "snapshot_hash": snapshot_hash, "action": snapshot["decision"]["decision"]["action"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    print(json.dumps(replay(snapshot), ensure_ascii=False, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    snapshot = read_snapshot(args.snapshot)
    path = write_human_approval(args.out, snapshot, args.approved, args.note)
    print(json.dumps({"human_approval": str(path), "approved": args.approved, "snapshot_hash": snapshot["snapshot_hash"]}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iios-mvp", description="IIOS minimal investment-decision kernel")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one investment case")
    run.add_argument("case")
    run.add_argument("--out", default="runs")
    run.add_argument("--format", choices=("json", "markdown"), default="json")
    run.set_defaults(func=cmd_run)

    rp = sub.add_parser("replay", help="replay a frozen snapshot")
    rp.add_argument("snapshot")
    rp.set_defaults(func=cmd_replay)

    ap = sub.add_parser("approve", help="record separate human approval")
    ap.add_argument("snapshot")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--approved", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--note", required=True)
    ap.set_defaults(func=cmd_approve)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
