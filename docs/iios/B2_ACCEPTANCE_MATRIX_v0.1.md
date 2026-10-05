# IIOS B2 — Acceptance Matrix v0.1

Status: CANDIDATE — implementation gate
Date: 2026-10-05

## Investment Core B2-A

| Gate | Required condition | Current status |
|---|---|---|
| Evidence contract | Machine-readable Evidence Record schema + executable validator | PASS |
| Source registry | Free-first registry, paid data non-mandatory | PASS |
| PIT semantics | known_at / published_at / retrieved_at / effective intervals separated | PASS |
| Single-company manifest | Versioned case-level Evidence Manifest schema + validator | IMPLEMENTED / CI PENDING |
| Exact-byte verifier | Physical size + SHA-256 recomputed from local raw bytes | IMPLEMENTED / CI PENDING |
| PIT fail-closed test | Future known_at blocks | IMPLEMENTED / CI PENDING |
| Coverage fail-closed test | Missing required company evidence group blocks | IMPLEMENTED / CI PENDING |
| Raw verification boundary | No raw bytes => no exact-byte admission | IMPLEMENTED / CI PENDING |

## A02 Research Track

A02/CSI800 remains a separate adapter and is not a B2 Investment Core completion gate.

| Gate | Current status |
|---|---|
| 000906cons.xls exact historical bytes | BLOCKED |
| Historical CSI800 coverage | BLOCKED |
| PIT Security Master raw bundle | BLOCKED |
| A02 overall admission | BLOCKED |

## B2-A exit criterion

B2-A passes when the single-company Evidence Manifest machinery and its fail-closed boundaries pass CI.

A CATL production-data admission is a subsequent B2-B task. Existing metadata hashes do not constitute physical byte verification.
