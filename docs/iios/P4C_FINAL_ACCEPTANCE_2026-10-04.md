# P4-C Final Acceptance — DCF / DDM Conditional Market Implied Expectation v0.2

Date: 2026-10-04

## Acceptance Status

**P4-C = FINAL PASS / MERGED**

## Evidence Chain

- PR #12: MERGED
- P4-C pre-merge HEAD: `620977682155f5f633f1dcd81ddbc6d71a2005e1`
- P4-C merge commit: `b6bfb8df10a8ffee5f01154fbe4b47201f6048fe`
- PR Investment Core CI #143 / run `37189169223`: **SUCCESS**
- PR FM00 CI #115 / run `37189169218`: **SUCCESS**
- Post-merge main Investment Core CI #144 / run `37189193858`: **SUCCESS**
- Post-merge main FM00 CI #116 / run `37189193862`: **SUCCESS**
- Final regression: **128 passed**
- Acceptance matrix: `docs/iios/P4C_DCF_DDM_CONDITIONAL_MIE_ACCEPTANCE_MATRIX_v0.2.md`

## Scope

P4-C supports:

- DCF
- DDM

It directly consumes:

- P3-B model-specific inverse result;
- P4-A typed Market Implied Expectation boundary.

It does not redesign the P2-B market-model domain.

## Semantic Result

P4-C materializes a **conditional MIE slice**:

- DCF → implied `fcf` conditional on the explicit current model-assumption slice;
- DDM → implied `dividend` conditional on the explicit current model-assumption slice.

DCF conditioning/context variables:

- `growth`
- `margin`
- `reinvestment`
- `terminal_value`
- `discount_rate`

DDM conditioning/context variables:

- `payout`
- `growth`
- `discount_rate`

The P3-B inverse is not recomputed.

### Important Interpretation Boundary

P3-B's current DCF/DDM baseline mathematically inverts the primary variable using the model-supported price/valuation inputs; the other listed variables are explicit model-required current context and validation inputs. They are **not separately asserted by P4-C to be market-implied variables**.

Accordingly, P4-C is a conditional requirement slice, not a simultaneous inverse of every DCF/DDM assumption.

## Critical Red-Line

P4-C does not claim:

- a full multidimensional feasible assumption space;
- that the observed conditioning values equal market beliefs;
- that a conditional inverse is market truth;
- decision-grade MIE qualification.

All outputs use:

```
representation = CONDITIONAL_IMPLIED_VARIABLE
qualification  = CONDITIONAL_ONLY
```

for positively materialized conditional slices, even when P3 reports `IDENTIFIABLE + STABLE`.

Blocked upstream states remain fail-closed.

## Fail-Closed / Red-Team Behavior

The implementation rejects or blocks:

- unstable P3 interpretation;
- insufficient / unidentifiable P3 interpretation;
- insufficient candidate coverage;
- insufficient evidence;
- non-DCF/DDM contamination;
- wrong P3 primary variable;
- missing current conditional assumptions;
- assumption evidence provenance / variable / unit mismatch;
- P3 status/method tampering;
- generic implied net profit;
- any attempt to promote the conditional output to decision-grade;
- cross-snapshot / cross-price test-fixture contamination.

The final red-team regression passed **128 tests**.

## Explicit Non-Goals

P4-C does not implement:

- SOTP/rNPV MIE;
- full multidimensional DCF/DDM feasible assumption-space inference;
- multi-model expectation-set logic beyond emitting one conditional slice per feasible candidate;
- Expectation Gap;
- Expected Return;
- decision actions;
- auto-execution.

## Next Gate

**P4-D — SOTP / rNPV expectation extraction**

Then:

```
P4-E multi-model expectation set
        ↓
P4-F PIT/replay/fail-closed integration
        ↓
P5 Expectation Gap → Expected Return >15%
```
