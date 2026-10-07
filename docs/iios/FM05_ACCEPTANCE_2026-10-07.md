# M1.2-FM05 Acceptance — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

## Scope

FM05 freezes the M1.2 exploratory research scope, estimand, and sample-sufficiency policy after FM04. It does not alter FM04 implementation, the frozen origin schedule, the four-model candidate universe, the N=3 selection threshold, or the contaminated/development-only research posture.

## Frozen adjudication

The current scope is:

**INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION**

The exact FM04 replay must reproduce:

- 406 outer selection units;
- 0 selected;
- 0 outer evaluated;
- 406 `NO_SELECTION`;
- 79 structural conditional groups;
- 0 empirical conditional groups.

These are sufficiency facts under the already-frozen estimand. They do not authorize a same-epoch threshold relaxation, state regrouping, origin deletion, model expansion, or result-driven tuning.

## Frozen estimand

Selection unit:

`security × driver × horizon × state_dimension × state_value × outer_origin`

Structural group unit:

`security × driver × horizon × state_dimension × state_value`

Primary selection estimand:

`difference in mean inner MAE among the four frozen model instances on the common inner-origin universe conditional on the outer-origin state`

Primary metric: MAE. Secondary metrics: RMSE and sMAPE. Rolling origins are not assumed IID. Inferential/significance claims are forbidden; outputs are descriptive only.

## Amendment boundary

Within research epoch `RE-M12-EXP-CATL-20260930`, the following are forbidden:

- lowering the common inner sample threshold;
- merging state values;
- deleting/skipping origins;
- expanding the model-family universe;
- adding result-derived thresholds;
- changing the primary metric;
- redefining the estimand from the FM04 outcome;
- relabeling DATA_QUALITY as an economic state.

Any result-driven change requires a **new research epoch** and a new scope/estimand freeze.

## Capability boundary

FM05 adds only a research-governance freeze and an independently generated validation receipt. It does not authorize model selection, production forecast routing, automatic execution, or investment decisions.

## Upstream hard boundaries

PIT, UNKNOWN, provenance, frozen origin schedule, nested inner/outer separation, and capability isolation remain inherited hard boundaries.

## CI acceptance evidence

- PR: #156
- accepted exact head: `b6ba3fa72b692b641b6e755df111b863db63bbad`
- dedicated workflow: `IIOS M1.2 FM05 Scope / Estimand / Sufficiency Freeze`
- accepted run: #1
- accepted run id: `37578843014`
- accepted job: `verify-fm05-scope-freeze`
- accepted job id: `112653697085`
- conclusion: **SUCCESS**
- archived receipt: `iios-m12-fm05-scope-freeze-37578843014`
- artifact SHA-256: `94d31e169d3fed1af20f21f788f0aa23815fe19625523652c50e9eb53a20e6e`

The dedicated gate independently replays FM02/FM03/FM04 inputs needed for the sufficiency adjudication, verifies the pinned FM03 snapshot and frozen upstream byte anchors, validates the FM05 contract, and emits the machine-readable FM05 scope-freeze receipt.
