# Action A — Capability Map and ChatGPT Free Web Governance Decision

- Date: 2026-10-11
- Status: **ACTION A AUDIT / GOVERNANCE RECOMMENDATION**. Under A0, this branch remains DIAGNOSTIC until merged to `main`; once merged, this is the canonical audit record, not a B0 amendment or a second State Index.
- Canonical inspection baseline: `main` at `0e6ab65764298afa1fe723ad0a16b8683eb93276`
- Scope: source/test capability map and producer-governance decision only.
- No runtime code, economic semantics, test definition, source evidence, or user-private data was changed by this audit.

## 1. Executive decision

**Recommendation: NO-GO for formal/canonical semantic admission from the current manual ChatGPT Free Web route under the frozen B0 contract. GO only for explicitly NON-CANONICAL operator-assisted research until a versioned governance successor/amendment and a hard runtime enforcement gate are approved.**

This is not a judgment that ChatGPT's reasoning is necessarily poor. It is a boundary decision about what the system can prove and what the frozen policy currently authorizes.

The existing route stores the exact prompt and imported response bytes, binds them to task/run/request/case/cutoff/stage, creates a local hash receipt, and explicitly records `provider_origin_verified=false`. The hashes demonstrate integrity of the saved bytes; they do not authenticate that OpenAI generated them. The operator receipt is not embedded as a formal signed-provider attestation in the complete `IIOS_RUN_RECEIPT`. The current implementation registers the manual Web producer as active, while the generic semantic-admission contract validates registration, policy/version and local receipt/hash integrity without independently verifying service-side origin. Therefore, the code-level presence of a registered producer must not be mistaken for a governance authorization of this assurance level.

The frozen [B0 LLM Governance Boundary](B0_LLM_CANONICAL_EXECUTION_GOVERNANCE_FREEZE_20261007.md) requires an authorized producer boundary and semantic provenance bound to producer, version/policy, stage and input/output lineage. It also explicitly rejects treating arbitrary external JSON as canonical semantic evidence. No canonical B0 successor authorizing the weaker operator-asserted assurance tier was found on the inspected mainline. Until such a successor exists, current formal admission should fail closed for this channel.

**Implementation mismatch found:** this NO-GO is not yet enforced as a hard runtime denial. `build_chatgpt_chat_runtime` currently registers the manual producer as active, and generic local semantic admission does not consume the handoff's `provider_origin_verified=false` as an authorization gate. The current source inspection therefore does not prove the adapter is technically prevented from reaching formal semantic admission when its other inputs are supplied. Treat this as a governance/runtime enforcement gap: do not select this adapter for formal decisions; the next narrow implementation PR must fail closed as `BLOCKED` / `NON_CANONICAL` before formal semantic admission, and add a regression proving that behavior. This must not be “fixed” by weakening or changing the frozen producer-authenticity contract.

This recommendation does **not** change or close P0-LLM-001 / P0-LLM-004; both remain OPEN. It does not establish investment-strategy predictive validity, source admission, local Mac persistence, production-host acceptance, or a completed real-company run.

## 2. Canonical sources inspected

| Source | Exact inspected revision | What it governs / shows |
|---|---|---|
| `docs/PROJECT_STATE_INDEX.md` | blob `b84cf01a20f331adcd93a041b15958248bc4ecd5` on `0e6ab65764298afa1fe723ad0a16b8683eb93276` | Only canonical Current State Index; P0-LLM-001/004 open; production Host acceptance and source-by-source Evidence/PIT admission remain open; 605016 local private persistence remains unverified. |
| `AGENTS.md` | blob `245b6ffc195470a1eb92505864ddab8d3aab3a31` | Task contract, narrow-PR discipline, immutable history, no direct LLM writes to authoritative state. |
| `docs/iios/B0_LLM_CANONICAL_EXECUTION_GOVERNANCE_FREEZE_20261007.md` | blob `f1ddf1ac1cc332e36e0de16432d34836df1b476b` | Frozen P0-LLM-001..004 boundary and producer-authenticity / receipt requirements. |
| `docs/iios/P0_CHATGPT_FREE_WEB_RUNTIME_20261010.md` | blob `1098868de38e3b1c67d8b5cb0403eda5cbc11a3c` | Describes the Web route as implementation candidate, not production acceptance; origin is explicitly unverified. |
| `iios_mvp/chatgpt_chat_runtime_v01.py` | blob `fda486e50bea3e36f0e2e453403d8d615940a160` | Registers request interpreter and thesis-semantic producer and composes the canonical runtime. |
| `iios_mvp/chatgpt_chat_handoff_v01.py` | blob `f17133bff5476d093ae500cc69d44fd37a0180ef` | Prompt/response import, strict JSON, immutable writes, task binding, receipt hash, and explicit unverified-origin semantics. |
| `iios_mvp/semantic_producer_admission_v01.py` | blob `11b532a7bf0a654c3b6fedb510526e589ffc0cb3` | Generic admission binds registered producer/version/policy and local producer receipt; it is not, on its own, a service-origin attestation. |
| `iios_mvp/external_semantic_provider_admission_v01.py` | blob `645316fefdd5e24486970360256eff7d1d62546a` | Separate Ed25519 signed-receipt verification path; its assurance cannot be inherited by the manual Web route. |

## 3. Capability map: files, entrypoints, tests and limits

The classifications below distinguish **code present** from **production acceptance**. Test names and assertions are source-inspection evidence; no test suite was freshly executed as part of this documentation-only audit.

| Capability | Implementation / entrypoint | Relevant tests or acceptance records | Classification and proven boundary |
|---|---|---|---|
| Canonical state / scope | `docs/PROJECT_STATE_INDEX.md`, `AGENTS.md`, `docs/iios/A0_STATE_AUTHORITY_POLICY_v0.1.md` | `tests/test_state_authority.py`, `tests/test_state_authority_index.py`, `tests/test_c0_state_authority.py` | **ACCEPTED governance boundary.** Main + Project State Index are authoritative. Unmerged PR #312 is not policy. |
| User request and supported CLI entry | `iios_mvp/cli.py::cmd_canonical_run`; `_resolve_canonical_runtime`; `canonical-run` command | `tests/test_canonical_cli_host_integration.py::test_cli_host_routes_natural_language_request_through_canonical_run`; `tests/test_p0_canonical_entry_incident_reproduction.py` | **IMPLEMENTED, bounded control-plane coverage.** The integration test uses an explicit TEST_ONLY runtime and asserts that the command does not itself create the complete Run Receipt. It does not identify or accept a deployed production product host. |
| Orchestration and stage order | `iios_mvp/canonical_research_orchestrator.py::CanonicalResearchOrchestrator`; persisted authority in `canonical_run_authority_v01.py::PersistedCanonicalResearchOrchestrator` | `tests/test_canonical_research_orchestrator.py`; `tests/test_b2e_nl_semantic_decision_e2e.py` | **IMPLEMENTED, bounded tests.** Stage order, identity, producer type and receipt chains are validated. In-memory orchestrator behavior or fixture E2E alone is not proof of a real host-origin run. |
| Trusted runtime factory / binding | `iios_mvp/canonical_runtime_registry_v01.py`; `canonical_runtime_factory_v01.py`; `canonical_runtime_preflight_v01.py`; `cli.py::_resolve_canonical_runtime` | `tests/test_canonical_runtime_factory_v01.py`; `tests/test_canonical_runtime_preflight_v01.py`; `tests/test_canonical_cli_host_integration.py`; `tests/independent_redteam_runtime_preflight.py` | **IMPLEMENTED, bounded contract coverage.** Factory and callback contracts exist. The preflight explicitly sets Evidence/PIT and semantic admission unchecked, and decision/publication/full receipt creation false. Passing it is not production acceptance. |
| Manual ChatGPT Web handoff | `iios_mvp/chatgpt_chat_runtime_v01.py::build_chatgpt_chat_runtime`; `chatgpt_chat_handoff_v01.py::prepare_chatgpt_handoff`, `import_chatgpt_response`, `ChatGPTChatJsonClient` | `tests/test_chatgpt_chat_operator_runtime.py` (immutable prompts; strict JSON; task/case/run/stage binding; mismatched prompt; receipt tampering; no API key requirement) | **IMPLEMENTED, local contract tests only.** The code supports operator copy/paste for request-intent and thesis-semantic callbacks. Tests use supplied response fixtures; they do not call ChatGPT, independently identify the model, or authenticate the service-side origin. `provider_origin_verified` must remain false. |
| Semantic producer admission | `iios_mvp/semantic_producer_admission_v01.py`; signed route in `external_semantic_provider_admission_v01.py` | `tests/test_b2_semantic_producer_admission.py`; `tests/independent_redteam_b2_semantic_producer.py`; signed-provider contracts in `tests/test_canonical_runtime_factory_v01.py` | **IMPLEMENTED, distinct assurance paths.** Generic producer receipts prove local payload/lineage integrity under a registered producer policy; Ed25519 verification is a separate path. No inspected contract promotes an operator assertion to a cryptographically verified Web origin. |
| Official evidence / PIT | `iios_mvp/canonical_evidence_admission_v01.py`; `evidence_root_admission.py`; `tools/company_evidence_intake.py`; `tools/verify_company_evidence_intake.py` | `tests/test_company_evidence_intake.py`; `tests/independent_redteam_company_evidence_intake.py`; canonical state record for `RC-CN-A-605016-20261009` | **IMPLEMENTED, source- and case-dependent.** Validation and private-ingest tooling exist. Main records the latest 605016 quote path as PASS_EPHEMERAL_B2, not durable private admission; local Mac persistence and the production admission chain remain pending. |
| Current price / independent forecast / valuation inputs | `iios_mvp/canonical_current_price.py`; `canonical_independent_forecast.py`; `valuation.py`; resolvers composed by the ChatGPT runtime | `tests/test_canonical_current_price.py`; `tests/test_canonical_independent_forecast.py`; `tests/test_b04_forecast_valuation_return_lineage.py`; `tests/test_p2_1_canonical_price_response.py` | **IMPLEMENTED with separate admission gates.** The manual Web runtime resolves prior admitted price, Forecast and Valuation records; the manual callbacks do not create official market-price evidence or independently admitted Forecast/Valuation outputs. |
| Decision, approval, publication and report QA | `iios_mvp/decision_admission.py`; `decision_lifecycle_production.py`; `human_report.py`; `investor_review_report_v02.py`; CLI `approve` / `publish` / report commands | `tests/test_decision_lifecycle_production.py`; `tests/test_investor_review_report_v02.py`; `tests/test_human_report.py`; `tests/test_b2e_nl_semantic_decision_e2e.py` | **IMPLEMENTED, lifecycle tests bounded by their inputs.** Deterministic gates and report QA exist. Preconstructed/synthetic inputs do not prove real semantic reasoning or production admission. Human approval remains mandatory; automatic trading remains disabled. |
| Complete Run Receipt / replay | `iios_mvp/canonical_run_authority_v01.py::validate_complete_run_receipt`; `iios_mvp/validation_replay.py`; `cli.py::cmd_replay` | `tests/test_validation_replay.py`; `tests/test_b2e_nl_semantic_decision_e2e.py`; `tools/pilot04_clean_replay_verify.py`; `docs/iios/PILOT-04_CLEAN_REPLAY_20261007.md` | **IMPLEMENTED, fixture/replay-specific acceptance.** A complete receipt can be validated and replayed for an accepted input package. Main explicitly says a real production-host chain from official source/PIT through authentic semantics, report and full receipt replay has not been accepted. |
| Local single-user launcher / durable privacy | `tools/Launch_IIOS_Private_605016_B2_Ingest.command`; `tools/iios_private_605016_b2_ingest_v01.py`; existing Store and filesystem artifacts | `tests/test_prepare_iios_local_ollama_runtime.py`; private-ingest contract tests referenced by the canonical index | **PARTIAL / OPERATING-ENVIRONMENT ACCEPTANCE OPEN.** The actual operator Mac persistence has not been observed. GitHub CI artifacts and hashes are not a substitute for durable local persistence or private-directory verification. |

## 4. Architecture-plan claims checked against present capability

1. **LOCAL_SINGLE_USER is a valid direction, not yet a proven complete product.** The canonical CLI, filesystem admission resolvers, Store, reports and replay machinery exist. A separate deployed user-facing host wired to a real runtime and a complete real-company run remains unaccepted.
2. **The proposed two-round AI interaction is not implemented by the current Free Web adapter.** Present code supports two callbacks named request-intent and thesis-semantic. It does not yet implement the proposed Round A (price-blind Reality/Quality/Thesis/Value Drivers/Independent Forecast package) plus Round B (price-aware Valuation/MIE/Expectation Gap/Risk/Position/Decision proposal) as two validated, separately admitted artifact bundles. Do not describe this as implemented or tested.
3. **The ChatGPT Web route does not replace evidence acquisition, PIT, Forecast or Valuation admission.** It relies on previously staged bundles and admitted resolvers; required absence must continue to block.
4. **Existing PILOT / CI PASS has bounded meaning.** It supports the control contracts and the fixtures it actually exercised. It does not establish model-origin authenticity, model reasoning quality, production-host conformance, or predictive investment validity.
5. **No paid endpoint is required for the manual callback path, but “free” is not the same as production-authorized.** It is a human-operated channel without an API guarantee or a signed response attestation.

## 5. Governance Go / No-Go matrix

| Use case | Decision now | Conditions / boundary |
|---|---|---|
| Copy/paste ChatGPT Free Web for exploratory notes, clearly outside canonical IIOS artifacts | **GO — NON-CANONICAL ONLY** | Do not call the result admitted, approved, independently verified, or a canonical IIOS decision. Keep private data out of public GitHub. |
| Use the current operator Web response as a formal semantic producer for a canonical investment run | **NO-GO** | Frozen B0 does not yet authorize the operator-asserted source-assurance level; the route records origin unverified and its local receipt is not a signed service-origin attestation. |
| Claim that hash integrity proves OpenAI/model origin | **NO-GO** | The code explicitly declares the contrary. |
| Claim the proposed Round A / Round B flow is implemented | **NO-GO** | The implemented callbacks are request-intent and thesis-semantic only. |
| Close P0-LLM-001 / P0-LLM-004 or claim MVP acceptance from these tests | **NO-GO** | Both P0s remain OPEN in the canonical State Index; real host-origin evidence/semantic chain, complete receipt replay and independent acceptance remain unproven. |

## 6. Required follow-up after this Action A decision

1. Merge/review this map and the State Index pointer before treating Action A as accepted. Do not merge PR #312 merely to make the plan “canonical”; review it separately.
2. Before any production use of the manual Web runtime, add an explicit fail-closed policy gate so an unapproved assurance tier cannot reach formal semantic admission. This is a narrow safety follow-up, not a reason to rewrite the Orchestrator.
3. If the intended product requires formal canonical admission from manual Web outputs, propose a versioned B0 successor/amendment that defines the assurance class, admissible artifact kinds, prohibited claims, operator attestation, immutable handoff receipt integration into the complete Run Receipt, replay behavior, adversarial cases, and explicit human approval. That amendment must be independently reviewed and must not describe operator assertion as cryptographic verification.
4. If that amendment is not approved, keep the manual Web output NON-CANONICAL and use an already-governed producer path for any formal semantic admission. Do not silently downgrade the existing producer-authenticity requirement.
5. Action B may verify the local intake/persistence path after Action A is accepted. Action C may prepare only the non-canonical workflow unless the formal producer governance gate changes. Action D remains blocked until real evidence/PIT, approved producer lineage, Forecast/Valuation, Decision, report, complete Run Receipt and independent replay gates all pass.

## 7. Acceptance record and non-claims

Action A's audit deliverable is the capability map above plus the recommendation matrix. It is a source-and-test inspection, not a newly executed test suite. CI remains responsible for syntax/diff/policy-contract validation of this PR. No claim is made that current source acquisition succeeded during this audit.

- Runtime code changed: **NO**
- Economic semantics changed: **NO**
- Tests weakened: **NO**
- User/private evidence added to repository: **NO**
- P0-LLM-001 closed: **NO**
- P0-LLM-004 closed: **NO**
- ChatGPT Free Web formally authorized: **NO**
- Recommendation: **NO-GO for canonical Web semantic admission; GO only for non-canonical operator assistance.**

## 8. Follow-up hard gate at formal semantic admission — 2026-10-11

The original capability audit found that the manual ChatGPT Web producer remained active while its saved-response receipt explicitly set `provider_origin_verified=false`; the generic semantic admission boundary did not consume that false value. That finding prompted a narrow enforcement follow-up in PR for branch `feat/manual-web-semantic-fail-closed-guard-20261011`.

The candidate change adds a deny gate at `admit_semantic_artifact`, the canonical semantic admission boundary. It rejects (a) `iios-chatgpt-web-semantic-producer` and (b) any renamed producer that retains the `IIOS-CHATGPT-WEB-OPERATOR-POLICY-` policy namespace, returning `NON_CANONICAL` because provider origin is unverified under frozen B0. Regression tests construct otherwise correctly hashed artifacts and producer receipts and verify that both the original identity and a renamed identity using the same unapproved policy are rejected before canonical admission.

This does not authenticate the origin or create an alternative formal assurance class. It preserves the current policy: the manual Web route may be used for exploratory/non-canonical operator assistance, but it cannot feed formal semantic admission. The current request-intent / thesis-semantic handoff still does not implement the proposed two-round research flow. P0-LLM-001/P0-LLM-004, production Host acceptance, complete Run Receipt, and independent D1/D2 validation remain open.

**Acceptance boundary:** only after this guard's exact-head contract, Investment Core CI, State Hygiene, C0 governance, B2 semantic admission and independent red-team checks pass should its state be promoted as canonical. The original Action A source-inspection record remains historical evidence of the gap found before this follow-up.
