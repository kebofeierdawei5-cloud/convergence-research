# IIOS B2 — Evidence Contract v0.1

Status: FROZEN / ENGINEERING BASELINE
Date: 2026-10-04
Scope: Data / Evidence / PIT Foundation
Investment Core dependency: none. A02/CSI800 is a separate Research Track adapter.

## Task Contract

### Objective
Define the authoritative evidence object used by IIOS between raw source capture and normalized investment facts.

### User Value
Every material investment input must be traceable to exact source bytes, source identity, temporal availability, provenance and deterministic transformation.

### Product Surface
- schemas/evidence_record_v0.1.schema.json
- schemas/source_registry_v0.1.schema.json
- schemas/pit_temporal_semantics_v0.1.schema.json
- research/b2/

### Test / Acceptance
- Evidence cannot be admitted without source identity and exact-byte provenance when the source is byte-addressable.
- known_at is distinct from retrieved_at, published_at, effective_from, and effective_to.
- PIT qualification uses known_at <= cutoff; effective interval qualification is a separate test.
- Missing, stale, conflicting or unverifiable evidence fails closed to the affected permission.
- Derived facts retain parent evidence lineage and transformation identity.
- No current-state value is silently back-applied to historical cutoffs.
- Exact raw-byte admission is independently hashable and replayable.

### Out of Scope
- Company Quality scoring.
- Independent Forecast.
- Valuation construction.
- Market Implied Expectation.
- Any paid data subscription as a mandatory dependency.

## 1. Canonical Evidence Object

An Evidence Record represents one defensible observation or claim, not merely a number copied from a provider.

Minimum identity:
```text
evidence_id
subject_id
field_id
claim_type
```

Minimum temporal fields:
```text
observation_date / period
published_at
known_at
retrieved_at
effective_from
effective_to
```

Minimum provenance:
```text
source_ref
source_version
source_locator
artifact_id
content_sha256
```

For byte-addressable source material, artifact_id + content_sha256 + exact_bytes=true form the source-integrity anchor.

## 2. Evidence Classes

Allowed provenance classes:
```text
SOURCE_VINTAGE_VERIFIED
EVENT_PUBLICATION_VERIFIED
VENDOR_PIT_QUERY
DERIVED_FROM_ADMITTED_RAW
UNKNOWN
```

- SOURCE_VINTAGE_VERIFIED: exact historical source vintage establishes the fact/time basis.
- EVENT_PUBLICATION_VERIFIED: a contemporaneous publication/event establishes what became knowable.
- VENDOR_PIT_QUERY: the provider explicitly supports historical cutoff querying and the exact request/response is preserved; this is provider-dependent and weaker than source-vintage evidence.
- DERIVED_FROM_ADMITTED_RAW: deterministic transformation from admitted raw evidence; formula/code identity and all parents are mandatory.
- UNKNOWN: the available evidence does not support a defensible PIT conclusion.

Agreement between two weak sources does not upgrade provenance.

## 3. Temporal Semantics

The time dimensions are independent:
```text
published_at   = public/provider publication time, when evidenced
known_at       = earliest defensible availability to the research process
retrieved_at   = time IIOS obtained the bytes
effective_from = economic/index/legal start of effect
effective_to   = economic/index/legal end of effect
```

Normative knowledge rule:
```text
PIT_QUALIFIED(e, cutoff) iff known_at(e) <= cutoff
```

For interval-valued facts:
```text
EFFECTIVE_QUALIFIED(e, cutoff) iff
    effective_from(e) <= cutoff
    AND
    (effective_to(e) is null OR cutoff < effective_to(e))
```

A fact that passes one dimension but fails the other is not PIT-qualified for a use case requiring both.

retrieved_at MUST NEVER substitute for known_at.

## 4. Observation vs Knowledge

A historical observation can be collected today and still be PIT-qualified only when its underlying fact is independently shown to have been knowable by the historical cutoff.

Therefore retrieved_at > cutoff is allowed when the source independently proves the fact was already knowable.

known_at > cutoff is not PIT-qualified.

A source that only exposes a current value, even when it returns historical dates, is classified as current reconstruction unless the historical knowledge/vintage basis is separately evidenced.

## 5. Revision Semantics

Evidence is append-only.

A later source revision MUST produce a new evidence identity/version rather than mutating an older observation.

For a deterministic derived value:
```text
known_at(derived) = max(known_at(parent_i))
```
unless a stricter source-specific rule is explicitly frozen.

A derived value cannot become PIT-qualified before all required parents are PIT-qualified.

## 6. Conflict Semantics

When two sources disagree about the same fact at the same cutoff:
```text
stronger admissible evidence -> resolve
otherwise -> UNKNOWN
```

Forbidden:
```text
majority vote
newest-value wins
current-value backfill
model-preferred value
missing-value imputation
```

An unresolved material conflict MUST close the affected permission.

## 7. Raw / Evidence / Fact / Metric Boundary

```text
Raw Artifact
   -> Evidence Record
   -> Normalized Fact
   -> Derived Metric
   -> Forecast / Valuation / Decision
```

A downstream object must not become its own evidence source.

## 8. B2 Fail-Closed Rule

If a required material input is missing, stale beyond its allowed cutoff, conflicting and unresolved, source identity missing, exact bytes unavailable where required, hash mismatch, known_at unverifiable, or transformation lineage incomplete, the affected permission is BLOCKED / UNKNOWN / REVIEW_REQUIRED according to the consuming contract.

The system MUST NOT manufacture a PASS by substituting a weaker or current source.

## 9. Single-company Investment Core binding

The Evidence Contract is directly consumable by a user-selected A-share or Hong Kong company case. The minimum company evidence envelope is defined by B2-A and does not require universe construction, CSI800 history or a PIT Security Master.

## 10. A02 Binding

A02 Object A and Object B must both pass their own exact-capture and provenance requirements before:
```text
A02_ADMISSION_PASS
-> FM-02 cross-security parameterization
-> FM-03 cross-security parameterization
-> A02 FM-04/FM-05/FM-06
-> model selection
```

The B2 Evidence Contract does not lower or replace the existing A02 v0.3 provenance requirements.