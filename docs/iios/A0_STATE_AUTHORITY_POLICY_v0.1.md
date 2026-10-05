# A0 State Authority Policy v0.1

Date: 2026-10-05
Status: CANONICAL GOVERNANCE POLICY

## Purpose

Prevent project-state drift and make one rule authoritative for all future development:

> New development starts only from canonical `main` and the canonical Current State Index.

This policy governs project-state classification. It does not change Investment Core economics, valuation, forecast, MIE or Decision semantics.

## Three state classes

### 1. CANONICAL

Authoritative current state.

A record is CANONICAL only when it is present on the canonical `main` branch and is explicitly designated as current by this policy.

Primary authority:

- Git `main`
- `docs/PROJECT_STATE_INDEX.md` — the only canonical Current State Index
- `STATUS.md` — current human-readable summary, non-authoritative if it conflicts with the Current State Index
- versioned normative contracts / schemas / production code / tests on `main`

A merged PR is part of capability only after it is present on `main`.

### 2. HISTORICAL

Immutable record of a prior point in time.

Examples:
- prior state reconciliations;
- superseded roadmaps;
- prior semantic proposals;
- acceptance records for earlier milestones;
- old snapshots and frozen historical packages.

Historical records may explain how the project reached the current state, but they MUST NOT define current capability or next work.

Historical records must carry an explicit `HISTORICAL` or `SUPERSEDED` banner when their old state could otherwise be mistaken for current state.

### 3. DIAGNOSTIC

Non-authoritative investigative or experimental material.

Examples:
- unmerged PRs/branches;
- source-capture probes;
- diagnostic runners;
- temporary CI artifacts;
- experiments that are not accepted into `main`.

Diagnostic results may identify problems or support an engineering decision, but MUST NOT be treated as product capability or canonical project state.

## Authority precedence

When records disagree:

1. canonical `main`;
2. `docs/PROJECT_STATE_INDEX.md`;
3. normative versioned contracts / schemas / production tests on `main`;
4. independent CI execution evidence;
5. historical records;
6. chat context.

Historical or diagnostic material never overrides canonical main.

## New-development gate

Before any new implementation:

```
Read canonical main
        ↓
Read docs/PROJECT_STATE_INDEX.md
        ↓
Read the relevant normative contract
        ↓
Confirm target work is not already merged
        ↓
Create branch from the current canonical main SHA
        ↓
Implement only the declared batch scope
```

A historical branch, stale PR head, old snapshot, or chat transcript MUST NOT be used as the development base when a newer canonical main exists.

## State-writing rule

A state-changing document MUST identify whether it is:

- CANONICAL;
- HISTORICAL;
- DIAGNOSTIC.

Do not create a second competing Current State Index.

Do not store a mutable current-main SHA in multiple documents as an independent authority. The Git ref is authoritative.

## Scope protection

A0 introduces no investment capability.

It does not:

- add valuation models;
- change return semantics;
- change Decision Kernel precedence;
- add MIE logic;
- add forecast logic;
- add portfolio optimization;
- add automatic trading.

## A0 acceptance

A0 is PASS only when:

1. `docs/PROJECT_STATE_INDEX.md` is the only canonical Current State Index;
2. `STATUS.md` is a current summary and cannot contradict the Current State Index;
3. known superseded state documents are explicitly marked historical/superseded;
4. stale development paths are closed or explicitly diagnostic;
5. a deterministic state-authority test is executed in CI;
6. the documented new-development gate points only to canonical `main` + Current State Index.