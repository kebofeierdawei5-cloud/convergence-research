# IIOS CORE-00 — Scope Reset & Architecture Reconciliation v0.1

Date: 2026-10-04
Status: CANDIDATE FOR ACCEPTANCE
Parent: B0/B1 repair conclusions + B1 Investment Core Contract v0.3

## 1. Purpose

CORE-00 establishes the executable boundary between:

- Investment Core: single-company investment analysis and decision.
- Research Track: cross-company, historical-universe and forecast-model research.

This document is the current execution-scope authority for the repaired Investment Core until superseded by a versioned successor.

## 2. First-principles product boundary

The Investment Core starts from a user-selected security and cutoff:

```
Market + Symbol + As-of/Cutoff + Current Position
                    ↓
           Single-company Case
```

The core MUST NOT require a universe-selection stage.

Therefore the following are Research Track inputs, not Investment Core required dependencies:

- CSI800 historical membership;
- CSI Industry historical classification;
- historical universe reconstruction;
- PIT Security Master for universe construction;
- FINANCIAL / NON_FINANCIAL universe filtering.

A company can be classified or economically profiled inside its own case when useful, but no full-market historical universe is required to start or complete an Investment Core case.

## 3. PIT boundary

CORE-00 removes only the unnecessary universe dependency.

It does NOT remove PIT.

### Current case

For a current as-of case, the system may use current authoritative/free sources and preserve capture/provenance metadata.

### Historical case

For a historical cutoff T, the case must still establish what was knowable by T.

Required temporal distinctions remain:

```
published_at
known_at
retrieved_at
observation_date / period
effective_from / effective_to
```

Canonical historical knowledge rule:

```
known_at <= cutoff
```

A current value cannot be silently back-applied to a historical cutoff.

The key reduction is therefore:

```
Historical company PIT case
    ≠
Historical full-market PIT universe
```

## 4. Evidence layering

The frozen B2 Evidence Contract v0.1 remains valid as a cross-cutting evidence/PIT semantic foundation.

CORE-00 applies it in two layers:

### Core Evidence Layer

Allowed for Investment Core:

- evidence identity;
- source identity and provenance;
- observation date / period;
- published_at / known_at / retrieved_at;
- effective intervals where applicable;
- source-content hashing when byte-addressable;
- derivation lineage;
- conflict handling;
- PIT qualification;
- immutable snapshot / replay semantics.

### Research Universe Layer

Reserved for Research Track:

- CSI800 membership history;
- CSI Industry history;
- historical universe construction;
- PIT Security Master assembly for cross-company research;
- cross-company forecast research datasets.

A02 admission is NOT a prerequisite for a normal single-company Investment Core run.

The existing frozen B2 v0.1 document is not rewritten by CORE-00; its A02/universe application remains confined to the Research Track.

## 5. MIE boundary

P3/P4 Market Implied Expectation infrastructure remains part of the Investment Core capability surface because it is the market-side explanation of what the current price requires.

However, under B1 v0.3:

- MIE is explanatory/conditional infrastructure;
- MIE is not a universal BUY/ADD gate;
- MIE UNKNOWN or ambiguity does not by itself veto a company-side opportunity;
- qualified contradiction may trigger REVIEW_REQUIRED only through an explicit decision-policy rule;
- P3/P4 model breadth must not expand merely to increase model count.

P3/P4 remain reusable infrastructure. CORE-00 does not delete or bypass them.

## 6. Research Track

The following remain valid research work:

```
RESEARCH
  ├─ CSI800 historical membership
  ├─ CSI Industry historical classification
  ├─ PIT Security Master / historical universe
  ├─ FM-00 / FM-01 / later forecast research
  └─ cross-company backtest / model-selection research
```

Research may improve company-case capabilities later, but Research completion is not an Investment Core release gate.

A02 may continue independently without blocking CORE-01 and later core batches.

## 7. Investment Core path after CORE-00

```
CORE-00  Scope / architecture reconciliation
    ↓
CORE-01  Single Company Research Intake
    ↓
CORE-02  Company Economic Core
    ↓
CORE-03  Market Expectation + Expectation Gap
    ↓
CORE-04  Decision Kernel
    ↓
CORE-05  Immutable Decision / Replay / Real Case
    ↓
Real Company #1
    ↓
Real Company #2
    ↓
Independent Audit
```

CORE-00 is complete when the scope is both documented and machine-guarded.

## 8. Forbidden dependency rule

The following MUST NOT become an Investment Core Required Dependency:

```
A02
CSI800
CSI Industry historical database
PIT Security Master for universe selection
full-market historical universe
paid broker/commercial data
```

This does not prohibit the core from consuming an independently supplied company-specific fact whose provenance happens to originate from a research dataset. It prohibits requiring the research platform itself as the entry or completion gate for a single-company case.

## 9. Machine acceptance invariants

1. No Python module under `iios_mvp/` imports `research.*`.
2. The Investment Core CI workflow contains no A02 / CSI800 / CSI Industry / research-track path dependency.
3. A02/CSI research workflows remain separately addressable.
4. Core documentation identifies A02/CSI work as Research Track rather than Required Dependency.
5. B1 v0.3 MIE semantics remain intact: MIE is non-mandatory for BUY/ADD.
6. Historical single-company use still requires defensible PIT evidence.
7. CORE-00 introduces no new valuation model, forecast model, portfolio optimizer or trading capability.

## 10. Non-claims

CORE-00 does not claim:

- that all company-specific public data is already available;
- that historical single-company PIT evidence is always recoverable;
- that P3/P4 identify the true market pricing model;
- that the Investment Core is already production-capable;
- that A02 research is unnecessary in the long-term Research Track.

## 11. Acceptance

CORE-00 acceptance requires:

- this scope contract present on canonical branch;
- automated isolation tests PASS;
- Investment Core CI remains green;
- no mutation to frozen B2 v0.1 semantic artifacts;
- status/index documents point to CORE-00 as the current execution gate;
- A02/CSI research status explicitly marked independent/non-blocking for Investment Core.

