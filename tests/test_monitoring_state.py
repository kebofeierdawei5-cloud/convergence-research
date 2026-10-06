import json
import pytest
from jsonschema import Draft202012Validator, FormatChecker

from iios_mvp.trigger_production import build_trigger_contract, build_trigger_event
from iios_mvp.monitoring_state import build_monitoring_state, validate_monitoring_state, apply_trigger_event

def contract(**overrides):
    p = dict(trigger_id='tr-1', decision_id='CN-A-300750-r001', decision_series_id='CN-A-300750', revision=1,
             decision_revision_hash='a'*64, case_id='RC-CN-A-300750-20261004', decision_cutoff_date='2026-10-04',
             role='MONITORING', metric_id='market_price', operator='LTE', target='350', unit='CNY/share',
             evidence_ids=[], enabled=True)
    p.update(overrides)
    return build_trigger_contract(**p)

def evt(c, event_id='e1', known='2026-10-05T10:05:00+00:00', cutoff='2026-10-05T10:06:00+00:00', value='349.5'):
    return build_trigger_event(trigger_contract=c, trigger_event_id=event_id, evaluation_cutoff_at=cutoff,
                               observed_at='2026-10-05T10:00:00+00:00', known_at=known, source_id='szse', evidence_id='ev-'+event_id, value=value)

def test_initial_state_is_deterministic_and_hash_protected():
    c=contract(); a=build_monitoring_state(monitor_id='m1', trigger_contract=c, lifecycle_status='ACTIVE', next_due_at=None)
    b=build_monitoring_state(monitor_id='m1', trigger_contract=c, lifecycle_status='ACTIVE', next_due_at=None)
    assert a==b and a['evaluation_status']=='NEVER_EVALUATED' and a['due_state']=='UNSCHEDULED'
    validate_monitoring_state(a, trigger_contract=c)

def test_due_states_are_explicit():
    c=contract()
    assert build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE',next_due_at='2026-10-06T00:00:00+00:00',evaluation_reference_at='2026-10-05T00:00:00+00:00')['due_state']=='NOT_DUE'
    assert build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE',next_due_at='2026-10-06T00:00:00+00:00',evaluation_reference_at='2026-10-06T00:00:00+00:00')['due_state']=='DUE'
    assert build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE',next_due_at='2026-10-05T00:00:00+00:00',evaluation_reference_at='2026-10-06T00:00:00+00:00')['due_state']=='OVERDUE'

def test_event_advances_state():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE')
    e=evt(c); n=apply_trigger_event(previous_state=s,trigger_contract=c,trigger_event=e)
    assert n['evaluation_status']=='VALID' and n['last_trigger_state']=='MATCHED' and n['last_event_id']=='e1'
    validate_monitoring_state(n, trigger_contract=c)

def test_same_event_is_idempotent():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE')
    e=evt(c); n=apply_trigger_event(previous_state=s,trigger_contract=c,trigger_event=e)
    assert apply_trigger_event(previous_state=n,trigger_contract=c,trigger_event=e)==n

def test_older_event_cannot_roll_state_back():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE')
    n=apply_trigger_event(previous_state=s,trigger_contract=c,trigger_event=evt(c,event_id='e2'))
    with pytest.raises(ValueError, match='strictly later'): apply_trigger_event(previous_state=n,trigger_contract=c,trigger_event=evt(c,event_id='e1',known='2026-10-05T10:04:00+00:00',cutoff='2026-10-05T10:05:00+00:00'))

def test_cross_trigger_event_is_blocked():
    c1=contract(); c2=contract(trigger_id='tr-2')
    s=build_monitoring_state(monitor_id='m1',trigger_contract=c1,lifecycle_status='ACTIVE')
    with pytest.raises(ValueError, match='trigger'): apply_trigger_event(previous_state=s,trigger_contract=c1,trigger_event=evt(c2))

def test_tampering_is_blocked():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE'); s['lifecycle_status']='DISABLED'
    with pytest.raises(ValueError, match='hash mismatch'): validate_monitoring_state(s,trigger_contract=c)

def test_disabled_state_remains_non_decisional():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='DISABLED')
    e=evt(c,value='1'); n=apply_trigger_event(previous_state=s,trigger_contract=c,trigger_event=e)
    assert n['lifecycle_status']=='DISABLED'

def test_schema_accepts():
    c=contract(); s=build_monitoring_state(monitor_id='m1',trigger_contract=c,lifecycle_status='ACTIVE')
    schema=json.load(open('schemas/monitoring_state_v0.1.schema.json',encoding='utf-8'))
    assert list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(s))==[]
