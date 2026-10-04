# P2-A Final Acceptance — Investment Core Contract v0.2

Date: 2026-10-04

## Acceptance Status

**P2-A = FINAL PASS**

P2-A scope: convert the frozen IIOS Investment Core Contract v0.2 into a machine-readable domain schema, executable invariants, CI-enforced tests, and explicit isolation from the legacy v0.1.1 decision semantics.

## Evidence Chain

- PR: #5
- PR URL: https://github.com/kebofeierdawei5-cloud/convergence-research/pull/5
- P2-A source HEAD before merge: `ec208f347fde64b08694d181d8ee8cf2f433e7ed`
- CI workflow run: #70
- CI run ID: `37183859358`
- CI conclusion: **success**
- Merge commit on `main`: `203aed6ce22c5ed34dfa4aba4639de3dde0801b8`

## Implemented

1. JSON Schema: `schemas/investment_core_case_v0.2.schema.json`
2. Executable validator: `iios_mvp/investment_core_contract.py`
3. Contract tests: `tests/test_investment_core_contract.py`
4. Engine integration guard: `iios_mvp/engine.py`
5. CI integration: `.github/workflows/iios_mvp.yml`

## Validated Boundaries

The P2-A validator enforces, at minimum:

- exact v0.2 contract version;
- PIT ordering for as-of / cutoff / evidence / price observation;
- explicit price adjustment semantics;
- required company and market evidence manifests;
- model-semantic economic-variable compatibility for Expectation Gap;
- no forced market-model winner under ambiguity / non-identifiability;
- explicit scenario probabilities and exact probability sum;
- deterministic expected-value / expected-return recomputation;
- strict positive Expected Return >15% hurdle;
- BUY / ADD Trust, thesis, market-identifiability, stability and risk gates;
- rejection of legacy market-implied fields in v0.2 cases.

Integration hardening additionally closes:

- unsupported explicit contract versions cannot fall through to the legacy validator;
- v0.2 cases cannot create a legacy 0.1.1 snapshot;
- legacy snapshot replay cannot accept a v0.2 input;
- v0.2 cases cannot enter the legacy v0.1.1 decision path.

## Explicit Capability Boundary

P2-A does **not** implement:

- evidence-backed Market Model Identification;
- calibrated Feasible Solution Set;
- Identifiability / Stability algorithms;
- model-specific Market Implied Expectation engine;
- semantic Expectation Gap calculation engine;
- production v0.2 decision engine;
- position sizing / Kelly;
- automatic execution.

The current engine therefore fails closed for a v0.2 case with:

`V02_ENGINE_NOT_IMPLEMENTED`

and does not execute legacy valuation / market-expectation logic.

## Next Gate

The next engineering target is **P2-B / Market Model Identification v0.2 foundation**, beginning with canonical market-model acceptance cases and the evidence-backed candidate-model / feasible-solution interfaces. Batch 2 v0.1 PR #3 remains blocked and must not be extended or merged.

## Acceptance Rule

This document records the completed P2-A gate on canonical `main`. It is not an independent third-party audit; its evidence consists of the frozen semantic contract, implementation review, integration audit, and GitHub CI execution.
