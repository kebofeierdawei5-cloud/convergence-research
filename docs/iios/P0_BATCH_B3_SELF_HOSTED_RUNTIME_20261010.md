# P0 Batch B3 — Free-First Self-Hosted Semantic Runtime — 2026-10-10

**Status:** implementation candidate; production deployment and real-company acceptance remain OPEN.  
**Base:** main@bfd888447cab2c455b9b0800576dc7050a8a709a  
**Purpose:** supply a genuine local-model callback without making a paid provider endpoint or API key a prerequisite, while preserving the canonical fail-closed boundaries.

## What the implementation adds

- A loopback-only OpenAI Responses-compatible client. The configured endpoint must be HTTP on loopback and end with /v1/responses; URL credentials, query strings, fragments, redirects and non-loopback HTTP are rejected. Requests use store=false and no Authorization header.
- A local-model request interpreter bound to the operator-staged case. Explicit disagreement on market, symbol, as-of date or current position blocks the run.
- A local-model THESIS_ASSESSMENT producer with exact fields and recursive decision-authority rejection. Its result stays untrusted until the existing deterministic IIOS semantic admission and Core projection succeed.
- A trusted runtime factory that supplies all eight canonical runtime bindings using the local model and existing filesystem resolvers. It checks exact case-bound current-price, forecast and valuation records before returning runtime bindings; it does not create or seed fallback data.
- Dedicated contract tests and a focused GitHub Actions workflow.

## Local inference service

The adapter implements the OpenAI Responses-compatible HTTP contract. Ollama's official compatibility documentation says POST /v1/responses was added in Ollama v0.13.3 and supports non-stateful Responses requests only:
https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx

Example local preparation (choose a model compatible with available memory and compute; pin the exact service/model versions for production acceptance):

    ollama --version
    ollama serve
    ollama pull qwen3:8b

Keep the model service bound to loopback. Do not expose the unauthenticated local inference endpoint to a LAN or public interface. The IIOS adapter rejects non-loopback endpoints, but the model service's own listener configuration still needs to be checked.

## Trusted host configuration

Configure these values in the actual operator service environment or secret store, not in Git:

- IIOS_HOST_BUNDLE_ROOT: directory containing reviewed <bundle_id>.json request bundles.
- IIOS_HOST_DATA_ROOT: root containing the Evidence/PIT manifest and raw-evidence bundle referenced by the operator-staged request bundle.
- IIOS_HOST_OUTPUT_ROOT: durable write-restricted run/artifact directory.
- IIOS_HOST_AUTH_TOKEN: host bearer secret of at least 32 characters.
- IIOS_HOST_RUNTIME_DATA_ROOT: root containing already-admitted canonical records, as described below.
- IIOS_CANONICAL_RUNTIME_FACTORY: iios_mvp.self_hosted_runtime_factory_v01:create_canonical_runtime.
- IIOS_SELF_HOSTED_RESPONSES_ENDPOINT: for example, http://127.0.0.1:11434/v1/responses.
- IIOS_SELF_HOSTED_MODEL: the exact local model identifier, for example qwen3:8b.
- IIOS_SELF_HOSTED_PROVIDER_ID and IIOS_SELF_HOSTED_PROVIDER_VERSION: operator-controlled, versioned identity values.
- IIOS_SELF_HOSTED_TIMEOUT_SECONDS: optional; defaults to 120 and must be 1–300 seconds.

No IIOS_LLM_PROVIDER_API_KEY is read or required by this adapter. Never place host bearer tokens, provider secrets or signing keys in the request bundle or repository.

Start the host from the repository's canonical working directory using:

    python -m iios_mvp.canonical_host_v01

The host's existing security contract remains in force: loopback-first HTTP listener, bearer authentication for submissions, only operator-staged bundle_id accepted in the request body, trusted paths/factory selected by process configuration, human approval required, automatic execution disabled. /readyz remains CONFIGURED_NOT_PRODUCTION_ACCEPTED; a successful health/readiness response is not production acceptance.

## Required canonical record layout

IIOS_HOST_RUNTIME_DATA_ROOT must be operator-controlled and contain admitted record bytes in this layout:

- current_price/current_price_admissions/*.price.json — exact-case current-price admission records.
- independent_forecast/independent_forecast_admissions/*.forecast.json — exact-case independent forecast admission records.
- investment_admissions/<sha256(admission_record_hash UTF-8)>.admission.json — canonical investment admission records whose own hash and case identity revalidate.
- valuation_outputs/<sha256(admission_record_hash UTF-8)>.valuation.json — canonical valuation outputs whose output hash matches an admitted VALUATION record.

These records must be created through existing admission producers and verification paths. Do not hand-edit an ADMITTED status or manufacture reference hashes to satisfy preflight. Records must match the exact case ID, market, symbol, company and cutoff. Missing, unknown, inconsistent or unadmitted records must block runtime creation or the run.

The staged request bundle must bind:
- the exact Research/Investment Case identity and cutoff;
- current_price_observation plus its canonical admission reference;
- canonical_forecast_ref and canonical_valuation_ref in return_gate;
- the exact source Evidence/PIT manifest path and raw-evidence root, both confined within IIOS_HOST_DATA_ROOT;
- a semantic_prompt containing reviewed, source-located excerpts needed for thesis interpretation, with fact/claim-to-source links. A hash list alone is not document content.

The ordinary B2 validator remains the source-of-truth for source origin, exact bytes, known_at/PIT, reuse/license status and seven mandatory field groups. A provider response cannot upgrade captured evidence to admitted evidence. Current 605016 source-origin/PIT admission remains a separate gate.

## Exact acceptance sequence

1. Install and pin the local inference service and selected model; record version/build provenance without secrets.
2. Provision the trusted host directories, bearer secret, runtime-data directory and reviewed case bundle.
3. Verify that every referenced current-price, forecast, valuation and upstream-admission record is genuinely admitted and case/cutoff bound.
4. Start the first-party host with the trusted runtime factory configured.
5. Submit exactly one real operator-selected company request through the HTTP Host, not directly through the CLI or kernel.
6. Verify genuine local-model request parsing and semantic callback provenance; replay the canonical Evidence/PIT, Forecast/Valuation, Decision, publication/report and complete IIOS_RUN_RECEIPT lineage from a clean process.
7. Run a fresh independent red-team over positive and negative paths before changing any production P0 status.

## Non-claims

- CI uses test doubles to verify parser, schema, trust-boundary and fail-closed control flow. It does not prove the local model process ran.
- This change does not deploy a host or local model, create case evidence, admit 605016, or claim an investment conclusion.
- The runtime factory intentionally blocks if trusted config or case-bound admitted records are absent.
- P0-LLM-001 / P0-LLM-004 remain OPEN until a host-origin real-company run completes all gates, report publication, complete receipt replay and independent red-team.
- Human approval remains mandatory. No order execution is enabled.
