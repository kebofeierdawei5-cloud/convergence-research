# IIOS M1.2-FM-01 — Driver History Foundation v0.1

## Task Contract

### Objective
Build a deterministic, point-in-time-safe `DriverSeries` foundation that preserves quarterly observations, publication/knowledge timing, revisions, provenance, derivation lineage and data-quality state.

### User Value
Create the reusable historical driver layer required by FM-02 Feature Builder without silently mixing current knowledge, revisions, derived values or unverified data.

### Product Surface
`research/fm01/` — schema, deterministic resolver/validator, dataset manifest and adversarial tests.

### Test / Acceptance
- Schema validation is deterministic.
- `known_at` never precedes `published_at`.
- Direct observations cannot masquerade as derived observations and vice versa.
- Derived observations require explicit parent records and formula metadata.
- Same PIT snapshot conflicts fail closed.
- Future-known records are excluded from historical cutoff resolution.
- Missing records resolve to `UNKNOWN`, not an imputed value.
- Resolution is deterministic and replayable.
- No fabricated CATL observations are accepted.

### Out of Scope
- FM-02 Feature Builder.
- State Engine.
- Model selection / router logic.
- Production data-provider integration.
- Reconstructing unavailable M1.1 exact source bytes from memory or inference.

## Data ingress status

The implementation is ready, but the CATL production-history population gate is intentionally `BLOCKED_DATA_INGRESS` because the exact M1.1 historical source snapshot is not present in the FM-00 Git baseline. This is a data-lineage blocker, not permission to invent replacement values.
