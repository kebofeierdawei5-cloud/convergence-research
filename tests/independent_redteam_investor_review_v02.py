#!/usr/bin/env python3
"""Independent clean-room red-team for the IIOS Investor Review v0.2 surface.

This file intentionally imports only Python standard-library modules.
It must not import the Investor Review implementation under test.
"""
import argparse
import json
from pathlib import Path


EXPECTED_PUBLICATION_HASH = "7e9bc390c03e12ac3309754cdb65938aa928d9dea97a4145998e3ab9911a0ea0"


def _load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _check(condition: bool, check_id: str) -> dict:
    return {"id": check_id, "pass": bool(condition)}


def run(report_path: str, qa_path: str, markdown_path: str) -> dict:
    report = _load(report_path)
    qa = _load(qa_path)
    markdown = Path(markdown_path).read_text(encoding="utf-8")

    audit = report["machine_report"]["semantic_surface"]["human_auditability"]
    decision = report["machine_report"]["semantic_surface"]["decision"]
    results = [
        _check(report["publication_hash"] == EXPECTED_PUBLICATION_HASH, "RT2-001 publication binding"),
        _check(qa["qa_status"] == "PASS" and not qa["issues"], "RT2-002 QA clean"),
        _check(audit["contract_version"] == "IIOS-HUMAN-AUDITABILITY-0.2", "RT2-003 contract version"),
        _check(audit["overall_status"] == "INCOMPLETE", "RT2-004 overall not promotable"),
        _check(
            audit["required_return"]["status"] == "INCOMPLETE"
            and audit["required_return"]["numeric_value"] is None
            and audit["required_return"]["pass_flag"] is True,
            "RT2-P0-01 Required Return",
        ),
        _check(
            audit["expected_return"]["status"] == "INCOMPLETE"
            and audit["scenario_probability"]["status"] == "MISSING",
            "RT2-P0-02 Expected Return / probability",
        ),
        _check(
            audit["entry_price"]["status"] == "THRESHOLD_ONLY"
            and audit["entry_price"]["actionable_target_entry_price"] is None
            and audit["entry_price"]["threshold_price"] == "26.6",
            "RT2-P0-03 Entry Price",
        ),
        _check(
            audit["portfolio_permission"]["status"] == "OVERRIDDEN_BY_DECISION"
            and audit["portfolio_permission"]["package_can_add"] is True
            and audit["portfolio_permission"]["decision_new_capital_allowed"] is False,
            "RT2-P0-04 Portfolio override",
        ),
        _check(
            audit["mie_expectation_gap"]["mie"]["status"] == "NOT_PROVIDED"
            and audit["mie_expectation_gap"]["mie"]["source_presence"] == "MISSING"
            and audit["mie_expectation_gap"]["inference_rule"] == "absence_never_implies_not_identifiable",
            "RT2-P0-05 MIE absence boundary",
        ),
        _check(
            audit["mie_expectation_gap"]["expectation_gap"]["status"] == "UNKNOWN",
            "RT2-005 Expectation Gap preserved UNKNOWN",
        ),
        _check(decision["target_entry_price"] is None, "RT2-006 actionable entry remains null"),
        _check(
            "required return pass: 是" not in markdown
            and "return gate pass: 是" not in markdown
            and "target entry price: 26.6" not in markdown,
            "RT2-007 raw positive flags not human-rendered",
        ),
        _check(
            "Entry Price：**THRESHOLD_ONLY**" in markdown
            and "Required Return：**INCOMPLETE**" in markdown,
            "RT2-008 explicit human guardrails visible",
        ),
        _check(
            "Portfolio Permission：**OVERRIDDEN_BY_DECISION**" in markdown,
            "RT2-009 permission precedence visible",
        ),
        _check(
            "MIE：**NOT_PROVIDED**" in markdown
            and "Expectation Gap：**UNKNOWN**" in markdown,
            "RT2-010 MIE/Gap distinction visible",
        ),
        _check(
            "本报告不能下单，也不授权下单。" in markdown
            and "Human Approval" in markdown,
            "RT2-011 non-authority boundary",
        ),
        _check(
            "### Evidence / PIT provenance" in markdown,
            "RT2-013 provenance section present",
        ),
        _check(
            audit["required_return"]["pass_flag"] is True
            and audit["required_return"]["numeric_value"] is None
            and audit["required_return"]["status"] != "AUDITABLE",
            "RT2-NEG-A required-return bypass blocked",
        ),
        _check(
            audit["expected_return"]["expected_annualized_return"] is not None
            and audit["scenario_probability"]["status"] == "MISSING"
            and audit["expected_return"]["status"] != "AUDITABLE",
            "RT2-NEG-B expected-return bypass blocked",
        ),
        _check(
            audit["entry_price"]["threshold_price"] == "26.6"
            and audit["entry_price"]["actionable_target_entry_price"] is None
            and audit["entry_price"]["status"] != "ACTIONABLE",
            "RT2-NEG-C threshold bypass blocked",
        ),
        _check(
            audit["portfolio_permission"]["package_can_add"] is True
            and audit["portfolio_permission"]["decision_new_capital_allowed"] is False
            and audit["portfolio_permission"]["status"] == "OVERRIDDEN_BY_DECISION",
            "RT2-NEG-D portfolio bypass blocked",
        ),
        _check(
            audit["mie_expectation_gap"]["mie"]["source_presence"] == "MISSING"
            and audit["mie_expectation_gap"]["mie"]["status"] == "NOT_PROVIDED"
            and audit["mie_expectation_gap"]["mie"].get("identifiability") is None,
            "RT2-NEG-E MIE inference bypass blocked",
        ),
    ]
    failures = [item for item in results if not item["pass"]]
    return {
        "status": "PASS" if not failures else "FAIL",
        "total": len(results),
        "failed": len(failures),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--qa", required=True)
    parser.add_argument("--markdown", required=True)
    args = parser.parse_args()
    result = run(args.report, args.qa, args.markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
