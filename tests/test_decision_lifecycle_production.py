from jsonschema import Draft202012Validator, FormatChecker
from iios_mvp.decision_lifecycle_production import *

CASE="V03-DL-001"
CUTOFF="2026-10-04"

def snapshot(action="REVIEW_REQUIRED", hash_seed="a"):
    core={"snapshot_schema":"IIOS-MVP-SNAPSHOT-0.3.0","engine_version":"0.3.0","input":{"case_id":CASE,"cutoff_date":CUTOFF},"decision":{"action":action}}
    import hashlib,json
    h=hashlib.sha256(json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    core["snapshot_hash"]=h
    return core

def test_revision_is_deterministic():
    s=snapshot()
    a=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=s,run_id="run-1")
    b=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=s,run_id="run-1")
    assert a==b
    assert a["decision_status"]=="AI_PROPOSED"
    assert a["human_approval_required"] is True
    assert a["auto_execution"] is False
    validate_decision_revision(a,case_id=CASE,cutoff_date=CUTOFF)

def test_revision_supports_legacy_decision_key():
    s=snapshot()
    s["decision"]={"decision":"HOLD"}
    import hashlib,json
    core={k:s[k] for k in ("snapshot_schema","engine_version","input","decision")}
    s["snapshot_hash"]=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=s,run_id="run-1")["ai_action"]=="HOLD"

def test_approval_binds_exact_revision_and_snapshot():
    rev=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=snapshot(),run_id="run-1")
    approval=build_human_approval(decision_revision=rev,approved=True,note="human review complete")
    validate_human_approval(approval,decision_revision=rev)
    tampered=dict(approval); tampered["snapshot_hash"]="0"*64
    import pytest
    with pytest.raises(ValueError,match="snapshot_hash"):
        validate_human_approval(tampered,decision_revision=rev)

def test_approval_hash_tampering_is_detected():
    rev=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=snapshot(),run_id="run-1")
    approval=build_human_approval(decision_revision=rev,approved=True,note="approve")
    approval["note"]="tampered"
    import pytest
    with pytest.raises(ValueError,match="approval hash mismatch"):
        validate_human_approval(approval,decision_revision=rev)

def test_current_projection_is_monotonic():
    rev1=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=snapshot(),run_id="run-1")
    ap1=build_human_approval(decision_revision=rev1,approved=True,note="r1")
    p1=project_current_approval(previous=None,decision_revision=rev1,approval=ap1)
    validate_current_projection(p1)
    rev2=build_decision_revision(decision_series_id="CN-A-300750",revision=2,snapshot=snapshot("BUY"),run_id="run-2")
    ap2=build_human_approval(decision_revision=rev2,approved=True,note="r2")
    p2=project_current_approval(previous=p1,decision_revision=rev2,approval=ap2)
    assert p2["current_revision"]==2
    p_old=project_current_approval(previous=p2,decision_revision=rev1,approval=ap1)
    assert p_old["projection_status"]=="UNCHANGED"
    assert p_old["current_revision"]==2

def test_same_revision_cannot_be_overwritten_by_conflicting_approval():
    rev = build_decision_revision(
        decision_series_id="CN-A-300750",
        revision=1,
        snapshot=snapshot(),
        run_id="run-1",
    )
    first = build_human_approval(decision_revision=rev, approved=True, note="first")
    current = project_current_approval(previous=None, decision_revision=rev, approval=first)
    conflicting = build_human_approval(decision_revision=rev, approved=True, note="second")
    with __import__("pytest").raises(ValueError, match="conflicting approval"):
        project_current_approval(previous=current, decision_revision=rev, approval=conflicting)


def test_rejected_approval_does_not_replace_current():
    rev=build_decision_revision(decision_series_id="CN-A-300750",revision=2,snapshot=snapshot("BUY"),run_id="run-2")
    ap=build_human_approval(decision_revision=rev,approved=False,note="reject")
    p=project_current_approval(previous={"current_revision":1,"current_decision_id":"CN-A-300750-r001"},decision_revision=rev,approval=ap)
    assert p["projection_status"]=="UNCHANGED"
    assert p["current_revision"]==1

def test_revision_schema_accepts_record():
    rev=build_decision_revision(decision_series_id="CN-A-300750",revision=1,snapshot=snapshot(),run_id="run-1")
    schema=__import__("json").load(open("schemas/decision_lifecycle_v0.1.schema.json"))
    assert list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(rev))==[]
