# B2 / A02 Development Status — 2026-10-04

> **CORE-00 scope classification:** this document is **Research Track only**. A02 remains independently recoverable work and is **not an Investment Core dependency or release gate**. B2 evidence/PIT semantics remain reusable for company-specific cases; the historical-universe/A02 application does not.

## Frozen baseline

- B2 Evidence Contract + Source Registry + PIT Temporal Semantics: merged to `main`.
- B2 merge commit: `7d5ac91eb312e783d44316ec612d84f040457cf9`.
- A02 historical target remains immutable:
  - `000906cons.xls`
  - expected size: 169,984 bytes
  - expected SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`
  - historical package target: `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`

## Current verified materialization

The official CSI endpoint was reached successfully by the GitHub Actions acquisition bridge. The retrieved current file is exactly 169,984 bytes but has SHA-256:

`b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`

Therefore it is a current snapshot only and MUST NOT be admitted as the frozen historical target.

## Historical recovery

- Direct historical recovery was wired into `research/a02_raw/acquire_raw_sources.py`.
- Current recovery checks the Internet Archive for the current CSI URL.
- No exact historical target bytes have been recovered yet.
- The old G0 evidence establishes that the frozen historical object existed and was independently recomputed/approved, but the raw package was local-only and is not present in the current Git tree/releases.

## B security-master status

No exact PIT Security Eligibility/Master raw bundle has been materialized in the current runtime.

Required raw domains remain:

`identity/`, `listing_delisting/`, `common_equity/`, `st_history/`, `industry_history/`, `source_vintages/` (plus `namechange/` only if required).

Current bridge logic deliberately fails closed because static security-master snapshots and derived industry effective intervals do not by themselves establish PIT `known_at` provenance.

## Admission state

A02 remains:

`BLOCKED`

because both exact historical A bytes and a complete PIT B evidence chain are not yet admitted.

## Next recovery action

Continue historical A recovery across legacy CSI URL variants / public archives, accepting bytes only on exact SHA-256 match. In parallel, pursue materialization of the complete B raw PIT bundle. No substitution by current data is permitted.
