# IIOS Project State Index

State classification: **CANONICAL**
Snapshot: 2026-10-06
Authority: this file is the **only canonical Current State Index**.

## 1. Canonical state

```
G2 R10 Reference Governance Runtime = FROZEN
        ↓
B0 Repair = PASS
        ↓
B1 Investment Semantics v0.3 = PASS / FROZEN
        ↓
CORE-00 = PASS / MERGED
        ↓
CORE-01 = PASS / MERGED
        ↓
CORE-02 Company Economic Core = PASS / MERGED
        ↓
CORE-03 Real 300750 = PASS / MERGED
        ↓
CORE-04 Production Decision Kernel = PASS / MERGED
        ↓
CORE-04 × 300750 Final Decision Chain = PASS / REVIEW_REQUIRED / NO NEW CAPITAL
        ↓
A0 Governance / State Cleanup = PASS / MERGED
        ↓
A1-01 Economic Evidence Bridge = PASS / MERGED
        ↓
A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED
        ↓
A1-03 Quality Gate Integration = PASS / MERGED
        ↓
A1 Company-side Evidence Closure = PASS / MERGED
        ↓
RP-01 Risk / Portfolio Production Contract = MERGED
        ↓
DR-01 Decision Revision / Human Approval = PASS / MERGED
        ↓
DR-02 Persistence / CLI = MERGED
        ↓
TR-01 Trigger Contract / Event Semantics = PASS / MERGED / CANONICAL
        ↓
TR-02 Monitoring State = PASS / MERGED / CANONICAL
        ↓
TR-03 Validation / Replay = PASS / MERGED / CANONICAL
        ↓
C0 Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL
        ↓
C1 Machine Publication = PASS / MERGED / CANONICAL
```

Current canonical main is the sole source of current implementation truth. The Git ref, not a duplicated document hash, defines the current main SHA.
A0 acceptance: `docs/iios/A0_ACCEPTANCE_2026-10-05.md`.

## 2. Investment Core capability boundary

```
user-selected company + cutoff
→ admitted PIT evidence
→ Reality / Trust / Quality / Value Drivers / Thesis
→ Primary Valuation
→ Independent Forecast
→ Return / Required Return
→ Risk / Portfolio
→ Optional MIE
→ Decision
```

The core decision boundary is implemented and has a real CATL/300750 E2E.

Not an Investment Core entry/completion gate:

- CSI800 historical membership;
- CSI Industry historical classification;
- full-market historical universe;
- PIT Security Master for universe construction;
- FM forecast research capability.

Those remain separate Research Track capabilities.

## 3. CORE-04 / 300750 canonical result

Case: `RC-CN-A-300750-20261004`

- current PIT price: 291.11 CNY/share;
- Reality: PASS;
- Quality Gate: CONDITIONAL;
- Value Driver: PASS;
- Primary Valuation: PASS;
- Independent Forecast: PASS;
- Thesis Admission: ADMITTED;
- Thesis: INTACT;
- Trust: REVALIDATION;
- H: 3Y with explicit Horizon Override;
- MIE: OPTIONAL_EXPLANATORY and absent;
- Expected Annualized Return: about 14.20%;
- Required Return: 10%;
- Risk: PASS;
- final action: REVIEW_REQUIRED;
- new capital: FALSE.

This is an accepted system result, not a claim that the security should be bought.

## 4. Current blockers

### A1 — Company-side Evidence Closure

A1 is PASS / MERGED as an engineering and evidence-closure milestone.

Completed sub-batches:
- A1-01 Economic Evidence Bridge = PASS / MERGED;
- A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED;
- A1-03 Quality Gate Integration = PASS / MERGED.

The company-side evidence chain is integrated into the existing Quality Gate semantics. For 300750, Quality Gate remains CONDITIONAL and new capital remains FALSE. A1 completion does not imply BUY/ADD.

### Productization

RP-01 Risk / Portfolio Production Contract is merged in canonical main:
- PR #84;
- merge commit d2180754ef6b3e71ecf5eaad9ad7d6224d46af00;
- explicit risk budget and portfolio capacity inputs;
- fail-closed package validation;
- deterministic audit hash;
- no Decision Precedence change.

C1 Machine Publication is PASS / MERGED / CANONICAL:
- PR #97;
- merge commit b9a8ff0fe1341a56f363fb058677dbd50a4f87b8;
- dedicated C1 CI #7 = SUCCESS;
- 5 C1 tests passed;
- JSON Schema validation and diff check passed.

Remaining Stage C productization:
- C2 Human Report / Report Quality Gate;
- C3 Second Company Acceptance;
- C4 Expectation Gap Production Integration;
- C5 Positioning / Sizing;
- C6 Human Execution Receipt;
- C7 Full Lifecycle E2E;
- C8 Final Independent Red-team / MVP Acceptance.

The full Investment Core CI still carries the separately tracked four CORE-04 assertion regressions; C1 does not modify that subsystem.

## 5. State classification

### CANONICAL

Only current accepted state on `main` is authoritative.

Examples:
- this file;
- current `STATUS.md`;
- production code / schemas / tests on `main`;
- accepted milestone records explicitly referenced from this index.

### HISTORICAL

Immutable past-state material. It explains history but cannot define current capability.

Known historical/superseded state records include:

- `docs/iios/STATE_RECONCILIATION_2026-10-04.md`;
- `docs/iios/IIOS_CURRENT_STATE_INDEX.md`;
- `docs/iios/IIOS_CONSOLIDATED_POST_REDTEAM_DEVELOPMENT_PLAN_2026-10-04.md`;
- pre-adjudication B1 proposal documents.

### DIAGNOSTIC

Non-authoritative experiments, probes, unmerged work and temporary validation artifacts.

No diagnostic branch or PR is a current capability until merged to `main`.

## 6. New-development gate

Every new batch MUST begin from:

```
canonical main
    +
docs/PROJECT_STATE_INDEX.md
```

Then:

1. verify current main SHA;
2. verify the target batch is not already merged;
3. read the relevant normative contract;
4. create a fresh branch from current main;
5. keep the PR scope inside the declared batch;
6. merge only after CI evidence passes.

Never continue from a stale branch merely because it contains previous work.

## 7. Authority precedence

```
canonical main
    >
Current State Index
    >
normative contracts / schemas / production tests
    >
independent CI evidence
    >
historical records
    >
chat context
```

A diagnostic or historical record can identify a problem, but cannot promote itself into capability.

## 8. Current next batch

**A1 Company-side Evidence Closure = PASS / MERGED**

A1 is complete as the current company-side evidence-closure milestone.

**RP-01 Risk / Portfolio Production Contract = MERGED**

RP-01 is implementation-complete on canonical main; runtime CI evidence was not independently observable through the available workflow interface in this session.

**DR-01 Decision Revision / Human Approval Contract = PASS / MERGED**

Canonical lifecycle semantics are frozen. Independent execution passed 8/8; GitHub Actions runtime telemetry was not exposed by the available workflow interface and is recorded as UNOBSERVED.

**DR-02 Persistence + CLI Integration = MERGED / IMPLEMENTATION COMPLETE**

Merge commit: a4e493cc0c7f45647a02dd587f89fb7d98ee22e2.
Canonical persistence and lifecycle replay are integrated. GitHub Actions runtime telemetry was not exposed by the available workflow interface and is recorded as UNOBSERVED.

**TR-01 Trigger Contract / Event Semantics = PASS / MERGED / CANONICAL**

Merge commit: 0fb7262ded47b3497f5be33dc93163e209f0098f.
Dedicated GitHub Actions run #9 = SUCCESS; independent exact-module execution = PASS.

Acceptance:
- `docs/iios/A1_ACCEPTANCE_2026-10-05.md`
- `docs/iios/RP_01_RISK_PORTFOLIO_PRODUCTION_CONTRACT_v0.1.md`
- `docs/iios/DR_01_ACCEPTANCE_2026-10-05.md`
- `docs/iios/DR_02_PERSISTENCE_CLI_INTEGRATION_v0.1.md`
- `docs/iios/TR_01_ACCEPTANCE_2026-10-06.md`

**TR-02 Monitoring State = PASS / MERGED / CANONICAL**

Merge commit: 6b5a83ff3dcb0028945f455c517b369dbbf8220b.
Dedicated GitHub Actions run #10 = SUCCESS; red-team review passed; no scheduler, alerts, or Decision Kernel changes were introduced.

Acceptance:
- `docs/iios/TR_02_ACCEPTANCE_2026-10-06.md`

**TR-03 Validation / Replay = PASS / MERGED / CANONICAL**

Merge commit: 33291911c6e6b26da6deaf6c28a7a2046173c842.
Dedicated GitHub Actions run #5 = SUCCESS; red-team review passed.
TR-03 closes the historical `next_due_at` replay gap with immutable Monitoring Evaluation Records.

Acceptance:
- `docs/iios/TR_03_ACCEPTANCE_2026-10-06.md`

C0 Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL. C1 Machine Publication = PASS / MERGED / CANONICAL. The next development boundary is C2 Human Report / Report Quality Gate. Scheduler/alerts remain out of scope until a separate explicit batch is authorized; no new P3/P4/MIE model work is implied.

Completed sub-batches:
- **A1-01 Economic Evidence Bridge = PASS / MERGED**
- **A1-02 Capital Allocation + Trust/Governance Evidence Closure = PASS / MERGED**
- **A1-03 Quality Gate Integration = PASS / MERGED**

Acceptance records:
- `docs/iios/A1_01_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_02_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_ACCEPTANCE_2026-10-05.md`

A1 is complete as the company-side evidence-closure milestone.

## 9. Stage C current development boundary

**C0 — Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL**

C0 closed project-state authority, continuity hygiene, stale-document boundaries, and deterministic governance CI checks. No investment semantics or new investment capability were introduced.

Detailed roadmap: `docs/iios/IIOS_STAGE_C_PRODUCTIZATION_PLAN_v0.1.md`.

Immediate next batch: C2 Human Report / Report Quality Gate → C3 Second Company Acceptance.

Parallel FM Research remains separate.

C0 acceptance: `docs/iios/C0_ACCEPTANCE_2026-10-06.md`.
C0 merge: `1594e43eee14aaa41ddde675ddbe61d650462cf7`.
