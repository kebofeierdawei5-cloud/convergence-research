- **Batch 2 scenario-integrity audit (2026-10-11):** PR #360 merged to canonical main at `0d257fe243d0a2e921023504c2a3b2128fdd285a`; its 13 exact-head checks passed and dedicated CI reported 43 scenario/intake tests passing. The new independent regression checks compare fixed 002001/605016 assumptions against separately stated constants, recalculate expected wealth / returns / entry ceilings, check Chinese report-to-JSON consistency and recompute exact file/body hashes. The batch remains open only for review of the operator's actual local bundle/receipt; the operator reports normal completion, but no receipt summary has been independently inspected here. These are calculations over uncalibrated analysis-only assumptions and do not admit a formal Forecast or Decision. See `docs/iios/BATCH2_PATHA_SCENARIO_INTEGRITY_AUDIT_20261011.md`.
- **Path A macOS launcher repair (2026-10-11):** operator replay exposed `OUTPUT_ROOT_PERMISSIONS_TOO_OPEN`; the prior launcher created the output root without explicitly setting mode `0700`, so the deterministic scenario module correctly failed closed. The replacement launcher creates private roots with `0700`, prompts before tightening an existing current-user-owned output directory, rejects symlinks/owner mismatches, and fixes the `set -u` failure-report path. PR #358's 12 exact-head checks and all 3 launcher static tests passed. The operator now reports that the fixed launcher completed normally; the generated local bundle/receipt has not been independently reviewed in this session. The analysis-only/non-canonical boundary remains unchanged. See `docs/iios/PATHA_MACOS_ONECLICK_LAUNCHER_PERMISSION_FIX_20261011.md`.
- **Batch 0 / Batch 1 status (2026-10-11):** Batch 0 PR #355 merged at `e06669fc6093669e2bfd657a8679c6d061d414e3`; all 12 exact-head PR checks passed. Its narrow push-trigger change did not resolve the separate P0 incident workflow anomaly: runs [#38143107853](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38143107853) and [#38143645878](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38143645878) ended `failure` with zero jobs. They provide no failed assertion and no PASS evidence; keep the workflow/execution anomaly OPEN. Batch 1 PR #356 merged at `4ccb8cf89084d7299dfa8d0774cce97009eb5b54`. Its dedicated exact-head workflow [#38143577446](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38143577446) ran compile, 40 tests (scenario runner + Path A intake) and diff check successfully; the post-merge main workflow [#38143646589](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38143646589) also passed. The runner consumes the existing private normalized Path A record, produces a content-addressed private JSON/Chinese report/integrity receipt, and verifies replay; it creates no formal Forecast/Valuation Admission, Decision, Publication, complete Run Receipt or execution authority. Actual replay on the operator's Mac is still pending. A separately generated one-click macOS ZIP is pinned to the merged canonical commit and verifies both module Git blob SHA-1s before running. C1 SSE price-use rights/trusted signer and C2 independent fact/use signature remain open in parallel.
- **Path A operator-attested price overlay (2026-10-11):** the operator provided 2026-10-09 unadjusted closes for 002001 and 605016. A deterministic local-only intake is implemented in PR #354; actual values and source labels stay out of public Git. The overlay supports scenario valuation only, not canonical price admission, source-vintage verification, formal PIT admission or Decision authority. Because the frozen Case cutoff `2026-10-09` is start-of-day, these closes cannot be backfilled into those Cases; the price-only overlay uses `2026-10-10` start-of-day and does not revalidate the complete evidence set. No local LLM/model/API is required. See `docs/iios/OPERATOR_ATTESTED_PRICE_ANALYSIS_PATH_A_20261011.md`.
- **Operator-entered price direction (2026-10-11):** MP-1/MP-2/report assurance merged in PRs #366/#368/#370. PRs #372/#375/#377/#378/#379 successively cover cross-layer resolver/reference/receipt rejection, Evidence/PIT non-substitution, current-price/C4/return-gate snapshot tampering, stale record hash/Case/currency/class errors, all eight provenance flags and exchange metadata, and blocked-run no-publication/no-receipt. PR #383 adds the successful full-lifecycle test for a manual-price B2-E run: Decision Admission → Machine Publication → investor report → COMPLETE Run Envelope → complete Run Receipt; it verifies stage hashes/chain match the final state, private bundle ID and the input/receipt hashes are not exposed, and tampered-then-rehashed Run Receipt stage hashes are rejected. PR #383's two exact-head workflows passed (B2-E 24/24, B2-E red-team 8/8, B2 semantic admission 14/14, semantic red-team 15/15). PR #378 passed 9/9 repo checks incl. `test-mvp` 412/412 and `pilot-02`. Still open: sanitized independent review of one actual local Mac private bundle/complete Run Receipt/replay and deeper stage-bypass/replay variants. C1 SSE price rights and C2 independent fact/use sign-off remain separate open gates.
- **C1/C2 signer and source-rights workstream (2026-10-11):** PR #353 contains the deterministic Ed25519 admission implementation and an 8-test adversarial suite; no trusted signer is registered yet, and SSE market-price rights remain ungranted. C2 independent signature and exact use boundary remain pending. No C1 ingest or quote search is repeated. This workstream does **not** require a local LLM, Ollama, model installation, or model API. See `docs/iios/EVIDENCE_ADMISSION_SIGNING_AND_MARKET_DATA_RIGHTS_GATE_20261011.md` and `docs/iios/EXCHANGE_MARKET_DATA_RIGHTS_REQUESTS_20261011.md`.
- **C0 architecture/product-entry decision (2026-10-11):** the C0 ADR and aligned batch/state records select LOCAL_SINGLE_USER/local-first as the default profile, reusing the canonical CLI/loopback Host, Orchestrator, runtime factory, Store, report/QA and Run Receipt/replay path. The manual ChatGPT Free Web handoff remains NON-CANONICAL for formal semantic admission. This decision record does not close production P0s, formally admit C1/C2 evidence, or claim MVP acceptance.
- **D1-A loopback probe utility (2026-10-11):** `tools/iios_d1a_host_liveness_probe_v01.py` now collects only `/healthz` and `/readyz` statuses/version/response hashes on IPv4 loopback and writes a mode-0600 sanitized report. It has not been run on the operator host and cannot claim provider invocation or production acceptance.
- **D1-A provider smoke audit (2026-10-11):** B2-D run [#38127035406](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38127035406) had a green overall job conclusion but its live step found the required provider configuration absent, emitted `BLOCKED_OR_FAILED`, and produced no independently verified live receipt. It is diagnostic only, not provider PASS or Host acceptance.
- **D1-A dependency clarification (2026-10-11):** Host configuration/liveness can be checked in parallel, but a real canonical 605016 request cannot be accepted until C1 signed Evidence/PIT admission is complete. The local Ollama setup path is a separate optional runtime candidate; it is not a prerequisite for evidence-signature or source-rights resolution. No host-origin request has been run by this session.
- **C2-P3 durable result archive (2026-10-11):** sanitized workflow result from [run #38126026797](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38126026797) is preserved at `evidence/real_cases/RC-CN-A-002001-20261009/C2_P3_FACT_REVIEW_CI_RESULT_38126026797.json`. It contains 13 source/page/hash records and aggregate PIT outcomes only; source use/retention remains `PUBLIC_ACCESS_REUSE_UNKNOWN`, and this is not external sign-off.
- **C2-P3 separate-method review (2026-10-11):** PR [#345](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/345) merged after exact-head workflow [#38126026797](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38126026797) passed. It verified 13/13 fact locators, official source/date bindings and cutoff-safe bounds from the pinned Run #8 object hashes; it correctly keeps source-use status `PUBLIC_ACCESS_REUSE_UNKNOWN`. This is not external reviewer sign-off, formal admission or a legal opinion.
- **D1-A Host acceptance (2026-10-11):** [runbook](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/docs/iios/D1_A_PRODUCTION_HOST_ACCEPTANCE_RUNBOOK_20261011.md) and sanitized status record exist. No operator-host process or endpoint has been invoked from this task session; actual provider receipts, durable storage/replay and production acceptance remain false. P0-LLM-001/P0-LLM-004, formal Decision, complete Run Receipt and execution authorization remain OPEN.
- **Action A manual-Web semantic gate (2026-10-11):** PR [#342](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/342) is PASS / MERGED / CANONICAL at `a496b82b8cfbc2256a9affd3337f97fce305d217`. Canonical semantic admission now fails closed for the manual ChatGPT Web producer and renamed IDs retaining its unapproved policy namespace. This keeps the Web callback non-canonical only; it does not authenticate origin, close P0-LLM-001/P0-LLM-004, or accept the production Host.

# IIOS Project Status

State classification: **CANONICAL SUMMARY**
Date: 2026-10-11

Authoritative current-state record:
`docs/PROJECT_STATE_INDEX.md`

## Current C1 / C2 evidence status — 2026-10-11

- **C1 / 605016:** the operator reported a successful bounded source-vintage successor migration. The candidate contains 11 evidence records and 8 unique raw files; Core/PIT validator PASS. The exact endpoint first-public timestamp remains unverified. Formal signed admission and production Host acceptance are not granted.
- **C1 exact-head checks:** private persistence 53/53 PASS; B2 data Evidence/PIT 31/31 PASS; company Evidence/PIT 23/23 PASS; B2 scope 3/3 PASS; State Hygiene, C0 Governance, Investment Core and independent red-team PASS.
- **C2 / 新和成 (002001.SZ) successor result:** PR [#333](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/333) corrected date-only cutoff normalization to 2026-10-09 00:00:00 +08; PR [#334](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/334) merged the pinned Run #8 successor adjudicator. Exact-head workflow [#38121849097](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38121849097) passed: 8 raw objects byte/hash verified; 13 PDF page-located facts checked against 3 official SZSE PDFs; the unchanged Core/PIT validator returned only `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`. The ephemeral candidate manifest covers six groups; overall B2 remains BLOCKED because the permitted source/vintage for the required 2026-10-08 close is not established.
- The historic Run #8 manifest/preflight stay unmodified and diagnostic. The 2026-10-09 same-day buyback progress notice and close, the current issuer IR page, and captured Sohu/Eastmoney price pages remain excluded. Exact first-public timestamps are unverified, and independent source/vintage review is still pending. Sanitized machine report: `evidence/real_cases/RC-CN-A-002001-20261009/C2_SUCCESSOR_CORE_VALIDATION_REPORT_20261011.json`; no raw source bytes or numeric market quote values were committed.
- No formal signed admission, production Host acceptance, Decision, Publication, complete Run Receipt, or execution authority was created. Primary 605016 production Host/semantic/Forecast/Valuation and complete Run Receipt replay remain an independent open critical path.
- **C2 / 新和成 price and Core/PIT update (2026-10-11):** PR [#338](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/338) merged the operator-attested price class; PR [#340](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/340) merged the full synthetic positive-path test. The actual private run of the merged tool against the pinned Run #8 archive now passes all seven required Core/PIT groups with an operator-attested price. Eight captured raw objects and 13 PDF locators were reverified. This is `PASS_EPHEMERAL_OPERATOR_ATTESTED_NOT_SOURCE_VINTAGE_VERIFIED`: no second web audit, no quote value/private manifest uploaded to GitHub, and no source-origin claim. A separate local second-pass found 13/13 locator and cutoff-bound checks pass; genuinely independent human/external review of the 13 facts/use boundary remains open. Formal signed admission, production Host, D2 canonical decision and full Run Receipt remain blocked. Machine record: `evidence/real_cases/RC-CN-A-002001-20261009/C2_MARKET_PRICE_SOURCE_REVIEW_20261011.json`.
- Primary 605016 production Host/semantic/Forecast/Valuation and complete Run Receipt replay remain an independent open critical path. No formal Decision or automatic execution is authorized.

Canonical source of truth remains docs/PROJECT_STATE_INDEX.md.
## Latest P0 status — 2026-10-10

P0 Batch B3 is merged in PR [#276](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/276), merge commit `d3582621918b285f29b4573c2618c1072247885c`. Formal Decision Revision, Publication and Report writers now revalidate persisted upstream admissions and fail closed when those bytes are missing.

P0 C1 source adjudication PR [#278](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/278), official dividend PR [#282](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/282), and official HTTPS B2 validation PR [#294](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/294) are merged. The latest exact-head run #38050190177 passed the unchanged B2/PIT validator ephemerally: 11/11 records, all seven required groups, zero validation errors. Artifact #11669076729 and machine record `evidence/real_cases/RC-CN-A-605016-20261009/OFFICIAL_HTTPS_B2_ADJUDICATION_20261010.json` contain only source hashes, dates, row shape and gate status. Numeric quote values and raw market-price bytes are not published. The local-persistence gate was still open at the time of this historical P0 entry; it was later closed by the operator-confirmed C1 successor migration above. Do not rerun ingest. Eastmoney and Yahoo remain excluded by source-specific reuse/automation terms. Original cutoff and HTTPS intake rules have not been relaxed. The additional free-HTTPS provider review is recorded in `evidence/real_cases/RC-CN-A-605016-20261009/PRICE_PROVIDER_TERMS_ADJUDICATION_20261010.json`: Tencent reuse is unresolved for this evidence use, and Yahoo's terms require express prior permission for automated data collection. PR #289 was closed without merge; neither source is admitted or used to close the price gate.

**Production P0-LLM-001 / P0-LLM-004 remain OPEN.** There is still no deployed production-host run proving a genuine company semantic/Forecast/Valuation chain, Decision Revision, publication/report and complete Run Receipt replay with independent red-team. Follow `docs/PROJECT_STATE_INDEX.md` for the active next boundary. PR #285 merged into canonical main at `cf3fb42ebf3f0faedb7a50244ea0edd00fc142ac`; exact PR-head checks passed 17/17 and post-merge required checks passed 6/6. It adds the no-paid-key local Ollama runtime path and narrows the HTTP exception to same-machine loopback + `SELF_HOSTED` + `AUTH_MODE=NONE`; this is implementation/CI coverage only, not a real Host/model/company run. PR #296 subsequently merged at `b7c5b0d4a317990017e88e35220a1279524c0e03`; its free ChatGPT Web operator-handoff contract passed 8/8 exact-head checks and 3/3 post-merge required checks. This enables manual request-intent/semantic callbacks without a local model or API key, but copied web replies are explicitly not provider-authenticated, the handoff receipt is not yet embedded in the formal complete Run Receipt, and production P0 remains OPEN.


This file is a concise human-readable summary. When it conflicts with the Current State Index, the Current State Index wins.

## Current stage

**Current canonical M1.2 status: New Research Epoch Design Proposal = CANONICAL DESIGN / NOT ACTIVATED**

C8 and all prior Stage C productization milestones remain canonical.

Authority hardening is complete through:

```
B02 → B03-B → B04-B → independent post-B04 re-audit
```

M1.2 baseline progression:

```
FM00 Git Baseline = PASS
        ↓
FM01 exact M1.1 source admission = PASS
        ↓
FM01 DATA_READY
        ↓
FM02 PIT feature builder / feature contract = PASS
        ↓
FM03 State Engine / Forecastability State Construction = PASS
        ↓
FM04 Conditional Backtest = PASS
        ↓
FM05 Scope / Estimand / Sufficiency Freeze = PASS
        ↓
FM04 Conditional Backtest = PASS
```

FM02 feature merge commit:
`ade3541302eb6f3fa43ec8aac76540820000a727`

Baseline:
- PR #136 = MERGED;
- exact FM00 source anchor = `536e883bc873dbe7dd7383690a7a95a0f65591a7`;
- immutable tag `m1.2-fm00-v0.1.0`;
- baseline workflow #6 = SUCCESS on exact PR head `ff6bfe0ff7677d0a965af513ac2ee644413565d1`.

G2 historical frozen identity remains separate from the accepted R0 successor evidence; no frozen-byte rewrite was performed.

**Next boundary: A02 B-01 Free-First Raw Evidence Materialization, required before activating the recommended cross-sectional successor epoch.**

FM01 data gate is now `DATA_READY` after exact-source admission, provenance binding, 22-quarter coverage validation, and independent PIT replay.

Admitted CATL scope: 300750.SZ, 2021Q1–2026Q2, 22 quarters, 44 DriverSeries records for REVENUE / NET_PROFIT.

No FM01 numeric data were fabricated, inferred, or reconstructed from memory.

FM02 is now PASS / MERGED / CANONICAL as a feature-construction research capability. It remains separately gated from confirmatory model selection by M1.2 research governance, State / UNKNOWN semantics, conditional backtest, partitioning, sealed-manifest and blind-scoring controls.

FM02 acceptance:
- PR #144;
- merge commit `ade3541302eb6f3fa43ec8aac76540820000a727`;
- final pre-merge head `617c9b8a3f091e76d5ea44a39e963ff255ffd99b`;
- remote CI run #15 = SUCCESS;
- 13 / 13 FM02 unit tests passed;
- generated feature snapshot = 22 rows (11 origins × 2 drivers);
- canonical feature-row content hash `3803be1404255652b831627fcd32acaf203f8984da33f70d3784e28dc449b9da`;
- generated snapshot schema validation = PASS;
- independent PIT provenance audit = PASS.

Acceptance: `docs/iios/FM02_ACCEPTANCE_2026-10-07.md`.

FM02 does not authorize State Engine, Conditional Backtest, confirmatory model selection, production router, current-price inputs, scheduler, alerts, or automatic execution.
FM03 acceptance:
- PR #147;
- merge commit `007ac477f7e45664c6eb7d4681de5d92c3a16b11`;
- accepted pre-merge head `276d37111c0866ef7a0e69b7ab38aa1e4e1d2788`;
- dedicated Actions run #2 = SUCCESS;
- 14 / 14 FM03 tests passed;
- generated state snapshot = 22 rows (11 frozen origins × 2 drivers);
- canonical state-row content hash `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- independent PIT/provenance audit, output schema validation, compileall, and diff-check = PASS;
- `confirmatory_eligible=false`, principal `iios_research`, grant `m1.2.fm03.state_engine`.

FM03 preserves PIT visibility, explicit UNKNOWN propagation without imputation, provenance closure to FM02 / DriverSeries, the hash-bound frozen origin schedule, and fail-closed capability isolation. It uses deterministic non-tuned state mappings only and does not authorize Conditional Backtest, Model Selection, Production Router, or Automatic Execution.

Acceptance: `docs/iios/FM03_ACCEPTANCE_2026-10-07.md`.


RP-01 remains a separate legacy fixture regression and is not M1.2 baseline acceptance evidence.


## Canonical Investment Core

```
Reality
→ Quality / Thesis / Value Driver
→ Primary Valuation
→ Independent Forecast
→ Return H
→ Risk
→ Portfolio
→ Optional MIE
→ Decision
```

The production Decision Kernel is merged and the real 300750 chain has passed E2E.

## 300750 accepted result

- Price: 291.11 CNY/share
- Quality: CONDITIONAL
- Thesis: INTACT / ADMITTED
- Trust: REVALIDATION
- H: 3Y explicit override; system default remains 1Y
- Expected Annualized Return: about 14.20%
- Required Return: 10%
- Risk: PASS
- MIE: OPTIONAL / absent
- Decision: REVIEW_REQUIRED
- New capital: FALSE

## Development boundary

Investment Core remains single-company and PIT-bound.

CSI800 / CSI Industry / historical-universe reconstruction and FM forecast research remain separate Research Track workstreams and do not block the core.

## A1 status

A1 is PASS / MERGED as an engineering/evidence-closure milestone.

A1-01 established the deterministic economic bridge; A1-02 established the capital-allocation and Trust/Governance evidence bridge; A1-03 integrated them into existing Quality and Trust semantics. These layers do not directly authorize capital.

For 300750, Quality Gate remains CONDITIONAL, Trust remains CONDITIONAL, and new capital remains FALSE.

Acceptance:
- `docs/iios/A1_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_01_ACCEPTANCE_2026-10-05.md`
- `docs/iios/A1_02_ACCEPTANCE_2026-10-05.md`
- `docs/iios/RP_01_RISK_PORTFOLIO_PRODUCTION_CONTRACT_v0.1.md`
- `docs/iios/DR_01_DECISION_LIFECYCLE_CONTRACT_v0.1.md`
- `docs/iios/DR_02_PERSISTENCE_CLI_INTEGRATION_v0.1.md`

## TR-01 status

TR-01 Trigger Contract / Event Semantics = PASS / MERGED / CANONICAL.
- PR #89;
- merge commit: 0fb7262ded47b3497f5be33dc93163e209f0098f;
- dedicated Actions run #9 = SUCCESS;
- independent exact-module execution = PASS.

The full Investment Core CI on the pre-merge TR-01 head retained four unrelated CORE-04 assertion regressions. These remain a separate cleanup item and do not change the TR-01 acceptance boundary.

## TR-02 status

TR-02 Monitoring State = PASS / MERGED / CANONICAL.
- PR #91;
- merge commit: 6b5a83ff3dcb0028945f455c517b369dbbf8220b;
- dedicated Actions run #10 = SUCCESS;
- red-team boundary review = PASS.

TR-02 does not include scheduler, alerts, automatic decision execution, or investment-semantic changes.

## TR-03 status

TR-03 Validation / Replay = PASS / MERGED / CANONICAL.
- PR #93;
- merge commit: 33291911c6e6b26da6deaf6c28a7a2046173c842;
- dedicated Actions run #5 = SUCCESS;
- red-team boundary review = PASS.

TR-03 closes the historical `next_due_at` replay gap using immutable monitoring initialization/evaluation records and source-derived fail-closed validation.

Scheduler/alerts remain out of scope.
## C8 status

C8 Final Independent Red-team / MVP Acceptance = PASS / MERGED / CANONICAL.

Remediation PR #116:
- merge commit: c99763a9eae957e59c238590ad64b00bc308e54b.

Canonical-main rerun:
- Actions Run #30;
- tested head: c99763a9eae957e59c238590ad64b00bc308e54b;
- 36 tests passed;
- compileall, C3 harness, C7 harness and git diff-check passed.

AUTH-001/002/003 are enforced at Decision Admission, Decision Series persistence and Human Approval authorization boundaries.

Acceptance: docs/iios/C8_ACCEPTANCE_2026-10-06.md.

C8 adds no new investment capability, scheduler/alerts or automatic execution.

**Post-C8 development boundary: explicit governance decision required.**

Historical Stage C milestone sequencing remains context only.

## Stage C milestone status after C5

Historical TR-03 checkpoint: TR-03 Validation / Replay is now PASS / MERGED / CANONICAL.

- C6 Human Execution Receipt = PASS / MERGED / CANONICAL
- C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL
- Current next boundary: C8 Final Independent Red-team / MVP Acceptance

## Governance rule

All new development starts from:

```
canonical main
    ↓
docs/PROJECT_STATE_INDEX.md
    ↓
relevant normative contract
```

Historical documents are context only. Diagnostic branches / PRs are not capability until merged.

## C0 status

C0 Governance Hygiene / Stage Baseline = PASS / MERGED / CANONICAL.

C0 closed project-state authority, continuity hygiene, stale-document boundaries, and deterministic governance CI checks. It did not modify Investment Core economics or Decision semantics.

The canonical Stage C plan is `docs/iios/IIOS_STAGE_C_PRODUCTIZATION_PLAN_v0.1.md`.

Canonical C0 merge: `1594e43eee14aaa41ddde675ddbe61d650462cf7`.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration.


## C1 status

C1 Machine Publication = PASS / MERGED / CANONICAL.

C1 provides a read-only, content-addressed machine-readable projection of an exact Decision Revision, with explicit AI/Human separation and bound Trigger / Monitoring / Validation references.

Acceptance: `docs/iios/C1_ACCEPTANCE_2026-10-06.md`.

Canonical C1 merge: `b9a8ff0fe1341a56f363fb058677dbd50a4f87b8`.

Historical next boundary at the checkpoint documented in this section: C2 Human Report / Report Quality Gate.


## C2 status

C2 Human Report / Report Quality Gate = PASS / MERGED / CANONICAL.

C2 provides a deterministic human-readable projection of an accepted Machine Publication, plus immutable report metadata/Markdown and a fail-closed Report Quality Gate.

Acceptance: `docs/iios/C2_ACCEPTANCE_2026-10-06.md`.

Canonical C2 merge: `75bb360436286ae950a05028769701380120e561`.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration.

 
## C3 status

C3 Second Company Acceptance = PASS / MERGED / CANONICAL.

Real second company: 四川科伦药业股份有限公司 / CN-A / 002422.

Dedicated C3 Actions run #11 = SUCCESS; 4 C3 tests passed; executable acceptance harness passed; compileall and git diff --check passed.

Acceptance: docs/iios/C3_ACCEPTANCE_2026-10-06.md.
Canonical C3 merge: eb0f9fc965f9ce6aa09685776d2ec8a0522e3b47.

Historical next boundary at the checkpoint documented in this section: C4 Expectation Gap Production Integration. C3 introduced no Expectation Gap, positioning/sizing, scheduler, alerts, or automatic execution capability.


## C4 status

C4 Expectation Gap Production Integration = PASS / MERGED / CANONICAL.

Dedicated C4 Actions run #7 = SUCCESS on exact head aacf1c0cc715697bfac2aa0bae5e2f0a4c899ad2.
75 tests passed; executable acceptance harness 7 / 7 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C4_ACCEPTANCE_2026-10-06.md.
Canonical C4 merge: 07d45c18df8df9100d4866dd5f92fa95ccdb7186.

Historical next boundary at the checkpoint documented in this section: C5 Positioning / Sizing.


## C5 status

C5 Positioning / Sizing = PASS / MERGED / CANONICAL.

Dedicated C5 Actions run #7 = SUCCESS on exact head f9758beb683b3ba044fc9a153018050fa4ff09d9.
86 tests passed; executable acceptance harness 9 / 9 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C5_ACCEPTANCE_2026-10-06.md.
Canonical C5 merge: cdf998cd21776363914f178e648f03ec0c1539f8.

C5 is timing/sizing-only. It cannot mutate fundamental Decision action, Trust, Quality, Thesis, intrinsic value, Return, Required Return, or Risk. It does not add Kelly, portfolio optimization, scheduler, alerts, automatic execution, or Forecast Research productionization.

Historical next boundary at the checkpoint documented in this section: C6 Human Execution Receipt.


## C6 status

C6 Human Execution Receipt = PASS / MERGED / CANONICAL.

Dedicated C6 Actions run #2 = SUCCESS on exact head f817041471a43618d30f88538b11a96e67b71fa0.
23 tests passed; executable acceptance harness 8 / 8 PASS; compileall and git diff --check passed.

Acceptance: docs/iios/C6_ACCEPTANCE_2026-10-06.md.
Canonical C6 merge: 4c01e40dd7469221d9f5aee005c96e05bf4eb55f.

C6 is record-only: execution receipt requires exact HUMAN_APPROVED binding, is immutable, and cannot mutate Decision Revision, Human Approval, Current Projection, or Decision action. auto_execution remains false.

Historical next boundary at the checkpoint documented in this section: C7 Full Lifecycle E2E.


## C7 status

C7 Full Lifecycle E2E = PASS / MERGED / CANONICAL.

Dedicated C7 Actions run #6 = SUCCESS on exact head 43664c9bee33b3d53f212428da019e197a9fcaf2.
74 related tests passed; executable acceptance harness 4 / 4 PASS; compileall and git diff-check passed.

Acceptance: docs/iios/C7_ACCEPTANCE_2026-10-06.md.
Canonical C7 merge: 82d1911c985791e4b76f63d792588d175ee505f8.

C7 proves append-only revisions, downstream-only Monitoring and Execution Receipt, deterministic replay, new-run/new-revision requirements, and projection-only Publication / Report. It introduces no new investment policy or execution automation.

Historical next development boundary at the C7 checkpoint: C8 Final Independent Red-team / MVP Acceptance.

## FM04 status

M1.2-FM04 Conditional Backtest = PASS / MERGED / CANONICAL.

- PR #150;
- accepted CI run #2 = SUCCESS (run id `37564860982`);
- 12 FM04 tests passed;
- exact FM02 and FM03 reconstruction passed;
- pinned FM03 snapshot hash: `7e020df6eeb5b6aa4cf47e625d902c3c5ca7645457427c8af085a55d25811fd4`;
- real CATL result: 406 selection units, 0 selected, 406 `NO_SELECTION`, 79 conditional descriptive groups;
- independent PIT/nested-selection/scoring audit = PASS;
- output schema/invariants, compileall, and git diff-check = PASS.

The backtest machinery is valid, but the frozen 11-origin / seven-state-dimension sample produces no state-conditioned inner selection with N≥3. This is a data-sufficiency result, not predictive-validity evidence. FM04 does not authorize production routing, confirmatory inference, or investment decisions.

Acceptance: `docs/iios/FM04_ACCEPTANCE_2026-10-07.md`.

**Next boundary: M1.2-FM05 Scope Freeze / Data Sufficiency Adjudication.**


## FM05 status

M1.2-FM05 Scope / Estimand / Sufficiency Freeze = PASS / MERGED / CANONICAL.

- PR #156;
- merge commit `215afcc60e649dde331e7f076be809dda716770a`;
- accepted exact head `e6b5a77290409d3e95164007245d57f58246ccd4`;
- dedicated FM05 workflow run #1 = SUCCESS;
- run id `37578843014`;
- adjudication: **INSUFFICIENT_FOR_STATE_CONDITIONED_SELECTION**;
- frozen replay: 406 outer selection units, 0 selected, 0 outer evaluated, 406 NO_SELECTION, 79 structural conditional groups, 0 empirical conditional groups.

FM05 is governance-only. It does not authorize model selection, production routing, automatic execution, or investment decisions. Result-driven redesign requires a new research epoch.


## FM07 status

M1.2-FM07 Research Epoch Amendment Gate = PASS / MERGED / CANONICAL.

- PR #159;
- merge commit: `549f16ce37058a9b889c159b6392d175bc3397b4`;
- accepted exact head: `d8870e08aded67eac5f6cdda1b811b4d4632eda7`;
- gate decision: **DO_NOT_AMEND_CURRENT_EPOCH**;
- current epoch `RE-M12-EXP-CATL-20260930` is closed to same-epoch amendment.

Any result-driven scope, estimand, threshold, state, model-family, metric, origin-schedule, or universe change requires a new research epoch with pre-execution freeze and renewed PIT/provenance/purity controls. FM07 does not open that epoch automatically.


## New research epoch design

M1.2 New Research Epoch Design Proposal = **CANONICAL DESIGN / NOT ACTIVATED**.

- PR #161;
- merge commit `8dfcb150583c05f963fa2bd1c50ca9a55aed9935`;
- recommendation: cross-sectional universe expansion with threshold preservation;
- N>=3, MAE primary metric, existing model instances and state dimensions remain provisional defaults, not an active epoch;
- A02 PIT universe admission, renewed provenance, purity freeze, and owner approval remain required before execution.


## A02 B-01 status

A02 B-01 Free-First Source Registry = **PASS / MERGED / CANONICAL — ADMISSION REMAINS BLOCKED**.

- PR #163;
- merge commit: `3230c7d09f212ab92622ffefc66e684d18262dd0`;
- current unresolved domains: `st_history`, `industry_history`, `source_vintages`;
- no historical PIT admission is claimed from current official pages alone.

### DATA-01-B Run #2

- workflow run: `37593042893`;
- head SHA: `6e8fc8ef9639c486daae33aa74bb64b86366c4dc`;
- artifact: `11469004605`;
- GitHub artifact digest = independent ZIP SHA-256: `dabc25996524f03e8c533e33bd7921ed5c03e85a4b72edbf1b3a15589c4b17ec`;
- independent manifest verification: **8/8 PASS**;
- exact current official bytes: SSE / SZSE stock lists, SSE risk plate, SZSE company notice, CSI taxonomy definition;
- Baostock secondary materialization: **BLOCKED** at login;
- PIT sufficiency: **BLOCKED**;
- identity / listing-delisting / common-equity / ST historical known_at: **not admitted**;
- CSI security-level historical industry assignments: **not materialized**.

A run-2 provenance inconsistency in the emitted admission matrix was identified and corrected in the canonical materializer. No admission boundary was relaxed.

### DATA-01-B Run #3

- workflow run: `37593671212`;
- head SHA: `6f47e5f6f481df8f4a300765f237c5f7f70dae0d`;
- artifact: `11469780985`;
- GitHub artifact digest = independent ZIP SHA-256: `85e836b2e797730be459a334172993118eb7101e44014c2539344c7ef679eb62`;
- independent manifest verification: **8/8 PASS**;
- materializer exit code: `4` (expected bounded fail-closed result);
- current official raw evidence: materialized and independently hashed;
- historical security-master PIT evidence: **NOT ESTABLISHED**;
- Baostock: **BLOCKED / NOT ADMITTED**;
- overall B sufficiency: **BLOCKED**;
- permitted Run #3 result class: **BLOCKED**.

Run #3 confirms the repaired artifact-transport path. It does not convert current snapshots into historical PIT evidence and does not change A02 admission state.

Next technical boundary: obtain reproducible historical PIT carrier evidence with source-vintage / known_at; do not activate the proposed successor forecast epoch before A02 admission is complete.

### DATA-01-A Batch 2

- historical G0-T02 handoff pointer located: `CSINDEX_000906_20260703T100909Z`;
- declared historical package: 373560 bytes;
- declared package SHA-256: `fab0950153e3a683e9590dc895533276e0092146d7774b4822442d00d45b369b`;
- declared terminal member: `000906cons.xls`, 169984 bytes, SHA-256 `f8e4aa8d28bec4871fe6f582d4e5fc490c79312524a568de8f23b73e22b2b984`;
- current runtime/package access: **BLOCKED**;
- independent A raw preflight: **BLOCKED**;
- negative-control tests: **3/3 PASS**;
- no checksum/package declaration has been promoted to raw-byte evidence.

Batch-2 state remains `HISTORICAL_CARRIER_BYTES = BLOCKED`. The approved next transition is actual package/raw-byte supply followed by independent SHA-256 and A preflight.

## DATA-01-B Batch 3

- Batch 3: `DATA-01-B` B-side Free-First Raw Intake.
- Independent B raw preflight: `research/a02_raw/b_raw_preflight.py`.
- Required B domains: identity, listing_delisting, common_equity, st_history, industry_history, source_vintages.
- Required PIT origins: 11 origins from 2023Q3 through 2026Q1.
- Latest runtime probe: Run `37595133874`, Artifact `11469743020`, artifact SHA-256 `cffd3bcd18609d85b290875fe7c6b492994aae994c7d43efd9996075c68f3d49`.
- B raw preflight result: **BLOCKED / exit 4**; latest artifact contains no `DELIVERY_MANIFEST.json` and no B raw-domain files.
- Independent negative-control suite: **4/4 PASS**.
- No B raw-intake declaration, current snapshot, checksum-only metadata, or `retrieved_at` value has been promoted to PIT evidence.
- Downstream remains locked: A02 admission BLOCKED; Model Selection LOCKED; cross-security successor epoch LOCKED.
- Next transition: actual B raw bundle supply → independent DATA-01-C verification.
