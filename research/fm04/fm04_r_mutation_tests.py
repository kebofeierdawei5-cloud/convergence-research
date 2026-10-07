from __future__ import annotations

import copy
import json
import os
import tempfile
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path

from fm04_conditional_backtest import build_result, load_json, load_ndjson
import fm04_independent_audit as audit


@contextmanager
def env(**values):
    old = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            os.environ[k] = str(v)
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_audit(result_path: Path, state_path: Path) -> str:
    with env(FM04_BACKTEST_RESULT=result_path, FM03_STATE_SNAPSHOT=state_path):
        try:
            with redirect_stdout(StringIO()):
                rc = audit.main()
        except AssertionError:
            return "REJECT"
        except Exception as exc:
            return f"ERROR:{type(exc).__name__}"
        return "ACCEPT" if rc == 0 else f"ERROR:RC_{rc}"


def main() -> int:
    root = Path("research")
    contract = load_json(root / "fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json")
    state_path = Path(os.environ["FM03_STATE_SNAPSHOT"])
    states = load_ndjson(state_path)
    records = load_ndjson(root / "fm01/CATL_DRIVER_HISTORY.ndjson")
    lock = load_json(root / "fm00/OU-M12-FM00-CATL-001.json")
    baseline = build_result(contract, states, lock, records)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        baseline_path = tmp_path / "baseline.json"
        write_json(baseline_path, baseline)
        assert run_audit(baseline_path, state_path) == "ACCEPT", "BASELINE_AUDIT_FAILED"

        attacks = []

        def attack(label, mutate):
            value = copy.deepcopy(baseline)
            mutate(value)
            path = tmp_path / (label + ".json")
            write_json(path, value)
            observed = run_audit(path, state_path)
            attacks.append({"attack": label, "expected": "REJECT", "observed": observed})
            assert observed == "REJECT", f"{label}:{observed}"

        attack("mutate_group_definition_state_value",
               lambda x: x["conditional_group_definitions"][0].__setitem__("state_value", "FORGED_STATE"))
        attack("append_group_definition",
               lambda x: x["conditional_group_definitions"].append(copy.deepcopy(x["conditional_group_definitions"][0])))
        attack("mutate_selection_eligibility",
               lambda x: x["selection_eligibility"][0].__setitem__("eligible", True))
        attack("mutate_driver_history_binding",
               lambda x: x["input_bindings"].__setitem__("driver_history_git_blob_sha", "0" * 40))
        attack("mutate_selected_count",
               lambda x: x["summary"].__setitem__("selected_count", 1))
        attack("inject_forged_empirical_performance",
               lambda x: x["conditional_empirical_performance"].append({
                   "performance_id": "FM04-EMP-FORGED",
                   "group_id": x["conditional_group_definitions"][0]["group_id"],
                   "driver_id": x["conditional_group_definitions"][0]["driver_id"],
                   "horizon": x["conditional_group_definitions"][0]["horizon"],
                   "state_dimension": x["conditional_group_definitions"][0]["state_dimension"],
                   "state_value": x["conditional_group_definitions"][0]["state_value"],
                   "common_outer_sample_size": 1,
                   "common_outer_origins": ["FORGED"],
                   "observations": [],
                   "models": {},
                   "selection_eligible": False,
                   "descriptive_only": True,
               }))

    print(json.dumps({"baseline": "ACCEPT", "attacks": attacks}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
