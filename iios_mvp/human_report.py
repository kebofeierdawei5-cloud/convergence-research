
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .engine import canonical_json, sha256_obj
from .machine_publication import validate_machine_publication

REPORT_VERSION = "IIOS-HUMAN-REPORT-0.1"
QA_VERSION = "IIOS-REPORT-QA-0.1"

REQUIRED_SECTIONS = (
    "Executive Decision",
    "Investment Case",
    "Trust & Evidence Boundary",
    "Reality / Forecast / Valuation",
    "Risk & Monitoring",
    "Human Decision Boundary",
    "Provenance & Integrity",
)


def _timestamp(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601 timestamp") from exc
    return text


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _fmt(value: Any) -> str:
    if value is None:
        return "UNAVAILABLE"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))
    return str(value)



def _render_risk_portfolio_contract(value: Any) -> list[str]:
    """Render risk/portfolio data as investor-facing bullets, never as a machine JSON dump."""
    if not isinstance(value, Mapping):
        return ["- Risk / portfolio contract: unavailable (structured contract not provided)"]

    lines = ["- Risk / portfolio contract: available"]
    if "contract_version" in value:
        lines.append(f"  - Contract version: {_fmt(value.get('contract_version'))}")
    readiness = value.get("readiness")
    if isinstance(readiness, Mapping):
        lines.append(f"  - Risk ready: {_fmt(readiness.get('risk_ready'))}")
        lines.append(f"  - Portfolio constraint ready: {_fmt(readiness.get('portfolio_constraint_ready'))}")
        lines.append(f"  - Package ready: {_fmt(readiness.get('package_ready'))}")
    portfolio = value.get("portfolio")
    if isinstance(portfolio, Mapping):
        lines.append(f"  - Current position: {_fmt(portfolio.get('position_pct'))}%")
        lines.append(f"  - Add permission in package: {_fmt(portfolio.get('can_add'))}")
        lines.append(f"  - Portfolio constraint: {_fmt(portfolio.get('constraint_status'))}")
        lines.append(f"  - Position package: {_fmt(portfolio.get('package_status'))}")
        package = portfolio.get("buy_add_package")
        if isinstance(package, Mapping):
            zone = package.get("entry_zone")
            if isinstance(zone, list) and len(zone) == 2:
                lines.append(f"  - Entry zone: {_fmt(zone[0])}–{_fmt(zone[1])}")
            lines.append(f"  - Initial position: {_fmt(package.get('initial_position_pct'))}%")
            lines.append(f"  - Target position: {_fmt(package.get('target_position_pct'))}%")
            lines.append(f"  - Maximum position: {_fmt(package.get('max_position_pct'))}%")
            triggers = package.get("monitoring_triggers")
            if isinstance(triggers, list) and triggers:
                lines.append("  - Package monitoring triggers:")
                lines.extend(f"    - {item}" for item in triggers)
            breaks = package.get("thesis_break_triggers")
            if isinstance(breaks, list) and breaks:
                lines.append("  - Package thesis-break triggers:")
                lines.extend(f"    - {item}" for item in breaks)
    risk = value.get("risk")
    if isinstance(risk, Mapping) and "max_loss_pct" in risk:
        lines.append(f"  - Maximum loss boundary: {_fmt(risk.get('max_loss_pct'))}%")
    return lines

def render_human_report(publication: Mapping[str, Any]) -> str:
    validate_machine_publication(publication)
    case = publication["case"]
    ref = publication["decision_ref"]
    decision = publication["ai_decision"]
    payload = publication["decision_payload"]
    approval = publication["human_approval"]
    current = publication["current_projection"]
    lifecycle = publication["lifecycle_refs"]
    gates = payload.get("gates") or {}
    returns = payload.get("return_metrics") or {}
    risk = payload.get("risk") or {}
    monitoring = payload.get("monitoring") or []

    lines = [
        f"# IIOS Investment Decision Report — {case['company']} ({case['symbol']})",
        "",
        f"Case: {case['case_id']}",
        f"Cutoff: {case['cutoff_date']}",
        f"As of: {case['as_of_date']}",
        f"Decision Revision: r{ref['revision']:03d}",
        "",
        "## Executive Decision",
        "",
        f"- Action: {_fmt(decision.get('action'))}",
        f"- Decision status: {_fmt(decision.get('decision_status'))}",
        f"- Investability status: {_fmt(decision.get('investability_status'))}",
        f"- Primary reason: {_fmt(decision.get('primary_reason'))}",
        f"- Human approval required: {_fmt(decision.get('human_approval_required'))}",
        f"- Automatic execution: {_fmt(decision.get('auto_execution'))}",
        "",
        "## Investment Case",
        "",
        f"- Trust gate: {_fmt(gates.get('trust'))}",
        f"- Evidence/PIT gate: {_fmt(gates.get('evidence_pit'))}",
        f"- Forecast readiness: {_fmt(gates.get('forecast_ready'))}",
        f"- Valuation readiness: {_fmt(gates.get('valuation_ready'))}",
        f"- BUY/ADD permission at decision time: {_fmt(gates.get('new_buy_add_allowed'))}",
        f"- Decision scope: {_fmt(payload.get('decision_scope'))}",
        "",
        "### Return & Valuation",
        "",
        f"- Entry Return Cushion: {_fmt(returns.get('entry_return_cushion'))}",
        f"- Expected Total Return: {_fmt(returns.get('expected_total_return'))}",
        f"- Expected Annualized Return: {_fmt(returns.get('expected_annualized_return'))}",
        f"- Fundamental Target Pass: {_fmt(returns.get('fundamental_target_pass'))}",
        f"- Required Return Pass: {_fmt(returns.get('required_return_pass'))}",
        f"- Required Return: {_fmt(returns.get('required_return'))}",
        "",
        "## Trust & Evidence Boundary",
        "",
        "This report reproduces the canonical Decision Revision and does not create new evidence.",
        f"- Decision Revision hash: {ref['revision_hash']}",
        f"- Snapshot hash: {ref['snapshot_hash']}",
        f"- Engine version: {ref['engine_version']}",
        f"- Contract version: {ref['contract_version']}",
        f"- Publication hash: {publication['publication_hash']}",
        "",
        "## Reality / Forecast / Valuation",
        "",
        f"- Current canonical decision price: {_fmt(decision.get('current_price'))}",
        f"- Target entry price: {_fmt(decision.get('target_entry_price'))}",
        f"- Target entry semantics: {_fmt(decision.get('target_entry_price_semantics'))}",
        f"- Canonical entry evaluation: {_fmt(decision.get('canonical_entry_evaluation'))}",
        "",
        "The report does not independently recalculate company economics. Those values remain owned by the canonical Decision payload.",
        "",
        "## Risk & Monitoring",
        "",
        *_render_risk_portfolio_contract(decision.get("risk_portfolio_contract")),
        f"- Maximum loss / risk surface: {_fmt(risk.get('max_loss_pct'))}",
        "- Thesis break and risk boundaries are carried by the canonical Decision and are not amended here.",
    ]
    for item in (payload.get("thesis") or {}).get("falsifiers", []) or []:
        lines.append(f"- Thesis falsifier: {item}")
    if monitoring:
        lines += ["", "### Monitoring"]
        for item in monitoring:
            lines.append(f"- {_fmt(item.get('metric'))}: {_fmt(item.get('condition'))}")
    lines += [
        "",
        "## Human Decision Boundary",
        "",
        f"- Human approval status: {_fmt(approval.get('approval_status'))}",
        f"- Approved: {_fmt(approval.get('approved'))}",
        f"- Current projection status: {_fmt(current.get('status'))}",
        "- Final capital authorization remains a human decision.",
        "- Report publication does not approve, reject, revise, or execute a decision.",
        "",
        "## Provenance & Integrity",
        "",
        f"- Machine Publication ID: {publication['publication_id']}",
        f"- Machine Publication hash: {publication['publication_hash']}",
        f"- Trigger contracts referenced: {len(lifecycle['trigger_contracts'])}",
        f"- Monitoring states referenced: {len(lifecycle['monitoring_states'])}",
        f"- Validation records referenced: {len(lifecycle['validation_records'])}",
        "",
        "### Explicit Non-Authority",
        "",
        "- This report is a human-readable projection only.",
        "- It cannot mutate the Decision Revision.",
        "- It cannot mutate Monitoring or Validation state.",
        "- It cannot place orders or enable automatic execution.",
        "",
    ]
    return "\n".join(lines)


def build_human_report(*, publication: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    validate_machine_publication(publication)
    generated_at = _timestamp(generated_at, "generated_at")
    core = {
        "report_version": REPORT_VERSION,
        "generated_at": generated_at,
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "decision_id": publication["decision_ref"]["decision_id"],
        "revision": publication["decision_ref"]["revision"],
        "case_id": publication["decision_ref"]["case_id"],
        "cutoff_date": publication["decision_ref"]["cutoff_date"],
        "markdown": render_human_report(publication),
    }
    report_hash = sha256_obj(core)
    return {
        **core,
        "report_id": f'{publication["publication_id"]}-report-{report_hash[:16]}',
        "report_hash": report_hash,
    }


def validate_human_report(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("human_report must be an object")
    required = {
        "report_version", "generated_at", "publication_id", "publication_hash",
        "decision_id", "revision", "case_id", "cutoff_date", "markdown",
        "report_id", "report_hash",
    }
    if set(record) != required:
        raise ValueError("human_report fields are invalid")
    if record["report_version"] != REPORT_VERSION:
        raise ValueError("human_report version mismatch")
    _timestamp(record["generated_at"], "generated_at")
    for field in ("publication_hash", "report_hash"):
        if not isinstance(record[field], str) or len(record[field]) != 64:
            raise ValueError(f"human_report {field} invalid")
    if not isinstance(record["revision"], int) or record["revision"] < 1:
        raise ValueError("human_report revision invalid")
    if not isinstance(record["markdown"], str) or not record["markdown"].strip():
        raise ValueError("human_report markdown invalid")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in record["markdown"]:
            raise ValueError(f"human_report missing required section: {section}")
    core = {k: record[k] for k in required if k not in {"report_id", "report_hash"}}
    if record["report_hash"] != sha256_obj(core):
        raise ValueError("human_report hash mismatch")
    expected_id = f'{record["publication_id"]}-report-{record["report_hash"][:16]}'
    if record["report_id"] != expected_id:
        raise ValueError("human_report id mismatch")


def qa_human_report(*, publication: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "publication_integrity": "PASS",
        "publication_binding": "PASS",
        "report_integrity": "PASS",
        "deterministic_render_replay": "PASS",
        "required_sections": "PASS",
        "decision_fidelity": "PASS",
        "human_boundary": "PASS",
        "non_authority": "PASS",
        "human_readability": "PASS",
    }
    issues: list[str] = []
    try:
        validate_machine_publication(publication)
    except Exception as exc:
        checks["publication_integrity"] = "FAIL"
        issues.append(f"publication_integrity: {exc}")
    try:
        validate_human_report(report)
    except Exception as exc:
        checks["report_integrity"] = "FAIL"
        issues.append(f"report_integrity: {exc}")
    ref = publication.get("decision_ref") or {}
    if (
        report.get("publication_id") != publication.get("publication_id")
        or report.get("publication_hash") != publication.get("publication_hash")
        or report.get("decision_id") != ref.get("decision_id")
        or report.get("revision") != ref.get("revision")
        or report.get("case_id") != ref.get("case_id")
        or report.get("cutoff_date") != ref.get("cutoff_date")
    ):
        checks["publication_binding"] = "FAIL"
        issues.append("publication_binding: exact Machine Publication mismatch")
    try:
        regenerated = build_human_report(
            publication=publication,
            generated_at=report["generated_at"],
        )
        if canonical_json(regenerated) != canonical_json(report):
            checks["deterministic_render_replay"] = "FAIL"
            issues.append("deterministic_render_replay: regenerated report differs")
    except Exception as exc:
        checks["deterministic_render_replay"] = "FAIL"
        issues.append(f"deterministic_render_replay: {exc}")
    markdown = str(report.get("markdown", ""))
    decision = publication.get("ai_decision") or {}
    action = str(decision.get("action", ""))
    reason = str(decision.get("primary_reason", ""))
    if action not in markdown or reason not in markdown:
        checks["decision_fidelity"] = "FAIL"
        issues.append("decision_fidelity: canonical action/reason missing")
    approval = publication.get("human_approval") or {}
    if str(approval.get("approval_status", "")) not in markdown:
        checks["human_boundary"] = "FAIL"
        issues.append("human_boundary: approval status missing")
    lower = markdown.lower()
    if "does not approve" not in lower or "cannot place orders" not in lower:
        checks["non_authority"] = "FAIL"
        issues.append("non_authority: explicit boundary language missing")
    machine_json_dump = False
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        value = stripped.split(":", 1)[1].strip()
        if value.startswith("{") or value.startswith("["):
            machine_json_dump = True
            break
    if machine_json_dump:
        checks["human_readability"] = "FAIL"
        issues.append("human_readability: machine-readable JSON-like field dump detected in main report")
    status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    core = {
        "qa_version": QA_VERSION,
        "qa_id": f'{report["report_id"]}-qa',
        "report_id": report["report_id"],
        "report_hash": report["report_hash"],
        "publication_id": publication["publication_id"],
        "publication_hash": publication["publication_hash"],
        "qa_status": status,
        "checks": checks,
        "issues": issues,
        "policy_effect": "REPORT_ONLY_PROJECTION",
    }
    return {**core, "qa_hash": sha256_obj(core)}


def validate_report_qa(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("report_qa must be an object")
    required = {
        "qa_version", "qa_id", "report_id", "report_hash",
        "publication_id", "publication_hash", "qa_status", "checks",
        "issues", "policy_effect", "qa_hash",
    }
    if set(record) != required:
        raise ValueError("report_qa fields are invalid")
    if record["qa_version"] != QA_VERSION:
        raise ValueError("report_qa version mismatch")
    if record["qa_status"] not in {"PASS", "FAIL"}:
        raise ValueError("report_qa status invalid")
    checks = record["checks"]
    expected_checks = {
        "publication_integrity", "publication_binding", "report_integrity",
        "deterministic_render_replay", "required_sections", "decision_fidelity",
        "human_boundary", "non_authority", "human_readability",
    }
    if not isinstance(checks, Mapping) or set(checks) != expected_checks:
        raise ValueError("report_qa checks invalid")
    if any(v not in {"PASS", "FAIL"} for v in checks.values()):
        raise ValueError("report_qa check status invalid")
    expected_status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    if record["qa_status"] != expected_status:
        raise ValueError("report_qa status/check mismatch")
    if record["policy_effect"] != "REPORT_ONLY_PROJECTION":
        raise ValueError("report_qa policy effect invalid")
    core = {k: record[k] for k in required if k != "qa_hash"}
    if record["qa_hash"] != sha256_obj(core):
        raise ValueError("report_qa hash mismatch")


def report_path(root: str | Path, report_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{report_hash}.report.json"


def markdown_path(root: str | Path, report_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{report_hash}.report.md"


def qa_path(root: str | Path, qa_hash: str) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    return root_path / f"{qa_hash}.report-qa.json"


def write_human_report(
    root: str | Path,
    *,
    publication_path: str | Path,
    generated_at: str,
) -> tuple[Path, Path]:
    publication = _load_json(publication_path)
    validate_machine_publication(publication)
    report = build_human_report(publication=publication, generated_at=generated_at)
    validate_human_report(report)
    qa = qa_human_report(publication=publication, report=report)
    validate_report_qa(qa)
    if qa["qa_status"] != "PASS":
        raise ValueError("report quality gate failed: " + "; ".join(qa["issues"]))
    rp = report_path(root, report["report_hash"])
    if rp.exists():
        existing = _load_json(rp)
        validate_human_report(existing)
        if canonical_json(existing) != canonical_json(report):
            raise ValueError("human report hash collision or attempted overwrite")
    else:
        rp.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    mp = markdown_path(root, report["report_hash"])
    markdown_bytes = report["markdown"].encode("utf-8")
    if mp.exists():
        if mp.read_bytes() != markdown_bytes:
            raise ValueError("human report markdown collision or attempted overwrite")
    else:
        mp.write_bytes(markdown_bytes)

    qp = qa_path(root, qa["qa_hash"])
    if qp.exists():
        existing = _load_json(qp)
        validate_report_qa(existing)
        if canonical_json(existing) != canonical_json(qa):
            raise ValueError("report QA hash collision or attempted overwrite")
    else:
        qp.write_text(
            json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return rp, qp
