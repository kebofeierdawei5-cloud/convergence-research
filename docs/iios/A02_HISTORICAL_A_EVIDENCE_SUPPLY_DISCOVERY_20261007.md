# A02 Historical A Evidence Supply Discovery — 2026-10-07

Status: DIAGNOSTIC / CANONICAL FINDING
Universe: `OU-M12-A02-CSI800-NONFIN-PIT-001`

## New finding

A historical predecessor repository (`benzemaer/convergence-research`) contains a tracked G0-T02 handoff manifest for a **previously materialized** CSI800 official snapshot package.

The tracked manifest identifies:

- snapshot: `CSINDEX_000906_20260703T100909Z`
- document: `000906cons.xls`
- effective date: `2026-06-12`
- retrieval timestamp: `2026-07-03T10:09:21.8572846Z`
- package size: `373560` bytes
- package SHA-256: `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`
- constituent file size: `169984` bytes
- constituent file SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`

The same manifest records the official constituent source as:

`https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000906cons.xls`

and records the official rebalance announcement as publication 2026-05-29 with effectiveness after market close on 2026-06-12.

## Critical limitation

The package itself is explicitly documented by the predecessor repository as **local non-Git review material**. The current public Git object contains the manifest and hashes, but not the binary XLS or ZIP package.

Therefore:

- the historical exact A bytes are **not currently admitted** into A02;
- the hash declaration is **not** treated as independent byte verification;
- the predecessor manifest is **provenance/recovery-path evidence only**;
- no historical membership rows are materialized from this declaration.

## B finding

The predecessor repository contains security-master provider contracts and Tushare/tnskhdata candidate materialization code, but no directly materializable PIT raw bundle establishing all A02-required domains with field-level historical `known_at` evidence.

Required B domains remain:

`identity`, `listing_delisting`, `common_equity`, `st_history`, `industry_history`, `source_vintages`.

## Operational effect

```
A historical exact bytes      = NOT MATERIALIZED
B PIT raw bundle              = NOT MATERIALIZED
A02 admission                 = BLOCKED
cross-security/model select  = LOCKED
```

This finding does not change FM02/FM03/FM04/FM05/FM07 semantics, current research-epoch status, or any investment capability.
