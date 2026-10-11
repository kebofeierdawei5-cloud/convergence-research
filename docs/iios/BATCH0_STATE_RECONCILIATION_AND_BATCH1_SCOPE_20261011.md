# Batch 0 — Narrow state reconciliation and execution order

- Date: 2026-10-11
- Record class: canonical state-reconciliation record after this PR is accepted
- Baseline: canonical `main@f632169f4da60a19f194b0abba109600c67e51f3`
- Scope: reconcile the current status and next execution order only; no Investment Core economic semantics are changed.

## 1. Adjudication

The canonical product is **not yet accepted as a production-ready formal investment-decision system**. Existing Investment Core, decision lifecycle, publication/report, QA, and replay components remain reusable; their historic PASS applies only to each documented acceptance scope.

The immediately useful product gap is now narrower than rebuilding the system: the operator has successfully persisted private Path A prices, but the repository does not yet expose one deterministic local function that consumes that normalized private record and emits an immutable, reproducible *scenario-only* JSON analysis, human-readable report, and replay-verifiable receipt. Batch 1 fills that exact gap. It must not create Evidence/PIT admission, a formal Forecast/Valuation admission, Decision, Machine Publication, formal Run Receipt, or execution permission.

## 2. Exact current-state findings

1. Path A private input persistence was actually reported successful by the operator. That is operator-host evidence, not an assistant-claimed Mac execution.
2. The canonical Path A contract explicitly preserves `OPERATOR_ATTESTED_MARKET_DATA`, analysis-only resolver permission, false source-origin/source-vintage/source-use-rights flags, and no canonical price/decision authority.
3. C1 / 605016 remains a private Core/PIT candidate; formal signed admission and SSE closing-price use permission are open. Exact first-public time is not to be fabricated.
4. C2 / 002001 has 13 fact locators/time-bound checks but still lacks required independent human/external sign-off and a resolved source-use scope. A local second-pass or CI pass is not that signature or a legal opinion.
5. The actual production Host, trusted production semantic producer, formal upstream admissions and complete Run Receipt/replay remain unaccepted. The ordinary ChatGPT Free Web handoff is NON-CANONICAL for formal semantic admission under frozen governance.
6. Neither deterministic scenario work nor signature/rights review requires installing a local LLM, Ollama, a paid API key, or a provider API.

## 3. CI anomaly disposition

The workflow run `38137977103` at `main@f632169f4da60a19f194b0abba109600c67e51f3` reports conclusion `failure`, event `push`, and the Jobs API returns zero jobs. The workflow file at this baseline declares `pull_request` and `workflow_dispatch`, not an explicit `push` trigger.

This is classified as **UNCLASSIFIED ZERO-JOB WORKFLOW FAILURE**, not as evidence that a test step failed and not as a PASS. Batch 0 makes the trigger explicit for pushes to `main` and retains the pull-request path filter. The next exact relevant run must contain an actual job and step result. If it still returns zero jobs, investigate repository/workflow execution configuration; do not infer application-code failure or success.

## 4. Active execution order after Batch 0

### Batch 1 — Path A deterministic private scenario runner (next)

Reuse the existing normalized private price record and existing case-linked scenario assumptions; do not reacquire quotes. Implement deterministic computation, report rendering, private immutable outputs, content-addressed analysis identity, and replay verification. Both existing cases must run, but all case fundamentals and assumptions remain labelled according to their real provenance. The runner is scenario-only.

Required output:
- machine-readable analysis record with input file hash, runner/profile version, case/symbol/date/price class, explicit assumptions and assumption provenance;
- Chinese investor-facing Markdown explaining model values, weighted value, expected total and annualized return, hurdle entry-price ceiling, case-specific bear-loss ceiling and binding price;
- private integrity receipt binding input, analysis and Markdown hashes;
- deterministic replay command/function that re-computes the same semantic output;
- fail-closed behavior for wrong schema, unapproved/unknown scenario profile, malformed probabilities, duplicate/missing price matches, bad hashes, public-repository paths and unsafe/overwriting output paths.

### Parallel lane — C1 / C2 signature and source-use gates

- C1: keep its admitted-candidate bytes pinned; do not rerun ingestion. A trusted signer cannot override missing legal/use permission. Written exchange permission or a documented applicable permission basis must precede an ADMIT signature for the SSE price.
- C2: retain the 13 reviewed fact locators and explicit `PUBLIC_ACCESS_REUSE_UNKNOWN` statuses. A distinct authorized independent reviewer must sign the allowed internal fact-level scope; any unresolved source rights remain blocking.
- Keep trust registry empty until a specific signer identity, role, scope, validity period, key custody, and owner authorization have been approved. Creating a keypair or signing code does not establish trust by itself.
- Avoid repeated broad price searches. Use only narrowly justified rights/source actions; preserve private price data outside GitHub.

### Batch 2 — scenario usability and analytical integrity

After Batch 1 passes: validate reports for both cases with the operator; verify all calculations independently; add sensitivity tests for scenario EPS/value, probability changes, horizon and entry-price constraints. Fix only evidenced usability defects. No new valuation model families.

### Formal path — gated, not the immediate dependency of Batch 1

Proceed to C1/C2 formal Evidence/PIT admission and production Host acceptance only when their own evidence, source-use and producer requirements are met. Then run one real company through the existing canonical Orchestrator, formal Forecast/Valuation/Risk/Position/Decision Admission, human approval boundary, Publication/report QA, complete `IIOS_RUN_RECEIPT`, and independent replay. The first actual user-host run must not use fixtures, operator-attested quote as formal price, or manual Web output as a formal model-origin receipt.

## 5. Batch 1 acceptance contract

- Same exact private input bytes + same versioned scenario profile produce identical analysis semantics and hashes; repeated runs do not overwrite prior files.
- Run only outside the public checkout. Private numeric prices, source labels, raw source bytes, holdings, secrets, prompts and outputs must not be committed or uploaded as workflow artifacts.
- A public/sanitized receipt may identify case, symbol, date, input/output hash and scenario-only status, but must not expose price numbers or operator source labels.
- All formal authority flags remain false. Output explicitly says the price-only overlay does not revalidate the whole company evidence set at the overlay cutoff.
- Dedicated tests prove both positive deterministic output and negative tampering/permission/scope controls.
- Exact-head CI has real job results, including this runner's dedicated tests; a zero-job check is not acceptance.
- The one authoritative `docs/PROJECT_STATE_INDEX.md` and `STATUS.md` are updated only through the accepted canonical PR.

## 6. Explicit out of scope

No stock screening, CSI800/A02 dependency, data warehouse, external paid API, local model installation, second Orchestrator/store, new valuation families, canonical market-price admission, formal Decision, scheduler, portfolio optimizer or automatic trading.
