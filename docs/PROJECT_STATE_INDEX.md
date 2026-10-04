# IIOS Project State Index

Snapshot: 2026-10-04

## Current canonical engineering state

```
G2 R10 Reference Governance Runtime = FROZEN
        ↓
B0 Repair = PASS
        ↓
B1 Investment Semantics v0.3 = PASS / FROZEN
        ↓
P3/P4 Market Implied Expectation Infrastructure = FINAL PASS / CONDITIONAL
        ↓
CORE-00 Scope Reset & Architecture Reconciliation = PASS / MERGED
        ↓
CORE-01 Single Company Research Intake = PASS / MERGED
        ↓
CORE-02 Company Economic Core = PASS / MERGED
        ↓
CORE-03 Market Expectation + Expectation Gap = ACTIVE
```

## Authority / continuity

1. Git repository `main`: source, contracts, tests, ADRs, changelog, state indexes.
2. Frozen governance artifact identity + evidence: `governance/g2-r10-reference/`.
3. Investment Core contract: `docs/iios/IIOS_INVESTMENT_CORE_CONTRACT_v0.3.md`.
4. CORE-00 scope authority: `docs/iios/CORE_00_SCOPE_RECONCILIATION_v0.1.md`.
5. Research-control artifacts: `research/`.
6. Chat history is context only, not authoritative project state.

## Immutable boundary

G2 frozen bytes remain immutable. B2 v0.1 evidence/PIT artifacts remain historical engineering artifacts and are not rewritten by CORE-00.

## Investment Core boundary

Investment Core begins with a user-selected security and cutoff.

Required research infrastructure:

- Single-company evidence/PIT;
- company reality / quality / value core;
- independent forecast;
- valuation;
- risk / portfolio constraints;
- decision semantics.

Not required as an Investment Core entry/completion gate:

- CSI800 historical membership;
- CSI Industry historical classification;
- full-market historical universe;
- PIT Security Master for universe construction;
- FINANCIAL / NON_FINANCIAL universe filtering.

## Research Track boundary

A02/CSI historical-universe reconstruction and FM forecast research remain valid independent workstreams.

A02 admission status:

```
BLOCKED / RESEARCH-ONLY / NON-BLOCKING TO INVESTMENT CORE
```

## Current development task

`CORE-03 | Market Expectation + Expectation Gap`

CORE-02 is now merged and accepted. It consumes admitted company-specific evidence and constructs Reality / Trust / Quality / Value Core / Value Driver Ranking plus a candidate valuation route.

CORE-02 acceptance:
- PR #29 merged;
- merge commit `2a1c376e2bf3c608ebdf88a95d8be5aeaf8580b9`;
- dedicated CI run #6 / `37209264413`: SUCCESS;
- 30 CORE-02 regression tests passed;
- Investment Core CI run #214 / `37209264423`: SUCCESS;
- CORE-01 CI run #10 / `37209264528`: SUCCESS.

Acceptance remains per-company and PIT-bound. CORE-03 must consume this economic core and the existing P4-F MIE infrastructure without introducing universe-level dependencies.
