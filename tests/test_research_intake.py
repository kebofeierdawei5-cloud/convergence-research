from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.research_intake import CONTRACT_VERSION, build_research_case, validate_research_case

ROOT = Path(__file__).resolve().parents[1]

def test_minimal_300750_creates_deterministic_auditable_case():
    case = build_research_case("300750", "2026-10-04", "0", generated_at="2026-10-04T00:00:00+08:00")
    assert case["contract_version"] == CONTRACT_VERSION
    assert case["case_id"] == "RC-CN-A-300750-20261004"
    assert case["security_identity"]["venue_hint"] == "SZSE"
    assert case["security_identity"]["venue_hint_is_evidence"] is False
    assert case["security_identity"]["status"] == "UNRESOLVED"
    assert case["temporal_scope"]["pit_rule"] == "known_at <= cutoff"
    assert case["admission"]["status"] == "EVIDENCE_PENDING"
    assert case["admission"]["decision_ready"] is False
    assert case["evidence"] == []
    assert validate_research_case(case) == []

def test_input_hash_is_deterministic():
    a = build_research_case("300750", "2026-10-04", "10", generated_at="2026-10-04T00:00:00+00:00")
    b = build_research_case("300750", "2026-10-04", "10", generated_at="2026-10-04T01:00:00+00:00")
    assert a["audit"]["input_sha256"] == b["audit"]["input_sha256"]
    assert a["case_id"] == b["case_id"]

def test_position_bounds_fail_closed():
    with pytest.raises(ValueError):
        build_research_case("300750", "2026-10-04", "-0.1")
    with pytest.raises(ValueError):
        build_research_case("300750", "2026-10-04", "100.1")

def test_future_as_of_fails_closed():
    future = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="future"):
        build_research_case("300750", future, "0")

def test_case_does_not_fabricate_company_or_price():
    case = build_research_case("300750", "2026-10-04", "0", generated_at="2026-10-04T00:00:00+00:00")
    assert "company" not in case["request"]
    assert "company_name" not in case["security_identity"]
    assert "price" not in case
    assert not case["evidence"]

def test_source_plan_is_free_first():
    case = build_research_case("300750", "2026-10-04", "0", generated_at="2026-10-04T00:00:00+00:00")
    assert all(item["required_for_admission"] for item in case["evidence_plan"])
    assert all("PAID" not in item["source_classes"] for item in case["evidence_plan"])

def test_schema_accepts_generated_case():
    case = build_research_case("300750", "2026-10-04", "0", generated_at="2026-10-04T00:00:00+00:00")
    schema = json.loads((ROOT / "schemas" / "research_case_v0.1.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(case), key=lambda e: e.path)
    assert errors == []
