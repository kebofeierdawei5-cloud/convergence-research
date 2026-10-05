# A1 Acceptance — Company-side Evidence Closure

Date: 2026-10-05
State classification: **CANONICAL**

## Scope

A1 closes the company-side evidence loop for the canonical single-company case RC-CN-A-300750-20261004:

    Incremental ROIC
            ↓
    CAPEX → D&A → FCF
            ↓
    Earnings → OCF → FCF
            ↓
    Working Capital
            ↓
    Capital Allocation
            ↓
    Trust / Governance
            ↓
    Existing Quality Gate

A1 is an evidence-closure milestone, not a new investment model.

## Accepted sub-batches

### A1-01 Economic Evidence Bridge

PR #75, merge commit 1b72870298cee2e976054e4f65627e24ad3e1c0e.

Accepted scope:
- CAPEX → D&A → FCF;
- Earnings → OCF → FCF;
- Working Capital;
- Incremental ROIC proxy.

The real-case Incremental ROIC remains CONDITIONAL because the invested-capital perimeter and effective-tax treatment are proxy limitations.

### A1-02 Capital Allocation + Trust/Governance Evidence

PR #77, merge commit ffa3e1d4908dbf990185af4b9e47e1ef553b88f8.

Accepted evidence:
- E014_A1 — 2025 annual capital allocation;
- E015_A1 — 2026 H1 capital allocation;
- E016_A1 — related-party guarantee;
- E017_A1 — related-party procurement.

The bridge remains CONDITIONAL where the evidence does not establish project economics, arm's-length fairness, full governance history, or aggregate Trust PASS.

### A1-03 Quality Gate Integration

PR #80, merge commit 6932d68263e922ab3bdc9d81a6ae4cda94bf78ce.

Accepted semantics:
- existing build_quality_gate() remains the sole Quality Gate authority;
- A1 evidence may resolve an evidence-missing UNKNOWN;
- otherwise evidence applies a fail-closed status cap;
- known PASS / CONDITIONAL analytical states are never upgraded by A1;
- BLOCKED evidence blocks the affected dimension;
- decision_effect = NO_DIRECT_GATE_EFFECT.

## Real 300750 acceptance result

After A1 integration:

- incremental_return_on_capital = CONDITIONAL;
- cash_flow_conversion = CONDITIONAL;
- reinvestment_runway = CONDITIONAL;
- balance_sheet_resilience = PASS;
- governance_integrity = CONDITIONAL;
- shareholder_treatment = CONDITIONAL;
- Quality Gate = CONDITIONAL;
- capital_admission_pass = false;
- aggregate Trust = CONDITIONAL;
- Decision effect = NO_DIRECT_GATE_EFFECT.

This is the intended fail-closed outcome. A1 closes missing evidence; it does not manufacture a Quality PASS or authorize new capital.

## CI / regression evidence

A1-03 dedicated workflow run #9 completed successfully.

Investment Core CI run #502 on the A1-03 pull-request merge ref had:
- 408 tests passed;
- one failure: test_current_state_index_is_unique_and_canonical;
- the failure expected stale pre-A1-02 / pre-A1-03 state markers;
- no A1 economic bridge, capital/trust bridge, A1-03 integration, or Decision Kernel test failed.

The failure is corrected by this final A1 state-sync change in tests/test_state_authority.py and the canonical state documents.

## A1 acceptance decision

**A1 = PASS / MERGED**

This means the current company-side evidence bridge is closed and integrated into the existing Quality / Trust semantics.

It does not imply:
- Quality Gate = PASS;
- Trust = PASS;
- BUY / ADD authorization;
- new valuation or forecast capability;
- P3 / P4 / MIE changes.

## Next boundary

A1 is complete. The next development batch must start from canonical main + docs/PROJECT_STATE_INDEX.md and be separately scoped.

No P3/P4/MIE model work is part of this A1 closure.
