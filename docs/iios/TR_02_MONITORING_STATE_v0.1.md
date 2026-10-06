# TR-02 — Monitoring State v0.1

Date: 2026-10-06
Status: ACCEPTED / CANONICAL

## Objective

Productize the monitoring state that consumes canonical Trigger Events without implementing a scheduler or notification service.

TR-02 freezes:
- one mutable, hash-protected Monitoring State projection per Trigger Contract;
- deterministic state transition from immutable Trigger Events;
- explicit due-state semantics;
- replay of the Monitoring State from persisted events.

## State separation

Monitoring State has independent fields for:
- lifecycle_status: ACTIVE / DISABLED / RETIRED;
- evaluation_status: NEVER_EVALUATED / VALID / UNKNOWN;
- last_trigger_state: MATCHED / NOT_MATCHED / UNKNOWN;
- due_state: UNSCHEDULED / NOT_DUE / DUE / OVERDUE.

Trigger state is observation output. It is not a Decision State and cannot authorize capital.

## Event transition

A Trigger Event must bind to the exact Trigger Contract. The Monitoring State is advanced only by a valid immutable event.

Events must be strictly newer by known_at than the persisted prior event, and evaluation_cutoff_at cannot move backwards. The same event_id may be re-applied idempotently only without changing next_due_at.

The next_due_at field is explicit state. TR-02 does not compute a schedule, run a scheduler, send alerts, or automatically mutate next_due_at.

## Due semantics

If next_due_at is absent, due_state is UNSCHEDULED. If next_due_at is supplied, due_reference_at must be explicit; no implicit current-time or next-due assumption is allowed.
If next_due_at equals the evaluation reference, due_state is DUE.
If next_due_at is earlier than the evaluation reference, due_state is OVERDUE.
Otherwise due_state is NOT_DUE.

## Boundary

Monitoring State cannot change Decision Precedence, Trust, Quality, valuation, forecast, MIE, portfolio constraints, or Human Approval.

TR-03 may consume monitoring history to build explicit Validation / replay evidence, but any investment decision remains under the canonical Decision Kernel and Human Approval lifecycle.


## Acceptance

TR-02 = PASS / MERGED / CANONICAL.

Canonical merge:
- PR #91;
- merge commit: 6b5a83ff3dcb0028945f455c517b369dbbf8220b.

Verification:
- dedicated GitHub Actions run #10 = SUCCESS;
- compileall = PASS;
- TR-02 test suite = PASS;
- monitoring state schema = PASS;
- git diff check = PASS;
- red-team scope and state/replay review = PASS.

Known non-blocking observation: replay reconstructs the final Monitoring State projection, but historical next_due_at mutations are not themselves represented as a separate immutable event stream. A future validation/audit-history layer may address that without changing TR-02 canonical semantics.

Next product boundary: Validation / Replay Productization. No scheduler or alerts implementation is implied.
