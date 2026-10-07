from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ8 = timezone(timedelta(hours=8))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def qkey(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def qadd(period: str, offset: int) -> str:
    y, q = qkey(period)
    n = (y * 4 + (q - 1)) + offset
    return f"{n // 4}Q{n % 4 + 1}"


def qcutoff(period: str) -> datetime:
    y, q = qkey(period)
    month = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return datetime(y, month, day, 23, 59, 59, tzinfo=TZ8)


def canonical_sha(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research/fm01/CATL_DRIVER_HISTORY.ndjson")
    ap.add_argument("--source-manifest", default="research/fm01/M1_1_EXACT_SOURCE_SNAPSHOT_MANIFEST.json")
    ap.add_argument("--admission", default="research/fm01/M1_1_SOURCE_ADMISSION.json")
    args = ap.parse_args()

    dataset = load_ndjson(Path(args.dataset))
    sm = load_json(Path(args.source_manifest))
    admission = load_json(Path(args.admission))

    assert sm["status"] == "ADMITTED"
    assert admission["status"] == "PASS"
    assert len(dataset) == 44

    periods = sorted({r["period"] for r in dataset if r["driver_id"] == "REVENUE"}, key=qkey)
    assert len(periods) == 22
    assert periods[0] == "2021Q1" and periods[-1] == "2026Q2"

    by_driver_period = {(r["driver_id"], r["period"]): r for r in dataset}
    assert len(by_driver_period) == 44

    source_by_id = {x["source_evidence_ref"]: x for x in sm["source_records"]}
    for r in dataset:
        assert r["source_ref"] in source_by_id
        assert r["known_at"] == source_by_id[r["source_ref"]]["published_at"]
        if r["provenance"] == "DIRECT_PERIODIC_FILING":
            assert r["transformation_type"] == "NONE"
            assert r["input_record_ids"] == []
            assert r["formula"] is None
        else:
            assert r["input_record_ids"]
            assert r["formula"]
            assert r["transformation_type"] in {"H1_MINUS_Q1", "ANNUAL_MINUS_Q1_Q2_Q3"}

    horizons = {"3M": (1, 11), "6M": (2, 10), "12M": (4, 8)}
    origins = []
    for off, horizon in [(i, "3M") for i in range(11)]:
        origins.append(("3M", qadd("2023Q3", off), 1))
    for off in range(10):
        origins.append(("6M", qadd("2023Q3", off), 2))
    for off in range(8):
        origins.append(("12M", qadd("2023Q3", off), 4))

    replay_rows = []
    for horizon, origin, offset in origins:
        cutoff = qcutoff(origin)
        visible = {}
        for driver in ("REVENUE", "NET_PROFIT"):
            rows = [
                r for r in dataset
                if r["driver_id"] == driver
                and datetime.fromisoformat(r["known_at"]) <= cutoff
            ]
            visible_periods = sorted({r["period"] for r in rows}, key=qkey)
            visible[driver] = visible_periods
            assert all(datetime.fromisoformat(r["known_at"]) <= cutoff for r in rows)
            target = qadd(origin, offset)
            assert target not in visible_periods
            target_record = by_driver_period[(driver, target)]
            assert datetime.fromisoformat(target_record["known_at"]) > cutoff
        replay_rows.append({
            "horizon": horizon,
            "origin": origin,
            "cutoff": cutoff.isoformat(),
            "history_count_revenue": len(visible["REVENUE"]),
            "history_count_net_profit": len(visible["NET_PROFIT"]),
            "target_period": qadd(origin, offset),
            "target_excluded": True
        })

    counts = {
        "3M": sum(1 for x in replay_rows if x["horizon"] == "3M"),
        "6M": sum(1 for x in replay_rows if x["horizon"] == "6M"),
        "12M": sum(1 for x in replay_rows if x["horizon"] == "12M")
    }
    assert counts == {"3M": 11, "6M": 10, "12M": 8}

    result = {
        "schema_version": "IIOS-FM01-INDEPENDENT-PIT-REPLAY-0.1",
        "status": "PASS",
        "source_manifest_id": sm["manifest_id"],
        "admission_id": admission["admission_id"],
        "records": len(dataset),
        "quarters": periods,
        "origin_counts": counts,
        "target_actual_excluded_from_training": all(x["target_excluded"] for x in replay_rows),
        "replay_rows": replay_rows
    }
    result["replay_sha256"] = canonical_sha(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
