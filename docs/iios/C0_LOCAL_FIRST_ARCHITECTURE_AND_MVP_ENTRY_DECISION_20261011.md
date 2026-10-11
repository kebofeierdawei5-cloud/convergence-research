# C0 — Local-First Architecture and MVP Entry Decision

- Decision date: 2026-10-11
- Record class: architecture/product-scope decision; documentation-only
- Decision baseline: `main@3684689fab0376473ac6f514c71b97fbb450363f`
- State authority: `docs/PROJECT_STATE_INDEX.md`
- Status in this branch: proposed for canonical promotion by PR; it does not claim runtime or MVP acceptance
- Scope: reconcile product-effectiveness audit #310, local-single-user red-team #311, and Local-first proposal #312 with the existing canonical batch/PILOT acceptance framework.

## 1. Decision

**Adopt LOCAL_SINGLE_USER / local-first as the default MVP deployment profile. Reuse the existing canonical Host, Orchestrator, runtime factory, admission contracts, Store, publication/report pipeline and Run Receipt/replay machinery. Do not create a second architecture or rewrite these components without a demonstrated gap.**

For the initial formal execution profile:
- the supported entry is the operator-controlled local canonical CLI or first-party loopback Host, which must route into the existing Canonical Research Orchestrator;
- a loopback Host is acceptable as a local deployment mechanism; a remote/cloud deployment is not a prerequisite for the personal single-user MVP;
- use the existing provider-neutral runtime with a configured, operator-controlled local Ollama-compatible model when it meets the signed-receipt and producer-lineage contracts; no paid model API key is a product prerequisite;
- retain the existing first-party Host, factory and signed-provider path. This decision does not retire, delete or weaken them;
- defer any remote/multi-user profile, browser extension, new UI, database replacement and parallel orchestrator until an observed user need and a narrow acceptance case justify them.

This is a deployment/profile choice, not an investment-semantic change. All existing PIT, provenance, UNKNOWN, scope isolation, fail-closed authorization, append-only history, human approval, no-auto-execution and replay requirements remain unchanged.

## 2. Producer governance decision

**The present manual ChatGPT Free Web handoff remains NON-CANONICAL only. It is not an authorized formal semantic producer under the current frozen B0 contract.**

Saved-response hashes show byte integrity, not OpenAI/model origin. The merged fail-closed policy from PR #342 remains in force. No request-intent or thesis-semantic response copied from the ordinary ChatGPT Web UI may be promoted into formal semantic admission by a relabelled producer ID, operator assertion, hash, or local handoff receipt.

The default formal path is therefore a genuinely invoked, configured local/provider-backed runtime whose producer identity, model/version, stage/input/output lineage and signed receipts are verified by the existing contracts. A local runtime's attestation proves only the configured local runtime path and its recorded bytes; it must not be described as independent certification of model quality or investment validity.

No paid provider endpoint is required if the selected local model/provider satisfies the existing runtime and receipt contracts. If it does not, the run stays BLOCKED; there is no silent fallback to manual Web output.

## 3. User-entry contract

A formal IIOS result can be presented as canonical only if it is produced by the supported entry and bound to:
- a single Research Case, market/security identity and explicit cutoff;
- a durable Run Envelope and ordered stage receipts;
- admitted Evidence/PIT and the applicable signed/authorized producer and upstream Forecast/Valuation records;
- formal Decision Admission, Decision Revision, Machine Publication, human-readable report/QA and a complete `IIOS_RUN_RECEIPT`;
- a clean replay from persisted frozen inputs.

A generic ChatGPT conversation that merely receives the instruction “use IIOS” is not evidence that the repository runtime was invoked. It must return an explicitly non-canonical explanation or BLOCKED state unless a supported connector/host actually invokes the canonical entry and returns the canonical artifact references.

The MVP must make it clear whether the user entered through the local canonical CLI/Host or through an unconnected chat surface. Do not imply that this C0 decision itself wires this conversation to the local runtime.

## 4. AI research rounds

The proposed price-blind Round A / price-aware Round B workflow is **not treated as already implemented and is not frozen as an irreversible architecture rule**.

Before production acceptance, use the existing source/test capability map to verify whether current typed artifacts and admission boundaries fully express the required stages:
- price-blind Reality, Quality, Thesis, Value Drivers and Independent Forecast;
- price-aware Valuation, MIE, Expectation Gap, Risk, Positioning and AI Decision Proposal.

If a concrete gap is demonstrated, implement only the missing versioned artifact/schema/lineage contract with adversarial tests. Keep current price out of independent-forecast inputs. Measure handoff count, failure/retry rate, missing-field rate and manual edit rate before deciding whether two rounds are the best permanent workflow.

## 5. Scope and non-goals

In scope:
- local single-user product entry and execution profile;
- reuse of canonical components and one durable workspace/admission/report/replay path;
- one real company vertical slice through the supported entry;
- source/PIT, producer lineage, human approval and replay acceptance.

Out of scope:
- new valuation or prediction model families;
- CSI800/A02 as a company-level MVP dependency;
- automatic stock selection, scheduled screening, order execution or broker integration;
- remote SaaS/multi-user deployment;
- browser automation or automatic extraction of ChatGPT Web responses;
- weakening source reuse, timestamp, signature, producer authenticity or PIT contracts.

## 6. Execution order and dependencies

1. **C1 / 605016 formal Evidence/PIT admission:** use the existing private/source-vintage successor; do not repeat ingest. The conservative `known_at` upper bound and unverified exact first-public timestamp must remain visible until resolved by the applicable admission contract.
2. **C2 / 002001 independent fact/use review:** proceed in parallel with C1 and local Host preparation. The current operator-attested price class remains distinct from source-vintage-verified market data. Keep C2 blocked if allowed-use or source/PIT questions remain unresolved; do not restart broad price web-search without a new reason.
3. **Local Host preparation (D1-A prep):** configuration, protected environment, local model readiness and loopback health checks may proceed in parallel. These are preparation evidence only, not production acceptance.
4. **D1-A + D1 shared live acceptance:** after C1 formal admission and runtime prerequisites pass, run one actual host-origin 605016 canonical request. Use the same exact run to gather overlapping Host evidence and complete D1 where possible, avoiding a redundant provider smoke run. Close each gate only to the extent its own acceptance evidence passes.
5. **D2 / 002001:** only after independent C2 fact/use review and formal seven-group Evidence/PIT admission, then complete the same canonical pipeline and replay.
6. **Final acceptance:** execute the required clean-room red-team, negative bypass tests, actual supported-user-entry test and the existing PILOT acceptance requirements. Preserve human approval and keep automatic execution disabled.

The real 605016 run cannot begin while C1 remains only a local candidate. A successful health check, provider callback preflight, component CI or signed receipt in isolation cannot close D1-A/D1 or the MVP.

## 7. Exact acceptance gates

C0 is accepted as a decision record only when this ADR and the updated plan/state index are merged from an exact-head PR. It does **not** close the implementation gates below.

MVP remains NOT ACCEPTED until all applicable items pass:
- supported user entry demonstrably invokes the canonical Orchestrator;
- all seven required Evidence/PIT groups are admitted for each accepted real case;
- producer identity/assurance and case/cutoff/stage lineage are verified;
- Forecast, Valuation/MIE, Risk/Position, Decision and Publication use admitted, bound upstream records;
- human-readable report and machine artifacts agree and pass deterministic QA;
- complete Run Receipt persists and independently replays from frozen inputs;
- independent clean-room red-team passes;
- existing PILOT requirements are retained: materially different companies, at least one fresh user-selected candidate, comprehensible report, lifecycle continuity, no unresolved P0, no evidence substitution and no automatic execution;
- operator confirms actual entry usability. Historical component/PILOT PASS is not substituted for new product-surface acceptance.

## 8. State and non-claims

This decision does not:
- mark P0-LLM-001 or P0-LLM-004 closed;
- declare the current ChatGPT Free Web handoff canonical;
- claim local Ollama or Host has been deployed/run in the operator environment;
- grant formal Evidence/PIT admission to C1 or C2;
- create a formal Decision, Publication, complete Run Receipt or execution authorization;
- establish forecast predictiveness, valuation quality or investment performance.

Every implementation batch must start from the then-current canonical main, update the single State Index after merge, and preserve exact-head validation plus historical diagnostics.
