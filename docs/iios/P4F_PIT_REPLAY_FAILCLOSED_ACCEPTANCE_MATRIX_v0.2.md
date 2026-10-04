# P4-F PIT / Replay / Fail-closed MIE Integration Acceptance Matrix v0.2

## Scope
P4-F binds the accepted P4-A through P4-E Market Implied Expectation path to a PIT-aware provenance manifest and an immutable, hash-addressed snapshot.

P4-F does not calculate Expectation Gap, Expected Return, position sizing, or decisions.

## Evidence Binding
Every evidence ID referenced by the P4-E set must resolve to exactly one P4FProvenanceRecord containing:

- explicit variable / unit / basis;
- observation date;
- `known_at` timestamp;
- source and source location;
- content SHA-256;
- capture timestamp.

The price observation ID in each materialized MIE must resolve to a provenance record with `variable=market_price`, matching observation date and currency/unit.

## PIT Rule
For cutoff `T`:

`observation_date <= T` and `known_at.date() <= T` for every bound evidence record.

Capture time may be after `T`; PIT is determined by when the evidence was knowable, not when the local snapshot was captured.

Every materialized MIE observation basis must use exactly the snapshot cutoff date.

## Immutable Snapshot
The snapshot contains:

- P4-F schema/version;
- case ID and cutoff;
- canonicalized P4-E set payload;
- complete provenance manifest;
- SHA-256 of the set;
- SHA-256 of the provenance manifest;
- final snapshot SHA-256.

`write_p4f_snapshot` is create-once: an existing hash-addressed file may only be rewritten with byte-equivalent canonical content.

## Replay
Replay recomputes and checks:

1. snapshot integrity hash;
2. MIE-set hash;
3. provenance hash;
4. PIT validity;
5. evidence closure;
6. price observation binding;
7. common observation basis;
8. P4-E resolution and qualification semantics.

Any failure returns `replay_status=FAIL` and never upgrades the case to a positive state.

## Required Red-team Cases
- future `known_at` leak;
- future observation date;
- missing provenance record;
- wrong price variable;
- price observation date/currency mismatch;
- mismatched model observation bases;
- tampered MIE set;
- tampered provenance manifest;
- malformed content hash;
- blocked / insufficient P4-E set;
- deterministic snapshot serialization;
- post-cutoff capture with pre-cutoff `known_at` allowed.

## PASS Gate
P4-F passes only when PIT/provenance are fail-closed, snapshot identity is immutable and hash-verifiable, replay independently revalidates semantics, and the complete P4-A through P4-E regression remains green.
