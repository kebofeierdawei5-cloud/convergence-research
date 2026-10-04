from datetime import date
from decimal import Decimal
from pathlib import Path
import json

import pytest

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment, CandidateCoverageState,
    EvidenceSufficiencyAssessment, EvidenceSufficiencyState,
    MIEAssumption, MIEEconomicRequirement, MIEObservationBasis,
    MIEQualification, MIERepresentation, MarketImpliedExpectation,
)
from iios_mvp.market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation, MIESetResolutionState,
    build_multi_model_market_implied_expectation_set,
)

CUTOFF = date(2026, 10, 4)

def coverage(*ids, status=CandidateCoverageState.SUFFICIENT):
    return CandidateCoverageAssessment(status, 'global-admitted-market-model-universe', tuple(ids), tuple(f'coverage-{x}' for x in ids), 'Global candidate universe is explicitly enumerated.')

def evidence(*ids, status=EvidenceSufficiencyState.SUFFICIENT):
    return EvidenceSufficiencyAssessment(status, 'P4-E evidence is sufficient for the stated dispositions.', tuple(f'evidence-{x}' for x in ids))

def make_mie(*, model_id, family, qualification=MIEQualification.DECISION_GRADE, observation_id='price-100', conditional=False):
    req_var = 'forward_eps' if family == MarketModelFamily.FORWARD_PE else 'revenue' if family == MarketModelFamily.PS else 'fcf'
    req_role = 'IMPLIED_PRIMARY_CONDITIONAL_ON_ASSUMPTIONS' if conditional else 'IMPLIED_PRIMARY'
    rep = MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE if conditional else MIERepresentation.IMPLIED_POINT
    requirement = MIEEconomicRequirement(req_var, 'CNY/share', 'fixture', 'NTM', '12M', 'reported', req_role, value=Decimal('5'), evidence_ids=(f'mie-evidence-{model_id}',))
    assumptions = ()
    if conditional:
        assumptions = (MIEAssumption('growth', Decimal('0.03'), 'pct', 'fixture', 'NTM', '12M', 'reported', (f'assumption-{model_id}',)),)
    local_cov = CandidateCoverageAssessment(CandidateCoverageState.SUFFICIENT, 'family-local', (model_id,), (f'local-coverage-{model_id}',), 'Local P4 coverage.')
    local_ev = EvidenceSufficiencyAssessment(EvidenceSufficiencyState.SUFFICIENT, 'Local P4 evidence.', (f'local-evidence-{model_id}',))
    ids = (f'mie-evidence-{model_id}', f'local-coverage-{model_id}', f'local-evidence-{model_id}', *(() if not conditional else (f'assumption-{model_id}',)))
    return MarketImpliedExpectation(
        f'mie-{model_id}', model_id, family, IdentifiabilityState.IDENTIFIABLE, StabilityState.STABLE,
        local_cov, rep, (requirement,),
        MIEObservationBasis(observation_id, CUTOFF, CUTOFF, 'CNY', 'UNADJUSTED'),
        assumptions, local_ev, ids, qualification, f'Fixture {model_id} qualification.',
    )

def aggregate(records, candidate_ids, coverage_status=CandidateCoverageState.SUFFICIENT, evidence_status=EvidenceSufficiencyState.SUFFICIENT):
    cv = coverage(*candidate_ids, status=coverage_status)
    ev = evidence(*candidate_ids, status=evidence_status)
    ids = set(cv.evidence_ids) | set(ev.evidence_ids)
    for r in records:
        ids.update(r.evidence_ids)
        if r.expectation is not None: ids.update(r.expectation.evidence_ids)
    return build_multi_model_market_implied_expectation_set(
        set_id='set-1', candidate_coverage=cv, evidence_sufficiency=ev,
        model_evaluations=tuple(records),
        qualification_rationale='P4-E aggregate fixture; no market model is selected.',
        evidence_ids=tuple(sorted(ids)),
    )

def test_unique_decision_grade_model_can_be_decision_grade():
    r = aggregate([MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE))], ('pe-1',))
    assert r.resolution_state == MIESetResolutionState.UNIQUE_MODEL
    assert r.qualification == MIEQualification.DECISION_GRADE
    assert not hasattr(r, 'selected_model_id')

def test_unique_conditional_model_remains_conditional():
    r = aggregate([MIEModelEvaluation.from_expectation(make_mie(model_id='dcf-1', family=MarketModelFamily.DCF, qualification=MIEQualification.CONDITIONAL_ONLY, conditional=True))], ('dcf-1',))
    assert r.resolution_state == MIESetResolutionState.UNIQUE_MODEL
    assert r.qualification == MIEQualification.CONDITIONAL_ONLY
    assert r.materialized_expectations()[0].representation == MIERepresentation.CONDITIONAL_IMPLIED_VARIABLE

def test_multiple_model_expectations_are_ambiguous_and_all_are_preserved():
    r = aggregate([
        MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE)),
        MIEModelEvaluation.from_expectation(make_mie(model_id='ps-1', family=MarketModelFamily.PS)),
    ], ('pe-1','ps-1'))
    assert r.resolution_state == MIESetResolutionState.AMBIGUOUS
    assert r.qualification == MIEQualification.CONDITIONAL_ONLY
    assert {x.model_id for x in r.materialized_expectations()} == {'pe-1','ps-1'}

def test_conditional_and_decision_grade_models_still_form_conditional_set():
    r = aggregate([
        MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE)),
        MIEModelEvaluation.from_expectation(make_mie(model_id='dcf-1', family=MarketModelFamily.DCF, qualification=MIEQualification.CONDITIONAL_ONLY, conditional=True)),
    ], ('pe-1','dcf-1'))
    assert r.resolution_state == MIESetResolutionState.AMBIGUOUS
    assert r.qualification == MIEQualification.CONDITIONAL_ONLY

def test_no_feasible_alternative_does_not_create_false_ambiguity():
    r = aggregate([
        MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE)),
        MIEModelEvaluation.no_feasible_solution(model_id='dcf-1', evidence_ids=('no-feasible-dcf',), rationale='P3 produced an empty feasible set.'),
    ], ('pe-1','dcf-1'))
    assert r.resolution_state == MIESetResolutionState.UNIQUE_MODEL
    assert r.qualification == MIEQualification.DECISION_GRADE

def test_blocked_alternative_prevents_unique_claim():
    r = aggregate([
        MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE)),
        MIEModelEvaluation.blocked(model_id='dcf-1', evidence_ids=('blocked-dcf',), rationale='Current evidence cannot evaluate DCF.'),
    ], ('pe-1','dcf-1'))
    assert r.resolution_state == MIESetResolutionState.INSUFFICIENT_EVIDENCE
    assert r.qualification == MIEQualification.BLOCKED

@pytest.mark.parametrize('cov,ev', [
    (CandidateCoverageState.INSUFFICIENT, EvidenceSufficiencyState.SUFFICIENT),
    (CandidateCoverageState.SUFFICIENT, EvidenceSufficiencyState.INSUFFICIENT),
])
def test_global_coverage_or_evidence_shortfall_blocks(cov, ev):
    r = aggregate([MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE))], ('pe-1',), cov, ev)
    assert r.resolution_state == MIESetResolutionState.INSUFFICIENT_EVIDENCE
    assert r.qualification == MIEQualification.BLOCKED

def test_every_admitted_candidate_requires_one_evaluation_record():
    r = MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE))
    with pytest.raises(ValueError, match='exactly one evaluation'):
        aggregate([r], ('pe-1','ps-1'))

def test_duplicate_model_evaluation_is_rejected():
    r = MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE))
    with pytest.raises(ValueError, match='model evaluation model_ids must be unique'):
        aggregate([r,r], ('pe-1',))

def test_same_snapshot_basis_is_required():
    a = MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE, observation_id='price-100'))
    b = MIEModelEvaluation.from_expectation(make_mie(model_id='ps-1', family=MarketModelFamily.PS, observation_id='price-101'))
    with pytest.raises(ValueError, match='same observation basis'):
        aggregate([a,b], ('pe-1','ps-1'))

def test_evidence_closure_is_enforced():
    r = MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE))
    with pytest.raises(ValueError, match='evidence_ids must cover'):
        build_multi_model_market_implied_expectation_set(set_id='set-1', candidate_coverage=coverage('pe-1'), evidence_sufficiency=evidence('pe-1'), model_evaluations=(r,), qualification_rationale='forged', evidence_ids=('only-one',))

def test_no_feasible_model_is_blocked_not_ambiguous():
    r = aggregate([MIEModelEvaluation.no_feasible_solution(model_id='pe-1', evidence_ids=('none',), rationale='No feasible PE solution.')], ('pe-1',))
    assert r.resolution_state == MIESetResolutionState.NO_FEASIBLE_MODEL
    assert r.qualification == MIEQualification.BLOCKED

def test_blocked_p4_mie_is_consumed_as_blocked_disposition():
    blocked = make_mie(model_id='ddm-1', family=MarketModelFamily.DDM, qualification=MIEQualification.BLOCKED)
    r = MIEModelEvaluation.from_expectation(blocked)
    assert r.state.value == 'BLOCKED'
    assert r.expectation is None

def test_serialization_preserves_model_identity_and_validates_schema():
    r = aggregate([
        MIEModelEvaluation.from_expectation(make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE)),
        MIEModelEvaluation.from_expectation(make_mie(model_id='ps-1', family=MarketModelFamily.PS)),
    ], ('pe-1','ps-1'))
    payload = r.to_dict()
    assert payload['resolution_state'] == 'AMBIGUOUS'
    assert {x['model_id'] for x in payload['model_evaluations']} == {'pe-1','ps-1'}
    assert payload['qualification'] == 'CONDITIONAL_ONLY'
    schema_path = Path('schemas/market_implied_expectation_set_v0.2.schema.json')
    schema = json.loads(schema_path.read_text())
    from jsonschema import Draft202012Validator
    Draft202012Validator(schema).validate(payload)
