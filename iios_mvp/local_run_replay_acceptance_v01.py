from __future__ import annotations

"""One-command macOS wrapper for the existing local IIOS pilot + verified Replay.

This module orchestrates the existing pilot CLI; it does not implement a second
valuation, decision, receipt, or replay engine.
"""

import codecs
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = Path.home() / ".iios-private"
PILOT_ROOT = PRIVATE_ROOT / "local-pilot"
INPUT_ROOT = PILOT_ROOT / "inputs"
RUN_ROOT = PILOT_ROOT / "runs"
LOG_ROOT = PILOT_ROOT / "acceptance-logs"
ACCEPTANCE_BUNDLE_ROOT = PILOT_ROOT / "acceptance-bundles"

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
    "duplicate_evidence_ids",
    "untraceable_evidence_ids",
    "untraceable_evidence_fields",
    "unresolved_evidence_references",
    "after_cutoff_evidence_references",
    "uncertain_timing_evidence_references",
    "forecast_valuation",
    "operating_driver_forecast",
    "valuation_transmission",
    "sotp_valuation",
    "eps_multiple_valuation",
    "eps_earnings_bridge",
    "valuation_model_consistency",
    "valuation_timing",
    "return_metrics",
    "return_metrics_reason",
    "operator_valuation_context",
    "price_zone_sensitivity",
    "decision_parameters",
    "portfolio_package",
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
    for path in (PRIVATE_ROOT, PILOT_ROOT, INPUT_ROOT, RUN_ROOT, LOG_ROOT, ACCEPTANCE_BUNDLE_ROOT):
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
        # Do not iterate by lines: input() prompts commonly end with ":" and
        # have no newline. Line iteration would hide the prompt until after
        # the operator enters input. Read available bytes immediately and
        # decode incrementally so prompts and mixed Chinese UTF-8 remain live.
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while True:
                raw = os.read(process.stdout.fileno(), 4096)
                if not raw:
                    tail = decoder.decode(b"", final=True)
                    if tail:
                        sys.stdout.write(tail)
                        sys.stdout.flush()
                        log.write(tail)
                    break
                text = decoder.decode(raw)
                if not text:
                    continue
                sys.stdout.write(text)
                sys.stdout.flush()
                log.write(text)
                if "\\n" in text:
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
    log_paths: list[Path] | None = None,
) -> dict[str, Any]:
    log_path = _new_log(stage)
    if log_paths is not None:
        log_paths.append(log_path)
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


def _current_code_revision() -> str | None:
    """Return the checked-out Git commit for audit provenance without requiring network access."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def _create_acceptance_bundle(
    *,
    original_dir: Path,
    replay_dir: Path,
    log_paths: Iterable[Path],
    comparison: dict[str, Any],
    prompt_issues: list[str],
) -> Path:
    """Create a private audit ZIP containing both runs and their full acceptance evidence."""
    original_dir = original_dir.expanduser().resolve(strict=True)
    replay_dir = replay_dir.expanduser().resolve(strict=True)
    run_root = RUN_ROOT.resolve(strict=True)
    if original_dir.parent != run_root or replay_dir.parent != run_root:
        raise AcceptanceError("ACCEPTANCE_BUNDLE_RUNS_MUST_BE_DIRECT_CHILDREN_OF_PRIVATE_RUN_ROOT")
    if original_dir == replay_dir or not RESULT_ID_PATTERN.fullmatch(original_dir.name) or not RESULT_ID_PATTERN.fullmatch(replay_dir.name):
        raise AcceptanceError("ACCEPTANCE_BUNDLE_RUN_IDENTITIES_INVALID")

    original_receipt = _read_json(original_dir / "pilot_receipt.json", "ORIGINAL_RUN_RECEIPT")
    replay_receipt = _read_json(replay_dir / "pilot_receipt.json", "REPLAY_RUN_RECEIPT")
    if original_receipt.get("pilot_id") != original_dir.name or original_receipt.get("replay_of") is not None:
        raise AcceptanceError("ACCEPTANCE_BUNDLE_ORIGINAL_RUN_IDENTITY_INVALID")
    if replay_receipt.get("pilot_id") != replay_dir.name or replay_receipt.get("replay_of") != original_dir.name:
        raise AcceptanceError("ACCEPTANCE_BUNDLE_REPLAY_PARENT_INVALID")

    entries: dict[str, bytes] = {}
    run_summaries: dict[str, dict[str, Any]] = {}
    for label, run_dir, receipt in (
        ("first_run", original_dir, original_receipt),
        ("replay_run", replay_dir, replay_receipt),
    ):
        manifest = receipt.get("file_manifest")
        if not isinstance(manifest, dict):
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_SOURCE_HASH_MANIFEST_MISSING:{label}")
        for filename in ("input.json", "analysis.json", "report.md"):
            file_path = run_dir / filename
            if file_path.is_symlink() or not file_path.is_file():
                raise AcceptanceError(f"ACCEPTANCE_BUNDLE_SOURCE_FILE_MISSING_OR_SYMLINK:{label}:{filename}")
            try:
                payload = file_path.read_bytes()
            except OSError as exc:
                raise AcceptanceError(f"ACCEPTANCE_BUNDLE_SOURCE_FILE_UNREADABLE:{label}:{filename}") from exc
            expected = manifest.get(filename)
            if not isinstance(expected, dict):
                raise AcceptanceError(f"ACCEPTANCE_BUNDLE_SOURCE_HASH_MISSING:{label}:{filename}")
            expected_hash = str(expected.get("sha256") or "")
            expected_size = expected.get("byte_size")
            actual_hash = hashlib.sha256(payload).hexdigest()
            if (
                not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
                or not isinstance(expected_size, int)
                or isinstance(expected_size, bool)
                or expected_size != len(payload)
                or expected_hash != actual_hash
            ):
                raise AcceptanceError(f"ACCEPTANCE_BUNDLE_SOURCE_HASH_MISMATCH:{label}:{filename}")
            entries[f"{label}/{run_dir.name}/{filename}"] = payload

        receipt_path = run_dir / "pilot_receipt.json"
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_RECEIPT_MISSING_OR_SYMLINK:{label}")
        entries[f"{label}/{run_dir.name}/pilot_receipt.json"] = receipt_path.read_bytes()
        analysis = _read_json(run_dir / "analysis.json", f"{label.upper()}_ANALYSIS")
        decision = analysis.get("decision") if isinstance(analysis.get("decision"), dict) else {}
        run_summaries[label] = {
            "pilot_id": run_dir.name,
            "replay_of": receipt.get("replay_of"),
            "provisional_action": decision.get("provisional_action"),
            "file_manifest": {
                name: dict(manifest[name]) for name in ("input.json", "analysis.json", "report.md")
            },
        }

    log_root = LOG_ROOT.resolve(strict=True)
    log_entries: list[str] = []
    for supplied_path in log_paths:
        if supplied_path.is_symlink():
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_LOG_MUST_NOT_BE_SYMLINK:{supplied_path.name}")
        try:
            log_path = supplied_path.resolve(strict=True)
        except OSError as exc:
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_LOG_MISSING:{supplied_path.name}") from exc
        if log_path.parent != log_root or not log_path.is_file():
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_LOG_OUTSIDE_PRIVATE_LOG_ROOT:{supplied_path.name}")
        archive_name = f"acceptance_logs/{log_path.name}"
        if archive_name in entries:
            continue
        entries[archive_name] = log_path.read_bytes()
        log_entries.append(archive_name)

    status = "REVIEW_REQUIRED" if prompt_issues else "PASS"
    summary = {
        "bundle_schema": "IIOS-LOCAL-ACCEPTANCE-BUNDLE-0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "code_revision": _current_code_revision(),
        "overall_status": status,
        "technical_status": "PASS",
        "input_completeness_status": "REVIEW_REQUIRED" if prompt_issues else "PASS",
        "input_completeness_issues": list(prompt_issues),
        "first_run": run_summaries["first_run"],
        "replay_run": run_summaries["replay_run"],
        "replay_comparison": comparison,
        "acceptance_log_files": sorted(log_entries),
        "formal_decision_created": False,
        "canonical_run_receipt_created": False,
        "execution_authorized": False,
        "auto_execution": False,
        "note": "Private audit package. Contains the original and Replay analysis inputs/results and local logs; it is not a formal decision or trade authorization.",
    }
    entries["acceptance_summary.json"] = json.dumps(
        summary, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8")
    bundle_manifest = {
        "manifest_schema": "IIOS-LOCAL-ACCEPTANCE-BUNDLE-MANIFEST-0.1",
        "hash_algorithm": "SHA-256",
        "manifest_excludes_self": True,
        "files": [
            {
                "path": name,
                "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(entries.items())
        ],
    }
    manifest_bytes = json.dumps(
        bundle_manifest, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8")
    archive_entries = dict(entries)
    archive_entries["bundle_manifest.json"] = manifest_bytes

    _ensure_private_directory(ACCEPTANCE_BUNDLE_ROOT)
    archive_path = ACCEPTANCE_BUNDLE_ROOT / (
        f"iios-acceptance-{original_dir.name}-replay-{replay_dir.name}.zip"
    )
    if archive_path.exists() or archive_path.is_symlink():
        raise AcceptanceError("ACCEPTANCE_BUNDLE_DESTINATION_ALREADY_EXISTS")
    temporary_path = ACCEPTANCE_BUNDLE_ROOT / f".{archive_path.name}.{_stamp()}.tmp"
    try:
        with temporary_path.open("xb"):
            pass
        if os.name != "nt":
            temporary_path.chmod(0o600)
        with zipfile.ZipFile(
            temporary_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for name, payload in sorted(archive_entries.items()):
                archive.writestr(name, payload)
        if os.name != "nt":
            temporary_path.chmod(0o600)
        with zipfile.ZipFile(temporary_path, mode="r") as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise AcceptanceError(f"ACCEPTANCE_BUNDLE_ZIP_CORRUPT:{bad_member}")
            if set(archive.namelist()) != set(archive_entries):
                raise AcceptanceError("ACCEPTANCE_BUNDLE_ARCHIVE_MEMBERS_MISMATCH")
            for record in bundle_manifest["files"]:
                archived_payload = archive.read(record["path"])
                if (
                    len(archived_payload) != record["byte_size"]
                    or hashlib.sha256(archived_payload).hexdigest() != record["sha256"]
                ):
                    raise AcceptanceError(f"ACCEPTANCE_BUNDLE_ARCHIVE_HASH_MISMATCH:{record['path']}")
        temporary_path.replace(archive_path)
        if os.name != "nt":
            archive_path.chmod(0o600)
            if archive_path.stat().st_mode & 0o077:
                raise AcceptanceError("ACCEPTANCE_BUNDLE_FILE_PERMISSIONS_NOT_PRIVATE")
        return archive_path
    except Exception as exc:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        if archive_path.exists() and not temporary_path.exists():
            try:
                archive_path.unlink(missing_ok=True)
            except OSError:
                pass
        if isinstance(exc, AcceptanceError):
            raise
        if isinstance(exc, (OSError, ValueError, zipfile.BadZipFile)):
            raise AcceptanceError(f"ACCEPTANCE_BUNDLE_CREATE_FAILED:{type(exc).__name__}:{exc}") from exc
        raise


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
    price_input = analysis.get("price_input")
    entry_assumption = price_input.get("entry_assumption") if isinstance(price_input, dict) else None
    if (
        not isinstance(entry_assumption, dict)
        or entry_assumption.get("schema_version") != "IIOS-ENTRY-PRICE-ASSUMPTION-0.1"
        or entry_assumption.get("mode") != "HYPOTHETICAL_ENTRY_AT_INPUT_PRICE_ON_CUTOFF_DATE"
        or not isinstance(entry_assumption.get("hypothetical_entry_date"), str)
        or entry_assumption.get("actual_execution_status") != "NOT_CONFIRMED"
        or entry_assumption.get("actual_execution_confirmed") is not False
        or entry_assumption.get("execution_guaranteed") is not False
        or entry_assumption.get("dividend_entitlement_status") != "CONDITIONAL_ON_HYPOTHETICAL_ENTRY"
        or entry_assumption.get("actual_dividend_entitlement_confirmed") is not False
    ):
        raise AcceptanceError(f"ENTRY_PRICE_ASSUMPTION_MISSING_OR_UNSAFE:{run_dir.name}")
    sotp = analysis.get("sotp_valuation")
    if (
        not isinstance(sotp, dict)
        or not isinstance(sotp.get("status"), str)
        or not isinstance(sotp.get("scenarios"), dict)
    ):
        raise AcceptanceError(f"SOTP_VALUATION_MISSING_OR_INVALID:{run_dir.name}")
    eps_multiple = analysis.get("eps_multiple_valuation")
    if (
        not isinstance(eps_multiple, dict)
        or eps_multiple.get("schema_version") != "IIOS-EPS-MULTIPLE-VALUATION-0.1"
        or eps_multiple.get("method") != "EPS_PER_SHARE_X_PE_MULTIPLE"
        or not isinstance(eps_multiple.get("status"), str)
        or not isinstance(eps_multiple.get("scenarios"), dict)
        or not isinstance(eps_multiple.get("issues"), list)
        or not isinstance(eps_multiple.get("selected_for_primary_model"), bool)
        or (eps_multiple.get("status") == "CALCULATED" and eps_multiple.get("selected_for_primary_model") is not True)
        or (eps_multiple.get("status") == "CALCULATED" and set(eps_multiple.get("scenarios", {})) != {"bear", "base", "bull"})
    ):
        raise AcceptanceError(f"EPS_MULTIPLE_VALUATION_MISSING_OR_INVALID:{run_dir.name}")
    eps_bridge = analysis.get("eps_earnings_bridge")
    eps_bridge_allowed_statuses = {
        "CALCULATED", "ASSUMPTION_ONLY", "MIXED_CALCULATED_AND_ASSUMPTION_ONLY",
    }
    if (
        not isinstance(eps_bridge, dict)
        or eps_bridge.get("schema_version") != "IIOS-EPS-EARNINGS-BRIDGE-0.1"
        or eps_bridge.get("method") != "B4_NET_PROFIT_PROXY_MINUS_NCI_PLUS_ADJUSTMENTS_DIVIDED_BY_DILUTED_SHARES"
        or not isinstance(eps_bridge.get("status"), str)
        or not isinstance(eps_bridge.get("scenarios"), dict)
        or not isinstance(eps_bridge.get("issues"), list)
        or not isinstance(eps_bridge.get("primary_eps_price_calculation_eligible"), bool)
    ):
        raise AcceptanceError(f"EPS_EARNINGS_BRIDGE_MISSING_OR_INVALID:{run_dir.name}")
    selected_model = analysis.get("operator_valuation_context")
    selected_model = selected_model if isinstance(selected_model, dict) else {}
    if str(selected_model.get("selected_model_family") or "UNKNOWN").upper() == "EPS_MULTIPLE":
        if eps_multiple.get("status") == "CALCULATED":
            if (
                eps_bridge.get("status") not in eps_bridge_allowed_statuses
                or eps_bridge.get("primary_eps_price_calculation_eligible") is not True
                or set(eps_bridge.get("scenarios", {})) != {"bear", "base", "bull"}
                or any(
                    not isinstance(eps_bridge["scenarios"].get(name), dict)
                    or eps_bridge["scenarios"][name].get("status") not in {"CALCULATED", "ASSUMPTION_ONLY"}
                    for name in ("bear", "base", "bull")
                )
            ):
                raise AcceptanceError(f"EPS_MULTIPLE_CALCULATED_WITHOUT_ELIGIBLE_EARNINGS_BRIDGE:{run_dir.name}")
        else:
            price_zone = analysis.get("price_zone_sensitivity")
            if (
                analysis.get("return_metrics") is not None
                or not isinstance(price_zone, dict)
                or price_zone.get("target_entry_price") is not None
            ):
                raise AcceptanceError(f"EPS_MULTIPLE_INELIGIBLE_BRIDGE_DID_NOT_BLOCK_PRICE_OUTPUTS:{run_dir.name}")
    if eps_bridge.get("status") in {"NOT_LINKED", "EPS_MISMATCH"}:
        price_zone = analysis.get("price_zone_sensitivity")
        if (
            analysis.get("return_metrics") is not None
            or (isinstance(price_zone, dict) and price_zone.get("target_entry_price") is not None)
        ):
            raise AcceptanceError(f"EPS_EARNINGS_BRIDGE_FAILURE_DID_NOT_FAIL_CLOSED:{run_dir.name}")

    model_consistency = analysis.get("valuation_model_consistency")
    if (
        not isinstance(model_consistency, dict)
        or not isinstance(model_consistency.get("status"), str)
        or not isinstance(model_consistency.get("primary_model_price_calculation_eligible"), bool)
    ):
        raise AcceptanceError(f"VALUATION_MODEL_CONSISTENCY_MISSING_OR_INVALID:{run_dir.name}")
    valuation_timing = analysis.get("valuation_timing")
    if not isinstance(valuation_timing, dict) or not isinstance(valuation_timing.get("status"), str):
        raise AcceptanceError(f"VALUATION_TIMING_MISSING_OR_INVALID:{run_dir.name}")
    if analysis.get("return_metrics_reason") is not None and not isinstance(analysis.get("return_metrics_reason"), str):
        raise AcceptanceError(f"RETURN_METRICS_REASON_INVALID:{run_dir.name}")
    for field in (
        "duplicate_evidence_ids",
        "untraceable_evidence_ids",
        "unresolved_evidence_references",
        "after_cutoff_evidence_references",
        "uncertain_timing_evidence_references",
    ):
        if not isinstance(analysis.get(field), list):
            raise AcceptanceError(f"EVIDENCE_DIAGNOSTIC_LIST_MISSING_OR_INVALID:{run_dir.name}:{field}")
    if not isinstance(analysis.get("untraceable_evidence_fields"), dict):
        raise AcceptanceError(f"EVIDENCE_DIAGNOSTIC_MAP_MISSING_OR_INVALID:{run_dir.name}:untraceable_evidence_fields")

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


def _verify_and_replay(
    original_dir: Path,
    *,
    preceding_logs: Iterable[Path] = (),
) -> int:
    audit_logs = list(preceding_logs)
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
        log_paths=audit_logs,
    )
    original_analysis, original_receipt = _inspect_bundle(original_dir, expected_replay_of=None)

    print("\n[2/4] 使用首次运行的原始 input.json 执行真正的 Replay 重算与决策材料比较")
    replay_result = _run_cli(
        ["--replay-run", str(original_dir), "--output-root", str(RUN_ROOT)],
        stage=f"replay-{original_dir.name}",
        expected_statuses={"PILOT_REPLAY_MATCHED", "PILOT_REPLAY_MISMATCH"},
        log_paths=audit_logs,
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
        log_paths=audit_logs,
    )

    prompt_issues = _prompt_completion_issues(original_analysis)
    replay_prompt_issues = _prompt_completion_issues(replay_analysis)
    if prompt_issues != replay_prompt_issues:
        raise AcceptanceError("REPLAY_PROMPT_COMPLETENESS_DRIFT")

    acceptance_bundle = _create_acceptance_bundle(
        original_dir=original_dir,
        replay_dir=replay_dir,
        log_paths=audit_logs,
        comparison=comparison,
        prompt_issues=prompt_issues,
    )

    print("\n[4/4] 全流程结果")
    print(f"  首次运行：{original_dir}")
    print(f"  Replay 运行：{replay_dir}")
    print(f"  首次报告：{original_dir / 'report.md'}")
    print(f"  首次分析：{original_dir / 'analysis.json'}")
    print(f"  首次记录：{original_dir / 'pilot_receipt.json'}")
    print(f"  Replay 报告：{replay_dir / 'report.md'}")
    print(f"  Replay 分析：{replay_dir / 'analysis.json'}")
    print(f"  Replay 记录：{replay_dir / 'pilot_receipt.json'}")
    print(f"  Replay 比较：MATCH（比较字段数：{len(comparison.get('compared_fields', []))}）")
    print("  首次包哈希：PASS；Replay 包哈希：PASS")
    print(f"  完整审计交接 ZIP（首次运行 + Replay + 日志 + SHA-256 清单，仅本机私有保存）：{acceptance_bundle}")
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
            return _verify_and_replay(run_dir, preceding_logs=[wizard_log])
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
