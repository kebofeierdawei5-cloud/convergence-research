# IIOS Project State Index

State classification: **CANONICAL**
Snapshot: 2026-10-15
Authority: this file is the **only canonical Current State Index**.

## CURRENT ACTIVE DEVELOPMENT AUTHORITY — 2026-10-15

**Current canonical main:** Git ref `main` (resolve the SHA from Git; do not duplicate a fixed SHA in this document).

**Next user-visible acceptance:** one real macOS run and replay on current `main`, completing the portfolio and B5 model/baseline prompts, then reviewing `report.md`, `analysis.json`, and `pilot_receipt.json`. Do not start B7 scope expansion before this run exposes concrete functional gaps.

The records below are cumulative milestone history. A milestone's historical “next boundary” is **time-local** and MUST NOT be interpreted as the current development instruction.

### Current implementation state

```text
Investment Core / Stage C / C8 / PILOT-04              PASS / CANONICAL
Investor Review Report v0.2 + Human Acceptance          PASS / CANONICAL
B2-A Semantic Producer Admission                       PASS / CANONICAL
B2-B Natural-Language Conformance                       PASS / CANONICAL
B2-C Signed External Provider Binding                   PASS / CANONICAL
B2-D Canonical Refresh + Live Provider Boundary        PASS / CANONICAL
B2-D1 Live Evidence Verification Hardening             PASS / CANONICAL
B2-D2 Provider-Neutral Runtime Boundary               PASS / CANONICAL
B2-D Live Provider Invocation / Evidence                OPTIONAL / BLOCKED — NOT MVP GATE
B2-E Natural-Language → Semantic → Decision E2E          PASS / CANONICAL
B2-F Full Independent Red-team                          PASS / CANONICAL
P0 B3 persisted upstream write authorization             MERGED / EXACT-HEAD CI PASS
P0 Canonical Runtime Callback Preflight                  MERGED / EXACT-HEAD CONTRACT + ADVERSARIAL PASS
Batch 0 narrow state reconciliation                     PASS ON MERGE; NO ECONOMIC SEMANTICS CHANGED
Local MVP Batch 0 baseline audit (revised plan)          BASELINE ESTABLISHED / ARCHIVED RESPONSE CONTRACT FAIL / MAC RUN BUNDLE OPEN
Local MVP Batch 1 IIOS decision-kernel integration             MERGED PR #404 / 17-OF-17 EXACT-HEAD CHECKS PASS / MAC RUN OPEN
Batch 1 private Path A scenario runner                  PASS / MERGED; 40 TESTS; ANALYSIS-ONLY
Batch 1 macOS local pilot + hash-bound replay             PR #411/#417 MERGED; POST-#417 MAC RUN + REPLAY ACCEPTED WITH SCOPE LIMIT; PR #422 fixed default prompt; real Mac rerun with completed portfolio package DEFERRED / PENDING
Batch 2 Path A scenario integrity audit                    IN PROGRESS / PR #360 MERGED; 43 TESTS + 13 EXACT-HEAD CHECKS PASS; LOCAL BUNDLE REVIEW OPEN
Operator-entered price decision-input track                 MP-1/2 + REPORT ASSURANCE PASS; MP-3 MULTI-SLICE + COMPLETE RECEIPT-REPLAY TEST PASS / PRs #372/#375/#377/#378/#379/#383; LOCAL PRIVATE RUN REVIEW + RESIDUAL BYPASS CASES OPEN
C0 Local-first architecture / product-entry decision     DECISION RECORDED; IMPLEMENTATION GATES OPEN
P0 incident workflow zero-job anomaly                    OPEN / DIAGNOSTIC BACKLOG; NON-BLOCKING FOR LOCAL PILOT
C1 formal Evidence/PIT admission                         OPEN / TRUST REGISTRY EMPTY; SSE PRICE RIGHTS UNGRANTED
C2 independent fact/use sign-off                         OPEN / 13 LOCATORS PASS; INDEPENDENT SIGNER AND RIGHTS SCOPE PENDING
D1-A operator host preparation                           RUNBOOK READY / SEPARATE TRACK; LOCAL MODEL NOT REQUIRED FOR C1/C2 SIGNER OR RIGHTS REVIEW
Production P0-LLM-001 / P0-LLM-004                      OPEN / REAL-HOST ACCEPTANCE REQUIRED
D1-A 605016 production Host acceptance                         RUNBOOK + LOOPBACK PROBE TOOL CANONICAL; HOST PROBE OPEN; C1 FORMAL ADMISSION REQUIRED; GREEN B2-D JOB IS NOT LIVE-PROVIDER PROOF
605016 source-vintage successor                           PASS / LOCAL CORE-VALIDATED CANDIDATE; FORMAL/HOST GATES OPEN
Route A C2 / 新和成 002001                            PRIVATE CORE/PIT PASS (7/7; PRIOR INPUT); FORMAL/INDEPENDENT/HOST GATES OPEN
Path A operator-attested price overlay               ANALYSIS-ONLY INTAKE IMPLEMENTATION; NO CANONICAL PRICE ADMISSION
Local single-user complete pilot                     ACTIVE P0 PRIORITY; PILOT_NON_CANONICAL BEFORE FORMALIZATION
Residual MP-3 adversarial expansion                  PAUSED EXCEPT DEMONSTRATED PILOT-BLOCKING DEFECTS
B4 operating-driver forecast bridge                    MERGED PR #424 + #426 SAFEGUARDS; LOCAL PILOT 74 PASS; RED-TEAM 7 PASS; 7 TRIGGERED WORKFLOWS SUCCESS
B5 valuation transmission / entry price mapping          MERGED PR #428; LOCAL PILOT 81 PASS; 7/7 TRIGGERED WORKFLOWS SUCCESS; EPS_MULTIPLE ONLY
B6 price zone / binding cap / sensitivity ladder           MERGED PR #430; LOCAL PILOT 87 PASS; 7/7 TRIGGERED WORKFLOWS SUCCESS; PRICE SCREEN ONLY
Local Mac full-run + Replay acceptance harness             MERGED PR #433; 15/15 EXACT-HEAD WORKFLOWS PASS; REAL MAC RUN + REPLAY OPEN
```

### B3 — close the local portfolio-context slice (2026-10-14)

- PR [#422](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/422) merged at `9bd48288ae88ca5b5bc172663dfc2d3872d3b968`.
- The standard wizard now defaults to collecting operator-owned portfolio risk budget and position limits; skipping requires explicit `0`. No decision policy or sizing formula changed.
- Exact PR head `5d6733689f538b8ab9444d14c8f5fe6babeee7a0`: dedicated local-pilot workflow `64 passed`; all 7 triggered workflows succeeded.
- **Still pending:** a new real macOS 605016 run using the merged `main`, completing the portfolio prompts from actual operator constraints, and reviewing `report.md`, `analysis.json`, and `pilot_receipt.json` from that run. CI does not substitute for this run.
- If the operator cannot confirm portfolio constraints, preserve `UNKNOWN`; no conditional size is implied and authorized new position remains `0%`. The pilot remains `PILOT_NON_CANONICAL`; this usability change does not create a formal Decision or trade authorization.

### B4 — operating-driver forecast bridge (2026-10-14)

- PR [#424](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/424) merged at `7cc511207a391ce9fac988cc24b6415a0011f138`.
- Added `IIOS-OPERATING-DRIVER-FORECAST-0.1` and wired it into the local `PILOT_NON_CANONICAL` prompt, normalizer, analysis, report and replay comparison. It separates `OBSERVED_ACTUAL`, `ISSUER_FORECAST`, `ANALYST_ASSUMPTION` and `UNKNOWN`; actual/issuer values need a registered, cutoff-compatible source reference to be calculation-usable.
- Per-product/scenario bridge computes sales × net ASP, sales × variable cost, EBITDA, EBIT, pre-tax and simplified after-tax earnings, plus a free-cash-flow proxy only when required inputs are present. Units are checked; missing values remain UNKNOWN; working-capital release may be negative and tax-rate ratios must be 0–1.
- Exact-head acceptance: local pilot **70 passed**; investment-core CI **412 passed**; independent red-team **7 passed**; all **7 triggered workflows succeeded**. These are repository tests, not a live Mac/chat-response run.
- Actual project contribution for 百龙创园 remains NOT_IDENTIFIABLE where project-specific actual shipments, net selling prices, unit variable costs, attribution and dilution are not publicly reconciled. The bridge explicitly reports `NOT_LINKED_TO_PER_SHARE_VALUE`; B5 must not infer project EPS or overwrite the human-selected valuation model.
- B3 Mac run with portfolio questions answered remains DEFERRED / PENDING and may be resumed after core code delivery. Do not mark local acceptance passed until a real run is reviewed.
- Post-merge calculation-integrity follow-up PR [#426](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/426) merged at `fb23f396128dfe73f84302f1e2d91d341101ccc6`; exact PR head `81cccf1305621a48c556a17f63d3a46f4e4edc9b` passed 74/74 local-pilot tests, 7/7 independent red-team tests, and all 7 triggered workflows. It prevents forecast/actual data-class leakage, makes duplicate product rows non-calculable, and preserves UNKNOWN utilization unless the period is explicitly a full year. This is code/CI evidence only; no new real Mac run is claimed.

### B5 — project earnings to per-share value and entry-price mapping (2026-10-14)

- PR [#428](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/428) merged at `f6de0db1320693b9dff1e73846cf8c78a19c63ff`; exact PR head `2ff8cb4dc1da671d2dcccd4f232f7e76feed57c3` passed **81/81 local-pilot tests** and all **7 triggered workflows**.
- Added the typed `IIOS-VALUATION-TRANSMISSION-0.1` adapter to the existing B4 → local analysis → report → v0.3 return/entry-price solver path. The operator, not AI, selects the primary model family and confirms whether the baseline valuation already includes the project.
- EPS-multiple incremental transmission is the only supported formula in B5. It accounts for project after-tax profit, ownership, displaced existing-business after-tax profit, basic shares, convertible-bond/other dilution and P/E multiple. It updates all three scenario terminal values and the Base entry-value anchor atomically only when each link is calculation-usable and the operator explicitly confirms the existing valuation excludes the project.
- If the existing valuation already includes the project, it reports sensitivity without double counting; if scope/model/period/attribution/cannibalization/dilution is unknown or inconsistent, original valuation is preserved and transmission remains NOT_LINKED. DCF/FCF, DDM, SOTP and RNPV are not run through the EPS formula.
- This is provisional pilot output only. The 81-test CI acceptance is not a new real macOS run, formal valuation admission, canonical Decision, or trade authorization. B3 Mac completion remains pending.

### B6 — current price zone, binding cap and sensitivity ladder (2026-10-15)

- PR [#430](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/430) merged at `bebf0abe8cc666e010b4d5a5cdcd634a5dfbd11b`. Exact head `6b7665d559cbfddda4518658b8df3ba3123024f3`: **87/87 local-pilot tests passed** and all **7 triggered workflows succeeded**.
- Adds `IIOS-PRICE-ZONE-SENSITIVITY-0.1` to machine-readable analysis and the Chinese report. It identifies the lowest existing cap among the 15% entry-return cushion, 15% annualized return hurdle, Required Return and the existing Bear-loss cap; ties remain visible.
- Classifies current price versus the combined entry-price cap and entry-value reference. The 90% / 100% / 110% sensitivity ladder reuses the existing `_return_metrics` → v0.3 `calculate_return_metrics` path and uses the prepared post-B5 valuation, including a valid B5-adjusted anchor where applicable. The 100% row is checked against the primary current-price result.
- The output is explicitly price-screen-only and records `decision_action_changed=false`; it never promotes an overall action. Missing/invalid return inputs preserve UNKNOWN. B6 adds no thresholds or data sources and is not a canonical Decision.
- These are exact-head CI results, not a new real macOS user run. The immediate next validation priority is the current-main Mac end-to-end run and replay review; the prior B3 run with complete portfolio inputs remains pending.

- B6 is now closed as a provisional code milestone. Next user-visible acceptance is one real macOS end-to-end run and replay on current `main` before expanding scope.

### Local MVP Batch 0 baseline audit (2026-10-13)

Audit record: `docs/iios/BATCH0_LOCAL_PILOT_BASELINE_AUDIT_20261013.md`.

- The archived `IIOS_Pilot_Response_山东赫达_002810_20261012.json` was reviewed as a research response/input, together with its separate narrative summary. These artifacts are in the user's Library, not the public repository; neither proves that the current local runner generated a bound output bundle.
- The archived response predates the current response contract and lacks `forecast_valuation.thesis_break_stress`, which current validation requires. It must be repaired/regenerated through the current handoff; do not weaken current validation.
- The visible response preserves conservative states (Trust UNKNOWN; MIE NOT_IDENTIFIABLE; expectation gap UNKNOWN; Risk UNKNOWN) and uncalibrated scenario assumptions. It does not establish formal evidence admission or a canonical BUY/ADD.
- Source review also found that the current local pilot receipt has no output-file hashes and the replay-labelled path does not compare a prior output against recomputation. This is a concrete reliability-batch gap, not Batch 0 evidence of replay success.
- **Batch 0 status:** enough baseline is recorded to proceed to core integration. The actual private macOS output bundle and current-run receipt remain NOT VERIFIED and do not block work on the non-canonical pilot. No quote values or private payloads were copied into Git.

### Local MVP Batch 1 — shared decision policy integration (2026-10-13; implementation PR open)

Implementation: PR [#404](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/404), merged at `0a1fc7a83f78108ce154e8c8eea17054ea159cf9`; 17/17 exact-head checks passed, including the dedicated local-pilot workflow (47 tests), compile/diff checks, Investment Core, MVP, scope/state hygiene and independent red-team workflows.

- The local pilot now routes provisional decision-policy evaluation through the shared `evaluate_production_decision` kernel instead of relying solely on a separate hand-written action branch. The deterministic return/entry-price calculation continues to use the existing v0.3 contract.
- Price eligibility is reported separately from overall decision readiness. A price screen can pass while the overall proposed action remains `REVIEW_REQUIRED`.
- The pilot does not invent a PASS for missing portfolio capacity, formal Thesis Admission or the complete BUY/ADD position package. These missing gates remain visible and block promotion of the kernel preview into an actionable capital proposal.
- Any kernel BUY/ADD/EXIT/REDUCE suggested from non-canonical AI response fields is demoted to `REVIEW_REQUIRED`; no formal Decision, canonical admission, execution authority or automatic trade is produced.
- This is a provisional-policy integration, not a production-host or real Mac acceptance. The code milestone is merged and its exact-head CI passed; the actual private Mac run bundle remains NOT VERIFIED.

### Personal local investment pilot — response-file handoff and report-quality gates (2026-10-12)

The one-click macOS pilot hands the large ChatGPT response through a dedicated UTF-8 JSON file in `~/.iios-private/local-pilot/inputs/`, not through `pbpaste` and not through long Terminal pastes. The wizard opens the response file in TextEdit and reads/validates it on Enter. Empty, truncated, or structurally invalid JSON produces an actionable message and can be corrected in place without restarting the wizard.

The report-quality follow-up explicitly resolves structured evidence references against `evidence_register` across assessment and forecast/valuation inputs, labels missing IDs as unresolved, preserves structured risk/assumption records for readable rendering, removes fragile Markdown tables in favor of portable headings/lists, and normalizes value-driver display numbering. The guided workflow preserves strict date-only PIT behavior when no time is entered; an optional timezone-aware `case.as_of_timestamp` enables same-day pilot observations only when their stated `known_at` is at or before the explicit cutoff. The output records which cutoff semantics were used. Referenced sources with missing/invalid `known_at`, or a date-only `known_at` matching the cutoff date, are now marked `UNKNOWN`, `KNOWN_AT_INVALID` or `KNOWN_AT_PRECISION_INSUFFICIENT` and force `REVIEW_REQUIRED` rather than silently supporting BUY/ADD. Exact time compatibility does not prove source authenticity, rights or formal/canonical admission. The latest personal-pilot report gate also detects explicitly labelled conflicting price claims in free-text notes; any conflict forces `REVIEW_REQUIRED`, while calculations use only the structured `price_input.price`. Bear scenarios must specify a failure trigger, operating impact and valuation mechanism; Bear/Base/Bull total wealth must be ordered, and a separately quantified thesis-break stress case (excluded from probability-weighted expected return) must be more adverse than Bear. Missing/inconsistent stress inputs force `REVIEW_REQUIRED`.

This is a usability/reporting repair to `PILOT_NON_CANONICAL` only. Explicit timestamp support is for the provisional local pilot's time-bound checks; it does not change the date-only Core/PIT contract, formal Evidence/PIT/Forecast/Valuation admission, canonical Decision authority, or human approval requirements.

### First operator-supplied single-company local run and renderer follow-up (2026-10-13)

- The operator supplied the Chinese Markdown report produced by a real local `PILOT_NON_CANONICAL` run for 山东赫达. Report-level arithmetic for the displayed scenario assumptions was internally consistent; the computed price screen passed while the policy result correctly remained `REVIEW_REQUIRED` because Trust was UNKNOWN, Reality/Quality were conditional, MIE was NOT_IDENTIFIABLE, expectation gap was UNKNOWN, and portfolio/formal Thesis Admission/complete BUY-ADD package inputs were unavailable. No price values or private input JSON were copied into this state record.
- The first-run report exposed three presentation defects: structured risk-item `summary` text was omitted; Markdown separated ranked-driver list items such that some renderers displayed repeated `1` numbering; and trailing Chinese punctuation could be included in auto-linked source URLs. The report also repeated the price-screen status line.
- PR [#406](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/406) fixes these defects in the human-readable renderer and adds focused regression tests. It was merged at `fc1da918a7e90fd784899a922d7d995f200e8e42`; all six checks on the exact PR head passed: local-pilot, pilot-02, test-mvp, pilot, threat-reproduction, and post-b04-redteam.
- **Existing-run cross-check (operator review, 2026-10-13):** the operator has now cross-checked `analysis.json` and `pilot_receipt.json` against the first Chinese report. The three records use the same `pilot_id`; case/symbol/cutoff and operator-attested price content agree; scenario-weighted terminal value, annualized return and entry-price screens are arithmetically consistent. The resulting provisional action correctly remains `REVIEW_REQUIRED`: Trust is `UNKNOWN`, MIE is `NOT_IDENTIFIABLE`, expectation gap is `UNKNOWN`, and portfolio constraints/formal Thesis Admission/complete BUY-ADD package are still missing. The old report was generated before PR #406 and therefore does not contain the rendering fixes.
- **Immediate next action:** use the current-Main macOS launcher `双击运行_IIOS山东赫达当前Main端到端试运行.command`. It resolves `main` when launched and uses the prepared current-main-compatible response; do not repeat web research or hand-edit the JSON. Review the newly generated `report.md`, `analysis.json` and `pilot_receipt.json` together: the new run's `pilot_id` must agree across all three; confirm readable risk summaries, distinct value-driver numbering, no duplicate price-screen line, and source URLs with punctuation outside the link.
- **Next after the fixed-report bundle passes:** run a second generic candidate-driven case for 百龙创园 (605016), with a fresh cutoff and operator-confirmed price, before prioritizing receipt-hash/replay engineering. Validate incremental expansion economics and preserve UNKNOWN wherever actual product-level realization or profit data are not available.
- **Residual traceability limit:** `pilot_receipt.json` currently records output filenames but not content hashes. The content-level consistency check cannot prove that the original bytes came from the same output directory and write. Keep output-byte binding as an open, later reliability item; this is not a reason to expand the current task into a broad anti-tampering project or to mark formal Decision/Execution authorization as complete.
- This follow-up changes report presentation only. It does not change valuation assumptions, decision thresholds, market price inputs, evidence admission, formal Decision authority or trading authorization.

### Cross-company pilot and run-bundle binding follow-up (2026-10-13)

- The operator supplied a fresh local report and machine-readable `analysis.json` for 百龙创园 (605016), cutoff 2026-10-13 15:30 +08:00, with operator-attested 19.75 CNY quote at 15:00. This is a real second-company report/analysis run; no private stock-price payload is copied into this repository.
- The result preserves `PILOT_NON_CANONICAL`, `REVIEW_REQUIRED`, uncalibrated scenario assumptions, and no execution authority. At the stated cutoff, the same-day convertible-bond approval announcement has only a date-level `known_at`; it is correctly flagged `KNOWN_AT_PRECISION_INSUFFICIENT`, so referenced-evidence timing prevents validation PASS. The price-only screen separately fails its return/risk ceiling. Do not weaken this timing gate to turn the case green.
- The *initial* 605016 report/analysis upload did not include `pilot_receipt.json` and remains an unverified historical artifact. This limitation is superseded for local workflow acceptance by the fresh post-#411 run documented below; do not retroactively treat the initial run as hash-verified.
- PR [#411](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/411) merged at `1c8bd09daec18d4af0dd01a51a66e23d85082411`; its exact-head local-pilot workflow passed 54 tests and all 15 triggered workflows passed. New receipts record SHA-256/byte-size fingerprints for `input.json`, `analysis.json`, and `report.md`; `--check-run` performs read-only byte verification; replay verifies the prior bundle and compares decision-material fields while ignoring the volatile run ID. A replay with mismatched material fields reports `PILOT_REPLAY_MISMATCH`, not success.
- The receipt intentionally does not hash itself (that would be self-referential). These per-output hashes are local integrity checks, not a signature or formal/canonical receipt. Legacy hashless runs remain unverified and cannot be silently upgraded to verified replay.
- The local macOS execution and output bundle remain operator-environment evidence; repository CI cannot stand in for the user's Mac run.

### Post-#411 real macOS run and verified replay acceptance (2026-10-13)

- The operator uploaded the current-main local run ZIP for 百龙创园. It contains first-run and replay reports, analyses and receipts plus the local acceptance summary. The summary reports `LOCAL_PILOT_HASH_AND_REPLAY_CHECKS_PASS`.
- Independent review recomputed SHA-256 and byte size for each included `analysis.json` and `report.md`; both match their corresponding first-run/replay receipt manifests. The report bytes are identical across both runs. An independent comparison of all 19 declared decision-material fields found no mismatch; only the volatile `pilot_id` differs.
- The uploaded ZIP intentionally excludes `input.json`. The two receipts record the same input digest and byte size, and the local summary reports the input bundle check passed; this review cannot recompute that input digest from the uploaded archive, so this limitation remains explicit.
- The output remains `PILOT_NON_CANONICAL` and `REVIEW_REQUIRED`; the return hurdle still fails, the same-day convertible registration announcement retains `KNOWN_AT_PRECISION_INSUFFICIENT`, and no formal Decision, canonical Run Receipt, execution authority or auto-execution is created. No quote value or private research payload is committed.
- **Batch acceptance:** the post-#411 current-main macOS output-binding and true replay checkpoint is accepted within the above scope. The next active work is the practical portfolio/position package, reusing the existing risk/portfolio contract rather than creating a second decision engine. The C5 positioning/sizing evaluator requires its own PIT-valid, sourced observation and is not imputed from AI sentiment. C1/C2 admission and rights review continue in parallel.
  
### Practical portfolio risk-budget package — PR #414 merged (2026-10-13)

- Added optional operator-only portfolio inputs separate from ChatGPT research content: constraint status, add-permission flag, portfolio-NAV stress-loss budget, entry zone, and initial/target/maximum position weights. Skipping input keeps portfolio status UNKNOWN.
- The package reuses the existing `risk_portfolio_production_contract` and reports a conditional position cap from the independent `thesis_break_stress` value at the entry-zone upper bound, capped again by the user's concentration limit. Existing positions above the calculated cap are flagged for manual review only; no automatic reduction is issued.
- PR #414 merged at `37b4f806bfc96f9cc39bce0fd7364cc1cce2f0bf`. The exact tested PR head passed the Local Investment Pilot workflow (61 tests) plus 14 other triggered workflows: Investment Core CI, MVP Pilot, B00-B authority threat reproduction, Post-B04 red team, M1.2 CATL exact-source admission, PILOT-02 Xinhecheng candidate and the remaining governance/runtime checks. The subsequent guide and state/plan documentation updates were also covered by the final 15/15 exact-head workflow run.
- **Real-user feature acceptance still open:** the package implementation is merged and server-side test/workflow verified, but the new portfolio prompt/conditional-sizing output has not yet run on the user's Mac. A fresh local run is required. The report remains `PILOT_NON_CANONICAL`; conditional sizing never means an authorized position, which remains 0%, until formal gates and human approval are independently met. No private portfolio values are committed.
- Next after real-run confirmation: focus on 605016's actual expansion contribution using disclosed project capacity, ramp, volumes, selling prices, costs, and actual contribution where identified; do not infer realized earnings from capex progress alone.

### Portfolio prompt EOF incident and terminal-input fix (2026-10-13)

- **Operator incident:** the fixed-input 605016 launcher invokes its Python driver from a heredoc. The newly added optional portfolio prompt used builtin `input()`, which read the exhausted source stream and raised `EOFError` before the run could finish. This was an implementation defect, not an operator-input error.
- PR [#417](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/417) merged at `67d22036269bcff4bab20cda3d076a3b739e0e0c`. The prompt reader now uses the macOS controlling terminal when Python is executing from non-interactive stdin, preserves the normal prompt path, and emits an actionable error when no terminal is available. The dedicated local-pilot suite passed **63/63 tests**, and Investment Core CI, MVP Pilot, B00-B, Post-B04 and PILOT-02 checks all passed on the exact PR head.
- A replacement 605016 package was rebuilt with the repaired source fallback SHA. Archive integrity, executable bit, shell syntax, bundled case identity/cutoff, and the documented repair note were checked before the operator reran it.
- **Real Mac acceptance completed within scope on 2026-10-13:** the newly uploaded ZIP contains first-run and Replay analyses, reports, receipts and acceptance summary. Independent SHA-256/byte-size checks for both included analyses and reports match their receipt manifests; the reports are byte-identical; all 20 declared decision-material fields compare equal and Replay says `MATCH`. Receipt manifests bind both runs to the same input digest/size.
- **Explicit limitation:** the ZIP omits `input.json`, so this review cannot independently recompute the input digest or inspect the original payload bytes. The digest in the receipts and local summary is recorded, but whole-input integrity remains supported by the local acceptance summary rather than reverified from this archive. This is not a full canonical IIOS Run Receipt.
- The optional portfolio wizard was skipped. `portfolio_package.status=NOT_PROVIDED`; the portfolio/risk-budget sizing therefore remains `UNKNOWN`, rather than a failed calculation. The pilot's actual authorized new position stays `0%`; the run remains `PILOT_NON_CANONICAL / REVIEW_REQUIRED`, with no formal Decision or execution authority.
- No portfolio inputs, price quote, local paths, output ZIP, or private response payload were committed to Git. PR #417 is now accepted on the real Mac for its intended TTY-prompt fix.

### 605016 expansion project's realized-contribution and unit-economics review (2026-10-13)

- First-pass revenue attribution and capex reconciliation are recorded in [605016_EXPANSION_PROJECT_REALIZED_CONTRIBUTION_REVIEW_20261013.md](iios/605016_EXPANSION_PROJECT_REALIZED_CONTRIBUTION_REVIEW_20261013.md).
- Further product/unit-economics reconciliation is recorded in [605016_PROJECT_UNIT_ECONOMICS_EVIDENCE_REVIEW_20261013.md](iios/605016_PROJECT_UNIT_ECONOMICS_EVIDENCE_REVIEW_20261013.md). It separates issuer forecasts from realized data and highlights that 2025 product-revenue/disclosed-output ratios are not valid realized ASPs without matched sales-volume/product-form/inventory reconciliation.
- Disclosed plan, not actual: the separate calendar-year capacity-release schedule gives 7,800/10,400/13,000 t for 2026/2027/2028; corresponding prospectus financial rows are project Years 3/4/5. No project-attributed shipments, realized prices, unit costs or incremental profit have been identified by 2026-10-13. A new audit flag `RAMP_CALENDAR_BASIS_UNRECONCILED` records that if 7,800 t meant actual 2026 calendar-year sales despite commissioning through H1 and expected commercial start around end-Q3, it is 2.4x the nominal Oct-Dec nameplate capacity of 3,250 t; this is a basis-reconciliation question, not proven forecast error. Keep project EPS out of Base; refresh after the Q3 report scheduled 2026-10-30.
- The post-#417 portfolio prompt fix has passed a real Mac test within scope and is recorded in PR #418 / main merge 3c48a818. The operator skipped portfolio inputs, so conditional sizing remains UNKNOWN; authorized new position remains 0%.
- **Next batch:** C1/C2 formal Evidence/PIT and rights/sign-off track. The short [C1_C2_NEXT_OPERATOR_ACTIONS_20261013.md](iios/C1_C2_NEXT_OPERATOR_ACTIONS_20261013.md) checklist consolidates the existing signer/rights and C2 review tooling. This track remains open on actual written rights, explicitly approved trusted signer enrollment, and a genuinely independent human reviewer.
### Local pilot guided-input / empty-response gate (2026-10-12)
The follow-up handoff embeds the full operator template directly into the clipboard prompt, so users no longer need to upload the separate template or manually collect source documents before ChatGPT starts researching. The prompt asks the web-enabled ChatGPT session to find cutoff-safe public company/exchange/regulator sources, separate evidence from valuation assumptions, and return one complete JSON object. If validation fails, a repair prompt with the validation feedback, original prompt/template and prior response is copied to the clipboard; the operator can paste it into the same ChatGPT conversation, replace the existing response file with the corrected JSON, save and press Enter. No manual field-by-field JSON editing or wizard restart is required. The validation also checks quantitative entry reference, Bear/Base/Bull probabilities and per-share terminal/cash values, and thesis-break stress values. This remains a browser ChatGPT workflow; no local model or provider API is introduced. Routine input prompts are also reduced: the close-after-cutoff choice is the default, closing-price availability defaults to 15:00 +08:00, and manual-price provenance is generated automatically; only non-close quotes require a custom timestamp. The operator can leave the common path on defaults instead of typing a full ISO timestamp and price-source sentence.


The macOS one-click wizard now offers named cutoff modes: date-only start-of-day (strict prior-date data), same-day close plus 15:30 +08:00, or an advanced explicit timezone-aware timestamp. Common same-day-close runs no longer require manually typing an ISO timestamp. Price-date parsing errors are caught within the prompt, weekend quote observation dates are rejected by both wizard and direct JSON input validation rather than silently treated as market closes, invalid prices/positions are re-prompted, and the wizard states that exchange holiday calendars are not queried.

Before generating a report, the guided response handoff now rejects a mostly untouched template: it requires at least one traceable evidence-register row and substantive Trust/Reality/Quality/MIE/expectation-gap/risk summaries, Thesis content, value drivers, scenario rationales, Bear failure path, model rationale/assumptions, and a standalone thesis-break stress explanation. Explicit UNKNOWN conclusions are allowed only when the response supplies a real explanation. An incomplete response remains open for correction in the same private response JSON; no empty report is generated. This is a usability gate for the personal PILOT_NON_CANONICAL path and does not certify evidence truth, data rights, formal admission, or investment validity.

### C1/C2 signer enrollment preparation (2026-10-12)

The signed Evidence/PIT CLI now supports `prepare-enrollment-request` and `prepare-rights-draft`. Signer enrollment proposals validate an Ed25519 public key and remain `PROPOSED_NOT_TRUSTED`; they exclude private keys, reject wildcard case scopes and combined admission/reviewer roles, and cannot modify the canonical registry. Rights drafts remain `UNKNOWN` by default, have no allowed uses or admitted permission instrument, and record any supplied candidate instrument hash only as a candidate. Neither command decides legal/data-use rights, enrolls a signer or admits Evidence/PIT. Owner authorization, separate independent review, written permission where required, and exact instrument verification remain open gates.

### C1 formal-admission preflight (2026-10-13)

A read-only `preflight` subcommand has been added to `iios_mvp.canonical_signed_evidence_admission_v01`. It checks the unchanged Core/PIT validator against raw bytes, the case-bound rights record and exact permission-instrument hash, and eligible trusted signer/role/case-scope coverage. It returns `BLOCKED` or `READY_FOR_SIGNATURE_NOT_ADMITTED`; the latter is not admission. It never signs, changes the trusted registry, grants rights, or creates Decision/Publication/Run Receipt/execution authorization. Exact-head Signed Evidence Admission Gate CI passed 36 tests, and relevant Investment Core/MVP/local-pilot checks passed for this head. **Actual C1 remains BLOCKED**: canonical trusted signer registry is empty and exchange-market-price use permission is not established. No private case manifest, market quote, raw source bytes, or key material was added to Git.

### C2 independent fact/use review packet preparation (2026-10-13)

Added `iios_mvp.c2_independent_fact_review_v01` to generate a private, mode-0600 packet from the existing sanitized C2-P3 archive. The packet contains 13 fact-level source/page/hash/size/known-at references and leaves each independent-review verdict, use-rights scope, retention terms and permission instrument explicitly `PENDING`. It rejects reports with failed/incomplete 13-fact machine checks, altered case/cutoff, duplicate/unmapped rows, unexpected reuse status or any market-price value. Tests cover deterministic construction, permissions and fail-closed cases. This is only a review aid; it does not inspect the preserved private PDFs, certify reviewer independence, grant rights, sign records, or admit facts. The separate human/authorized reviewer step remains OPEN, as do the applicable company-disclosure rights disposition and C2 formal signed Evidence/PIT admission. `OPERATOR_ATTESTED_MARKET_DATA` remains a distinct non-admitted price class.

### C2 independent fact/use review packet preparation (2026-10-13)

Added `iios_mvp.c2_independent_fact_review_v01` and regression tests to generate a private review packet from the pinned sanitized C2-P3 archive. The packet carries 13 fact IDs, labels, official PDF URLs, page locators, source byte hashes/sizes and conservative `known_at` bounds, with all independent reviewer conclusions, reuse/retention scope and permission instrument fields explicitly `PENDING`. It fails closed for changed case/cutoff, incomplete 13/13 machine checks, duplicate/unmapped rows, reuse-status changes or any numeric market-price value. It writes mode-0600 output outside the repository and includes no source PDF bytes or market quote. This is only a review-preparation tool: it does not inspect private PDF bytes, establish reviewer identity, grant rights, sign records or admit facts. **C2 remains NOT FORMALLY ADMITTED** until a genuinely separate reviewer resolves fact-level accuracy and use scope, the exact case manifest/rights record is reconciled, and authorized distinct signatures pass. Operator-attested market price remains a separate non-admitted class.

### Execution-first local MVP priority (owner direction, 2026-10-11; supersedes earlier task ordering)

The user has explicitly redirected IIOS delivery to **finish the core workflow and run it end-to-end in actual personal use before further optimization**. The governing decision and testable acceptance criteria are recorded in [Execution-first Local Single-User MVP Pivot](iios/LOCAL_SINGLE_USER_EXECUTION_FIRST_PIVOT_20261011.md).

Immediate order:

**Simplified personal app entry (2026-10-12):** the normal operator entry is now the repository-root `启动IIOS投资分析.command`. It launches the guided wizard, asks only the basic company/market/price/position inputs, opens ChatGPT and the input template, copies the research prompt to the clipboard, opens a dedicated JSON response file in TextEdit, reads the saved file when the operator presses Enter, runs the pilot and opens the Chinese report. The complete response is never pasted into Terminal. This is a usability shell around the existing `PILOT_NON_CANONICAL` engine—not a second investment engine and not a formal/canonical admission path. Follow [the simplified quick-start](iios/LOCAL_INVESTMENT_PILOT_V01_GUIDE_20261011.md); low-level CLI flags are fallback/developer options, not the user-facing workflow.

1. Pause additional MP-3 adversarial edge cases / anti-tamper expansion except defects that block the pilot or can silently distort an investment result.
2. Implement a complete local, candidate-driven path using the existing company research, deterministic investment and report modules. The current fixed-profile Path A scenario calculator is not the final product.
3. Permit an explicitly segregated `PILOT_NON_CANONICAL` run using manual price and free/manual AI handoff when needed. Do not bypass formal admission or claim a canonical Decision / complete canonical Run Receipt.
4. C1/C2 signature and market-data rights gates remain necessary for the corresponding formal evidence/canonical claims but do not block development and use of the provisional pilot.
5. Keep the P0 zero-job CI anomaly open as diagnostic backlog; it does not block local use.

Minimum safeguards remain: cutoff/known-at and source disclosure, manual-price assurance, visible UNKNOWN/missing/conflict, deterministic calculations, private local persistence, Chinese report, human approval separation and no automatic trading. The priority is to run one real company through the workflow and use observed defects to drive iteration.

### Current blockers

**Action A governance decision (2026-10-11, applying frozen B0; not a B0 amendment):** manual ChatGPT Free Web outputs are **NO-GO for formal/canonical semantic admission** because saved-response hashes do not authenticate OpenAI/model origin. PR [#342](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/342) is PASS / MERGED / CANONICAL at `a496b82b8cfbc2256a9affd3337f97fce305d217`; its fail-closed guard inside `admit_semantic_artifact` blocks both the currently registered manual producer ID and renamed IDs retaining the unapproved `IIOS-CHATGPT-WEB-OPERATOR-POLICY-` namespace. The handoff can remain available for explicitly NON-CANONICAL operator assistance; no canonical semantic admission may result. This change does not authenticate provider origin or close P0-LLM-001/P0-LLM-004, production Host acceptance, or the full Run Receipt path. The proposed Round A / Round B workflow is still not implemented. Batch 1 is explicitly a deterministic private scenario-analysis path, not the formal Round A/B producer path. Governance audit and follow-up tests: [Action A Capability Map and Governance Decision](iios/ACTION_A_CAPABILITY_MAP_CHATGPT_WEB_GOVERNANCE_20261011.md).

**C0 architecture/product-entry decision (2026-10-11):** adopt LOCAL_SINGLE_USER/local-first as the default deployment profile while reusing the existing canonical CLI/loopback Host, Orchestrator, runtime factory, Store/admission records, report QA and Run Receipt/replay path. Remote/multi-user deployment and new UI are deferred unless the real user-entry pilot demonstrates a need. The separate formal semantic/model route must satisfy the existing producer identity, model/version, signed-receipt and lineage contracts. That optional integration path does not gate deterministic signer implementation or market-data rights review. The merged PR #342 guard remains in force: manual ChatGPT Free Web output is NON-CANONICAL for formal semantic admission. This is an architecture decision only and does not close P0-LLM-001/P0-LLM-004 or prove production use.

**Parallel execution checkpoint (2026-10-11):** C1's private/source-vintage candidate remains Core/PIT PASS but has no formal signed admission; no ingest rerun is authorized. The deterministic Ed25519 Evidence/PIT signing implementation and fail-closed source-rights contract are covered by PR #353; the trusted signer registry starts empty, no signer key has been enrolled, and SSE price-use rights remain ungranted. C2's 13 factual locators and cutoff bounds passed prior exact-head CI/local second-pass; official SZSE public-site terms do not alone settle market-price retention/computation rights, and independent fact/use signature remains pending. The operator-attested price remains unverified by source. **No local LLM, Ollama, model installation, or model API is a prerequisite for signer enrollment or rights review.** Production Host/model acceptance remains a separate track. See `docs/iios/EVIDENCE_ADMISSION_SIGNING_AND_MARKET_DATA_RIGHTS_GATE_20261011.md` and `docs/iios/EXCHANGE_MARKET_DATA_RIGHTS_REQUESTS_20261011.md`.

**Path A operator-attested price overlay (2026-10-11):** the operator supplied 2026-10-09 unadjusted closing-price inputs for 002001 and 605016. The prices are held in the conversation/private operator file only and are not written to the public repository. A dedicated deterministic intake validates them as `OPERATOR_ATTESTED_MARKET_DATA`, permits scenario valuation only, and emits a price-redacted receipt; source origin, source-vintage, rights and formal admission remain false. Because date-only cutoff `2026-10-09` means Shanghai start-of-day, these same-day closes must not be inserted into either frozen Case. The price overlay uses cutoff `2026-10-10` for its own attested-time check, but does not revalidate the whole company evidence set to that new cutoff and cannot create a formal Decision. No local LLM/model/API is required. See `docs/iios/OPERATOR_ATTESTED_PRICE_ANALYSIS_PATH_A_20261011.md`.

**Operator-entered price direction (2026-10-11):** current A/H prices remain manual `OPERATOR_ATTESTED_MARKET_DATA`; automatic quote retrieval is not required. PRs #366/#368/#370 established private intake/replay, typed Decision/Run Envelope binding and human/machine assurance disclosure. MP-3 PRs #372/#375/#377/#378/#379 cover missing resolver/reference conflict/forged receipt, Evidence/PIT non-substitution, snapshot-tamper, stale record hash/Case ID/currency/unknown class, all eight provenance flags plus exchange identity, and blocked-run no-publication/no-receipt guards. PR #383 extends the successful operator-price B2-E path through Machine Publication, investor report, final `COMPLETE` Run Envelope and complete Run Receipt. The two exact-head workflows passed; the suite confirms that the receipt stage-hash/chain matches the completed Run Envelope, does not expose the private bundle ID or the two private input hashes, and rejects a receipt whose `DECISION_PENDING` stage hash is tampered with and then rehashed. Synthetic CI coverage includes B2-E 24/24, B2-E red-team 8/8, B2 semantic admission 14/14 and semantic red-team 15/15; PR #378 passed 9/9 checks including `test-mvp` 412/412. **Still OPEN:** independent sanitized review of one actual local Mac bundle/receipt/replay and remaining deeper stage-bypass/replay adversarial permutations. C1 SSE rights and C2 independent fact/use sign-off remain separate open gates; manual price is not a company-filing fact or canonical exchange quote.

**The company-level Investment Core MVP does NOT require an external LLM provider endpoint, paid search API, or API key.** Free-first Route A remains independent of optional provider integration. The remaining critical gates are production-runtime registration/deployment and actual source-by-source Evidence/PIT admission.

- Batch B: the first-party loopback-first HTTP host is implemented in canonical main (PR #270; dedicated host contract 21/21). Trusted runtime factory implementation is now also merged in PR #274 (`a62e2304983cbdf28f0365f7fd55f53378c4adab`), exact head `14105076b1b69f626907e4eb8bdddf0893d84c23`, with 8/8 exact-head checks passing. It wires genuine provider-backed request/semantic producers plus read-only canonical admission resolvers, pins the Ed25519 runtime public key, and deliberately refuses synthetic upstream admissions. It is still **not a deployed/production-accepted host**: no real provider endpoint, secret/keypair, durable canonical admission store, or real host-origin run has been provisioned/replay-verified. The API-backed route remains unprovisioned; PR #296 additionally adds a free ChatGPT Web operator handoff for the request-intent and thesis-semantic callbacks without a local model, API endpoint or API key. That route is manual, its model origin is not cryptographically verified, and it does not close the production-host or formal Run Receipt lineage gates.
- Runtime callback preflight: PR #283 merged at `d18251fe7541267dad49d04bad67ada54ab58e31`; exact validated PR head `a86457fcadeb951bbc89e0e0a0b8d747ef55b0b3`. All 8/8 triggered checks passed, including 23/23 preflight/factory/Host contract tests and a separately executed 5/5 adversarial suite. New command: `python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id <staged_bundle_id>`. It invokes the existing trusted factory's request interpreter and semantic producer and reuses signed Ed25519 provider-receipt verification. CI exercised control-flow with explicit fake bindings only; the actual operator-environment callback has NOT yet been run. The report explicitly says Evidence/PIT admission and semantic admission are unchecked and Decision/publication/Run Receipt are not created. P0-LLM-001/P0-LLM-004 remain OPEN.
- Primary C1 case: `RC-CN-A-605016-20261009`. Official HTTPS evidence is privately persisted and the bounded successor has passed the unchanged Core/PIT validator. The original candidate remains intact; the new successor uses a deterministic official-rule-derived public-availability upper bound of `2026-10-08T15:30:00+08:00`. `exact_first_public_timestamp_verified=false` remains explicit. Formal signed admission, production Host acceptance and Decision remain open.
- **Route A C2 / 新和成 (002001.SZ):** PR [#333](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/333) fixed the Route A date-only cutoff conversion and schema to Shanghai start-of-day semantics; the historic Run #8 manifest/preflight remain untouched diagnostic artifacts. PR [#334](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/334) is merged at `00be321497baf9cf0352ae14b303c560bc5846b7`. Exact-head successor workflow [#38121849097](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38121849097) passed: the pinned Run #8 artifact SHA-256 was verified before extraction; 8 captured raw objects passed receipt/hash replay; 13 page-located fact candidates from 3 official SZSE PDFs passed locator checks; and the unchanged Core/PIT validator returned only `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`. The ephemeral candidate covers six required groups; overall B2 remains `BLOCKED` because the required 2026-10-08 close has no admitted source/vintage/allowed-use record. The 2026-10-09 same-day buyback-progress filing and close, dynamic issuer IR page, and Sohu/Eastmoney price pages stay excluded. The exact first-public timestamp is not verified, the original bundle does not contain the supporting board-resolution bytes, and independent source/vintage review remains PENDING. Sanitized report: `evidence/real_cases/RC-CN-A-002001-20261009/C2_SUCCESSOR_CORE_VALIDATION_REPORT_20261011.json` (report-only; no raw data or numeric market quote values).
- A successful CI, byte hash, URL/title match, or payload format check alone is not source-origin proof or formal PIT admission. No signed admission, production Host acceptance, Decision, Publication, complete Run Receipt or execution authority has been created by C2.

The independent B2-F audit remains PASS / CANONICAL. Production host acceptance and real-company admission remain OPEN.

### Historical 605016 Private B2 Persistence Recovery — 2026-10-10 (superseded by C1 closure below)

Status: **PDF RECOVERY / DIAGNOSTICS / BASH-ZSH CLEANUP MERGED; CONTRACT 19/19 PASS; EPHEMERAL B2 PASS; LOCAL MAC PERSISTENCE STILL UNVERIFIED**.

- PR #300 added `tools/iios_private_605016_b2_ingest_v01.py` and `tools/Launch_IIOS_Private_605016_B2_Ingest.command` for local-only private persistence. The path still reruns the established source adjudicator and the Investment Core-owned Evidence/PIT validator, then copies only manifest-referenced raw artifacts with exact declared size/SHA-256 into the user-owned private root.
- PR #302 added a recovery route for a transport-blocked SSE listing API, reusing the pinned canonical dividend adjudication while requiring a new current-run HTTPS PDF retrieval and exact-byte recheck.
- Operator then reported repeated `OFFICIAL_DIVIDEND_PDF_DIRECT_HTTPS_FETCH_BLOCKED`. PR #304 added fixed official SSE HTTPS URL failover. Subsequent review found another reachable failure mode: the listing row can be fetched while none of the ordinary PDF candidates yields a valid PDF; that branch previously bypassed recovery. A later actual CI attempt reached a captured response but failed the unchanged exact-byte contract, which correctly remained blocked rather than accepting changed bytes.
- PR [#308](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/308) merged at `951726ed877678aebc4343832c25619ad9bff559`. It now (a) tries bounded system `curl` over HTTPS only after all pinned Python HTTPS candidates are transport-blocked, with TLS verification enabled and no HTTP redirects; (b) reuses the prior source adjudication for a failed PDF fetch only when a live captured listing row exactly matches the pinned code, name, date, title and PDF path; (c) emits sanitized endpoint/transport outcomes or exact-byte mismatch metadata, without URLs, source payload, or numeric quote values; and (d) replaces the launcher’s unsupported Zsh `read -p` prompt with portable `printf` + `read`. Captured wrong-origin/changed-byte responses still block immediately; source hash, size, PDF magic, page count, PIT and private-only write constraints are unchanged.
- Exact-head persistence contract workflow [#38061855545](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38061855545) passed **19/19** tests and patch-format checks. Live official HTTPS B2 workflow [#38061855334](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38061855334) returned **PASS_EPHEMERAL_B2**, with **11/11** records, all **7/7** required field groups, zero missing groups and zero validation errors. Artifact [#11673038135](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38061855334/artifacts/11673038135) contains only sanitized status/hash/shape data, no raw source bytes, full manifest or numeric quote value. That latest live run succeeded through the ordinary current-run announcement/PDF capture route; it does **not** prove the curl fallback was the path used.
- The new failure metadata is explicitly diagnostic, not permissive. If all endpoints remain blocked, result remains `BLOCKED` with no candidate manifest or private write. If bytes are returned but do not match the pinned SHA/size/PDF contract, the diagnostic reports expected/actual hash and size plus PDF-magic status, but no file is admitted and no alternate host is tried after a captured response.
- **Latest operator blocker / recovery (2026-10-11):** initial local ingest returned `ATTEMPT10_ARTIFACT_DOWNLOAD_FAILED_CHECK_GITHUB_ACTIONS_ACCESS` with `private_store_written=false`. The workflow run/artifact were confirmed present and unexpired. PR [#315](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/315) is now merged at `f53477d710095be808d0a6ac9b88b45932f3c913`; 11/11 associated checks passed. The downloader now uses the official Artifact API redirect, verifies the pinned ZIP digest/size before extraction, avoids forwarding the bearer token to the redirect host, and rejects unsafe ZIP paths/types. **This resolves the code-path change only; no successful Mac rerun has yet been observed.** Rerun the launcher from canonical `main` with no argument; if it blocks, report the new stable JSON reason without uploading source files.
- **Latest operator result (2026-10-11):** after PR #315, the local launcher returned `ATTEMPT10_ARTIFACT_API_TRANSPORT_FAILED`; `private_store_written=false` and no admission/production acceptance was created. This error class conflates DNS/proxy/TLS/timeout/socket failures and is not enough to identify the Mac-side cause. The follow-up implementation keeps TLS verification enabled, tries a bounded system `curl` fallback only after Python HTTPS transport fails, does not follow the API redirect or pass bearer credentials to the signed-URL host, and emits sanitized transport categories without raw URLs/tokens. This is a diagnostic/resilience change, not evidence that the operator Mac is fixed; the same launcher must be rerun after merge.
- **Latest operator result (2026-10-11, after PR #317):** the Mac returned `ATTEMPT10_ARTIFACT_DOWNLOAD_TRANSPORT_FAILED` with `private_store_written=false`, showing the failure is now at the signed Artifact URL's ZIP download stage. The current downloader only attempted Python `urllib` for this second-stage body and mapped DNS/proxy/TLS/timeout/socket errors to one generic code. Follow-up PR [#318](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/318) adds an HTTPS-only system `curl` fallback for the signed URL without sending the GitHub API bearer token, keeps size/hash checks before extraction, and returns sanitized transport/HTTP failure categories. **Local persistence remains unverified until a fresh Mac rerun succeeds.**
- **Latest operator result (2026-10-11, after PR #319):** the local run returned `OFFICIAL_SSE_HTTPS_PRICE_FETCH_BLOCKED` with `private_store_written=false`. The price stage previously called the Python HTTPS helper once against `yunhq.sse.com.cn:32042` and collapsed every failed outcome to one code; unlike the dividend PDF path, it had neither a `curl` fallback nor the already-discovered official alternate TLS port `32041`. Follow-up PR [#320](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/320) adds primary Python HTTPS, then bounded HTTPS-only `curl`, then the fixed official alternate port. All captured bytes remain subject to the existing exact 124-byte SHA-256 and 2026-10-08 one-row JSON gates. If every path fails, the output exposes only endpoint/transport/outcome categories, never the raw response or URLs. This changes transport resiliency, not the evidence gate; local persistence remains unverified until the Mac rerun succeeds.
- **Prior operator result (2026-10-11, after PR #318):** the launcher returned `UNEXPECTED_PRIVATE_INGEST_FAILURE` with `error_type=NameError`, and no private data was written. Root cause found in the real network-recovery branch: `_build_base_manifest_from_prior_dividend()` referenced `final_url` without binding that name in its local scope when reusing the canonical dividend ledger after a blocked listing API. Follow-up PR [#319](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/319) binds the source reference to the captured `dividend.final_pdf_url`, rechecks it against the HTTPS host allowlist, and adds targeted tests for the recovery branch and invalid URL rejection. This remains a candidate-code fix until exact-head CI passes and the Mac rerun succeeds.
- Non-claims remain: no cryptographically signed formal admission, canonical request bundle, production Host acceptance, Decision/Report/Run Receipt, or trade authorization. Exact first-public timestamp/source-vintage review remains open.

### P0 — Canonical Runtime Callback Preflight — 2026-10-10

Status: **MERGED / EXACT-HEAD CONTRACT + ADVERSARIAL TESTS PASS / LIVE OPERATOR CALLBACK NOT YET PROVEN**.

- PR #283 merged at `d18251fe7541267dad49d04bad67ada54ab58e31`; exact validated PR head `a86457fcadeb951bbc89e0e0a0b8d747ef55b0b3`.
- Eight triggered exact-head checks passed: Investment Core CI, MVP Pilot, PILOT-02, B00-B authority threat reproduction, Post-B04 independent red-team, FM01 source admission, FM02 feature builder, and the dedicated runtime-preflight workflow.
- Dedicated workflow: 23/23 callback-preflight + trusted-factory + Host contract tests passed; a separate adversarial test file passed 5/5. Compileall and diff checks passed.
- New entrypoint: `python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id <staged_bundle_id>`. It loads only a trusted staged bundle, resolves the existing `iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime`, then calls the request interpreter and thesis-semantic producer through that factory. Signed provider raw-response receipts remain pinned to the configured Ed25519 public key and independently verified.
- The preflight report records signed receipt hashes and minimal provider metadata only; it does not copy model prompts/raw outputs. It explicitly writes `evidence_pit_admission_checked=false`, `semantic_admission_checked=false`, `decision_created=false`, `publication_created=false`, `run_receipt_created=false`, `human_approval_required=true`, and `auto_execution=false`.
- Operator instructions: `docs/iios/P0_CANONICAL_RUNTIME_PREFLIGHT_20261010.md`.
- **Non-claim:** no real operator environment was available to run this command against an actual local/self-hosted or external provider. The CI fake bindings prove only diagnostic control flow. A successful preflight will prove callback connectivity and receipt persistence, not deployed Host-origin acceptance, source admission, semantic admission, forecast/valuation quality or a completed canonical company run.
- The canonical provider contract is preserved. A self-hosted model must still use the existing factory and a verified HTTPS endpoint with `AUTH_MODE=NONE`; the pinned runtime keypair and admitted-store contract remain required. No paid commercial API key is mandatory for a properly deployed self-hosted provider.
- Historical status at the time of the runtime-preflight milestone (before PR #294): C1 did not yet have an admitted market-price candidate. This was superseded by the later `PASS_EPHEMERAL_B2` run; private durable persistence and production-host acceptance remain OPEN.

### P0 C1 — Source-by-source adjudication and unchanged B2/PIT — historical status before PR #294

Status at the earlier Attempt-10-only run: **REAL RAW-BYTE REPLAY PASS / PARTIAL FACT ADMISSION / B2 BLOCKED ON MARKET PRICE**. Superseded by the latest official HTTPS ephemeral B2/PIT run.

- PR #278 merged at `1e574438a255c350905c1575a13a691078fe27b8`.
- Source review: `docs/iios/ROUTE_A_C1_605016_SOURCE_ADJUDICATION_20261010.md`; machine ledger: `evidence/real_cases/RC-CN-A-605016-20261009/SOURCE_ADJUDICATION_20261010.json`; run receipt summary: `evidence/real_cases/RC-CN-A-605016-20261009/SOURCE_ADJUDICATION_RUN_20261010.json`.
- Actual Attempt 10 artifact #11660285551 was re-opened and all 12 raw file sizes/SHA-256 values and all 12 payload types were independently reverified. The exact core validator `research.b2.company_evidence.build_company_evidence_manifest` ran unchanged.
- Six of seven required groups pass: `security_identity`, `corporate_disclosures`, `business_reality`, `financial_reality`, `capital_structure`, and `trust_governance_events`. Only `market_price` remains unadmitted.
- The 2026-10-09 18:09:28 meeting-resolution fact is preserved in the source ledger but omitted from the B2 manifest because its known-at time is after the original date-only cutoff. The pre-cutoff official 2026-09-11 announcement no. 2026-042 supplies the corporate-disclosure group without cutoff reinterpretation.
- Secondary market-price candidates were not admitted because source authority/reuse conditions were unresolved. Numeric quote values are withheld from this public repository. The later official HTTPS candidate passes only in an ephemeral B2/PIT run.
- Historical result for that earlier run: `BLOCKED`; `evidence_admission=false`, `pit_admission=false`. The later official HTTPS candidate passed ephemerally; no formal 605016 valuation/Decision Revision/report/complete Run Receipt is authorized until private persistence and production Host gates pass.

- P0 Batch B3 / PR #276 is merged: the formal Decision Revision, Machine Publication and Investor Review Report write gates now re-open and validate content-addressed semantic, Forecast and Valuation admission payloads and their stage bindings. Missing upstream bytes are required to fail closed as `BLOCKED` before formal output files or Run Envelope mutation.
- Exact validated PR head `f31f029b8027b19f4a8ff74fede7fdae8977f516`: P0 entry/write regression, B2-E E2E, Investment Core CI, trusted runtime factory, investor report, B04/B04-B, and independent authority/red-team workflows passed. This is control-plane regression evidence only.
- P0-LLM-001 / P0-LLM-004 remain OPEN: no production host-origin run has yet proved source-admitted 605016 Evidence/PIT, authentic semantic/Forecast/Valuation lineage, report/publication, complete Run Receipt replay and independent review in the deployed runtime.

### P0 C1 Follow-up — Official dividend implementation and initial market-price gate — historical status before PR #294

Status at the earlier run: **OFFICIAL DIVIDEND FACT ADMITTED / SIX-OF-SEVEN B2 GROUPS PASS / MARKET PRICE BLOCKED**. Superseded by the later official HTTPS ephemeral B2/PIT run.

- PR #282 merged at `8420d287271c565e61e8501e6168239d6f13bf73`. Adjudication record: `docs/iios/ROUTE_A_C1_605016_FOLLOWUP_ADJUDICATION_20261010.md`.
- Official SSE implementation notice `2026年半年度权益分派实施公告`, announcement no. 2026-043, was captured from the official SSE big5 host. Exact PDF: 146,499 bytes, SHA-256 `1a153c20f908abbd48fdd63a651ecb0edde269f3e7dd0ea27a0b8ce420e5ea8c`. Fact-level record confirms gross cash dividend RMB 0.075/share, record date 2026-09-28, ex-dividend/payment date 2026-09-29, share basis 420,012,320 and total RMB 31,500,924. Reuse class is `RESTRICTED_NO_REDISTRIBUTION`; PDF bytes are not committed to Git.
- Actual combination workflow #38039463649 downloaded the real Attempt 10 source artifact plus this exact official PDF and reran unchanged `research.b2.company_evidence.build_company_evidence_manifest`. It passed six of seven required groups; the only remaining error is `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price` plus the UNKNOWN price record.
- Date-only cutoff remains `2026-10-09`, interpreted by the unchanged core as the start of that date. The 2026-10-09 evening meeting resolution and any secondary same-day close remain excluded because their `known_at` is after the cutoff instant; no same-day close is back-applied. Numerical quote values are withheld from this public repository.
- The first official SSE daily-bar response was retrieved only over plaintext HTTP and remains `BLOCKED_HTTP_TRANSPORT_NOT_ADMISSIBLE`. A later HTTPS/TLS endpoint on port 32042 passed a complete ephemeral B2/PIT candidate run; see `evidence/real_cases/RC-CN-A-605016-20261009/OFFICIAL_HTTPS_B2_ADJUDICATION_20261010.json`. Numeric quote values remain withheld.
- Eastmoney HTTPS responses were used only as non-admitted historical cross-checks. The captured legal statement requires prior written permission to reproduce market quotes; no permission is available, so Eastmoney is excluded from B2 and its numerical quote values are withheld from this public repository. The later official SSE HTTPS candidate passed ephemerally; no source or PIT rule was relaxed.
- Canonical evidence/run records: `evidence/real_cases/RC-CN-A-605016-20261009/DIVIDEND_IMPLEMENTATION_ADJUDICATION_20261010.json`, `PRICE_CUTOFF_SOURCE_ADJUDICATION_20261010.json`, and `FOLLOWUP_B2_RUN_20261010.json`.
- Remaining evidence gate: run `tools/Launch_IIOS_Private_605016_B2_Ingest.command` on the operator Mac. The local tool clones current canonical `main`, reacquires source bytes over HTTPS, and only persists after candidate plus persisted-copy Core-validator replay pass. Expected status is `PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED` or idempotent `ALREADY_PERSISTED_CORE_VALIDATED_NOT_PRODUCTION_ACCEPTED`. Independently review the market-session-close `known_at` basis. Until private persistence passes, no formal valuation, Decision Revision, Publication, investor report or complete Run Receipt is permitted.
- Price-provider reuse review is preserved at `evidence/real_cases/RC-CN-A-605016-20261009/PRICE_PROVIDER_TERMS_ADJUDICATION_20261010.json`. Eastmoney requires prior written exchange permission for market-quote reuse; Yahoo requires express prior permission for automated retrieval; Tencent's terms do not establish an explicit reuse grant for this evidence use. These secondary sources remain excluded; the official HTTPS route has passed ephemerally, but durable admission is still OPEN.
- Production Host/deployment, genuine semantic/Forecast/Valuation and full host-origin Run Receipt replay remain separate OPEN gates. P0-LLM-001 / P0-LLM-004 remain **OPEN**.

### P0 Batch B2 — First-Party Host Implementation — 2026-10-10

Status: **HOST CODE MERGED / DEDICATED CONTRACT PASS / PRODUCTION RUNTIME + DEPLOYMENT ACCEPTANCE OPEN**.

- Discovery record: `docs/iios/P0_BATCH_B2_HOST_DISCOVERY_20261010.md`.
- First-party host record: `docs/iios/P0_BATCH_B2_FIRST_PARTY_HOST_20261010.md`.
- Implementation PR #270 merged at `d8c5b41e13185c365314adacae1449255b8e0eaf`, exact accepted PR head `79a5024ee52a37ff1450c6d56fbd24589cbcefcd`.
- Dedicated host workflow passed **21/21 tests**; the PR exact-head suite had **8/8 checks SUCCESS**, including Investment Core CI, PILOT, authority threat reproduction, post-B04 red-team, FM01/FМ02 and the dedicated host contract. The post-merge Investment Core CI also passed.
- New entrypoint: `python -m iios_mvp.canonical_host_v01`; authenticated `POST /v1/canonical-runs` accepts only a trusted operator-staged `bundle_id`, confines evidence paths to a configured data root, generates server-side run/request IDs, ignores caller-provided semantic claims, and delegates to the canonical CLI with runtime factory configuration sourced only from trusted process environment.
- Security defaults: loopback binding, bearer token of at least 32 characters, no shell for subprocess execution, no stderr disclosure; remote bind requires explicit opt-in and declared TLS termination.
- `/readyz` is deliberately `CONFIGURED_NOT_PRODUCTION_ACCEPTED`. Host CI proves implementation/control-flow boundaries only, not a deployed service, real runtime factory, live semantic response or company decision quality.
- P0-LLM-001 / P0-LLM-004 remain **OPEN** until a configured/deployed host executes a real company run with admitted evidence, authentic semantic/forecast/valuation lineage, report/publication, Run Receipt replay and independent red-team.

### P0 Batch B2 — Trusted runtime factory implementation — 2026-10-10

Status: **FACTORY CODE MERGED / EXACT-HEAD CONTRACT + RED-TEAM PASS / DEPLOYMENT AND REAL-RUNTIME ACCEPTANCE OPEN**.

- PR #274 merged at `a62e2304983cbdf28f0365f7fd55f53378c4adab`; exact validated PR head `14105076b1b69f626907e4eb8bdddf0893d84c23`.
- Exact-head checks: 8/8 success, including the dedicated `factory-contract` workflow, Investment Core CI, PILOT, authority threat reproduction and independent red-team.
- Factory entrypoint: `iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime`; configure only through trusted process/deployment configuration, never request JSON.
- The factory composes the eight validated bindings using the existing live Responses-compatible provider client, strict JSON request/semantic outputs, raw signed provider-response receipt persistence/verification, pinned Ed25519 public-key configuration, and read-only case/cutoff/domain-bound current-price, forecast, upstream-admission and valuation resolvers.
- No factory path writes or fabricates upstream ADMITTED price/forecast/quality/valuation records. Missing/corrupt/mismatched admission records fail closed. A compatible self-hosted provider can use `AUTH_MODE=NONE`; an external provider must use HTTPS. PR #285 narrows the only plaintext exception to same-machine loopback + `SELF_HOSTED` + `AUTH_MODE=NONE`; no provider is called by CI.
- The provider runtime factory contract does not admit the 605016 source capture, deploy the host or create economic evidence. Production acceptance still requires the operator to configure a real provider, provision the signed keypair and durable admission store, deploy the host, then pass an actual real-company Evidence/PIT → semantic/forecast/valuation → report/Run Receipt replay → independent red-team run.
- Free-first local runtime follow-up (PR #285) merged into canonical main at `cf3fb42ebf3f0faedb7a50244ea0edd00fc142ac`; exact PR-head checks **17/17 PASS** and post-merge required checks **6/6 PASS**. It repairs the mismatch between provider policy, trusted factory and independent receipt verifier. Plain HTTP is accepted only for loopback + SELF_HOSTED + AUTH_MODE=NONE; external HTTP, LAN addresses and loopback Bearer auth remain blocked. New signed response records bind authentication/deployment modes, which the independent verifier also checks.
- tools/prepare_iios_local_ollama_runtime.py checks a real loopback Ollama server/version and an explicitly installed model before writing a private mode-0600 host environment file. It does not create company bundles, facts, Evidence/PIT admissions, Forecast/Valuation admissions or Decisions. The Host and Ollama model must run in the same machine/network namespace for this loopback route.
- Non-claim / remaining gate: test-server fixtures and exact-head CI are control-contract evidence only. This change has not demonstrated real local Ollama inference or a deployed host-origin company run. P0-LLM-001/P0-LLM-004 remain OPEN. RC-CN-A-605016-20261009 still has market_price UNKNOWN, evidence_admission=false and pit_admission=false; no formal Decision/report/complete Run Receipt is authorized.
- P0-LLM-001/P0-LLM-004 remain **OPEN**; host/factory CI is not live semantic conformance.

### P0 Batch B2 — Free ChatGPT Web operator runtime — 2026-10-10

Status: **IMPLEMENTATION MERGED / 8-OF-8 PR CHECKS PASS / REAL OPERATOR RUN + FORMAL PROVENANCE-LINEAGE ACCEPTANCE OPEN**.

- PR #296 merged into canonical main at `b7c5b0d4a317990017e88e35220a1279524c0e03`; all 8 exact-head checks passed, and all 3 post-merge required checks passed.
- Runtime selector: `IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.chatgpt_chat_runtime_v01:build_chatgpt_chat_runtime`. It composes the canonical eight runtime bindings and requires neither a local model nor provider endpoint/API key. Every absent model response causes a fail-closed `CHATGPT_CHAT_RESPONSE_REQUIRED:<task_id>` with an immutable prompt file.
- Operator loop: copy the exact prompt into ChatGPT Free web UI, save its raw strict-JSON response, import with `python -m iios_mvp.chatgpt_chat_handoff_v01 import-response`, then rerun the identical canonical CLI command. Request-intent and thesis-semantic are distinct handoff stages; outputs are validated by the existing typed callback contracts.
- Hashes bind prompt and reply to stage/run/request/case/cutoff. Receipt replay checks response integrity, task binding, strict JSON, immutable writes and receipt hashes. `provider_origin_verified=false` is mandatory: hashes prove integrity of saved bytes, not that OpenAI produced them.
- The operator receipt is currently an adjacent audit artifact under the private handoff root, not yet a formal signed-provider receipt embedded into the complete `IIOS_RUN_RECEIPT`. This lineage integration, a real operator-driven run and independent production acceptance remain OPEN. No endpoint authentication or hidden browser/cookie mechanism is used.
- OpenAI documents that ChatGPT and API billing are separate: https://help.openai.com/en/articles/9039756-managing-billing-settings-on-the-chatgpt-web-and-api-platform.
- This route cannot produce market-price facts or upstream admissions. `RC-CN-A-605016-20261009` still has `market_price` UNKNOWN/unadmitted; no formal Decision/report/complete Run Receipt is authorized from a manual callback alone.

### Route A C1 — 605016 canonical-main capture refresh — 2026-10-10

Status: **RAW CAPTURE + INDEPENDENT INTEGRITY PASS / SOURCE-ORIGIN + EVIDENCE/PIT ADMISSION BLOCKED**.

- PR #272 merged at `2978cdbc3f76f1ab1596896e3425c75661144a57`; exact accepted PR head `e8209d5de74a034db11b06574577bc8653759cdd`.
- Canonical-main capture run #38026139364: [workflow](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364), artifact #11660285551 (8,526,921 bytes; temporary Actions retention).
- Exact result: 12/12 source bodies captured; 0 transport failures; 0 unregistered source refs; 12/12 independently recomputed size/SHA checks PASS; 12/12 declared payload types PASS.
- Correct states: `CAPTURED_NOT_ADMITTED`, `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`, and `CAPTURE_COMPLETE_NOT_ADMITTED`.
- Independent verifier states `source_origin_verified=false`; one source has unknown PIT timing. Unchanged B2 preflight is `BLOCKED_NOT_ADMITTED`; all seven required field groups remain uncovered, `evidence_admission=false`, `pit_admission=false`.
- Audit: `docs/iios/ROUTE_A_C1_605016_ATTEMPT10_ADJUDICATION_20261010.md`; full attempt ledger: `evidence/real_cases/RC-CN-A-605016-20261009/ROUTE_A_CAPTURE_ATTEMPTS_20261010.md`.
- Non-claim: 12 verified byte objects do not equal 12 true facts; the result does not permit valuation, Decision Revision, publication/report or `IIOS_RUN_RECEIPT`.

### P0 Canonical Entry Incident — Batch 0

Status: **INCIDENT REPRODUCTION PASS / CANONICAL RECORD — PRODUCTION P0s OPEN**

- Original regression request: `使用新版本iios分析百龙创园 605016，产能增长型B端成长股，截止2026-10-09`.
- Cutoff: `2026-10-09`.
- Batch 0 exact-head workflow #4 / Run ID `37940734602`: SUCCESS.
- Characterization tests: 6 / 6 PASS; compileall and diff-check PASS.
- The tests reproduce canonical-entry, unadmitted-evidence, missing-semantic-artifact and run-receipt/write-binding bypasses.
- This result proves the defect can be reproduced; it does not close P0-LLM-001 or P0-LLM-004, admit any company evidence, or establish investment-decision conformance.
- Historical successor completed: Batch 1 (PR #260) introduced canonical-run and stage-scoped write authorization and replaced characterization-only assertions with fail-closed regressions. The later PR #264 follow-up hardens host-registered and factory-loaded runtime bindings. Production-host integration and real-company evidence/semantic acceptance remain open.

Canonical incident contract: `docs/iios/P0_CANONICAL_ENTRY_INCIDENT_REPRODUCTION_20261009.md`.

- Canonical promotion status: Batch 0 freezes the reproducible defect and acceptance contract only. Successor code batches #260 and #264 have closed the tested CLI-entry/write-authorization and runtime-binding enforcement gaps; the remaining P0 is production acceptance (actual host wiring, real-company Evidence/PIT + semantic/Forecast/Valuation lineage, full receipt replay and independent red-team). Do not mark P0-LLM-001/P0-LLM-004 closed from synthetic/control-plane CI alone.


### P0 Canonical Entry and Write Authorization — Batch 1

Status: **MERGED / CODE + REGRESSION ACCEPTANCE PASS / PRODUCTION CONFORMANCE OPEN**

- Canonical promotion: PR #260 merged; merge commit `c14ef1b66da6f564da5f48178c5efd2728d69698`.
- Source branch was refreshed from the post-Route-A canonical main at `ad1c71ad97f7c19746cae68b863aac81524f142e`, not the stale pre-promotion base from earlier PR #257.
- Implemented: explicit `canonical-run` entry via a registered runtime; legacy `run` no longer writes a formal decision; persisted Run Envelope and stage receipts; request/Case/admission binding; exact-byte B2 Evidence/PIT manifest checks; stage-scoped Decision Revision, Machine Publication and report authorization; complete versioned `IIOS_RUN_RECEIPT` binding and replay validation; fail-closed bypass probes and synthetic positive control-plane E2E.
- Final PR-head `cf7be75651d7bbb830385e0c8aabab89fd27e417`: **34/34 triggered workflows SUCCESS**, including Investment Core CI, State Hygiene, CORE-00 scope isolation, P0 canonical-entry regression, B00-B authority threat reproduction, B2-E, B2-F independent red-team and report/lifecycle/monitoring regressions. This establishes the tested code/control-plane boundary; it does not prove the deployed host or live LLM economic reasoning. Post-merge run set also had 20+ workflow checks already successful, with remaining reruns tracked separately from the pre-merge exact-head acceptance.
- Strict non-claims: the actual product host is not yet proven to be wired to the registered runtime; the real 605016 case remains blocked until official-source Evidence/PIT admission and authorized semantic/Forecast/Valuation inputs pass; no capital or order execution is authorized.

```text
public / operator evidence intake (no Provider API key)
  ↓
explicit canonical-run entry / registered runtime
  ↓
persisted Run Envelope + monotonic stage receipts
  ↓
actual B2 exact-byte/PIT admission + authorized semantic/forecast/valuation artifacts
  ↓
Decision Admission + revision + immutable publication + report
  ↓
replay-validated IIOS_RUN_RECEIPT
```

Next acceptance gate is **runtime integration and real-case evidence**, not adding Provider endpoint/key requirements to Route A: (1) wire the actual user-facing host to call `canonical-run`; (2) register an approved request interpreter, semantic producer, and canonical resolvers in that host; (3) admit the source-vintage/license/PIT-verified 605016 evidence and authorized Forecast/Valuation chain; and (4) run production-backed natural-language-to-canonical conformance. The runtime registry is intentionally empty by default, so `canonical-run` returns `BLOCKED / CANONICAL_RUNTIME_NOT_REGISTERED` until an approved composition is supplied. P0-LLM-001/P0-LLM-004 remain OPEN until this is proven; no default fallback is allowed.


### P0 Follow-up — Runtime Composition Hook + Bounded Source Capture — 2026-10-09

Status: **MERGED / EXACT-HEAD CI PASS / PRODUCTION RUNTIME ACCEPTANCE OPEN**

- Canonical promotion: PR #262 merged; merge commit `9b017919f95b2a4e6f30c20656c58bd354f7c133`.
- Exact validated PR head: `aa42e56eab7c7968c65bc6f84df0dcb6c13cc645`; all **24 / 24** triggered workflows passed with zero failures.
- P0 canonical-entry regression and trusted-factory tests passed. The factory selector comes only from trusted CLI/environment configuration or host pre-registration, never request JSON; absent/invalid factory fails closed and raw factory exception text is not echoed.
- PILOT-02 source capture is bounded with `--connect-timeout 8 --max-time 25 --retry 1` for each of its three public-source calls and a four-minute step timeout. The final-head PILOT-03 scope guard explicitly allows the new timeout contract test and passed. A failed fetch stays a failed fetch; capture diagnostics are preserved.
- The E2E still correctly reports `BLOCKED_NOT_ADMITTED` when the seven-group B2 Evidence/PIT manifest is absent; no formal Decision Revision or report is written by the capture-only pilot.

Non-claims:
- This PR provides a trusted runtime-factory handoff, but does not ship or register a production runtime factory.
- The real host must still bind a request interpreter, genuine semantic producer, exact-byte B2 Evidence/PIT intake, date-correct current-price resolver, independent forecast, upstream-authority and valuation resolvers.
- P0-LLM-001 / P0-LLM-004 remain **OPEN** until the actual user-facing host is wired, a genuine company run completes Evidence/PIT → Decision Revision → Publication → report → Run Receipt replay, and production-backed semantic conformance is independently accepted.

F-001 through F-005 have been remediated and independently re-audited. The fresh B2-F audit passed against the FR5-fix head on 2026-10-09 and is preserved as a canonical, rerunnable source/contract audit. This closes the B2-F red-team finding set; it does **not** prove production provider invocation or model/economic validity.

**B2-D LIVE provider integration = OPTIONAL / BLOCKED (NOT AN MVP GATE).** No provider runtime configuration or `LIVE_RESPONSE_CAPTURED + INDEPENDENT_VERIFIED` evidence has been supplied; that matters only if the optional external-LLM integration itself is being accepted.


### P0 Follow-up — Runtime Binding Validation — 2026-10-10

Status: **MERGED / EXACT-HEAD CI PASS / PRODUCTION RUNTIME ACCEPTANCE OPEN**

- Canonical promotion: PR #264 merged; merge commit `e50018ffa5d8eec5909b98340ed74fe56c178344`.
- Exact validated PR head: `32de0b1a47188e45ea38339bfdc6013b631e0672`; all **16 / 16 triggered workflows passed** with zero failures.
- Dedicated P0 entry regression: **12 / 12 tests passed**; `compileall` and `git diff --check` passed.
- Runtime validation is now shared by `register_canonical_runtime`, `get_canonical_runtime`, the trusted host pre-registration path and the trusted `--runtime-factory` path.
- The validator requires all eight bindings, callable request-interpreter / semantic-producer methods, correctly typed allow-list registries, active registrations and exact type/version/policy binding. It also checks the four canonical resolver interfaces before the run can enter the canonical pipeline.
- Incomplete pre-registered runtime and placeholder resolver tests fail closed before formal artifacts can be written.

Non-claims:
- This closes a configuration-validation inconsistency; it does **not** register a production host runtime or prove a genuine LLM callback.
- Test doubles are only control-plane tests. They do not admit company Evidence/PIT, forecast or valuation artifacts and do not prove economic decision quality.
- P0-LLM-001 / P0-LLM-004 remain **OPEN** until the actual user-facing host is identified and wired, the seven-group 605016 evidence chain is admitted, and a production-backed canonical run passes report/receipt replay and independent red-team.

Next development batch remains **Batch B — actual host composition and runtime-registration proof**. The registry deliberately remains empty by default; no new default runtime or fallback was introduced.


### P0 Batch 1 — Repository CLI Host Integration — 2026-10-10

Status: **MERGED / CONTROL-PLANE INTEGRATION PASS / PRODUCTION HOST ACCEPTANCE OPEN**

- Canonical promotion: PR #267 merged; merge commit `b26e3e071eec7e145c46d4bef8a6f206439be1c2`.
- Exact validated PR head: `cd44c503ed2535bede25ad4a5e2f483cfb606ef4`.
- Dedicated P0 workflow: **13 / 13 tests passed**, including the new host-level CLI integration; module compile and diff check passed. The additional triggered FM01 exact-source workflow also passed.
- The integration test invokes the real `iios_mvp.cli.main()` dispatcher with `canonical-run`, a fresh run ID and a trusted test-only factory. It verifies a persisted Run Envelope and ordered stage receipts through `HUMAN_APPROVAL_PENDING`, with `human_approval_required=true` and `auto_execution=false`.
- It expressly asserts that the CLI run does not itself publish a report or create a complete Run Receipt. The semantic producer and evidence rows are deterministic `TEST_ONLY` fixtures.

Non-claims:
- This proves repository-resident CLI control-plane routing/persistence only.
- Repository inspection did not find a separate deployable web/server/front-end entry point; no external product-host integration was demonstrated.
- No production factory or live semantic/model callback was installed. Real 605016 Evidence/PIT admission remains a separate critical path.
- P0-LLM-001 / P0-LLM-004 remain **OPEN** until the real host is identified and wired, genuine runtime identity is independently verified, and a real-company run passes evidence/semantic/forecast/valuation admission, publication/report/receipt replay and independent red-team.

Next boundary at that checkpoint: **Batch B2 — production host identification and trusted runtime registration**. Do not call Batch B fully complete because Batch B1 is merged.

### P0 Batch B3 — Persisted Upstream Admission + Formal Write Authorization — 2026-10-10

Status: **MERGED / EXACT-HEAD CONTROL-PLANE REGRESSION PASS / PRODUCTION P0 OPEN**.

- Acceptance record: `docs/iios/P0_BATCH_B3_PERSISTED_UPSTREAM_WRITE_AUTHORIZATION_20261010.md`.
- PR #276: [P0 persisted upstream write authorization](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/276).
- Merge commit: `d3582621918b285f29b4573c2618c1072247885c`; validated pre-merge exact head: `f31f029b8027b19f4a8ff74fede7fdae8977f516`.
- The canonical run now retains exact content-addressed Semantic Artifact, Producer Receipt/Admission, Forecast Admission, Valuation Admission/Output and a bound upstream-admission bundle before `DECISION_ADMITTED` is persisted.
- Formal Decision Revision, Publication and Report authorization re-open and validate upstream artifact bytes, hashes, schema/identity, lineage and stage receipt bindings. A resolver that cannot return the exact admitted Valuation record cannot downgrade to reference-ID-only authorization.
- Negative compliance regression `test_p0_ce_07_formal_writers_block_when_upstream_admission_bytes_are_missing` deletes semantic, valuation-output or forecast-admission bytes at the corresponding writer boundary and checks that the request is blocked and the Run Envelope remains byte-identical; no formal output, report or complete Run Receipt is emitted on blocked paths.
- Exact-head checks passed for P0 canonical-entry incident reproduction, B2-E natural-language E2E, Investment Core CI, trusted runtime factory, investor report, B04 and B04-B lineage, B00-B authority reproduction, B2-F fresh independent red-team and post-B04 independent red-team.
- Scope limitation: the regressions use synthetic TEST_ONLY lifecycle records to test authorization mechanics. They do not admit 605016 company evidence, prove source-origin/PIT, deploy the HTTP host, prove live semantic reasoning or establish investment-decision quality. P0-LLM-001 / P0-LLM-004 remain OPEN.

### Retained B2-D integration history (optional, non-blocking)

B2-D canonical refresh is now merged in PR #215 (merge `b32c9203b5a7baf729cdff2090bb4e54237a177c`) from the post-State-Hygiene canonical main. The old pre-hygiene PR #212 is closed and is not an admissible development base.

B2-D1 independent live-evidence verification hardening is now merged in PR #217 (merge `0b0b9cb9db86b86dc3ffefef42dc624bffa11ca9`). The hardening gate was verified on the B2-D workflow run #7:
- B2-D tests: 11 / 11 PASS;
- independent clean-room red-team: 15 / 15 PASS;
- B2-D1 independent verifier tests: 7 / 7 PASS;
- compileall, schema validation and diff-check: PASS.

B2-D2 provider-neutral runtime boundary is now merged in PR #219 (merge `7997a107ab18687d7c81f731ec7e0b3fae09ed9a`). Exact-head B2-D workflow run #17 = SUCCESS:
- existing B2-D tests: 11 / 11 PASS;
- existing B2-D clean-room red-team: 15 / 15 PASS;
- B2-D1 independent verifier tests: PASS;
- B2-D2 provider runtime tests: PASS;
- B2-D2 independent clean-room red-team: PASS;
- compileall, schema validation and git diff-check: PASS.
The live job remained a non-authoritative success record with no production credentials; no `LIVE_RESPONSE_CAPTURED` evidence was admitted.

Therefore:
- fixture output MUST NOT be labeled as live-provider evidence;
- B2-D live MUST NOT be marked complete merely because static/preflight CI is green;
- B2-D1 and B2-D2 are complete;
- production provider configuration and live LLM invocation are only required to validate the optional B2-D external-provider adapter; they are not required for the free-first company research MVP.

### Current next development batch

**Current execution plan:** `docs/iios/IIOS_BATCH_EXECUTION_PLAN_20261010.md` remains governing. C1/605016 local persistence, read-only replay and bounded source-vintage successor are complete. C2/新和成 (002001.SZ) now has an exact-byte, page-located, ephemeral Core-validated successor; overall B2 is still BLOCKED only on `market_price` (observation date 2026-10-08), with independent source/vintage review still pending. **Next C2 gates:** independently review the 13 field-level claims, conservative publication-date `known_at` bounds and private internal-use-only handling; then admit a price source only if its origin, 2026-10-08 observation, cutoff-safe `known_at` and private-use permission are demonstrable. Public-web search on 2026-10-11 found no source satisfying all gates: the official SZSE historical UI was located but its data-use boundary was unresolved and the exact response was not captured; CNINFO advertises a quote/API/data-mall platform but did not prove a free retention-permitted path; Investing.com expressly requires prior written permission for data use/storage/copying; Yahoo's automated collection path is not authorized; Sohu/Eastmoney remain excluded. Machine review: `evidence/real_cases/RC-CN-A-002001-20261009/C2_MARKET_PRICE_SOURCE_REVIEW_20261011.json`. Next action is operator-supplied original price evidence from a source permitted for personal/internal research, kept private and subject to source/PIT review. If none is provided or passes, retain `market_price=UNKNOWN`. Primary 605016 production Host/semantic/Forecast/Valuation acceptance remains a separate open path. Do not publish numeric quote values or raw market data. P0-LLM-001/P0-LLM-004 remain OPEN.

The primary Investment Core MVP path is **Route A — free-first single-company evidence intake + public web discovery**. No LLM provider endpoint or API key is required for this Route A path. Public-web discovery, public-source capture, B2 preflight and artifact retention all run without an external LLM endpoint, paid search API or API key. Operator-supplied raw originals and manually supplied evidence remain supported when public URLs are unavailable or source bytes need to be supplied directly. B2-D remains an optional external-LLM integration adapter and is not an MVP gate.

**C2 Run #8 artifact recheck — 2026-10-11:** the preserved archive SHA-256 `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1` matched, and all eight captured raw files passed receipt size/hash replay. The ninth declared Eastmoney K-line source has no bytes. This is raw-integrity PASS only; evidence admission remains NOT_ADMITTED.

**Cutoff defect:** Run #8's B2 manifest and report used `2026-10-09T23:59:59+08:00`, which conflicts with the IIOS date-only cutoff rule for `2026-10-09` (interpreted at the start of that date). The historic manifest must stay diagnostic; do not edit the timestamp and reuse its digest/fingerprint. The 2026-10-09 buyback-progress filing and any same-day close remain excluded unless independent pre-cutoff availability is established.

**C2 next action (operator policy):** PR [#338](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/338) and synthetic full-path PR [#340](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/340) are PASS / MERGED / CANONICAL. The actual private C2 run has now passed the unchanged Core/PIT validator ephemerally for all seven required groups, using `OPERATOR_ATTESTED_MARKET_DATA`; Run #8's eight captured raw objects and 13 PDF locators were reverified. No further web search/audit was done. This is not source-vintage verification, a formal signed admission, production Host acceptance, or a canonical Decision. The numeric value, private manifest and result bundle remain local-only. See audit sections 10–11 and machine record `evidence/real_cases/RC-CN-A-002001-20261009/C2_MARKET_PRICE_SOURCE_REVIEW_20261011.json`.

C2-P3 PR [#345](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/345) is PASS / MERGED / CANONICAL for the separate-method review. Its exact-head workflow [#38126026797](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38126026797) independently re-extracted 13/13 page-located claim term sets from the verified Run #8 source members, checked official HTTPS SZSE bindings and conservative cutoff-safe `known_at` upper bounds, and excluded the 2026-10-09 same-day buyback-progress notice. The sanitized detailed CI result is archived at `evidence/real_cases/RC-CN-A-002001-20261009/C2_P3_FACT_REVIEW_CI_RESULT_38126026797.json`. This is not external third-party sign-off or a legal opinion. Every reviewed source still declares `PUBLIC_ACCESS_REUSE_UNKNOWN`, so formal C2 remains `NOT_ADMITTED` until a separate reviewer resolves the 13 claims and permitted private fact-level retention/use boundary, and signed Evidence/PIT admission plus production Host acceptance pass. Continue the 605016 production Host critical path in parallel. The C2 plan does not weaken cutoff or PIT requirements.

B2-D3 real LLM provider invocation → B2-D1 independent verification → production-backed B2-E remains a separately tracked optional integration path. It does not block Route A acquisition, manual original intake, fact-level review, or free-first MVP development.

B2-E fixture-backed conformance is not admitted as live-provider evidence.

### Explicit non-blockers

A02 / CSI800 historical-universe evidence and the M1.2 Research Track remain **outside the company-level MVP critical path**.

The M1.2 current epoch remains closed by FM07/FM05 governance; no same-epoch model/threshold redesign is authorized.

## Route A — Free-First Company Evidence Intake — 2026-10-09

Status: **PASS / MERGED / CANONICAL — RAW-INTAKE INFRASTRUCTURE ONLY**

Canonical promotion:
- PR #238;
- merge commit: `33ee2263683d346f7c6aec34a049b0bcd25e7dba`;
- validated source PR head: `9c19dba98b40073ccc53f677cd464c2f2797ecd6`.

Implementation:
- `tools/company_evidence_intake.py` supports public/free HTTPS URLs and operator-supplied original files;
- raw bytes are retained per run beside a byte-for-byte manifest copy;
- receipt records size, SHA-256, retrieval time, source identity/class claims, license/reuse declaration, publication/known-at basis, observation date and effective interval;
- `tools/verify_company_evidence_intake.py` independently recomputes manifest and raw-byte hashes, checks source metadata is bound to the manifest, rejects path traversal/unreferenced bytes and refuses forged admission;
- absent/unverifiable known_at remains UNKNOWN; future known_at is PIT-blocked; pre-cutoff known_at remains only a candidate for evidence-level review;
- no paid data subscription, provider API key or LLM runtime is needed for raw intake.

Exact PR validation on head `9c19dba98b40073ccc53f677cd464c2f2797ecd6`:
- Route A dedicated CI run #2 / `37916871337`: PASS;
- State Hygiene #25 / `37916871262`: PASS;
- B2-F independent red-team #6 / `37916871355`: PASS;
- Investment Core CI #1029 / `37916871376`: PASS;
- B1 Canonical Research Orchestrator #34 / `37916871290`: PASS;
- B2 Semantic Producer Admission #45 / `37916871235`: PASS;
- CORE-00 Scope Reconciliation #428 / `37916871397`: PASS;
- FM01 Exact CATL Source Admission #217 / `37916871388`: PASS;
- C0 Governance Hygiene #166 / `37916871346`: PASS.

Authority boundary:
- capture/byte integrity PASS does not mean source authenticity PASS, PIT admission PASS, completeness PASS or a real-company case admission;
- all capture outputs remain `NOT_ADMITTED` until the existing independent B2 Evidence/PIT gate accepts the source facts;
- no real company raw bundle was produced by the fixture-based PR CI; first real raw capture and later partial capture are separately documented in `docs/iios/ROUTE_A_CAPTURE_RC_CN_A_002001_20261009_RUN2.md` and `docs/iios/ROUTE_A_CAPTURE_RC_CN_A_002001_20261009_RUN8.md`;
- A02 / CSI800 / CSI Industry remains a separate Research Track, out of this path.

# Route A First Real Capture — 新和成 (002001.SZ)

**Record class:** DIAGNOSTIC / raw-source capture + independent byte-integrity result  
**Case ID:** `RC-CN-A-002001-20261009`  
**Cutoff:** `2026-10-09`  
**Run:** [GitHub Actions #2 / 37918304170](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/37918304170)  
**Run branch commit:** `ef0d99ffe664340e29be7f30c577a1662593a87d`  
**Run completed:** `2026-10-09T10:33:23Z` (UTC)  
**Artifact:** `iios-company-evidence-37918304170`, ID `11610237261`  
**Artifact ZIP SHA-256:** `71600859888d65d7bcdd67591f1029791910be744fe7e17dadedfcff804006d3`  
**Artifact size:** `1,367,116` bytes  
**GitHub retention expiry:** `2026-10-23T10:33:23Z` (UTC; 14 days)  
**Manifest SHA-256:** `2e2fb0648460d646daaca3f749f8971352b8e8895d442b580609e357794ceed2`

## Run result

- Capture receipt status: `CAPTURED_NOT_ADMITTED`.
- Source count: 5; successful captures: 5; failed captures: 0.
- Independent verifier: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`.
- Recomputed raw-byte hashes: 5/5; manifest SHA-256 binding: PASS.
- Unknown PIT sources: 1; future-known sources: 0.
- `evidence_admission = false`; `source_origin_verified = false`; `live_llm_required = false`.
- The first failed run #1 (ID `37918027867`) failed in request-path resolution before source network access and produced no source artifact. The resolver was fixed in PR #241, and run #2 used the merged fix.

## Captured objects

| Source ID | Byte size | SHA-256 | Capture / PIT status |
|---|---:|---|---|
| `ISSUER-IR-PAGE-CURRENT` | 21,953 | `18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c` | HTTP 200 / `UNKNOWN_NO_KNOWN_AT` |
| `SZSE-2026-H1-FULL` | 980,820 | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-H1-SUMMARY` | 144,809 | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-Q1-FULL` | 221,878 | `facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-BUYBACK-PLAN` | 142,384 | `e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |

The four PDFs' opening pages were checked as a document-identity sanity check: they identify 浙江新和成股份有限公司 / 证券代码 002001 and the expected H1, Q1 or 2026-027 repurchase documents. This is not a full report review and does not authenticate the source URL's full publication timeline by itself.

## Source locators

- Issuer IR page: https://www.cnhu.com/investor/zh-cn
- 2026 H1 full report: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/83165436-1015-4d77-919c-97c8cce0c67d.PDF
- 2026 H1 summary: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/6d1ad0be-5e22-482b-a163-2ebb0b6d1d95.PDF
- 2026 Q1 report: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-29/094c9e5d-f2de-4411-b604-b2aece32f35b.PDF
- 2026 repurchase plan: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-24/53248225-c2cf-45cf-a0fd-a6c9fee4f267.PDF

All records currently declare `license_status = PUBLIC_ACCESS_REUSE_UNKNOWN`. The report-date values are claims supported by path/indexing and should be checked against the existing B2 Evidence/PIT rules. They are not self-admitting provenance.

## Gaps and next action

- No market-price bytes are present.
- No separately captured operating/business-reality source beyond the reports yet.
- No separately captured capital-structure/source-master snapshot yet.
- The issuer IR landing page is current-content and has no defensible first-public date in the manifest, so it remains UNKNOWN.
- The next gate is the existing B2 Evidence/PIT admission for these objects, then add the missing company-level source groups. Neither the raw capture nor this record authorizes company-level investment conclusions.

# Route A Partial Capture Run #8 — 新和成 (002001.SZ)

**Record class:** DIAGNOSTIC / real public-source acquisition + independent raw-byte integrity; not Evidence/PIT admission  
**Case ID:** `RC-CN-A-002001-20261009`  
**Cutoff:** `2026-10-09`  
**Canonical source after code fix:** `067d28176da981245c84cdcd88b67a5f456991b8` (PR #252)  
**Run:** [GitHub Actions #8 / 37938129274](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/37938129274)  
**Capture request commit:** `b3f7486b0216d1bd88ad84332a31583ab311727b`  
**Completed:** `2026-10-09T13:37:27Z` (UTC)  
**Artifact:** `iios-company-evidence-37938129274`, ID `11620425220`  
**Artifact size:** `1,474,787` bytes  
**Artifact ZIP SHA-256:** `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`  
**Artifact expires:** `2026-10-23T13:37:26Z` (UTC; 14 days)  
**Exact manifest SHA-256:** `c6ec425f3c2ef5404bbdd1868e57434c64da90e255bcde5eae24586dba1227e3`

## Result

- Workflow conclusion: `SUCCESS` under the new **partial-capture** gate.
- Receipt: `PARTIAL_CAPTURE_NOT_ADMITTED`; 9 sources declared, 8 captured and 1 failed.
- Independent verifier: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`; 8/8 captured raw byte objects verified against receipt hashes.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; B2 manifest `BLOCKED`.
- `admitted_field_groups=[]`; all seven B2-required field groups remain uncovered for fact-level admission.
- `evidence_admission=false`; `pit_admission=false`; `source_origin_verified=false`; `llm_provider_required=false`.
- The job is green because it correctly preserved and checked the **partial** artifact, not because every candidate URL succeeded or evidence was admitted.

## Captured objects

| Source ID | Bytes | SHA-256 | Capture/PIT state |
|---|---:|---|---|
| `ISSUER-IR-PAGE-CURRENT` | 21,953 | `18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `SZSE-2026-H1-FULL` | 980,820 | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | SUCCESS / PIT candidate |
| `SZSE-2026-H1-SUMMARY` | 144,809 | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | SUCCESS / PIT candidate |
| `SZSE-2026-Q1-FULL` | 221,878 | `facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa` | SUCCESS / PIT candidate |
| `SZSE-2026-BUYBACK-PLAN` | 142,384 | `e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9` | SUCCESS / PIT candidate |
| `SZSE-2026-BUYBACK-PROGRESS-SEP` | 84,057 | `af6ad44d49b10b0f23306e0812fa64200880b29883bcaa71fecaf6b54a8ac6ed` | SUCCESS / PIT candidate |
| `PRICE-SOHU-HISTORY` | 21,829 | `0f05a4c643ef19de9d313c4231ab200386b6946920c066fb104d23ebb683efd3` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `PRICE-EASTMONEY-QUOTE` | 56,928 | `97bf733ac8f7d1fd14bb3377fd85041940b4ef225349bdc07710f9c22a827cfa` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `PRICE-EASTMONEY-KLINE-API` | — | — | FAILED / `SOURCE_FETCH_FAILED`; no bytes retained |

The active manifest no longer includes the previously flaky duplicate Sohu `app2/history.up` endpoint. Eastmoney's K-line API succeeded in an earlier run and failed on Run #8, showing that this runner-to-public-endpoint path is intermittent. This failure remains explicit; it is not changed to UNKNOWN success, and no hash is asserted for a source with no bytes.

## Existing B2 preflight result

The preflight generated artifact-level source records from the eight successfully captured files. Those records are explicitly `provenance_class=UNKNOWN` and `status=UNKNOWN`; therefore the existing B2 validator rejects them for PIT/field-group coverage. This is expected and correct: a file containing a report or a market page has not yet been mapped into admitted facts.

Next action after PR #259 fact extraction: independently adjudicate the three cited PDFs’ source identity, first-public timestamp and license/reuse; then construct B2 Evidence Records only for facts whose source/PIT basis passes. The 11 candidates are locator-verified but remain UNKNOWN/NOT_ADMITTED. Resolve the market-price gap separately; the failed K-line source remains failed and no close is inferred from captured quote pages.

## B2-D3 — Real Provider Runtime + Live Evidence Gate — 2026-10-08

Status: **IMPLEMENTATION PASS / LIVE EVIDENCE BLOCKED**

Canonical promotion:
- PR #221;
- canonical implementation merge: `52f3afb6925ec34dd2982c52908416e2e2fa302d`;
- source canonical base: `2906fb71715d51971e7dab0146bdbef8da9e45c9`.

Implementation boundary closed:
- strict, manual-only real-provider workflow;
- production runtime configuration is injected only through GitHub Secrets / Variables;
- existing B2-D2 provider-neutral runtime policy remains authoritative;
- real HTTP invocation path is implemented;
- raw response bytes are retained in the live evidence artifact;
- request/response SHA-256, replay hash and IIOS Ed25519 attestation are captured;
- B2-D1 independent verifier is invoked as a separate verification process;
- non-secret run manifest records the evidence file hash and verification hashes;
- live execution is not connected to Semantic, Forecast, Valuation, Decision, Human Approval or execution authority.

Verification:
- B2-D workflow run #21 = SUCCESS;
- B2-D tests and existing clean-room red-team = PASS;
- B2-D1 independent verifier tests = PASS;
- B2-D2 runtime tests / independent red-team = PASS;
- B2-D3 workflow contract tests = PASS;
- compile, schema validation and diff-check = PASS.

Live gate:
- B2-D3 production workflow was deliberately made `workflow_dispatch` only;
- no provider credentials were admitted in the repository runtime at this stage;
- therefore no authoritative `LIVE_RESPONSE_CAPTURED` evidence was produced;
- the existing B2-D live job correctly remained `BLOCKED_OR_FAILED` under fail-closed configuration absence and must not be counted as live PASS.

Next gate:

```
Configure production provider runtime
        ↓
Manually dispatch B2-D3 real-provider workflow
        ↓
LIVE_RESPONSE_CAPTURED
        ↓
B2-D1 INDEPENDENT_VERIFIED
        ↓
B2-E Natural-Language → Semantic → Decision E2E
```

Explicit non-claims:
- B2-D3 implementation PASS does not prove a real provider response;
- B2-D3 does not promote fixture output to live evidence;
- B2-D3 does not make any commercial LLM provider an architectural dependency;
- B2-E remains locked until a real live evidence artifact passes independent verification.

## B2-E — Natural-Language → Semantic → Decision E2E — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Canonical promotion:
- PR #223;
- merge commit: `bb297c212f3deb153549cab013000904ebd982dd`;
- canonical base before batch: `999bf17080f0ac73736d8a44d98a7202c1dad147`.

Closed control-plane boundary:
- B2-B natural-language request admission is the canonical entry;
- admitted Research Case identity is bound to the expanded Investment Core case by case_id / market / symbol / cutoff / as_of identity;
- admitted Evidence is required before semantic production;
- B2-A semantic admission precedes downstream Forecast / Valuation / Decision stages;
- semantic producer output is explicitly forbidden from writing Decision-authoritative fields;
- canonical v0.3 Decision Kernel is re-executed at Decision Admission;
- Decision Admission is bound to the resulting canonical Decision snapshot;
- lifecycle output is `AI_PROPOSED`;
- `human_approval_required=true`;
- `auto_execution=false`;
- E2E binding receipt ties raw request, Research Case, expanded Investment Core case, semantic artifact/admission, Decision Admission and Decision Revision.

Verification:
- dedicated B2-E workflow run #3 = SUCCESS;
- B2-E E2E tests: 3 / 3 PASS;
- independent B2-E red-team: 4 / 4 PASS;
- B2 Semantic Producer workflow #27 = SUCCESS, including B2-E E2E + red-team;
- Investment Core CI #999 = SUCCESS;
- MVP Pilot #137 = SUCCESS;
- Post-B04 independent red-team #126 = SUCCESS;
- B2 Data Evidence PIT #94 = SUCCESS.

Evidence classification:
- this batch uses fixture request interpreter / semantic producer and the existing canonical 300750 case/resolvers;
- therefore B2-E is a **control-plane and authority-conformance PASS**, not production LLM economic-reasoning validation.

Production gate remains:
```text
B2-D3 LIVE_RESPONSE_CAPTURED
        ↓
B2-D1 INDEPENDENT_VERIFIED
        ↓
production request interpreter / semantic producer
        ↓
B2-E production-backed execution
```

Explicit non-claims:
- B2-E does not claim model quality or economic forecast validity;
- semantic producer cannot directly authorize a Decision;
- no Human Approval was issued by B2-E;
- no automatic execution capability was added;
- B2-D3 LIVE remains BLOCKED until real production runtime evidence is captured and independently verified.

## B2-F — Full Independent Red-team — 2026-10-08

Status: **BLOCKED / FINDINGS REPRODUCED**

Audit branch: redteam/b2f-full-independent-20261008

Audit mode:
- independent clean-room source/AST and contract inspection;
- targeted authority / lineage attacks;
- no product-code remediation performed on the red-team branch.

Findings:
- **F-001 P0:** semantic artifact has no causal edge into canonical economic Decision input;
- **F-002 P1:** Forecast / Valuation stage admission is not independently validator-backed;
- **F-003 P1:** nested semantic Decision-authority fields can evade the top-level guard;
- **F-004 P1:** Decision Series identity depends on a caller-supplied series ID and does not structurally carry market / symbol / company.

Disposition:
B2-F BLOCKED
→ repair F-001
→ repair F-002
→ repair F-003
→ repair F-004
→ rerun independent B2-F
→ B2-F PASS / FAIL

Important distinction:
- B2-E remains PASS / CANONICAL as a control-plane conformance implementation;
- B2-F demonstrates that B2-E does not yet prove a causal production Semantic → Economic Decision chain;
- B2-D3 live-provider capture remains independently blocked and is not changed by the red-team result;
- MVP Final Human Acceptance remains locked.

## B2-FR1 — Semantic → Economic Canonical Transformation — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

- PR #227;
- merge commit: `88f21977f58057943af287ce2df3f356535c689a`;
- F-001 closed.

Closed boundary:
- admitted THESIS_ASSESSMENT requires an exact typed `core_projection`;
- semantic input evidence lineage is the source of projected thesis evidence_ids;
- projected Thesis is admitted by the existing Thesis Admission contract;
- canonical upstream admission is rebuilt with the projected Thesis state;
- B2-E Decision Kernel consumes the projected Core case;
- binding receipt records semantic core projection hash;
- semantic reasoning creation time is separated from PIT-bounded Thesis knowledge date.

Verification:
- B2-E E2E workflow: PASS;
- Investment Core CI: PASS;
- MVP Pilot: PASS;
- B2 semantic admission + clean-room: PASS;
- B00-B / Post-B04 red-teams: PASS.

F-001 is no longer an active blocker.

## B2-FR2 — Forecast / Valuation Admission Binding — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

- PR #228;
- merge commit: `b7f48b742f4ab4ddb60942365cdc24df160ab3c2`;
- F-002 closed.

Closed boundary:
- B2-E validates canonical Forecast / Valuation lineage before stage admission;
- existing `validate_forecast_valuation_return_lineage` is reused as the canonical validator;
- Forecast / Valuation stage receipts carry canonical admission hashes;
- Decision Pending carries the same canonical Forecast / Valuation lineage;
- tampered Return Gate scenario values are rejected before Decision.

Verification:
- B2-E E2E workflow: PASS;
- Investment Core CI: PASS;
- MVP Pilot: PASS;
- B2 semantic admission + clean-room: PASS;
- B00-B / Post-B04 red-teams: PASS.

F-002 is no longer an active blocker.

## B2-FR3 — Recursive Semantic Authority-Field Guard — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

- PR #231;
- merge commit: `fcb4253c71d415f5d56c539611763d228ea5241e`;
- F-003 closed.

Closed boundary:
- semantic Decision-authority fields are now checked recursively throughout the entire semantic artifact `output`, including nested mappings and list/tuple elements;
- the guard reports the offending nested path and rejects the artifact before semantic output can influence downstream canonical Decision processing;
- the existing top-level guard behavior remains covered.

Verification on FR3 head `77e892c16c98f364d684171b4bafcafb90fd4bb8`:
- B2-E E2E: PASS;
- B2 Semantic Producer Admission: PASS;
- Investment Core CI: PASS;
- MVP Pilot: PASS;
- B00-B Authority Threat Reproduction: PASS;
- Post-B04 Independent Red-team: PASS.

F-003 is no longer an active blocker.

## B2-FR4 — Decision Series Identity Hardening — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

- PR #232;
- merge commit: `7efe3fc227941429d3aac015d03d197af7b4254c`;
- F-004 closed.

Closed boundary:
- canonical `decision_series_id` is deterministically derived from snapshot `market + symbol`;
- a caller-supplied series ID is accepted only when it exactly matches that canonical identity;
- every Decision Revision now carries structured `case_id / market / symbol / company` series identity plus an integrity hash;
- canonical v0.3 Decision Revisions bind that identity to the canonical Decision Admission;
- B2-E no longer supplies a caller-defined series ID;
- Decision ID is structurally bound to the canonical series ID and revision number.

Regression repair:
- three legacy C6 lifecycle fixtures were updated to the new v0.2 revision contract;
- the resulting C6/C7/C8 lifecycle regressions were rerun and passed.

Verification on FR4 final head `dfbd533f3b9e14deeb7e6ad6fc5ede0a9a39d90c`:
- B2-E E2E: PASS;
- B2 Semantic Producer Admission: PASS;
- Investment Core CI: PASS;
- MVP Pilot: PASS;
- C6 Human Execution Receipt: PASS;
- C7 Full Lifecycle E2E: PASS;
- C8 Auth Remediation: PASS;
- DR-01 Decision Lifecycle Contract: PASS;
- DR-02 Persistence / CLI: PASS;
- B00-B Authority Threat Reproduction: parallel validation remained clean where completed; no FR4-specific failure remained;
- Post-B04 Independent Red-team: PASS.

F-004 is no longer an active blocker.

## B2-FR5 — D3 Workflow YAML / Trigger-Boundary Remediation — 2026-10-09

Status: **PASS / MERGED / CANONICAL**

Canonical promotions:
- PR #234 initially added an event guard on every provider-secret-bearing D3 job; merge commit `026a74461f81db2d653815a9912667163f8d54ee`.
- Root-cause follow-up PR #236 corrected the invalid D3 workflow YAML and added parser-based contract coverage; merge commit `8c112f1e343cf4c70e2ac159e98b42d95e56fbb2`.
- F-005 closed.

Root cause:
- The preflight step used an inline `run: python - <<'PY'` while its Python body was unindented outside the YAML scalar.
- Two later heredoc bodies also escaped their `run: |` scalar by being flush-left.
- GitHub did not parse the declared workflow name/trigger/jobs and instead recorded phantom failed `event=push` runs whose workflow name was the file path and whose job list was empty.

Closed boundary:
- all Python heredocs now reside inside valid YAML block scalars;
- the D3 contract tests parse the workflow with PyYAML BaseLoader and assert the custom workflow name, the exact single trigger `workflow_dispatch`, and the required job structure;
- every provider-secret-bearing job has an explicit `if: github.event_name == 'workflow_dispatch'` guard as defense in depth;
- PyYAML parsing is part of both the dedicated D3 contract CI and the fresh B2-F independent audit;
- no credentials were added, and this repair did not create live-provider evidence.

Exact-head verification:
- B2-D Live Provider workflow Run #23 / run id `37870351002` = SUCCESS; D3 workflow contract tests, existing B2-D tests, B2-D1 verifier tests, B2-D2 runtime/red-team, schemas, compile and diff-check all passed.
- Fresh B2-F Independent Red-team workflow Run #2 / run id `37870351055` = SUCCESS on head `a32b8b1b8461a7aa760190b4a53967da13bb80da`; the FR1–FR5 independent source/contract audit, targeted runtime regression tests, compileall and diff-check passed.
- On the previously malformed head `857f379128561cb894fba8ae3b48003d13635fd3`, GitHub recorded D3 path-named push failures with zero jobs. No D3 workflow run was observed for the corrected YAML head at the final run-history check.

Evidence boundary:
- F-005 is closed as a workflow syntax/trigger-boundary finding.
- B2-D LIVE remains **BLOCKED** because no authorized provider runtime configuration or independently verified real response has been admitted.
- A successful static or fail-closed smoke workflow is not live-provider evidence.

## B2-F Fresh Independent Red-team — FR1–FR5 — 2026-10-09

Status: **PASS / CANONICAL**

- Audit PR #235; merge commit `857f379128561cb894fba8ae3b48003d13635fd3`.
- Follow-up fresh audit on the D3 YAML correction: workflow Run #2, run id `37870351055`, SUCCESS.
- Independent probes cover:
  - F-001: typed semantic thesis projection is the actual canonical Decision input;
  - F-002: Forecast / Valuation transitions require canonical return-lineage validation;
  - F-003: semantic authority guard recursively checks mappings and sequences;
  - F-004: Decision Series identity is derived and bound to the Decision Admission;
  - F-005: D3 is valid YAML, workflow_dispatch-only, and all provider-secret-bearing jobs carry the explicit event guard.
- Relevant B2-E, Decision Lifecycle, and D3 workflow contract tests passed; compileall and diff-check passed.
- This is a code/contract authority pass only. It does not authorize capital, issue Human Approval, execute orders, or satisfy the live-provider evidence gate.

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

### B2-D — Live Provider Evidence

Status: **CANONICAL REFRESH PASS / LIVE GATE BLOCKED**

- canonical refresh PR: #215; merge commit `b32c9203b5a7baf729cdff2090bb4e54237a177c`;
- stale pre-hygiene PR #212: CLOSED / SUPERSEDED;
- B2-D static + independent red-team: PASS;
- real live-provider invocation evidence: NOT ADMITTED;
- production provider credential/runtime: NOT SUPPLIED;
- production-origin provider receipt with independent replay: NOT SUPPLIED;
- current live smoke artifact: Actions run #6, status `BLOCKED_OR_FAILED` because required runtime configuration was absent.

This is the current LLM/MVP blocker.

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


## 9. Historical MVP / Research boundary record

The original company-level Investment Core and the planned PILOT-00 → PILOT-04 technical lifecycle are completed historical foundations. Their milestone sequence is retained for audit history only.

The **current** development boundary is defined by the CURRENT ACTIVE DEVELOPMENT AUTHORITY section at the top of this file:

```text
B2-D → real provider evidence → B2-E → B2-F → final MVP acceptance
```

The M1.2 Research Track remains separate. A02 / CSI800 evidence is not an Investment Core dependency and must not be reintroduced into the MVP critical path.

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

> **Historical-record notice:** Sections 12–24 preserve immutable milestone records. Any “Immediate sequence”, “Next canonical development boundary”, or similar forward-looking statement inside these historical sections is time-local and is superseded by the **CURRENT ACTIVE DEVELOPMENT AUTHORITY** section above.

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
## 19. MVP Pilot Acceptance — technical gate complete / final MVP P0 remains — 2026-10-08
Status: **TECHNICAL PILOT ACCEPTANCE PASS / FINAL MVP DO NOT CLOSE**

Canonical implementation head after MVP human-report projection correction:
- PR #200 merge commit: `71ff164a19098c58b0d64745ce5f446e568eef7a`;
- canonical `main`: `71ff164a19098c58b0d64745ce5f446e568eef7a` at this state-sync start.

Post-fix technical verification:
- PILOT-02 fresh Xinhecheng run #46: SUCCESS;
- Investment Core CI #848 (pre-merge validation): SUCCESS;
- MVP Pilot CI #17 (pre-merge validation): SUCCESS;
- C2 Human Report #25: SUCCESS;
- C7 lifecycle #50: SUCCESS;
- B00-B authority red-team #90: SUCCESS;
- Post-B04 independent red-team #16: SUCCESS before canonical merge.

Corrected real Xinhecheng report evidence:
- report hash: `5a6a3e8136cd589d64a5008d0c70cfb88a1047051234a33a8013f34ae5b8a9c5`;
- publication hash: `7e9bc390c03e12ac3309754cdb65938aa928d9dea97a4145998e3ab9911a0ea0`;
- report QA hash: `a168cf332802cef5de0e9ff5c845dc9e6bb007ffce9f47a34cea5dd8468494ec`;
- report QA: `PASS`, including human_readability / decision_fidelity / binding / deterministic replay.

Observed report-projection defect was fixed:
- canonical Forecast / Valuation states now render correctly;
- new-capital permission now renders as `NO`;
- positioning/sizing permission now renders as `NO_SIZING_PERMISSION`;
- return/risk threshold `26.60` is exposed separately from actionable entry authorization;
- entry-zone arrays are rendered as human text rather than JSON.

Human usability remains a real operator gate. A review worksheet has been generated from the corrected report and must be completed by the operator; CI cannot substitute for this attestation.

### P0 governance override on final MVP closure

B0 LLM canonical-execution governance freeze and B1-LCE now supersede the earlier pilot-only interpretation of MVP closure.

P0-LLM-004 explicitly states that PILOT-01~04 primarily validate deterministic lifecycle behavior from preconstructed semantic inputs and **do not prove natural-language request → LLM reasoning → semantic admission → canonical decision**.

Therefore:

```text
PILOT technical gate = PASS
Human report review gate = APPROVED by owner/operator attestation on 2026-10-08
Final MVP v0.1.1 DoD = BLOCKED by P0-LLM-004
```

The next canonical development gate is therefore:

```text
B2 — LLM Semantic Workbench + Semantic Producer Admission
```

B2 must close the real semantic producer boundary and then add a natural-language-to-canonical conformance test before the final MVP gate can be closed.

A02 / CSI800 remains non-blocking and must not be reintroduced into the MVP critical path.


## 20. Dual Report Surface — Human Review + Machine Archive — 2026-10-08

Status: PASS / MERGED / CANONICAL

Decision:
- split the report layer into two separate outputs derived from the exact same canonical Machine Publication;
- human-facing surface = IIOS-INVESTOR-REVIEW-0.1, Chinese, detailed, intended for actual investor/operator usability review;
- machine/archive surface = existing IIOS-HUMAN-REPORT-0.1 output, retained as compact structured/English summary for CI, deterministic replay and archival lookup.

Authority boundary:
- both surfaces are one-way projections only;
- neither surface may create evidence, recalculate economics, mutate the Decision, or authorize execution;
- the new investor review report has exact publication/decision binding, deterministic rendering, immutable hash and its own QA record.

New implementation:
- iios_mvp/investor_review_report.py;
- schemas/investor_review_report_v0.1.schema.json;
- tests/test_investor_review_report.py;
- CLI command: iios-mvp investor-report <publication> --generated-at <timestamp>;
- design record: docs/iios/IIOS_DUAL_REPORT_SURFACE_20261008.md.

Acceptance rule:
- the Human Usability Gate must be performed against the Chinese Investor Review Report, not the compact machine/archive summary;
- accepting report usability does not equal approving a trade;
- final MVP remains blocked by B0 P0-LLM-004 / B2 natural-language-to-canonical conformance requirements.


## 21. Investor Review Report v0.2 — Human Acceptance + Canonical Promotion — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #204;
- merge commit: `aa0e298f5e7da4f793996a5a2bcf17d60a90ee34`;
- exact implementation head before merge: `41a3d114c8234250b0a8e8bfddaa32e7cad507ff`.

Technical gate:
- exact-head CI Run #80 / run id `37739468730` = SUCCESS;
- v0.2 targeted tests = 26 / 26 PASS;
- second-round independent clean-room red-team = 23 / 23 PASS;
- schemas, render, Human Auditability P0 assertions and diff-check = PASS;
- accepted real Xinhecheng Publication SHA-256:
  `7e9bc390c03e12ac3309754cdb65938aa928d9dea97a4145998e3ab9911a0ea0`;
- v0.2 human report hash:
  `b5ab777d1389d20f2b6f1d03e8d15324bb03fbe58fe299c0f5ee5f7b68672bce`;
- v0.2 machine report hash:
  `9764641a2274769a168155c99a93c6e4e1923f5c78d8da0589126fa762ee4c72`;
- v0.2 QA hash:
  `fefcdd47f83fe8c6a8b81eec7ae39cddc9cab8d6e364142fa0d6e2b118145b4d`;
- CI artifact id `11533186204`, digest:
  `sha256:5eeb573228f20cb5a68ecb3df67d7dba1cb58bcc8040d1c4842a26e36769147c`.

Human governance gate:
- owner/operator independently reviewed the real Xinhecheng Chinese Investor Review Report;
- Human Acceptance = **APPROVED** on 2026-10-08;
- acceptance is for the report projection only, not for investment capital or trade execution;
- known non-blocking usability observations are retained: some monitoring/validation fields are structurally dense, and expected annualized return uses high-precision decimal formatting;
- the underlying Xinhecheng case remains explicitly incomplete in Required Return, scenario probabilities, actionable entry admission and MIE/Expectation Gap, and these gaps remain fail-closed.

Authority:
- v0.2 is a projection-only report surface and cannot become a second Decision Source;
- canonical Decision, Risk/Portfolio precedence and Human Approval remain unchanged;
- B0 P0-LLM-004 remains unresolved by this report milestone: the pilot/report chain does not prove Natural Language → LLM Semantic Reasoning → Semantic Admission → Canonical Decision.

Next canonical development boundary:

```text
B2 — LLM Semantic Workbench + Semantic Producer Admission
```

B2 must establish the real typed semantic producer boundary, producer authenticity/provenance, deterministic semantic admission, and a natural-language-to-canonical conformance test before the final MVP DoD can close.

A02 / CSI800 remains non-blocking to company-level Investment Core MVP and must not be reintroduced into the critical path.

## 22. B2-A — LLM Semantic Workbench + Semantic Producer Admission — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #206;
- exact accepted implementation head: `7be863f19800810528784361b38b61c820e9c81d`;
- merge commit: `ae5b6dd6d7cd606f8aadd0100eb2beedb0bef5df`.

Technical evidence:
- B2 Semantic Producer Admission workflow Run #8: **SUCCESS**;
- B2 admission tests: **12 / 12 PASS**;
- independent clean-room B2 red-team: **15 / 15 PASS**;
- compileall: PASS;
- semantic producer receipt schema validation: PASS;
- git diff --check: PASS;
- additional repository regression workflows triggered on the exact head remained green where completed.

Closed boundary:
- typed semantic artifact allow-list;
- active producer registry binding producer_id / producer_type / producer_version / policy_version;
- producer receipt with semantic provenance;
- deterministic artifact / receipt / output hash binding;
- exact case / market / symbol / company / cutoff identity binding;
- semantic input references and hashes must originate from the current run's admitted Evidence receipt;
- Workbench requires canonical `SEMANTIC_PENDING`;
- Workbench request must exactly match the canonical run identity;
- successful admission advances only `SEMANTIC_PENDING → SEMANTIC_ADMITTED`.

Non-claims:
- B2-A does **not** prove a live external LLM connection;
- B2-A does **not** prove Natural Language → real LLM → semantic admission → canonical Decision;
- B2-A does not alter economic formulas, Decision precedence, Risk/Portfolio semantics, Human Approval, or automatic execution.

Governance:
- owner/operator approved B2-A for merge after the dedicated CI and independent red-team gate;
- B2-A is now canonical infrastructure, not an economic judgment engine.

Next canonical development boundary:

```text
B2-B — Natural-Language Semantic Conformance + Independent Red Team
```

## 23. B2-B — Natural-Language Semantic Conformance — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #208;
- exact accepted implementation head: `941926c7fe8762933cb90d6c21d6d1b446487c1f`;
- merge commit: `6eeccea9069d3262ca8a7484e4fa1461f9f2797e`.

Technical evidence:
- B2-B Natural Language Conformance workflow Run #2: **SUCCESS**;
- conformance tests: **7 / 7 PASS**;
- independent clean-room red-team: **15 / 15 PASS**;
- compileall: PASS;
- request-admission schema validation: PASS;
- git diff --check: PASS.

Closed boundary:
- raw natural-language request is hashed before interpretation;
- normalized request intent receives an independent canonical hash;
- request interpreter identity / type / version / policy is registry-bound;
- only INVESTMENT_DECISION requests enter this canonical path;
- existing Research Case v0.1 construction and validation remain the deterministic case boundary;
- request admission receipt binds request_id / run_id / case_id / case_hash / interpreter provenance;
- REQUEST_ADMITTED must precede CASE_CREATED;
- conformance can progress through Evidence → SEMANTIC_PENDING → B2-A Semantic Admission.
Non-claims:
- B2-B does **not** prove live external LLM/provider conformance;
- fixture interpreter and fixture semantic producer are test doubles;
- B2-B does **not** prove economic decision quality;
- no Decision, capital permission, Human Approval, or execution authority is granted.

Governance:
- owner/operator approved B2-B for merge after dedicated CI and independent red-team;
- B2-B is canonical entry infrastructure.

Next canonical development boundary:

```text
B2-C — Live Semantic Producer Binding + Natural-Language-to-Semantic-to-Decision Conformance
```

B2-C must introduce an authorized real semantic producer boundary or an explicitly signed external-provider receipt path. It must demonstrate end-to-end lineage from natural-language request through semantic admission and into Decision Admission without allowing the LLM to grant permission authority.

## 24. B2-C — Signed External Semantic Provider Binding — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Scope:
- PR #210;
- exact accepted implementation head: `1eaaae6f0859bf3283a65ff0c700c5da6392b4d0`;
- merge commit: `883ca6ee9be0c5982d7f9b2ef1e0d70c564a39f8`.

Technical evidence:
- B2-C Signed External Semantic Provider workflow Run #3: **SUCCESS**;
- signed-provider conformance tests: **7 / 7 PASS**;
- independent clean-room red-team: **15 / 15 PASS**;
- compileall: PASS;
- external signed-provider receipt schema validation: PASS;
- git diff --check: PASS.

Closed boundary:
- trusted Ed25519 external-provider public-key registry;
- exact producer_id / producer_type / producer_version / policy_version binding;
- raw natural-language request SHA-256 binding;
- exact request_id / run_id / case_id / cutoff binding;
- exact semantic input references and hashes binding;
- semantic artifact hash binding;
- attestation integrity hash and Ed25519 signature verification;
- reuse of B2-A deterministic semantic admission;
- successful path advances only `SEMANTIC_PENDING → SEMANTIC_ADMITTED`.

Governance:
- owner/operator approved B2-C for merge after dedicated CI and independent clean-room red-team;
- B2-C is canonical semantic-provider authentication infrastructure;
- no Decision, capital permission, Human Approval, publication or execution authority is introduced.

Explicit non-claim:
- B2-C uses a deterministic fixture signing key in repository conformance tests;
- B2-C does **not** prove a live production LLM/provider connection;
- B2-C does **not** prove provider model quality or economic decision validity.

Next canonical development boundary:

```text
B2-D — Real Provider Adapter / Live Model Invocation + Independent Provider Replay
```

B2-D is now the only remaining B2 blocker on the LLM side. It must either:
1. connect an actually authorized live provider through a real runtime connector, or
2. admit a production-origin provider artifact/receipt whose provenance can be independently replayed.

No fixture-only result may be promoted as live-provider evidence.

## 25. B2-D — Canonical Refresh + Real Provider Boundary — 2026-10-08

Status: **CANONICAL INFRASTRUCTURE PASS / LIVE EVIDENCE BLOCKED**

Canonical promotion:
- PR #215;
- source canonical main: `e1ad65a08be1beed626b21d4955107f29ad96098`;
- canonical refresh implementation head: `72d8bc3cf68e22c5dbffb4bc101af5277639f697`;
- merge commit: `b32c9203b5a7baf729cdff2090bb4e54237a177c`;
- stale PR #212: closed / superseded.

Closed engineering boundary:
- fail-closed live-provider runtime configuration;
- concrete `OPENAI_RESPONSES` request mapping;
- HTTPS-only transport;
- raw request/response bytes and SHA-256 capture;
- replay record bound to provider, model, run, case, request and cutoff;
- IIOS-side Ed25519 runtime attestation with independent verification;
- no semantic admission / Forecast / Valuation / Decision / Human Approval / publication / execution authority.

Dedicated B2-D validation:
- workflow `IIOS B2-D Live Provider`, run #6;
- static tests: 11 / 11 PASS;
- independent clean-room red-team: 15 / 15 PASS;
- compileall: PASS;
- schema validation: PASS;
- git diff --check: PASS.

Live-provider gate result:
- the Actions runtime exposed blank values for all seven required provider configuration variables;
- therefore no real provider HTTP invocation occurred;
- uploaded artifact id: 11537940345;
- artifact status: `BLOCKED_OR_FAILED`;
- `LIVE_RESPONSE_CAPTURED` evidence: NOT ADMITTED.

The live job is intentionally non-authoritative and must not be counted as a live PASS. The next gate is real production runtime configuration, followed by live invocation, independent replay/attestation verification, and only then B2-E consumption.

No fixture-only result may satisfy this gate.

## B2-D2 — Provider-Neutral Runtime Boundary — 2026-10-08

Status: **PASS / MERGED / CANONICAL**

Canonical promotion:
- PR #219;
- canonical base: `9b0a147ba86e7f7d2645b800cc95281e8082b55f`;
- accepted implementation head: `d5bffeff8afcde0b4b0be9114cfd9d9cab1bdfbf`;
- merge commit: `7997a107ab18687d7c81f731ec7e0b3fae09ed9a`.

Closed runtime boundary:
- `OPENAI_RESPONSES` remains the protocol contract, not a commercial-provider identity;
- provider identity/version remain separate from deployment mode and authentication mode;
- `auth_mode=BEARER` requires an API key;
- `auth_mode=NONE` emits no Authorization header and requires no API credential;
- `deployment_mode=SELF_HOSTED` is supported;
- non-HTTPS is permitted only for explicitly self-hosted loopback endpoints;
- non-loopback endpoints remain HTTPS-only;
- live invocation authentication is delegated to the provider-neutral runtime policy;
- no new semantic, Forecast, Valuation, Decision, Human Approval or execution authority is introduced.

Dedicated verification:
- B2-D workflow run #17 = SUCCESS;
- existing B2-D tests: 11 / 11 PASS;
- existing B2-D clean-room red-team: 15 / 15 PASS;
- B2-D1 independent verifier tests: PASS;
- B2-D2 provider runtime tests: PASS;
- B2-D2 independent clean-room red-team: PASS;
- compileall, provider-runtime schema validation and git diff-check: PASS.

Live status remains:
`BLOCKED` because the production provider runtime credentials/configuration are absent. This does not invalidate B2-D2; it confirms that runtime neutrality is implemented before credential admission.

Explicit non-claims:
- B2-D2 does not prove a real provider response;
- no commercial provider is a mandatory architectural dependency;
- no self-hosted provider has been connected or trusted yet;
- B2-E remains locked until a real `LIVE_RESPONSE_CAPTURED` evidence artifact passes independent verification.

### Latest 605016 private B2 ingest contract failure — 2026-10-11

- **Operator result after PR #320:** the official HTTPS stage returned `overall=PASS_EPHEMERAL_B2`, `candidate_manifest_status=PASS`, seven admitted field groups, no missing groups, and the expected official SSE raw-byte SHA-256. The private launcher then returned `BLOCKED / EPHEMERAL_B2_MANIFEST_STATUS_NOT_PASS`; `private_store_written=false`. No signed admission, production Host acceptance, bundle, or decision was created.
- **Root cause:** the adjudicator built a second, final manifest in memory after adding the official 2026-10-08 price record, but did not materialize it to the exact workspace path consumed by the private ingester. That path still contained the earlier pre-price combined manifest. The fail-closed rejection was correct; the producer/consumer handoff was inconsistent.
- **Additional adjacent contract defect found before rerun:** the public-safe report encoded the actual transport method (`PYTHON_HTTPS` / `CURL_HTTPS`) in `official_price_source.transport`, while the local preflight requires the explicit normalized TLS verification marker `HTTPS_TLS_VERIFIED`. The correction records the verified transport status separately from `transport_method`; HTTPS/TLS, official-host, exact-size/hash and one-row/date requirements are not relaxed.
- **PR #321** (https://github.com/kebofeierdawei5-cloud/convergence-research/pull/321) materializes the exact final PASS manifest within the temporary adjudication workspace and adds an integration regression test that proves both final-manifest persistence and compatibility with the private ingester's price-record preflight. The full manifest and raw bytes remain excluded from public artifacts.
- **Current status (post-merge):** PR #321 is **PASS / MERGED / CANONICAL** at merge commit `1c7fa7faf0e6c05aedcc1afb8e2a5cb9323590d2`; all **14/14 exact-head checks passed**, including the private-persistence contract, official HTTPS price-source verification, Investment Core CI, State Hygiene and independent red-team. The fix is now in canonical `main`; the remaining step is the operator’s local launcher rerun. Local private persistence is still **UNVERIFIED / PENDING** until that rerun returns `PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED` or the verified idempotent status. The original source-vintage review caveat remains open.

### Latest 605016 private B2 persistence blocker — shared raw source paths — 2026-10-11

- **Operator result after PR #321/#322:** the official HTTPS adjudicator reported `PASS_EPHEMERAL_B2`, all seven required field groups were present, and the price-byte SHA-256 matched. The private ingester then returned `BLOCKED / RAW_ARTIFACT_PATH_DUPLICATED`; `private_store_written=false`. No formal signed admission, production Host acceptance, bundle or decision was created.
- **Root cause:** the IIOS company-evidence manifest is evidence-centric and declares one raw-artifact binding per evidence record. Several fact records can validly be extracted from the same original official PDF/HTML response, so distinct evidence IDs can intentionally reference the same relative path and same exact byte size/hash. The private copy/verify layer incorrectly treated any repeated path as a duplicate-path attack rather than distinguishing a consistent shared-source reference from conflicting byte contracts.
- **Fix design:** allow a shared path only when every declaration has the same expected size and SHA-256; re-verify every evidence declaration against the raw source; copy the shared source bytes once; and have offline persisted-copy verification apply the same path-contract rule. Conflicting contracts remain fail-closed before private writes. The unchanged Core/PIT validator still validates every evidence ID/declaration and all byte hashes.
- **Follow-up PR #323:** [Allow multiple evidence records to share one verified raw source](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/323) is **PASS / MERGED / CANONICAL**, merge commit `bb6392f2d57b3412b104ace084077e0c4dcd0103`; all **13/13 exact-head checks passed**, including private persistence + offline replay, real Core-validator shared-path fixture, conflicting-contract blocking, static checks and independent red-team. The final design validates every declaration separately, writes each consistent shared raw path only once, and rejects inconsistent size/hash contracts before staging. No raw source bytes or numeric quote values were added to GitHub.
- **Latest operator result (2026-10-11 after PR #323/#324): LOCAL PRIVATE PERSISTENCE PASS.** The operator launcher returned `PERSISTED_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`; `overall=PASS_EPHEMERAL_B2`; the candidate contained 11 evidence records and reported 11 raw-artifact declarations; the Core validator passed. Candidate fingerprint: `c6b78f0185e27ddb089af723f1811ec00185775ca3dbbd679a933a887c566350`. Private manifest SHA-256: `034a4b5de2693d725422d9fb740ba4d5364a63b6b080531ee15a9b1bfff1a7da`. The numeric quotation and local filesystem path are intentionally not recorded here. No raw source bytes were uploaded.
- **Acceptance boundaries remain unchanged:** exact first-public timestamp is unverified and `source_vintage_review_required=true`; no formal signed admission, production Host acceptance, bundle, or decision exists. The next storage-integrity confirmation is the read-only `--verify-existing` replay against the already-persisted candidate; do not rerun ingest merely to validate storage.
- **Deep-audit hardening PR #325:** [Harden 605016 persistence to preflight all raw bytes before write](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/325) is **PASS / MERGED / CANONICAL**, merge commit `819a4080992a09e02e01a169a1c5be2951667976`; all **13/13 exact-head checks passed**, including the private-persistence contract, Investment Core CI and independent red-team. The final copy boundary now validates every path/size/hash contract, rejects symlinked path components, checks the complete set of bytes before creating the raw-output directory, then writes only the captured verified byte sequences. Sanitized results now distinguish manifest declaration count from unique physical raw-file count; the persisted receipt schema is unchanged.
- **Current action:** the operator-reported local persistence result closes the ingest/write blocker. Do not rerun ingest. Run one read-only `--verify-existing` replay to independently verify the already-persisted copy after atomic promotion. Exact first-public timestamp and production Host acceptance remain separate gates.


## 605016 read-only verification ModuleNotFoundError — 2026-10-11

- **Operator result:** `--verify-existing` returned `BLOCKED / UNEXPECTED_PRIVATE_INGEST_FAILURE`, `error_type=ModuleNotFoundError`; output confirms `private_store_written=false` and all authority-creating outputs remained false.
- **Root cause in code:** the Core validator import relied on a prior ingest-only side effect that inserts the repository root into `sys.path` while importing the HTTPS adjudicator. The read-only verifier intentionally skips adjudication, so the default `iios_mvp.canonical_evidence_admission_v01` import could fail before candidate validation.
- **Correction in review:** explicitly bootstrap the effective repository root in shared `_validate_core()`; propagate the caller-supplied root into persist-time validation and offline replay. Add a regression test with an isolated temporary Core package and no inherited module cache/path.
- **Safety boundary:** this is an import-path correction only. Do not rerun ingestion or download Attempt 10. The only operator follow-up after merge is one read-only replay against the existing private candidate.
- **Not yet closed:** local replay has not passed; first-public timestamp remains unverified, and production Host acceptance, signed admission and decision creation remain false.


## 605016 read-only private-copy replay — PASS — 2026-10-11

- **Operator-confirmed replay outcome:** `VERIFIED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`.
- Existing candidate count: 1; evidence records: 11; manifest raw-artifact declarations: 11; unique physical raw files: 8. The legacy `raw_artifact_count` is declaration count, not physical-file count.
- Candidate fingerprint: `c6b78f0185e27ddb089af723f1811ec00185775ca3dbbd679a933a887c566350`.
- Private manifest SHA-256: `034a4b5de2693d725422d9fb740ba4d5364a63b6b080531ee15a9b1bfff1a7da`.
- Core/PIT validator: PASS. `official_source_refetched=false`; the operator ran the read-only verifier after PR #327, with no new Attempt 10 or market-source retrieval.
- **PR #327** (https://github.com/kebofeierdawei5-cloud/convergence-research/pull/327) fixed the shared Core validator's import environment and added an isolated-import regression test; merged as `5ed399259a9e4b33e5687074739336eb1ba202c9`. Exact-head private B2 contract tests: 48/48 PASS; State Hygiene and independent red-team PASS; all 11 associated workflows succeeded.
- **Resolved:** the local read-only-verification `ModuleNotFoundError` incident and persisted-copy replay gate.
- **Still blocked / not admitted:** `exact_first_public_timestamp_verified=false`, `source_vintage_review_required=true`; no formal signed admission, production Host acceptance, request bundle, or decision. Human approval remains required; automatic execution remains false.
- **Next canonical boundary:** resolve the price-evidence source-vintage policy using official/reproducible evidence. Do not rerun ingest or storage verification just to revisit this closed gate. Do not promote a candidate into a decision until the source-vintage gate is explicitly adjudicated under the governing PIT contract.


## C1 — 605016 Bounded Source-Vintage / PIT Adjudication — 2026-10-11

Status: **PASS / MERGED / CANONICAL / LOCAL SUCCESSOR MIGRATION REPORTED PASS**

- PR [#329](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/329) is merged. Its final PR HEAD passed the private persistence contract (53/53), B2 data Evidence/PIT tests (31/31), company Evidence/PIT tests (23/23), B2 scope (3/3), State Hygiene, C0 Governance, Investment Core and independent B2-F red-team, plus the remaining triggered checks.
- Operator-reported successor result: `SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`. Fingerprint `9a4a1f2e22c982e12f09fc7858eba2ee06768cac59659734ab35ea450579bd3c`; manifest SHA-256 `90b1b4b77b28a0e8df36fb7737c7ade5a7ede85948246bcde0439cfc7bd1f72a`; adjudication SHA-256 `e06240acec667926aaa453a7558f76d9f1763488fe5630f5916b180157c75535`. There are 11 evidence records, 11 raw declarations and 8 unique physical raw files. Core/PIT validator PASS; the original candidate remains unchanged; no official source was refetched.
- The new `known_at` uses the conservative upper bound `2026-10-08T15:30:00+08:00`, derived from official SSE trading rules. It is not the exact historical endpoint upload time. `exact_first_public_timestamp_verified=false` remains explicit, as does the fact that rule-page bytes were not materialized and hashed in this run.
- Formal signed admission, production Host acceptance, request bundle, Decision, publication and execution authority remain open.
- **Immediate next evidence batch:** C2 / `RC-CN-A-002001-20261009`. The Run #8 source archive is preserved and independently verified, but its B2 manifest used an end-of-day cutoff timestamp incompatible with the canonical date-only cutoff rule. Keep it diagnostic/BLOCKED; rebuild a successor with the original raw bytes and correct date-only semantics. See `docs/iios/ROUTE_A_C2_SOURCE_ADJUDICATION_AUDIT_20261011.md`.
- Primary 605016 production Host acceptance remains a separate open critical path and must not be marked complete merely because its local source-vintage candidate passes.

