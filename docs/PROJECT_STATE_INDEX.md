# IIOS Project State Index

State classification: **CANONICAL**
Snapshot: 2026-10-07
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
        ↓
C2 Human Report / Report Quality Gate = PASS / MERGED / CANONICAL
        ↓
C3 Second Company Acceptance — 科伦药业 = PASS / MERGED / CANONICAL
         ↓
C4 Expectation Gap Production Integration = PASS / MERGED / CANONICAL
         ↓
C5 Positioning / Sizing = PASS / MERGED / CANONICAL
        ↓
C6 Human Execution Receipt = PASS / MERGED / CANONICAL
        ↓
C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL
        ↓
C8 Final Independent Red-team / MVP Acceptance = PASS / MERGED / CANONICAL
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

C2 Human Report / Report Quality Gate is PASS / MERGED / CANONICAL:
- PR #101;
- merge commit 75bb360436286ae950a05028769701380120e561;
- dedicated C2 CI #2 = SUCCESS;
- 7 C2 tests passed;
- report and QA JSON Schema validation plus diff check passed.

C4 Expectation Gap Production Integration is PASS / MERGED / CANONICAL:
- PR #105;
- merge commit 07d45c18df8df9100d4866dd5f92fa95ccdb7186;
- dedicated C4 CI #7 = SUCCESS on exact head aacf1c0cc715697bfac2aa0bae5e2f0a4c899ad2;
- 75 tests passed;
- executable acceptance harness 7 / 7 PASS;
- compileall and git diff --check passed;
- acceptance: docs/iios/C4_ACCEPTANCE_2026-10-06.md.

C5 Positioning / Sizing is PASS / MERGED / CANONICAL:
- PR #108;
- merge commit cdf998cd21776363914f178e648f03ec0c1539f8;
- dedicated C5 CI #7 = SUCCESS on exact head f9758beb683b3ba044fc9a153018050fa4ff09d9;
- 86 tests passed;
- executable acceptance harness 9 / 9 PASS;
- compileall and git diff --check passed;
- acceptance: docs/iios/C5_ACCEPTANCE_2026-10-06.md.

Canonical Stage C milestone state:
- C6 Human Execution Receipt = PASS / MERGED / CANONICAL;
- C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL.
- Current next Stage C boundary = C8 Final Independent Red-team / MVP Acceptance.

The separately tracked full Investment Core / Risk Portfolio CI regressions remain non-blocking for C4/C5/C6/C7 acceptance and are not current Stage C capability gaps.

The full Investment Core / Risk Portfolio CI still carries separately tracked pre-existing regressions; C4/C5 acceptance is independently bounded and these failures are not treated as C4/C5 capability evidence.

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

## 8. Current canonical authority-hardening state

The post-C8 authority-hardening sequence is complete through the independent re-audit:

```
B00 = PASS / MERGED / CANONICAL
   ↓
B02 Canonical Investment Admission = PASS / MERGED / CANONICAL
   ↓
B03-B Canonical Upstream Authority Mandatory = PASS / MERGED / CANONICAL
   ↓
B04-B Forecast → Valuation → Return Lineage Mandatory = PASS / MERGED / CANONICAL
   ↓
Post-B04 Independent Authority Re-audit = PASS / GOVERNANCE-ADJUDICATED
```

### B02 — Canonical Investment Admission

- PR #125;
- merge commit: `67e4ba3e6e4c047a2e59d684335bf1fd745e20f5`.

### B03-B — Mandatory Upstream Authority

- PR #128;
- merge commit: `18b848d569796ac3a712f8c5d217669496d3887f`;
- runtime requires canonical upstream authority schema `IIOS-CORE-04-UPSTREAM-ADMISSION-0.2`;
- legacy v0.1 caller-declared authority is blocked at Decision runtime.

### B04-B — Mandatory Forecast / Valuation / Return Lineage

Status: **PASS / MERGED / CANONICAL**

- PR #129;
- merge commit: `d9712c3f48fd71dfec348aca18fdf6b0fd1559a6`;
- dedicated B04-B workflow #29 = SUCCESS;
- Investment Core #746, B00-B #74, B03-B #54, B04 #60, C3 #89, C4 #87, C5 #75 and C8 #89 = SUCCESS on the exact B04-B branch head.

B04-B enforces:
- exact Return lineage version `IIOS-FORECAST-VALUATION-RETURN-LINEAGE-0.1`;
- canonical Forecast reference;
- canonical Valuation reference resolved through the trusted resolver;
- Return Gate scenario equality against canonical Valuation output;
- Return Gate current entry-price equality against the canonical current-price observation;
- fail-closed handling of missing, legacy, substituted or divergent lineage.

The B00-B P0-02 attack is closed on the enforced Decision path.

### PR #131 — Post-B04-B authority regression hardening

Status: **PASS / MERGED / CANONICAL TEST HARDENING**

- merge commit: `268852d754ab2385d9a96a10309a782978eb25af`;
- test-only changes;
- adds resolver-propagation spying at the engine boundary;
- hardens the P0-02 regression by explicitly forging the canonical Valuation admission hash.

No production Decision semantics changed.

### Post-B04 Independent Authority Re-audit

Status: **PASS / GOVERNANCE-ADJUDICATED**

- diagnostic PR #133;
- audit target: canonical `main` `268852d754ab2385d9a96a10309a782978eb25af`;
- exact audit head: `a080caebe3e6fa08d3716511128db674a6e8d7f1`;
- audit acceptance run #5 = SUCCESS;
- 7 / 7 fresh audit tests passed;
- compileall = PASS;
- git diff --check = PASS;
- governance verdict: no authority bypass reproduced in the tested post-B04 chain.

Fresh attack classes tested:
- valid alternate Forecast substitution;
- valid alternate Valuation substitution;
- valid cross-domain upstream reference;
- missing mandatory Valuation resolver at direct Decision runtime;
- missing mandatory Valuation resolver during v0.3 replay;
- immutable canonical Forecast same-ID conflicting bytes.

The persisted snapshot / re-execution distinction was also verified: replay returns `FAIL` when the mandatory resolver is absent, while the original snapshot remains integrity-valid.

Acceptance record:
`docs/iios/POST_B04_INDEPENDENT_REAUDIT_2026-10-07.md`.

### Independent regression track

RP-01 remains a separate legacy fixture failure (`str.read`) and is not authority-hardening acceptance evidence.

## 9. Next canonical development boundary

The post-B04 authority chain is now governance-adjudicated PASS.

The next engineering boundary is:

**M1.2-FM00 — Git Baseline / Frozen Reference Establishment**

Then proceed to:

**FM-01 — exact CATL M1.1 source snapshot**

FM-02 Forecast Model Selection / research-model productionization remains blocked by its own M1.2 governance, partitioning, capability-access and sealed-manifest requirements.

This boundary is a development-governance transition, not permission to bypass M1.2 controls.

The Investment Core remains single-company and PIT-bound. No scheduler, alerts, automatic execution, full-market screening, optimizer/Kelly logic, or new forecast/valuation model family is authorized by this state.

Historical Stage C acceptance records remain valid evidence of prior checkpoints but do not define the current development boundary.
