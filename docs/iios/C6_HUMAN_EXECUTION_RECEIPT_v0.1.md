# IIOS C6 — Human Execution Receipt v0.1

Date: 2026-10-06
Status: IMPLEMENTATION CANDIDATE — pending dedicated CI and canonical acceptance

## Objective

Record what the human actually executed after approving a specific Decision Revision, without changing the historical AI Decision, Human Approval, or Current Projection records.

Canonical relationship:

Decision Revision
→ Human Approval
→ Human Execution Receipt

The Receipt is downstream evidence. It is never an authorization mechanism and never feeds back into the Decision Kernel.

## Receipt binding

Every Receipt binds:

- execution receipt identity;
- exact decision ID and decision series;
- revision and run ID;
- case and cutoff;
- exact snapshot hash;
- exact revision hash;
- exact human approval hash;
- approved action;
- execution timestamp;
- execution status;
- executed quantity and/or executed position when applicable;
- executed price when available;
- human actor identity;
- auto-execution flag = false;
- policy effect.

A Receipt can only be created when the persisted Human Approval is exactly `HUMAN_APPROVED`.

## Execution status

Supported statuses:

- `EXECUTED`
- `PARTIALLY_EXECUTED`
- `NOT_EXECUTED`
- `CANCELLED`

For `EXECUTED` and `PARTIALLY_EXECUTED`, at least one actual execution quantity/position field is required. No fake zero quantity is generated for `NOT_EXECUTED` / `CANCELLED`.

## Immutability

Receipt persistence uses the existing immutable-create adapter.

Re-submitting an identical Receipt is idempotent. Re-submitting the same Receipt ID with different content is rejected.

The implementation never writes to:

- the Decision Revision record;
- the Human Approval record;
- the Current Projection record.

Replay reconstructs the Receipt from those exact upstream records and compares the content-addressed hash.

## Authority boundary

C6 policy effect:

`POST_APPROVAL_RECORD_ONLY_NO_DECISION_MUTATION`

Therefore:

- Receipt creation does not mutate the approved action;
- Receipt status does not change Decision status;
- execution quantity/price does not change historical AI or Human Approval artifacts;
- `auto_execution` remains false;
- no broker/order API is introduced.

The existing DR-01 contract does not carry an approval timestamp, so C6 machine-verifies exact approved-record binding and persistence ordering, but does not infer an approval-time chronology that is absent from the upstream contract.

## Explicit non-goals

C6 does not add:

- order placement;
- broker integration;
- automatic execution;
- scheduler / alerts;
- portfolio optimization;
- Decision Precedence changes;
- new P3/P4/MIE models;
- Forecast Research productionization;
- modification of DR-01 historical artifacts.

## Acceptance target

Dedicated C6 CI must prove:

1. Receipt binds exact revision, snapshot and approval hashes;
2. rejected approval cannot create a Receipt;
3. persisted Receipt is immutable;
4. Receipt creation does not mutate revision/approval/current projection;
5. tampering is detected;
6. replay is deterministic from persisted upstream records;
7. `NOT_EXECUTED` can be recorded without fabricated execution quantity;
8. invalid timestamps / negative execution values fail closed;
9. standalone schema validation passes;
10. no automatic execution path is introduced.
