# P0 Batch B2 production-host follow-up — Free-First Local Ollama Runtime Path — 2026-10-10

Status: **MERGED** in PR #285 at `cf3fb42ebf3f0faedb7a50244ea0edd00fc142ac`; exact PR-head checks **17/17 PASS** and post-merge required checks **6/6 PASS**. **Production Host acceptance remains OPEN.**  
Goal: make the existing trusted runtime factory usable with a local, no-paid-key model without weakening the external-provider boundary.

## Defect corrected

The canonical provider-neutral policy already allowed HTTP only for SELF_HOSTED loopback endpoints, and the preflight already allowed AUTH_MODE=NONE. However, the trusted factory and independent live-evidence verifier independently required HTTPS for every endpoint. That internal contradiction prevented a local model served only on the same machine from reaching the existing signed-receipt path.

The corrected exception is narrowly limited to:

- scheme http;
- loopback hostname/IP (localhost, loopback IPv4 or loopback IPv6);
- deployment_mode=SELF_HOSTED;
- auth_mode=NONE.

External endpoints, LAN endpoints, arbitrary hostnames over HTTP, and loopback HTTP with bearer mode are rejected. HTTPS behavior remains supported. auth_mode and deployment_mode are included in new signed runtime receipts and validated independently; historical HTTPS receipts without these optional fields remain verifiable.

## Local provisioning helper

tools/prepare_iios_local_ollama_runtime.py prepares a local workspace after checking the actual Ollama server:

- Ollama version must be at least 0.13.3, which introduced the non-stateful OpenAI Responses endpoint.
- The requested model must already be installed locally; default is qwen3:8b and can be changed explicitly.
- The generated secrets/host.env contains a fresh Ed25519 runtime keypair and a strong host bearer token. It is created with mode 0600, and the script never overwrites an existing env file.
- The workspace directories are private and local-only. .iios-local/ and .iios-secrets/ are ignored by Git.
- The helper does not create company bundles, raw Evidence, Evidence/PIT admissions, independent Forecast admissions, Valuation admissions or Decisions.

Official Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx

## Operator smoke procedure

1. Install Ollama and pull the selected model, for example: ollama pull qwen3:8b. Start the local Ollama service; it must be reachable only on loopback.
2. Run the commands below from the repository root:

    python tools/prepare_iios_local_ollama_runtime.py --workspace .iios-local --model qwen3:8b
    set -a
    source .iios-local/secrets/host.env
    set +a
    python -m iios_mvp.canonical_host_v01

3. From another local terminal, check `GET http://127.0.0.1:8765/healthz` and `GET http://127.0.0.1:8765/readyz`. Keep the authentication token private. `/readyz` only confirms safe configuration; it deliberately does not invoke the factory or the model.
4. For a real callback-only preflight, first stage a real operator-owned case bundle under `.iios-local/bundles/` with its manifest and original files under `.iios-local/data/`. Load the protected environment in the same shell and run `python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id <staged_bundle_id>`. This exercises the configured model's request interpreter and semantic producer and saves a signed preflight report; it explicitly does **not** run Evidence/PIT admission, Forecast, Valuation, Decision, publication or full Run Receipt. Use a real case and real captured bytes, never a fixture to claim production acceptance.
5. A full `POST /v1/canonical-runs` company request is authorized only after the real source bundle, all seven B2 Evidence/PIT groups, market-price evidence, independently admitted Forecast, authority records and Valuation output exist. An empty admission directory is intentionally not enough; missing records must remain `BLOCKED`.

## What this does not prove

- The helper's loopback test server is contract-test-only and is not production acceptance.
- Installing Ollama and generating config does not prove that an actual investment request ran.
- Host readiness does not mean the 605016 case is admitted. At the current canonical state, its market_price group remains UNKNOWN/unadmitted, and the full company run must remain blocked.
- This does not auto-create, infer or promote missing upstream admission records.
- A local model response is not a provider-quality certification or an investment Decision. Canonical admission, independent Forecast/Valuation, full Run Receipt replay, independent red-team and human approval remain mandatory.
- Automatic trade execution remains disabled.

## Remaining production acceptance

A real local operator must start the actual service and local model, record the exact main SHA and Ollama/model version, submit an operator-staged real bundle, preserve signed raw response receipts, and prove that negative cases remain blocked. Production P0 closure still requires a complete real-company run plus replay and independent red-team.
