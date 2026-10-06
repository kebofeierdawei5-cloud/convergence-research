# C0 — Governance Hygiene / Stage Baseline v0.1

Date: 2026-10-06
Status: CANDIDATE — PENDING ACCEPTANCE
Scope: project-state authority, continuity hygiene, and development-entry enforcement

## Objective

Close project-state drift after TR-03 and establish a clean entry boundary for Stage C.
C0 does not change investment calculations or decision semantics.

## User Value

A future development run can start from the repository without relying on chat context or accidentally following a superseded roadmap.

## Required controls

1. docs/PROJECT_STATE_INDEX.md is the only canonical Current State Index.
2. STATUS.md is a non-authoritative current summary and must not contradict the Current State Index.
3. Known superseded state/roadmap documents carry an explicit HISTORICAL or SUPERSEDED banner and point to the canonical Current State Index.
4. README describes current B1 v0.3 return/horizon semantics and current Stage C boundaries.
5. A deterministic CI validator checks the state-authority invariants.
6. New development starts from current canonical main + docs/PROJECT_STATE_INDEX.md.
7. PR/CI remains the acceptance path; an unmerged branch or PR is not current capability.

## Repository configuration boundary

GitHub branch protection / required-check configuration is repository-host configuration rather than source content. C0 records the required policy, but source-side acceptance must not claim that branch protection is active unless the GitHub repository configuration independently confirms it.

Observed at C0 start:
- main was not protected;
- no repository ruleset was configured through the available read interface.

This is a governance configuration gap, not an Investment Core semantic issue.

## Explicitly out of scope

- Valuation changes.
- Forecast changes.
- MIE changes.
- Decision Precedence changes.
- Trust/Quality semantics.
- Risk/Portfolio semantics.
- Trigger/Monitoring/Validation changes.
- scheduler.
- alerts/notifications.
- automatic execution/order placement.
- new P3/P4 model families.

## Acceptance

C0 source-level acceptance is PASS only when the deterministic validator passes in dedicated CI and the canonical state surfaces are internally consistent.

Repository branch-protection configuration, when available, should separately enforce the required CI checks on main; it is not silently treated as enabled.