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
CORE-03 Real 300750 Vertical Slice = PASS / MERGED
        ↓
CORE-03 P4-F / Expectation Gap Closure = ACTIVE / BLOCKED
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

CORE-02 is merged and accepted. CORE-03 real 300750 vertical slice is also merged and accepted: independent forecast → human-selected DCF → P4-F MIE attempt → fail-closed Expectation Gap.

CORE-03 current blocker is strictly the per-company PIT market-model observation set required to qualify P4-F. This is a data/evidence closure task, not a reason to activate CSI800/CSI Industry/A02.

CORE-02 acceptance:
- PR #29 merged;
- merge commit `2a1c376e2bf3c608ebdf88a95d8be5aeaf8580b9`;
- dedicated CI run #6 / `37209264413`: SUCCESS;
- 30 CORE-02 regression tests passed;
- Investment Core CI run #214 / `37209264423`: SUCCESS;
- CORE-01 CI run #10 / `37209264528`: SUCCESS.

Acceptance remains per-company and PIT-bound. CORE-03 must consume this economic core and the existing P4-F MIE infrastructure without introducing universe-level dependencies.


## CORE-03 Real 300750 acceptance

- PR #31 merged; merge commit `e0662bb4efa5bfc40478240a0d9ef4bbcadb658a`.
- CORE-03 CI run #7 / `37210940680`: SUCCESS.
- Real forecast 2027-2029: independent bottom-up scenario package, no FM01 production router.
- DCF: Bear/Base/Bull ~258.32 / 418.49 / 638.97 CNY per share; probability-weighted ~433.57; expected 3-year CAGR ~14.20% at 291.11 CNY.
- P4-F: BLOCKED / INSUFFICIENT_EVIDENCE with replay PASS.
- Expectation Gap: BLOCKED; intrinsic upside is not substituted.
- Next sub-gate: acquire PIT market-model observations for this single company.
