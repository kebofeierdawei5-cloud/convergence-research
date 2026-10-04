from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from iios_mvp.market_implied_expectation import (
    CandidateCoverageAssessment, CandidateCoverageState,
    EvidenceSufficiencyAssessment, EvidenceSufficiencyState,
    MIEEconomicRequirement, MIEObservationBasis, MIEQualification,
    MIERepresentation, MarketImpliedExpectation,
)
from iios_mvp.market_model_domain import IdentifiabilityState, MarketModelFamily, StabilityState
from iios_mvp.multi_model_market_implied_expectation_set import (
    MIEModelEvaluation, MIEModelEvaluationState, build_multi_model_market_implied_expectation_set,
)
from iios_mvp.p4f_mie_snapshot import (
    P4FProvenanceRecord, build_p4f_snapshot, read_p4f_snapshot,
    replay_p4f_snapshot, validate_p4f_snapshot, write_p4f_snapshot,
)

CUTOFF = date(2026, 10, 4)
CREATED = datetime(2026, 10, 4, 17, 10, tzinfo=timezone.utc)

def make_mie(model_id='pe-1', family=MarketModelFamily.FORWARD_PE, qualification=MIEQualification.DECISION_GRADE, observation_id='price-1'):
    variable = 'forward_eps' if family == MarketModelFamily.FORWARD_PE else 'revenue'
    req = MIEEconomicRequirement(variable, 'CNY/share', 'fixture', 'NTM', '12M', 'reported', 'IMPLIED_PRIMARY', value=Decimal('5'), evidence_ids=(f'req-{model_id}',))
    cov = CandidateCoverageAssessment(CandidateCoverageState.SUFFICIENT, 'fixture-candidate-set', (model_id,), (f'cov-{model_id}',), 'Fixture candidate coverage.')
    ev = EvidenceSufficiencyAssessment(EvidenceSufficiencyState.SUFFICIENT, 'Fixture evidence sufficiency.', (f'suff-{model_id}',))
    return MarketImpliedExpectation(
        expectation_id=f'mie-{model_id}', model_id=model_id, market_model=family,
        identifiability=IdentifiabilityState.IDENTIFIABLE, stability=StabilityState.STABLE,
        candidate_coverage=cov, representation=MIERepresentation.IMPLIED_POINT,
        economic_requirements=(req,),
        observation_basis=MIEObservationBasis(observation_id, CUTOFF, CUTOFF, 'CNY', 'UNADJUSTED'),
        assumption_set=(), evidence_sufficiency=ev,
        evidence_ids=(f'req-{model_id}', f'cov-{model_id}', f'suff-{model_id}'),
        qualification=qualification, qualification_rationale='Fixture qualification.',
    )

def make_set(*model_specs):
    ids = tuple(x[0] for x in model_specs)
    cov = CandidateCoverageAssessment(CandidateCoverageState.SUFFICIENT, 'global-universe', ids, tuple(f'global-cov-{x}' for x in ids), 'Global candidate coverage.')
    ev = EvidenceSufficiencyAssessment(EvidenceSufficiencyState.SUFFICIENT, 'Global evidence sufficiency.', tuple(f'global-ev-{x}' for x in ids))
    records = []
    evidence_ids = set(cov.evidence_ids) | set(ev.evidence_ids)
    for model_id, family, qualification in model_specs:
        mie = make_mie(model_id=model_id, family=family, qualification=qualification)
        records.append(MIEModelEvaluation.from_expectation(mie))
        evidence_ids.update(mie.evidence_ids)
    return build_multi_model_market_implied_expectation_set(set_id='set-1', candidate_coverage=cov, evidence_sufficiency=ev, model_evaluations=records, qualification_rationale='Fixture aggregate.', evidence_ids=tuple(sorted(evidence_ids)))

def make_provenance(mie_set, *, known_at=None, observation_date=CUTOFF, include_price=True):
    known_at = known_at or datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc)
    ids = set(mie_set.evidence_ids)
    for item in mie_set.materialized_expectations():
        ids.add(item.observation_basis.price_observation_id)
    records=[]
    for eid in sorted(ids):
        variable = 'market_price' if eid.startswith('price-') else 'fixture_variable'
        records.append(P4FProvenanceRecord(eid, variable, 'CNY', 'fixture', observation_date, known_at, 'fixture-source', f'fixture://{eid}', 'a'*64, CREATED))
    return records

def test_build_snapshot_closes_pit_provenance_and_hashes():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    snap = build_p4f_snapshot(case_id='CN-A-300750', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s))
    validate_p4f_snapshot(snap)
    assert snap['snapshot_schema'] == 'IIOS-MIE-SNAPSHOT-0.2'
    assert len(snap['snapshot_hash']) == 64
    assert len(snap['mie_set_hash']) == 64
    assert len(snap['provenance_hash']) == 64

def test_snapshot_is_immutable_on_disk(tmp_path):
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    snap = build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s))
    p = write_p4f_snapshot(tmp_path, snap)
    assert read_p4f_snapshot(p)['snapshot_hash'] == snap['snapshot_hash']
    with pytest.raises(ValueError, match='overwrite|collision'):
        p.write_text(json.dumps({**snap, 'case_id':'tampered'})+'\n')
        write_p4f_snapshot(tmp_path, {**snap, 'snapshot_hash': snap['snapshot_hash']})

def test_replay_passes_on_unchanged_snapshot():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    snap = build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s))
    result = replay_p4f_snapshot(snap)
    assert result['replay_status'] == 'PASS'
    assert result['integrity_status'] == 'PASS'
    assert result['pit_status'] == 'PASS'
    assert result['provenance_status'] == 'PASS'
    assert result['semantic_status'] == 'PASS'

def test_replay_fails_on_hash_tampering():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    snap = build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s))
    tampered = json.loads(json.dumps(snap))
    tampered['mie_set']['qualification'] = 'CONDITIONAL_ONLY'
    result = replay_p4f_snapshot(tampered)
    assert result['replay_status'] == 'FAIL'

def test_future_known_at_is_pit_blocked():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    future = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='known_at is after cutoff'):
        build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s, known_at=future))

def test_future_observation_date_is_pit_blocked():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    future = date(2026, 10, 5)
    with pytest.raises(ValueError, match='observation_date is after cutoff'):
        build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s, observation_date=future))

def test_missing_evidence_provenance_is_fail_closed():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    records = make_provenance(s)[:-1]
    with pytest.raises(ValueError, match='provenance missing evidence IDs'):
        build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=records)

def test_price_observation_requires_market_price_provenance_and_exact_date():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    records = make_provenance(s)
    bad=[]
    for r in records:
        bad.append(P4FProvenanceRecord(r.evidence_id, 'not_price' if r.evidence_id == 'price-1' else r.variable, r.unit, r.basis, r.observation_date, r.known_at, r.source, r.source_location, r.content_sha256, r.captured_at))
    with pytest.raises(ValueError, match='variable=market_price'):
        build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=bad)

def test_capture_after_cutoff_is_allowed_because_pit_uses_known_at():
    s = make_set(('pe-1', MarketModelFamily.FORWARD_PE, MIEQualification.DECISION_GRADE))
    captured_after = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    records=[]
    for r in make_provenance(s):
        records.append(P4FProvenanceRecord(r.evidence_id,r.variable,r.unit,r.basis,r.observation_date,r.known_at,r.source,r.source_location,r.content_sha256,captured_after))
    snap = build_p4f_snapshot(case_id='case-1', cutoff_date=CUTOFF, created_at=captured_after, mie_set=s, provenance_records=records)
    assert replay_p4f_snapshot(snap)['replay_status'] == 'PASS'

def test_cross_model_snapshot_basis_mismatch_is_rejected():
    a=make_mie(model_id='pe-1',family=MarketModelFamily.FORWARD_PE,observation_id='price-1')
    b=make_mie(model_id='ps-1',family=MarketModelFamily.PS,observation_id='price-2')
    cov=CandidateCoverageAssessment(CandidateCoverageState.SUFFICIENT,'global',('pe-1','ps-1'),('gc1','gc2'),'global')
    ev=EvidenceSufficiencyAssessment(EvidenceSufficiencyState.SUFFICIENT,'sufficient',('ge1','ge2'))
    records=(MIEModelEvaluation.from_expectation(a),MIEModelEvaluation.from_expectation(b))
    ids=set(cov.evidence_ids)|set(ev.evidence_ids)|set(a.evidence_ids)|set(b.evidence_ids)|{'price-1','price-2'}
    s=build_multi_model_market_implied_expectation_set(set_id='s',candidate_coverage=cov,evidence_sufficiency=ev,model_evaluations=records,qualification_rationale='ambiguous',evidence_ids=tuple(sorted(ids)))
    with pytest.raises(ValueError, match='observation basis'):
        build_p4f_snapshot(case_id='case', cutoff_date=CUTOFF, created_at=CREATED, mie_set=s, provenance_records=make_provenance(s))

def test_schema_validates_snapshot():
    s=make_set(('pe-1',MarketModelFamily.FORWARD_PE,MIEQualification.DECISION_GRADE))
    snap=build_p4f_snapshot(case_id='case-1',cutoff_date=CUTOFF,created_at=CREATED,mie_set=s,provenance_records=make_provenance(s))
    schema=json.loads(Path('schemas/p4f_mie_snapshot_v0.2.schema.json').read_text())
    Draft202012Validator(schema).validate(snap)
