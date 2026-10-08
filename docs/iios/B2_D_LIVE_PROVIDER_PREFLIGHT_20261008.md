# IIOS B2-D — Canonical Refresh + Live Provider

Date: 2026-10-08
Status: **LIVE EVIDENCE BLOCKED UNTIL PRODUCTION RUNTIME IS AVAILABLE**

## Canonical refresh

B2-D has been rebuilt from the canonical main line after the State-Hygiene merge. The stale pre-hygiene PR is not the merge base for this work.

The implementation is deliberately split:

`preflight`
→ `real provider invocation`
→ `raw response capture`
→ `replay record`
→ `runtime attestation`

No stage here authorizes semantic admission, forecast, valuation, Decision, Human Approval, publication, or execution.

## Real provider protocol

The first concrete provider protocol is `OPENAI_RESPONSES`. OpenAI's current API documentation uses the Responses API for new integrations; the request is model + input and this batch keeps `store=false` so the smoke call does not persist provider-side conversation state.

IIOS still treats the provider response as **untrusted external output**. The runtime attestation is an IIOS-side Ed25519 signature over the captured evidence. It is not a claim that the provider itself cryptographically signed the response.

## Required production runtime configuration

The live workflow reads these GitHub Actions secrets:

- `IIOS_LLM_PROVIDER_BASE_URL`
- `IIOS_LLM_PROVIDER_API_KEY`
- `IIOS_LLM_PROVIDER_MODEL`
- `IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64`
- `IIOS_LLM_PROVIDER_ID`
- `IIOS_LLM_PROVIDER_VERSION`
- `IIOS_LLM_PROVIDER_PROTOCOL`
- optional `IIOS_LLM_PROVIDER_TIMEOUT_SECONDS`

The runtime fails closed on missing credentials, non-HTTPS endpoints, unsupported protocol, malformed signing key, or invalid timeout.

## Live gate

A successful live smoke must produce an artifact containing:

- actual provider endpoint + selected model;
- real request/response bytes and SHA-256 hashes;
- run/case/request/cutoff identity;
- replay hash;
- IIOS runtime Ed25519 attestation;
- independently verifiable evidence.

The evidence artifact **does not** admit a semantic artifact. B2-E remains responsible for real NL→LLM→semantic admission and downstream Forecast/Valuation/Return/Risk/Portfolio/Decision lineage.

### Gate semantics

- credentials/configuration absent → `BLOCKED`;
- HTTP/provider invocation failure → `FAILED`;
- real response captured + replay verified + IIOS attestation verified → `LIVE_RESPONSE_CAPTURED`;
- only after this gate can B2-E consume the live provider output;
- fixture tests remain test evidence only.

## No secret persistence

The API key is used only in process memory by the transport adapter. It is never serialized into the replay or evidence records.

## Canonical state rule

This document is a B2-D development record. The canonical Current State remains `docs/PROJECT_STATE_INDEX.md`.
