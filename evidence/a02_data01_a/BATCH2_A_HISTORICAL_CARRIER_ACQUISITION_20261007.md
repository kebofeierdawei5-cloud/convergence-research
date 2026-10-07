# Batch 2 — DATA-01-A Historical Carrier Acquisition

## Result

`BLOCKED_EXACT_CARRIER_BYTES_NOT_AVAILABLE`

## Historical handoff located

A legacy G0-T02 handoff manifest was independently located at `benzemaer/convergence-research` commit `fec2a640d478e18e10c0a56164caedee7666ed16`.

Snapshot: `CSINDEX_000906_20260703T100909Z`

Historical package declaration:

- size: `373560` bytes
- SHA-256: `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`
- contents manifest SHA-256: `823d6d3ffe75730fb5789170d6539f65477b458c5cf70f9389af716f18c3412d`

The handoff declares an exact `000906cons.xls` member of 169984 bytes with frozen SHA-256 `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`.

## Critical evidence boundary

The handoff package itself is not present in the current Git tree, current Library, or current filesystem. The Git tree contains only the handoff manifest and related metadata; no binary XLS or package object is available for independent hashing.

Therefore:

`declared package/hash != current byte evidence`

## Independent A raw preflight

The new independent A-only preflight gate was executed with negative controls:

- manifest only → BLOCKED;
- wrong terminal bytes → BLOCKED;
- historical state without raw bytes → BLOCKED;
- tests: **3/3 PASS**.

The preflight does not consume collector receipts as proof and does not infer historical membership from a current snapshot.

## Exit state

`A_RAW_COMPLETE = BLOCKED`

`A02_ADMISSION = BLOCKED`

`cross-security successor epoch = LOCKED`

`model selection = LOCKED`

## Next accepted transition

Obtain the historical handoff package bytes through an approved non-Git channel, or an equivalent official CSI historical rebalance/raw bundle, then rerun the independent A preflight.
