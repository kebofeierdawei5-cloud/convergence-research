from pathlib import Path
import ast

ROOT = Path(__file__).parents[1]


def test_b2e_does_not_call_decision_from_semantic_producer():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.append(node.func.id)
    assert "_assert_no_authority_fields" in calls
    assert "admit_canonical_decision" in calls


def test_b2e_requires_canonical_decision_admission():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert "admit_canonical_decision(" in source
    assert "build_decision_revision(" in source


def test_b2e_human_execution_boundary_is_explicit():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert '"semantic_producer_can_decide": False' in source
    assert '"canonical_decision_kernel_is_authoritative": True' in source
    assert '"human_approval_is_required": True' in source
    assert '"automatic_execution_is_forbidden": True' in source


def test_b2e_does_not_import_live_provider_or_order_execution():
    source = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    assert "live_provider_" not in source
    assert "order" not in source.lower()


def test_operator_price_lane_is_never_promoted_to_exchange_evidence():
    intake = (ROOT / "iios_mvp/operator_entered_price_decision_input_v01.py").read_text(encoding="utf-8")
    core = (ROOT / "iios_mvp/investment_core_contract_v03.py").read_text(encoding="utf-8")
    resolver = (ROOT / "iios_mvp/canonical_current_price.py").read_text(encoding="utf-8")

    assert '"record_class": "OPERATOR_ATTESTED_MARKET_DATA"' in intake
    assert '"source_origin_verified": False' in intake
    assert '"source_vintage_verified": False' in intake
    assert '"source_use_rights_verified": False' in intake
    assert '"canonical_exchange_price_admission": False' in intake
    assert 'price_input_class == "OPERATOR_ATTESTED_MARKET_DATA"' in core
    assert "operator-attested input must not claim a canonical price admission hash" in core
    # Manual input uses a separate resolver; do not add a fake admit_current_price
    # path or weaken the established canonical price registry's ADMITTED contract.
    assert "class FileSystemCanonicalCurrentPriceRegistry" in resolver
    assert "canonical current price requires an ADMITTED market observation" in resolver


def test_operator_price_references_are_bound_as_two_distinct_stage_hashes():
    b2e = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    authority = (ROOT / "iios_mvp/canonical_run_authority_v01.py").read_text(encoding="utf-8")
    assert 'operator-price-input-record:' in b2e
    assert 'operator-price-input-receipt:' in b2e
    assert 'str(operator_price_input_binding["record_sha256"])' in b2e
    assert 'str(operator_price_input_binding["receipt_sha256"])' in b2e
    assert 'def _validate_decision_pending_input_refs(' in authority
    assert 'operator-price-input-record:' in authority
    assert 'operator-price-input-receipt:' in authority
    assert 'DECISION_PENDING operator-price hashes do not match snapshot input reference' in authority


def test_operator_price_is_not_used_as_p4f_baseline_or_public_receipt_payload():
    price_response = (ROOT / "iios_mvp/p2_1_canonical_price_response.py").read_text(encoding="utf-8")
    b2e = (ROOT / "iios_mvp/b2e_nl_semantic_decision_e2e_v01.py").read_text(encoding="utf-8")
    report = (ROOT / "iios_mvp/investor_review_report_v02.py").read_text(encoding="utf-8")
    assert "MIE calibration price provenance value is missing" in price_response
    assert "model_reference_price, decision_current_price = _reference_price(" in price_response
    assert 'gap["price"] = bound_price' in b2e
    assert 'return_gate["entry_price"] = bound_price' in b2e
    assert "current_price_assurance_limitation_codes" in report
    assert "operator_price_input_ref" not in report[report.index('"decision": {', report.index("def build_machine_surface")):report.index('"returns": returns', report.index("def build_machine_surface"))]
