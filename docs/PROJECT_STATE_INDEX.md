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
        ↓
M1.2-FM00 Git Baseline = PASS / MERGED / CANONICAL
        ↓
FM01 Exact M1.1 Source Snapshot Admission = PASS / MERGED / CANONICAL
        ↓
FM01 DATA_READY = PASS
        ↓
M1.2-FM02 PIT Feature Builder / Forecastability Feature Contract = PASS / MERGED / CANONICAL
        ↓
M1.2-FM03 State Engine / Forecastability State Construction = PASS / MERGED / CANONICAL
        ↓
M1.2-FM04 Conditional Backtest = PASS / MERGED / CANONICAL
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

The M1.2 research baseline is complete through the FM05 Scope / Estimand / Sufficiency Freeze, under the exploratory / contaminated / development-only boundary:

```
Post-B04 Authority Re-audit = PASS
        ↓
M1.2-FM00 Git Baseline = PASS / MERGED / CANONICAL
        ↓
FM01 Exact M1.1 Source Snapshot Admission = PASS / MERGED / CANONICAL
        ↓
FM01 DATA_READY = PASS
        ↓
M1.2-FM02 PIT Feature Builder / Forecastability Feature Contract = PASS / MERGED / CANONICAL
        ↓
M1.2-FM03 State Engine / Forecastability State Construction = PASS / MERGED / CANONICAL
        ↓
M1.2-FM04 Conditional Backtest = PASS / MERGED / CANONICAL
        ↓
M1.2-FM05 Scope / Estimand / Sufficiency Freeze = PASS / MERGED / CANONICAL
```

### M1.2-FM00 Git Baseline

Status: **PASS / MERGED / CANONICAL**

- PR #136; merge `ea1453f6ac1a04343b3b7fb9a704d3df03e7d6ba`;
- exact FM00 source anchor `536e883bc873dbe7dd7383690a7a95a0f65591a7`;
- immutable tag `m1.2-fm00-v0.1.0`;
- dedicated baseline CI passed on exact PR head.

### FM01 Exact CATL M1.1 Source Snapshot Admission

Status: **PASS / MERGED / CANONICAL**

- PR #138;
- baseline main before admission `13adfd6ad4475adf4a57b50ef009075a2a15ccef`;
- exact M1.1 package SHA-256 `34c16dca266a2f35bc2895739b3e847a6c20ea0d66e0acbbc57274a96e22804b`;
- exact M1.1 Git bundle SHA-256 `0f3dd5d5058722ce8f63a6a24d8c7aafa8b28c20ae0374c3bb0a94e9fa2609e1`;
- M1.1 commit `9b612cc79dc8c16ed8aea1529a6ea93e9eb8b993`;
- M1.1 tag `v1.1.0`;
- tag object `a9516728aa1429cd033b474414ed5398c939eabb`;
- exact source bytes were independently SHA-256 verified from the persistent Library and ZIP/bundle critical projections were byte-compared.

Admitted dataset:

- `300750.SZ`;
- 2021Q1–2026Q2;
- 22 quarters;
- 44 records;
- drivers: `REVENUE`, `NET_PROFIT`;
- 12 direct quarterly observations;
- 10 explicitly derived quarterly observations.

Derived provenance remains:

```
Q2 = H1 cumulative - Q1
Q4 = Annual cumulative - Q1 - Q2 - Q3
```

Each admitted record carries source evidence reference, publication/knowledge timestamp, source-vintage metadata, provenance and revision fields.

### PIT admission / independent replay

Status: **PASS**

Independent replay implementation:

`research/fm01/fm01_source_admission_replay.py`

Verified:

- all historical records satisfy the origin-cutoff rule;
- target actual is excluded from the training-visible set;
- future-known observations remain excluded;
- missing/conflicting source state remains fail-closed;
- M1.1 rolling origin counts reproduce as:
  - 3M = 11;
  - 6M = 10;
  - 12M = 8.

Remote exact-head CI:

- workflow `IIOS M1.2 FM01 Exact CATL Source Admission`;
- run #2 = SUCCESS;
- job `verify-fm01-source-admission` = SUCCESS;
- validation, PIT replay, admission invariants, compileall and diff-check all PASS.

Acceptance records:

- `research/fm01/M1_1_EXACT_SOURCE_SNAPSHOT_MANIFEST.json`
- `research/fm01/M1_1_EXACT_SOURCE_BYTES_VERIFICATION.json`
- `research/fm01/M1_1_SOURCE_ADMISSION.json`
- `research/fm01/FM01_ADMISSION_RESULT.json`
- `research/fm01/FM01_CI_ADMISSION_RECEIPT.json`

### FM01 data gate

The former gate:

```
BLOCKED_DATA_INGRESS
```

is now:

```
DATA_READY
```

Current `research/fm01/CATL_DRIVER_HISTORY.ndjson` contains 44 admitted records and the dataset manifest records 22-quarter coverage.

FM01 remains a historical driver-data foundation only. It does not authorize FM02 model selection or a production router.

### G2 reference boundary

Historical G2 frozen identity remains immutable and separate from R0 successor evidence:

- historical frozen carrier SHA-256: `899f0b1b9f3619458e17be76ac43dd6e00b5397d0c12adb7b68e2479c7f51524`;
- R0 successor evidence carrier SHA-256: `bd5cbaf23c9029b46fafd19992029932431059de7424a08de48624aca5d431c8`;
- successor role: `ACCEPTED_SUCCESSOR_FOR_CURRENT_CLOSURE_ROLE_ONLY`.

### Independent regression track

RP-01 remains a separate legacy fixture regression (`str.read`) and is not FM01 admission evidence.

### DATA-01-A exact-byte intake — run 37590889419

A second network-enabled A02 runtime attempt has been independently downloaded and verified.

- workflow run: `37590889419`
- job: `112691834326`
- artifact: `11468960920 / A02-exact-raw-37590889419`
- artifact SHA-256: `bdfff9342c848f3231127c4ee581829e275b29a7dcbbeab1e0b3501bb04e70de`
- exact historical A target SHA-256: `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`
- captured current 000906 SHA-256: `b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb`
- historical exact match: `FALSE`
- B free-first raw bundle in this run: `NOT MATERIALIZED`
- A02 admission: `BLOCKED`

Independent verification record: `docs/iios/A02_DATA01_RUN14_INDEPENDENT_VERIFICATION_20261007.md`.

The run therefore proves actual current-byte capture and fail-closed historical mismatch, but does not supply the missing historical A bytes or B evidence.

## 10. A02 Runtime Evidence — 2026-10-07

The canonical A02 acquisition workflow produced a real immutable runtime artifact, independently verified, but the admission gate remains BLOCKED.

- workflow run: 37588901115
- job: 112684403959
- artifact: 11468022181 / A02-exact-raw-37588901115
- artifact digest: b385d27e24b5765aca9c62e50bd01617c6553a1985f44f6be040e20ec47ab180
- current 000906 SHA-256: b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb
- frozen historical target SHA-256: f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984
- B PIT raw bundle: NOT MATERIALIZED
- A02 verdict: BLOCKED

The independent verification record is docs/iios/A02_RUNTIME_INDEPENDENT_VERIFICATION_v0.2.json. The full acquisition ZIP is retained in the persistent Library and is not itself canonical source evidence.

Development rule: prioritize actual historical raw evidence supply and B free-first materialization over additional archive-probe expansion. Until A/B raw evidence, field-level known_at, PIT reconstruction, and independent replay pass, the cross-sectional research path and model selection remain locked.


## 9. Next canonical development boundary

The original Investment Core is already implemented through the C8 independent red-team acceptance. The immediate development objective is now **MVP real-user pilot testing**, not additional research infrastructure.

The next boundary is:

**PILOT-00 → PILOT-01 → PILOT-02 → PILOT-03 → PILOT-04 → MVP Pilot Acceptance**

The M1.2 cross-sectional research epoch remains a separate proposed Research Track capability. A02 / CSI800 historical-universe evidence is **not an Investment Core dependency** and must not block company-level MVP testing.

The current FM research epoch remains closed to same-epoch amendment. The proposed cross-sectional successor epoch is not activated until its own scope, estimand, sufficiency, PIT/provenance, purity and owner-approval gates are satisfied.

### M1.2-FM02 canonical acceptance

Status: **PASS / MERGED / CANONICAL**

- PR #144;
- merge commit `ade3541302eb6f3fa43ec8aac76540820000a727`;
- final pre-merge head `617c9b8a3f091e76d5ea44a39e963ff255ffd99b`;
- final remote CI run #15 = SUCCESS;
- FM01 source-admission job = SUCCESS;
- FM02 unit tests = 13 / 13 PASS;
- real CATL feature build = PASS;
- output snapshot schema = PASS;
- independent PIT provenance audit = PASS;
- compileall = PASS;
- git diff --check = PASS;
- generated feature-row canonical content hash = `3803be1404255652b831627fcd32acaf203f8984da33f70d3784e28dc449b9da`;
- generated feature snapshot shape = 11 frozen origins × 2 drivers = 22 rows.

The canonical contract is `research/fm02/FM02_FEATURE_CONTRACT.json`. FM02 is explicitly non-confirmatory:

`confirmatory_eligible = false`

and does not authorize State Engine, Conditional Backtest, Model Selection, Production Router, current-price inputs, scheduler, alerts, or automatic execution.

FM02 features are horizon-neutral feature-construction outputs. Unknown outcomes remain explicit and are never imputed.

### M1.2 forward gates

FM04 is complete under its exploratory boundary. The next controlled development boundary is:
**M1.2-FM05 Scope Freeze / Data Sufficiency Adjudication.**

FM03 must preserve:

- research-epoch contamination/purity separation;
- PIT-only visibility;
- explicit AVAILABLE / UNKNOWN semantics;
- record-level provenance;
- frozen origin schedule;
- inner-selection / outer-evaluation separation;
- capability-access isolation;
- sealed research manifest requirements;
- independent blind scoring controls.

FM00 remains an exploratory contaminated epoch. FM02 output cannot be relabeled as clean-confirmatory model-selection evidence.

No scheduler, automatic execution, full-market screening, portfolio optimizer/Kelly logic, or unrestricted model family is authorized by this state.

### M1.2-FM03 canonical acceptance

Status: **PASS / MERGED / CANONICAL**

- PR #147; merge commit `007ac477f7e45664c6eb7d4681de5d92c3a16b11`;
- accepted pre-merge head `276d37111c0866ef7a0e69b7ab38aa1e4e1d2788`;
- canonical base main `bc5ca3f2166d946d69b47da27f2213f6e1758a7a`;
- dedicated workflow `IIOS M1.2 FM03 State Engine`, run #2 = SUCCESS;
- 14 / 14 FM03 tests passed;
- real CATL build = 22 rows (11 frozen origins × 2 drivers);
- generated state snapshot canonical content hash `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- independent PIT/provenance audit = PASS;
- output schema, compileall, and diff-check = PASS;
- confirmatory_eligible = false;
- capability principal = `iios_research`;
- capability grant = `m1.2.fm03.state_engine`.

FM03 preserves the frozen FM00 origin schedule and binds the FM02 feature contract and outer-universe lock by canonical content hash. It constructs the orthogonal state dimensions DIRECTION, MOMENTUM, VOLATILITY, SEASONALITY, MEAN_REVERSION_PRESSURE, STRUCTURAL_STABILITY, and DATA_QUALITY using deterministic, non-tuned mappings only.

UNKNOWN remains first-class and is never imputed. Comparison-only states require the immediately prior frozen origin. Feature/state provenance remains bound to FM02 feature rows and upstream DriverSeries record IDs. Downstream Conditional Backtest, Model Selection, Production Router, and Automatic Execution capabilities remain explicitly disabled.

FM03 is DEVELOPMENT_ONLY under the contaminated FM00 research lineage and does not constitute predictive evidence, confirmatory evidence, or production forecasting authorization.

### M1.2-FM04 canonical acceptance
Status: **PASS / MERGED / CANONICAL**

- PR #150;
- accepted CI run #2 = SUCCESS;
- accepted run id `37564860982`;
- 12 FM04 tests passed;
- exact FM02 and FM03 reconstruction passed;
- FM03 state snapshot canonical hash `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- real CATL Conditional Backtest: 406 outer selection units, 0 selected, 406 `NO_SELECTION`, 79 conditional descriptive groups;
- independent PIT/nested-selection/scoring audit = PASS;
- result schema/invariants, compileall, and git diff-check = PASS.

The 0 selected result is a valid sufficiency boundary under the frozen research policy. It is not evidence that a state dimension predicts future outcomes, nor evidence for production model routing. FM04 remains exploratory/contaminated/development-only with `confirmatory_eligible=false`.

Acceptance: `docs/iios/FM04_ACCEPTANCE_2026-10-07.md`.


### M1.2-FM05 canonical acceptance
Status: **PASS / MERGED / CANONICAL**

- PR #156;
- merge commit `215afcc60e649dde331e7f076be809dda716770a`;
- accepted exact head `e6b5a77290409d3e95164007245d57f58246ccd4`;
- dedicated workflow run #1 = SUCCESS;
- run id `37578843014`;
- adjudication: INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION;
- frozen replay: 406 outer selection units, 0 selected, 0 outer evaluated, 406 NO_SELECTION, 79 structural conditional groups, 0 empirical conditional groups.

FM05 is a governance freeze. Result-driven redesign requires a new research epoch and a fresh scope / estimand freeze.


### M1.2-FM07 canonical acceptance
Status: **PASS / MERGED / CANONICAL**

- PR #159;
- merge commit: `549f16ce37058a9b889c159b6392d175bc3397b4`;
- accepted exact head: `d8870e08aded67eac5f6cdda1b811b4d4632eda7`;
- dedicated workflow run: SUCCESS;
- gate decision: **DO_NOT_AMEND_CURRENT_EPOCH**;
- current research epoch: `RE-M12-EXP-CATL-20260930`;
- any scope / estimand / threshold / state / model / metric / origin / universe change requires a new research epoch;
- FM07 does not open a new epoch automatically and adds no model-selection or production capability.


### M1.2 New Research Epoch Design Proposal
Status: **PROPOSED / CANONICAL DESIGN ONLY**

- PR #161;
- merge commit: `8dfcb150583c05f963fa2bd1c50ca9a55aed9935`;
- accepted proposal head: `84666525a71f937e6a759113c86aba7083d18aeb`;
- recommended strategy: cross-sectional universe expansion with threshold preservation;
- current epoch `RE-M12-EXP-CATL-20260930` remains closed and unchanged;
- successor epoch is not activated;
- A02 PIT universe admission is a hard entry gate.


### A02 B-01 Free-First Source Registry
Status: **PASS / MERGED / CANONICAL — ADMISSION REMAINS BLOCKED**

- PR #163;
- merge commit: `3230c7d09f212ab92622ffefc66e684d18262dd0`;
- source registry distinguishes current/control sources from historical PIT-admissible evidence;
- paid sources and Tushare remain optional;
- field-level known_at, raw bytes, metadata, and fail-closed unresolved domains remain mandatory;
- current unresolved admission domains: `st_history`, `industry_history`, `source_vintages`.

The recommended successor M1.2 epoch remains inactive until a complete PIT universe is admitted and independently replayed.


### M1.2-DATA-01 A02 Evidence Supply & Free-First Materialization
Status: **PIPELINE READY / EVIDENCE GATE BLOCKED**

- PR #172;
- merge commit: `ba9eadb852de65bbdca3dded0ed7ac6e6378f06e`;
- isolated-branch CI head: `e3bb284386c340b8cb6cd40cea4ccc26d1a7ace7`;
- PR preflight run: `37590845175`;
- preflight job: `112691698097`;
- CI result: tests PASS; deterministic no-input preflight PASS as an engineering check; DATA-01 raw evidence state remains BLOCKED;
- preflight artifact: `11468790803`;
- artifact digest: `sha256:1b53e6662274f45d4cb1f539df5f8902cf6d0a3657f7d9e5f6f2252e281c1e1e`;
- persistent Library copy: `/iios/A02/A02-data01-preflight-37590845175.zip`.

The batch now has a non-self-certifying intake boundary for an operator-supplied `A02_DELIVERY` ZIP, independent raw-byte SHA-256 verification, manifest identity checks, required-origin/domain checks, and safe ZIP extraction limits.

The latest execution supplied **no external A/B raw evidence bundle**. The independent preflight therefore records:
- terminal `000906cons.xls`: absent from the supplied workspace;
- historical membership states: 7/7 missing;
- B required domains: 6/6 missing;
- A02 admission: `BLOCKED`;
- current-to-historical substitution, retrieved_at-to-known_at substitution, checksum-without-bytes, and self-authored receipt admission all remain forbidden.

This batch does **not** change A02 research semantics and does not unlock FM-02/FM-03 generalization, A02 FM-04/FM-05/FM-06, or model selection.

The actual next evidence objective remains:
```
DATA-01-A  exact historical A bytes
   +
DATA-01-B  complete B free-first PIT evidence bundle
   ↓
DATA-01-C independent raw verification
```

Only after those raw inputs exist will PIT reconstruction and independent replay begin.

Additional DATA-01 discovery on 2026-10-07: the predecessor `benzemaer/convergence-research` public repository exposes a tracked G0-T02 handoff manifest naming a previously materialized historical `000906cons.xls` with the frozen target SHA-256 `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984` and package SHA-256 `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`. The actual ZIP/XLS bytes are documented as non-Git local review material and are not present in the public Git object; therefore this remains a recovery/provenance lead, not admitted evidence. The same predecessor repository exposes security-master/Tushare/tnskhdata candidate contracts and code, but no directly materializable PIT raw bundle satisfying the six B domains. See `docs/iios/A02_HISTORICAL_A_EVIDENCE_SUPPLY_DISCOVERY_20261007.md`.

## 11. DATA-01-B / B3-01 latest evidence state — 2026-10-07

Status: **EVIDENCE GATE BLOCKED / CANONICAL GOVERNANCE RECORDED**

The B3-01 acquisition adjudication and independent preflight evidence were persisted and merged in **PR #185**, merge commit `3ee439fa5a0d51b4f43b8acad53db2f864298996`.

### Latest independently inspected runtime

- workflow: `A02 Exact Raw Materialization`
- run: `37596399460` (#16)
- runtime head: `08adaf484fee64f5448fafcfa8346403abac98a5`
- artifact: `11471840025 / A02-exact-raw-37596399460`
- artifact ZIP SHA-256: `5cad0c1dc67af0638ad4723ffb3a359f49f37b6f83c02a6860e4aea1ac58d0b1`
- workflow conclusion: **failure / fail-closed**
- complete B raw bundle: **NOT PRESENT**
- independent B preflight: **BLOCKED**
- strict exit code: `4`

The runtime artifact contains the current `000906cons.xls` snapshot and acquisition receipt, but no `DELIVERY_MANIFEST.json` and no `B_PIT_SECURITY_MASTER_RAW/` tree.

Independent verification recorded current `000906cons.xls` SHA-256 as:

```text
b3338f5f6fdfd04a72fb42f5444539507b50ee4805c83dabb04ec26e54c3b5fb
```

The frozen historical A target remains:

```text
f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984
```

Therefore the captured A file is not admitted as the historical target.

### B3-01 independent preflight

```text
independent_from_collector = true
raw_bundle_received         = PASS_RECEIVED
artifact_inventory          = PASS
independent_sha256          = PASS
manifest_comparison         = PARTIAL_ONLY
contract/schema             = FAIL
coverage                    = FAIL
provenance                  = FAIL
final                       = BLOCKED
```

Missing B domains:

```text
identity
listing_delisting
common_equity
st_history
industry_history
source_vintages
```

Canonical receipt:

```text
evidence/a02_data01_b/BATCH3_B_INDEPENDENT_PREFLIGHT_RECEIPT_20261007.json
```

### Human intervention boundary

**No human intervention is required for the current engineering steps.**

The next material dependency that requires the user or another data owner is:

```text
ACTUAL_B_RAW_EVIDENCE_BUNDLE
```

Accepted handoff:

```text
A02_DELIVERY ZIP
  + DELIVERY_MANIFEST.json
  + six required B domain raw trees
  + 11 required PIT origins
  + actual raw bytes
  + source-vintage / known_at evidence
  + license / redistribution status
```

A data-owner/vendor PIT export is also acceptable when it preserves the same evidence chain.

Until that bundle exists, `DATA-01-C`, `DATA-02`, A02 admission, cross-security epoch activation, and model selection remain locked.

The canonical rule is unchanged:

```text
no bytes → no hash admission
no known_at evidence → no PIT admission
no complete B bundle → no DATA-01-C
```

## 12. MVP Fast Launch status — 2026-10-07

Canonical launch plan:

docs/iios/IIOS_MVP_FAST_LAUNCH_PLAN_v0.1.md

Decision:

Investment Core = LIVE TESTING
Research Track A02 / CSI800 = NON-BLOCKING

Immediate sequence:

PILOT-00 Baseline / Test Protocol
→ PILOT-01 CATL + 科伦 controlled pilot
→ PILOT-02 fresh user-selected candidate
→ PILOT-03 observed-friction remediation
→ PILOT-04 independent replay
→ MVP Pilot Acceptance

The pilot starts from the already accepted company-level Investment Core and does not require CSI800 membership or A02 evidence.

Human intervention is required only for the fresh real-company pilot inputs: actual candidate-specific evidence, research cutoff/as-of, price/valuation evidence, and relevant portfolio constraints.

Hard stop conditions remain unchanged: any P0 authority/PIT/provenance/semantic bypass, human-approval bypass, current-to-historical substitution, publication/report mutation of canonical state, or non-reproducible lifecycle replay blocks pilot continuation.


## 13. PILOT-01 controlled real-company pilot — 2026-10-07

Status: **TECHNICAL PASS / HUMAN OBSERVATION PENDING**

Exact execution baseline:
- main: `a14e561b266fb288a696bb9c70d853a2e6e218f2`
- pilot workflow run: `37605725511`
- pilot job: `112740590739`
- dedicated pilot CI conclusion: **SUCCESS**
- pytest: **57 passed**
- compileall: **PASS**
- git diff --check: **PASS**
- CATL E2E: **PASS**
- 科伦 E2E: **PASS**
- full lifecycle E2E: **PASS**

Controlled case outcomes:
- CATL / 300750: `REVIEW_REQUIRED`, new capital `FALSE`, Quality `CONDITIONAL`, Trust `REVALIDATION`.
- 科伦 / 002422: `REVIEW_REQUIRED`, new capital `FALSE`, Quality `CONDITIONAL`, primary valuation `SOTP`; lifecycle replay `PASS`, monitoring `VALID`, validation `PASS`, publication/report QA `PASS`, automatic execution `FALSE`.

PILOT-01 proves the current technical Investment Core path works on two materially different real-company cases. It does **not** by itself prove operator usability or investment performance.

Human observation is now the explicit next gate:
- review the generated outputs;
- identify confusing, missing, or operationally burdensome elements;
- record what information had to be manually reconstructed;
- record whether the final report/decision is practically usable.

Human observations become PILOT-03 candidate findings only; they cannot silently change normative semantics.

PILOT-02 fresh-candidate testing remains gated on completion of this human observation step.

A02 / CSI800 remains non-blocking to Investment Core testing.


## 14. PILOT-02 fresh candidate — 浙江新和成股份有限公司 — 2026-10-07

Status: **TECHNICAL PASS / HUMAN OBSERVATION PENDING**

Owner-directed fresh-candidate test:
- company: 浙江新和成股份有限公司
- symbol: 002001.SZ
- market: CN-A
- cutoff / as-of: 2026-10-07
- security classification: NON_FINANCIAL
- research weighting: cyclical 70% + growth 30%
- weighting is explicit user input, not evidence

Sequencing note:
- PILOT-02 was started at the user's explicit direction before the previously planned PILOT-01 human-observation gate was completed.
- This is an owner-directed sequencing override, not a normative Investment Core change.

Accepted exact execution:
- workflow: `IIOS PILOT-02 — Xinhecheng Fresh Candidate`
- run #23
- run id `37627712090`
- accepted head `80aa3b6489963d51e65b8ea34c3c2325614ea42e`
- overall: SUCCESS
- evidence capture: PASS
- Investment Core E2E: PASS
- acceptance assertions: PASS
- artifact id: `11484414188`
- artifact ZIP SHA-256: `dc27e134749d0689cab1afe01533e6cf8dcc36dbfe4c7e52c3f16620e5b685fc`

Market-date rule:
- 2026-10-07 is non-trading;
- latest tradable date used: 2026-09-30;
- observed close: CNY 25.95;
- no current 2026-10-07 price was fabricated.

Accepted raw evidence:
- CNINFO H1 report SHA-256: `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e`
- Tencent historical K-line SHA-256: `637bd885980763b1eea5ce63e7b255746e4a4c6ade4ec8981dabbad75635405b`
- ChinaClear holiday-page SHA-256: `756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7`
- all three admitted as exact bytes

Canonical result:
- Quality: CONDITIONAL
- Trust: REVALIDATION
- Decision: REVIEW_REQUIRED
- New capital allowed: FALSE
- Human approval required: TRUE
- Automatic execution: FALSE
- Expected annualized return: 20.17%
- Fundamental 15% target: PASS
- Required return 10%: PASS
- Risk / max loss 25%: PASS
- Canonical target entry price: CNY 26.60
- Decision replay: PASS
- Monitoring evaluation: VALID
- Validation: PASS
- Publication QA: PASS
- Human Report QA: PASS
- report deterministic replay: TRUE

Red-team findings during this pilot:
1. The initial Bear valuation of CNY 19.00/share implied a 26.78% loss at CNY 25.95, correctly failing the 25% risk gate. The fixture was corrected to CNY 19.95/share; no risk semantics were changed.
2. The initial Yahoo historical-price endpoint returned HTTP 429, and the replacement free historical endpoints were tested fail-closed. The accepted run used Tencent historical K-line raw bytes.
3. The first canonical Decision Admission attempt exposed a source-provenance mismatch in the test harness; the case declaration was corrected to the admitted Tencent source before acceptance.

Interpretation:
- The candidate cleared return/risk mathematics but did not obtain buy permission because Trust remained REVALIDATION.
- The result therefore confirms separation of return attractiveness from Trust/evidence authority.
- This is technical pipeline evidence, not investment performance evidence or a capital-approval recommendation.

Human observation remains pending:
- review the generated artifact/report;
- record confusing or missing decision-critical information;
- record manual reconstruction burden;
- record workflow/report usability issues.

Human observations become PILOT-03 candidate findings only. No normative investment semantics are changed by this pilot.

A02 / CSI800 remains non-blocking to Investment Core testing.


## 15. PILOT-03 observed-friction remediation — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #192
- merge commit: `7bf304158116577a7676366a65e02c7caa87d499`
- no Investment Core production semantic code changed
- remediation limited to pilot CI hygiene and regression discipline

Accepted findings:
1. PILOT-02 duplicate execution was caused by the branch-specific `push` trigger in the pilot workflow. PILOT-03 removed that trigger; `pull_request` remains the canonical review path and `workflow_dispatch` remains available for explicit reruns.
2. The initial Bear scenario exceeded the declared 25% maximum-loss boundary. PILOT-02 correctly failed the Risk gate; PILOT-03 added regression coverage for Bear/Risk input discipline without changing Risk semantics.
3. The first canonical Decision Admission source mismatch was a test-harness provenance declaration defect. Existing canonical price binding correctly rejected it; no canonical binding rule was weakened.

External endpoint instability remains non-canonical operational behavior:
- Yahoo HTTP 429, alternative endpoint 502/connection reset were observed during acquisition;
- the runtime remained fail-closed;
- accepted PILOT-02 evidence was later captured and admitted from an exact Tencent historical K-line response.

PILOT-03 independent acceptance:
- Scope Check: PASS
- compileall: PASS
- targeted regression suite: PASS
- git diff --check: PASS
- canonical Trust precedence: preserved
- canonical current-price provenance binding: preserved
- Risk semantics: preserved
- Human Approval boundary: preserved
- automatic execution: remains disabled
- scheduler / alerts: remain disabled
- A02 / CSI800 remains non-blocking

Targeted regression outcome:
- 20 tests passed across:
  - PILOT-02 Bear/Risk discipline
  - canonical current-price binding
  - Decision Kernel Trust / Quality precedence

PILOT-03 does not modify the accepted PILOT-02 investment result. It only closes observed pilot-friction defects.

PILOT-03 does not modify the accepted PILOT-02 investment result. It only closes observed pilot-friction defects.

PILOT-04 is now **PASS / MERGED / CANONICAL** and closes the planned clean-replay boundary.

Human usability observations from PILOT-01 / PILOT-02 remain separate operator evidence and cannot be inferred from automated regression.


## 16. PILOT-04 independent clean replay — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #194
- merge commit: `f3405f66e74a091e4f60aac0ddb5c6d1e1ad4700`
- canonical starting main SHA: `79c5576bc4c63d3989a252401683c6691e66d998`
- no Investment Core production semantic code changed
- replay harness / pilot acceptance evidence only

Accepted independent replay:
- workflow: `IIOS PILOT-04 — Xinhecheng Independent Clean Replay`
- accepted run #3
- run id: `37632285110`
- job id: `112829358751`
- overall: **SUCCESS**
- all 11 acceptance steps completed successfully

Canonical clean-base proof:
- PR base SHA = `79c5576bc4c63d3989a252401683c6691e66d998`
- remote `origin/main` at replay = `79c5576bc4c63d3989a252401683c6691e66d998`
- replay was not based on a diagnostic branch

Fresh evidence:
- CNINFO H1 report raw SHA-256 reproduced exactly:
  `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e`
- ChinaClear holiday-page raw SHA-256 reproduced exactly:
  `756241e1e86515b5a9bbfafdede05055344c9ac9cf7dcba38a75141ed2096fa7`
- fresh Tencent raw SHA-256:
  `3716fea96259842264ee47a8c04a69c1515b127c3d4617ab803026398cb0caa5`
- normalized 2026-09-30 historical day-row SHA-256 matched accepted PILOT-02:
  `cdbe0bfc375a5d84ed99d59a3ca925e4488607d8ad3d4df57f7b5d88962473be`
- observed close remained CNY 25.95
- fresh Tencent raw-vintage differs because the endpoint carries dynamic transport metadata; this does not alter the normalized economic observation

Replay result:
- stable Decision/lifecycle semantic fingerprint:
  `acd3943850ed38ca001e4a636ba8fea6e5cf69e23b0cfb820a8ad2e398408af2`
- Trust = REVALIDATION
- Quality = CONDITIONAL
- Decision = REVIEW_REQUIRED
- Primary reason = TRUST_NOT_PASS_REQUIRES_REVIEW
- New capital = FALSE
- Human approval = TRUE
- Automatic execution = FALSE
- Expected annualized return = 20.1734104046%...
- Fundamental target / required return / risk gates = PASS
- Target entry price = CNY 26.60
- Decision ID = `CN-A-002001-r001`
- Revision = 1
- Monitoring = VALID
- Validation = PASS
- Lifecycle replay = PASS
- Machine Publication QA = PASS
- Human Report QA = PASS
- deterministic report replay = TRUE

Fresh lineage hashes are intentionally different from PILOT-02 because the admitted Tencent raw source-vintage is new. Internal binding and deterministic report QA both passed.

Run #2 diagnostic:
- The first PILOT-04 attempt failed only because the new replay receipt omitted `price_source_ref`, required by the existing canonical current-price admission path.
- This was classified as a pilot-harness defect, not an Investment Core semantic regression.
- The corrected receipt now binds source location, raw SHA and normalized historical-observation projection.

PILOT-04 conclusion:
**Independent clean replay PASS.**

Next canonical boundary:

**MVP Pilot Acceptance**

A02 / CSI800 remains non-blocking to company-level Investment Core testing.
Human usability evidence remains separate from technical replay acceptance.

## 17. MVP Pilot Acceptance — human gate preparation — 2026-10-07

Status: **TECHNICAL GATE READY / HUMAN ACCEPTANCE REQUIRED**

The company-level Investment Core remains on the MVP critical path after PILOT-04 independent clean replay. The final MVP Pilot Acceptance boundary is now split between machine-verifiable technical evidence and explicit operator usability acceptance.

This batch hardens the Human Report presentation layer without changing Investment Core decision semantics:
- Risk / Portfolio contract data is rendered as investor-facing bullets instead of raw internal JSON;
- Report QA now detects JSON-like machine field dumps in the main report and fails closed;
- regression coverage prevents reintroduction of the defect;
- PILOT-04 clean-replay CI is isolated from ordinary PRs because its canonical-base assertion is intentionally tied to the dedicated historical replay baseline.

Technical acceptance remains supported by PILOT-01 / PILOT-02 / PILOT-03 / PILOT-04 evidence. The remaining MVP acceptance blocker is the real operator's human usability attestation. CI success must not be used as a substitute for that attestation.

A02 / CSI800 remains non-blocking to company-level Investment Core MVP acceptance.

## 18. B0 — LLM Canonical Execution Governance Boundary Freeze — 2026-10-07

Status: **GOVERNANCE CONTENT FROZEN / CANONICAL ON MAIN AFTER MERGE**

Purpose:

The 2026-10-07 P0 LLM red-team findings are now converted into a formal governance boundary without changing Investment Core economic formulas or normative decision semantics.

Canonical execution constitution:

```text
explicit / deterministic rules
        → Code / Script

ambiguous / semantic / deep reasoning
        → LLM / expert reasoning

LLM semantic output
        → Typed Semantic Artifact + provenance
        → Deterministic Admission
        → Canonical State
```

Authority separation:

```text
LLM    = Reasoning Authority
Code   = Rule / Permission Authority
Human  = Capital / Approval Authority
```

Frozen mandatory boundary:

```text
User Natural-Language Request
→ Canonical Research Orchestrator
→ Research Case / Run Envelope
→ Evidence Acquisition + Evidence Admission
→ LLM Semantic Workbench
→ Typed Semantic Artifacts + semantic provenance
→ Deterministic Admission / consistency
→ Canonical State
→ Decision Kernel
→ Decision Admission
→ Human Approval
→ Machine Publication
→ Human Report
→ Monitoring / Validation / Replay
```

Confirmed P0 requirements:
- P0-LLM-001: natural-language investment requests must not bypass the Canonical Research Orchestrator;
- P0-LLM-002: Reality, Trust, Quality, Thesis, Value Drivers, Forecast reasoning, Valuation Proposal, MIE interpretation, Risk interpretation and Positioning interpretation require an explicit semantic producer boundary;
- P0-LLM-003: evidence provenance does not substitute for semantic provenance; producer identity/version/stage/input-output lineage are required for canonical semantic admission;
- P0-LLM-004: PILOT-01~04 do not prove real natural-language LLM conformance because their semantic inputs were preconstructed.

Canonicality rule:

```text
valid Evidence Provenance ≠ valid Semantic Provenance

missing / invalid IIOS_RUN_RECEIPT
→ NON-CANONICAL ANALYSIS / BLOCKED
```

Required `IIOS_RUN_RECEIPT` fields include run/case identity, market/symbol, cutoff/as-of, engine version, research/evidence hashes, semantic artifact hashes, forecast/valuation/return-risk-portfolio/decision admission hashes, decision revision, publication hash and report hash.

B0 prohibitions:
- no economic formula or return/risk semantic changes;
- no new universal MIE BUY gate;
- no automatic trading;
- no self-declared external JSON as canonical semantic state;
- no claim that existing pilots prove natural-language-to-canonical conformance;
- no B1/B2/B3 implementation changes under B0.

B1 unlock target:

```text
B1 — Canonical Research Orchestrator + Semantic Contract Design
```

B1 requires a successor versioned design covering the orchestrator/stage machine, typed semantic artifact contract, producer authenticity, run receipt, authority boundaries and Haomai conformance tests.

References:
- governance record: `docs/iios/B0_LLM_CANONICAL_EXECUTION_GOVERNANCE_FREEZE_20261007.md`;
- P0 findings: `docs/iios/P0_LLM_CANONICAL_EXECUTION_AUDIT_20261007.md`;
- P0 findings SHA-256: `b70d83e9920e4ef9b2b879e727fa427d057b2ffa96cf6c53ddd73329a1705ea1`;
- governance record SHA-256: `eacef7ec2ec40cfc716a44ba8374bcdc800aeebba0a2d1553e852e8a476f7191`.

Canonical Git promotion record:

```text
canonical main baseline = 0839dfe972f2e1451a9cc8a8ce3f909020b8b784
B0 governance commit     = de6e67904a644266133fd3436dbc7f2567e92e1b
repair branch            = audit/p0-llm-canonical-execution-20261007
promotion method         = Git Data tree → commit → ref
```

This section is the canonical Current State Index amendment for the P0 LLM governance freeze.
## B1-LCE — Canonical Research Orchestrator — 2026-10-07

Status: **PASS / MERGED / CANONICAL**

Parent canonical main: `de1fba8ccee403ce219455a35b12ea6fd712a0cb`
Implementation head: `8bf658b65ce7430d814046f1301af9915f3dea2c`
PR #198
Merge commit: `f34c3325e6cfab75303f944124330289c1cb9444`
Canonical main after merge: `f34c3325e6cfab75303f944124330289c1cb9444`

B1-LCE establishes the first production control-plane boundary required by P0-LLM-001 through P0-LLM-004.

Implemented:
- `CanonicalResearchOrchestrator` run-envelope authority;
- monotonic stage machine with fail-closed bypass rejection;
- append-only stage receipts carrying input/output refs, hashes, producer type/version, cutoff and timestamps;
- semantic-stage producer-type boundary;
- exact-stage authorization for downstream engine invocation;
- complete-run `IIOS-RUN-RECEIPT-0.1` construction;
- `IIOS-LLM-SEMANTIC-ARTIFACT-0.1` common envelope schema;
- regression coverage for stage bypass, semantic producer bypass, canonical completion and direct/non-canonical execution.

This is a control-plane implementation only. It does not generate economic judgments and does not modify Investment Core v0.3 formulas, Trust/Quality/Decision semantics or automatic-execution boundaries.

Local acceptance: **8 tests PASS / compileall PASS / JSON syntax PASS**.

Dedicated remote workflow: `.github/workflows/iios_b1_llm_orchestrator.yml` — Run #1 `37644825682` = SUCCESS.

The existing lower-level Investment Core modules remain directly unit-testable, but product-declared canonical investment execution must be bound to the orchestrator. B2 will implement the actual LLM Semantic Workbench and semantic producer admission against admitted evidence.

Next canonical gate:

```text
B2 — LLM Semantic Workbench + Semantic Producer Admission
```
