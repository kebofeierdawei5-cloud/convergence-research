# IIOS Project Status

State classification: **CANONICAL SUMMARY**
Date: 2026-10-10

Authoritative current-state record:
`docs/PROJECT_STATE_INDEX.md`

## Latest P0 status — 2026-10-10

P0 Batch B3 is merged in PR [#276](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/276), merge commit `d3582621918b285f29b4573c2618c1072247885c`. Formal Decision Revision, Publication and Report writers now revalidate persisted upstream admissions and fail closed when those bytes are missing.

P0 C1 source adjudication PR [#278](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/278) is also merged (`1e574438a255c350905c1575a13a691078fe27b8`). The real Attempt 10 artifact was independently re-hashed (12/12) and passed to the unchanged B2/PIT validator. Six of seven evidence groups are now covered; `market_price` remains UNKNOWN because the 2026-10-09 CNY 20.28 secondary close candidate still lacks admitted underlying-source authority/reuse. The date-only cutoff has not been reinterpreted; the 2026-10-09 evening meeting disclosure remains excluded, with a pre-cutoff official disclosure covering corporate_disclosures.

**Production P0-LLM-001 / P0-LLM-004 remain OPEN.** There is still no deployed production-host run proving a genuine company semantic/Forecast/Valuation chain, Decision Revision, publication/report and complete Run Receipt replay with independent red-team. Follow `docs/PROJECT_STATE_INDEX.md` for the active next boundary.


This file is a concise human-readable summary. When it conflicts with the Current State Index, the Current State Index wins.

## Current stage

**Current canonical M1.2 status: New Research Epoch Design Proposal = CANONICAL DESIGN / NOT ACTIVATED**

C8 and all prior Stage C productization milestones remain canonical.

Authority hardening is complete through:

```
B02 → B03-B → B04-B → independent post-B04 re-audit
```

M1.2 baseline progression:

```
FM00 Git Baseline = PASS
        ↓
FM01 exact M1.1 source admission = PASS
        ↓
FM01 DATA_READY
        ↓
FM02 PIT feature builder / feature contract = PASS
        ↓
FM03 State Engine / Forecastability State Construction = PASS
        ↓
FM04 Conditional Backtest = PASS
        ↓
FM05 Scope / Estimand / Sufficiency Freeze = PASS
        ↓
FM04 Conditional Backtest = PASS
```

FM02 feature merge commit:
`ade3541302eb6f3fa43ec8aac76540820000a727`

Baseline:
- PR #136 = MERGED;
- exact FM00 source anchor = `536e883bc873dbe7dd7383690a7a95a0f65591a7`;
- immutable tag `m1.2-fm00-v0.1.0`;
- baseline workflow #6 = SUCCESS on exact PR head `ff6bfe0ff7677d0a965af513ac2ee644413565d1`.

G2 historical frozen identity remains separate from the accepted R0 successor evidence; no frozen-byte rewrite was performed.

**Next boundary: A02 B-01 Free-First Raw Evidence Materialization, required before activating the recommended cross-sectional successor epoch.**

FM01 data gate is now `DATA_READY` after exact-source admission, provenance binding, 22-quarter coverage validation, and independent PIT replay.

Admitted CATL scope: 300750.SZ, 2021Q1–2026Q2, 22 quarters, 44 DriverSeries records for REVENUE / NET_PROFIT.

No FM01 numeric data were fabricated, inferred, or reconstructed from memory.

FM02 is now PASS / MERGED / CANONICAL as a feature-construction research capability. It remains separately gated from confirmatory model selection by M1.2 research governance, State / UNKNOWN semantics, conditional backtest, partitioning, sealed-manifest and blind-scoring controls.

FM02 acceptance:
- PR #144;
- merge commit `ade3541302eb6f3fa43ec8aac76540820000a727`;
- final pre-merge head `617c9b8a3f091e76d5ea44a39e963ff255ffd99b`;
- remote CI run #15 = SUCCESS;
- 13 / 13 FM02 unit tests passed;
- generated feature snapshot = 22 rows (11 origins × 2 drivers);
- canonical feature-row content hash `3803be1404255652b831627fcd32acaf203f8984da33f70d3784e28dc449b9da`;
- generated snapshot schema validation = PASS;
- independent PIT provenance audit = PASS.

Acceptance: `docs/iios/FM02_ACCEPTANCE_2026-10-07.md`.

FM02 does not authorize State Engine, Conditional Backtest, confirmatory model selection, production router, current-price inputs, scheduler, alerts, or automatic execution.
FM03 acceptance:
- PR #147;
- merge commit `007ac477f7e45664c6eb7d4681de5d92c3a16b11`;
- accepted pre-merge head `276d37111c0866ef7a0e69b7ab38aa1e4e1d2788`;
- dedicated Actions run #2 = SUCCESS;
- 14 / 14 FM03 tests passed;
- generated state snapshot = 22 rows (11 frozen origins × 2 drivers);
- canonical state-row content hash `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- independent PIT/provenance audit, output schema validation, compileall, and diff-check = PASS;
- `confirmatory_eligible=false`, principal `iios_research`, grant `m1.2.fm03.state_engine`.

FM03 preserves PIT visibility, explicit UNKNOWN propagation without imputation, provenance closure to FM02 / DriverSeries, the hash-bound frozen origin schedule, and fail-closed capability isolation. It uses deterministic non-tuned state mappings only and does not authorize Conditional Backtest, Model Selection, Production Router, or Automatic Execution.

Acceptance: `docs/iios/FM03_ACCEPTANCE_2026-10-07.md`.


RP-01 remains a separate legacy fixture regression and is not M1.2 baseline acceptance evidence.


## Canonical Investment Core

```
Reality
→ Quality / Thesis / Value Driver
→ Primary Valuation
→ Independent Forecast
→ Return H
→ Risk
→ Portfolio
→ Optional MIE
→ Decision
```

The production Decision Kernel is merged and the real 300750 chain has passed E2E.

## 300750 accepted result

- Price: 291.11 CNY/share
- Quality: CONDITIONAL
- Thesis: INTACT / ADMITTED
- Trust: REVALIDATION
- H: 3Y explicit override; system default remains 1Y
- Expected Annualized Return: about 14.20%
- Required Return: 10%
- Risk: PASS
- MIE: OPTIONAL / absent
- Decision: REVIEW_REQUIRED
- New capital: FALSE

## Development boundary

Investment Core remains single-company and PIT-bound.

CSI800 / CSI Industry / historical-universe reconstruction and FM forecast research remain separate Research Track workstreams and do not block the core.

## A1 status

A1 is PASS / MERGED as an engineering/evidence-closure milestone.

A1-01 established the deterministic economic bridge; A1-02 established the capital-allocation and Trust/Governance evidence bridge; A1-03 integrated them into existing Quality and Trust semantics. These layers do not directly authorize capital.

For 300750, Quality Gate remains CONDITIONAL, Trust remains CONDITIONAL, and new capital remains FALSE.

Acceptance:
- `docs/iios/A1_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_01_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_02_ACCEPTANCE_2026-10-05.md`
- `docs/iios/RP_01_RISK_PORTFOLIO_PRODUCTION_CONTRACT_v0.1.md`
- `docs/iios/DR_01_DECISION_LIFECYCLE_CONTRACT_v0.1.md`
- `docs/iios/DR_02_PERSISTENCE_CLI_INTEGRATION_v0.1.md`

## TR-01 status

TR-01 Trigger Contract / Event Semantics = PASS / MERGED / CANONICAL.
- PR #89;
- merge commit: 0fb7262ded47b3497f5be33dc93163e209f0098f;
- dedicated Actions run #9 = SUCCESS;
- independent exact-module execution = PASS.

The full Investment Core CI on the pre-merge TR-01 head retained four unrelated CORE-04 assertion regressions. These remain a separate cleanup item and do not change the TR-01 acceptance boundary.

## TR-02 status

TR-02 Monitoring State = PASS / MERGED / CANONICAL.
- PR #91;
- merge commit: 6b5a83ff3dcb0028945f455c517b369dbbf8220b;
- dedicated Actions run #10 = SUCCESS;
- red-team boundary review = PASS.

TR-02 does not include scheduler, alerts, automatic decision execution, or investment-semantic changes.

## TR-03 status

TR-03 Validation / Replay = PASS / MERGED / CANONICAL.
- PR #93;
- merge commit: 33291911c6e6b26da6deaf6c28a7a2046173c842;
- dedicated Actions run #5 = SUCCESS;
- red-team boundary review = PASS.

TR-03 closes the historical `next_due_at` replay gap using immutable monitoring initialization/evaluation records and source-derived fail-closed validation.

Scheduler/alerts remain out of scope.
## C8 status

C8 Final Independent Red-team / MVP Acceptance = PASS / MERGED / CANONICAL.

Remediation PR #116:
- merge commit: c99763a9eae957e59c238590ad64b00bc308e54b.

Canonical-main rerun:
- Actions Run #30;
- tested head: c99763a9eae957e59c238590ad64b00bc308e54b;
- 36 tests passed;
- compileall, C3 harness, C7 harness and git diff-check passed.

AUTH-001/002/003 are enforced at Decision Admission, Decision Series persistence and Human Approval authorization boundaries.

Acceptance: docs/iios/C8_ACCEPTANCE_2026-10-06.md.

C8 adds no new investment capability, scheduler/alerts or automatic execution.

**Post-C8 development boundary: explicit governance decision required.**

Historical Stage C milestone sequencing remains context only.

## Stage C milestone status after C5

Historical TR-03 checkpoint: TR-03 Validation / Replay is now PASS / MERGED / CANONICAL.

- C6 Human Execution Receipt = PASS / MERGED / CANONICAL
- C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL
- Current next boundary: C8 Final Independent Red-team / MVP Acceptance

## Governance rule

All new development starts from:

```
canonical main
    ↓
docs/PROJECT_STATE_INDEX.md
    ↓
relevant normative contract
```

Historical documents are context only. Diagnostic branches / PRs are not capability until merged.

## C0 status

C0 Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL.

C0 closed project-state authority, continuity hygiene, stale-document boundaries, and deterministic governance CI checks. It did not modify Investment Core economics or Decision semantics.

The canonical Stage C plan is `docs/iios/IIOS_STAGE_C_PRODUCTIZATION_PLAN_v0.1.md`.

Canonical C0 merge: `1594e43eee14aaa41ddde675ddbe61d650462cf7`.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration.


## C1 status

C1 Machine Publication = PASS / MERGED / CANONICAL.

C1 provides a read-only, content-addressed machine-readable projection of an exact Decision Revision, with explicit AI/Human separation and bound Trigger / Monitoring / Validation references.

Acceptance: `docs/iios/C1_ACCEPTANCE_2026-10-06.md`.

Canonical C1 merge: `b9a8ff0fe1341a56f363fb058677dbd50a4f87b8`.

Historical next boundary at the checkpoint documented in this section: C2 Human Report / Report Quality Gate.


## C2 status

C2 Human Report / Report Quality Gate = PASS / MERGED / CANONICAL.

C2 provides a deterministic human-readable projection of an accepted Machine Publication, plus immutable report metadata/Markdown and a fail-closed Report Quality Gate.

Acceptance: `docs/iios/C2_ACCEPTANCE_2026-10-06.md`.

Canonical C2 merge: `75bb360436286ae950a05028769701380120e561`.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration.

 
## C3 status

C3 Second Company Acceptance = PASS / MERGED / CANONICAL.

Real second company: 四川科伦药业股份有限公司 / CN-A / 002422.

Dedicated C3 Actions run #11 = SUCCESS; 4 C3 tests passed; executable acceptance harness passed; compileall and git diff --check passed.

Acceptance: docs/iios/C3_ACCEPTANCE_2026-10-06.md.
Canonical C3 merge: eb0f9fc965f9ce6aa09685776d2ec8a0522e3b47.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration. C3 introduced no Expectation Gap, positioning/sizing, scheduler, alerts, or automatic execution capability.


## C4 status

C4 Expectation Gap Production Integration = PASS / MERGED / CANONICAL.

Dedicated C4 Actions run #7 = SUCCESS on exact head aacf1c0cc715697bfac2aa0bae5e2f0a4c899ad2.
75 tests passed; executable acceptance harness 7 / 7 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C4_ACCEPTANCE_2026-10-06.md.
Canonical C4 merge: 07d45c18df8df9100d4866dd5f92fa95ccdb7186.

Historical next boundary at the checkpoint documented in this section: C5 Positioning / Sizing.


## C5 status

C5 Positioning / Sizing = PASS / MERGED / CANONICAL.

Dedicated C5 Actions run #7 = SUCCESS on exact head f9758beb683b3ba044fc9a153018050fa4ff09d9.
86 tests passed; executable acceptance harness 9 / 9 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C5_ACCEPTANCE_2026-10-06.md.
Canonical C5 merge: cdf998cd21776363914f178e648f03ec0c1539f8.

C5 is timing/sizing-only. It cannot mutate fundamental Decision action, Trust, Quality, Thesis, intrinsic value, Return, Required Return, or Risk. It does not add Kelly, portfolio optimization, scheduler, alerts, automatic execution, or Forecast Research productionization.

Historical next boundary at the checkpoint documented in this section: C6 Human Execution Receipt.


## C6 status

C6 Human Execution Receipt = PASS / MERGED / CANONICAL.

Dedicated C6 Actions run #2 = SUCCESS on exact head f817041471a43618d30f88538b11a96e67b71fa0.
23 tests passed; executable acceptance harness 8 / 8 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C6_ACCEPTANCE_2026-10-06.md.
Canonical C6 merge: 4c01e40dd7469221d9f5aee005c96e05bf4eb55f.

C6 is record-only: execution receipt requires exact HUMAN_APPROVED binding, is immutable, and cannot mutate Decision Revision, Human Approval, Current Projection, or Decision action. auto_execution remains false.

Historical next boundary at the checkpoint documented in this section: C7 Full Lifecycle E2E.


## C7 status

C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL.

Dedicated C7 Actions run #6 = SUCCESS on exact head 43664c9bee33b3d53f212428da019e197a9fcaf2.
74 related tests passed; executable acceptance harness 4 / 4 PASS; compileall and git diff-check passed.

Acceptance: docs/iios/C7_ACCEPTANCE_2026-10-06.md.
Canonical C7 merge: 82d1911c985791e4b76f63d792588d175ee505f8.

C7 proves append-only revisions, downstream-only Monitoring and Execution Receipt, deterministic replay, new-run/new-revision requirements, and projection-only Publication / Report. It introduces no new investment policy or execution automation.

Historical next development boundary at the C7 checkpoint: C8 Final Independent Red-team / MVP Acceptance.

## FM04 status

M1.2-FM04 Conditional Backtest = PASS / MERGED / CANONICAL.

- PR #150;
- accepted CI run #2 = SUCCESS (run id `37564860982`);
- 12 FM04 tests passed;
- exact FM02 and FM03 reconstruction passed;
- pinned FM03 snapshot hash: `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- real CATL result: 406 selection units, 0 selected, 406 `NO_SELECTION`, 79 conditional descriptive groups;
- independent PIT/nested-selection/scoring audit = PASS;
- output schema/invariants, compileall, and git diff-check = PASS.

The backtest machinery is valid, but the frozen 11-origin / seven-state-dimension sample produces no state-conditioned inner selection with N≥3. This is a data-sufficiency result, not predictive-validity evidence. FM04 does not authorize production routing, confirmatory inference, or investment decisions.

Acceptance: `docs/iios/FM04_ACCEPTANCE_2026-10-07.md`.

**Next boundary: M1.2-FM05 Scope Freeze / Data Sufficiency Adjudication.**


## FM05 status

M1.2-FM05 Scope / Estimand / Sufficiency Freeze = PASS / MERGED / CANONICAL.

- PR #156;
- merge commit `215afcc60e649dde331e7f076be809dda716770a`;
- accepted exact head `e6b5a77290409d3e95164007245d57f58246ccd4`;
- dedicated FM05 workflow run #1 = SUCCESS;
- run id `37578843014`;
- adjudication: **INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION**;
- frozen replay: 406 outer selection units, 0 selected, 0 outer evaluated, 406 NO_SELECTION, 79 structural conditional groups, 0 empirical conditional groups.

FM05 is governance-only. It does not authorize model selection, production routing, automatic execution, or investment decisions. Result-driven redesign requires a new research epoch.


## FM07 status

M1.2-FM07 Research Epoch Amendment Gate = PASS / MERGED / CANONICAL.

- PR #159;
- merge commit: `549f16ce37058a9b889c159b6392d175bc3397b4`;
- accepted exact head: `d8870e08aded67eac5f6cdda1b811b4d4632eda7`;
- gate decision: **DO_NOT_AMEND_CURRENT_EPOCH**;
- current epoch `RE-M12-EXP-CATL-20260930` is closed to same-epoch amendment.

Any result-driven scope, estimand, threshold, state, model-family, metric, origin-schedule, or universe change requires a new research epoch with pre-execution freeze and renewed PIT/provenance/purity controls. FM07 does not open that epoch automatically.


## New research epoch design

M1.2 New Research Epoch Design Proposal = **CANONICAL DESIGN / NOT ACTIVATED**.

- PR #161;
- merge commit `8dfcb150583c05f963fa2bd1c50ca9a55aed9935`;
- recommendation: cross-sectional universe expansion with threshold preservation;
- N>=3, MAE primary metric, existing model instances and state dimensions remain provisional defaults, not an active epoch;
- A02 PIT universe admission, renewed provenance, purity freeze, and owner approval remain required before execution.


## A02 B-01 status

A02 B-01 Free-First Source Registry = **PASS / MERGED / CANONICAL — ADMISSION REMAINS BLOCKED**.

- PR #163;
- merge commit: `3230c7d09f212ab92622ffefc66e684d18262dd0`;
- current unresolved domains: `st_history`, `industry_history`, `source_vintages`;
- no historical PIT admission is claimed from current official pages alone.

### DATA-01-B Run #2

- workflow run: `37593042893`;
- head SHA: `6e8fc8ef9639c486daae33aa74bb64b86366c4dc`;
- artifact: `11469004605`;
- GitHub artifact digest = independent ZIP SHA-256: `dabc25996524f03e8c533e33bd7921ed5c03e85a4b72edbf1b3a15589c4b17ec`;
- independent manifest verification: **8/8 PASS**;
- exact current official bytes: SSE / SZSE stock lists, SSE risk plate, SZSE company notice, CSI taxonomy definition;
- Baostock secondary materialization: **BLOCKED** at login;
- PIT sufficiency: **BLOCKED**;
- identity / listing-delisting / common-equity / ST historical known_at: **not admitted**;
- CSI security-level historical industry assignments: **not materialized**.

A run-2 provenance inconsistency in the emitted admission matrix was identified and corrected in the canonical materializer. No admission boundary was relaxed.

### DATA-01-B Run #3

- workflow run: `37593671212`;
- head SHA: `6f47e5f6f481df8f4a300765f237c5f7f70dae0d`;
- artifact: `11469780985`;
- GitHub artifact digest = independent ZIP SHA-256: `85e836b2e797730be459a334172993118eb7101e44014c2539344c7ef679eb62`;
- independent manifest verification: **8/8 PASS**;
- materializer exit code: `4` (expected bounded fail-closed result);
- current official raw evidence: materialized and independently hashed;
- historical security-master PIT evidence: **NOT ESTABLISHED**;
- Baostock: **BLOCKED / NOT ADMITTED**;
- overall B sufficiency: **BLOCKED**;
- permitted Run #3 result class: **BLOCKED**.

Run #3 confirms the repaired artifact-transport path. It does not convert current snapshots into historical PIT evidence and does not change A02 admission state.

Next technical boundary: obtain reproducible historical PIT carrier evidence with source-vintage / known_at; do not activate the proposed successor forecast epoch before A02 admission is complete.

### DATA-01-A Batch 2

- historical G0-T02 handoff pointer located: `CSINDEX_000906_20260703T100909Z`;
- declared historical package: 373560 bytes;
- declared package SHA-256: `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`;
- declared terminal member: `000906cons.xls`, 169984 bytes, SHA-256 `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`;
- current runtime/package access: **BLOCKED**;
- independent A raw preflight: **BLOCKED**;
- negative-control tests: **3/3 PASS**;
- no checksum/package declaration has been promoted to raw-byte evidence.

Batch-2 state remains `HISTORICAL_CARRIER_BYTES = BLOCKED`. The approved next transition is actual package/raw-byte supply followed by independent SHA-256 and A preflight.

## DATA-01-B Batch 3

- Batch 3: `DATA-01-B` B-side Free-First Raw Intake.
- Independent B raw preflight: `research/a02_raw/b_raw_preflight.py`.
- Required B domains: identity, listing_delisting, common_equity, st_history, industry_history, source_vintages.
- Required PIT origins: 11 origins from 2023Q3 through 2026Q1.
- Latest runtime probe: Run `37595133874`, Artifact `11469743020`, artifact SHA-256 `cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49`.
- B raw preflight result: **BLOCKED / exit 4**; latest artifact contains no `DELIVERY_MANIFEST.json` and no B raw-domain files.
- Independent negative-control suite: **4/4 PASS**.
- No B raw-intake declaration, current snapshot, checksum-only metadata, or `retrieved_at` value has been promoted to PIT evidence.
- Downstream remains locked: A02 admission BLOCKED; Model Selection LOCKED; cross-security successor epoch LOCKED.
- Next transition: actual B raw bundle supply → independent DATA-01-C verification.
