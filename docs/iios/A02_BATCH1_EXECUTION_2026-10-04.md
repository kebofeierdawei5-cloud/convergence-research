# A02 Batch 1 Execution Record — 2026-10-04

## Batch status

Batch 1 = **IN PROGRESS / BLOCKED_AT_ADMISSION**

### Completed in this batch

- A02 batch roadmap committed.
- Free-first source capability matrix committed.
- Vendor credential semantics corrected: Tushare token is optional, not a mandatory A02 dependency.
- Historical archive recovery expanded to legacy CSI URL variants, Arquivo.pt and Common Crawl.
- Common Crawl search window narrowed around the historical target period.
- Exact historical target hash remains immutable.

### Evidence from latest runs

Latest A02 recovery run:
- run: `37202689524`
- head: `8339ff0927e0b177233248467158c6200ee3ed21`
- workflow: `A02 Exact Raw Materialization`

Prior archive recovery run:
- run: `37199983353`
- Wayback: 4 tested URL variants, 0 captures.
- Arquivo.pt: runner received non-JSON responses and therefore obtained no usable capture.
- Common Crawl: 2026 collection index was reachable; record queries encountered 503/504/timeouts. No exact frozen bytes recovered.

Current official 000906 control snapshot:
- size: 169,984 bytes
- SHA-256: `b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`
- role: current snapshot only; never a substitute for frozen historical target.

Frozen historical target:
- size: 169,984 bytes
- SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`

### B free-first rule

The latest source matrix explicitly requires:
- no paid source as a mandatory dependency;
- no Tushare token as a prerequisite;
- field-level provenance;
- publication/effective/known_at separation;
- CSI Industry remains a hard-lock normative field;
- secondary public datasets may assist reconciliation but cannot silently become the normative source.

### Batch 1 exit criteria

A02 can transition to PASS only after:
1. exact historical A bytes are materialized and independently hashed to the frozen target;
2. B raw evidence covers identity, listing/delisting, common equity, ST, CSI Industry and source-vintage/known_at across all 11 origins;
3. canonical origin replay is deterministic;
4. independent verification reproduces the same result.

Until then:
- A02 = BLOCKED
- FM-02 / FM-03 remain locked
- no forecast model selection
- no downstream backtest is allowed to bypass A02.

## Next execution inside Batch 1

The next concrete task is **B-01 Free-First Raw Evidence Materialization**:
- acquire public raw evidence for listing/delisting, ST and identity/common-equity fields;
- identify a reproducible free route for CSI Industry historical states;
- preserve raw response bytes + metadata;
- assign `known_at` only where source evidence actually supports it;
- produce field-level admission results.

A exact-byte recovery remains a parallel, independent workstream.
