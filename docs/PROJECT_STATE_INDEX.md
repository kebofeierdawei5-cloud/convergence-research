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
CORE-00 Scope Reset & Architecture Reconciliation = ACTIVE
        ↓
CORE-01 Single Company Research Intake = NEXT
```

## Authority / continuity

1. Git repository `main): source, contracts, tests, ADRs, changelog, state indexes.
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

## Next development task

`CORE-00 | Scope Reset & Architecture Reconciliation`

Acceptance requires the scope contract, machine isolation guard, status/index reconciliation and green CI.

After CORE-00:

`CORE-01 | Single Company Research Intake`.
