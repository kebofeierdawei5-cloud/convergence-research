# CATL Existing Evidence Migration Audit — 2026-10-05

Status: CANDIDATE FOR ACCEPTANCE

## Scope

This batch migrates the already-existing case-bound CATL capture artifacts into the B2 Single-Company Evidence/PIT Manifest.

It does **not** create a new CATL historical-data acquisition platform, universe dataset, CSI800 dependency, or forecast-research dependency.

## Technical migration

Existing capture artifacts E001-E010 are preserved unchanged and bound to the B2 manifest by:

- case_id = `RC-CN-A-300750-20261004`;
- physical capture path;
- expected file size;
- expected SHA-256;
- Evidence Record content SHA-256;
- known_at / retrieved_at;
- Evidence field group.

The manifest must pass the B2 exact-byte verifier against the repository working tree and the PIT rule `known_at <= cutoff`.

## Source-quality audit

The technical migration status is independent of source authority.

| Evidence | Existing source | Assessment | Supplement |
|---|---|---|---|
| E001 | SZSE listing notice | Primary official source directly identified | None |
| E002 | Stockstar market-price page | Secondary dynamic market observation; not sufficient as canonical primary price evidence | **P0: obtain a reproducible first-party/free historical 2026-09-30 price observation** |
| E003 | CNINFO-hosted issuer disclosure | Public disclosure mirror; source content is an issuer announcement, but direct issuer/exchange capture is absent | **P1: supplement direct primary capture if this event is material to Trust/Governance gate** |
| E007 | CNINFO-hosted issuer disclosure | Same primary-source gap as E003 | **P1: supplement direct primary capture if this event is material to Trust/Governance gate** |
| E004-E006 | CNINFO-hosted 2026 H1 issuer report | Public issuer-report mirror; retained as existing evidence, with authority classified by current registry | No immediate re-acquisition; direct primary copy is a provenance enhancement |
| E008-E010 | CNINFO-hosted issuer disclosures | Public issuer-report mirror; retained for migration and historical anchoring | No immediate re-acquisition unless a downstream material claim requires direct-primary proof |

## Decision-grade boundary

The B2 migration can establish that the existing capture artifacts are:

- case-bound;
- physically present;
- hash-verifiable;
- PIT-valid.

It does **not** upgrade E002 from secondary market data into primary market evidence.

Therefore:

```
B2 technical Evidence admission
        PASS
              +
source-quality audit
        PARTIAL
              ↓
decision-grade price evidence
        BLOCKED until E002 primary gap closes
```

This prevents the historical CORE-03 secondary price source from silently becoming canonical decision evidence.

## Next narrow action

Only supplement the identified material first-party gaps. Do not build CSI800, CSI Industry, full-market PIT Security Master, or a new company-wide historical database for this case.
