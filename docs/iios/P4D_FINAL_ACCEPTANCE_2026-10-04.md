# P4-D Final Acceptance — SOTP / rNPV Market Implied Expectation v0.2

Date: 2026-10-04

## Acceptance Status

**P4-D = FINAL PASS / MERGED**

## Evidence Chain

- PR #13: MERGED
- P4-D pre-merge HEAD: `dd3e2cc775677b63ee1d48cdd15940b03af1f498`
- P4-D merge commit: `13729e7493850cb513843567dd5ee263c2301f36`
- PR Investment Core CI #147 / `37189771181`: **SUCCESS**
- PR FM00 CI #121 / `37189771200`: **SUCCESS**
- Post-merge main Investment Core CI #148 / `37189797363`: **SUCCESS**
- Post-merge main FM00 CI #122 / `37189797243`: **SUCCESS**
- Final regression reported by CI: **139 passed**
- Acceptance matrix: `docs/iios/P4D_SOTP_RNPV_MIE_ACCEPTANCE_MATRIX_v0.2.md`

## Scope

P4-D supports:

- SOTP
- rNPV

It directly consumes:

- P3-B model-specific inverse results;
- P4-A typed Market Implied Expectation boundary.

It does not redesign P2-B and does not implement P4-E/P4-F/P5.

## SOTP Semantic Result

P4-D emits:

- primary economic requirement: `residual_value`;
- role: `IMPLIED_RESIDUAL_CONDITIONAL_ON_SEGMENTS`;
- conditioning set: one explicit `segment_value` per `segment:<id>`.

The segment values are observed/current conditioning inputs. They are not relabeled as market-implied segment beliefs.

## rNPV Semantic Result

P4-D emits:

- one `pipeline_value` economic requirement per pipeline ID;
- basis preserves `pipeline:<id>`;
- role: `IMPLIED_PIPELINE_CONDITIONAL_ON_OBSERVED_COMPOSITION`.

The pipeline-specific requirements are a deterministic pro-rata decomposition of the accepted P3-B total implied pipeline requirement using the observed current pipeline-value composition.

Observed:

- `pipeline_value` is the composition anchor;
- `probability` is a conditioning variable;
- `timing` is a conditioning variable;
- `discount_rate` is a conditioning variable;
- `base_value` is a conditioning variable.

P4-D never emits probability as an economic requirement and never creates a pseudo market-implied probability.

## Critical Red Lines

P4-D does not claim:

- a full multidimensional feasible assumption space;
- that SOTP segment values are market-implied truths;
- that rNPV probabilities are market-implied probabilities;
- that a conditional requirement is market truth;
- decision-grade MIE qualification.

All materialized positive outputs use:

```
representation = CONDITIONAL_IMPLIED_VARIABLE
qualification  = CONDITIONAL_ONLY
```

Blocked upstream states remain fail-closed.

## Fail-Closed / Red-Team

Covered behavior:

- unstable upstream -> BLOCKED;
- insufficient candidate coverage -> BLOCKED;
- insufficient evidence -> BLOCKED;
- non-SOTP/rNPV candidate rejection;
- wrong P3 primary variable rejection;
- missing SOTP segments;
- missing rNPV pipeline/probability/timing;
- pipeline ID misalignment;
- observation/evidence provenance and variable/unit mismatch;
- P3 status/method tampering;
- P3 solution preservation without inverse recomputation;
- generic implied net profit rejection;
- no market-implied probability/timing output;
- no forced winner under ambiguity.

CI regression: 139 passed.

## Next Gate

**P4-E — Multi-model Market Implied Expectation Set + ambiguity handling**

Then:

```
P4-E
    ↓
P4-F PIT / replay / fail-closed integration
    ↓
P5 Expectation Gap
    ↓
Expected Return >15%
```
