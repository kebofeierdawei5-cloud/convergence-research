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

## 8. Current canonical M1.2 baseline state

The post-C8 authority-hardening sequence is complete through independent re-audit, and the M1.2-FM00 Git baseline is now established on the canonical repository:

```
B00 = PASS / MERGED / CANONICAL
   ↓
B02 = PASS / MERGED / CANONICAL
   ↓
B03-B = PASS / MERGED / CANONICAL
   ↓
B04-B = PASS / MERGED / CANONICAL
   ↓
Post-B04 Independent Authority Re-audit = PASS / GOVERNANCE-ADJUDICATED
   ↓
M1.2-FM00 Git Baseline = PASS / MERGED / CANONICAL
```

### Post-B04 Independent Authority Re-audit

Status: **PASS / GOVERNANCE-ADJUDICATED**

- diagnostic PR #133;
- audit target: `268852d754ab2385d9a96a10309a782978eb25af`;
- acceptance workflow #5 = SUCCESS;
- 7 / 7 fresh authority attack tests passed;
- acceptance record: `docs/iios/POST_B04_INDEPENDENT_REAUDIT_2026-10-07.md`.

### M1.2-FM00 Git Baseline

Status: **PASS / MERGED / CANONICAL**

- baseline PR #136;
- baseline base main: `60d5f9927cb5543415307454aea231376f86c72e`;
- exact FM00 source anchor: commit `536e883bc873dbe7dd7383690a7a95a0f65591a7`;
- immutable FM00 tag: `m1.2-fm00-v0.1.0`;
- tag object: `aac0cccf596ee2703caedffc08f434be9e2dffed`;
- exact-head baseline CI: workflow run #6 = SUCCESS on head `ff6bfe0ff7677d0a965af513ac2ee644413565d1`;
- baseline merge commit: `ea1453f6ac1a04343b3b7fb9a704d3df03e7d6ba`.

The baseline does not rewrite the historical FM00 root commit or frozen G2 bytes.

### G2 reference resolution

The historical frozen G2 identity remains immutable and separate from the R0 successor evidence used for current closure:

- historical frozen carrier SHA-256: `899f0b1b9f3619458e17be76ac43dd6e00b5397d0c12adb7b68e2479c7f51524`;
- R0 successor evidence carrier SHA-256: `bd5cbaf23c9029b46fafd19992029932431059de7424a08de48624aca5d431c8`;
- successor role: `ACCEPTED_SUCCESSOR_FOR_CURRENT_CLOSURE_ROLE_ONLY`;
- no historical frozen identity rewrite.

Reference resolution record:
`governance/m1-2-fm00-baseline/G2_REFERENCE_RESOLUTION_v0.1.json`.

### FM00 boundary

FM00 remains:

- `EXPLORATORY`;
- `EXPOSED_PRIOR_RESULTS`;
- `confirmatory_eligible = false`;
- `production_router_allowed = false`.

The exact historical source baseline is anchored by the immutable Git commit/tag above.

### FM01 boundary

FM01 implementation exists on the repository, but the CATL population gate remains:

```
BLOCKED_DATA_INGRESS
```

The target remains 22 quarters (2021Q1–2026Q2), and no numeric value may be fabricated or inferred while the exact M1.1 source snapshot is absent.

Acceptance / baseline records:
- `governance/m1-2-fm00-baseline/M1_2_FM00_BASELINE_MANIFEST_v0.2.json`
- `governance/m1-2-fm00-baseline/M1_2_FM00_GIT_BASELINE_ACCEPTANCE_2026-10-07.md`

### Independent regression track

RP-01 remains a separate legacy fixture regression (`str.read`) and is not M1.2 baseline acceptance evidence.

## 9. Next canonical development boundary

The next engineering boundary is:

**M1.2-FM-01 / exact CATL M1.1 source snapshot admission**

However, implementation already exists and is explicitly blocked at data ingress. Therefore the next permitted task is:

**Acquire / admit the exact M1.1 CATL source snapshot under PIT and provenance controls.**

Only after exact source admission should FM01 data population proceed.

FM02 Forecast Model Selection remains gated by the M1.2 research epoch, feature/state contracts, conditional backtest, research partition, capability-access and sealed-manifest requirements.

This boundary does not authorize:
- model selection;
- result-driven tuning in the contaminated FM00 epoch;
- a production router;
- scheduler / alerts;
- automatic execution;
- full-market screening;
- portfolio optimizer / Kelly logic.

Historical Stage C acceptance records remain valid evidence of prior checkpoints but do not define the current development boundary.
