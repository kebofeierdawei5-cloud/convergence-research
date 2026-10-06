# IIOS Stage C — Productization / Generalization / Closed-loop Validation Plan v0.1

Date: 2026-10-06
Status: CANONICAL ROADMAP
Basis: canonical C4 implementation merge `07d45c18df8df9100d4866dd5f92fa95ccdb7186`.

## 1. Purpose

This plan records the next development stage after TR-03 Validation / Replay.

The project is transitioning from building core analytical/runtime capability to:
- productizing the canonical decision output;
- proving cross-company generalization;
- completing the expectation-gap and positioning layers that are part of the original IIOS investment objective;
- completing the decision-to-monitoring-to-validation lifecycle;
- performing final independent full-system acceptance.

The objective is not to maximize module count. Each batch must close a concrete product or investment-decision capability gap.

## 2. Current canonical baseline

Completed / canonical:

- G2 R10 Reference Governance Runtime = FROZEN
- B0 Authority Repair = PASS
- B1 Investment Semantics v0.3 = FROZEN
- CORE-00 through CORE-04 = PASS / MERGED
- 300750 real decision E2E = PASS / REVIEW_REQUIRED / NO NEW CAPITAL
- A0 State Cleanup = PASS / MERGED
- A1 Company-side Evidence Closure = PASS / MERGED
- RP-01 Risk / Portfolio Contract = MERGED
- DR-01 Decision Revision / Human Approval = PASS / MERGED
- DR-02 Persistence / CLI = MERGED
- TR-01 Trigger Contract / Event Semantics = PASS / MERGED / CANONICAL
- TR-02 Monitoring State = PASS / MERGED / CANONICAL
- TR-03 Validation / Replay = PASS / MERGED / CANONICAL
- C4 Expectation Gap Production Integration = PASS / MERGED / CANONICAL

Current 300750 result:
- Quality = CONDITIONAL
- Trust = REVALIDATION
- Expected Annualized Return_H ≈ 14.20%
- Required Return = 10%
- MIE = OPTIONAL_EXPLANATORY / absent
- Decision = REVIEW_REQUIRED
- New capital = FALSE

## 3. Development strategy

From this stage onward, development follows:

Canonical core
→ productization
→ cross-company acceptance
→ semantic expectation-gap completion
→ positioning / sizing
→ execution evidence
→ full lifecycle E2E
→ independent final red-team

Do not resume sideways expansion of P3/P4/MIE model families unless a separately demonstrated semantic gap requires it.

## 4. Batch roadmap

### C0 — Governance Hygiene / Stage Baseline

Objective:
- reconcile README and continuity surfaces with current canonical semantics;
- make canonical / historical / diagnostic boundaries explicit;
- record the completed TR-01/TR-02/TR-03 chain and current next boundary;
- strengthen Git/CI enforcement where practical.

Acceptance:
- current semantics have one authoritative entry point;
- stale documents cannot plausibly be mistaken for current state;
- new development starts from canonical main + PROJECT_STATE_INDEX.

Out of scope:
- investment-semantic changes;
- new valuation/MIE capability;
- scheduler/alerts.

### C1 — Machine Publication

Objective:
- publish a stable machine-readable projection of the canonical Decision Revision.

Core requirements:
- explicit revision identity;
- as-of/cutoff;
- AI/Human decision separation;
- Trust/Quality/Thesis/Valuation/Return/Risk/Portfolio state;
- active Trigger / Monitoring / Validation references;
- engine/schema/provenance identity;
- immutable publication versioning.

Acceptance:
- an external consumer can read the decision without parsing Markdown or internal storage;
- publication cannot mutate or replace canonical decision state;
- publication history remains auditable.

Out of scope:
- changing Decision Kernel semantics;
- automatic execution;
- scheduler/alerts.

### C2 — Human Report + Report Quality Gate

Objective:
- produce a controlled investor-facing report from the canonical decision.

Required report structure:
1. Investment conclusion
2. Thesis
3. Trust / Evidence
4. Reality / Quality
5. Value Drivers
6. Forecast
7. Valuation
8. Market Implied Expectation
9. Expectation Gap
10. Risk / Thesis Breaks
11. Decision / Position
12. Monitoring / Triggers
13. Audit appendix

Quality Gate:
- deterministic numeric consistency;
- decision/action consistency;
- Trust/Risk/Portfolio consistency;
- as-of/cutoff/revision consistency;
- trigger consistency;
- readability and contradiction checks.

Acceptance:
- report is independently readable;
- report is a projection only and cannot modify Decision;
- Report Blocked does not silently alter investment state.

### C3 — Second Company Acceptance

Default candidate:
- 科伦药业

Objective:
- prove that the architecture is not CATL-specific.

Acceptance must exercise materially different:
- economic structure;
- evidence chain;
- valuation path;
- forecast assumptions;
- risk structure;
- report/publication path;
- monitoring/validation lifecycle.

A successful C3 requires a real end-to-end case, not merely unit-test fixtures.

### C4 — Expectation Gap Production Integration

Objective:
- reconnect the already-built MIE substrate to the original IIOS expectation-difference objective.

Canonical chain:
Independent Fundamental Forecast / Intrinsic Value
+
Market Implied Expectation
→ semantic compatibility
→ Expectation Gap
→ Expected Return / decision policy

Hard conditions:
- same economic variable;
- same unit;
- same basis;
- same horizon;
- explicit comparison direction;
- valid PIT/provenance;
- no forced choice when market interpretation is materially ambiguous.

Failure states:
- BLOCKED;
- AMBIGUOUS;
- INCOMPATIBLE;
- NO_FEASIBLE_SOLUTION;
- UNIQUE_MODEL / DECISION_GRADE only when evidence supports it.

Do not infer market truth merely from algebraic inverse solvability.

Acceptance:
- valid comparable expectations can generate a semantic gap;
- incompatible expectations produce no scalar gap;
- the result reconnects to the existing B1 return semantics without additive thresholds;
- no new P3/P4 model family is required.

### C4 — Expectation Gap Production Integration
Status: **PASS / MERGED / CANONICAL**

Implementation:
- PR #105;
- merge commit: `07d45c18df8df9100d4866dd5f92fa95ccdb7186`;
- dedicated C4 Actions run #7 = SUCCESS on exact head `aacf1c0cc715697bfac2aa0bae5e2f0a4c899ad2`;
- 75 tests passed;
- executable acceptance harness = 7 / 7 PASS;
- compileall = PASS;
- git diff --check = PASS.

Acceptance record: `docs/iios/C4_ACCEPTANCE_2026-10-06.md`.

### C5 — Positioning / Sizing

Objective:
- complete the original “基本面 × 流动性 × 博弈” architecture.

Positioning hierarchy:
Market Regime
→ Industry Sentiment
→ Stock Structure
→ Holder / Capital Structure
→ Crowding / Supply Pressure

Permitted role:
- timing;
- entry/add/reduce zones;
- position sizing within portfolio constraints.

Prohibited role:
- rewriting Quality;
- rewriting Thesis;
- rewriting intrinsic value;
- bypassing Trust or Risk.

Initial sizing surface:
- initial position;
- target position;
- maximum position;
- entry zone;
- add zone;
- reduce zone;
- hard exposure limit.

Do not productionize Kelly/optimizer formulas in this batch.

Acceptance:
- positioning affects only timing/sizing outputs;
- fundamental decision semantics remain unchanged;
- missing/ambiguous positioning data fails closed for the affected sizing permission.

Canonical C5 acceptance:
- PR #108 merged as `cdf998cd21776363914f178e648f03ec0c1539f8`;
- dedicated C5 CI #7 passed on exact head `f9758beb683bba044fc9a153018050fa4ff09d9`;
- acceptance record: `docs/iios/C5_ACCEPTANCE_2026-10-06.md`.

Status: **PASS / MERGED / CANONICAL**

Implementation PR: #108
Merge: `cdf998cd21776363914f178e648f03ec0c1539f8`
Dedicated acceptance: C5 workflow #7 SUCCESS on exact head `f9758beb683b3ba044fc9a153018050fa4ff09d9`; 86 tests passed; acceptance harness 9 / 9 PASS; compileall and git diff-check PASS.
Acceptance record: `docs/iios/C5_ACCEPTANCE_2026-10-06.md`.

### C6 — Human Execution Receipt

Objective:
- record what the human actually executed after approval.

Receipt fields should bind:
- decision revision;
- approved action;
- execution timestamp;
- executed quantity/position;
- executed price when available;
- execution status;
- human actor identity.

Acceptance:
- execution evidence is immutable;
- execution cannot modify historical AI/Human decision records;
- no automatic order path exists.

### C7 — Full Lifecycle E2E

Objective:
- prove the complete operating loop.

Canonical lifecycle:
Decision Revision
→ Human Approval
→ Execution Receipt
→ Active Trigger
→ Trigger Event
→ Monitoring State
→ Evaluation Receipt
→ Validation
→ Replay
→ New Run
→ New Decision Revision
→ Machine Publication
→ Human Report

Acceptance must prove:
- historical revisions are append-only;
- Monitoring does not mutate Decision directly;
- a changed investment decision requires a new Run + new Revision;
- Validation independently recomputes from source;
- replay reproduces persisted state;
- Publication and Report remain projections.

### C8 — Final Independent Red-team / MVP Acceptance

Objective:
- perform a full-system adversarial acceptance using real companies.

Minimum real-company set:
- CATL / 300750
- 科伦药业

Attack surfaces:
- PIT leakage;
- silent evidence substitution;
- Trust / Quality bypass;
- Forecast contamination;
- valuation semantic mismatch;
- MIE false-identifiability;
- Expectation Gap variable mismatch;
- 15% return-gate bypass;
- Required Return bypass;
- revision overwrite;
- approval mismatch;
- stale/superseded triggers;
- Monitoring history tampering;
- replay mismatch;
- Publication/Report drift;
- LLM authority escalation;
- cross-company coupling;
- hidden automatic execution.

Final acceptance target:
- full product DoD across both companies;
- independent red-team PASS;
- no unresolved critical semantic or authority bypass.

## 5. Parallel Forecast Research Track

The Forecast Research Track remains independent from Investment Core productization.

Current state:
- FM-00 = PASS;
- FM-01 code contract = PASS;
- FM-01 data population = BLOCKED_DATA_INGRESS.

Next sequence:
FM-01 exact source admission
→ FM-02 PIT Feature Builder
→ FM-03 Driver State Engine
→ FM-04 Conditional Backtest
→ FM-05 research scope freeze
→ model/router research
→ prospective shadow validation.

Research results must not be relabeled as clean confirmatory evidence without the required research-epoch controls.

## 6. Explicitly prohibited on the main critical path

Until C8 acceptance, do not:
- add more P3/P4 market-model families;
- broaden to full-market stock screening;
- implement automatic portfolio optimization;
- freeze production Kelly sizing;
- introduce Kafka/event-bus/microservice infrastructure;
- implement automatic order placement;
- implement scheduler or alerts;
- allow report/publication to mutate decisions;
- allow Monitoring to bypass the Decision Kernel.

Scheduler / alerts require a separate future governance batch after the Validation boundary is already canonical.

## 7. Batch acceptance discipline

Every batch must declare:
- Objective;
- User Value;
- Product Surface;
- Tests / Acceptance;
- Out of Scope.

Preferred sequence:
- one narrow PR per batch;
- start from current canonical main;
- dedicated CI;
- negative/red-team tests where applicable;
- canonical acceptance only after merge and evidence review.

## 8. Stage completion definition

Stage C is complete only when:
1. Machine Publication is productionized;
2. Human Report + Report Quality Gate pass;
3. at least one materially different second company passes;
4. semantic Expectation Gap is production-usable when evidence permits;
5. positioning/sizing is implemented without contaminating fundamental semantics;
6. Human Execution Receipt exists;
7. full lifecycle E2E passes;
8. final independent red-team passes;
9. no automatic execution/scheduler/alerts capability has been introduced without separate authorization.

## 9. Next immediate batch

Current execution state after C2 acceptance:
C0 — Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL
→ C1 — Machine Publication = PASS / MERGED / CANONICAL
→ C2 — Human Report + Report Quality Gate = PASS / MERGED / CANONICAL
→ C3 — Second Company Acceptance = PASS / MERGED / CANONICAL
→ C4 — Expectation Gap Production Integration = PASS / MERGED / CANONICAL
→ C5 — Positioning / Sizing

C5–C8 follow only after the preceding acceptance boundaries are satisfied.

Parallel FM Research remains separate and does not block Stage C productization.
