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


def test_unknown_event_propagates_to_unknown_evaluation_status():
    c = contract()
    s = build_monitoring_state(monitor_id='m1', trigger_contract=c, lifecycle_status='ACTIVE')
    e = evt(c, value='not-a-number')
    n = apply_trigger_event(previous_state=s, trigger_contract=c, trigger_event=e)
    assert n['last_trigger_state'] == 'UNKNOWN'
    assert n['evaluation_status'] == 'UNKNOWN'


def test_replay_reconstructs_persisted_state(tmp_path):
    from iios_mvp.store import (
        apply_monitoring_event,
        create_or_load_series,
        initialize_monitoring_state,
        replay_monitoring_state,
        write_decision_revision,
        write_snapshot,
        write_trigger_contract,
        write_trigger_event,
    )
    import hashlib
    import json

    core = {
        'snapshot_schema': 'IIOS-MVP-SNAPSHOT-0.3.0',
        'engine_version': '0.3.0',
        'input': {'case_id': 'RC-CN-A-300750-20261004', 'cutoff_date': '2026-10-04'},
        'decision': {'action': 'HOLD'},
    }
    snapshot_hash = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    snapshot = {**core, 'snapshot_hash': snapshot_hash}
    write_snapshot(tmp_path, snapshot)
    series = create_or_load_series(tmp_path, 'CN-A', '300750', 'CATL', '2026-10-04T00:00:00Z')
    write_decision_revision(tmp_path, series['decision_series_id'], 1, snapshot, 'run-1')
    revision = json.loads((tmp_path / 'CN-A-300750-r001.decision.json').read_text())

    trigger = write_trigger_contract(tmp_path, 'CN-A-300750-r001', {
        'trigger_id': 'tr-replay',
        'decision_id': 'CN-A-300750-r001',
        'decision_series_id': 'CN-A-300750',
        'revision': 1,
        'decision_revision_hash': revision['revision_hash'],
        'case_id': 'RC-CN-A-300750-20261004',
        'decision_cutoff_date': '2026-10-04',
        'role': 'MONITORING',
        'metric_id': 'market_price',
        'operator': 'LTE',
        'target': '350',
        'unit': 'CNY/share',
        'evidence_ids': [],
        'enabled': True,
    })
    initialize_monitoring_state(tmp_path, 'tr-replay', 'monitor-1')
    event_path = write_trigger_event(tmp_path, {
        'trigger_id': 'tr-replay',
        'trigger_event_id': 'evt-replay',
        'evaluation_cutoff_at': '2026-10-05T10:06:00+00:00',
        'observed_at': '2026-10-05T10:00:00+00:00',
        'known_at': '2026-10-05T10:05:00+00:00',
        'source_id': 'szse',
        'evidence_id': 'ev-replay',
        'value': '349.5',
        'previous_value': None,
    })
    apply_monitoring_event(tmp_path, 'evt-replay')
    result = replay_monitoring_state(tmp_path, 'tr-replay')
    assert result['replay_status'] == 'PASS'
    assert result['last_event_id'] == 'evt-replay'
    assert event_path.exists()
    assert trigger.exists()


def test_due_reference_is_persisted_and_replayed_deterministically():
    c = contract()
    s = build_monitoring_state(
        monitor_id='m1',
        trigger_contract=c,
        lifecycle_status='ACTIVE',
        next_due_at='2026-10-07T00:00:00+00:00',
        evaluation_reference_at='2026-10-06T00:00:00+00:00',
    )
    assert s['due_reference_at'] == '2026-10-06T00:00:00+00:00'
    assert s['due_state'] == 'NOT_DUE'
    validate_monitoring_state(s, trigger_contract=c)


def test_scheduled_state_requires_explicit_due_reference():
    c = contract()
    with pytest.raises(ValueError, match='evaluation_reference_at is required'):
        build_monitoring_state(
            monitor_id='m1',
            trigger_contract=c,
            lifecycle_status='ACTIVE',
            next_due_at='2026-10-07T00:00:00+00:00',
        )


def test_evaluation_cutoff_cannot_move_backwards():
    c = contract()
    s = build_monitoring_state(monitor_id='m1', trigger_contract=c, lifecycle_status='ACTIVE')
    n = apply_trigger_event(
        previous_state=s,
        trigger_contract=c,
        trigger_event=evt(c, event_id='e2', known='2026-10-05T11:05:00+00:00', cutoff='2026-10-05T11:06:00+00:00'),
    )
    with pytest.raises(ValueError, match='evaluation_cutoff_at cannot move backwards'):
        apply_trigger_event(
            previous_state=n,
            trigger_contract=c,
            trigger_event=evt(c, event_id='e3', known='2026-10-05T12:05:00+00:00', cutoff='2026-10-05T11:05:00+00:00'),
        )
