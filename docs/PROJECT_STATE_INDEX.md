# IIOS Project State Index

Snapshot: 2026-10-05

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
B2-A Single Company Evidence / PIT Foundation = PASS / MERGED
        ↓
B2-A Scope Repair = PASS / MERGED
        ↓
CATL Existing Evidence Migration / Admission = PASS / TECHNICAL
        ↓
CATL Primary-Source Gap Supplementation = ACTIVE
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

CATL Primary-Source Gap Supplementation

CATL E001-E010 existing capture artifacts have passed B2 technical migration: physical capture bytes, size/SHA-256, case binding, PIT and manifest integrity all pass CI. The remaining work is limited to targeted source-quality gaps; no new historical-data platform is required.

PR #32 Horizon Semantics is merged to main (a524390382044b9474c17f2712a2cef8adeb9612). Investment Core horizon semantics use H=1Y as the normative default; H=3 requires explicit case-level override evidence.

CORE-00 through CORE-03 vertical execution are merged/accepted. P4-F remains valid infrastructure, but Expectation Gap is not forced ahead of Evidence/PIT closure.

B2-A is PASS / MERGED:
- PR #33 merged c8246ceaaad5e9b1cc02fe422723c39a441ea4f3;
- B2 exact raw-byte, PIT, case-binding and required-group machinery is active;
- PR #34 raw-root containment hardening merged 6583b054ed764daa5fbbe5f1b3d4b0b004866ad3;
- B2 CI passed after both changes.

CATL Existing Evidence Migration / Admission is PASS / TECHNICAL for RC-CN-A-300750-20261004.
E001-E010 are physically present and pass B2 byte/PIT/manifest validation. Source-quality is separately graded: E002 remains P0 primary-price gap; E003/E007 remain P1 direct-primary disclosure gaps if material to Trust/Governance. Secondary evidence is never silently upgraded to primary.

Current canonical main baseline: 00fdf82a374ac46a5b99567b590e940d7220bd23.

## CORE-03 Real 300750 acceptance

- PR #31 merged; merge commit `e0662bb4efa5bfc40478240a0d9ef4bbcadb658a`.
- CORE-03 CI run #7 / `37210940680`: SUCCESS.
- Real forecast 2027-2029: independent bottom-up scenario package, no FM01 production router.
- DCF: Bear/Base/Bull ~258.32 / 418.49 / 638.97 CNY per share; probability-weighted ~433.57; expected 3-year CAGR ~14.20% at 291.11 CNY.
- P4-F: BLOCKED / INSUFFICIENT_EVIDENCE with replay PASS.
- Expectation Gap: BLOCKED; intrinsic upside is not substituted.
- Next sub-gate: acquire PIT market-model observations for this single company.
