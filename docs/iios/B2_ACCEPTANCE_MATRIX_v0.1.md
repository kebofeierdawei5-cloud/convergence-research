# IIOS B2 — Acceptance Matrix v0.1

Status: CANDIDATE — implementation gate / scope-repair
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

## Research Track isolation

A02/CSI800 is outside the B2 namespace and B2 CI execution surface. It remains an independent Research Track capability under `research/a02*` and `research/a02_raw/`.

| Gate | Required condition | Current status |
|---|---|---|
| B2 namespace isolation | No A02/CSI800 code or artifacts under `research/b2/` | IMPLEMENTED / CI PENDING |
| B2 CI isolation | No A02/CSI800 execution step in B2 workflow | IMPLEMENTED / CI PENDING |
| Core/Research separation | A02 remains independently addressable | PASS |

## B2-A scope-repair exit criterion

B2-A passes only when the single-company Evidence/PIT machinery is green AND B2 has no A02/CSI800 namespace or CI dependency.

A CATL Evidence migration/admission is subsequent work. Existing capture artifacts must be audited for source fidelity before being admitted; metadata hashes alone do not prove source bytes.
