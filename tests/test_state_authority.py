from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_state_index_is_unique_and_canonical():
    index = ROOT / 'docs' / 'PROJECT_STATE_INDEX.md'
    assert index.exists()
    text = index.read_text(encoding='utf-8')
    assert 'State classification: **CANONICAL**' in text
    assert 'only canonical Current State Index' in text
    assert 'A1 Company-side Evidence Closure = PASS / MERGED' in text
    assert 'A1-01 Economic Evidence Bridge = PASS / MERGED' in text
    assert 'A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED' in text
    assert 'A1-03 Quality Gate Integration = PASS / MERGED' in text
    assert 'A1-03 Quality Gate Integration = NEXT' not in text
    assert 'A1-02 Capital Allocation + Trust/Governance Evidence Closure = NEXT' not in text


def test_status_is_summary_not_a_competing_state_authority():
    text = (ROOT / 'STATUS.md').read_text(encoding='utf-8')
    assert 'State classification: **CANONICAL SUMMARY**' in text
    assert 'docs/PROJECT_STATE_INDEX.md' in text
    assert 'Current State Index wins' in text


def test_superseded_state_records_are_explicitly_marked():
    historical = [
        ROOT / 'docs' / 'iios' / 'STATE_RECONCILIATION_2026-10-04.md',
        ROOT / 'docs' / 'iios' / 'IIOS_CURRENT_STATE_INDEX.md',
        ROOT / 'docs' / 'iios' / 'IIOS_CONSOLIDATED_POST_REDTEAM_DEVELOPMENT_PLAN_2026-10-04.md',
        ROOT / 'docs' / 'iios' / 'B1_RETURN_SEMANTICS_ADR_v0.3.md',
    ]
    for path in historical:
        text = path.read_text(encoding='utf-8')
        assert 'HISTORICAL' in text or 'SUPERSEDED' in text, path


def test_no_legacy_core04_merge_candidate_claims_remain():
    forbidden = (
        'PR #70 is the current CORE-04 merge candidate',
        'PR #70 remains **OPEN / NOT MERGED**',
        'Production investment decision kernel: NOT YET',
        'current merge candidate',
    )
    texts = []
    for path in [ROOT / 'STATUS.md', ROOT / 'docs' / 'PROJECT_STATE_INDEX.md']:
        texts.append(path.read_text(encoding='utf-8'))
    joined = '\n'.join(texts)
    for phrase in forbidden:
        assert phrase not in joined


def test_new_development_gate_names_only_canonical_state_inputs():
    policy = (ROOT / 'docs' / 'iios' / 'A0_STATE_AUTHORITY_POLICY_v0.1.md').read_text(encoding='utf-8')
    assert 'canonical `main`' in policy
    assert 'docs/PROJECT_STATE_INDEX.md' in policy
    assert 'historical branch' in policy
    assert 'stale PR head' in policy