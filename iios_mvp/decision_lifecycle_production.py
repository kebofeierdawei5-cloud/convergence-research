from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .decision_admission import validate_decision_admission_receipt

DECISION_LIFECYCLE_CONTRACT_VERSION = "IIOS-DECISION-LIFECYCLE-0.2"
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
    direct_action = decision.get('action')
    if direct_action is not None:
        value = direct_action
    else:
        nested = decision.get('decision')
        if isinstance(nested, Mapping):
            value = nested.get('action')
        else:
            value = None
    result = str(value or '').strip().upper()
    if result not in DECISION_ACTIONS:
        raise ValueError(f'decision.action has unsupported action: {result}')
    return result

def _derive_series_identity(snapshot_core: Mapping[str, Any]) -> tuple[str, dict[str, str], str]:
    input_data = snapshot_core.get('input')
    if not isinstance(input_data, Mapping):
        raise ValueError('snapshot.input must be an object')
    identity = {
        'case_id': _text(input_data.get('case_id'), 'snapshot.input.case_id'),
        'market': _text(input_data.get('market'), 'snapshot.input.market').upper(),
        'symbol': _text(input_data.get('symbol'), 'snapshot.input.symbol').upper(),
        'company': _text(input_data.get('company'), 'snapshot.input.company'),
    }
    series_id = f"{identity['market']}-{identity['symbol']}"
    return series_id, identity, _sha(identity)

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

def build_decision_revision(*, decision_series_id: str | None = None, revision: int, snapshot: Mapping[str, Any], run_id: str, trigger_event_id: str | None = None, decision_admission: Mapping[str, Any] | None = None, run_authority_ref: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError('revision must be a positive integer')
    snapshot_core = _snapshot_core(snapshot)
    input_data = snapshot_core['input']
    decision = snapshot_core['decision']
    case_id = _text(input_data.get('case_id'), 'snapshot.input.case_id')
    cutoff_date = _text(input_data.get('cutoff_date'), 'snapshot.input.cutoff_date')
    canonical_series_id, series_identity, series_identity_hash = _derive_series_identity(snapshot_core)
    if decision_series_id is None:
        bound_series_id = canonical_series_id
    else:
        bound_series_id = _text(decision_series_id, 'decision_series_id')
        if bound_series_id != canonical_series_id:
            raise ValueError(
                f'decision_series_id is not canonical for snapshot identity: expected {canonical_series_id}'
            )
    action = _action(decision)
    if snapshot_core["snapshot_schema"] == "IIOS-MVP-SNAPSHOT-0.3.0":
        if decision_admission is None:
            raise ValueError("canonical v0.3 Decision Revision requires a Decision Admission receipt")
        validate_decision_admission_receipt(decision_admission, snapshot=snapshot)
        if decision_admission["canonical_action"] != action:
            raise ValueError("decision admission canonical_action does not match snapshot action")
        if decision_admission["engine_version"] != snapshot_core["engine_version"]:
            raise ValueError("decision admission engine_version does not match snapshot")
    decision_id = f'{bound_series_id}-r{revision:03d}'
    core = {
        'contract_version': DECISION_LIFECYCLE_CONTRACT_VERSION,
        'decision_id': decision_id,
        'decision_series_id': bound_series_id,
        'decision_series_identity': series_identity,
        'decision_series_identity_hash': series_identity_hash,
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
        'decision_admission': None if decision_admission is None else dict(decision_admission),
    }
    if run_authority_ref is not None:
        core["run_authority_ref"] = dict(run_authority_ref)
    return {**core, 'revision_hash': _sha(core)}

def validate_decision_revision(record: Any, *, case_id: str, cutoff_date: str) -> None:
    if not isinstance(record, Mapping):
        raise ValueError('decision_revision must be an object')
    required = {'contract_version','decision_id','decision_series_id','decision_series_identity','decision_series_identity_hash','revision','run_id','trigger_event_id','case_id','as_of_date','cutoff_date','snapshot_hash','ai_action','decision_status','engine_version','human_approval_required','auto_execution','decision_admission','revision_hash'}
    supplied_fields = set(record)
    if not required.issubset(supplied_fields) or supplied_fields - required - {'run_authority_ref'}:
        raise ValueError('decision_revision fields are invalid')
    if record['contract_version'] != DECISION_LIFECYCLE_CONTRACT_VERSION:
        raise ValueError('decision_revision version mismatch')
    if record['case_id'] != case_id or record['cutoff_date'] != cutoff_date or record['as_of_date'] != cutoff_date:
        raise ValueError('decision_revision case/cutoff mismatch')
    if not isinstance(record['revision'], int) or isinstance(record['revision'], bool) or record['revision'] < 1:
        raise ValueError('decision_revision revision invalid')
    identity = record['decision_series_identity']
    if not isinstance(identity, Mapping) or set(identity) != {'case_id', 'market', 'symbol', 'company'}:
        raise ValueError('decision series identity fields are invalid')
    if identity['case_id'] != record['case_id']:
        raise ValueError('decision series identity mismatch: case_id')
    market = _text(identity['market'], 'decision_series_identity.market').upper()
    symbol = _text(identity['symbol'], 'decision_series_identity.symbol').upper()
    company = _text(identity['company'], 'decision_series_identity.company')
    if record['decision_series_id'] != f'{market}-{symbol}':
        raise ValueError('decision series identity mismatch: series_id')
    if record['decision_id'] != f"{record['decision_series_id']}-r{record['revision']:03d}":
        raise ValueError('decision series identity mismatch: decision_id')
    if _sha({'case_id': identity['case_id'], 'market': market, 'symbol': symbol, 'company': company}) != record['decision_series_identity_hash']:
        raise ValueError('decision series identity hash mismatch')
    if record['decision_status'] != 'AI_PROPOSED':
        raise ValueError('decision_revision status invalid')
    _action({'action': record['ai_action']})
    if record['human_approval_required'] is not True or record['auto_execution'] is not False:
        raise ValueError('decision_revision approval/execution flags invalid')
    if len(str(record['snapshot_hash'])) != 64 or len(str(record['revision_hash'])) != 64:
        raise ValueError('decision_revision hashes invalid')
    admission = record.get('decision_admission')
    if record['engine_version'] == '0.3.0':
        if admission is None:
            raise ValueError('canonical v0.3 Decision Revision requires decision_admission')
        validate_decision_admission_receipt(admission, snapshot={
            'snapshot_schema': 'IIOS-MVP-SNAPSHOT-0.3.0',
            'engine_version': record['engine_version'],
            'input': {
                'case_id': record['case_id'],
                'market': str(admission.get('market', '')).upper(),
                'symbol': str(admission.get('symbol', '')).upper(),
                'company': admission.get('company', ''),
                'cutoff_date': record['cutoff_date'],
            },
            'decision': dict(admission['canonical_decision_projection']),
            'snapshot_hash': record['snapshot_hash'],
        })
        if admission['canonical_action'] != record['ai_action']:
            raise ValueError('decision admission action binding mismatch')
        if (
            admission['case_id'] != identity['case_id']
            or str(admission['market']).upper() != market
            or str(admission['symbol']).upper() != symbol
            or str(admission['company']) != company
        ):
            raise ValueError('decision series identity does not match canonical Decision Admission')
    elif admission is not None:
        raise ValueError('legacy Decision Revision cannot carry decision_admission')
    run_authority_ref = record.get('run_authority_ref')
    if run_authority_ref is not None:
        auth_required = {
            'schema_version', 'run_id', 'case_id', 'market', 'symbol', 'cutoff_date',
            'stage', 'stage_receipt_hash', 'state_hash_at_stage', 'authorized_refs',
            'authorized_hashes', 'authorization_hash',
        }
        if not isinstance(run_authority_ref, Mapping) or set(run_authority_ref) != auth_required:
            raise ValueError('decision_revision run_authority_ref fields are invalid')
        if run_authority_ref['schema_version'] != 'IIOS-RUN-STAGE-AUTH-0.1':
            raise ValueError('decision_revision run_authority_ref version mismatch')
        if run_authority_ref['run_id'] != record['run_id'] or run_authority_ref['stage'] != 'DECISION_ADMITTED':
            raise ValueError('decision_revision run_authority_ref run/stage mismatch')
        if (
            run_authority_ref['case_id'] != identity['case_id']
            or str(run_authority_ref['market']).upper() != market
            or str(run_authority_ref['symbol']).upper() != symbol
            or run_authority_ref['cutoff_date'] != record['cutoff_date']
        ):
            raise ValueError('decision_revision run_authority_ref identity mismatch')
        auth_core = {k: run_authority_ref[k] for k in auth_required if k != 'authorization_hash'}
        if run_authority_ref['authorization_hash'] != _sha(auth_core):
            raise ValueError('decision_revision run_authority_ref hash mismatch')
        if not all(isinstance(run_authority_ref.get(k), str) and len(run_authority_ref[k]) == 64
                   for k in ('stage_receipt_hash', 'state_hash_at_stage')):
            raise ValueError('decision_revision run_authority_ref digest invalid')
        if record['snapshot_hash'] not in run_authority_ref['authorized_hashes']:
            raise ValueError('decision_revision snapshot is not bound to run stage receipt')
        if admission is not None and admission['admission_record_hash'] not in run_authority_ref['authorized_hashes']:
            raise ValueError('Decision Admission is not bound to run stage receipt')
    core = {k: record[k] for k in required if k != 'revision_hash'}
    if run_authority_ref is not None:
        core['run_authority_ref'] = dict(run_authority_ref)
    if record['revision_hash'] != _sha(core):
        raise ValueError('decision_revision revision hash mismatch')

def build_human_approval(*, decision_revision: Mapping[str, Any], approved: bool, note: str, actor_identity: str, authorization_method: str = "HUMAN_AUTHENTICATED") -> dict[str, Any]:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    if not isinstance(approved, bool):
        raise ValueError('approved must be boolean')
    actor = _text(actor_identity, 'actor_identity')
    if authorization_method != 'HUMAN_AUTHENTICATED':
        raise ValueError('authorization_method must equal HUMAN_AUTHENTICATED')
    core = {
        'contract_version': DECISION_LIFECYCLE_CONTRACT_VERSION,
        'decision_id': decision_revision['decision_id'],
        'revision': decision_revision['revision'],
        'revision_hash': decision_revision['revision_hash'],
        'snapshot_hash': decision_revision['snapshot_hash'],
        'approved': approved,
        'approval_status': 'HUMAN_APPROVED' if approved else 'HUMAN_REJECTED',
        'note': _text(note, 'note'),
        'actor_identity': actor,
        'authorization_method': authorization_method,
    }
    return {**core, 'approval_hash': _sha(core)}

def validate_human_approval(record: Any, *, decision_revision: Mapping[str, Any]) -> None:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    if not isinstance(record, Mapping):
        raise ValueError('human_approval must be an object')
    required = {'contract_version','decision_id','revision','revision_hash','snapshot_hash','approved','approval_status','note','actor_identity','authorization_method','approval_hash'}
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
    if not str(record['actor_identity']).strip() or record['authorization_method'] != 'HUMAN_AUTHENTICATED':
        raise ValueError('human_approval actor/authorization boundary invalid')
    core = {k: record[k] for k in required if k != 'approval_hash'}
    if record['approval_hash'] != _sha(core):
        raise ValueError('human_approval approval hash mismatch')

def project_current_approval(*, previous: Mapping[str, Any] | None, decision_revision: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    validate_decision_revision(decision_revision, case_id=decision_revision['case_id'], cutoff_date=decision_revision['cutoff_date'])
    validate_human_approval(approval, decision_revision=decision_revision)
    previous = {} if previous is None else dict(previous)
    if previous:
        validate_current_projection(previous)
    current_revision = int(previous.get('current_revision', 0))
    revision = decision_revision['revision']
    if revision == current_revision and current_revision > 0:
        if previous.get('current_decision_id') != decision_revision['decision_id']:
            raise ValueError('same revision cannot bind a different decision_id')
        if previous.get('snapshot_hash') != decision_revision['snapshot_hash']:
            raise ValueError('same revision cannot bind a different snapshot')
        if approval['approved'] and previous.get('approval_hash') != approval['approval_hash']:
            raise ValueError('conflicting approval for current revision')
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