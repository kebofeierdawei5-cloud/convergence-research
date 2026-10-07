# DATA-01-A Batch 2 — Latest Runtime Artifact Adjudication

Date: 2026-10-07

## Result

The latest canonical-head A02 Exact Raw Materialization run was independently downloaded and byte-hashed.

- Workflow run: `37595133874`
- Head: `ee260b4d19d034c82433483acbc24e0eb2caaf16`
- Artifact: `11469743020` / `A02-exact-raw-37595133874`
- Artifact size: `197437` bytes
- GitHub artifact digest: `cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49`
- Independent ZIP SHA-256: `cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49`
- Artifact integrity: **PASS**

## Terminal control

The artifact contains a 169,984-byte `000906cons.xls`, but it is the current 2026-10-04 snapshot:

- observed SHA-256: `b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`
- required historical target SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`
- size match: **PASS**
- exact SHA match: **FAIL**
- classification: `CURRENT_SNAPSHOT_NOT_HISTORICAL_TARGET`

Therefore the artifact does **not** satisfy the Batch 2 historical carrier requirement.

## PIT coverage

The required historical states remain:

`2023-06, 2023-12, 2024-06, 2024-12, 2025-06, 2025-12, 2026-06`

No raw state-file set for these seven historical states is present in the artifact. PIT reconstruction is therefore not reached.

## Adjudication

`HISTORICAL_CARRIER_BYTES = BLOCKED`

No checksum declaration, current snapshot, archive URL, or `retrieved_at` field is promoted to historical PIT evidence.

Downstream locks remain unchanged:

- A02 admission: **BLOCKED**
- Model Selection: **LOCKED**
- Cross-security successor research epoch: **LOCKED**

The next valid transition is still the supply of an actual historical carrier: either the exact historical `000906cons.xls` bytes or an official historical CSI800 rebalance/adjustment bundle sufficient to reconstruct all seven frozen states.
