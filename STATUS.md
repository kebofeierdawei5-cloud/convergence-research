# IIOS Project Status

State classification: **CANONICAL SUMMARY**
Date: 2026-10-07

Authoritative current-state record:
`docs/PROJECT_STATE_INDEX.md`

This file is a concise human-readable summary. When it conflicts with the Current State Index, the Current State Index wins.

## Current stage

**Current canonical M1.2 status: FM01 Exact CATL M1.1 Source Snapshot Admission = PASS / MERGED / CANONICAL**

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
```

Canonical main after FM01 admission and final governance sync:
`840f653f52dbfb13bf3d1dba3074283dc383334f`

Baseline:
- PR #136 = MERGED;
- exact FM00 source anchor = `536e883bc873dbe7dd7383690a7a95a0f65591a7`;
- immutable tag `m1.2-fm00-v0.1.0`;
- baseline workflow #6 = SUCCESS on exact PR head `ff6bfe0ff7677d0a965af513ac2ee644413565d1`.

G2 historical frozen identity remains separate from the accepted R0 successor evidence; no frozen-byte rewrite was performed.

**Next boundary: M1.2-FM-02 Feature Builder / Forecastability Feature Contract.**

FM01 data gate is now `DATA_READY` after exact-source admission, provenance binding, 22-quarter coverage validation, and independent PIT replay.

Admitted CATL scope: 300750.SZ, 2021Q1–2026Q2, 22 quarters, 44 DriverSeries records for REVENUE / NET_PROFIT.

No FM01 numeric data were fabricated, inferred, or reconstructed from memory.

FM02 remains separately gated by M1.2 research governance, feature/state contracts, conditional backtest, partitioning and sealed-manifest controls.

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
