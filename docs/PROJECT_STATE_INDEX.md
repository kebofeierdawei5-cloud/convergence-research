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
CORE-04 Production Decision Kernel = ACTIVE / UNDER CI
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

Decision Semantics Reconciliation → CORE-04 Production Decision Kernel.

- PR #69 P3-A-RA remains OPEN / NOT MERGED; its exact implementation head is `26079a14f8d50ae8e8d1f589d06f2f0aec44341a`.
- CORE-04 production-kernel work is intentionally based on canonical `main`, not on the unmerged PR #69 branch.
- B1 v0.3 MIE semantics are consumed as `OPTIONAL_EXPLANATORY` in the new kernel.
- Legacy MIE-mandatory decision behavior remains compatibility-only.
- Target entry price is return/risk-first; MIE revalidation is an optional refinement when a qualified MIE reference exists.

## CORE-03 Real 300750 acceptance

- PR #31 merged; merge commit `e0662bb4efa5bfc40478240a0d9ef4bbcadb658a`.
- CORE-03 CI run #7 / `37210940680`: SUCCESS.
- Real forecast 2027-2029: independent bottom-up scenario package, no FM01 production router.
- DCF: Bear/Base/Bull ~258.32 / 418.49 / 638.97 CNY per share; probability-weighted ~433.57; expected 3-year CAGR ~14.20% at 291.11 CNY.
- P4-F: BLOCKED / INSUFFICIENT_EVIDENCE with replay PASS.
- Expectation Gap: BLOCKED; intrinsic upside is not substituted.
- Next sub-gate: acquire PIT market-model observations for this single company.


## CORE-04 Decision Semantics Reconciliation

- B1 v0.3 MIE role is frozen as OPTIONAL_EXPLANATORY for BUY/ADD.
- Missing / UNKNOWN / BLOCKED / AMBIGUOUS MIE does not by itself veto a company-side BUY/ADD opportunity.
- Return/risk target-entry price is valid without mandatory MIE revalidation; qualified MIE may refine it when present.
- Production kernel: `iios_mvp/decision_kernel_v03.py`.
- Governance record: `docs/iios/CORE_04_DECISION_SEMANTICS_RECONCILIATION_v0.1.md`.
- PR #70 is the current CORE-04 merge candidate and is not yet merged.
- PR #69 P3-A-RA remains independently open and not merged.
