# P4-F Final Acceptance — 2026-10-04

## Status

**FINAL PASS / MERGED**

P4-F PIT / Replay / Fail-closed MIE Integration is accepted on canonical `main`.

## Git / CI Evidence

- PR: #16
- PR head before merge: `e498466549bc040085ddf46a2512a9208e3d7a12`
- merge commit: `9732f33d3b0163832d317661b8171046d93c6455`
- PR Investment Core CI #164 / `37192169418`: **SUCCESS**
- PR FM00 CI #141 / `37192169420`: **SUCCESS**
- post-merge main Investment Core CI #165 / `37192209207`: **SUCCESS**
- post-merge main FM00 CI #142 / `37192209217`: **SUCCESS**
- final regression on PR head: **171 passed**
- compileall: **SUCCESS**
- schema JSON validation: **SUCCESS**
- existing CLI run + snapshot replay: **SUCCESS**

## Implementation

- `iios_mvp/p4f_mie_snapshot.py`
- `tests/test_p4f_mie_snapshot.py`
- `schemas/p4f_mie_snapshot_v0.2.schema.json`
- `docs/iios/P4F_PIT_REPLAY_FAILCLOSED_ACCEPTANCE_MATRIX_v0.2.md`

## Accepted Semantics

P4-F is the provenance, PIT and replay boundary for the accepted P4-A through P4-E Market Implied Expectation chain.

Every evidence ID referenced by the P4-E set must resolve to exactly one provenance record containing:

- explicit variable / unit / basis;
- observation date;
- `known_at` timestamp;
- source and source location;
- source content SHA-256;
- capture timestamp.

For cutoff `T`, P4-F enforces:

`observation_date <= T` and `known_at.date() <= T`.

Capture time may be after `T` because local acquisition time is not the PIT criterion. The criterion is whether the evidence was knowable by `T`.

Each materialized MIE price observation ID must resolve to a provenance record with `variable=market_price`, exact observation-date match and currency/unit match.

All materialized MIEs in one snapshot must share the same exact price observation ID, observation date, cutoff date, currency and adjustment semantics.

The snapshot contains the P4-E set payload, canonical provenance manifest, MIE-set hash, provenance hash and final snapshot hash. Disk persistence is create-once and refuses divergent overwrite.

Replay does not trust stored status fields. It independently revalidates:

1. MIE-set hash;
2. provenance hash;
3. snapshot integrity hash;
4. PIT validity;
5. evidence closure;
6. price observation binding;
7. common observation basis;
8. P4-E resolution and qualification semantics.

Any failure returns `replay_status=FAIL`.

## Red-team Findings Closed

1. Future `known_at` is rejected.
2. Future observation dates are rejected before downstream price-binding checks.
3. Missing provenance is rejected.
4. Wrong price variable is rejected.
5. Cross-model snapshot-basis tampering is rejected even for a forged self-consistent hash set.
6. Tampered snapshots fail integrity/replay.
7. Serialized non-materialized evaluations carrying an expectation are rejected.
8. Serialized model-ID/expectation mismatch is rejected.
9. Schema unknown-field boundary is tightened at the snapshot and evaluation top levels.
10. Post-cutoff capture with pre-cutoff `known_at` remains valid.

## Explicit Non-claims

P4-F does not prove the truth of external source content merely because a content hash is recorded. The external bytes/source capture themselves remain a separate evidence-admission concern.

P4-F does not implement Expectation Gap, Expected Return, probability selection, position sizing, or the production v0.2 decision engine.

## Next Gate

**P5 — Semantic Expectation Gap + Return Gate**

P5 may begin from the P4-F bound MIE artifact, but it must remain fail-closed whenever independent and market-implied variables are not economically equivalent or the market interpretation remains ambiguous.
