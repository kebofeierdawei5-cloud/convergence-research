# D1-A — Production Host acceptance runbook

Date: 2026-10-11

Status: **PRECHECK TOOL ADDED; PRODUCTION ACCEPTANCE OPEN**

## Purpose and limit

The preflight tool verifies operator-local configuration without exposing secrets. It can only return CONFIG_PREFLIGHT_PASS_NOT_PRODUCTION_ACCEPTED or BLOCKED. It does not start a host, invoke a provider, create formal admissions or claim acceptance.

## Preflight on the operator-controlled host

Run from a clean checkout of canonical main on the machine that will host IIOS:

    python tools/iios_d1a_host_acceptance_preflight_v01.py --out /path/inside/private-store/D1_A_PREFLIGHT.json

The output contains presence/status metadata only; it never writes the bearer token, provider API key, runtime private key, pinned public key or full endpoint URL. Keep the output private because it reveals non-secret deployment metadata.

Expected successful preflight status: CONFIG_PREFLIGHT_PASS_NOT_PRODUCTION_ACCEPTED. That status is not acceptance.

## Production acceptance evidence still required

1. Run `python -m iios_mvp.canonical_host_v01 --check-config`; expected CONFIGURED_NOT_PRODUCTION_ACCEPTED, which verifies configuration only.
2. Start the actual host as the operator-managed process/service. Verify /healthz returns the canonical host version and /readyz says CONFIGURED_NOT_PRODUCTION_ACCEPTED. Neither endpoint invokes the model.
3. Invoke one explicitly authorized staged bundle through POST /v1/canonical-runs with the operator's bearer token kept out of shell history and logs. Use the canonical provider factory, never the manual ChatGPT Web adapter.
4. Verify actual provider receipts in output_root/live-provider-evidence against schemas, response/request hashes, Ed25519 signature and separately pinned public key. Confirm provider ID/version/model and case/cutoff binding. Keep raw prompts/responses private.
5. Confirm immutable/durable output persistence and independently replay evidence receipts; confirm there is no path to auto-execution and that human approval remains required.
6. Attach a sanitized acceptance record reviewed by a separate reviewer. It must include host version, environment class, test run IDs/receipt hashes, actual-provider invocation true, receipt verification true, durable replay result and independent review. Do not include secrets or market quote values.

## Current gap

The canonical repository and CI establish contract coverage, not a deployment on the operator's machine. This task runtime cannot access the operator-managed host, provider endpoint, secret store or private admission store. Therefore this branch does not claim that the real host has been started or accepted. The next executable dependency is the preflight and real host-origin smoke on the intended host; no paid provider API key is required when a valid local Ollama-compatible endpoint is used with SELF_HOSTED and AUTH_MODE=NONE.

## Acceptance boundary

Do not close P0-LLM-001/P0-LLM-004 on config/healthz/readyz alone. Production acceptance requires real host-origin provider invocation, independently verified signed receipts, durable admitted records, canonical run completion and a clean independent replay. No decision, publication, complete IIOS_RUN_RECEIPT or execution authority is created by this preflight.