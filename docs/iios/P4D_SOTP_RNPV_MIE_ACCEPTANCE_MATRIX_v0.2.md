# P4-D SOTP / rNPV Market Implied Expectation Acceptance Matrix v0.2

Date: 2026-10-04

## Scope

P4-D consumes the accepted P3-B complex-model identification outputs through the frozen P4-A Market Implied Expectation boundary.

Supported families:
- SOTP
- rNPV

It does not redesign P2-B, recompute P3-B inverse models, or implement P4-E/P4-F/P5.

## Canonical Semantic Rule

### SOTP

~~~
current price
  -
current observed segment value construction
  ↓
implied residual value
  ↓
CONDITIONAL_IMPLIED_VARIABLE
  ↓
CONDITIONAL_ONLY
~~~

The segment values are explicit conditioning inputs. They are not asserted to be market-implied segment beliefs.

### rNPV

~~~
current market residual value
        +
P3-B implied total pipeline requirement
        ↓
preserve observed pipeline composition
        ↓
pipeline-specific implied requirements
        ↓
CONDITIONAL_IMPLIED_VARIABLE
        ↓
CONDITIONAL_ONLY
~~~

Current pipeline probabilities and timings remain explicit conditioning variables.
They are not inverted into a market probability, and the pipeline portfolio is not collapsed into a single undifferentiated probability-weighted value.

## Acceptance Matrix

| ID | Case | Required result |
|---|---|---|
| D01 | SOTP feasible + sufficient evidence/coverage + stable | One conditional MIE; implied residual_value; current segment values explicit in conditioning set |
| D02 | rNPV feasible + sufficient evidence/coverage + stable | One conditional MIE; one pipeline_value requirement per pipeline; composition preserved |
| D03 | SOTP identifiable + stable | CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY |
| D04 | rNPV identifiable + stable | CONDITIONAL_IMPLIED_VARIABLE / CONDITIONAL_ONLY |
| D05 | multiple SOTP/rNPV feasible candidates | one conditional slice per candidate; no forced winner |
| D06 | AMBIGUOUS | conditional only; selected model remains unset |
| D07 | UNSTABLE | BLOCKED |
| D08 | insufficient / unidentifiable | BLOCKED / no positive materialization |
| D09 | insufficient candidate coverage | BLOCKED |
| D10 | insufficient evidence | BLOCKED |
| D11 | non-SOTP/rNPV candidate | reject |
| D12 | wrong P3 primary variable | reject |
| D13 | missing current SOTP segment | fail-closed |
| D14 | missing rNPV pipeline/probability/timing | fail-closed |
| D15 | pipeline IDs misaligned | reject |
| D16 | assumption/observation evidence unknown or variable/unit mismatch | reject |
| D17 | P3 status/method tampering | reject |
| D18 | P3 solution altered | exact P3 primary total/value must be consumed without inverse recomputation |
| D19 | rNPV probability presented as market-implied requirement | forbidden |
| D20 | rNPV timing presented as market-implied requirement | forbidden |
| D21 | generic market_implied_net_profit | forbidden |
| D22 | SOTP segment values promoted to market truth | forbidden |
| D23 | rNPV pipeline portfolio collapsed into one pseudo-probability | forbidden |
| D24 | period/horizon/accounting/price-adjustment semantics inferred silently | not permitted; explicit inputs required |

## Output Contract

### SOTP

One primary requirement:
- economic_variable = residual_value
- role = IMPLIED_RESIDUAL_CONDITIONAL_ON_SEGMENTS
- conditioning set: one segment_value assumption per explicit segment:<id>.

### rNPV

One primary requirement per pipeline:
- economic_variable = pipeline_value
- basis contains pipeline:<id>
- role = IMPLIED_PIPELINE_CONDITIONAL_ON_OBSERVED_COMPOSITION

Conditioning set includes:
- observed pipeline_value as composition anchor;
- observed probability per pipeline;
- observed timing per pipeline;
- global discount_rate;
- global base_value.

The per-pipeline implied requirements are a deterministic pro-rata decomposition of the accepted P3-B total implied pipeline requirement using the observed current pipeline-value composition. This is a decomposition rule, not a second inverse model.

## Provenance / PIT

Each output must:
- bind to the exact current price observation ID/date;
- preserve P3 solution evidence;
- bind every conditioning observation to its evidence;
- carry candidate coverage/evidence sufficiency evidence;
- remain within the identification cutoff;
- preserve explicit currency and adjustment semantics.

## Red-Team Boundary

The key negative tests are:
1. SOTP: observed segment values must not be relabeled as market-implied segment values.
2. rNPV: observed probability must never become economic_requirements; it is a conditioning input only.
3. rNPV: multiple pipeline IDs must remain separately represented.
4. Even with IDENTIFIABLE + STABLE + SUFFICIENT, SOTP/rNPV output remains conditional and cannot become decision-grade through P4-D.

P4-D therefore preserves:

conditional inverse ≠ full feasible assumption space ≠ market truth