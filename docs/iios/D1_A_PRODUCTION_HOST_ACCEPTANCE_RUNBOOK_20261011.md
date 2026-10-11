# D1-A — Production Host acceptance runbook

Date: 2026-10-11

Status: **RUNBOOK / EVIDENCE CONTRACT ADDED; PRODUCTION ACCEPTANCE OPEN**

## Purpose and boundary

The canonical Host, trusted runtime factory, signed live-provider receipt, independent receipt verifier and runtime preflight components exist. Their contract tests do not prove that a real Host process has been deployed with the operator's actual model/provider, durable admission store and accepted case. This runbook distinguishes configuration from production acceptance.

## Phase 1 — configuration only

Run the existing configuration check on the intended operator-controlled host:

    python -m iios_mvp.canonical_host_v01 --check-config

Expected status: CONFIGURED_NOT_PRODUCTION_ACCEPTED. The output explicitly states that the production runtime was not invoked. A passing output is not Host acceptance.

Confirm the trusted factory is the provider-backed factory (not the manual Web adapter), the provider transport conforms to the endpoint policy, the configured model/provider identity and version are pinned, and the Ed25519 runtime key pair is internally consistent. For a no-paid-key setup, a self-hosted Ollama-compatible endpoint may be used with SELF_HOSTED and AUTH_MODE=NONE on loopback. Do not put deployment credentials, private keys, raw prompts or responses into PRs, CI logs or public artifacts.

## Phase 2 — live process probe

Start the actual Host process/service from the operator-controlled deployment. Check the configured Host /healthz and /readyz endpoints. /healthz proves only that the process responds; /readyz intentionally reports CONFIGURED_NOT_PRODUCTION_ACCEPTED and does not call the provider. Preserve the sanitized HTTP status and Host version in the private acceptance notes.

## Phase 3 — real host-origin provider invocation

Using an operator-staged bundle bound to the exact 605016 Case and cutoff, submit one explicit request to the Host's canonical-run endpoint. The Host must invoke the configured provider-backed runtime; a manual ChatGPT Web copy/paste is not an admissible substitute. Keep full prompts/responses and deployment secrets on the private host.

Verify the actual output-root live-provider evidence for the request-intent and semantic stages using the independent Ed25519 receipt verifier and the separately pinned public key. Require matching case/run/request/stage identities, provider ID/version/model, endpoint policy, request and response hashes, signatures and strict response contract. Demonstrate that the artifacts are persisted durably and survive process restart. Readiness, mocked tests, fixture providers and local hash receipts from manual Web do not meet this gate.

## Phase 4 — acceptance evidence

A separate reviewer must confirm: (1) real host-origin request performed; (2) actual authorized provider invocation occurred; (3) signed receipts independently validate against the configured public-key pin; (4) evidence and output bytes persist durably; (5) fail-closed behavior blocks missing/wrong-case evidence; (6) canonical run and clean replay results are bound to the same exact Case/cutoff; (7) human approval remains mandatory and auto-execution remains disabled.

Keep the acceptance report sanitized. It may record run IDs, version identifiers, SHA-256 hashes, result statuses and test counts, but not private market quotes, raw filing data beyond permitted use, prompts/responses, bearer credentials or private signing keys.

## Current result

No production Host acceptance is claimed by this runbook. This assistant session can inspect canonical code and CI results but does not have direct control of the operator's deployment, model endpoint, secret store or durable admission filesystem. Therefore the following remain open until the real host-origin evidence is returned and independently reviewed: actual provider invocation, signed-receipt verification, durable persistence/replay, production Host acceptance, P0-LLM-001/P0-LLM-004, complete IIOS_RUN_RECEIPT, formal Decision and execution authorization.

