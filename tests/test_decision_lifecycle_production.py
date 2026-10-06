from jsonschema import Draft202012Validator, FormatChecker

from tests.decision_admission_fixture import build_fixture_admission_receipt
from iios_mvp.decision_lifecycle_production import (
    build_decision_revision,
    build_human_approval,
    project_current_approval,
    validate_current_projection,
    validate_decision_revision,
    validate_human_approval,
)

CASE = "V03-DL-001"
CUTOFF = "2026-10-04"


def snapshot(action="REVIEW_REQUIRED"):
    core = {
        "snapshot_schema": "IIOS-MVP-SNAPSHOT-0.3.0",
        "engine_version": "0.3.0",
        "input": {
            "case_id": CASE,
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "cutoff_date": CUTOFF,
        },
        "decision": {
            "action": action,
        },
    }
    import hashlib
    import json

    core["snapshot_hash"] = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return core


def admission(s):
    return build_fixture_admission_receipt(snapshot=s, canonical_decision=s["decision"])


def revision(s, revision_number=1, run_id="run-1"):
    return build_decision_revision(
        decision_series_id="CN-A-300750",
        revision=revision_number,
        snapshot=s,
        run_id=run_id,
        decision_admission=admission(s),
    )


def test_revision_is_deterministic():
    s = snapshot()
    a = revision(s)
    b = revision(s)
    assert a == b
    assert a["decision_status"] == "AI_PROPOSED"
    assert a["human_approval_required"] is True
    assert a["auto_execution"] is False
    validate_decision_revision(a, case_id=CASE, cutoff_date=CUTOFF)


def test_revision_rejects_legacy_decision_key():
    import pytest

    s = snapshot()
    s["decision"] = {"decision": "HOLD"}
    import hashlib
    import json

    core = {k: s[k] for k in ("snapshot_schema", "engine_version", "input", "decision")}
    s["snapshot_hash"] = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(KeyError, match="action"):
        revision(s)

def test_approval_binds_exact_revision_and_snapshot():
    rev = revision(snapshot())
    approval = build_human_approval(
        decision_revision=rev,
        approved=True,
        note="human review complete",
        actor_identity="human:test",
    )
    validate_human_approval(approval, decision_revision=rev)
    tampered = dict(approval)
    tampered["snapshot_hash"] = "0" * 64
    import pytest

    with pytest.raises(ValueError, match="snapshot_hash"):
        validate_human_approval(tampered, decision_revision=rev)


def test_approval_hash_tampering_is_detected():
    rev = revision(snapshot())
    approval = build_human_approval(
        decision_revision=rev,
        approved=True,
        note="approve",
        actor_identity="human:test",
    )
    approval["note"] = "tampered"
    import pytest

    with pytest.raises(ValueError, match="approval hash mismatch"):
        validate_human_approval(approval, decision_revision=rev)


def test_current_projection_is_monotonic():
    rev1 = revision(snapshot(), 1, "run-1")
    ap1 = build_human_approval(
        decision_revision=rev1,
        approved=True,
        note="r1",
        actor_identity="human:test",
    )
    p1 = project_current_approval(previous=None, decision_revision=rev1, approval=ap1)
    validate_current_projection(p1)

    s2 = snapshot("BUY")
    rev2 = revision(s2, 2, "run-2")
    ap2 = build_human_approval(
        decision_revision=rev2,
        approved=True,
        note="r2",
        actor_identity="human:test",
    )
    p2 = project_current_approval(previous=p1, decision_revision=rev2, approval=ap2)
    assert p2["current_revision"] == 2

    p_old = project_current_approval(previous=p2, decision_revision=rev1, approval=ap1)
    assert p_old["projection_status"] == "UNCHANGED"
    assert p_old["current_revision"] == 2


def test_same_revision_cannot_be_overwritten_by_conflicting_approval():
    rev = revision(snapshot())
    first = build_human_approval(
        decision_revision=rev,
        approved=True,
        note="first",
        actor_identity="human:test",
    )
    current = project_current_approval(previous=None, decision_revision=rev, approval=first)
    conflicting = build_human_approval(
        decision_revision=rev,
        approved=True,
        note="second",
        actor_identity="human:test",
    )
    with __import__("pytest").raises(ValueError, match="conflicting approval"):
        project_current_approval(previous=current, decision_revision=rev, approval=conflicting)


def test_rejected_approval_does_not_replace_current():
    rev1 = revision(snapshot(), 1, "run-1")
    ap1 = build_human_approval(
        decision_revision=rev1,
        approved=True,
        note="r1",
        actor_identity="human:test",
    )
    current = project_current_approval(previous=None, decision_revision=rev1, approval=ap1)

    rev2 = revision(snapshot("BUY"), 2, "run-2")
    ap2 = build_human_approval(
        decision_revision=rev2,
        approved=False,
        note="reject",
        actor_identity="human:test",
    )
    p = project_current_approval(previous=current, decision_revision=rev2, approval=ap2)
    assert p["projection_status"] == "UNCHANGED"
    assert p["current_revision"] == 1
    assert p["current_decision_id"] == "CN-A-300750-r001"


def test_revision_approval_projection_schema_accepts_records():
    import json

    schema = json.load(open("schemas/decision_lifecycle_v0.2.schema.json", encoding="utf-8"))
    rev = revision(snapshot())
    approval = build_human_approval(
        decision_revision=rev,
        approved=True,
        note="approve",
        actor_identity="human:test",
    )
    projection = project_current_approval(previous=None, decision_revision=rev, approval=approval)

    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(rev)) == []
    assert list(
        Draft202012Validator(schema["$defs"]["human_approval"], format_checker=FormatChecker()).iter_errors(approval)
    ) == []
    assert list(
        Draft202012Validator(schema["$defs"]["current_projection"], format_checker=FormatChecker()).iter_errors(projection)
    ) == []


def test_revision_without_admission_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="Decision Admission"):
        build_decision_revision(
            decision_series_id="CN-A-300750",
            revision=1,
            snapshot=snapshot(),
            run_id="run-1",
        )


def test_approval_without_actor_is_rejected():
    import pytest

    rev = revision(snapshot())
    with pytest.raises(ValueError, match="actor_identity"):
        build_human_approval(
            decision_revision=rev,
            approved=True,
            note="missing actor",
            actor_identity="",
        )


def test_wrong_admission_action_is_rejected():
    import pytest

    s = snapshot("BUY")
    bad = admission(snapshot("HOLD"))
    with pytest.raises(ValueError, match="snapshot binding mismatch"):
        build_decision_revision(
            decision_series_id="CN-A-300750",
            revision=1,
            snapshot=s,
            run_id="run-1",
            decision_admission=bad,
        )
