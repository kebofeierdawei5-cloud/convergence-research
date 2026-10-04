# P4-E Final Acceptance — 2026-10-04

## Status

**FINAL PASS / MERGED**

P4-E Multi-model Market Implied Expectation Set + Ambiguity Handling is accepted on canonical `main`.

## Git / CI Evidence

- PR: #14
- PR head before merge: `60e40bed89f96bcc30df4a31967ff55d84847423`
- merge commit: `3c1b4944d715bbb0e4716bab3a0721c78f0f4157`
- PR Investment Core CI #155 / `37190663254`: **SUCCESS**
- PR FM00 CI #130 / `37190663258`: **SUCCESS**
- post-merge main Investment Core CI #157 / `37190695693`: **SUCCESS**
- post-merge main FM00 CI #132 / `37190695593`: **SUCCESS**
- final regression on the PR head: **156 passed**
- existing CLI run + snapshot replay: **SUCCESS**
- compileall: **SUCCESS**
- schema JSON validation: **SUCCESS**

## Implementation

- `iios_mvp/multi_model_market_implied_expectation_set.py`
- `tests/test_multi_model_market_implied_expectation_set.py`
- `schemas/market_implied_expectation_set_v0.2.schema.json`
- `docs/iios/P4E_MULTI_MODEL_MIE_SET_ACCEPTANCE_MATRIX_v0.2.md`

## Accepted Semantics

P4-E is an aggregation and qualification boundary over accepted P4-A through P4-D `MarketImpliedExpectation` outputs.

It does not recompute any P3 inverse, change model-native variables, compare unlike economic variables, rank or select market models, assign model weights, average model requirements, calculate Expectation Gap, or calculate Expected Return.

Every globally admitted candidate model must have exactly one disposition:

- `MATERIALIZED`: a non-blocked P4 MIE artifact exists;
- `NO_FEASIBLE_SOLUTION`: the candidate was actually evaluated but its feasible solution set is empty;
- `BLOCKED`: the candidate cannot be resolved under the current evidence/state.

Resolution is deterministic:

| Condition | Resolution | Qualification |
|---|---|---|
| candidate coverage/evidence insufficient, or any candidate is BLOCKED | `INSUFFICIENT_EVIDENCE` | `BLOCKED` |
| all candidates are `NO_FEASIBLE_SOLUTION` | `NO_FEASIBLE_MODEL` | `BLOCKED` |
| exactly one `MATERIALIZED`, all others explicitly non-feasible | `UNIQUE_MODEL` | inherits the member qualification |
| two or more `MATERIALIZED` candidates | `AMBIGUOUS` | `CONDITIONAL_ONLY` |

Ambiguity is represented, not resolved by force. Different model-native requirements are preserved separately; the system never manufactures a common pseudo-variable.

All materialized expectations in one set must share the exact same price observation ID, observation date, PIT cutoff, currency and adjustment semantics. Set-level evidence IDs must close over candidate coverage, evidence sufficiency, model dispositions and nested MIE evidence.

## Red-team Findings Closed

1. Accidental literal-newline encoding in initial Python payload was caught by compileall.
2. Invalid blocked-MIE test fixture was caught because the base P4 validator correctly rejected inconsistent qualification.
3. Initial schema encoding was caught by JSON parsing.
4. Direct construction of a `MATERIALIZED` evaluation carrying a `BLOCKED` MIE is now rejected.
5. Model-evaluation order is canonicalized for deterministic serialization.

No red-team finding required reopening P2-B, P3-A, P3-B, or the frozen v0.2 semantic contract.

## Explicit Non-claims

P4-E does not claim that a surviving model is the true market pricing model. It does not claim that multiple surviving models can be combined into a probability distribution. It does not make an Expectation Gap or >15% return determination.

## Next Gate

**P4-F — PIT / Replay / Fail-closed MIE Integration**

P4-F must bind the completed P4-A through P4-E path to immutable case snapshots, exact PIT/provenance manifests, replay, and runtime fail-closed behavior before P5.
