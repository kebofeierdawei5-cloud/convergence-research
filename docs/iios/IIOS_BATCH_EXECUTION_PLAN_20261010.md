# IIOS Batch Execution Plan — Refreshed 2026-10-10

**Plan class:** execution plan / canonical-main recovery  
**Authority baseline:** `main@a62e2304983cbdf28f0365f7fd55f53378c4adab`  
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
| P0 Batch 1 CLI host integration | PR #267 / merge `b26e3e071eec7e145c46d4bef8a6f206439be1c2` | Exact validated head `cd44c503ed2535bede25ad4a5e2f483cfb606ef4`: 13/13 dedicated P0 tests passed; CLI persists ordered stage lineage | Proves repository CLI path only; no deployed host or live LLM conformance |

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
B1. PR #267 repository CLI host-route persistence integration (MERGED; control-plane only)
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

**Critical path:** PR #270 first-party HTTP host + PR #274 trusted factory code (MERGED) → real endpoint/keypair/durable admitted-store provisioning and host deployment acceptance → PR #272 current-main 605016 capture refresh → issuer-origin/license/PIT fact admission → one real canonical run → report/Run Receipt replay → independent red-team.

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

### Batch B — first-party host composition, runtime registration and production acceptance

**Status:** FIRST-PARTY HOST IMPLEMENTATION MERGED / PRODUCTION RUNTIME + DEPLOYMENT ACCEPTANCE OPEN.

PR #270 added a first-party loopback-first HTTP host entrypoint inside the canonical repository. This resolves the absence of a repository-owned deployable host adapter. It does not claim that any deployment is already running, or that an actual production runtime has been registered.

#### Batch B1 — repository CLI host integration

**Status:** MERGED / EXACT-HEAD P0 WORKFLOW PASS.

- PR #267 merged at `b26e3e071eec7e145c46d4bef8a6f206439be1c2`.
- Exact accepted head: `cd44c503ed2535bede25ad4a5e2f483cfb606ef4`.
- Dedicated P0 workflow passed **13/13 tests**, including `tests/test_canonical_cli_host_integration.py`; module compile and `git diff --check` passed. The additional triggered FM01 exact-source workflow also passed.
- The new test invokes `iios_mvp.cli.main()`, calls `canonical-run`, uses a fresh run ID, resolves the trusted factory from the CLI argument, and validates the persisted Run Envelope and ordered receipts through `HUMAN_APPROVAL_PENDING`.
- Test-only semantic/evidence inputs are explicitly marked `TEST_ONLY`; no report or complete Run Receipt is emitted by the CLI step itself.

This closes the repository-CLI route/persistence integration test gap only.

#### Batch B2 — first-party host adapter (MERGED) and production composition (OPEN)

**Implementation status:** MERGED; **production status:** NOT DEPLOYED / NOT ACCEPTED.

- PR #270 / merge `d8c5b41e13185c365314adacae1449255b8e0eaf`; exact PR head `79a5024ee52a37ff1450c6d56fbd24589cbcefcd`.
- Dedicated host workflow: **21/21 tests PASS**; eight exact-head checks all SUCCESS.
- Operator entrypoint: `python -m iios_mvp.canonical_host_v01`.
- HTTP accepts only an operator-staged `bundle_id`; trusted roots/runtime factory remain process configuration. The default bind is loopback, run submission is bearer-authenticated and responses cannot authorize trading.
- Deployment instructions and the complete trust-boundary/non-claim contract are in `docs/iios/P0_BATCH_B2_FIRST_PARTY_HOST_20261010.md`.

#### Batch B3 — trusted runtime factory implementation (MERGED) / runtime provisioning (OPEN)

- PR #274 merged at `a62e2304983cbdf28f0365f7fd55f53378c4adab`; exact head `14105076b1b69f626907e4eb8bdddf0893d84c23`; **8/8 exact-head checks SUCCESS**, including factory contract and red-team.
- Factory: `iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime`; set only in the trusted host environment as `IIOS_CANONICAL_RUNTIME_FACTORY`.
- Uses a real provider Responses-compatible HTTPS endpoint through the existing provider-neutral caller. Strict schema validates the model's natural-language request intent and thesis-only semantic proposal. Signed raw-response receipts are written immutably and checked against a configured Ed25519 public-key pin before semantic admission.
- All eight runtime bindings are composed, but upstream stores remain read-only: the factory cannot write fake ADMITTED current prices, forecasts, authority, or valuation outputs.
- Factory contract and operator setup are specified in `docs/iios/P0_BATCH_B2_TRUSTED_RUNTIME_FACTORY_20261010.md`.

**Remaining actions**
1. Provision trusted bundle/data/output roots and the host auth token outside Git; deploy the host and record the deployed commit/config provenance.
2. Configure `IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime`, a real HTTPS provider endpoint (self-hosted with `AUTH_MODE=NONE` is permitted if genuinely available), pinned Ed25519 keypair, and a durable canonical admission root. No API credential is required for source capture; a live semantic callback requires a real endpoint.
3. Ensure the bundle is prepared from the real case and admitted source bytes; never accept request-supplied paths or semantic assertions. The factory must resolve genuine current-price, independent forecast, upstream-authority and valuation records, all case/cutoff bound and independently replayable.
4. Obtain one fresh host-origin run. Missing model output, missing evidence, absent references or wrong case identity must return `BLOCKED`, not fallback.
5. Only after successful Evidence/PIT + semantic/Forecast/Valuation admission run publication/report/complete `IIOS_RUN_RECEIPT` replay and independent red-team.

**Pass criteria remaining**
- The service is actually deployed in the operator environment and its build SHA/config provenance are recorded.
- The factory returns a fully validated `CanonicalRuntimeBindings` from trusted config; real callback/producer identity and output lineage replay cleanly.
- At least one real company run passes the exact-byte seven-group Evidence/PIT gate and all downstream admission/report/receipt gates.
- Human approval remains required and automatic execution remains disabled.

**Credential boundary:** the host adapter itself and Route A evidence intake need no paid API key. A genuine semantic stage requires a real configured model callback or signed production-origin semantic receipt; the host deliberately blocks rather than fabricating one.

### Batch C1 — actual 605016 (百龙创园) source bundle and B2/PIT admission

**Status:** **CURRENT-MAIN RAW CAPTURE/INTEGRITY PASS / SOURCE-ORIGIN + EVIDENCE/PIT NOT ADMITTED**.

**Canonical implementation and actual capture**
- PR #272 merged at `2978cdbc3f76f1ab1596896e3425c75661144a57`; exact accepted PR head `e8209d5de74a034db11b06574577bc8653759cdd`.
- Case: `RC-CN-A-605016-20261009`; cutoff `2026-10-09`; source manifest: `manifests/company_cases/RC-CN-A-605016-20261009.json`.
- Attempt 10 workflow #38026139364 succeeded against current-main-refresh code; artifact #11660285551 (8,526,921 bytes; retained temporarily under Actions retention).
- 12/12 response bodies captured; 0 failed sources; 0 unregistered refs; 12/12 independent byte-size/SHA checks passed; 12/12 expected-payload contracts passed; 0 mismatches.
- Independent status: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`; `source_origin_verified=false`; one source has unknown PIT timing.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; all seven field groups uncovered; `evidence_admission=false`, `pit_admission=false`.

**Next actions — fact-level adjudication, not more capture-only changes**
1. Preserve Artifact #11660285551 beyond the temporary Actions window, keeping intake receipt, manifest hash, exact source hashes and ledger together; do not claim permanent retention until a durable copy is confirmed.
2. For every object, re-open exact bytes and recompute hash/size; confirm issuer/exchange identity, title, stock code, report/announcement number, period and date from document body; retain page/table/row locators.
3. Verify first-public/known-at from an official source-backed index/event record, not retrieval time or URL date alone. Keep the unknown source as UNKNOWN.
4. Review reuse/licensing separately from public accessibility; unresolved `PUBLIC_ACCESS_REUSE_UNKNOWN` remains explicit.
5. Resolve the cutoff-correct 2026-10-09 closing price. Stockstar's reported CNY 20.28 close is a secondary cross-check only pending exact-byte capture and adjudication; do not use the 2026-09-30 close by default.
6. Create fact-level B2 Evidence Records only for individually adjudicated facts; run unchanged B2/PIT validator and fresh independent red-team. A source group is covered only by admitted facts, never by captured source count.

Audit record: `docs/iios/ROUTE_A_C1_605016_ATTEMPT10_ADJUDICATION_20261010.md`; full attempt history: `evidence/real_cases/RC-CN-A-605016-20261009/ROUTE_A_CAPTURE_ATTEMPTS_20261010.md`.

**Decision gate:** Until all seven groups are covered by valid, case-bound and PIT-qualified `ADMITTED` Evidence Records, D1 may not produce formal valuation, expectation-gap decision, report/publication or complete `IIOS_RUN_RECEIPT`. Do not convert capture/integrity PASS into an economic-analysis PASS.

**Price-date correction:** the exchange was closed Oct 1–7 and resumed Oct 8; cutoff Oct 9 requires the Oct 9 close when exact source verification is available. Keep the Oct 7 PILOT cutoff and Sep 30 price receipt separate.

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

1. Batch A, the first-party host and trusted runtime factory code are merged. PR #262 passed 24/24, PR #264 passed 16/16, PR #267 passed 13/13 dedicated P0 tests, PR #270 passed 21/21 host tests, and PR #274 passed 8/8 exact-head checks including factory-contract and red-team.
2. Batch B source code is implemented (host PR #270 + factory PR #274); production deployment/runtime/semantic acceptance remains OPEN until the operator environment provisions a real endpoint/keypair/store and a real host-origin run passes receipt replay. Do not infer production acceptance from host/factory CI.
3. Continue C1 (605016) source-origin/license/PIT fact adjudication using Attempt 10 artifact #11660285551 and preserve all UNKNOWN states; run C2 (002001) source adjudication in parallel.
4. Only after the seven evidence groups and PIT admission pass, execute D1/D2 real canonical runs and complete receipt replay.
5. Finish with independent red-team and explicit MVP acceptance; keep P0-LLM-001/P0-LLM-004 OPEN until a production-backed real-company conformance run passes.
