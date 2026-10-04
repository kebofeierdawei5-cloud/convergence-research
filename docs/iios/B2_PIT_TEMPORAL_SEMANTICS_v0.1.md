# IIOS B2 — PIT Temporal Semantics v0.1

Status: FROZEN
Date: 2026-10-04
Timezone: +08:00

## 1. Canonical dimensions

IIOS distinguishes:

```text
published_at
known_at
retrieved_at
effective_from
effective_to
```

`published_at` is the source publication time when directly evidenced.
`known_at` is the earliest defensible time the fact was available to the research process under the admitted source basis.
`retrieved_at` is the time IIOS obtained the source bytes or response.
`effective_from` and `effective_to` define the economic, legal, index or eligibility interval.

These dimensions are independent.

## 2. Historical cutoff

For A02 origin T:

```text
origin_cutoff = quarter-end 23:59:59 +08:00
```

Canonical PIT knowledge condition:

```text
known_at <= origin_cutoff
```

Canonical effective-interval condition:

```text
effective_from <= origin_cutoff
AND
(effective_to IS NULL OR origin_cutoff < effective_to)
```

When both are required, both must pass.

## 3. Retrieval-time rule

`retrieved_at > origin_cutoff` is allowed when the source independently proves that the fact was already knowable.

`known_at > origin_cutoff` fails PIT.

Acquisition date therefore cannot be used as a proxy for historical availability.

## 4. Publication vs knowledge

When publication is the evidence basis, `published_at <= known_at` is expected unless a source-specific rule establishes an earlier knowledge channel.

When no defensible `known_at` can be established, provenance is `UNKNOWN`.

## 5. Revision rule

Historical evidence is append-only.

A later source revision cannot silently rewrite an earlier evidence record. Each source vintage or revision receives a distinct evidence identity.

For deterministic derivations:

```text
known_at(derived) = max(known_at(parent_1), ..., known_at(parent_n))
```

unless a stricter frozen transformation rule applies.

## 6. Membership and eligibility

For historical universe records, applicable tests are explicit:

```text
CSI800_MEMBER
AND common_equity
AND listed_at_origin
AND NOT ST_AT_ORIGIN
AND NOT FINANCIAL
```

Membership uses effective intervals AND PIT knowledge qualification.
Listing uses the historical listing interval.
Industry exclusion uses the historical industry interval.
ST exclusion uses evidence-backed historical status/event intervals.

No current name, current industry, current ST flag, current listing state or current index membership may be back-applied.

## 7. Conflict

Same-key / same-cutoff conflicts are resolved only through stronger admissible evidence.
Otherwise the result is `UNKNOWN`.

No majority vote and no current-state tie-breaker are permitted.

## 8. Price observation

For a historical market-price observation, `observed_at` identifies the economic observation time and `known_at` identifies availability to the research process.

Both must satisfy the consuming PIT requirement. An end-of-day timestamp is not assumed to establish availability at the close without a source rule.

## 9. Failure closure

The following MUST block the affected historical permission:

```text
missing known_at
future known_at
unresolved source conflict
missing source identity
hash mismatch
current-state substitution
incomplete derivation lineage
```

B2 therefore treats PIT as an executable temporal qualification, not as a field-level annotation.