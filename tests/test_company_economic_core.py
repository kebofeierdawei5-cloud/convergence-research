import json
from datetime import timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.company_economic_core import (
    QUALITY_DIMENSIONS,
    TRUST_DIMENSIONS,
    build_company_economic_core,
    validate_company_economic_core,
)
from iios_mvp.research_intake import build_research_case


ROOT = Path(__file__).resolve().parents[1]


def _case_and_evidence():
    case = build_research_case(
        "300750",
        "2026-10-04",
        "0",
        generated_at="2026-10-04T00:00:00+00:00",
    )
    evidence = []
    for index, item in enumerate(case["evidence_plan"], start=1):
        group = item["field_group"]
        evidence.append({
            "evidence_id": f"E{index}",
            "subject_id": case["case_id"],
            "field_id": f"{group}.primary",
            "claim_type": "OBSERVED_FACT",
            "known_at": "2026-10-03T12:00:00+08:00",
            "retrieved_at": "2026-10-04T00:00:00+08:00",
            "source_ref": f"https://example.invalid/{group}",
            "artifact_id": f"artifact-{index}",
            "content_sha256": f"{index:064x}",
            "exact_bytes": True,
            "provenance_class": "SOURCE_VINTAGE_VERIFIED",
            "status": "ADMITTED",
        })
    case["evidence"] = evidence
    return case


def _assessment(dimensions, evidence_ids, status="PASS", prefix="assessment"):
    return {
        "dimensions": [
            {
                "dimension": dimension,
                "status": status,
                "rationale": f"{prefix}:{dimension}",
                "evidence_ids": [evidence_ids[0]],
            }
            for dimension in dimensions
        ]
    }


def _inputs():
    case = _case_and_evidence()
    evidence_ids = [row["evidence_id"] for row in case["evidence"]]

    reality = {
        "facts": [
            {
                "fact_id": "F1",
                "domain": "corporate_disclosures",
                "field_id": "disclosure.material_facts",
                "value": "documented",
                "unit": "status",
                "basis": "admitted primary disclosure evidence",
                "observation_date": "2026-09-30",
                "evidence_ids": [evidence_ids[2]],
                "status": "ESTABLISHED",
            },
            {
                "fact_id": "F2",
                "domain": "business_reality",
                "field_id": "business.segment_mix",
                "value": "documented",
                "unit": "status",
                "basis": "admitted primary business evidence",
                "observation_date": "2026-09-30",
                "evidence_ids": [evidence_ids[3]],
                "status": "ESTABLISHED",
            },
            {
                "fact_id": "F3",
                "domain": "financial_reality",
                "field_id": "financial.cash_flow",
                "value": "documented",
                "unit": "status",
                "basis": "admitted financial evidence",
                "observation_date": "2026-09-30",
                "evidence_ids": [evidence_ids[4]],
                "status": "ESTABLISHED",
            },
            {
                "fact_id": "F4",
                "domain": "capital_structure",
                "field_id": "capital.shares",
                "value": "documented",
                "unit": "status",
                "basis": "admitted capital-structure evidence",
                "observation_date": "2026-09-30",
                "evidence_ids": [evidence_ids[5]],
                "status": "ESTABLISHED",
            },
        ]
    }
    trust = _assessment(TRUST_DIMENSIONS, evidence_ids, prefix="trust")
    quality = _assessment(QUALITY_DIMENSIONS, evidence_ids, prefix="quality")
    value_core = {
        "version": "1.0",
        "nodes": [
            {
                "id": "core_business",
                "name": "Core operating business",
                "node_type": "operating_business",
                "materiality": "HIGH",
                "ownership_pct": 100,
                "assessment_basis": "evidence-linked economic assessment",
                "evidence_ids": [evidence_ids[3], evidence_ids[4]],
                "economic_attributes": {
                    "earnings_stability": "HIGH",
                    "cash_flow_visibility": "HIGH",
                    "capital_intensity": "MEDIUM",
                    "cyclicality": "LOW",
                    "asset_intensity": "MEDIUM",
                    "reinvestment_intensity": "HIGH",
                    "payout_characteristic": "LOW",
                    "pipeline_optionality": "NONE",
                    "maturity": "MATURE",
                },
            }
        ],
    }
    drivers = [
        {
            "driver_id": "D1",
            "name": "Revenue growth to cash-flow growth",
            "rank": 1,
            "materiality": "HIGH",
            "mechanism": "Volume/price/mix drive revenue, margins and ultimately FCF.",
            "economic_variables": ["volume", "price", "product_mix", "gross_margin", "fcf"],
            "evidence_ids": [evidence_ids[3], evidence_ids[4]],
        },
        {
            "driver_id": "D2",
            "name": "Reinvestment economics",
            "rank": 2,
            "materiality": "MEDIUM",
            "mechanism": "CAPEX and incremental ROIC determine the quality of growth reinvestment.",
            "economic_variables": ["capex", "depreciation_amortization", "incremental_roic", "fcf"],
            "evidence_ids": [evidence_ids[4]],
        },
    ]
    return case, reality, trust, quality, value_core, drivers


def test_core02_builds_complete_chain():
    result = build_company_economic_core(
        *_inputs(),
        generated_at="2026-10-04T01:00:00+00:00",
    )
    assert result["case_id"] == "RC-CN-A-300750-20261004"
    assert result["status"] == "PASS"
    assert result["evidence_admission"]["status"] == "ADMITTED"
    assert result["reality"]["status"] == "ESTABLISHED"
    assert result["trust"]["status"] == "PASS"
    assert result["quality"]["status"] == "PASS"
    assert result["value_core"]["status"] == "PASS"
    assert result["value_driver_ranking"][0]["rank"] == 1
    assert result["valuation_route"]["status"] == "CANDIDATE_SET_ONLY"
    assert result["valuation_route"]["selection_authority"] == "HUMAN"
    assert validate_company_economic_core(result) == []


def test_core02_is_deterministic_with_fixed_generation_time():
    inputs = _inputs()
    a = build_company_economic_core(*inputs, generated_at="2026-10-04T01:00:00+00:00")
    b = build_company_economic_core(*inputs, generated_at="2026-10-04T01:00:00+00:00")
    assert a == b
    assert len(a["audit"]["core_sha256"]) == 64
    assert len(a["audit"]["input_sha256"]) == 64


def test_non_admitted_evidence_fails_closed():
    inputs = list(_inputs())
    case = dict(inputs[0])
    case["evidence"] = [dict(row) for row in case["evidence"]]
    case["evidence"][0]["status"] = "CONDITIONAL"
    inputs[0] = case
    with pytest.raises(ValueError, match="must be ADMITTED"):
        build_company_economic_core(*inputs)


def test_post_cutoff_evidence_fails_closed():
    inputs = list(_inputs())
    case = dict(inputs[0])
    case["evidence"] = [dict(row) for row in case["evidence"]]
    case["evidence"][0]["known_at"] = "2026-10-05T00:00:00+08:00"
    case["evidence"][0]["retrieved_at"] = "2026-10-05T00:00:00+08:00"
    inputs[0] = case
    with pytest.raises(ValueError, match="PIT-qualified"):
        build_company_economic_core(*inputs)


def test_wrong_subject_id_fails_closed():
    inputs = list(_inputs())
    case = dict(inputs[0])
    case["evidence"] = [dict(row) for row in case["evidence"]]
    case["evidence"][0]["subject_id"] = "OTHER-CASE"
    inputs[0] = case
    with pytest.raises(ValueError, match="subject_id"):
        build_company_economic_core(*inputs)


def test_missing_required_evidence_domain_fails_closed():
    inputs = list(_inputs())
    case = dict(inputs[0])
    case["evidence"] = [row for row in case["evidence"] if not row["field_id"].startswith("financial_reality.")]
    inputs[0] = case
    with pytest.raises(ValueError, match="required evidence domains missing"):
        build_company_economic_core(*inputs)


def test_reality_cannot_reference_unadmitted_evidence():
    inputs = list(_inputs())
    reality = dict(inputs[1])
    reality["facts"] = [dict(row) for row in reality["facts"]]
    reality["facts"][0]["evidence_ids"] = ["NOT-ADMITTED"]
    inputs[1] = reality
    with pytest.raises(ValueError, match="unknown evidence IDs"):
        build_company_economic_core(*inputs)


def test_conditional_quality_downgrades_core_without_inventing_pass():
    inputs = list(_inputs())
    quality = {"dimensions": [dict(row) for row in inputs[3]["dimensions"]]}
    quality["dimensions"][0]["status"] = "UNKNOWN"
    inputs[3] = quality
    result = build_company_economic_core(*inputs, generated_at="2026-10-04T01:00:00+00:00")
    assert result["quality"]["status"] == "CONDITIONAL"
    assert result["status"] == "CONDITIONAL"


def test_value_driver_rank_must_be_contiguous_and_material():
    inputs = list(_inputs())
    drivers = [dict(row) for row in inputs[5]]
    drivers[1]["rank"] = 3
    inputs[5] = drivers
    with pytest.raises(ValueError, match="contiguous"):
        build_company_economic_core(*inputs)


def test_value_node_must_be_evidence_linked():
    inputs = list(_inputs())
    value_core = {
        "version": "1.0",
        "nodes": [dict(inputs[4]["nodes"][0])],
    }
    value_core["nodes"][0]["evidence_ids"] = []
    inputs[4] = value_core
    with pytest.raises(ValueError, match="evidence_ids"):
        build_company_economic_core(*inputs)


def test_schema_accepts_built_core():
    result = build_company_economic_core(
        *_inputs(),
        generated_at="2026-10-04T01:00:00+00:00",
    )
    schema = json.loads((ROOT / "schemas" / "company_economic_core_v0.1.schema.json").read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(result),
        key=lambda e: list(e.path),
    )
    assert errors == []


def test_core_hash_tampering_is_detected():
    result = build_company_economic_core(
        *_inputs(),
        generated_at="2026-10-04T01:00:00+00:00",
    )
    result["valuation_route"]["model_router_suggestion"] = "tampered"
    assert "AUDIT_CORE_HASH_MISMATCH" in validate_company_economic_core(result)


def test_no_research_namespace_import_in_company_economic_core():
    source = (ROOT / "iios_mvp" / "company_economic_core.py").read_text(encoding="utf-8")
    assert "from research" not in source
    assert "import research" not in source
