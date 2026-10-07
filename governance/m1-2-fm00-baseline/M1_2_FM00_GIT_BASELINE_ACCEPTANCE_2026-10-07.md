# M1.2-FM00 Git Baseline Acceptance — 2026-10-07

Status: **CANDIDATE / PENDING CI**

## Task contract

### Objective
Establish the remote Git baseline for M1.2-FM00 as an additive child of the actual canonical IIOS `main`, while preserving the exact historical FM00 source baseline and the immutable G2 reference identity.

### User Value
Make M1.2 continuity reproducible from Git and machine-readable governance artifacts, without relying on chat state or silently rewriting historical frozen references.

### Product Surface
`governance/m1-2-fm00-baseline/` plus the dedicated baseline CI workflow and canonical state synchronization.

### Test / Acceptance
- current base main verified;
- historical FM00 baseline commit and tag verified as exact immutable anchors;
- current `research/fm00/` remains unchanged relative to the FM00 baseline lineage;
- G2 historical frozen identity and R0 successor evidence remain explicitly separated;
- FM01 data ingress remains blocked without exact M1.1 source bytes;
- baseline governance manifest validates;
- FM00 deterministic CI remains green;
- `git diff --check` passes.

### Out of Scope
FM01 data population, FM02, model selection, new forecast models, new valuation models, A02 universe construction, automatic execution, scheduler/alerts, and portfolio optimization.

## Exact lineage

Remote canonical main at task start:

```
60d5f9927cb5543415307454aea231376f86c72e
```

Immutable FM00 source baseline:

```
commit  536e883bc873dbe7dd7383690a7a95a0f65591a7
tag     m1.2-fm00-v0.1.0
tag obj  aac0cccf596ee2703caedffc08f434be9e2dffed
```

The historical FM00 commit is the exact source-baseline identity. This task does not rewrite that commit or its tag.

## G2 reference discipline

Historical frozen identity remains:

```
carrier = 899f0b1b9f3619458e17be76ac43dd6e00b5397d0c12adb7b68e2479c7f51524
```

The later R0 successor carrier is tracked separately:

```
carrier = bd5cbaf23c9029b46fafd19992029932431059de7424a08de48624aca5d431c8
role    = ACCEPTED_SUCCESSOR_FOR_CURRENT_CLOSURE_ROLE_ONLY
```

It is not substituted for the historical frozen carrier.

## M1.2 scope boundary

FM00 is the research-control baseline.

FM01 implementation already exists in the repository, but its CATL data admission remains:

```
BLOCKED_DATA_INGRESS
```

because the exact M1.1 historical source snapshot is absent. No numeric replacement is permitted.

## Acceptance rule

This document remains **PENDING CI** until the additive remote baseline commit has passed the dedicated baseline workflow on its exact PR head. It must then be independently checked after merge.

No production capability is changed by this governance baseline.
