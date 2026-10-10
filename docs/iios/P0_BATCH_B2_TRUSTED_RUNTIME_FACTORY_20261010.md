# P0 Batch B — Trusted Runtime Factory — 2026-10-10

**Implementation status:** factory and resolver contract code; production acceptance remains OPEN until real endpoint, durable store records and real admitted case pass.

## Entry contract

Set `IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime` in the trusted host process environment. The HTTP request cannot select a factory or override provider/store config.

The factory expects an operator-staged bundle with an `investment_case` carrying matching `case_id`, `market`, `symbol`, `company`, `as_of_date` and `cutoff_date`. It also requires a trusted `IIOS_CANONICAL_ADMISSION_ROOT` containing previously admitted canonical records.

## Provider config

Required existing provider-neutral variables:

- `IIOS_LLM_PROVIDER_BASE_URL`: HTTPS URL for an OpenAI Responses-compatible endpoint.
- `IIOS_LLM_PROVIDER_MODEL`, `IIOS_LLM_PROVIDER_ID`, `IIOS_LLM_PROVIDER_VERSION`, `IIOS_LLM_PROVIDER_PROTOCOL=OPENAI_RESPONSES`.
- `IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64`: 32-byte Ed25519 runtime attestation key, stored only in deployment secret storage.
- `IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64`: separately pinned 32-byte public key. Startup derives the public key from the configured private key and rejects mismatched keypairs; every captured receipt must match this pin before downstream semantic admission.
- `IIOS_LLM_PROVIDER_AUTH_MODE=NONE` and no `IIOS_LLM_PROVIDER_API_KEY` may be used for a self-hosted, HTTPS-protected model endpoint. If bearer auth is selected, a key is required by that provider's own deployment. The production factory currently requires HTTPS because the independent provider verifier requires HTTPS; use a verified TLS endpoint/reverse proxy for local model services rather than disabling TLS verification.

The runtime calls the actual provider at execution time. It writes a signed raw provider receipt to the immutable `<output_root>/live-provider-evidence/` store for each request-intent and semantic call, independently verifies the receipt and checks the attested public key against the configured pin before parsing strict JSON. Extra fields, schema drift, instrument/cutoff mismatch, non-finite numbers, non-JSON output, refusal and incomplete provider responses block the run. Provider output still passes the existing deterministic semantic admission and cannot set action/authority fields.

## Admission-store layout

`IIOS_CANONICAL_ADMISSION_ROOT` is operator-owned and must be durable and write-restricted. Required files are immutable records admitted by the existing domain producers:

- `current_price_admissions/<sha256(price_observation_id)>.price.json` — current-price resolver's canonical admission record.
- `independent_forecast_admissions/<sha256(forecast_id)>.forecast.json` — existing canonical independent forecast store.
- `investment_admissions/<sha256(admission_id)>.json` — JSON output of an existing `CanonicalInvestmentAdmissionRecord.to_dict()`, status `ADMITTED`, including the correct case identity, domain, evidence IDs and canonical record hash.
- `valuation_outputs/<sha256(admission_id)>.json` — validated output of `build_canonical_valuation_output()`, whose `output_hash` must equal the corresponding admitted VALUATION record's `output_hash`.

The factory only resolves these records; it has no write/admit method for upstream domains or valuation outputs. Missing, corrupt, tampered, wrong-domain, wrong-case or wrong-cutoff records return BLOCKED through the existing canonical run boundary. Do not seed the store with fixtures or manually set admission status to `ADMITTED`.

## Acceptance limits

- Contract CI confirms the factory returns the eight validated runtime bindings with no paid API key requirement for a configured self-hosted HTTPS endpoint. It does not call a model endpoint or prove production output.
- No factory can create missing 605016 source facts or make an unadmitted capture eligible. Attempt 10 remains `BLOCKED_NOT_ADMITTED` until each of the seven groups has fact-level, source-origin/reuse-reviewed, cutoff-bound B2 Evidence/PIT admission.
- The request interpreter is constrained to the bundle's instrument/cutoff identity. The semantic producer emits only `core_projection`; all model text is untrusted and still enters canonical semantic admission.
- Host deployment, provider certificate/auth configuration, trust-store provisioning, genuine request/semantic responses, complete report/Run Receipt replay and independent red-team remain separate gates. Human approval remains required; auto-execution remains disabled.
