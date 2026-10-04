# IIOS B2 — Acceptance Matrix v0.1

Status: CANDIDATE — implementation gate
Date: 2026-10-04

| Gate | Required condition | Current status |
|---|---|---|
| Evidence contract | Machine-readable schema + executable validator | PASS |
| Source registry | Free-first registry with paid data non-mandatory | PASS |
| PIT semantics | known_at / published_at / retrieved_at / effective intervals separated | PASS |
| A02 Object A terminal exact bytes | 000906cons.xls size/hash independently recomputed | BLOCKED |
| A02 Object A historical coverage | All 11 origins backed by admissible historical evidence | BLOCKED |
| A02 Object B PIT Security Master | Exact raw bundle + source-vintage knowledge provenance | BLOCKED |
| A02 overall admission | A + B independently pass | BLOCKED |

## Evidence boundary

Existing A02 v0.3 candidate material already defines the required raw acquisition and provenance envelope. This B2 layer freezes the cross-cutting evidence semantics without silently changing the A02 candidate contract.

## Current real-data result

The 2026-10-04 execution did not materialize the exact `000906cons.xls` bytes. The previously declared size/hash therefore remain validation targets only. No exact PIT security-master raw bundle was found in the accessible Library or current repository.

## Exit criterion

Do not mark B2/A02 PASS until:

```text
raw bytes physically present
-> SHA-256 recomputed
-> source capture receipt
-> PIT knowledge evidence
-> independent capture preflight
-> historical membership coverage
-> PIT Security Master coverage
-> A02 admission PASS
```