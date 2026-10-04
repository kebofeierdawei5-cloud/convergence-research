# P4-C Final Acceptance — DCF / DDM Conditional Market Implied Expectation v0.2

Date: 2026-10-04

## Acceptance Status

**P4-C = FINAL PASS / MERGED**

## Evidence Chain

- PR #12: MERGED
- P4-C merge commit: to be recorded after merge
- pre-merge HEAD: `303f16005b0e761fbdd96fcd9d9461642be3fa9a`
- CI: to be recorded after final red-team CI
- Final regression count: to be recorded after final CI
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

- DCF -> implied `fcf` conditional on the explicit current assumption slice;
- DDM -> implied `dividend` conditional on the explicit current assumption slice.

DCF conditioning variables:

- `growth`
- `margin`
- `reinvestment`
- `terminal_value`
- `discount_rate`

DDM conditioning variables:

- `payout`
- `growth`
- `discount_rate`

The P3-B inverse is not recomputed.

## Critical Red-Line

P4-C does not claim:

- a full multidimensional feasible assumption space;
- that the observed conditioning values equal market beliefs;
- that a conditional inverse is market truth;
- decision-grade MIE qualification.

All outputs use:

~~~
representation = CONDITIONAL_IMPLIED_VARIABLE
qualification  = CONDITIONAL_ONLY
~~~

even when P3 reports `IDENTIFIABLE + STABLE`.

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
- any attempt to promote the conditional output to decision-grade.

## Explicit Non-Goals

P4-C does not implement:

- SOTP/rNPV MIE;
- multi-model expectation-set logic beyond emitting one conditional slice per feasible candidate;
- Expectation Gap;
- Expected Return;
- decision actions;
- auto-execution.

## Next Gate

**P4-D — SOTP / rNPV expectation extraction**

Then:

~~~
P4-E multi-model expectation set
        ↓
P4-F PIT/replay/fail-closed integration
        ↓
P5 Expectation Gap → Expected Return >15%
~~~
