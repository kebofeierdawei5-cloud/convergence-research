# B0 ACTIVE-PLAN NOTICE — 2026-10-04

This document is retained as the consolidated post-red-team historical roadmap. **Its active execution sequence is superseded by the B0/B1 repair program.**

Read first: `docs/iios/B0_AUTHORITY_AUDIT_FREEZE_2026-10-04.md`

Current repair baseline: `d209b33b7f922866f2fdc1190785c27edb8a28e4`
Current next gate: **B1 Investment Semantics v0.3**
P4-F remains retained as conditional explanatory infrastructure. No new P5/P6 production decision capability is to be added until B7 validation of the repaired semantics.

The roadmap below remains useful as historical design context and dependency evidence, but its old `P5`-first immediate-next-step wording must not be used to bypass B0/B1.

---

# IIOS Consolidated Post-Red-Team Development Plan — 2026-10-04

## 1. Consolidated audit conclusion
Red-team round 1 and round 2 converge on one principle: P3 is an evidence-backed deterministic market-model inverse baseline, not proof that the market's true pricing model has been unconditionally identified.

Therefore:
- P1 / P2-A / P2-B / P3-A / P3-B remain accepted engineering capabilities.
- P3 IDENTIFIABLE is candidate-set-conditional and evidence-bound.
- P3 complex-model outputs are conditional inverse results, not automatically full multidimensional feasible assumption sets.
- Historical min/max ranges remain deterministic admissibility baselines, not calibrated descriptions of valuation behavior.
- Variable/unit binding is necessary but P4/P5 must also preserve period, horizon, accounting basis, share-count, scenario and timestamp semantics.
- Public/free PIT data availability is a first-class dependency because the target user has no paid broker/commercial data.

## 2. Current canonical state
Canonical main HEAD: ceae90f89f96f550645bc57a9b96528021e5ca9e.
P3-B code lineage is still covered by the last full green Investment Core CI after merge; the latest current-main push was documentation-only and passed the FM00 workflow.
Known documentation drift from the previous plan must be removed before new feature work.

## 3. Critical path
R1 State reconciliation
→ P4-A MIE qualification contract
→ P4-B ratio MIE vertical slice
→ P4-C DCF/DDM conditional MIE
→ P4-D SOTP/rNPV MIE
→ P4-E candidate coverage + multi-model expectation set
→ P4-F PIT/replay/fail-closed integration
→ P5-A semantic compatibility
→ P5-B expectation gap
→ P5-C probability integrity + Expected Return >15%
→ P5-D decision-gate red-team
→ P6-A production decision engine
→ P6-B human approval boundary
→ P7 monitoring/revision/execution receipt
→ P8 real-company acceptance
→ P9 independent audit

Parallel tracks: D public/free data capability; C company-side value/forecast readiness.

## 4. R1 — State and governance reconciliation
Objective: make STATUS, current-state index, continuity plan and roadmap mutually consistent.
Acceptance: current HEAD matches Git main; no document says P3 has completed Market Implied Expectation; P3 IDENTIFIABLE is explicitly qualified.

## 5. P4-A — Market Implied Expectation qualification contract
Objective: define when a reverse result is legally allowed to become a Market Implied Expectation.
Output must distinguish: full feasible set, conditional implied variable, implied range, insufficient evidence.
Required metadata: model, candidate-set scope, identifiability, stability, economic variable, point/range/conditionality, unit, basis, period/horizon, accounting basis, assumptions, evidence IDs, PIT cutoff and qualification rationale.
Hard block: ambiguous, unidentifiable, insufficient, unstable, semantically incomplete or candidate-coverage-insufficient outputs cannot become decision-grade MIE.
Acceptance: typed object + JSON schema + invariants + adversarial tests.

## 6. P4-B — Ratio-family MIE vertical slice
Models: forward PE, PS, PB, EV/EBITDA.
Produce model-native implied economic variables and ranges. Preserve candidate scope, units, PIT and provenance. Never emit generic implied net profit.
Acceptance: deterministic replay from an evidence snapshot.

## 7. P4-C — DCF / DDM MIE
Start with explicitly conditional inversion, not false full-space claims.
DCF: given admissible growth/margin/reinvestment/discount/terminal semantics, derive conditional implied FCF.
DDM: given admissible growth/payout/discount semantics, derive conditional implied dividend.
Any future full multidimensional feasible assumption space requires a separate contract and acceptance.

## 8. P4-D — SOTP / rNPV MIE
SOTP preserves segment identities, segment basis, residual value and equity-value bridge.
rNPV preserves pipeline identities, probability, timing, discounting, base value and observed composition.
Component identity or composition loss is a hard failure.

## 9. P4-E — Candidate coverage and multi-model expectation
Separate 'identifiable within supplied candidates' from 'sufficient candidate coverage for decision-grade interpretation'.
Multiple materially feasible models produce an expectation set; no forced winner.
Acceptance must prove that incomplete candidate coverage can downgrade eligibility instead of manufacturing certainty.

## 10. P4-F — PIT / replay / fail-closed
Bind MIE to exact price observation, evidence manifest, semantic basis, snapshot hash, engine/schema versions and replay.
Same snapshot must reproduce the same result. Changed evidence/semantic version requires mismatch or a new revision.

## 11. P5-A — Semantic compatibility
Before gap calculation, prove compatibility of model, variable, unit, period/horizon, accounting basis, scenario basis, share-count basis, enterprise/equity bridge and segment/pipeline identity.
Numeric comparability alone is insufficient.

## 12. P5-B — Semantic Expectation Gap
Ratio families compare economically equivalent variables.
DCF/DDM compare independent assumptions with market-implied conditional/feasible assumption requirements.
SOTP/rNPV compare independent component economics with market-implied residual/component requirements.
Do not force a scalar gap when the economic object is multidimensional.

## 13. P5-C — Expected Return gate
Primary metric: probability-weighted intrinsic value divided by entry price minus one.
Gate is strictly Expected Return >15%; exactly 15% fails.
Probabilities must be explicit, non-negative, sum to one under the contract representation and be supported by the forecast process. No fabricated fallback.

## 14. P5-D — Red-team
Attack ambiguous model sets, unstable identification, incomplete candidate coverage, conditionality mislabeling, semantic mismatch, invalid probabilities, exact-15 boundary, PIT leakage and replay mismatch.
Any bypass is a block.

## 15. P6 — Production decision engine
Reconnect Trust + PIT + Thesis + Independent Value + qualified Market Model + qualified MIE + Expectation Gap + Return >15% + Risk + Portfolio Constraints → Action.
Priority remains Trust > Portfolio Constraint > Long-term Value > Expectation Gap > Tactical Market/Positioning.
Human approval is mandatory.

## 16. P7 — Audit lifecycle
Complete immutable Run → Snapshot → Revision → Human Approval → Execution Receipt → Monitoring → Trigger → New Run/Revision.
No automatic order placement.

## 17. P8 — Real company acceptance
At minimum CATL and 科伦药业.
Each case must pass evidence/PIT, company reality, human valuation model, independent forecast/value, market-model qualification, MIE, expectation gap, >15% gate, risk/portfolio, human approval and replay.

## 18. Parallel data track D
D0 source inventory → D1 public/free adapters → D2 PIT normalization → D3 evidence manifests → D4 CATL/科伦 data-readiness.
Material variables must carry source, location, observation date, known_at, unit, basis, evidence ID and snapshot linkage.
Commercial-data assumptions are not acceptable substitutes.

## 19. Parallel company-side track C
C0 harden Value Core: business/asset nodes, capital intensity, CAPEX→D&A→FCF, incremental returns, capital allocation, dilution.
C1 ensure forecasts align with the human-selected Primary Model and are PIT/evidence backed.
C2 require company-side minimum readiness before real-company P5/P6 acceptance.

## 20. Explicitly deferred
Do not revive PR #3; do not build broad screening, auto-trading, frozen Kelly/sizing, unnecessary distributed infrastructure, fabricated historical model datasets, or a universal statistical market-model classifier.

## 21. Definition of done
Production-capable only when company evidence, human valuation, deterministic intrinsic value, candidate coverage, qualified market interpretation, model-semantic MIE, semantic gap, valid >15% return, Trust/Risk/Portfolio gates, human approval, revision/replay, two real-company acceptances and independent audit all pass.

## 22. Immediate next move
R1 → P4-A → red-team.
Do not start P4-B until P4-A has frozen the qualification semantics for conditionality, candidate coverage, semantic compatibility and stability.

Strategic principle: semantic truthfulness before feature completeness; vertical decision capability before breadth.