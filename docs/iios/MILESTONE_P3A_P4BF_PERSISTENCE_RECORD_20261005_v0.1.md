# IIOS Milestone Persistence Record — P3-A-RA / P4-B~P4-F

Date: 2026-10-05
Repository: `kebofeierdawei5-cloud/convergence-research`
PR: #69
Branch: `feature/p3-a-ra-market-support-regime-20261005`

## Canonical checkpoint

The completed implementation checkpoint before this persistence record is:

`26079a14f8d50ae8e8d1f589d06f2f0aec44341a`

Base used for the P3-A-RA comparison:

`461fe661c735247956ee6865edd93acb8e746273`

PR #69 remains OPEN and mergeable. Owner merge decision is intentionally preserved.

## Verified CI

At commit `26079a14f8d50ae8e8d1f589d06f2f0aec44341a`:

- IIOS Investment Core CI #438 — SUCCESS
- IIOS CORE-00 Scope Reconciliation #175 — SUCCESS
- IIOS CORE-03 Real 300750 #87 — SUCCESS

## Preserved semantic result

P3-A-RA separates three previously conflated states:

1. Mathematical model fit:
   `FEASIBLE / INFEASIBLE / INSUFFICIENT_EVIDENCE / CONTRADICTED`
2. Historical empirical support:
   `IN_RANGE / BELOW_HISTORICAL_RANGE / ABOVE_HISTORICAL_RANGE / UNKNOWN / INSUFFICIENT_EVIDENCE`
3. Regime interpretation:
   `NOT_ASSESSED / POSSIBLE_REGIME_SHIFT / VERIFIED_REGIME_SHIFT / VERIFIED_MODEL_FAILURE`

Outside historical support is not proof of mathematical infeasibility, unidentifiability, regime shift, or model failure.

## Downstream hard negative invariant

`FEASIBLE + IDENTIFIABLE + OUTSIDE_HISTORICAL_SUPPORT`

must never become:

`DECISION_GRADE`

and must never permit:

`Capital Admission`

The exercised downstream paths enforce this through:

- P4-B ratio MIE: outside-support hard block;
- P4-C DCF/DDM: conditional-only / blocked;
- P4-D SOTP/rNPV: conditional-only / blocked;
- P4-E multi-model resolution: `NO_DECISION_GRADE_MODEL + BLOCKED` when any admitted model is outside-support, including mixed-model anti-bypass;
- P4-F snapshot/replay: semantic recomputation preserves the blocked result and rejects tampered resolution/qualification.

## 300750 real-case preserved oracle

- current EV/EBITDA: `8.3755367867x`
- historical support: `13.6686920853x`–`16.3854513730x`
- P3 fit: `FEASIBLE`
- support: `BELOW_HISTORICAL_RANGE`
- regime interpretation: `POSSIBLE_REGIME_SHIFT`
- identifiability: `IDENTIFIABLE`
- P4-B: `BLOCKED`
- P4-F: `NO_DECISION_GRADE_MODEL + BLOCKED`, replay `PASS`
- capital admitted: `FALSE`
- no decision-grade MIE / Expectation Gap / BUY / ADD is produced by this outside-support path.

## Source-of-truth rule

This file is a durable milestone index, not a substitute for the implementation.

The canonical implementation consists of the production code, schemas, tests, workflow, and 300750 E2E changes already present in PR #69. The full 23-file change set is referenced by the checkpoint manifest maintained with the local backup.

## Local backup

A matching local checkpoint was created on 2026-10-05:

`IIOS_P3A_P4BF_CHECKPOINT_2026-10-05.zip`

Local archive SHA-256:

`a25c03dbf709027510484a23b91520b3c3549322bad1ec5e4ff42b3ecdf3ee3b`

The local package preserves the two governing semantic documents, Git references, changed-file manifest, and integrity hashes. Git remains the canonical full-source store.
