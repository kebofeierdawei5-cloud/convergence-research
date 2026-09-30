# IIOS Project State Index

Snapshot: 2026-09-30

## Current canonical engineering state

```text
G2 R10 Reference Governance Runtime = FROZEN
        ↓
M1.2 Forecast Validation = ACTIVE
        ↓
FM-00 Exploratory Research Epoch = PASS
        ↓
FM-01 Driver History Foundation = NEXT
```

## Authority / continuity

1. Git repository: source, contracts, tests, ADRs, changelog, state indexes.
2. Frozen governance artifact identity + evidence: `governance/g2-r10-reference/`.
3. Research-control artifacts: `research/`.
4. Long-term compact memory: `IIOS_LONG_TERM_MEMORY_2026-09-30.md`.
5. Chat history is context only, not authoritative project state.

## Immutable boundary

G2 frozen bytes are not modified by M1.2 research development. Governance changes require a successor candidate and a new freeze chain.

## Active research boundary

FM-00 is exploratory and contaminated by prior exposed M1.0/M1.1 results. It cannot produce clean confirmatory evidence or authorize a production router.

## Next development task

`M1.2-FM-01 | Driver History Foundation`

Build a deterministic PIT-aware `DriverSeries` layer from available historical Reality, preserving `known_at`, `published_at`, revisions, provenance, and quality semantics.
