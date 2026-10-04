# P4-C DCF / DDM Conditional Market Implied Expectation Acceptance Matrix v0.2

Date: 2026-10-04

## Scope

P4-C is a vertical slice on top of the accepted P3-B DCF/DDM model-specific inverse and the frozen P4-A Market Implied Expectation boundary.

Supported families:

- DCF
- DDM

P4-C does not reopen P2-B domain semantics and does not implement SOTP/rNPV, Expectation Gap, Expected Return, or decision actions.

## Canonical Semantic Rule

For complex models, the current price can be inverted only under an explicit current assumption slice.

~~~
P3-B inverse
    ↓
implied primary variable
    conditioned on
explicit observed current assumptions
    ↓
CONDITIONAL_IMPLIED_VARIABLE
    ↓
CONDITIONAL_ONLY
~~~

This is not:

- a full multidimensional feasible assumption space;
- a statistical statement that the assumptions are the market's true beliefs;
- a decision-grade MIE.

The P4-A contract enforces the qualification boundary.

## Acceptance Matrix

| ID | Case | Required result |
|---|---|---|
| C01 | DCF feasible + sufficient evidence/coverage + stable | One conditional MIE; implied `fcf`; explicit current `growth`, `margin`, `reinvestment`, `terminal_value`, `discount_rate` assumptions |
| C02 | DDM feasible + sufficient evidence/coverage + stable | One conditional MIE; implied `dividend`; explicit current `payout`, `growth`, `discount_rate` assumptions |
| C03 | DCF IDENTIFIABLE + STABLE | Still `CONDITIONAL_ONLY`; representation must be `CONDITIONAL_IMPLIED_VARIABLE` |
| C04 | DDM IDENTIFIABLE + STABLE | Still `CONDITIONAL_ONLY`; representation must be `CONDITIONAL_IMPLIED_VARIABLE` |
| C05 | DCF + DDM both feasible | One conditional slice per feasible candidate; no forced winner |
| C06 | P3 AMBIGUOUS | Conditional slices only; no winner promotion |
| C07 | P3 unstable | `BLOCKED` |
| C08 | P3 insufficient/unidentifiable | `BLOCKED` / no materialization |
| C09 | insufficient candidate coverage | `BLOCKED` |
| C10 | insufficient evidence assessment | `BLOCKED` |
| C11 | non-DCF/DDM candidate | Reject before MIE materialization |
| C12 | wrong P3 primary variable (`dividend` for DCF or `fcf` for DDM) | Reject |
| C13 | missing current conditional assumption | Reject / fail-closed |
| C14 | assumption evidence variable/unit mismatch or unknown provenance | Reject |
| C15 | P3 status/method tampering | Reject |
| C16 | P3 implied primary value altered after identification | P4-C output must preserve the exact P3 value/basis/evidence |
| C17 | caller asks for non-conditional representation | P4-C must not provide it |
| C18 | caller attempts to interpret assumptions as a feasible region | No region field is materialized; assumptions remain point-valued conditioning inputs |
| C19 | generic `market_implied_net_profit` | Forbidden |
| C20 | period/horizon/accounting/price-adjustment semantics omitted or silently inferred | Not permitted; explicit inputs required |

## Output Contract

For each feasible model candidate:

### DCF

Primary requirement:

- `economic_variable = fcf`
- role = `IMPLIED_PRIMARY_CONDITIONAL_ON_ASSUMPTIONS`

Conditioning set:

- `growth`
- `margin`
- `reinvestment`
- `terminal_value`
- `discount_rate`

### DDM

Primary requirement:

- `economic_variable = dividend`
- role = `IMPLIED_PRIMARY_CONDITIONAL_ON_ASSUMPTIONS`

Conditioning set:

- `payout`
- `growth`
- `discount_rate`

All conditioning values are current observed point values with source evidence. They are not claimed to be market-implied values.

## Provenance / PIT

Every emitted MIE must:

- bind to the exact current price observation ID/date;
- use the P3-B candidate/evaluation/solution evidence;
- include current assumption evidence;
- include candidate coverage evidence;
- include evidence-sufficiency evidence;
- remain within the identification input cutoff;
- preserve explicit currency and price-adjustment semantics.

## Red-Team Boundary

The key negative test is:

> Even a single, stable, fully covered DCF/DDM candidate cannot become DECISION_GRADE through P4-C, because the output remains conditional on an observed assumption slice.

P3-B's current DCF/DDM baseline mathematically inverts only the primary variable with its supported price/valuation inputs. The other listed DCF/DDM variables are explicit current model-required conditioning/context inputs, not separately market-implied outputs. A future multidimensional feasible assumption-space implementation would require a separate contract and evidence model. P4-C deliberately does not introduce one implicitly.
