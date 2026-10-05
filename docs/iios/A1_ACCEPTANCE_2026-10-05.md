# A1 Acceptance — Company-side Evidence Closure

Date: 2026-10-05
State classification: CANONICAL

## Scope

A1 closes the company-side evidence chain required before adding further investment-model capability:

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
    Quality Gate

A1 is complete as an engineering/evidence-closure milestone. It does not imply that the current security passes Quality or should be purchased.

## Canonical delivery

A1-01 — Economic Evidence Bridge:
- PR #75, merged 1b72870298cee2e976054e4f65627e24ad3e1c0e
- deterministic CAPEX → D&A → FCF;
- Earnings → OCF → FCF;
- working-capital cash bridge;
- Incremental ROIC proxy;
- admitted-evidence binding, PIT checks, fail-closed validation, schema and hash audit.

A1-02 — Capital Allocation + Trust/Governance Evidence:
- PR #77, merged ffa3e1d4908dbf990185af4b9e47e1ef553b88f8
- shareholder-return / repurchase evidence;
- strategic capital-commitment evidence;
- related-party guarantee and procurement evidence;
- governance safeguards;
- explicit separation of exposure facts from Trust conclusions.

A1-03 — Quality Gate Integration:
- PR #80, merged 6932d68263e922ab3bdc9d81a6ae4cda94bf78ce
- integrated A1-01/A1-02 into existing Quality and Trust semantics;
- existing build_quality_gate() remains authoritative;
- evidence may resolve an evidence-missing UNKNOWN or cap a stronger unsupported state;
- no new Quality score or model;
- no Decision Kernel semantic change;
- decision_effect = NO_DIRECT_GATE_EFFECT.

## Verification

A1-01:
- dedicated CI #8 PASS;
- Investment Core #481 PASS;
- CORE-00 #217 PASS;
- CORE-02 #41 PASS;
- CORE-03 Real 300750 #96 PASS;
- B2 PIT #51 PASS.

A1-02:
- dedicated CI #10 PASS;
- Investment Core #492 PASS;
- CORE-00 #230 PASS;
- CORE-02 #52 PASS;
- CORE-03 Real 300750 #107 PASS;
- B2 PIT #61 PASS.

A1-03:
- dedicated CI #10 PASS;
- CORE-00 #245 PASS;
- Investment Core #503 PASS;
- latest A1-03 test suite: PASS.

## 300750 canonical effect

For RC-CN-A-300750-20261004:
- incremental_return_on_capital: evidence closes the former UNKNOWN to CONDITIONAL because the A1-01 bridge is itself conditional;
- cash_flow_conversion: CONDITIONAL;
- reinvestment_runway: CONDITIONAL;
- balance_sheet_resilience: unchanged PASS;
- Quality Gate: CONDITIONAL;
- capital_admission_pass: FALSE;
- Trust: CONDITIONAL;
- Decision effect: no new capital / REVIEW_REQUIRED remains.

Therefore A1 does not manufacture a BUY/ADD signal. It improves evidence completeness while preserving the same decision boundary.

## A1 boundary

A1 does not include:
- new P3/P4/MIE models;
- new valuation models;
- forecast research;
- portfolio-constraint changes;
- automatic trading;
- second-company rollout.

These remain separate future work.

## Final state

    CORE-04 Production Decision Kernel = PASS / MERGED
            ↓
    CORE-04 × 300750 Final Decision Chain = PASS / REVIEW_REQUIRED / NO NEW CAPITAL
            ↓
    A0 Governance / State Cleanup = PASS / MERGED
            ↓
    A1-01 Economic Evidence Bridge = PASS / MERGED
            ↓
    A1-02 Capital Allocation + Trust/Governance = PASS / MERGED
            ↓
    A1-03 Quality Gate Integration = PASS / MERGED
            ↓
    A1 Company-side Evidence Closure = PASS / MERGED

Next work should be an acceptance/red-team review or another explicitly scoped productization batch. It should not start by adding P3/P4/MIE models.
