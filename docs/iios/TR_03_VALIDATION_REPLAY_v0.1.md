# TR-03 — Validation / Replay Productization v0.1

Date: 2026-10-06
Status: ACCEPTED / CANONICAL

## Objective

Productize a fail-closed Validation layer for the canonical monitoring chain without introducing a scheduler, notifications, automatic execution, or new investment-decision semantics.

TR-03 closes the known TR-02 audit observation that historical `next_due_at` mutations were not independently represented in an immutable transition history.

## Canonical source chain

Validation reads, but never trusts a prior Validation result as proof:

```
Decision Revision + Snapshot
        ↓
Trigger Contract
        ↓
Immutable Trigger Events
        ↓
Immutable Monitoring Initialization
        ↓
Immutable Monitoring Evaluation Records
        ↓
Mutable/hash-protected Monitoring State
        ↓
Fresh Validation / Replay
```

A Validation Record is an audit output, not an input to the validation algorithm.

## Immutable transition history

For every accepted Monitoring Event application, TR-03 persists one immutable Monitoring Evaluation Record.

The record binds:
- exact Decision Revision and revision hash;
- exact Trigger Contract and trigger hash;
- exact Trigger Event;
- previous Monitoring State hash;
- resulting Monitoring State hash;
- previous and resulting `next_due_at`;
- event `known_at` and `evaluation_cutoff_at`;
- evaluation status.

An immutable Monitoring Initialization Record preserves the exact initial state from which replay starts.

This makes historical `next_due_at` changes observable and replayable without changing the TR-02 Monitoring State schema.

## Replay semantics

Replay must:
1. independently validate the persisted Decision Revision against its snapshot;
2. independently validate the exact Trigger Contract binding;
3. independently validate every Trigger Event;
4. independently validate the immutable Initialization Record;
5. replay every Event in deterministic `known_at, trigger_event_id` order;
6. consume the corresponding immutable Evaluation Record for the explicit resulting `next_due_at`;
7. verify the previous-state and resulting-state hash chain;
8. verify the replayed final state is byte-equivalent in canonical JSON to the persisted Monitoring State.

Replay never consumes a previous Validation Record as evidence.

## Validation semantics

A Validation Record is `PASS` only when all required checks pass:

- `decision_revision_replay`
- `trigger_contract_binding`
- `trigger_event_pit`
- `monitoring_state_integrity`
- `transition_history`
- `monitoring_replay`

Otherwise the Validation Record is `FAIL`.

Validation uses an explicit `validation_cutoff_at`. Every checked Trigger Event must satisfy:

`observed_at <= known_at <= evaluation_cutoff_at <= validation_cutoff_at`.

A later local capture time does not create PIT validity; PIT is determined from the event's knowability timestamps.

Failure is fail-closed. A failed Validation never upgrades a Decision, Trust, Quality, Valuation, Forecast, MIE, Risk, Portfolio or Human Approval state.

## Persistence

Validation Records are immutable and hash-protected.

Reusing the same Validation ID with different content is rejected.

## CLI surface

TR-03 adds:
- `monitor-validate <trigger_id> --validation-cutoff-at <timestamp>`
- `monitor-validation-replay <validation_id>`

These commands only validate, persist, or replay audit evidence.

## Boundary

TR-03 does not implement or change:
- scheduler execution;
- notifications or alerts;
- automatic decision mutation or order execution;
- Decision Precedence;
- Trust, Quality, Thesis, Valuation, Forecast, MIE, Risk or Portfolio semantics;
- Machine Publication;
- Human Report / Report Quality Gate;
- new company acceptance.

TR-03 is a validation/audit layer only.
