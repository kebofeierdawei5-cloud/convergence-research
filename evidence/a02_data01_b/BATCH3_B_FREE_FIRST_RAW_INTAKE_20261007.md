# DATA-01-B Batch 3 — Free-First B Raw Intake

Date: 2026-10-07

## Decision

**Proceed with Batch 3.** This batch implements and independently verifies the B-side raw-intake boundary without weakening A02.

### B raw domains

- identity
- listing_delisting
- common_equity
- st_history
- industry_history
- source_vintages

All 11 A02 origins are required.

## Runtime probe

The latest canonical A02 artifact was independently inspected:

- run: `37595133874`
- artifact: `11469743020`
- ZIP SHA-256: `cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49`
- B preflight exit code: `4`
- status: **BLOCKED**

The artifact contains the current A snapshot only. It has no `DELIVERY_MANIFEST.json` and no B raw-domain files. Therefore B raw intake is not yet materially supplied.

## Engineering closure

An independent B-only raw preflight was added. It checks:

- exact 11-origin coverage;
- all six required B domains;
- actual raw file presence;
- independent SHA-256 recomputation;
- source reference;
- license/redistribution status;
- explicit knowledge basis;
- rejection of `retrieved_at` as `known_at`;
- rejection of current-only / UNKNOWN evidence as historical PIT capability;
- rejection of checksum-only declarations.

This is a **raw-readiness** gate only. It does not claim PIT admission or A02 admission.

## Negative controls

Local test suite: **4/4 PASS**.

The expected fail-closed cases include manifest-only delivery, checksum without bytes, retrieved_at-as-known_at, and current-only knowledge evidence.

## Boundary

Batch 3 may continue with actual B raw materialization when supplied. Until then:

`A02 = BLOCKED`
`Model Selection = LOCKED`
`Cross-security successor epoch = LOCKED`

Next valid material transition is actual B raw bundle supply, followed by Batch 4 / DATA-01-C independent raw verification.
