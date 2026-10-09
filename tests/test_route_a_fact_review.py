from __future__ import annotations

from tools.route_a_fact_review import FACT_SPECS, SCHEMA, compact


def test_route_a_fact_candidates_have_unique_ids_and_explicit_source_locators():
    assert SCHEMA == "IIOS-ROUTE-A-FACT-EXTRACTION-REVIEW-0.1"
    assert len(FACT_SPECS) == 11
    ids = [row["id"] for row in FACT_SPECS]
    assert len(ids) == len(set(ids))
    for row in FACT_SPECS:
        assert row["source"].startswith("SZSE-")
        assert isinstance(row["page"], int) and row["page"] >= 1
        assert isinstance(row["printed_page"], int) and row["printed_page"] >= 1
        assert "." in row["field"]
        assert row["claim"]
        assert row["terms"]
        assert row["candidate_date"] in {"2026-08-20", "2026-10-09"}
        assert row["section"]


def test_fact_locator_whitespace_normalization_only_removes_whitespace():
    assert compact(" 营业收入（元）\n13,129,300,260.89 ") == "营业收入（元）13,129,300,260.89"
    assert compact("  0.2322%  ") == "0.2322%"


def test_all_specs_are_review_candidates_not_admission_instructions():
    # Fact specifications contain text terms and candidate metadata only; the
    # runtime always sets known_at=null, provenance/status UNKNOWN and
    # admission_status=NOT_ADMITTED until an independent B2/PIT adjudication.
    for row in FACT_SPECS:
        assert "known_at" not in row
        assert "status" not in row
        assert "provenance_class" not in row
