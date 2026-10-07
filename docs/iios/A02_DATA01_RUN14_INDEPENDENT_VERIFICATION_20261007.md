# M1.2 DATA-01-A — Run #14 Independent Runtime Evidence

Date: 2026-10-07
Status: DIAGNOSTIC / CANONICAL STATE EVIDENCE
Universe: `OU-M12-A02-CSI800-NONFIN-PIT-001`

## 1. Runtime artifact identity

- Workflow: `A02 Exact Raw Materialization`
- Run: `37590889419`
- Job: `112691834326`
- Run head: `ba9eadb852de65bbdca3dded0ed7ac6e6378f06e`
- Artifact ID: `11468960920`
- Artifact name: `A02-exact-raw-37590889419`
- Artifact size: `197114` bytes
- GitHub artifact digest: `bdfff9342c848f3231127c4ee581829e275b29a7dcbbeab1e0b3501bb04e70de`
- Independently recomputed ZIP SHA-256: `bdfff9342c848f3231127c4ee581829e275b29a7dcbbeab1e0b3501bb04e70de`

Artifact integrity therefore = `PASS`.

## 2. Exact A result

The artifact contains a real 169,984-byte `000906cons.xls` response.

- path: `A_CSI800_RAW/official_000906_current_20261004_000906cons.xls`
- observed SHA-256: `b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`
- expected historical target SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`
- size match: `TRUE`
- SHA-256 match: `FALSE`
- exact bytes: `TRUE`
- role: `CURRENT_SNAPSHOT_NOT_HISTORICAL_TARGET`

Conclusion: the run captured exact current official bytes, but not the required historical terminal snapshot. This does not satisfy DATA-01-A historical exact-byte admission.

## 3. Historical recovery result

The same receipt records no accepted historical bytes from the tested archive routes.

Observed route outcomes include:
- Wayback CDX: zero captures / service-unavailable responses;
- Wayback Availability: no snapshot at the tested target timestamp;
- Memento: DNS resolution failure;
- Arquivo.pt: unusable response;
- Common Crawl: no usable target capture.

The predecessor G0-T02 manifest remains only a recovery/provenance lead because its historical ZIP/XLS bytes were explicitly outside Git and are not present in the accessible Library.

## 4. B result in the same runtime

- B raw bundle: `NOT MATERIALIZED`
- `pit_admission`: `BLOCKED_FREE_FIRST_ROUTE_NOT_MATERIALIZED`
- Tushare credential: not configured

No B evidence is promoted by this artifact.

## 5. Admission consequence

```text
artifact integrity              = PASS
A exact historical bytes        = BLOCKED
B PIT raw bundle                = BLOCKED
A02 admission                   = BLOCKED
PIT reconstruction              = LOCKED
independent replay              = LOCKED
model selection                 = LOCKED
```

## 6. Integrity boundary

This record is an independent verification of a GitHub Actions runtime artifact and its contained byte hashes. It does not promote a declared checksum into evidence, does not treat current data as historical PIT data, and does not self-certify A02 admission.