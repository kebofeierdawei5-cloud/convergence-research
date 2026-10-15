from __future__ import annotations

"""One-command macOS wrapper for the existing local IIOS pilot + verified Replay.

This module orchestrates the existing pilot CLI; it does not implement a second
valuation, decision, receipt, or replay engine.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path.home() / ".iios-private"
PILOT_ROOT = PRIVATE_ROOT / "local-pilot"
INPUT_ROOT = PILOT_ROOT / "inputs"
RUN_ROOT = PILOT_ROOT / "runs"
LOG_ROOT = PILOT_ROOT / "acceptance-logs"

PILOT_MODULE = "iios_mvp.local_investment_pilot_v01"
PILOT_STATUS = "PILOT_NON_CANONICAL"
ANALYSIS_SCHEMA = "IIOS-LOCAL-INVESTMENT-PILOT-ANALYSIS-0.1"
RECEIPT_SCHEMA = "IIOS-LOCAL-PILOT-RUN-RECORD-0.1"
RESULT_ID_PATTERN = re.compile(r"^local-pilot-[A-Za-z0-9._-]+$")
REQUIRED_ANALYSIS_FIELDS = (
    "case",
    "price_input",
    "assessment",
    "evidence_register",
    "forecast_valuation",
    "operating_driver_forecast",
    "valuation_transmission",
    "operator_valuation_context",
    "price_zone_sensitivity",
    "decision_parameters",
    "portfolio_package",
    "return_metrics",
    "thesis_break_stress_review",
    "decision",
    "governance",
)


class AcceptanceError(RuntimeError):
    """An actionable failure in the local run / Replay acceptance wrapper."""


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _ensure_private_directory(path: Path) -> None:
    """Create a private directory and tighten its mode without following symlinks."""
    if path.is_symlink():
        raise AcceptanceError(f"PRIVATE_PATH_MUST_NOT_BE_SYMLINK:{path}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise AcceptanceError(f"PRIVATE_PATH_MUST_BE_DIRECTORY:{path}")
    if os.name != "nt":
        path.chmod(0o700)
        if path.stat().st_mode & 0o077:
            raise AcceptanceError(f"PRIVATE_DIRECTORY_PERMISSIONS_NOT_PRIVATE:{path}")


def _prepare_private_roots() -> None:
    # Apply from outer to inner. No private input, price, or research result is
    # written into Git; the existing pilot continues to own the run bundle.
    for path in (PRIVATE_ROOT, PILOT_ROOT, INPUT_ROOT, RUN_ROOT, LOG_ROOT):
        _ensure_private_directory(path)


def _new_log(stage: str) -> Path:
    safe_stage = re.sub(r"[^A-Za-z0-9_-]", "-", stage)
    return LOG_ROOT / f"{_stamp()}-{safe_stage}.log"


def _base_environment() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPOSITORY_ROOT) + (os.pathsep + current if current else "")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _stream_command(command: list[str], log_path: Path) -> int:
    """Run a command with terminal-visible output and a private, complete log."""
    with log_path.open("x", encoding="utf-8") as log:
        if os.name != "nt":
            # chmod is a filesystem operation; TextIOWrapper has no chmod method.
            # LOG_ROOT is already private, and this tightens the file itself.
            log_path.chmod(0o600)
        try:
            process = subprocess.Popen(
                command,
                cwd=str(REPOSITORY_ROOT),
                env=_base_environment(),
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise AcceptanceError(f"COMMAND_START_FAILED:{command[0]}:{exc}") from exc

        assert process.stdout is not None
        try:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                log.flush()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
        return process.wait()


def _extract_cli_result(log_path: Path, expected_statuses: Iterable[str]) -> dict[str, Any]:
    """Find a complete JSON result object in a log that may also contain prompts."""
    content = log_path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    expected = set(expected_statuses)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for index, char in enumerate(content):
        if char != "{":
            continue
        try:
            item, _end = decoder.raw_decode(content, index)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or item.get("status") not in expected:
            continue
        has_run_identity = isinstance(item.get("pilot_id"), str)
        has_required_path = (
            isinstance(item.get("run_dir"), str)
            or item.get("status") == "PILOT_BUNDLE_HASH_CHECK_PASS"
        )
        if has_run_identity and has_required_path:
            candidates.append((index, item))
    if not candidates:
        raise AcceptanceError(
            "CLI_RESULT_JSON_NOT_FOUND; inspect the private log: " + str(log_path)
        )
    return candidates[-1][1]


def _run_cli(
    args: list[str],
    *,
    stage: str,
    expected_statuses: Iterable[str],
) -> dict[str, Any]:
    log_path = _new_log(stage)
    command = [sys.executable, "-m", PILOT_MODULE, *args]
    return_code = _stream_command(command, log_path)
    if return_code != 0:
        raise AcceptanceError(
            f"{stage.upper()}_COMMAND_EXITED_{return_code}; inspect the private log: {log_path}"
        )
    return _extract_cli_result(log_path, expected_statuses)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"{label}_JSON_UNREADABLE:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label}_JSON_MUST_BE_OBJECT:{path}")
    return value


def _assert_private_mode(path: Path, *, directory: bool) -> None:
    if os.name == "nt":
        return
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        kind = "DIRECTORY" if directory else "FILE"
        raise AcceptanceError(f"{kind}_PERMISSIONS_TOO_OPEN:{path}:{mode:04o}")


def _inspect_bundle(run_dir: Path, *, expected_replay_of: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check schema, decision-material presence, and no-trade declarations."""
    if not run_dir.is_dir():
        raise AcceptanceError(f"RUN_DIRECTORY_NOT_FOUND:{run_dir}")
    _assert_private_mode(run_dir, directory=True)

    receipt = _read_json(run_dir / "pilot_receipt.json", "RUN_RECEIPT")
    analysis = _read_json(run_dir / "analysis.json", "ANALYSIS")
    report_path = run_dir / "report.md"
    if not report_path.is_file() or report_path.stat().st_size == 0:
        raise AcceptanceError(f"REPORT_MISSING_OR_EMPTY:{report_path}")
    report_path.read_text(encoding="utf-8")
    for name in ("input.json", "analysis.json", "report.md", "pilot_receipt.json"):
        file_path = run_dir / name
        if not file_path.is_file():
            raise AcceptanceError(f"RUN_FILE_MISSING:{file_path}")
        _assert_private_mode(file_path, directory=False)

    if receipt.get("receipt_schema") != RECEIPT_SCHEMA:
        raise AcceptanceError(f"RUN_RECEIPT_SCHEMA_MISMATCH:{run_dir.name}")
    if receipt.get("status") != PILOT_STATUS:
        raise AcceptanceError(f"RUN_RECEIPT_NOT_NON_CANONICAL:{run_dir.name}")
    if receipt.get("pilot_id") != run_dir.name:
        raise AcceptanceError(f"RUN_RECEIPT_ID_MISMATCH:{run_dir.name}")
    if receipt.get("replay_of") != expected_replay_of:
        raise AcceptanceError(
            f"RUN_RECEIPT_REPLAY_PARENT_MISMATCH:{run_dir.name}:"
            f"expected={expected_replay_of!r}:actual={receipt.get('replay_of')!r}"
        )
    if analysis.get("schema_version") != ANALYSIS_SCHEMA:
        raise AcceptanceError(f"ANALYSIS_SCHEMA_MISMATCH:{run_dir.name}")
    if analysis.get("status") != PILOT_STATUS:
        raise AcceptanceError(f"ANALYSIS_NOT_NON_CANONICAL:{run_dir.name}")
    if analysis.get("pilot_id") != run_dir.name:
        raise AcceptanceError(f"ANALYSIS_ID_MISMATCH:{run_dir.name}")
    missing = [field for field in REQUIRED_ANALYSIS_FIELDS if field not in analysis]
    if missing:
        raise AcceptanceError(f"ANALYSIS_MISSING_REQUIRED_FIELDS:{','.join(missing)}")
    decision = analysis.get("decision")
    if not isinstance(decision, dict) or not decision.get("provisional_action"):
        raise AcceptanceError(f"ANALYSIS_DECISION_ACTION_MISSING:{run_dir.name}")
    if not isinstance(analysis.get("valuation_transmission"), dict):
        raise AcceptanceError(f"B5_VALUATION_TRANSMISSION_MISSING:{run_dir.name}")
    if not isinstance(analysis.get("price_zone_sensitivity"), dict):
        raise AcceptanceError(f"B6_PRICE_ZONE_SENSITIVITY_MISSING:{run_dir.name}")

    governance = analysis.get("governance")
    if not isinstance(governance, dict):
        raise AcceptanceError(f"ANALYSIS_GOVERNANCE_MISSING:{run_dir.name}")
    for field in ("formal_decision_created", "canonical_run_receipt_created", "execution_authorized", "auto_execution"):
        if governance.get(field) is not False:
            raise AcceptanceError(f"NO_TRADE_BOUNDARY_NOT_FALSE:{run_dir.name}:{field}")
    for field in ("formal_decision_created", "canonical_run_receipt_created", "execution_authorized", "auto_execution"):
        if receipt.get(field) is not False:
            raise AcceptanceError(f"RECEIPT_NO_TRADE_BOUNDARY_NOT_FALSE:{run_dir.name}:{field}")
    if receipt.get("canonical_run_receipt_created") is not False:
        raise AcceptanceError(f"NON_CANONICAL_RECEIPT_FLAG_INVALID:{run_dir.name}")
    return analysis, receipt


def _prompt_completion_issues(analysis: dict[str, Any]) -> list[str]:
    """Identify user-skipped inputs without converting UNKNOWN into a pass."""
    issues: list[str] = []
    package = analysis.get("portfolio_package")
    if not isinstance(package, dict) or package.get("status") == "NOT_PROVIDED":
        issues.append("组合风险预算/仓位包被明确跳过，完整输入验收未通过。")

    valuation_context = analysis.get("operator_valuation_context")
    if not isinstance(valuation_context, dict):
        issues.append("缺少操作者确认的 B5 主估值模型选择。")
        return issues
    family = valuation_context.get("selected_model_family")
    if not isinstance(family, str) or family in {"", "UNKNOWN"}:
        issues.append("B5 主估值模型仍为 UNKNOWN；请在后续正式复验中明确选择。")
    elif family == "EPS_MULTIPLE" and not isinstance(valuation_context.get("baseline_includes_project"), bool):
        issues.append("EPS_MULTIPLE 模型未确认原估值是否已包含项目，B5 传导保持关闭。")
    return issues


def _list_original_runs() -> list[Path]:
    candidates: list[Path] = []
    if not RUN_ROOT.is_dir():
        return candidates
    for path in RUN_ROOT.iterdir():
        if not path.is_dir() or not RESULT_ID_PATTERN.fullmatch(path.name):
            continue
        try:
            receipt = _read_json(path / "pilot_receipt.json", "RUN_RECEIPT")
        except AcceptanceError:
            continue
        if (
            receipt.get("status") == PILOT_STATUS
            and receipt.get("pilot_id") == path.name
            and receipt.get("replay_of") is None
        ):
            candidates.append(path)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def _list_all_runs() -> list[Path]:
    candidates: list[Path] = []
    if not RUN_ROOT.is_dir():
        return candidates
    for path in RUN_ROOT.iterdir():
        if not path.is_dir() or not RESULT_ID_PATTERN.fullmatch(path.name):
            continue
        if (path / "pilot_receipt.json").is_file():
            candidates.append(path)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def _select_run(*, original_only: bool) -> Path:
    candidates = _list_original_runs() if original_only else _list_all_runs()
    candidates = candidates[:30]
    if not candidates:
        if original_only:
            raise AcceptanceError("NO_ORIGINAL_PILOT_RUNS_FOUND; first complete a run from option 1.")
        raise AcceptanceError("NO_PILOT_RUNS_FOUND; first complete a local run.")
    print("\n请选择运行目录（最新的在最上方）：")
    for number, path in enumerate(candidates, start=1):
        try:
            receipt = _read_json(path / "pilot_receipt.json", "RUN_RECEIPT")
            analysis = _read_json(path / "analysis.json", "ANALYSIS")
            case = analysis.get("case") if isinstance(analysis.get("case"), dict) else {}
            label = f"{case.get('company', 'UNKNOWN')} / {case.get('symbol', 'UNKNOWN')}"
            kind = "首次运行" if receipt.get("replay_of") is None else f"Replay of {receipt.get('replay_of')}"
        except AcceptanceError:
            label, kind = "需检查的运行包", "无法读取元数据"
        print(f"  {number:2d}. {path.name}  |  {label}  |  {kind}")
    while True:
        response = input("输入编号（输入 0 取消）：").strip()
        if response == "0":
            raise AcceptanceError("OPERATOR_CANCELLED")
        if response.isdigit() and 1 <= int(response) <= len(candidates):
            chosen = candidates[int(response) - 1]
            if original_only:
                receipt = _read_json(chosen / "pilot_receipt.json", "RUN_RECEIPT")
                if receipt.get("replay_of") is not None:
                    raise AcceptanceError("REPLAY_INPUT_MUST_BE_ORIGINAL_RUN")
            return chosen
        print("编号无效，请输入列表中的编号。")


def _verify_and_replay(original_dir: Path) -> int:
    original_dir = original_dir.expanduser().resolve(strict=True)
    if original_dir.parent != RUN_ROOT.resolve():
        raise AcceptanceError(f"RUN_DIRECTORY_NOT_DIRECT_CHILD_OF_PRIVATE_RUN_ROOT:{original_dir}")
    if not RESULT_ID_PATTERN.fullmatch(original_dir.name):
        raise AcceptanceError("PILOT_ID_FORMAT_INVALID")

    print("\n[1/4] 校验首次运行包：input.json / analysis.json / report.md 与 receipt 的哈希和字节数")
    _run_cli(
        ["--check-run", str(original_dir)],
        stage=f"check-original-{original_dir.name}",
        expected_statuses={"PILOT_BUNDLE_HASH_CHECK_PASS"},
    )
    original_analysis, original_receipt = _inspect_bundle(original_dir, expected_replay_of=None)

    print("\n[2/4] 使用首次运行的原始 input.json 执行真正的 Replay 重算与决策材料比较")
    replay_result = _run_cli(
        ["--replay-run", str(original_dir), "--output-root", str(RUN_ROOT)],
        stage=f"replay-{original_dir.name}",
        expected_statuses={"PILOT_REPLAY_MATCHED", "PILOT_REPLAY_MISMATCH"},
    )
    if replay_result.get("status") != "PILOT_REPLAY_MATCHED":
        mismatches = replay_result.get("replay_comparison", {}).get("mismatched_fields", [])
        raise AcceptanceError(f"REPLAY_NOT_MATCHED:{mismatches!r}")

    replay_dir = Path(str(replay_result.get("run_dir", ""))).expanduser().resolve(strict=True)
    if replay_dir.parent != RUN_ROOT.resolve():
        raise AcceptanceError("REPLAY_OUTPUT_OUTSIDE_PRIVATE_RUN_ROOT")
    if replay_result.get("replay_of") != original_dir.name:
        raise AcceptanceError("REPLAY_RESULT_PARENT_ID_MISMATCH")
    comparison = replay_result.get("replay_comparison")
    if not isinstance(comparison, dict):
        raise AcceptanceError("REPLAY_COMPARISON_MISSING")
    if (
        comparison.get("status") != "MATCH"
        or comparison.get("hash_verification") != "PASS"
        or comparison.get("prior_pilot_id") != original_analysis.get("pilot_id")
        or comparison.get("mismatched_fields") != []
    ):
        raise AcceptanceError("REPLAY_DECISION_MATERIAL_COMPARISON_INVALID")

    replay_analysis, replay_receipt = _inspect_bundle(
        replay_dir,
        expected_replay_of=original_dir.name,
    )
    persisted_comparison = replay_receipt.get("replay_comparison")
    if not isinstance(persisted_comparison, dict):
        raise AcceptanceError("REPLAY_RECEIPT_COMPARISON_MISSING")
    for key in ("status", "hash_verification", "prior_pilot_id", "mismatched_fields"):
        if persisted_comparison.get(key) != comparison.get(key):
            raise AcceptanceError(f"REPLAY_RECEIPT_COMPARISON_MISMATCH:{key}")

    print("\n[3/4] 校验 Replay 输出包自身的文件哈希和字节数")
    _run_cli(
        ["--check-run", str(replay_dir)],
        stage=f"check-replay-{replay_dir.name}",
        expected_statuses={"PILOT_BUNDLE_HASH_CHECK_PASS"},
    )

    prompt_issues = _prompt_completion_issues(original_analysis)
    replay_prompt_issues = _prompt_completion_issues(replay_analysis)
    if prompt_issues != replay_prompt_issues:
        raise AcceptanceError("REPLAY_PROMPT_COMPLETENESS_DRIFT")

    print("\n[4/4] 全流程结果")
    print(f"  首次运行：{original_dir}")
    print(f"  Replay 运行：{replay_dir}")
    print(f"  首次报告：{original_dir / 'report.md'}")
    print(f"  首次分析：{original_dir / 'analysis.json'}")
    print(f"  首次记录：{original_dir / 'pilot_receipt.json'}")
    print(f"  Replay 比较：MATCH（比较字段数：{len(comparison.get('compared_fields', []))}）")
    print("  首次包哈希：PASS；Replay 包哈希：PASS")
    print("  非正式试运行 / 不创建正式 Decision / 不授权交易：已核验")

    if prompt_issues:
        print("\n[未通过完整输入验收]")
        for issue in prompt_issues:
            print(f"  - {issue}")
        print("技术 Replay 虽然匹配，但不能记为“已完成完整输入验收”。")
        return 2

    print("\n[PASS] 当前 Mac 的全流程运行与 Replay 技术验收通过。")
    print("请继续按指引人工审阅 report.md、analysis.json 与两份 pilot_receipt.json；")
    print("这不是正式 IIOS Decision、投资批准或交易授权。")
    return 0


def _check_only(run_dir: Path) -> int:
    run_dir = run_dir.expanduser().resolve(strict=True)
    if run_dir.parent != RUN_ROOT.resolve():
        raise AcceptanceError(f"RUN_DIRECTORY_NOT_DIRECT_CHILD_OF_PRIVATE_RUN_ROOT:{run_dir}")
    _run_cli(
        ["--check-run", str(run_dir)],
        stage=f"check-only-{run_dir.name}",
        expected_statuses={"PILOT_BUNDLE_HASH_CHECK_PASS"},
    )
    _inspect_bundle(run_dir)
    print(f"\n[PASS] 运行包哈希、结构、私有权限与非交易声明均符合本地验收脚本：{run_dir}")
    print("注意：只校验文件包，不代表执行过 Replay。")
    return 0


def main() -> int:
    if sys.version_info < (3, 10):
        print("需要 Python 3.10 或更新版本。", file=sys.stderr)
        return 2
    if not (REPOSITORY_ROOT / "iios_mvp" / "local_investment_pilot_v01.py").is_file():
        print(f"未找到本仓库的 local pilot 模块：{REPOSITORY_ROOT}", file=sys.stderr)
        return 2

    try:
        os.umask(0o077)
        _prepare_private_roots()
        print("IIOS 本地全流程 + Replay 验收")
        print(f"代码目录：{REPOSITORY_ROOT}")
        print(f"私有运行目录：{RUN_ROOT}")
        print(f"私有日志目录：{LOG_ROOT}")
        print("本脚本只编排已有本地试运行与 Replay，不访问付费 API，不使用本地模型，不下单。\n")
        print("  1 = 新建分析 → 首次运行包校验 → Replay → Replay 包校验（推荐）")
        print("  2 = 对已有首次运行执行校验 + Replay（不重新进行 ChatGPT 研究）")
        print("  3 = 只校验已有运行包（不运行 Replay）")
        print("  0 = 退出")
        choice = input("请选择 [1]：").strip() or "1"
        if choice == "0":
            print("已退出，没有新建分析或修改旧运行包。")
            return 0
        if choice == "1":
            wizard_log = _new_log("wizard")
            print("\n即将启动现有的 IIOS 研究向导。所有输入和报告继续由原模块写入私有目录。")
            code = _stream_command(
                [sys.executable, "-m", PILOT_MODULE, "--wizard"],
                wizard_log,
            )
            if code != 0:
                print(f"\n向导未正常完成（退出码 {code}）。日志保留于：{wizard_log}", file=sys.stderr)
                return code or 2
            result = _extract_cli_result(wizard_log, {"PILOT_CREATED"})
            pilot_id = str(result.get("pilot_id", ""))
            if not RESULT_ID_PATTERN.fullmatch(pilot_id):
                raise AcceptanceError("WIZARD_RESULT_PILOT_ID_INVALID")
            run_dir = Path(str(result.get("run_dir", ""))).expanduser().resolve(strict=True)
            if run_dir != (RUN_ROOT / pilot_id).resolve():
                raise AcceptanceError("WIZARD_RESULT_RUN_PATH_MISMATCH")
            return _verify_and_replay(run_dir)
        if choice == "2":
            return _verify_and_replay(_select_run(original_only=True))
        if choice == "3":
            return _check_only(_select_run(original_only=False))
        print("无效选项；请选择 0、1、2 或 3。", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已由操作者中断。已有文件保留；未自动删除或改写任何旧运行包。", file=sys.stderr)
        return 130
    except (AcceptanceError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"\n[BLOCKED] {exc}", file=sys.stderr)
        print("未删除旧运行包。请先保留终端输出和私有 acceptance-logs 日志再排查。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
