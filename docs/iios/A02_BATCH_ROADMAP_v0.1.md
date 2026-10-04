# IIOS A02 / M1.2 Batch Roadmap v0.1

Date: 2026-10-04

## Batch 0 — B2 foundation / state freeze — COMPLETE

Acceptance:
- Evidence Contract frozen
- Source Registry frozen
- PIT temporal semantics frozen
- exact-admission validator runnable
- CI green

Main evidence:
- B2 merge: `7d5ac91eb312e783d44316ec612d84f040457cf9`

## Batch 1 — A02 raw evidence acquisition / admission preparation — CURRENT

Two parallel workstreams:

### A. Exact historical CSI800 membership bytes
1. Preserve frozen target bytes/hash as immutable control.
2. Capture current official file only as a negative/control snapshot.
3. Probe legacy CSI URLs and public archives.
4. Accept only exact SHA-256 match.
5. On match, materialize immutable raw artifact + capture receipt.
6. Independent replay of the admitted bytes.

Current result:
- current 000906 file: 169,984 bytes, SHA `b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`
- frozen target: SHA `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`
- Wayback: no 2026 captures for tested URL variants
- Arquivo.pt: endpoint response was not machine-readable in runner
- Common Crawl: index reachable, but collection queries suffered 503/504/timeouts
- therefore A remains BLOCKED

### B. PIT Security Eligibility Evidence — free-first path
Required domains:
`identity/`, `listing_delisting/`, `common_equity/`, `st_history/`, `industry_history/`, `source_vintages/`

Execution order:
1. freeze free-first source matrix;
2. materialize public raw source responses/snapshots where legally and technically reproducible;
3. attach field-level publication/effective/known_at evidence;
4. derive per-security/per-origin eligibility;
5. fail closed on unresolved CSI-industry or known_at gaps.

Important:
- no paid source is mandatory;
- no Tushare token is a prerequisite;
- vendor APIs may remain optional cross-checks;
- current/latest data cannot be back-applied to prior origins.

Batch 1 acceptance:
- A exact historical target admitted;
- B PIT evidence covers all required fields for all 11 origins;
- independent replay produces identical origin universes;
- A02 admission = PASS.

## Batch 2 — A02 canonical PIT replay / independence — NEXT AFTER BATCH 1

1. Build canonical origin snapshots.
2. Replay 11 origin cutoffs.
3. Reconcile membership + eligibility.
4. Run independent verifier.
5. Freeze A02 manifest/replay outputs.
6. Unlock FM-02 / FM-03 only after PASS.

## Batch 3 — FM-02 / FM-03 state and forecast engine

1. Implement driver state engine.
2. Implement forecastability feature contract.
3. Bind PIT snapshot + provenance + immutable inputs.
4. Runtime fail-closed tests.
5. Freeze execution boundary.

## Batch 4 — Conditional backtest / model selection

1. Conditional backtest.
2. Sufficiency/statistical adequacy checks.
3. Research Plan -> Inner Selection -> Frozen Router -> Outer Evaluation.
4. Forecast model selection becomes frozen only after independent evaluation.
5. FM-05 scope freeze / FM-07 amendment gate.

## Batch 5 — Investment Core runtime migration / audit

1. Migrate B1 Decision Semantics into executable runtime.
2. Validate BUY/ADD/HOLD/REDUCE/EXIT/NO-BUY/WATCH/REVIEW_REQUIRED.
3. Bind Trust / Investability / Portfolio Constraint / ER / RR / MoS / Horizon.
4. Cross-module bypass red-team.
5. Independent audit.

Ordering invariant:
`A02 PASS -> FM02/FM03 -> conditional backtest/model selection -> runtime decision migration -> independent audit`

No downstream batch may silently bypass an upstream BLOCKED gate.
