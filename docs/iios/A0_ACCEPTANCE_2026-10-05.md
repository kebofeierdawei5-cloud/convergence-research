# A0 Governance / State Cleanup — Acceptance Record

Date: 2026-10-05
Status: **PASS / MERGED / CANONICAL**

## Scope

A0 changes project-state governance only. No Investment Core economics or decision capability was added or modified.

## Canonical authority

- canonical implementation source: Git `main`;
- canonical Current State Index: `docs/PROJECT_STATE_INDEX.md`;
- `STATUS.md`: human-readable summary only;
- governance policy: `docs/iios/A0_STATE_AUTHORITY_POLICY_v0.1.md`.

## Three state classes

- CANONICAL — current accepted state on `main`;
- HISTORICAL — immutable past-state records, explicitly marked;
- DIAGNOSTIC — unmerged/experimental/non-authoritative material.

## New-development gate

Every new batch starts from:

`canonical main → docs/PROJECT_STATE_INDEX.md → relevant normative contract → fresh branch`

Historical branches, stale PR heads and chat context cannot override canonical main.

## Changes accepted

- `docs/PROJECT_STATE_INDEX.md` rewritten as the single canonical Current State Index;
- `STATUS.md` reduced to a canonical summary and no longer competes as a state authority;
- stale/superseded state and continuity records explicitly marked historical;
- obsolete PR #3, #52 and #53 closed;
- deterministic `tests/test_state_authority.py` added and wired into Investment Core CI.

## CI evidence

PR #74:
- PR CI Investment Core #472 — PASS;
- PR CI CORE-00 #211 — PASS;
- full pytest on PR head — 385 passed;
- compileall — PASS.

Post-merge canonical main:
- merge commit: `8b0fdc0aa212fe14a186c1e60373b6a14a81e406`;
- Investment Core CI #473 — PASS;
- CORE-00 #212 — PASS.

## Acceptance judgment

**A0 PASS.** State authority is now explicit, testable and canonical.

Current next development batch:

**A1 — Company-side Evidence Closure**

Do not start new P3/P4/MIE model work as part of A0/A1.