# IIOS MVP Fast Launch Plan v0.1 — 2026-10-07

Status: CANONICAL LAUNCH PLAN
Decision: Investment Core enters user-pilot; A02 / cross-sectional forecast research is a non-blocking parallel track.

## 1. Goal

The immediate goal is to start testing IIOS as an investment operating product, not to keep expanding research infrastructure.

Launch path:
Investment Core
→ controlled real-company pilot
→ fresh user-selected candidate
→ fix only observed P0/P1/P2 problems
→ independent replay
→ MVP pilot acceptance

The pilot does not prove investment performance. It tests whether the system can execute the intended research-to-decision workflow reliably.

## 2. Existing sufficient baseline

Canonical main already has the accepted company-level chain through C8:

Evidence / Trust / Reality / Quality
→ Value Drivers
→ Valuation
→ Independent Forecast
→ Return / Required Return / Risk
→ Expectation Gap
→ Position / Sizing
→ Decision
→ Human Approval
→ Execution Receipt
→ Monitoring
→ Validation / Replay
→ Machine Publication
→ Human Report
→ Independent Red-team

Real-company acceptance already exists for:
- CATL / 300750;
- 科伦药业 / 002422.

No new investment semantics are required to start testing.

## 3. Critical-path separation

### Investment Core — critical path

PILOT-00 Baseline / test protocol
→ PILOT-01 CATL + 科伦 controlled pilot
→ PILOT-02 fresh user-selected candidate
→ PILOT-03 observed-friction remediation
→ PILOT-04 repeatability / clean replay
→ MVP Pilot Acceptance

### Research Track — non-blocking

A02 exact A + B evidence
→ DATA-01-C
→ DATA-02 / DATA-03
→ new research epoch
→ cross-sectional forecast research

A02 failure or delay MUST NOT prevent company-level Investment Core testing.

## 4. PILOT-00 — Baseline / test protocol

Freeze:
- exact canonical main SHA;
- case/evidence versions;
- engine/schema versions;
- cutoff/as-of;
- publication/report identity;
- human approval boundary.

Questions:
- can a case be reconstructed from the recorded inputs?
- are material inputs source/provenance bound?
- are current and historical evidence boundaries preserved?

No new valuation model, market-model family, A02 universe logic, scheduler, alerting or automatic execution is introduced.

## 5. PILOT-01 — Controlled real-company pilot

Cases:
1. CATL / 300750.
2. 科伦药业 / 002422.

Test the operator workflow:

candidate intake
→ evidence review
→ thesis
→ trust / quality / reality
→ valuation / forecast
→ return / required return
→ risk
→ expectation gap when admissible
→ decision
→ human review
→ position package
→ publication
→ human report
→ monitoring / validation

Record:
- what the user must provide;
- what the system derives;
- where judgment is required;
- where the system blocks;
- whether report output is understandable;
- whether replay is deterministic.

Acceptance:
- no gate bypass;
- AI proposal and human approval stay separate;
- no automatic ordering;
- BLOCKED / UNKNOWN remain visible.

## 6. PILOT-02 — Fresh user-selected candidate

The candidate does not require CSI800 membership or A02 evidence.

Required material:
- company/ticker;
- market;
- research cutoff;
- as-of date;
- available primary evidence;
- price / valuation evidence;
- relevant portfolio constraints.

A missing input must produce a bounded BLOCKED / REVIEW_REQUIRED state, never a fabricated substitute.

This is the first real-world test of the original candidate-driven IIOS product boundary.

## 7. PILOT-03 — Remediation discipline

Only pilot-observed problems enter this batch.

P0 = safety / authority / PIT / provenance / semantic bypass
P1 = materially blocks workflow
P2 = usability / report / operational friction
P3 = research convenience

P0 blocks pilot immediately.
P1 is fixed before widening the pilot.
P2 is grouped after repeated evidence.
P3 remains backlog.

Every fix gets a narrow PR and deterministic regression tests.

## 8. PILOT-04 — Independent repeatability

For the same exact inputs verify:

same inputs
→ same decision semantics
→ same publication
→ same report
→ same lifecycle replay

Then perform clean replay from persisted inputs instead of generated outputs.

Any mutation of a historical decision, hidden dependency, or replay mismatch blocks acceptance.

## 9. MVP Pilot Acceptance

Required:
- at least two materially different real companies exercised;
- at least one fresh user-selected candidate;
- report understandable to the operator;
- Decision → Human Approval → Execution Receipt → Monitoring → Validation linked;
- no unresolved P0;
- deterministic replay passes;
- no automatic execution;
- no evidence substitution;
- no current-to-historical substitution;
- no LLM authority escalation.

## 10. 000906cons / A02 boundary

000906cons is classified as:

RESEARCH-TRACK / HISTORICAL-UNIVERSE-EVIDENCE

It is NOT:

INVESTMENT-CORE / UNIVERSAL DEPENDENCY

Therefore the lack of historical CSI800 membership must never block:
- company-level research;
- fresh candidate testing;
- report testing;
- lifecycle testing;
- human execution receipt testing;
- monitoring / validation testing.

A02 remains a dependency only for the specific cross-sectional research program that explicitly selects CSI800 as its historical universe.

## 11. Human intervention

Engineering: no intervention required unless an external capability/credential is genuinely unavailable.

Fresh real-company pilot: human intervention is required to provide actual candidate-specific evidence and portfolio constraints. The system must never manufacture those inputs.

## 12. Execution decision

From this point forward:

Investment Core = LIVE TESTING
Research Track = NON-BLOCKING

Do not add more research infrastructure before obtaining actual pilot evidence of a product gap.

The next engineering batch is PILOT-00, followed immediately by PILOT-01.
