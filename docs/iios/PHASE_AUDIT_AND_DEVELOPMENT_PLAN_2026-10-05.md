# IIOS Phase Audit & Development Plan — 2026-10-05

Status: AUDIT COMPLETE / DEVELOPMENT GATE SET
Canonical main at audit: 2328a6f9352a0ba5beb6b22475cdf85fd6c4435f

## 1. Audit conclusion

Overall: the project remains aligned with the original Investment Core objective. No theme-level deviation requiring rollback was found.

The correct current statement is: CORE-04 is a real, executable single-company investment-decision vertical slice. This is not yet equivalent to the full IIOS v0.1.1 product DoD.

Historical MIE/P3/P4 expansion was broader than strictly necessary, but the architecture has now corrected course: MIE is optional/explanatory and further P3/P4 model expansion is not on the critical path.

## 2. Original-requirement alignment

PASS — single-company, user-selected candidate, strict PIT, evidence/provenance and fail-closed.
PASS — Reality / Quality / Value Driver / Thesis are now structurally bound to the Decision Kernel.
PASS — human-authoritative Primary Valuation and independent forecast path exist.
PASS — H=1Y is the normative default; CATL uses an explicit 3Y exception.
PASS — Entry Return Cushion, Expected Annualized Return, Required Return and MoS are separated; BUY/ADD return conditions are conjunctive.
PASS — MIE remains optional and cannot by itself veto company-side BUY/ADD.
PASS — no automatic trading; human approval remains required.
PARTIAL — Risk and Portfolio are connected but remain minimal; sizing policy is intentionally not finalized.
NOT COMPLETE — chips/positioning is not yet downstream-integrated for timing/sizing.
NOT COMPLETE — monitoring/validation lifecycle is not yet productionized.
NOT COMPLETE — Machine Publication and Human Report/Report Quality Gate are not productionized.
NOT COMPLETE — CATL is the only real-company final decision E2E; a second company is still required for generalization.

## 3. 300750 audit result

Real case RC-CN-A-300750-20261004 passes the complete CORE-04 vertical execution.
Price = 291.11 CNY/share.
Quality = CONDITIONAL; Thesis Admission = ADMITTED; Thesis = INTACT; Trust = REVALIDATION.
DCF probability-weighted value ≈ 433.57 CNY/share.
Selected H = 3Y with explicit Horizon Override; system default remains 1Y.
Expected Annualized Return ≈ 14.20%, below the 15% strategy target.
Required Return = 10%; Risk = PASS; Portfolio constraint = PASS.
MIE is absent and remains OPTIONAL_EXPLANATORY.
Final strict action = REVIEW_REQUIRED; new capital = FALSE.
With Trust normalized to PASS, Quality alone still yields REVIEW_REQUIRED / QUALITY_GATE_UNRESOLVED.

## 4. Persistence audit

PASS — CORE-04 Quality/Thesis code, schemas, tests and acceptance documentation are merged.
PASS — final 300750 decision-chain acceptance is in docs/iios/CORE_04_FINAL_300750_DECISION_CHAIN_2026-10-05.md.
PASS — E001–E010 evidence captures and manifests are in Git.
PASS — E011 metadata, provenance and exact SHA-256 are in Git. Exact raw E011 bytes remain in the private operator vault by design.
PASS — CORE-04-C historical EV/EBITDA observations, source hashes and compact receipt are in Git.
PASS — final CI evidence is persisted in GitHub Actions: Investment Core #470, CORE-00 #207, 380 tests passed.
PARTIAL — current decision-lifecycle store primitives exist, but revision/approval/trigger semantics are not yet a complete production contract.
Important implementation finding: store approval keeps a sidecar rather than changing the revision status to HUMAN_APPROVED, and approve_revision has a current-state return-value bug for non-current revisions. These must be fixed before lifecycle acceptance.

## 5. Documentation/state audit

Historical state documents contain some superseded semantic/status text. They should remain immutable historical records but must be explicitly marked HISTORICAL/SUPERSEDED so future work cannot treat them as current truth.
Open stale PRs #3, #52, #53 were closed during this audit to remove obsolete development paths.

## 6. Targeted development batches

### A0 — Governance/state cleanup
Mark superseded state documents, keep one current-state authority, and enforce canonical/history/diagnostic status classes.

### A1 — Company-side evidence closure
Finish CATL incremental ROIC, CAPEX-to-FCF, earnings-to-OCF/FCF conversion, working-capital normalization and fuller Trust/governance history. Goal: move Quality/Trust from unresolved where evidence justifies PASS. Do not force a BUY result.

### A2 — Minimal Risk/Portfolio contract
Formalize max loss, thesis-break triggers, exposure limits and initial/target/max positions. No Kelly, optimizer or auto-trading.

### A3 — Second real company
Run 科伦药业 through the full chain to test SOTP/rNPV and mixed-business semantics and prevent CATL-specific coupling.

### A4 — Decision Revision / Human Approval productionization
Complete immutable revision state transitions, HUMAN_APPROVED/HUMAN_REJECTED/SUPERSEDED semantics, approval binding, current projection and replay. Fix the store bug identified above.

### A5 — Trigger + Monitoring + Validation
Implement Active Trigger → Event → Evaluation → New Run → New Revision, then connect thesis, forecast, valuation and decision validation.

### A6 — Machine Publication
Freeze a stable external Decision Publication contract independent of Markdown.

### A7 — Human Report
Add controlled report rendering and deterministic Report Quality Gate. Report changes must never alter the canonical decision.

### A8 — Chips/Positioning/Sizing
Add Market Regime → Industry Sentiment → Stock Structure → Holder/Capital Structure → Crowding as timing/sizing inputs only. Never let this layer rewrite Quality, Thesis or intrinsic value.

### A9 — Final red-team + MVP v0.1.1 acceptance
Attack PIT leaks, Trust/Quality bypass, revision overwrite, approval bypass, stale triggers, publication/report drift, replay mismatch, human override semantics and cross-company generalization. Final acceptance requires CATL + 科伦药业 and the full product DoD.

## 7. Parallel research track

FM-01/M1.2 forecast research continues independently. Exact source admission, PIT driver history, state engine and conditional backtest may proceed in parallel but must not block Investment Core productization.

## 8. Development gate

Next engineering gate: A0 → A1. Do not start new P3/P4/MIE model work unless a separately identified decision-semantic gap cannot be solved without it.

Target architecture after this audit:
evidence → company quality/thesis → valuation/forecast → return/risk/portfolio → optional MIE → decision → approval/revision → monitoring/trigger → publication/report → validation.