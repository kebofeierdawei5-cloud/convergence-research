# P4-E Multi-model Market Implied Expectation Set Acceptance Matrix v0.2

## Scope
P4-E is the aggregation and qualification boundary over already accepted P4-A through P4-D MarketImpliedExpectation outputs.

P4-E does not recompute inverse valuation, alter model-native variables, compare unlike economic variables, rank/choose models, average model requirements, or calculate Expectation Gap / Expected Return.

## Typed Boundary
The global candidate universe is supplied through the existing CandidateCoverageAssessment. Exactly one MIEModelEvaluation record is required for every admitted candidate model.

Each model disposition is one of:
- MATERIALIZED: a non-blocked P4 MIE exists;
- NO_FEASIBLE_SOLUTION: the candidate was evaluated and its feasible solution set is empty;
- BLOCKED: the candidate cannot be resolved under the current evidence/state.

NO_FEASIBLE_SOLUTION is deliberately distinct from BLOCKED. This is what makes a single remaining feasible model distinguishable from an incompletely evaluated universe.

## Resolution Matrix
| Condition | Resolution | Qualification |
|---|---|---|
| coverage/evidence insufficient or any candidate BLOCKED | INSUFFICIENT_EVIDENCE | BLOCKED |
| all candidates NO_FEASIBLE_SOLUTION | NO_FEASIBLE_MODEL | BLOCKED |
| exactly one MATERIALIZED and every other candidate NO_FEASIBLE_SOLUTION | UNIQUE_MODEL | inherits member qualification |
| two or more MATERIALIZED candidates | AMBIGUOUS | CONDITIONAL_ONLY |

## Ambiguity Rule
AMBIGUOUS means more than one materially feasible model explanation survives for the same market-price observation basis. P4-E never selects a winner, assigns model weights, averages economic requirements, or converts different economic variables into a pseudo-variable.

## Snapshot Rule
All MATERIALIZED MIE expectations in a set must share the exact MIEObservationBasis: price observation ID, observation date, PIT cutoff date, currency, and adjustment semantics.

## Evidence Closure
The set evidence_ids must cover global candidate-coverage evidence, global evidence-sufficiency evidence, every model disposition evidence ID, and every nested MIE evidence ID. Underlying P4-A validation remains authoritative for the raw evidence manifest.

## Red-team Cases
Required coverage: unique decision-grade; unique conditional; two-model ambiguity; mixed decision-grade/conditional ambiguity; non-feasible alternative; blocked alternative; coverage/evidence shortfall; incomplete candidate evaluation; duplicate model IDs; cross-snapshot mismatch; evidence-closure failure; no-feasible-model blocked state; serialization/schema validation.

## PASS Gate
P4-E passes only when the aggregate is deterministic, candidate-complete, model-preserving, snapshot-consistent, evidence-closed, never chooses a market-model winner, never introduces generic market_implied_net_profit, and existing P4-A through P4-D regression remains green.