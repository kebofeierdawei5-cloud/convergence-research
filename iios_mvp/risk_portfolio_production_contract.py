from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

RISK_PORTFOLIO_CONTRACT_VERSION = "IIOS-RISK-PORTFOLIO-PRODUCTION-0.1"
RISK_STATES = {'PASS', 'FAIL', 'UNKNOWN'}
PORTFOLIO_STATES = {'PASS', 'BLOCKED', 'UNKNOWN'}

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()

def _dec(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'{field} must be numeric') from exc
    if not result.is_finite():
        raise ValueError(f'{field} must be finite')
    return result

def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f'{field} must be a non-empty list')
    result = [str(x).strip() for x in value]
    if any(not x for x in result):
        raise ValueError(f'{field} contains an empty item')
    if len(result) != len(set(result)):
        raise ValueError(f'{field} contains duplicate items')
    return result

def _status(value: Any, field: str, allowed: set[str]) -> str:
    result = str(value).strip().upper()
    if result not in allowed:
        raise ValueError(f'{field} has unsupported status: {result}')
    return result

def _package(package: Any) -> tuple[str, dict[str, Any] | None]:
    if package is None:
        return 'ABSENT', None
    if not isinstance(package, Mapping):
        raise ValueError('portfolio.buy_add_package must be an object when supplied')
    required = {'entry_zone','initial_position_pct','target_position_pct','max_position_pct','thesis_break_triggers','monitoring_triggers'}
    missing = sorted(required - set(package))
    if missing:
        raise ValueError(f'portfolio.buy_add_package missing required fields: {missing}')
    zone = package['entry_zone']
    if not isinstance(zone, list) or len(zone) != 2:
        raise ValueError('portfolio.buy_add_package.entry_zone must contain exactly two prices')
    low = _dec(zone[0], 'portfolio.buy_add_package.entry_zone[0]')
    high = _dec(zone[1], 'portfolio.buy_add_package.entry_zone[1]')
    if low <= 0 or high <= 0 or low > high:
        raise ValueError('portfolio.buy_add_package.entry_zone must be positive and ordered')
    values = {}
    for name in ('initial_position_pct','target_position_pct','max_position_pct'):
        value = _dec(package[name], f'portfolio.buy_add_package.{name}')
        if value < 0 or value > 100:
            raise ValueError(f'portfolio.buy_add_package.{name} must be within [0,100]')
        values[name] = value
    if not (values['initial_position_pct'] <= values['target_position_pct'] <= values['max_position_pct']):
        raise ValueError('portfolio.buy_add_package must satisfy initial <= target <= max position')
    return 'COMPLETE', {
        'entry_zone': [str(low), str(high)],
        'initial_position_pct': str(values['initial_position_pct']),
        'target_position_pct': str(values['target_position_pct']),
        'max_position_pct': str(values['max_position_pct']),
        'thesis_break_triggers': _strings(package['thesis_break_triggers'], 'portfolio.buy_add_package.thesis_break_triggers'),
        'monitoring_triggers': _strings(package['monitoring_triggers'], 'portfolio.buy_add_package.monitoring_triggers'),
    }

def validate_risk_portfolio_input(*, risk: Mapping[str, Any], portfolio: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(risk, Mapping):
        raise ValueError('risk must be an object')
    if not isinstance(portfolio, Mapping):
        raise ValueError('portfolio must be an object')
    risk_status = _status(risk.get('status'), 'risk.status', RISK_STATES)
    max_loss = _dec(risk.get('max_loss_pct'), 'risk.max_loss_pct')
    if max_loss < 0 or max_loss >= 100:
        raise ValueError('risk.max_loss_pct must be within [0,100)')
    thesis_breaks = _strings(risk.get('thesis_breaks'), 'risk.thesis_breaks')
    evidence_ids = _strings(risk.get('evidence_ids'), 'risk.evidence_ids')
    position = _dec(portfolio.get('position_pct'), 'portfolio.position_pct')
    if position < 0 or position > 100:
        raise ValueError('portfolio.position_pct must be within [0,100]')
    constraint_status = _status(portfolio.get('constraint_status'), 'portfolio.constraint_status', PORTFOLIO_STATES)
    if 'can_add' not in portfolio:
        raise ValueError('portfolio.can_add is required; implicit default is forbidden')
    can_add = portfolio['can_add']
    if not isinstance(can_add, bool):
        raise ValueError('portfolio.can_add must be boolean')
    package_status, package = _package(portfolio.get('buy_add_package'))
    return {
        'risk': {'status': risk_status, 'max_loss_pct': str(max_loss), 'thesis_breaks': thesis_breaks, 'evidence_ids': evidence_ids},
        'portfolio': {'position_pct': str(position), 'constraint_status': constraint_status, 'can_add': can_add, 'buy_add_package': package, 'package_status': package_status},
        'readiness': {'risk_ready': risk_status == 'PASS', 'portfolio_constraint_ready': constraint_status == 'PASS', 'package_ready': package_status == 'COMPLETE'},
    }

def build_risk_portfolio_contract(*, case_id: str, cutoff_date: str, risk: Mapping[str, Any], portfolio: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_risk_portfolio_input(risk=risk, portfolio=portfolio)
    core = {'contract_version': RISK_PORTFOLIO_CONTRACT_VERSION, 'case_id': case_id, 'cutoff_date': cutoff_date, **normalized, 'policy_effect': 'NO_DIRECT_DECISION_PRECEDENCE_CHANGE'}
    record = {**core, 'audit_sha256': _sha(core)}
    validate_risk_portfolio_contract(record, case_id=case_id, cutoff_date=cutoff_date)
    return record

def validate_risk_portfolio_contract(record: Any, *, case_id: str, cutoff_date: str) -> None:
    if not isinstance(record, Mapping):
        raise ValueError('risk_portfolio_contract must be an object')
    required = {'contract_version','case_id','cutoff_date','risk','portfolio','readiness','policy_effect','audit_sha256'}
    if set(record) != required:
        raise ValueError('risk_portfolio_contract fields are invalid')
    if record['contract_version'] != RISK_PORTFOLIO_CONTRACT_VERSION:
        raise ValueError('risk_portfolio_contract version mismatch')
    if record['case_id'] != case_id:
        raise ValueError('risk_portfolio_contract case_id mismatch')
    if record['cutoff_date'] != cutoff_date:
        raise ValueError('risk_portfolio_contract cutoff_date mismatch')
    if record['policy_effect'] != 'NO_DIRECT_DECISION_PRECEDENCE_CHANGE':
        raise ValueError('risk_portfolio_contract policy effect invalid')
    normalized = validate_risk_portfolio_input(risk=record['risk'], portfolio=record['portfolio'])
    if record['risk'] != normalized['risk'] or record['portfolio'] != normalized['portfolio'] or record['readiness'] != normalized['readiness']:
        raise ValueError('risk_portfolio_contract normalized input drift')
    core = {k: record[k] for k in required if k != 'audit_sha256'}
    if record['audit_sha256'] != _sha(core):
        raise ValueError('risk_portfolio_contract audit hash mismatch')

__all__ = ['RISK_PORTFOLIO_CONTRACT_VERSION','build_risk_portfolio_contract','validate_risk_portfolio_input','validate_risk_portfolio_contract']