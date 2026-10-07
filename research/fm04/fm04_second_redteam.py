from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
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


def run_current_audit(result_path: Path, state_path: Path) -> bool:
    with env(FM04_BACKTEST_RESULT=result_path, FM03_STATE_SNAPSHOT=state_path):
        try:
            rc = audit.main()
        except AssertionError:
            return False
        return rc == 0


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_rejection(label: str, result: dict, state_path: Path, path: Path, mutate) -> dict:
    mutated = copy.deepcopy(result)
    mutate(mutated)
    write_json(path, mutated)
    accepted = run_current_audit(path, state_path)
    return {
        "attack": label,
        "expected": "REJECT",
        "observed": "ACCEPT" if accepted else "REJECT",
        "vulnerable": accepted,
    }


def main() -> int:
    root = Path("research")
    contract = load_json(root / "fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json")
    states = load_ndjson(Path(os.environ["FM03_STATE_SNAPSHOT"]))
    records = load_ndjson(root / "fm01/CATL_DRIVER_HISTORY.ndjson")
    lock = load_json(root / "fm00/OU-M12-FM00-CATL-001.json")

    result = build_result(contract, states, lock, records)
    result_path = Path("/tmp/fm04-redteam-baseline.json")
    state_path = Path(os.environ["FM03_STATE_SNAPSHOT"])
    write_json(result_path, result)

    assert run_current_audit(result_path, state_path), "BASELINE_AUDIT_DID_NOT_PASS"

    attacks = []
    def populated_group_index(x):
        for i, group in enumerate(x["conditional_performance"]):
            if group.get("common_outer_sample_size", 0) > 0:
                return i
        raise AssertionError("NO_POPULATED_CONDITIONAL_GROUP")
    def tr01(x):
        i = populated_group_index(x)
        x["conditional_performance"][i]["models"]["SEASONAL_NAIVE"]["metrics"]["MAE"] += 1.0
    attacks.append(require_rejection(
        "TR-01 mutate conditional_performance metric",
        result,
        state_path,
        Path("/tmp/fm04-redteam-tr01.json"),
        tr01,
    ))
    attacks.append(require_rejection(
        "TR-02 mutate conditional_performance length",
        result,
        state_path,
        Path("/tmp/fm04-redteam-tr02.json"),
        lambda x: x["conditional_performance"].append(copy.deepcopy(x["conditional_performance"][populated_group_index(x)])),
    ))
    attacks.append(require_rejection(
        "TR-03 mutate driver history canonical binding",
        result,
        state_path,
        Path("/tmp/fm04-redteam-tr03.json"),
        lambda x: x["input_bindings"].__setitem__("driver_history_canonical_sha256", "0" * 64),
    ))
    attacks.append(require_rejection(
        "TR-04 mutate selected model counts",
        result,
        state_path,
        Path("/tmp/fm04-redteam-tr04.json"),
        lambda x: x["summary"]["selected_model_counts"].__setitem__("SEASONAL_NAIVE", 999),
    ))
    attacks.append(require_rejection(
        "TR-05 mutate conditional group state value",
        result,
        state_path,
        Path("/tmp/fm04-redteam-tr05.json"),
        lambda x: x["conditional_performance"][populated_group_index(x)].__setitem__("state_value", "FORGED_STATE"),
    ))

    # Independent static weakness check: a unit test contains a blanket exception
    # which can swallow its own assertion failure.
    test_source = (root / "fm04/tests/test_fm04_conditional_backtest.py").read_text(encoding="utf-8")
    blanket_exception = "except Exception:\n                            pass" in test_source
    static = {
        "attack": "TR-06 blanket exception in future-input unit test",
        "expected": "NO_SWALLOWING_ASSERTIONS",
        "observed": "BLANKET_EXCEPTION_FOUND" if blanket_exception else "NOT_FOUND",
        "vulnerable": blanket_exception,
    }

    print(json.dumps({
        "baseline_audit": "PASS",
        "attacks": attacks,
        "static": static,
        "vulnerable_count": sum(int(x["vulnerable"]) for x in attacks) + int(static["vulnerable"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
