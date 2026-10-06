# C4 Acceptance — Expectation Gap Production Integration

Date: 2026-10-06
Status: PASS / MERGED / CANONICAL
Canonical main: 07d45c18df8df9100d4866dd5f92fa95ccdb7186

## Scope

C4 promotes the existing Market Implied Expectation substrate into a first-class production Expectation Gap evaluation and reconnects it to the canonical Investment Core v0.3 Decision payload.

Implementation PR: #105
Implementation merge: 07d45c18df8df9100d4866dd5f92fa95ccdb7186

## Exact-head CI evidence

C4 dedicated workflow:

- Workflow: IIOS C4 — Expectation Gap Production Integration
- Run: #7
- Exact head: aacf1c0cc715697bfac2aa0bae5e2f0a4c899ad2
- Result: SUCCESS

Verified steps:

- compileall: PASS
- C4 + semantic Expectation Gap + Investment Core v0.3 regression tests: 75 passed
- executable C4 acceptance harness: PASS
- acceptance harness checks: 7 / 7
- git diff --check: PASS

An earlier C4 workflow run #4 also passed 75 tests and 7 / 7 acceptance checks before the final schema-diff cleanup; run #7 is the exact-head acceptance evidence.

## Acceptance conclusions

### 1. Comparable expectations produce a scalar gap

A uniquely resolved, decision-grade market expectation that matches the independent forecast on:

- economic variable;
- unit;
- basis;
- horizon;
- comparison direction

produces a deterministic scalar Expectation Gap evaluation.

### 2. Incompatible expectations do not produce a scalar gap

Variable, unit, basis, horizon, direction, or representation mismatch is fail-closed. Incompatible semantics produce no market-required scalar and no scalar gap.

### 3. Ambiguous market interpretation does not become market truth

When more than one materialized market interpretation remains, C4 returns AMBIGUOUS and does not force a scalar market expectation.

### 4. No-feasible-model state is explicit

When the MIE candidate set has no feasible market model, C4 returns NO_FEASIBLE_SOLUTION and does not fabricate a market-required scalar.

### 5. Existing decision semantics remain authoritative

C4 does not add a new return hurdle and does not change Decision precedence.

MIE remains:

MIE_POLICY = OPTIONAL_EXPLANATORY

A valid negative or non-positive gap remains an explicit advisory calculation and is not converted into a hidden BUY/ADD veto.

### 6. Canonical persistence is upgraded

The detailed C4 Expectation Gap evaluation is bound into the canonical v0.3 Decision output and therefore remains available to the existing Decision Revision / Publication / Report lifecycle.

The evaluation is content-addressed and replayable.

## Explicitly unchanged

C4 does not add:

- C5 Positioning / Sizing;
- C6 Human Execution Receipt;
- scheduler / alerts;
- automatic execution / order placement;
- portfolio optimization;
- new P3/P4/MIE model families;
- Forecast Research productionization.

## Known independent regression track

The broader Investment Core CI continues to report the separately tracked CORE-04 assertion regression. That failure is not used to invalidate C4 because the dedicated C4 acceptance suite isolates the C4 boundary and all C4 acceptance checks pass.

## Next canonical boundary

C5 — Positioning / Sizing.

C4 is therefore closed as a canonical productization boundary.
