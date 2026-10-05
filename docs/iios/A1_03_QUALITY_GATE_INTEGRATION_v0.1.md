# A1-03 — Quality Gate Integration v0.1

Date: 2026-10-05
Status: IMPLEMENTATION TARGET

## Objective

Integrate the completed A1 company-side evidence bridges into the existing Trust / Quality / Quality Gate semantics.

This is a deterministic evidence constraint layer. It does not introduce a new score, model, valuation method, P3/P4 capability, or MIE behavior.

## Core rule

A1-03 uses a one-way status cap:

    Integrated Status = max(Existing Analytical Status, Closed Evidence Status)

Severity ordering:

    PASS < CONDITIONAL < UNKNOWN < BLOCKED

Therefore:
- evidence cannot upgrade a weaker existing analytical status;
- evidence can downgrade an unjustifiably strong status;
- BLOCKED evidence blocks the affected dimension;
- UNKNOWN remains UNKNOWN when the underlying analytical state is weaker than the evidence.

This is deliberate fail-closed behavior.

## Quality mapping

A1-01 → Quality:
- incremental_return_on_capital ← Incremental ROIC bridge status
- cash_flow_conversion ← economic bridge interpretation status
- reinvestment_runway ← A1-02 capital-allocation status

A1-03 does not infer new statuses for competitive_advantage, earnings_quality, or balance_sheet_resilience. Those remain governed by existing evidence-linked assessments.

## Trust mapping

A1-02 → Trust:
- governance_integrity ← related-party governance revalidation status;
- shareholder_treatment ← shareholder-treatment evidence status.

Aggregate Trust uses the existing fail-closed precedence and is additionally capped by bridge-level Trust revalidation status.

A related-party exposure is not translated into an automatic Trust FAIL. The evidence layer captures the exposure and disclosed governance safeguards; economic fairness, arm's-length terms, recurrence and shareholder impact remain analytical questions.

## Quality Gate mapping

The existing build_quality_gate() remains the sole production Quality Gate policy.

A1-03 supplies it with the integrated Quality dimensions.

Existing policy remains:

    ALL_CORE_DIMENSIONS_PASS_FOR_NEW_CAPITAL

Thus any remaining CONDITIONAL / UNKNOWN / BLOCKED dimension means:

    capital_admission_pass = false

No new capital is authorized by A1-03.

## Real 300750 regression

The current 300750 CORE-02 quality assessment has:
- incremental_return_on_capital = UNKNOWN;
- earnings_quality = CONDITIONAL;
- cash_flow_conversion = CONDITIONAL;
- balance_sheet_resilience = PASS;
- reinvestment_runway = CONDITIONAL.

After A1 evidence integration:
- incremental_return_on_capital becomes CONDITIONAL because the A1-01 bridge is itself CONDITIONAL, not PASS;
- cash_flow_conversion remains CONDITIONAL;
- reinvestment_runway remains CONDITIONAL because capital-allocation evidence is CONDITIONAL;
- balance_sheet_resilience remains PASS.

The resulting Quality Gate remains CONDITIONAL and capital_admission_pass=false.

Trust remains CONDITIONAL because the existing trust assessment is already conditional and the A1-02 governance revalidation is also conditional.

This is the intended effect: A1-03 closes evidence gaps without manufacturing a stronger investment-quality state.

## Decision boundary

The output explicitly states:

    decision_effect = NO_DIRECT_GATE_EFFECT

The existing CORE-04 Decision Kernel remains unchanged. When its existing upstream Quality Gate receives CONDITIONAL, the pre-existing decision semantics continue to deny new capital and route unresolved cases to REVIEW_REQUIRED.

## Acceptance

A1-03 is accepted only when:
1. the integration module is deterministic;
2. the existing Quality Gate implementation remains the authority;
3. evidence can only cap, never upgrade, analytical status;
4. the real 300750 CORE-02 input passes the integration regression;
5. Quality Gate remains CONDITIONAL for the real 300750 evidence state;
6. Trust remains CONDITIONAL;
7. case/cutoff bridge mismatches fail closed;
8. tampering is detected by integration hash;
9. schema validation passes;
10. Investment Core CI remains PASS;
11. no Decision Kernel semantic change occurs;
12. no P3/P4/MIE model is added or modified.

## Out of scope

- new valuation model;
- MIE;
- forecast research;
- new Quality dimensions;
- Quality scoring;
- automatic recommendation or trading;
- portfolio semantics;
- Decision Kernel precedence changes.

## Next A1 boundary

After A1-03, the company-side evidence loop is materially closed for the current single-company case, but the broader A1 acceptance still requires review of whether the integrated Quality / Trust states are sufficient for the canonical company-quality contract. That review should be an acceptance/red-team step, not another model-building batch.
