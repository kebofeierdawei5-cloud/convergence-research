# IIOS Project Status

State classification: **CANONICAL SUMMARY**
Date: 2026-10-06

Authoritative current-state record:
`docs/PROJECT_STATE_INDEX.md`

This file is a concise human-readable summary. When it conflicts with the Current State Index, the Current State Index wins.

## Current stage

**A0 Governance / State Cleanup = PASS / MERGED**

**A1-01 Economic Evidence Bridge = PASS / MERGED**

**A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED**

CORE-04 vertical decision closure is complete.

**A1 Company-side Evidence Closure = PASS / MERGED**

A1 is complete as the company-side evidence-closure engineering milestone. Current 300750 Quality remains CONDITIONAL and new capital remains FALSE.

C0 Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL. C1 Machine Publication = PASS / MERGED / CANONICAL. C2 Human Report / Report Quality Gate = PASS / MERGED / CANONICAL. C3 Second Company Acceptance = PASS / MERGED / CANONICAL. C4 Expectation Gap Production Integration = PASS / MERGED / CANONICAL. The next Stage C batch is C5 Positioning / Sizing.

TR-03 Validation / Replay is now PASS / MERGED / CANONICAL.

No new P3/P4/MIE model work is on the critical path.

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
## Product gaps after C2

- C4 Expectation Gap Production Integration
- C5 Positioning / Sizing
- C6 Human Execution Receipt
- C7 Full Lifecycle E2E
- C8 Final Independent Red-team / MVP Acceptance

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

Next boundary: C5 Positioning / Sizing.


## C1 status

C1 Machine Publication = PASS / MERGED / CANONICAL.

C1 provides a read-only, content-addressed machine-readable projection of an exact Decision Revision, with explicit AI/Human separation and bound Trigger / Monitoring / Validation references.

Acceptance: `docs/iios/C1_ACCEPTANCE_2026-10-06.md`.

Canonical C1 merge: `b9a8ff0fe1341a56f363fb058677dbd50a4f87b8`.

Next boundary: C2 Human Report / Report Quality Gate.


## C2 status

C2 Human Report / Report Quality Gate = PASS / MERGED / CANONICAL.

C2 provides a deterministic human-readable projection of an accepted Machine Publication, plus immutable report metadata/Markdown and a fail-closed Report Quality Gate.

Acceptance: `docs/iios/C2_ACCEPTANCE_2026-10-06.md`.

Canonical C2 merge: `75bb360436286ae950a05028769701380120e561`.

Next boundary: C4 Expectation Gap Production Integration.

 
## C3 status

C3 Second Company Acceptance = PASS / MERGED / CANONICAL.

Real second company: 四川科伦药业股份有限公司 / CN-A / 002422.

Dedicated C3 Actions run #11 = SUCCESS; 4 C3 tests passed; executable acceptance harness passed; compileall and git diff --check passed.

Acceptance: docs/iios/C3_ACCEPTANCE_2026-10-06.md.
Canonical C3 merge: eb0f9fc965f9ce6aa09685776d2ec8a0522e3b47.

Next development boundary: C4 Expectation Gap Production Integration. C3 introduced no Expectation Gap, positioning/sizing, scheduler, alerts, or automatic execution capability.
