from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from iios_mvp.decision_admission import admit_canonical_decision
from iios_mvp.decision_lifecycle_production import build_human_approval, validate_human_approval
from iios_mvp.investment_core_contract_v03 import decide_v03
from iios_mvp.store import create_or_load_series, write_decision_revision, write_snapshot
from tests.decision_admission_fixture import build_fixture_admission_receipt
from tools.c3_kolun_second_company_e2e import admit_price, build_case, load_case_fixture, AUTHORITY_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(case: dict, decision: dict) -> dict:
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": case["case_id"],
            "market": case["market"],
            "symbol": case["symbol"],
            "company": case["company"],
            "as_of_date": case["as_of_date"],
            "cutoff_date": case["cutoff_date"],
        },
        "decision": decision,
    }
    core["snapshot_hash"] = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return core


def _canonical_kolun_case():
    fixture = load_case_fixture()
    registry, price_ref = admit_price()
    return build_case(fixture, price_ref), registry


def test_c8_auth_001_admission_reexecutes_kernel_and_rejects_forged_decision():
    case, registry = _canonical_kolun_case()
    canonical_decision = decide_v03(case, current_price_resolver=registry, upstream_authority_resolver=AUTHORITY_REGISTRY)
    valid_snapshot = _snapshot(case, canonical_decision)

    receipt = admit_canonical_decision(
        case=case,
        snapshot=valid_snapshot,
        current_price_resolver=registry,
        upstream_authority_resolver=AUTHORITY_REGISTRY,
    )
    assert receipt["status"] == "ADMITTED"
    assert receipt["admission_method"] == "CANONICAL_DECIDE_V03_REEXECUTED"
    assert receipt["canonical_action"] == canonical_decision["action"]

    forged = deepcopy(valid_snapshot)
    forged["decision"] = deepcopy(forged["decision"])
    forged["decision"]["action"] = "BUY"
    forged["snapshot_hash"] = hashlib.sha256(
        json.dumps(
            {k: forged[k] for k in ("snapshot_schema", "engine_version", "input", "decision")},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValueError, match="does not equal freshly re-executed"):
        admit_canonical_decision(
            case=case,
            snapshot=forged,
            current_price_resolver=registry,
        )


def test_c8_auth_002_store_rejects_cross_company_series_binding(tmp_path):
    fixture = load_case_fixture()
    registry, price_ref = admit_price()
    case = build_case(fixture, price_ref)
    decision = decide_v03(case, current_price_resolver=registry)
    snapshot = _snapshot(case, decision)

    series = create_or_load_series(
        tmp_path,
        "CN-A",
        "300750",
        "CATL",
        "2026-10-06T00:00:00+00:00",
    )
    write_snapshot(tmp_path, snapshot)
    receipt = build_fixture_admission_receipt(
        snapshot=snapshot,
        canonical_decision=decision,
    )

    with pytest.raises(ValueError, match="decision series identity mismatch"):
        write_decision_revision(
            tmp_path,
            series["decision_series_id"],
            1,
            snapshot,
            "c8-auth-002",
            decision_admission=receipt,
        )


def test_c8_auth_003_approval_requires_actor_and_human_authorization(tmp_path):
    from tests.test_c7_full_lifecycle_e2e import seed_c7

    _, _, revision_path, _, _ = seed_c7(tmp_path)
    revision = json.loads(revision_path.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="actor_identity"):
        build_human_approval(
            decision_revision=revision,
            approved=True,
            note="missing actor",
            actor_identity="",
        )

    with pytest.raises(ValueError, match="authorization_method"):
        build_human_approval(
            decision_revision=revision,
            approved=True,
            note="wrong authorization boundary",
            actor_identity="human:owner",
            authorization_method="AUTOMATED",
        )


def test_c8_auth_003_tampered_actor_boundary_is_detected(tmp_path):
    from tests.test_c7_full_lifecycle_e2e import seed_c7

    _, _, revision_path, _, _ = seed_c7(tmp_path)
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    approval = build_human_approval(
        decision_revision=revision,
        approved=True,
        note="valid actor boundary",
        actor_identity="human:owner",
    )
    tampered = deepcopy(approval)
    tampered["actor_identity"] = "automation:llm"
    with pytest.raises(ValueError, match="approval hash mismatch"):
        validate_human_approval(tampered, decision_revision=revision)
