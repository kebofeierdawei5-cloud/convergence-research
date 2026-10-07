# M1.2-DATA-01 — A02 Evidence Supply & Free-First Materialization v0.1

Status: CANDIDATE / ENGINEERING-ONLY
Universe: `OU-M12-A02-CSI800-NONFIN-PIT-001`

## Purpose

This batch creates the first executable evidence-supply boundary for A02.

It does **not** admit A02. It does not modify FM-02/FM-03, FM-04/FM-05/FM-06, model-selection semantics, the six state dimensions, the forecast metrics, or the closed M1.2 epoch.

The boundary is:

```
real external raw evidence
    ↓
immutable delivery bundle
    ↓
independent raw-byte preflight
    ↓
PIT reconstruction (later batch)
    ↓
A02 admission (later batch)
```

## Required delivery objects

### A — CSI800 historical membership evidence

The delivery may contain:

- exact official `000906cons.xls`;
- historical CSI800 official rebalance snapshots / adjustment notices;
- where explicitly permitted by the frozen contract, official CSI300 + CSI500 historical source files sufficient for deterministic CSI800 reconstruction.

Terminal control target:

- file: `000906cons.xls`
- expected size: 169984 bytes
- expected SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`

The expected hash is a validation target only. It becomes evidence only when the corresponding bytes are physically present and independently hashed.

Minimum membership states:

`2023-06, 2023-12, 2024-06, 2024-12, 2025-06, 2025-12, 2026-06`

Each state must reference an actual raw file and source-vintage/publication basis in the delivery metadata.

### B — PIT Security Eligibility Evidence

Required domains:

`identity, listing_delisting, common_equity, st_history, industry_history, source_vintages`

The raw bundle must contain actual source bytes, not only normalized parquet/CSV output.

Each B record must declare:

- source reference;
- raw path;
- SHA-256 / file size;
- retrieval time;
- publication/source-vintage basis where available;
- effective interval semantics;
- known-at basis;
- license / redistribution status.

`retrieved_at` is never a substitute for `known_at`.

## Free-first rule

No paid commercial source is required.

Tushare and other vendors are optional reconciliation or acquisition aids only. A02 must remain capable of reaching its admission gate without making a paid vendor or private credential an architectural prerequisite.

A free source is not automatically admissible; authority, raw bytes, temporal provenance and PIT visibility are evaluated per field.

## Intake interface

The canonical delivery layout is:

```
A02_DELIVERY/
├── DELIVERY_MANIFEST.json
├── A_CSI800_RAW/
│   ├── official/
│   ├── rebalance/
│   ├── interim_adjustments/
│   ├── announcements/
│   └── receipts/
├── B_PIT_SECURITY_MASTER_RAW/
│   ├── identity/
│   ├── listing_delisting/
│   ├── common_equity/
│   ├── ST_history/
│   ├── industry_history/
│   ├── namechange/
│   └── source_vintages/
└── provenance/
```

The independent verifier is deliberately separate from the collector. A collector-generated receipt cannot certify itself.

## Preflight result semantics

- `PASS_RAW_COMPLETE`: exact A terminal bytes match and A/B raw structural coverage is complete enough to proceed to PIT reconstruction.
- `BLOCKED`: one or more required raw objects are missing, mismatched, or structurally unprovable.
- `NOT_ADMISSION`: every preflight PASS is still only a raw-evidence readiness result; A02 PIT admission remains a later gate.

The verifier MUST NOT:

- infer historical membership from a current 000906 snapshot;
- infer `known_at` from `retrieved_at`;
- synthesize missing bytes from a checksum;
- convert secondary datasets into normative CSI evidence;
- claim A02 admission.

## Next batches

`DATA-01-A` Historical A intake
→ `DATA-01-B` B free-first raw intake
→ `DATA-01-C` independent raw verification
→ `DATA-02` PIT reconstruction
→ `DATA-03` independent replay
→ `DATA-04` A02 admission.

Downstream cross-security forecast work remains locked until A02 admission.
