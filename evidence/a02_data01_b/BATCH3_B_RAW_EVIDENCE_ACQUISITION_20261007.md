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

Canonical main at B3-01 start:

```text
08adaf484fee64f5448fafcfa8346403abac98a5
```

The canonical source tree already contains the independent B preflight, delivery manifest template, evidence-supply contract, source matrix, free-first materializer, and corresponding GitHub Actions workflow.

The independent B preflight requires 11 PIT origins from 2023Q3 through 2026Q1 and six domains: identity, listing_delisting, common_equity, st_history, industry_history, source_vintages.

It additionally requires actual raw files, independently recomputed SHA-256, source reference, license / redistribution status, explicit knowledge basis, exact_bytes=true, and no retrieved_at to known_at substitution.

## 3. Latest runtime evidence

Latest canonical Batch-3 runtime probe recorded in the project state:

- workflow run: 37595133874
- artifact: 11469743020
- artifact SHA-256: cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49
- B raw preflight: **BLOCKED**
- exit code: 4

The artifact did not contain DELIVERY_MANIFEST.json or a complete B_PIT_SECURITY_MASTER_RAW tree. This is consistent with the independent B preflight semantics and does not create admission evidence.

## 4. Acquisition-path inspection

### Free-first materializer

research/a02_b1b/materialize_free_pit.py was inspected. It can capture current SSE/SZSE stock lists, current risk-warning pages, the official CSI industry taxonomy definition, and optional Baostock secondary material. Its own admission matrix leaves the historical B fields blocked or conditional. It is therefore not a mechanism for manufacturing a PIT Security Master from current snapshots.

### Older raw acquisition runner

research/a02_raw/acquire_raw_sources.py was inspected. Its Tushare path can archive raw API responses, but the current implementation explicitly records B as conditional raw only / blocked provenance because static listing metadata and industry/member material do not by themselves close the historical known_at chain.

Therefore a Tushare token alone does not automatically satisfy B3-01.

### Persistent recovery policy

The persistent A02 recovery playbook defines two valid operational routes: a network-enabled environment that preserves exact raw responses and provenance, or a data-owner/vendor export containing raw bytes plus source-vintage / known_at evidence.

## 5. Current evidence inventory

The canonical repository contains B-side diagnostic/adjudication records, source registries, and preflight machinery, but no complete B raw bundle. Persistent Library search likewise surfaced prior receipts, adjudications, and recovery documents, not a complete B raw delivery.

## 6. Required B3-01 handoff object

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

## 7. Negative decisions

The following were deliberately not promoted to B raw evidence:

- current stock lists;
- current exchange classification pages;
- current CSI taxonomy;
- old Run #2 / Run #3 artifacts;
- checksum or manifest declarations without corresponding bytes;
- secondary reconstructions;
- retrieved_at used as known_at;
- source pointers without underlying bytes.

## 8. Exit condition

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

## 9. B3-01 conclusion

**B3-01 is correctly BLOCKED at the evidence-supply boundary.**

The engineering side of the gate is ready. The remaining work is not another verifier or another declaration; it is the arrival of the actual historical B raw evidence package.