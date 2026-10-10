# IIOS Batch Execution Plan — Refreshed 2026-10-10

**Plan class:** execution plan / canonical-main recovery  
**Authority baseline:** `main@e50018ffa5d8eec5909b98340ed74fe56c178344`  
**State authority:** `docs/PROJECT_STATE_INDEX.md`  
**Purpose:** move IIOS from validated control-plane code to a real, fail-closed, single-company research run without making external LLM API credentials a Route A prerequisite.

## 1. Refreshed project state

### Canonically complete

| Batch | Promotion | Verified result | What it does not prove |
|---|---|---|---|
| P0 Batch 0 incident reproduction | Merged in earlier history | Canonical-entry, evidence, semantic-artifact and Run Receipt bypasses were reproduced | Production enforcement |
| Route A fact extraction | PR #259 / merge `ad1c71ad97f7c19746cae68b863aac81524f142e` | 11 PDF page-located fact candidates; exact raw bytes are rechecked; offline contract CI passed | Any B2 Evidence/PIT admission |
| P0 Batch 1 write authorization | PR #260 / merge `c14ef1b66da6f564da5f48178c5efd2728d69698` | Explicit `canonical-run`, persisted Run Envelope/stage receipts, stage-scoped write authorization, versioned `IIOS_RUN_RECEIPT`, replay validation | Actual host registration or real model/economic conformance |
| State index sync | PR #261 / merge `0ca9ce1927da8f24e955927fd40847f70653eaf0` | State Hygiene, Investment Core CI, CORE-00 and other exact-head contract checks passed | Real case evidence admission |
| Trusted runtime-factory hook + bounded capture | PR #262 / merge `9b017919f95b2a4e6f30c20656c58bd354f7c133` | Exact validated head `aa42e56eab7c7968c65bc6f84df0dcb6c13cc645`: 24/24 triggered workflows passed; trusted factory selector and bounded free-source capture are tested | Does not register a production runtime or admit evidence |
| P0 runtime-binding validation | PR #264 / merge `e50018ffa5d8eec5909b98340ed74fe56c178344` | Exact validated head `32de0b1a47188e45ea38339bfdc6013b631e0672`: 16/16 triggered workflows passed; dedicated P0 test file 12/12 passed | Does not wire a production host or admit evidence |

P0 Batch 1 exact validated head `cf7be75651d7bbb830385e0c8aabab89fd27e417` passed 34/34 triggered workflows before merge. This is code/control-plane evidence, not proof that a production host has registered a runtime. Older PRs #257 and #258 are superseded and closed.

### PR #262 follow-up — now merged

Status: **MERGED / 24-OF-24 EXACT-HEAD WORKFLOWS PASS / PRODUCTION RUNTIME ACCEPTANCE OPEN**

- Merge commit: `9b017919f95b2a4e6f30c20656c58bd354f7c133`.
- Exact validated PR head: `aa42e56eab7c7968c65bc6f84df0dcb6c13cc645`; all 24 triggered workflows completed successfully with zero failures.
- The follow-up adds the trusted `--runtime-factory module:callable` / `IIOS_CANONICAL_RUNTIME_FACTORY` handoff, rejects factory selectors supplied by request JSON, hides arbitrary factory exception text, and adds bounded per-request network timeouts plus a four-minute PILOT-02 capture-step limit.
- A prior head's PILOT-03 scope guard rejected the new timeout-contract test. The final head explicitly included the exact test path and its PILOT-03 scope-guard workflow passed.
- The pilot source capture is bounded and preserves failed-fetch diagnostics; the case remains `BLOCKED_NOT_ADMITTED`. No formal Decision Revision or report was written by the capture-only pilot.
- Non-claim: this PR supplies the trusted factory interface, not a production factory instance. The runtime registry remains empty unless the real host explicitly registers a genuine case-specific runtime. P0-LLM-001/P0-LLM-004 remain OPEN.



### PR #264 follow-up — runtime binding validation — merged 2026-10-10

Status: **MERGED / 16-OF-16 EXACT-HEAD WORKFLOWS PASS / PRODUCTION RUNTIME ACCEPTANCE OPEN**

- Merge commit: `e50018ffa5d8eec5909b98340ed74fe56c178344`.
- Exact validated PR head: `32de0b1a47188e45ea38339bfdc6013b631e0672`; all **16 / 16** triggered workflows completed successfully with zero failures.
- The dedicated P0 regression workflow passed **12 / 12 tests**; `compileall` and `git diff --check` passed.
- The shared validator is applied at runtime registration, registry lookup, host pre-registration resolution and runtime-factory resolution. It checks all eight non-null bindings, callable request/semantic interfaces, typed active registries, identity/version/policy matches, and the resolver methods required by the canonical decision path.
- Invalid pre-registered runtimes and placeholder resolver objects are blocked before formal artifacts are written.
- This closes the runtime-binding validation inconsistency only. It does not register a production runtime, identify the real user-facing host, admit evidence, or demonstrate genuine LLM/economic conformance. P0-LLM-001/P0-LLM-004 remain OPEN.

## 2. Priority and dependency graph

```text
A. PR #262 trusted factory handoff + bounded capture (MERGED)
A2. PR #264 runtime-binding validation across host/factory entry paths (MERGED)
        |
        v
B. Wire a trusted runtime factory into the actual user-facing host
        |
        +-------------------------------+
        |                               |
        v                               v
C1. Build real 605016 evidence      C2. Continue Route A / 新和成
    manifest with B2/PIT                 source adjudication
        |                               |
        v                               v
D1. Canonical real 605016 run       D2. B2-admitted 新和成 case
        |                               |
        +---------------+---------------+
                        v
E. Independent red-team + full Run Receipt replay
                        |
                        v
F. MVP acceptance decision (not trade execution)
```

**Critical path:** PR #262 + PR #264 → trusted host/runtime integration → 605016 source evidence and PIT admission → one real canonical run → independent red-team/replay.

The 新和成 case is a parallel Route A proving ground because its real raw-source bundle and fact-extraction candidates already exist. It must not block the original 605016 P0 acceptance, and it must not be relabeled admitted merely because source capture and PDF text matching succeeded.

## 3. Batch definitions and acceptance gates

### Batch A — trusted runtime-factory / bounded-capture follow-up

**Status:** MERGED / ACCEPTANCE PASS / PRODUCTION RUNTIME ACCEPTANCE OPEN.

**Promotion and observed result**
- PR #262 merged at `9b017919f95b2a4e6f30c20656c58bd354f7c133`.
- Exact validated head `aa42e56eab7c7968c65bc6f84df0dcb6c13cc645`: 24/24 required workflows completed successfully.
- Trusted factory configuration is sourced only from CLI/environment or host pre-registration, never from request JSON; invalid or missing factory is fail-closed and error details are not echoed.
- Each PILOT-02 source fetch is bounded (`--connect-timeout 8 --max-time 25 --retry 1`) and the capture step has a four-minute timeout.
- The earlier PILOT-03 scope-check finding on a stale head was corrected on the final head; exact-head PILOT-03 passed.

**Acceptance boundary**
- Batch A closes only the runtime-factory *handoff* and the hung-capture failure mode.
- It does not instantiate/register a production runtime, prove the actual host calls `canonical-run`, admit company Evidence/PIT, validate live model output or create a trade-authorized decision.
- The next batch is Batch B. Do not relabel P0-LLM-001/P0-LLM-004 as PASS merely because Batch A CI is green.

### Batch B — actual host composition and runtime-registration proof

**Status:** NOT STARTED; depends on Batch A.

The repository contains the CLI and a deliberately empty-by-default canonical runtime registry. A trusted factory loader is only a hook; it is not itself a deployed runtime. No separate web/server/front-end deployment entry was identified in the repository tree during this refresh, so the actual supported user-facing host must be identified and verified rather than assumed.

**Actions**
1. Identify the real user-facing host/entry path and document the exact handoff from natural-language request to `canonical-run`.
2. Implement the smallest trusted composition root for that host. It must provide all required bindings: request interpreter and registry, semantic producer and producer registry, current-price resolver, independent-forecast resolver, upstream-authority resolver and valuation-output resolver.
3. Ensure host-controlled deployment configuration selects the factory. Do not load a Python module/callable name from the user request bundle or case JSON.
4. Add a host-level integration test that uses a new test run ID and verifies the persisted Run Envelope and stage receipts. Keep test-only producers clearly typed and inadmissible as production evidence.
5. If the host cannot invoke a genuine model callback, explicitly report the semantic stage as BLOCKED/NOT_RUN. A manually supplied expert artifact or fixture is not live LLM conformance.

**Pass criteria**
- A user request through the actual host reaches `canonical-run`, not legacy `run` or `run_case` directly;
- a trusted runtime is registered for the process and all mandatory bindings are present;
- runtime binding and producer identity/version/input-output lineage are persisted and replay-verifiable;
- no host integration test relies on fixture outputs to claim production semantic conformance.

**Credential boundary:** no LLM API key is required for public-source discovery, raw evidence capture or B2/PIT validation. A real model-runtime callback is necessary to claim that a live natural-language-to-semantic reasoning stage passed. If the deployed host has no usable model callback, report that as a separately blocked integration, not a reason to reintroduce paid credentials into Route A.

### Batch C1 — actual 605016 (百龙创园) source bundle and B2/PIT admission

**Status:** **PARTIAL CAPTURE VERIFIED / EVIDENCE AND PIT NOT ADMITTED**. Raw bundle and case manifest exist; this advances acquisition but not the original P0 analysis acceptance.

**Observed capture**
- Case manifest: `manifests/company_cases/RC-CN-A-605016-20261009.json`; capture request: `manifests/capture_requests/RC-CN-A-605016-20261009.json`.
- Attempt 1, run `38014567975`: 11/12 sources captured; Investing historical-price URL failed with `HTTP_REQUEST_FAILED`; artifact `11655558984`.
- Attempt 2, run `38014724607`: source refs registered as official SSE or explicitly secondary-validation types; 11/12 captured; the same Investing URL failed; artifact `11655484327`.
- Attempt 3, run `38014829961`: the Sohu historical-price page replaced the inaccessible Investing candidate; 12/12 captured, 0 failed sources, 0 unregistered refs, independent byte/hash verification 12/12, artifact `11655654643`. All outputs remain NOT_ADMITTED.
- Attempt ledger: `evidence/real_cases/RC-CN-A-605016-20261009/ROUTE_A_CAPTURE_ATTEMPTS_20261010.md`.

**Remaining actions**
1. Independently adjudicate each captured document's identity, source origin, title, page/table/row locator, exact publication timestamp/known-at basis and reuse/license status. A registered source_ref and exact bytes alone do not admit a fact.
2. Resolve the authoritative 2026-10-09 close; Stockstar/Sohu are secondary acquisition candidates, not primary market-data authority. Preserve the declared `unknown_pit_sources=1` until resolved.
3. Convert only fact-level claims that pass independent adjudication to B2 Evidence Records, preserving exact bytes and their hashes; run the unchanged B2 Evidence/PIT validator and independent red-team. `UNKNOWN` must not cover a required group.
4. Where an official public source cannot provide the necessary time/version facts, capture an operator-supplied original and preserve provenance. Do not backfill dates from current retrieval time.
5. Keep the three-run acquisition history, including the failed Investing URL attempts; do not rewrite failed rows as successful merely because a replacement source was later captured.

**Price-date correction.** The official 2026 exchange calendar says the A-share market closed October 1–7 and resumed October 8. Therefore for a cutoff of **2026-10-09**, the intended latest-trading-date observation is the **2026-10-09 close**, subject to exact source verification—not the September 30 close used in the earlier 2026-10-07 PILOT-02 test. Keep the two cutoffs and their receipts separate. Official calendar sources:
- SZSE 2026 trading calendar: https://investor.szse.cn/English/services/trading/calendar/index.html
- SSE holiday notice dated 2026-09-17: https://www.sse.org.cn/disclosure/notice/general/t20260917_622911.html

**Pass criteria**
- all seven required groups have at least one individually valid, source-bound, case-bound and PIT-qualified `ADMITTED` evidence record;
- the manifest's raw artifacts re-verify from bytes, not caller-supplied hash declarations alone;
- case ID, symbol, company, cutoff and source identity are consistent;
- no report valuation/decision proceeds while a required group remains uncovered or UNKNOWN.

### Batch C2 — finish Route A evidence adjudication for 新和成 (002001.SZ)

**Status:** PARTIAL CAPTURE VERIFIED / FACT CANDIDATES NOT ADMITTED; can proceed in parallel with C1.

Run #8 retained 8 of 9 declared sources and passed independent byte verification for the 8 captured objects. PR #259 added 11 page-located fact candidates from three PDFs; all remain `known_at=null`, `provenance_class=UNKNOWN`, `status=UNKNOWN`, `admission_status=NOT_ADMITTED`.

**Actions**
1. Preserve and verify the downloaded Run #8 ZIP outside Git. The GitHub Actions artifact is scheduled to expire on **2026-10-23 UTC**; do not rely on a short-lived Actions artifact as the only copy.
2. Independently verify issuer/exchange document identity and first-public timestamp for each fact's source. URL path/filing heading/PDF text match is a candidate locator, not by itself proof of first-public time.
3. Resolve the declared `PUBLIC_ACCESS_REUSE_UNKNOWN` status, keeping redistribution restrictions distinct from the ability to use an internally reviewed fact.
4. Convert only adjudicated facts to B2 Evidence Records and run the current B2/PIT preflight. Keep all rejected/unknown rows and reason codes.
5. Capture a date-specific free historical price observation for the case cutoff. Do not reuse the 2026-09-30 close for a 2026-10-09 cutoff without showing why it is the correct as-of observation.
6. Fill any missing corporate-disclosure and other group coverage with official/free sources; source capture count is not group admission.

**Pass criteria**
- each admitted fact has independently supportable source origin, field-level locator, exact source-byte hash, known-at basis and legal/reuse disposition;
- the B2 manifest covers all seven mandatory groups without UNKNOWN placeholders;
- the original failed source row and any new acquisition failures remain explicit;
- a fresh independent B2 review agrees with the validator outcome.

### Batch D1 — one real canonical 605016 run

**Status:** BLOCKED until B and C1 pass.

Run only the single user-selected company. Do not add CSI800/industry screening, broad dataset construction or auto-trading.

The canonical run must follow:
`Research Case → Run Envelope → Evidence acquisition/admission → genuine semantic production/admission → independent forecast → valuation/MIE → risk/positioning → Decision Admission → Decision Revision → Machine Publication → human-readable report → IIOS_RUN_RECEIPT → independent replay`.

**Decision contract**
- Use the user's current fundamental-long-term investment rules and the default reference horizon `H=1Y`; only use a 3Y override if the Case explicitly records `Override=TRUE` and the reason qualifies.
- The 15% hurdle is an annualized return target, not a discount rate.
- Preserve the priority order `Trust > Portfolio Constraint > Long-term Value > Expectation Gap > Tactical`.
- Output action, core/tactical position, price zones or target-entry price, annualized expected return, key drivers, risks, thesis-break conditions and reassessment triggers.
- Human approval remains mandatory; no automatic order execution.

**Pass criteria**
- the actual run uses admitted case evidence and genuine authorized stage outputs, not test fixtures;
- decision, publication, report and receipt are immutable and bound to the exact run/cutoff;
- a clean replay re-verifies the final `IIOS_RUN_RECEIPT`;
- evidence failure, missing semantic output or incomplete forecast/valuation blocks formal publication.

### Batch D2 — one real canonical Route A 002001 run

**Status:** BLOCKED on C2; do not allow this parallel case to obscure the primary 605016 P0 acceptance.

Apply the same full run/receipt/replay gates as D1. Use the 2026-10-09 cutoff and a separately verified October 9 price observation. Do not inherit the older PILOT-02 cutoff of October 7 or its September 30 price receipt.

### Batch E — fresh independent red-team and final MVP acceptance

**Status:** NOT STARTED; depends on D1 for the critical path and D2 if Route A is claimed accepted.

The red-team must test both negative bypasses and one end-to-end positive real case:

- direct legacy CLI, direct kernel and direct low-level writer attempts cannot create formal canonical artifacts;
- caller-supplied case/run IDs, factory spec, hashes or admission receipts cannot manufacture authority;
- wrong case/symbol/cutoff or cross-run receipts are rejected;
- source tampering, missing/late `known_at`, unknown provenance and uncovered groups fail closed;
- missing or fixture-only semantic/forecast/valuation output blocks the canonical run;
- publication/report/Run Receipt mutation or replay against a different run is rejected;
- network acquisition timeouts preserve raw failure diagnostics and never convert failed fetches into successful/UNKNOWN bytes;
- the real positive case produces a replay-verifiable receipt while still requiring explicit human approval.

**MVP acceptance only if:** exact-head CI is green; an independent clean-room red-team passes; the actual host path, genuine producer identity and case evidence lineage are demonstrated; the real run reaches report and replay without bypass; all seven evidence groups are admitted; no order execution is possible.

## 4. Operating rules across all batches

1. **Exact-head discipline:** every PR gate is evaluated against that PR's current head. An older green run does not validate a newer commit.
2. **Unknown stays unknown:** capture, byte integrity, page text matching, source authenticity, PIT admission and decision-grade sufficiency are separate statuses.
3. **Free-first:** Route A cannot be blocked on paid search or external-LLM API credentials. Optional provider integration is not an evidence-ingestion dependency.
4. **No fake passes:** no fixture or human-entered semantic artifact may be described as live LLM output. Do not infer admission from CI green.
5. **No scope drift:** no automatic stock screening, CSI800/industry dependency, broad data warehouse or trading engine in this MVP sequence.
6. **Persist each accepted batch:** merge the code and sync `PROJECT_STATE_INDEX.md` with exact SHA, validation outcome, non-claims and next gate.
7. **Fail safely:** any incomplete required gate results in `BLOCKED` / `REVIEW_REQUIRED`; do not create a formal investment proposal or claim a completed Run Receipt by fallback.

## 5. Immediate execution order

1. Batch A and P0 runtime-binding validation are complete: PR #262 passed 24/24 exact-head workflows; PR #264 passed 16/16, including 12/12 dedicated P0 regression tests. Do not treat either result as production-runtime acceptance.
2. Begin Batch B: wire the trusted factory into the actual user-facing host and prove the host calls `canonical-run`; a loader and valid binding interface alone are not a registered production runtime.
3. Continue C1 from the verified 12/12 raw capture into source-origin/license/PIT adjudication, especially the authoritative 2026-10-09 price; run C2's Xinhecheng fact adjudication in parallel.
4. Only after source groups and PIT admission pass, execute D1/D2 canonical real runs and receipt replay.
5. Finish with independent red-team and explicit MVP acceptance; keep P0-LLM-001/P0-LLM-004 OPEN until production-backed semantic conformance is proved.
