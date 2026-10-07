# M1.2-DATA-01-B / B3-01 — B Raw Evidence Acquisition Adjudication

Date: 2026-10-07
Status: **BLOCKED — awaiting actual B raw evidence supply**
Batch: DATA-01-B / B3-01
Universe: OU-M12-A02-CSI800-NONFIN-PIT-001

## 1. Decision

B3-01 was executed as an acquisition and supply verification exercise.

The current canonical environment does **not** contain a complete B_PIT_SECURITY_MASTER_RAW bundle.

Therefore:

```text
B3-01 acquisition
    = BLOCKED / NO COMPLETE RAW BUNDLE
```

This record does not grant DATA-01-C, DATA-02, A02 admission, cross-security epoch activation, or model selection.

## 2. Canonical baseline verified

Canonical `main` used for this adjudication:

```text
7aa4e333146ad29d3312a61e4c867b472e7a873f
```

The acquisition probe itself executed on a later canonical runtime head:

```text
08adaf484fee64f5448fafcfa8346403abac98a5
```

The distinction is intentional: the runtime head is evidence about an execution; it is **not** a replacement for the current-state authority of `main`.

The canonical source tree already contains the independent B preflight, delivery manifest template, evidence-supply contract, source matrix, free-first materializer, and corresponding GitHub Actions workflow.

The independent B preflight requires 11 PIT origins from 2023Q3 through 2026Q1 and six domains: identity, listing_delisting, common_equity, st_history, industry_history, source_vintages.

It additionally requires actual raw files, independently recomputed SHA-256, source reference, license / redistribution status, explicit knowledge basis, exact_bytes=true, and no retrieved_at to known_at substitution.

## 3. Latest runtime evidence

Latest A02 Exact Raw Materialization runtime independently inspected for this B3-01 follow-up:

- workflow run: 37596399460
- run number: 16
- runtime head: 08adaf484fee64f5448fafcfa8346403abac98a5
- artifact: 11471840025 / A02-exact-raw-37596399460
- artifact ZIP SHA-256: 5cad0c1dc67af0638ad4723ffb3a359f49f37b6f83c02a6860e4aea1ac58d0b1
- workflow conclusion: **failure / fail-closed**
- B raw preflight: **BLOCKED**
- strict independent preflight exit code: 4

The downloaded artifact contains:

```text
A02_RAW_MATERIALIZATION_RECEIPT.json
A_CSI800_RAW/official_000906_current_20261004_000906cons.xls
A_CSI800_RAW/official_000906_current_20261004_000906cons.xls.meta.json
GITHUB_RUN_CONTEXT.txt
SHA256_MANIFEST.txt
```

It contains **no** `DELIVERY_MANIFEST.json` and **no** `B_PIT_SECURITY_MASTER_RAW/` tree.

Independent verification of the transport artifact showed that the substantive listed file hashes match their actual bytes. The manifest's self-hash entry is inherently non-self-consistent after final write and is treated only as a transport-manifest limitation, not as B evidence.

The current `000906cons.xls` bytes are 169,984 bytes but have SHA-256:

```text
b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb
```

rather than the frozen historical target:

```text
f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984
```

Accordingly the A file is a **current snapshot**, not the historical A target.

## 4. Independent B preflight result

The canonical independent verifier was run against the downloaded runtime artifact using its own SHA-256 computation over the actual unpacked files.

Result:

```text
RC=4
status=BLOCKED
admission_status=NOT_ADMISSION
independent_from_collector=true
missing_domains=
  identity
  listing_delisting
  common_equity
  st_history
  industry_history
  source_vintages
finding:
  missing DELIVERY_MANIFEST.json
```

This is a genuine raw-byte-to-verifier result, not a producer-declared PASS.

## 5. Acquisition-path inspection

### Free-first materializer

`research/a02_b1b/materialize_free_pit.py` can capture current SSE/SZSE stock lists, current risk-warning pages, the official CSI industry taxonomy definition, and optional Baostock secondary material. Its own admission matrix leaves the historical B fields blocked or conditional.

It is therefore not a mechanism for manufacturing a PIT Security Master from current snapshots.

### Older raw acquisition runner

`research/a02_raw/acquire_raw_sources.py` can archive raw API responses through the Tushare path, but the current implementation explicitly records B as conditional raw only / blocked provenance because static listing metadata and industry/member material do not by themselves close the historical known_at chain.

Therefore a Tushare token alone does not satisfy B3-01.

### Persistent recovery policy

The persistent A02 recovery playbook defines two valid operational routes: a network-enabled environment that preserves exact raw responses and provenance, or a data-owner/vendor export containing raw bytes plus source-vintage / known_at evidence.

## 6. Current evidence inventory

The canonical repository contains B-side diagnostic/adjudication records, source registries, and preflight machinery, but no complete B raw bundle.

The latest A02 runtime artifact independently inspected also contains no B raw bundle.

No checksum, pointer, prior receipt, or secondary reconstruction is promoted to substitute for the missing bytes.

## 7. Required B3-01 handoff object

The next material input must conform to the existing contract:

```text
A02_DELIVERY/
└── B_PIT_SECURITY_MASTER_RAW/
    ├── identity/
    ├── listing_delisting/
    ├── common_equity/
    ├── st_history/
    ├── industry_history/
    └── source_vintages/
```

Every raw file must be bound to source_ref, source vintage / publication basis, known_at basis, effective interval, retrieved_at, license / redistribution status, size_bytes, sha256, and exact_bytes=true.

Where a vendor-PIT source is used, the delivery must preserve the query/export evidence needed to establish availability by the claimed cutoff. retrieved_at alone is insufficient.

## 8. Negative decisions

The following remain explicitly non-admissible:

- current stock lists;
- current exchange classification pages;
- current CSI taxonomy;
- old runtime artifacts;
- checksum or manifest declarations without corresponding bytes;
- secondary reconstructions;
- retrieved_at used as known_at;
- source pointers without underlying bytes.

## 9. Exit condition

B3-01 changes from BLOCKED only when an actual B raw bundle is physically supplied and can enter the canonical intake path.

Then:

```text
actual B raw bytes
        ↓
independent SHA-256 / inventory
        ↓
DATA-01-B raw preflight
        ↓
DATA-01-C independent verification
        ↓
DATA-02 PIT reconstruction
        ↓
A02 admission
```

Until that point:

```text
DATA-01-C             = NOT STARTED
DATA-02               = LOCKED
A02 admission         = BLOCKED
Cross-security epoch  = LOCKED
Model Selection       = LOCKED
```

## 10. B3-01 conclusion

**B3-01 is correctly BLOCKED at the evidence-supply boundary.**

The engineering side of the gate is ready. The remaining material dependency is the arrival of the actual historical B raw evidence package.

The next engineering action can be performed autonomously: on receipt of the bundle, immediately run the existing independent preflight against the actual bytes. No additional verifier design is needed merely to advance the gate.
