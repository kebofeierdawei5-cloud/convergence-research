# IIOS v0.3 Final Delivery Plan — 2026-11-12

## 1. Delivery objective

Stop treating each numbered batch as an independent development goal. Deliver one usable, auditable, local single-user A/H investment research workflow that answers:

**At the operator-entered current price, is this company investable under the user's evidence, return, risk and portfolio constraints?**

The delivery target is a reliable personal research tool, not a broker terminal, SaaS product, automated analyst, or trading system.

## 2. Frozen product boundary

### In scope
- Local macOS single-user launcher and private workspace.
- Manual company / market / cutoff / price / position inputs; manual price remains explicitly operator-attested and unverified unless independently sourced.
- Free-first public/official research evidence with provenance, cutoff/PIT discipline, Trust and UNKNOWN fail-closed behavior.
- Round A / Round B ChatGPT Free Web handoff by explicit manual copy/paste; preserve raw response bytes and their hashes.
- Independent operating forecast and earnings bridge; EPS_MULTIPLE and SOTP valuation paths with explicit model selection and no silent substitution.
- Current-price implied operating requirement / expectation-gap explanation where inputs are sufficient; otherwise NOT_IDENTIFIABLE or UNKNOWN.
- Annualized 15% return hurdle (not WACC), target entry price when calculable, risk and portfolio constraints, human approval.
- Readable report plus machine-readable run bundle, integrity verification and deterministic Replay.
- Durable task resume, partial-input recovery, private file permissions and concise one-click entry.

### Explicitly out of scope for this release
- Paid/commercial data APIs, screeners, auto-ordering or automatic trading.
- Programmatic ChatGPT/browser control, clipboard polling, Accessibility automation or background daemons.
- Remote Host / multi-user / SaaS deployment.
- Forcing an MIE number when expectations cannot be identified from verifiable evidence.
- New convenience features that do not close a demonstrated end-to-end acceptance failure.

## 3. Workstreams — run in parallel where independent

### W1 — Freeze and stabilize the delivery branch
- Keep PR #588 Draft until exact-head code CI and Mac acceptance are reviewed.
- No unrelated feature additions to B83.
- Keep canonical main unchanged until release gates are met.
- Every change must state its affected contract, tests and whether it changes investment semantics.

### W2 — One integrated B42–B81 critical-path audit
Audit existing implementation and tests against the actual decision chain, not batch-number completion:
1. Historical operating baseline and evidence coverage.
2. Production / sales / inventory / working-capital consistency.
3. FCF and earnings bridge reconciliation.
4. Independent operating forecast and driver-to-EPS transmission.
5. EPS_MULTIPLE and SOTP arithmetic, timing and per-share transmission.
6. Current-price implied earnings / required operating performance.
7. Expectation gap, downside/failure path, risk and portfolio constraints.
8. Report-to-machine-record parity.

Classify each finding as:
- RELEASE BLOCKER: can produce a wrong, overstated or falsely complete investment conclusion, or break provenance/replay.
- ACCEPTANCE BLOCKER: implementation exists but cannot be demonstrated on a representative real task.
- DEFER: explanatory convenience or edge case that does not affect the core decision or safety boundary.

Fix release blockers first. Do not reimplement already completed batches. Do not convert missing source data into fabricated estimates; UNKNOWN is an acceptable correct result.

### W3 — Minimal real-world acceptance
Use existing representative cases and existing outputs; do not invent data to force a pass.
- One EPS_MULTIPLE company task.
- One SOTP company task, only where the required segment and attribution inputs are actually available.
- At least one interruption and Finder relaunch during a real task.
- Round A/B raw-response capture and provenance hash verification.
- Complete run-bundle integrity verification and deterministic Replay.
- Explicit negative cases: missing evidence, blocked Trust, unavailable primary valuation inputs, incomplete portfolio context and unidentifiable MIE must remain blocked/UNKNOWN rather than silently passing.
- Review whether the report communicates the main operating contradiction, key drivers, current-price implied requirements, downside path and decision limits.

### W4 — Release and handover
- Run exact-head CI and independent red-team on the final code-bearing commit.
- Review Mac acceptance artifacts locally; do not upload private portfolio or raw research files to GitHub.
- Update canonical project state and release runbook.
- Merge only after W1–W3 gates pass and the PR diff is reconciled with main.
- Tag the delivered version and record known limitations / manual steps.

## 4. Release gates (all required)

| Gate | Pass condition |
|---|---|
| G1 Scope | Frozen boundary above; no paid APIs, screeners or automatic execution |
| G2 Code integrity | Exact-head required CI and independent red-team pass |
| G3 Evidence / Trust | Provenance and PIT constraints hold; unsupported claims remain UNKNOWN / blocked |
| G4 Calculation | EPS_MULTIPLE and SOTP arithmetic independently reconciled; no silent model substitution |
| G5 End-to-end | Real company input → research handoff → forecast → valuation → risk/portfolio → report |
| G6 Resume | Finder relaunch resumes the same task without duplicated accepted inputs |
| G7 Replay | Run bundle hash checks pass; deterministic Replay comparison is MATCH |
| G8 Decision boundary | 15% annualized hurdle remains separate from discount rate; human approval required; no auto-trading |
| G9 Release | State docs, runbook, PR and main are consistent; no unreviewed draft changes |

## 5. Fast execution rules

- Work by release blocker, not by sequential batch numbering.
- Run independent code audits in parallel; integrate fixes in small, testable commits.
- No speculative refactors and no new fields unless a concrete acceptance failure requires them.
- Do not spend time polishing documentation before core code and real-task behavior are verified.
- Do not repeat successful tests without a code or environment change.
- A CI pass is code evidence, not proof of Mac Finder, clipboard, or real-user workflow behavior.
- A missing dataset is a data gap, not a software defect unless the system mishandles the gap.
- Keep all private run bundles, raw ChatGPT responses and portfolio context on the operator's Mac.

## 6. Current known baseline on 2026-11-12

- PR #588: OPEN / Draft / unmerged; branch `feat/b83-durable-task-resume-20261108`.
- PR head: `b3448989ef85f1015beadd705a0c4a3b807e16a2`.
- Base main: `2fd009b10bd4b13467ebdd8b2692eab62a772878`.
- Compare reports branch ahead 136 / behind 0; the PR currently lists 19 changed files. Reconcile this history/diff before any merge.
- B83-7 exact-head Local Investment Pilot: 418 passed; 6/6 triggered workflows passed.
- B83-7 CI is Ubuntu-based. Finder launch, actual macOS clipboard capture, interruption/resume and real-task Replay acceptance remain unverified.
- Existing formal v0.3 core and earlier end-to-end work are not to be rebuilt. The remaining B42–B81 deep-research work is to be assessed by the integrated audit above, and only material release blockers should be reopened.

## 7. Immediate next actions

1. Audit the B42–B81 implementation against the eight critical-path checks and produce one consolidated blocker ledger.
2. In parallel, keep the B83 branch stable and prepare a minimal Mac acceptance script/checklist (not a new subsystem).
3. Fix only confirmed release blockers, with exact-head tests.
4. Run one integrated representative case and Replay; add the second valuation-family case where data permits.
5. Close release gates and prepare the single v0.3 release merge.

**Definition of done:** a personal investor can start one local task, provide a company/cutoff/price/position, review the research handoff, obtain an evidence-disciplined forecast/valuation/risk report, interrupt and resume safely, verify and replay the complete run, and retain final human decision authority. The system must say UNKNOWN or BLOCKED when the evidence is insufficient.
