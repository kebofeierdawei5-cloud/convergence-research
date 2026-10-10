# IIOS Project State Index

State classification: **CANONICAL**
Snapshot: 2026-10-10
Authority: this file is the **only canonical Current State Index**.

## CURRENT ACTIVE DEVELOPMENT AUTHORITY — 2026-10-10

**Current canonical main:** Git ref `main` (resolve the SHA from Git; do not duplicate a fixed SHA in this document).

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
```

### Current blocker

**The company-level Investment Core MVP does NOT require an external LLM provider endpoint, paid search API, or API key.** The provider-specific live-evidence gate is an optional integration track, not a blocker to research execution.

Current MVP acceptance gaps:
- source-by-source B2 Evidence/PIT admission of the five actual 新和成 (002001.SZ) source objects;
- public-web discovery for missing official/free sources, followed by raw-byte capture and independent hash verification;
- coverage gaps for `market_price`, `business_reality`, and `capital_structure`;
- sufficient admitted evidence before company-level analysis, valuation or decision.

The current independent B2-F audit remains PASS / CANONICAL.

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

**Current execution plan:** `docs/iios/IIOS_BATCH_EXECUTION_PLAN_20261010.md`; current main baseline before this Route A evidence-intake branch was `7ba1adcf99532b2de10bc7f405b66b4affd4647d`. Batch A and PR #264 runtime-binding hardening are complete (PR #262: 24/24; PR #264: 16/16 exact-head workflows PASS). The active work combines **Batch B — actual host composition/runtime-registration proof** with **Batch C1 — 605016 source-vintage and B2/PIT admission**. The actual host integration remains unproven. Route A / 新和成 (002001.SZ) fact-source adjudication proceeds in parallel. No paid provider key is required for free-first acquisition.

The primary Investment Core MVP path is **Route A — free-first single-company evidence intake + public web discovery**. No LLM provider endpoint or API key is required for this Route A path. Public-web discovery, public-source capture, B2 preflight and artifact retention all run without an external LLM endpoint, paid search API or API key. Operator-supplied raw originals and manually supplied evidence remain supported when public URLs are unavailable or source bytes need to be supplied directly. B2-D remains an optional external-LLM integration adapter and is not an MVP gate.

### P0 C1 — 605016 / 百龙创园 Free-First Raw Capture — 2026-10-10

Status: **RAW CAPTURE COMPLETE / PAYLOAD CONTRACT MISMATCHES EXPLICIT / EVIDENCE-PIT BLOCKED / NOT ADMITTED**

- Case: `RC-CN-A-605016-20261009`, cutoff `2026-10-09`; manifest `manifests/company_cases/RC-CN-A-605016-20261009.json` (12 free-first candidates across seven required groups).
- The full eight-attempt history, including failed Investing URLs and code-level failures, is preserved in `evidence/real_cases/RC-CN-A-605016-20261009/ROUTE_A_CAPTURE_ATTEMPTS_20261010.md`.
- Attempts 1–3 exposed Investing access failure and unregistered source refs; attempt 3 captured 12 HTTP response bodies but retrospective inspection showed 8 of 9 PDF-declared SSE URLs were HTML challenge pages.
- Payload-type validation, independent replay, B2 candidate exclusion and bounded HTTP reads have now been implemented. Attempts 4–7 exposed and fixed the lowercase PDF magic bug, slow sequential capture risk, and two clock-module naming collisions; every failure is retained in the attempt ledger.
- **Attempt 8 / run `38016339121`: SUCCESS in ~36 seconds.** 12/12 raw response bodies captured, 0 failed rows, 0 unregistered refs, 12/12 SHA/size verification; expected-payload contract = **8 mismatches / 4 passes**. Artifact `11656422240`.
- B2 preflight remains `BLOCKED_NOT_ADMITTED`; `b2_candidate_source_count=4`; eight PDF-declared responses were excluded as HTML challenges; all seven required field groups remain uncovered for decision-grade admission; `evidence_admission=false`, `pit_admission=false`.
- The correct status is `RAW_CAPTURE_COMPLETE_WITH_PAYLOAD_MISMATCHES_NOT_ADMITTED`, not “12 valid documents.” Raw response integrity is not issuer-origin verification, known-at/PIT admission, licensing, or fact truth.

Next: replace the challenged direct PDF transport paths with an accessible official-source locator (or preserve operator-supplied issuer-origin originals); then verify document identity and timestamps, independently adjudicate the declared reuse state and extract page/table-located facts. The 2026-10-09 closing price still requires a defensible authoritative market-data observation. No valuation, formal Decision Revision, publication or report is authorized.

**Latest real capture: Run #8 succeeded as `PARTIAL_CAPTURE_VERIFIED_NOT_ADMITTED`.** Eight of nine declared source objects were retained and independently hash-verified; the public Eastmoney K-line endpoint failed on this run. The artifact and failure row were retained instead of discarding the other eight files. The existing B2 preflight executed successfully and correctly returned `BLOCKED_NOT_ADMITTED`.

**Latest Route A advance — PR #259, page-located fact extraction review.** A reproducible extractor now re-verifies raw source SHA-256/size, checks selected text terms against exact PDF page locators, and emitted 11 fact-level candidates from the H1 summary, H1 full report and 2026-09 buyback progress PDF. The review record is `docs/iios/ROUTE_A_FACT_EXTRACTION_REVIEW_20261009.md`; local machine-readable output is `ROUTE_A_FACT_EXTRACTION_REVIEW_20261009.json`.

This advances beyond file-only capture, but does **not** change admission status: every candidate remains `known_at=null`, `provenance_class=UNKNOWN`, `status=UNKNOWN`, `admission_status=NOT_ADMITTED`; `admitted_field_groups=[]`. The report is useful for review and reproducible locator checking only. The extractor's test CI validates contracts, not official source-origin or economic truth.

Next action is **source-level adjudication and B2 Evidence/PIT admission**, not more LLM configuration:
1. Independently verify each cited document's issuer/exchange identity and actual first-public timestamp; only then decide whether the proposed `known_at` can be admitted.
2. Resolve the declared `PUBLIC_ACCESS_REUSE_UNKNOWN` license/reuse state.
3. Convert individually reviewed facts to B2 Evidence Records and run the unchanged B2 validator; UNKNOWN must continue to fail closed.
4. Capture a date-specific official/free market-price observation with defensible PIT/source vintage. Run #8's Eastmoney K-line row failed and has no bytes/hash; Sohu/Eastmoney quote/history page bytes are not admitted closing-price facts.
5. Add any still-missing business-reality/capital-structure/trust facts. Only adequate admitted group coverage permits company-level valuation and decision.

```text
Public web discovery (no key; candidate URLs only)
  ↓
Route A raw capture + independent byte verification
  ↓
page-located fact extraction (11 candidates; text match PASS)
  ↓
source-origin / first-public-time / license adjudication (OPEN)
  ↓
B2 Evidence/PIT admission (currently BLOCKED_NOT_ADMITTED)
  ↓
market-price and remaining field-group gaps
  ↓
only after adequate admitted facts: company analysis / valuation / expectation gap / decision
```

Run #8 details remain in `docs/iios/ROUTE_A_CAPTURE_RC_CN_A_002001_20261009_RUN8.md`. The original Run #8 receipt, capture artifact and failed-source row remain unchanged. No source is promoted from a declared date, public-search snippet, PDF text match or successful download alone.

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
