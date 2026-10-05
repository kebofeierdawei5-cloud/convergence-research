from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

DECISION_LIFECYCLE_CONTRACT_VERSION = "IIOS-DECISION-LIFECYCLE-0.1"
REVISION_STATUSES = {"AI_PROPOSED", "HUMAN_APPROVED", "HUMAN_REJECTED"}
APPROVAL_STATUSES = {"HUMAN_APPROVED", "HUMAN_REJECTED"}
DECISION_ACTIONS = {"BUY", "ADD", "HOLD", "REDUCE", "EXIT", "NO-BUY", "WATCH", "REVIEW_REQUIRED"}

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()

def _text(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f'{field} is required')
    return result

def _action(decision: Mapping[str, Any]) -> str:
    value = decision.get('action', decision.get('decision'))
    result = str(value or '').strip().upper()
    if result not in DECISION_ACTIONS:
        raise ValueError(f'decision.action has unsupported action: {result}')
    return result

def _snapshot_core(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ValueError('snapshot must be an object')
    required = {'snapshot_schema', 'engine_version', 'input', 'decision', 'snapshot_hash'}
    if not required.issubset(set(snapshot)):
        raise ValueError('snapshot is missing required fields')
    if not isinstance(snapshot.get('input'), Mapping) or not isinstance(snapshot.get('decision'), Mapping):
        raise ValueError('snapshot.input and snapshot.decision must be objects')
    snapshot_core = {k: snapshot[k] for k in ('snapshot_schema', 'engine_version', 'input', 'decision')}
    if _sha(snapshot_core) != snapshot['snapshot_hash']:
        raise ValueError('snapshot hash mismatch')
    return snapshot_core

def build_decision_revision(*, decision_series_id: str, revision: int, snapshot: Mapping[str, Any], run_id: str, trigger_event_id: str | None = None) -> dict[str, Any]:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError('revision must be a positive integer')
    snapshot_core = _snapshot_core(snapshot)
    input_data = snapshot_core['input']
    decision = snapshot_core['decision']
    case_id = _text(input_data.get('case_id'), 'snapshot.input.case_id')
    cutoff_date = _text(input_data.get('cutoff_date'), 'snapshot.input.cutoff_date')
    action = _action(decision)
    decision_id = f'{decision_series_id}-r{revision:03d}'
    core = {
        'contract_version': DECISION_LIFECYCLE_CONTRACT_VERSION,
        'decision_id': decision_id,
        'decision_series_id': _text(decision_series_id, 'decision_series_id'),
        'revision': revision,
        'run_id': _text(run_id, 'run_id'),
        'trigger_event_id': None if trigger_event_id is None else _text(trigger_event_id, 'trigger_event_id'),
        'case_id': case_id,
        'as_of_date': cutoff_date,
        'cutoff_date': cutoff_date,
        'snapshot_hash': snapshot['snapshot_hash'],
        'ai_action': action,
        'decision_status': 'AI_PROPOSED',
        'engine_version': _text(snapshot_core['engine_version'], 'snapshot.engine_version'),
        'human_approval_required': True,
        'auto_execution': False,
    }
    return {**core, 'revision_hash': _sha(core)}

def validate_decision_revision(record: Any, *, case_id: str, cutoff_date: str) -> None:
    if not isinstance(record, Mapping):
        raise ValueError('decision_revision must be an object')
    required = {'contract_version','decision_id','decision_series_id','revision','run_id','trigger_event_id','case_id','as_of_date','cutoff_date','snapshot_hash','ai_action','decision_status','engine_version','human_approval_required','auto_execution','revision_hash'}
    if set(record) != required:
        raise ValueError('decision_revision fields are invalid')
    if record['contract_version'] != DECISION_LIFECYCLE_CONTRACT_VERSION:
        raise ValueError('decision_revision version mismatch')
    if record['case_id'] != case_id or record['cutoff_date'] != cutoff_date or record['as_of_date'] != cutoff_date:
        raise ValueError('decision_revision case/cutoff mismatch')
    if not isinstance(record['revision'], int) or isinstance(record['revision'], bool) or record['revision'] < 1:
        raise ValueError('decision_revision revision invalid')
    if record['decision_status'] != 'AI_PROPOSED':
        raise ValueError('decision_revision status invalid')
    _action({'action': record['ai_action']})
    if record['human_approval_required'] is not True or record['auto_execution'] is not False:
        raise ValueError('decision_revision approval/execution flags invalid')
    if len(str(record['snapshot_hash'])) != 64 or len(str(record['revision_hash'])) != 64:
        raise ValueError('decision_revision hashes invalid')
    core = {k: record[k] for k in required if k != 'revision_hash'}
    if record['revision_hash'] != _sha(core):
        raise ValueError('decision_revision revision hash mismatch')

def build_human_approval(*, decision_revision: Mapping[str, Any], approved: bool, note: str) -> dict[str, Any]:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    if not isinstance(approved, bool):
        raise ValueError('approved must be boolean')
    core = {
        'contract_version': DECISION_LIFECYCLE_CONTRACT_VERSION,
        'decision_id': decision_revision['decision_id'],
        'revision': decision_revision['revision'],
        'revision_hash': decision_revision['revision_hash'],
        'snapshot_hash': decision_revision['snapshot_hash'],
        'approved': approved,
        'approval_status': 'HUMAN_APPROVED' if approved else 'HUMAN_REJECTED',
        'note': _text(note, 'note'),
    }
    return {**core, 'approval_hash': _sha(core)}

def validate_human_approval(record: Any, *, decision_revision: Mapping[str, Any]) -> None:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    if not isinstance(record, Mapping):
        raise ValueError('human_approval must be an object')
    required = {'contract_version','decision_id','revision','revision_hash','snapshot_hash','approved','approval_status','note','approval_hash'}
    if set(record) != required:
        raise ValueError('human_approval fields are invalid')
    if record['contract_version'] != DECISION_LIFECYCLE_CONTRACT_VERSION:
        raise ValueError('human_approval version mismatch')
    for field in ('decision_id','revision_hash','snapshot_hash'):
        if record[field] != decision_revision[field]:
            raise ValueError(f'human_approval {field} does not match decision revision')
    if record['revision'] != decision_revision['revision'] or not isinstance(record['approved'], bool):
        raise ValueError('human_approval revision/approved invalid')
    expected_status = 'HUMAN_APPROVED' if record['approved'] else 'HUMAN_REJECTED'
    if record['approval_status'] != expected_status or not str(record['note']).strip():
        raise ValueError('human_approval status or note invalid')
    core = {k: record[k] for k in required if k != 'approval_hash'}
    if record['approval_hash'] != _sha(core):
        raise ValueError('human_approval approval hash mismatch')

def project_current_approval(*, previous: Mapping[str, Any] | None, decision_revision: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    validate_human_approval(approval, decision_revision=decision_revision)
    previous = {} if previous is None else dict(previous)
    current_revision = int(previous.get('current_revision', 0))
    revision = decision_revision['revision']
    if not approval['approved'] or revision < current_revision:
        return {
            **previous,
            'projection_status': 'UNCHANGED',
            'candidate_decision_id': decision_revision['decision_id'],
            'candidate_revision': revision,
        }
    core = {
        'contract_version': DECISION_LIFECYCLE_CONTRACT_VERSION,
        'decision_series_id': decision_revision['decision_series_id'],
        'current_decision_id': decision_revision['decision_id'],
        'current_revision': revision,
        'snapshot_hash': decision_revision['snapshot_hash'],
        'approval_hash': approval['approval_hash'],
        'projection_status': 'CURRENT',
    }
    return {**core, 'projection_hash': _sha(core)}

def validate_current_projection(record: Any) -> None:
    if not isinstance(record, Mapping):
        raise ValueError('current_projection must be an object')
    status = record.get('projection_status')
    if status == 'UNCHANGED':
        if 'candidate_decision_id' not in record or 'candidate_revision' not in record:
            raise ValueError('unchanged projection missing candidate fields')
        return
    required = {'contract_version','decision_series_id','current_decision_id','current_revision','snapshot_hash','approval_hash','projection_status','projection_hash'}
    if set(record) != required:
        raise ValueError('current_projection fields are invalid')
    if record['contract_version'] != DECISION_LIFECYCLE_CONTRACT_VERSION or record['projection_status'] != 'CURRENT':
        raise ValueError('current_projection status/version invalid')
    if not isinstance(record['current_revision'], int) or record['current_revision'] < 1:
        raise ValueError('current_projection revision invalid')
    core = {k: record[k] for k in required if k != 'projection_hash'}
    if record['projection_hash'] != _sha(core):
        raise ValueError('current_projection projection hash mismatch')

__all__ = ['DECISION_LIFECYCLE_CONTRACT_VERSION','build_decision_revision','validate_decision_revision','build_human_approval','validate_human_approval','project_current_approval','validate_current_projection']