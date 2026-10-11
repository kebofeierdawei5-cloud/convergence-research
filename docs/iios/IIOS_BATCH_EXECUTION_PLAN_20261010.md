# IIOS Batch Execution Plan — C0-aligned refresh 2026-10-11

## ACTIVE EXECUTION ORDER — AUTHORITATIVE REFRESH (2026-10-11)

This order supersedes the earlier “Immediate execution order” further below. The then-current Git `main` and `docs/PROJECT_STATE_INDEX.md` remain the state authority.

1. **Batch 0 — narrow state reconciliation:** make the P0 incident workflow run on explicit `main` pushes, classify the observed failure-with-zero-jobs as unclassified (not a test failure and not a PASS), align the current plan/state surfaces, and retain the C0 local-first decision without making local model installation a dependency for deterministic work.
2. **Batch 1 — PASS / MERGED at `4ccb8cf89084d7299dfa8d0774cce97009eb5b54`:** deterministic private Path A scenario runner is implemented in `iios_mvp/private_scenario_analysis_v01.py`; PR #356 exact-head checks and the dedicated workflow passed, including 40 tests. The post-merge scenario workflow passed as run #38143646589. It consumes the normalized private price record, binds versioned analysis-only profiles, calculates price-return/downside constraints, emits private JSON/Chinese Markdown/integrity receipt, and verifies replay. The operator now reports that the replacement launcher completed normally. The local bundle/receipt is not attached to GitHub and has not been independently reviewed in this session, so it is recorded as operator-reported success rather than independently verified bundle acceptance. The first launch's permission mismatch and `set -u` defect were fixed in PR #358; 12 exact-head checks and three static tests passed. See `docs/iios/PATHA_MACOS_ONECLICK_LAUNCHER_PERMISSION_FIX_20261011.md`. No formal Decision is created.
3. **Parallel C1:** preserve the existing 605016 candidate and hashes. Resolve applicable SSE market-data use permission and authorized signer identity/scope. Do not repeat source ingestion. No signer or permission flag may be self-asserted.
4. **Parallel C2:** preserve the pinned Xinhecheng 13-fact review; obtain the distinct authorized fact/use reviewer and record the permitted scope. `PUBLIC_ACCESS_REUSE_UNKNOWN` remains blocking until independently resolved.
5. **Batch 2 — CI audit slice PASS / local bundle review OPEN:** PR #360 is merged at `0d257fe243d0a2e921023504c2a3b2128fdd285a`; the dedicated workflow passed 43 tests and all 13 exact-head checks passed. The independent checks cover profile assumptions, scenario arithmetic, hurdle/Bear-loss entry ceilings, Chinese report-to-JSON consistency and exact-byte hashes. A sanitized local receipt review is still required before independently recording bundle acceptance; no private input, price, or source label is to be uploaded.
6. **Operator-entered price track — owner-directed; MP-1 implementation on the feature branch:** the operator will initially enter A/H share prices manually. The PR adds `iios_mvp/operator_entered_price_decision_input_v01.py`, an interactive local intake, private content-addressed input/receipt, replay validation, 19 focused tests, including self-rehashed provenance escalation and timestamp/storage boundary cases, and dedicated CI wiring. Its output remains `OPERATOR_ATTESTED_MARKET_DATA`; hashes and local confirmation do not prove source truth, vintage or rights. Exact-head CI and independent red-team remain pending. MP-2 decision-chain/Run Envelope binding and MP-3 end-to-end adversarial acceptance remain open. Until MP-2/3 pass, this tool does not create a formal Decision and existing Path A scenario output remains analysis-only.
7. **C1/C2 formal evidence admission and authorization:** continue independent company-fact source/use review and authorized-signature work. C1's existing exchange-price candidate remains blocked as exchange-sourced evidence; do not repeat ingestion. The manual-input lane does not close the old SSE rights question, authorize public reuse, or replace C2's independent sign-off of its thirteen company-filing facts.
8. **Formal path:** production Host and canonical Decision work proceed only when their own gates pass. A genuine canonical company run still requires admitted company evidence, authorized semantic producer, case-bound Forecast/Valuation/Risk/Position, Decision Admission, human approval boundary, publication/report QA, full `IIOS_RUN_RECEIPT`, and independent replay.

**No local LLM/Ollama/model/API prerequisite applies to Batch 1, evidence signer code/key generation, or exchange-rights review.** The unresolved formal semantic-producer assurance remains an explicit separate gate; ordinary ChatGPT Free Web output must not be relabelled canonical.

**Batch 0 CI anomaly:** run `38137977103` on `f632169f4da60a19f194b0abba109600c67e51f3` shows failure with zero jobs, while the workflow lacked an explicit push trigger. It is not evidence of failed test assertions. Follow-up after Batch 0: the explicit push trigger did NOT resolve the anomaly; run `38143107853` at `main@e06669fc6093669e2bfd657a8679c6d061d414e3` again reports `failure` with zero jobs. Keep this item OPEN and investigate workflow execution/check-suite configuration in a separate narrow CI repair. It is not a test assertion failure and cannot be treated as PASS. This specific anomaly does not replace or mask the dedicated Batch 1 scenario-analysis test workflow.


**Plan class:** execution plan / canonical-main recovery  
**Authority baseline for this refresh:** `main@18854586bd6cd71059d6da7d3beef4f1f61a8e64`  
**State authority:** `docs/PROJECT_STATE_INDEX.md`  
**Purpose:** move IIOS from validated control-plane code to a real, fail-closed, single-company research run without making external LLM API credentials a Route A prerequisite.

## 0. C0 — Architecture and product-entry decision (2026-10-11)

**Decision:** use **LOCAL_SINGLE_USER / local-first** as the default MVP deployment profile, reusing the existing canonical CLI/first-party loopback Host, Orchestrator, trusted runtime factory, Store/admission records, report QA, complete Run Receipt and replay. The remote/multi-user profile, new UI, browser extension, database replacement and parallel orchestration remain deferred. See `docs/iios/C0_LOCAL_FIRST_ARCHITECTURE_AND_MVP_ENTRY_DECISION_20261011.md`.

**Formal producer boundary:** the existing ChatGPT Free Web manual handoff is NON-CANONICAL only under frozen B0; it cannot be selected for formal semantic admission. Prefer the existing provider-neutral factory with an operator-controlled local Ollama-compatible runtime when its configured identity, model/version, signed receipts and lineage pass the existing contracts. No paid API key is a prerequisite; absence of a compliant runtime means BLOCKED, never silent manual-Web fallback.

**Product-entry boundary:** a generic ChatGPT conversation saying “use IIOS” does not prove the repository runtime ran. Formal output must return from a supported local CLI/Host entry and bind to the canonical Run Envelope, stage receipts, admissions, Decision/Publication/report and full Run Receipt/replay. This decision does not itself connect the current chat surface to a local process.

**Dependency rule:** safe local configuration/liveness and C1/C2 review can proceed in parallel. One actual 605016 Host-origin canonical run, after C1 formal Evidence/PIT admission, should provide overlapping D1-A/D1 evidence wherever each gate's own criteria are met; avoid a redundant smoke run unless an independently required test cannot be covered by the same run. C2 remains a parallel evidence track and D2 remains separately gated.

**Non-claim:** C0 does not close P0-LLM-001/P0-LLM-004, does not claim a real Host/provider run, does not admit C1/C2 evidence, and does not constitute MVP acceptance or investment-performance validation.



**No-local-LLM boundary for admission/rights work (2026-10-11):** formal Evidence/PIT signer implementation, signer trust enrollment, official source-use review and written exchange permission requests are deterministic governance/data-rights work. They must not be held behind installing or configuring a local model. Local Ollama/model runtime work remains a separate integration lane; absence of a local LLM does not justify resetting or pausing C1/C2 signature and rights progress.

## 0.1 Parallel execution checkpoint — C1 / C2 / D1-A (2026-10-11)

Current checkpoint record: `docs/iios/C1_C2_D1A_PARALLEL_GATE_EXECUTION_AUDIT_20261011.md`.

- **C1:** existing private source-vintage successor and Core/PIT candidate are complete; do not rerun ingestion or fetch the source again. Formal signed Evidence/PIT admission remains BLOCKED: the current private-candidate receipt explicitly sets `formal_signed_admission_created=false`, the inspected candidate/validator path does not produce an approved signed admission, and the SSE rule separately restricts use of exchange transaction information absent permission. The rule-derived 15:30 upper bound supports conservative PIT ordering, not exact endpoint first-public time or reuse permission.
- **C2:** preserve Run #8 and operator-attested price class. The second-source spot review checked official SZSE PDF/board-resolution pages and the official SZSE site terms. A narrow personal non-commercial private fact-level/no-redistribution handling is supported as an operational interpretation, not a legal opinion. The canonical machine disposition and external/human reviewer sign-off remain open; do not relabel `PUBLIC_ACCESS_REUSE_UNKNOWN` as admitted without that review.
- **D1-A:** existing setup helper and Runbook provide the local preparation path. This assistant session has not executed them on the operator's Mac. Configuration, installed model/version and loopback probe remain operator-environment evidence, not code/CI status. Do not call the 605016 canonical endpoint before C1 formal admission.
- **Path A price overlay:** use the separately supplied 2026-10-09 closes as private `OPERATOR_ATTESTED_MARKET_DATA` on a price-only 2026-10-10 start-of-day overlay. This is allowed for scenario valuation only; it must not mutate the frozen 2026-10-09 start-of-day Case, enter the canonical current-price resolver, claim source-vintage or usage-rights PASS, or create a formal Decision. The Python intake is deterministic and has no LLM/model prerequisite. Full company Evidence/PIT consistency at 2026-10-10 is not established by this price-only overlay.
- No private quote values, source bytes, manifests, secrets or prompt/response bodies are published by this checkpoint.

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

### PR #283 — canonical runtime callback preflight — merged 2026-10-10

Status: **MERGED / 8-OF-8 EXACT-HEAD CHECKS PASS / REAL OPERATOR CALLBACK STILL OPEN**.

- Merge commit: `d18251fe7541267dad49d04bad67ada54ab58e31`.
- Exact validated head: `a86457fcadeb951bbc89e0e0a0b8d747ef55b0b3`; all eight triggered checks passed.
- The dedicated workflow passed 23/23 preflight/factory/Host contract tests plus a separately executed 5/5 adversarial suite; compileall and diff checks passed.
- Entry: `python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id <staged_bundle_id>`. It uses the existing trusted factory, not an alternate factory, and calls both provider-backed request-intent and thesis-semantic callbacks. Signed raw provider receipts continue to be pinned to the trusted Ed25519 public key and independently verified.
- The report records only receipt hashes and minimal provider metadata, not prompt or raw output. It is an immutable diagnostic, not a canonical run receipt. Evidence/PIT admission and semantic admission remain explicitly unchecked; no forecast, valuation, decision, publication, report or complete Run Receipt is produced.
- The adversarial suite covers bundle path traversal, duplicate JSON keys, wrong instrument, semantic authority smuggling, prompt/output leakage and provider failure without fallback.
- Non-claim: no real operator environment/model endpoint was available for a genuine callback run; test doubles in CI do not prove production connectivity or Host-origin acceptance. The preflight command must be run inside the actual intended operator environment.
- C1/605016 remains blocked on `market_price`; P0-LLM-001/P0-LLM-004 remain OPEN.



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
2. Use the existing provider-neutral factory as the formal route, preferably with an operator-controlled local Ollama-compatible endpoint under the documented loopback + `SELF_HOSTED` + `AUTH_MODE=NONE` policy when the model meets the signed-receipt and lineage contracts. Configure `IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime` and the trusted provider identity/model/version/keypair in the protected host environment. Do not select `iios_mvp.chatgpt_chat_runtime_v01:build_chatgpt_chat_runtime` for formal decisions: the PR #342 fail-closed governance guard keeps copied ChatGPT Free Web responses NON-CANONICAL because saved-byte hashes do not authenticate model origin. This path remains available only for explicitly NON-CANONICAL operator assistance. A compliant local runtime needs no paid model API key; if no compliant producer is available, formal semantic admission stays BLOCKED.
3. Ensure the bundle is prepared from the real case and admitted source bytes; never accept request-supplied paths or semantic assertions. The factory must resolve genuine current-price, independent forecast, upstream-authority and valuation records, all case/cutoff bound and independently replayable.
4. Obtain one fresh host-origin run. Missing model output, missing evidence, absent references or wrong case identity must return `BLOCKED`, not fallback.
5. Only after successful Evidence/PIT + semantic/Forecast/Valuation admission run publication/report/complete `IIOS_RUN_RECEIPT` replay and independent red-team.

**Pass criteria remaining**
- The service is actually deployed in the operator environment and its build SHA/config provenance are recorded.
- The factory returns a fully validated `CanonicalRuntimeBindings` from trusted config; real callback/producer identity and output lineage replay cleanly.
- At least one real company run passes the exact-byte seven-group Evidence/PIT gate and all downstream admission/report/receipt gates.
- Human approval remains required and automatic execution remains disabled.

**Credential boundary:** the host adapter itself and Route A evidence intake need no paid API key. A genuine semantic stage can use a real local Ollama Responses endpoint without a paid API key if the Host and model share a machine; a remote/external endpoint must be HTTPS and may impose its own credential requirements. The host deliberately blocks rather than fabricating a response.

### Batch C1 — actual 605016 (百龙创园) source bundle and B2/PIT admission

**Status:** LOCAL PRIVATE CANDIDATE + BOUNDED SOURCE-VINTAGE SUCCESSOR PASS; FORMAL ADMISSION/HOST ACCEPTANCE OPEN.

- PR #329 is merged at `53b6896e9d63affd05d6d66cbddc5c0aa3bd81f6`. Its final HEAD passed private persistence 53/53, B2 Evidence/PIT 31/31, company Evidence/PIT 23/23, B2 scope 3/3, plus State Hygiene, C0 Governance, Investment Core and independent red-team.
- Operator-confirmed successor result: `SOURCE_VINTAGE_ADJUDICATED_PRIVATE_B2_CANDIDATE_CORE_VALIDATOR_PASS_NOT_PRODUCTION_ACCEPTED`; 11 evidence records, 11 declarations, 8 unique raw files; Core/PIT PASS.
- The new `known_at` uses the rule-derived upper bound `2026-10-08T15:30:00+08:00`, not the official endpoint's exact first-public timestamp. `exact_first_public_timestamp_verified=false` remains explicit; rule-page bytes were not materialized/hashed in the run.
- The legacy candidate is retained unchanged. `official_source_refetched=false`, `attempt10_downloaded=false`. Do not rerun ingest or perform another C1 price acquisition for this closed storage/vintage gate.
- Formal signed admission, a production Host-origin run, authorized semantic/Forecast/Valuation chain, Decision, publication, full Run Receipt and trade authorization remain separate and open.
- **Formal admission blocker confirmed by the parallel checkpoint:** the existing private ingest/persistence result is a candidate receipt, not an authorized signed admission. Before C1 can be declared formally admitted, the project must identify/approve the signing authority and admission record contract and establish the allowed-use basis for the exchange market-price source. Do not reuse the Provider signing key or manually flip a state field to manufacture authority.

**PIT price-date correction:** the cutoff is date-only `2026-10-09` and is interpreted as the start of that date. The applicable market-price observation is the latest fully completed session before cutoff, `2026-10-08`, not the `2026-10-09` close. The date-only rule must not be changed to end-of-day merely to admit same-day data.
### Batch C2 — 新和成 (002001.SZ) cutoff-safe successor adjudication

**Status: ACTUAL PRIVATE CORE/PIT PASS (7/7; OPERATOR-ATTESTED) / C2-P3 SEPARATE-METHOD CI PASS (13/13) / PR #345 MERGED / USE RIGHTS AND EXTERNAL SIGN-OFF OPEN.**

**Resolved breakpoint and exact-head execution**

- PR [#333](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/333) corrected the Route A preflight implementation, regression tests and schema: a date-only cutoff `2026-10-09` is normalized to `2026-10-09T00:00:00+08:00`, matching the unchanged Core temporal contract. Explicit timezone-aware timestamps are preserved. The historic Run #8 manifest and preflight were not modified.
- PR [#334](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/334) merged at `00be321497baf9cf0352ae14b303c560bc5846b7`. Exact-head workflow [#38121849097](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38121849097) passed its C2 contract tests, verified the pinned Run #8 artifact digest before extraction, replayed source-byte checks, validated 13 page-located fact candidates from three official SZSE PDFs, ran the unchanged canonical Core/PIT validator, and uploaded only a sanitized status report.
- The original Run #8 archive SHA-256 remains `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`; all 8 captured raw files match their receipt size/hash. The uncaptured Eastmoney K-line source still has no bytes or hash.
- Run #8 was created before the optional payload-contract fields were introduced. The verifier first rejected that legacy shape; the new tool handles only this exact missing-default case through an ephemeral copy and normalizes `expected_payload_type=ANY` / `payload_contract_status=NOT_CHECKED`. Original ZIP, receipt, manifest, raw bytes and old preflight stay untouched. All other verification failures remain blocking.

**Core/PIT successor result**

- Case cutoff is `2026-10-09T00:00:00+08:00`. Thirteen exact PDF page/term locators passed. The candidate manifest uses conservative publication-date upper bounds for `known_at`; `published_at` remains a date-level value. The exact intraday first-public timestamps remain unverified, and supporting board-resolution PDF bytes were not present in the original Run #8 capture.
- The unchanged Core/PIT validator returned only `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`. The six other required groups are covered in the ephemeral candidate manifest; overall B2 status is still `BLOCKED`, not PASS.
- The original Run #8 same-day 2026-10-09 buyback-progress notice and close remain excluded. The dynamic issuer IR page and Sohu/Eastmoney price pages are excluded; public access does not automatically establish source-vintage or allowed-use rights.
- Sanitized machine report: `evidence/real_cases/RC-CN-A-002001-20261009/C2_SUCCESSOR_CORE_VALIDATION_REPORT_20261011.json`. It includes no raw PDF bytes, source numeric fact values or numeric market quote.

**Next gates**

1. **Completed:** direct operator-provided close handled through the private `OPERATOR_ATTESTED_MARKET_DATA` path; no second web audit was performed. The actual private run of the merged tool passed all seven Core/PIT groups with 14 evidence records (13 official filing candidates plus one operator-attested price), while preserving the pinned Run #8 bytes. See audit section 10 for hashes; numeric values and the private manifest remain off GitHub.
2. **Completed: separate-method C2-P3 review in CI.** PR [#345](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/345) and exact-head workflow [#38126026797](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38126026797) passed by re-opening the pinned Run #8 capture, independently extracting the 13 PDF locator sets and validating original member hashes, official HTTPS source bindings and conservative `known_at` bounds. The sanitized detailed result is durably archived at `evidence/real_cases/RC-CN-A-002001-20261009/C2_P3_FACT_REVIEW_CI_RESULT_38126026797.json`. This is not a separate human/external reviewer or legal opinion. The output explicitly shows all sources remain `PUBLIC_ACCESS_REUSE_UNKNOWN`. The parallel second-source spot review reopened the official SZSE report pages and publication resolutions and reviewed SZSE's public-site legal statement, which permits non-commercial browsing/downloading but restricts for-profit use without written permission. This supports only a narrow proposed personal non-commercial private fact-level/no-redistribution handling class, not a legal opinion or market-data license. The existing machine status remains unchanged and the independent reviewer sign-off is still open.
3. After that review, prepare a new immutable case successor and complete formal signed Evidence/PIT admission. Preserve the operator-attested market-price class as distinct from source-vintage-verified price data. Do not repeat price web search unless the operator explicitly asks.
4. **D2 remains blocked** until the independent fact review and signed admission pass, then production Host acceptance is demonstrated. Only after genuine authorized stages are available may D2 proceed through Forecast/Valuation/Decision/Publication, complete `IIOS_RUN_RECEIPT`, and independent replay. No formal admission, Host acceptance, Decision, Publication, receipt or execution authority is currently claimed.
**Pass criteria:** all seven required field groups are individually source/PIT/use-qualified; unchanged Core/PIT reports PASS; independent review is resolved; historical diagnostics remain unchanged. The current candidate is a bounded advance, not final C2 admission.

Machine/human audit records: `docs/iios/ROUTE_A_C2_SOURCE_ADJUDICATION_AUDIT_20261011.md` and `evidence/real_cases/RC-CN-A-002001-20261009/C2_MARKET_PRICE_SOURCE_REVIEW_20261011.json`. Normative operator-attestation policy: `docs/iios/OPERATOR_MARKET_PRICE_ATTESTATION_v0.1.md`.

### Batch D1-A — production Host acceptance runbook and evidence gate

**Status:** RUNBOOK CANONICAL; REAL HOST ACCEPTANCE OPEN.

- [D1-A runbook](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/docs/iios/D1_A_PRODUCTION_HOST_ACCEPTANCE_RUNBOOK_20261011.md) defines no-paid-key local Ollama setup, protected environment config, the loopback-only GET probe at `tools/iios_d1a_host_liveness_probe_v01.py`, protected Host request, Ed25519 receipt verification, durable persistence and clean replay. The probe utility is code-only until run on the operator's host; it never invokes the provider or claims acceptance. Host config/liveness may run in parallel, but the real canonical case invocation must wait for formal C1 Evidence/PIT admission.
- The sanitized machine status at `evidence/real_cases/RC-CN-A-605016-20261009/D1_A_HOST_ACCEPTANCE_STATUS_20261011.json` explicitly keeps host process, provider invocation, signed receipts, durable replay, canonical run and acceptance false. No real operator-host evidence was available in this task session.
- A local `--check-config`, CI PASS, `healthz` or `readyz` alone cannot close D1-A. The host must invoke an authorized provider-backed factory. A local Ollama-compatible endpoint can avoid paid API keys under `SELF_HOSTED` + `AUTH_MODE=NONE` on loopback; the private Ed25519 signing key stays in the operator environment.
- **Parallel preparation status:** the local setup helper, protected environment workflow and loopback-only probe are available and their contracts are covered in CI. They have not been run in the operator environment in this session. Operator-run configuration/model checks and the sanitized probe report must be recorded locally; never paste the environment file, private keys or bearer token into GitHub/chat.
- Avoid a separate provider smoke run when the same exact 605016 host-origin run can satisfy the applicable D1-A provider/receipt evidence and D1 end-to-end acceptance. Run separate probes only for criteria not covered by the canonical run; always record each gate's own result independently.

### Batch D1 — one real canonical 605016 run

**Status:** BLOCKED on formal C1 / 605016 Evidence/PIT admission, production Host acceptance and authorized semantic producer lineage. C1 candidate validation alone is insufficient. Host configuration and liveness can proceed in parallel, but the real canonical 605016 request/provider run cannot be accepted until signed C1 Evidence/PIT admission is complete.

**Safety predecessor completed:** PR [#342](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/342) merged at `a496b82b8cfbc2256a9affd3337f97fce305d217`, adding a canonical fail-closed guard that rejects the unverified manual-Web producer from formal semantic admission. Next provision/deploy the actual Host, authorized producer key/receipt path and durable admission store; do not count test-fixture or manual Web response hashes as provider-origin proof.

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

Apply the same full run/receipt/replay gates as D1. For the date-only case cutoff `2026-10-09`, source price must be the latest completed session before the cutoff: `2026-10-08`. Do not use the October 9 close or inherit the older PILOT-02 cutoff of October 7 / its September 30 price receipt.

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

## 5. Earlier immediate execution order (superseded by ACTIVE EXECUTION ORDER above)

1. **C0 decision:** default to LOCAL_SINGLE_USER/local-first while reusing the existing canonical Host/CLI, Orchestrator, runtime factory, Store, report/QA and receipt/replay contracts. Do not rewrite components or add UI unless the actual product-entry pilot demonstrates a gap. The generic ChatGPT Free Web handoff remains NON-CANONICAL for formal decisions.
2. **Parallel, safe work:** (a) retain C1's completed local/source-vintage candidate; do not repeat ingestion. Resolve the formal admission signer/authority contract and allowed-use basis for the SSE closing-price source before creating a signed admission; (b) obtain the required independent human/external sign-off for C2's 13 facts and narrow private-use boundary while keeping operator-attested price distinct; (c) prepare a genuine Host only if/when a compliant producer path is available, and run the GET-only Host probe only when a deployment exists; neither activity is a prerequisite for deterministic scenario analysis or signer/rights review. These are parallel tasks; a local config/health check is diagnostic only.
3. **D1-A + D1:** only after C1 formal admission, execute one real 605016 host-origin canonical run. Use the same run for overlapping production Host evidence and end-to-end acceptance where possible, and separately evaluate each gate. Require genuine authorized producer receipts, seven-group admission, Forecast/Valuation lineage, Decision/Publication/report QA, complete `IIOS_RUN_RECEIPT`, and a clean replay.
4. **D2:** after C2 independent fact/use review and formal seven-group Evidence/PIT admission, execute one real 002001 canonical run with case-bound Forecast/Valuation inputs and the same full receipt/replay gates. Do not repeat price web search; do not upgrade `OPERATOR_ATTESTED_MARKET_DATA` into `SOURCE_VINTAGE_VERIFIED`.
5. **Final acceptance:** run fresh clean-room red-team against the actual supported local entry and real positive path; test bypasses, wrong case/cutoff, evidence tampering, missing/fixture-only outputs and replay mutation. Retain the canonical PILOT requirements including a fresh user-selected candidate and operator usability acceptance. Keep P0-LLM-001/P0-LLM-004 OPEN until their exact production criteria pass.
