# DATA-01-B Run #3 Independent Adjudication

Workflow run `37593671212`; head `6f47e5f6f481df8f4a300765f237c5f7f70dae0d`; artifact `11469780985`.

## Integrity

GitHub artifact digest:
`sha256:85e836b2e797730be459a334172993118eb7101e44014c2539344c7ef679eb62`

Independent ZIP SHA-256:
`85e836b2e797730be459a334172993118eb7101e44014c2539344c7ef679eb62`

Result: **PASS**.

The artifact contains 9 physical files. Its independent manifest contains 8 entries and all 8/8 hashes recompute exactly.

## Runtime

The materializer returned exit code `4`, the explicitly accepted fail-closed result. Workflow `success` therefore means execution/upload succeeded, not B admission.

## PIT adjudication

- Identity: **BLOCKED**.
- Listing/delisting PIT: **BLOCKED_FOR_PIT**.
- Common-equity PIT: **BLOCKED_FOR_PIT**.
- ST history PIT: **BLOCKED**.
- CSI taxonomy definition: **PASS_FOR_STANDARD_DEFINITION**.
- CSI security-level industry history: **BLOCKED**.
- Baostock: **BLOCKED / not admitted** (`10002007 网络接收错误`).
- `retrieved_at` was not promoted to `known_at`.
- Current snapshots were not promoted to historical PIT evidence.
- Secondary data was not promoted to normative authority.

## Final result

**BLOCKED**. This is the only permitted Batch-1 result for Run #3.
