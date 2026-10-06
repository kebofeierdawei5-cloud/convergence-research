# C8 Auth Remediation — 2026-10-06

Status: IMPLEMENTATION CANDIDATE — pending dedicated CI and canonical merge

## Scope

This batch remediates the three C8 authority/identity findings without adding investment capability:

- AUTH-001 — canonical Decision Admission required before a v0.3 Decision Revision can persist;
- AUTH-002 — Decision Series market/symbol/company identity is bound to the snapshot at the persistence boundary;
- AUTH-003 — Human Approval requires actor identity and the explicit HUMAN_AUTHENTICATED authorization method.

The lifecycle contract is versioned from `IIOS-DECISION-LIFECYCLE-0.1` to `IIOS-DECISION-LIFECYCLE-0.2` so the security semantics do not drift under the historical v0.1 label.

## AUTH-001

A production `admit_canonical_decision()` path re-runs `decide_v03` against the validated v0.3 case and compares the resulting decision byte-for-byte (canonical JSON) with the candidate snapshot decision.

The persisted Decision Revision carries the resulting immutable Decision Admission record and refuses v0.3 persistence without it.

The test suite also verifies that changing the snapshot action after canonical admission causes re-execution mismatch rather than admission.

## AUTH-002

`write_decision_revision()` loads the target Decision Series and requires exact market/symbol/company agreement with the snapshot identity before persisting the revision.

Case identity is simultaneously bound through the immutable Decision Admission record: case_id, cutoff_date, market, symbol and company must match the snapshot.

This prevents a CATL snapshot from being assigned the 科伦药业 series.

## AUTH-003

Human Approval now requires:

- actor_identity: non-empty;
- authorization_method: exactly HUMAN_AUTHENTICATED.

The approval hash includes both fields, so tampering with actor identity is detected.

This establishes the repository-level authorization boundary; actual human authentication remains an external application/session responsibility.

## Compatibility

Historical lifecycle v0.1 schema remains unchanged. New canonical lifecycle revisions use v0.2.

No scheduler, alerts, automatic execution, new valuation/forecasting logic, MIE model, portfolio optimization, or universe expansion is included.
