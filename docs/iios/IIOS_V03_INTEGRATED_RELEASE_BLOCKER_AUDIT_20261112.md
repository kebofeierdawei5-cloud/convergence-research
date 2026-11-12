# IIOS v0.3 Integrated Release Blocker Audit — 2026-11-12

**Classification:** DELIVERY AUDIT / NON-CANONICAL  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Purpose:** reconcile the B42–B81 research chain with B83 local workflow and identify only the blockers that prevent a usable, safe v0.3 release. This record does not promote any proposal branch to canonical main.

## 1. Executive result

**The project is not yet releasable as one integrated product.** There are two independently developed branches from the same canonical-main baseline:

- B83 delivery branch: durable local task workspace, Round A/B handoff, compact entry and launcher. Its PR #588 is Draft and targets `main`.
- Deep-research proposal chain: B42–B81 work on `feat/b73-evidence-driven-remediation-20261031` / `feat/b76-core-integrated-20261101`; PR #587 is Draft and targets the B73 proposal branch, not `main`.

The branches are not integrated. The B76/B81 branch has a large accumulated history and must not be merged wholesale into main or PR #588. Conversely, merging B83 alone would omit the B42–B81 research capabilities from the delivered product.

## 2. Evidence-based status ledger

| Area | Verified state | Release classification | Required disposition |
|---|---|---|---|
| B42–B43 inventory / working capital | Explicit production-sales balance proxy and WC inclusion contract; not a full inventory ledger | Integrate selectively; retain proxy limitations | Verify actual B42/B43 code and report path in the unified tree; keep UNKNOWN when treatment is absent |
| B44–B54 normalized earnings / FCF / expectation synthesis | Proposal-chain modules and contracts exist | Integration / arithmetic audit | Do not port by batch; inspect dependencies and preserve source classes / UNKNOWN |
| B55–B59 operating and EPS bridges | Strict physical-driver bridge; financial-statement amount bridge separately supports reported statement rows; EPS attribution and consistency gates | Real-case data blocker, not permission to weaken controls | Keep physical unit-economics UNKNOWN when volume/ASP/unit variable cost are absent; never relabel accounting cost as variable cost |
| B60–B68 price inversion / SOTP | Separate EPS_MULTIPLE and SOTP calculations; price-implied earnings/value-pool requirements and attribution | Integration and independent arithmetic audit | Preserve model-family separation, periods, units, diluted shares, parent adjustments and one-at-a-time sensitivity semantics |
| B69–B73 feasibility / exception / remediation | Evidence and operating feasibility gaps are explicit; remediation is reassessment, not a ticketing engine or automatic close | Integrate only after contract and output audit | Keep alternative B61/B63 lenses separate; no summed segment thresholds or composite probability |
| B74–B75 contradiction / event chain | Prompt/report implementation is ported onto proposal chain; docs state initial regressions were not run at that point | Verify on exact final code head | Require one primary contradiction and causal event-to-B4 mapping; do not add a second forecast engine |
| B76 integrated expectation comparison | EPS_MULTIPLE and SOTP comparison paths, arithmetic cross-checks and UNKNOWN gates | High-priority integration blocker | Audit against B57/B58/B60 and B61/B62/B63/B68 using same period/unit/basis |
| B78 provenance / B79 signed Evidence-PIT / B80 exact timestamp | Provenance relay, trusted signer registry checks, signed evidence resolver and exact PIT timestamp binding are described and covered in proposal-branch CI | Security / authority integration blocker | Production signer registry is empty; real company formal Evidence/PIT and Forecast admission are not demonstrated. Do not treat CI fixtures as production admission |
| B81 macOS runner repair | Hosted macOS runner moved from retired macos-14 to macos-15; exact code commit 7fb6798... had 35/35 related workflows pass, 466 tests on Linux and hosted macOS | CI issue closed; operator acceptance still open | Hosted runner success is not the user's Finder/clipboard/real-task acceptance |

## 3. Real-company acceptance: 新和成 002001

The B76 readiness record is explicit:

1. 2025FY and 2026Q1–Q3 published financial-statement amount bridges reconcile within CNY 1.
2. The B55 physical operating baseline is not identifiable from the reviewed public disclosures: business-line sales tonnes, net ASP and unit variable cost are absent. Segment revenue and accounting operating cost cannot be substituted for those physical measures.
3. B56/B57/B58 cannot produce a fully reconciled forward EPS merely from nine-month actual EPS. The annual weighted-average diluted-share assumption is missing.
4. The Q4 Bear/Base/Bull financial-statement assumptions are not supplied; therefore no conditional FY2026 EPS is produced.
5. The 2026-11-05 operator-attested price is absent in the readiness package; B60 current-price inversion is not run.
6. MIE remains NOT_IDENTIFIABLE. No BUY/NO-BUY decision is produced.

This is a valid fail-closed result, not a software bug. Do not invent Q4 assumptions, infer annual diluted shares from rounded EPS, or carry forward an old quote.

## 4. SOTP acceptance

The SOTP path is distinct from EPS_MULTIPLE and must remain so. Existing B61/B62/B63/B68 contracts calculate price-implied equity/value-pool and segment-profit sensitivities, but the inspected Xinhecheng readiness case is EPS_MULTIPLE and lacks the real inputs required to demonstrate a full SOTP case.

**SOTP real-company acceptance remains unproven.** Run it only on a company/case with cutoff-valid segment attributable earnings, segment P/Es, parent-level adjustments, net cash/debt, other adjustments and diluted shares. If these are not available, mark the SOTP real-case gate NOT_TESTABLE / UNKNOWN rather than forcing a fixture.

## 5. Release blockers (ordered)

### R1 — Branch integration and history reconciliation (P0)
- PR #588 contains B83 local workflow changes only.
- PR #587 validates the deep-research proposal chain against the B73 proposal base; it is not a main-targeted release PR.
- The B76 branch comparison to main reports hundreds of commits ahead and dozens of changed files. This is not a safe merge unit.
- Required: construct one clean integration branch from current main; port only the audited, dependency-closed B42–B81 runtime modules, tests, schemas, prompts and report projections; then layer B83 local workflow changes. Preserve original proposal branches and PRs for traceability. No bulk merge of either historical proposal chain.

### R2 — Exact integrated-tree validation (P0)
- Re-run the relevant test suites on the integrated tree, not merely on separate branches.
- Independently recalculate EPS_MULTIPLE and SOTP arithmetic at their adapter boundaries.
- Confirm report-to-machine-output parity and all fail-closed cases.
- Exact-head CI must include Ubuntu and supported macOS hosted runner jobs plus independent red-team. A test pass on PR #587 or PR #588 separately is not proof of the integrated tree.

### R3 — Real Mac operator acceptance (P0)
- User desktop Finder launch, manual Round A/B exchange, one-shot clipboard capture, task interruption/relaunch, accepted-input non-duplication, run-bundle integrity and deterministic Replay remain NOT VERIFIED.
- Keep private raw responses and portfolio data local; never upload them to GitHub.

### R4 — Evidence / formal-admission boundary (P0)
- B79 states the production trusted signer registry is empty.
- A signed test fixture or source reference does not establish production Evidence/PIT admission or Forecast Admission.
- Either enroll an actually authorized signer and complete a real evidence-backed case, or explicitly ship this personal pilot as non-canonical research output with formal admission unavailable. Do not claim formal decision-grade forecasts.

### R5 — Representative SOTP real case (P1 / conditional)
- Required only if release claims both valuation families have real-company acceptance.
- If no suitable public segment data case is available, release can describe SOTP as code-tested but real-case-unverified; it cannot claim full dual-model real-case acceptance.

### R6 — Missing company inputs (not a software defect)
- Xinhecheng Q4 assumptions, annual diluted shares, current price, and historical physical unit economics are operator/company-data dependencies.
- Keep their outputs UNKNOWN. The product must be usable for another company with adequate data; do not hold the whole release hostage to fabricating this one case.

## 6. Scope decisions

- Do not add new B84+ feature batches.
- Do not expand CSI800/A02 universe research, paid data APIs, screeners, provider credentials, auto-trading, browser automation, clipboard polling, daemons or multi-user hosting.
- Do not force MIE or win-rate estimates.
- Do not weaken B55/B56/B57/B58/B60 or signed Evidence/PIT requirements to make the demonstration look complete.
- Prioritize branch integration, exact integrated tests, real Mac acceptance and truthful release boundary.

## 7. Definition of release

A release candidate is acceptable only when:
1. one clean integration branch contains the intended B42–B81 and B83 runtime path without unrelated historical branch baggage;
2. exact integrated-head tests and independent red-team pass;
3. at least one real EPS_MULTIPLE case runs through the B83 guided workflow and Replay;
4. SOTP is either real-case accepted with adequate data or explicitly documented as code-tested / real-case-unverified;
5. user Mac interruption/resume and Replay are verified;
6. production formal admission is either genuinely demonstrated or explicitly unavailable and the product/report says so;
7. no private run bundle or raw response is committed.

**Current verdict: NOT RELEASED.** The main obstacle is no longer a need for more feature batches. It is integrating two proposal branches safely and proving the integrated local workflow end to end.


## 8. Reconciliation addendum — live GitHub audit, 2026-11-12

This section supersedes stale branch-count / validation statements above where they conflict.

### 8.1 Current branch graph and net diff

- Canonical `main` observed at `2fd009b10bd4b13467ebdd8b2692eab62a772878`.
- B83 branch `feat/b83-durable-task-resume-20261108` compares as **139 commits ahead / 0 behind**, with **21 net changed paths**. This differs from the earlier 136 / 19 snapshot. Its net changes include the local launcher, durable task workspace/session/resume modules, operator profile, quick start, pilot/workflow changes and B83 tests/docs.
- Deep-research branch `feat/b76-core-integrated-20261101` compares as **515 commits ahead / 0 behind**, with approximately **110 net changed paths**. It includes B42–B81 docs and runtime modules, changes to the existing local pilot, canonical forecast/evidence lineage, schemas, workflows and broad regression suites.
- PR #587 is explicitly validation-only, Draft, and targets `feat/b73-evidence-driven-remediation-20261031`; it is not a release PR and must not be merged to main.
- PR #588 is Draft and targets main, but contains only the B83 net diff. It does not contain the B42–B81 net diff.

### 8.2 Validation evidence refined

- B76/B80 recorded exact Linux Local Pilot suite: **466 passed**. At the B80 exact code commit `bb668cb5694bd36584988e204a5dad29fcee580e`, the combined Local Investment Pilot workflow was cancelled because its macOS acceptance job was cancelled; the other listed workflows succeeded. Do not count this as a macOS pass.
- B81 exact code commit `7fb679835a71e25572dc6db701e24e6dddb59bdf` has **35/35 associated workflow runs successful**, including the hosted macOS 15 arm64 Local Investment Pilot job and 466 tests. This closes the hosted-runner image retirement/cancellation defect. It does not prove the operator's own Finder / clipboard / real-task acceptance.
- B79 explicitly records the production signer registry as `NO_TRUSTED_SIGNERS_REGISTERED`. Signed test fixtures are ephemeral and do not establish real-company formal Evidence/PIT or Forecast admission. The product must either preserve the non-canonical pilot boundary or separately complete authorized signer enrollment; no fixture-based promotion is allowed.
- Xinhecheng 002001 remains a valid UNKNOWN / not-ready case: physical business-line tonnes / ASP / unit variable cost are missing; annual diluted-share assumption and Q4 scenario assumptions are missing; the dated operator price for that readiness package is missing. This is a data dependency, not a reason to weaken B55–B60.
- SOTP real-company acceptance remains unproven. The code path is distinct and has test evidence, but a suitable real case with attributable segment earnings, segment multiples, parent adjustments, net cash/debt and diluted shares has not been demonstrated.

### 8.3 Integration conflict that must be resolved explicitly

The two release branches both modify:
- `iios_mvp/local_investment_pilot_v01.py`;
- `.github/workflows/iios_local_investment_pilot_v01.yml`;
- `tests/test_local_investment_pilot_v01.py`;
- `docs/PROJECT_STATE_INDEX.md`.

The B76 branch substantially expands the existing pilot (roughly +3,500 lines in its net file diff), while B83 rewrites/refactors portions of the same pilot to add durable guided-task orchestration. A blind file copy from either branch would discard functionality from the other. These overlapping files require a deliberate three-way integration, followed by exact integrated-tree tests. The B83-only task modules can be layered separately once the pilot adapter seam is defined.

### 8.4 Updated blocker order

1. **P0 — Integration design:** create a clean branch from current main; define the pilot orchestration seam; integrate B76 research adapters without replacing B83 durable task/session control, and reconcile the workflow and tests.
2. **P0 — Exact integrated validation:** run the complete Local Pilot + Replay, Investment Core, signed Evidence/PIT, B76 arithmetic and red-team suites on the same integrated commit. Separate branch passes are insufficient.
3. **P0 — Operator Mac acceptance:** one real Round A/B task, explicit clipboard capture, interruption/Finder relaunch, private bundle integrity and Replay MATCH.
4. **P0 — Truthful authority boundary:** ship explicitly as `PILOT_NON_CANONICAL` while production signer registry is empty; do not claim formal Evidence/PIT, Forecast or Decision admission.
5. **P1 — SOTP real case:** conditional; either demonstrate a data-sufficient real case or document code-tested / real-case-unverified.
6. **Not a release blocker:** missing Xinhecheng source inputs; preserve UNKNOWN.

**Execution decision:** do not merge PR #587 or #588 as-is. The next engineering unit is a clean integration branch and the pilot orchestration seam, not another B-batch feature.
