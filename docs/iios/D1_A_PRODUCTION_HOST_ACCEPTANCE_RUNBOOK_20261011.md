# D1-A — Production Host acceptance runbook

Date: 2026-10-11

Status: **RUNBOOK / EVIDENCE CONTRACT ADDED; PRODUCTION ACCEPTANCE OPEN**

## Purpose and boundary

The canonical Host, trusted runtime factory, signed live-provider receipt, independent receipt verifier and runtime preflight components exist. Their contract tests do not prove that a real Host process has been deployed with the operator's actual model/provider, durable admission store and accepted case. This runbook distinguishes configuration from production acceptance.

## Phase 1 — configuration only

Run the existing configuration check on the intended operator-controlled host:

    python -m iios_mvp.canonical_host_v01 --check-config

Expected status: CONFIGURED_NOT_PRODUCTION_ACCEPTED. The output explicitly states that the production runtime was not invoked. A passing output is not Host acceptance.

For a no-paid-key local path, first start the operator-managed Ollama service and ensure the chosen model is already installed. The repository helper checks the local version and model before writing a private environment file (it requires Ollama >= 0.13.3):

    python tools/prepare_iios_local_ollama_runtime.py --workspace "$HOME/.iios-private" --model "qwen3:8b"

Use an installed model name if a smaller model is required. The helper creates private directories and secrets/host.env with mode 0600; it does not print the generated bearer token or private key and will not overwrite an existing env file. Load the protected environment without shell tracing and run:

    set +x
    source "$HOME/.iios-private/secrets/host.env"
    python -m iios_mvp.canonical_host_v01 --check-config

This remains configuration preflight, not production acceptance.

Confirm the trusted factory is the provider-backed factory (not the manual Web adapter), the provider transport conforms to the endpoint policy, the configured model/provider identity and version are pinned, and the Ed25519 runtime key pair is internally consistent. For a no-paid-key setup, a self-hosted Ollama-compatible endpoint may be used with SELF_HOSTED and AUTH_MODE=NONE on loopback. Do not put deployment credentials, private keys, raw prompts or responses into PRs, CI logs or public artifacts.

## Phase 2 — live process probe

Start the actual Host process/service from the operator-controlled deployment. Check the configured Host /healthz and /readyz endpoints. /healthz proves only that the process responds; /readyz intentionally reports CONFIGURED_NOT_PRODUCTION_ACCEPTED and does not call the provider. Preserve the sanitized HTTP status and Host version in the private acceptance notes.

With the private environment loaded, start the host bound to loopback and keep logs under the private output root:

    python -m iios_mvp.canonical_host_v01 > "$IIOS_HOST_OUTPUT_ROOT/host.log" 2>&1 &

In a second terminal, load the same protected env with tracing disabled and probe without verbose curl output:

    curl --silent --show-error "http://127.0.0.1:${IIOS_HOST_PORT:-8765}/healthz"
    curl --silent --show-error "http://127.0.0.1:${IIOS_HOST_PORT:-8765}/readyz"

Expected: health status OK; ready status CONFIGURED_NOT_PRODUCTION_ACCEPTED and runtime invocation false. These are liveness/configuration observations only.

## Phase 3 — real host-origin provider invocation

Using an operator-staged bundle bound to the exact 605016 Case and cutoff, submit one explicit request to the Host's canonical-run endpoint. The Host must invoke the configured provider-backed runtime; a manual ChatGPT Web copy/paste is not an admissible substitute. Keep full prompts/responses and deployment secrets on the private host.

The Host accepts a JSON body containing only a bundle_id. The corresponding bundle file is resolved under IIOS_HOST_BUNDLE_ROOT; its evidence manifest/root must resolve within IIOS_HOST_DATA_ROOT. The HTTP request never contains the bundle or evidence itself.

Only after formal C1 / 605016 Evidence/PIT admission is complete, submit the pre-staged immutable case bundle using a private curl config file. Keep shell tracing off:

    umask 077
    printf 'header = "Authorization: Bearer %s"\n' "$IIOS_HOST_AUTH_TOKEN" > "$IIOS_HOST_OUTPUT_ROOT/.curl-auth.cfg"
    chmod 600 "$IIOS_HOST_OUTPUT_ROOT/.curl-auth.cfg"
    printf '{"bundle_id":"<STAGED_BUNDLE_ID>"}\n' > "$IIOS_HOST_OUTPUT_ROOT/.host-request.json"
    chmod 600 "$IIOS_HOST_OUTPUT_ROOT/.host-request.json"
    curl --silent --show-error --fail-with-body \
      --config "$IIOS_HOST_OUTPUT_ROOT/.curl-auth.cfg" \
      -H 'Content-Type: application/json' \
      --data-binary @"$IIOS_HOST_OUTPUT_ROOT/.host-request.json" \
      "http://127.0.0.1:${IIOS_HOST_PORT:-8765}/v1/canonical-runs"
    rm -f "$IIOS_HOST_OUTPUT_ROOT/.curl-auth.cfg" "$IIOS_HOST_OUTPUT_ROOT/.host-request.json"

Do not use set -x, curl -v, or put the bearer token into command-line arguments, PR comments or logs. Do not run the 605016 canonical request while evidence remains a local candidate rather than formally admitted.

Verify the actual output-root live-provider evidence for the request-intent and semantic stages using the independent Ed25519 receipt verifier and the separately pinned public key. Require matching case/run/request/stage identities, provider ID/version/model, endpoint policy, request and response hashes, signatures and strict response contract. Demonstrate that the artifacts are persisted durably and survive process restart. Readiness, mocked tests, fixture providers and local hash receipts from manual Web do not meet this gate.

## Phase 4 — acceptance evidence

A separate reviewer must confirm: (1) real host-origin request performed; (2) actual authorized provider invocation occurred; (3) signed receipts independently validate against the configured public-key pin; (4) evidence and output bytes persist durably; (5) fail-closed behavior blocks missing/wrong-case evidence; (6) canonical run and clean replay results are bound to the same exact Case/cutoff; (7) human approval remains mandatory and auto-execution remains disabled.

Keep the acceptance report sanitized. It may record run IDs, version identifiers, SHA-256 hashes, result statuses and test counts, but not private market quotes, raw filing data beyond permitted use, prompts/responses, bearer credentials or private signing keys.

## Current result

No production Host acceptance is claimed by this runbook. This assistant session can inspect canonical code and CI results but does not have direct control of the operator's deployment, model endpoint, secret store or durable admission filesystem. Therefore the following remain open until the real host-origin evidence is returned and independently reviewed: actual provider invocation, signed-receipt verification, durable persistence/replay, production Host acceptance, P0-LLM-001/P0-LLM-004, complete IIOS_RUN_RECEIPT, formal Decision and execution authorization.



## Dependency made explicit

The 605016 successor is currently a local Core/PIT-validated candidate, not formal signed Evidence/PIT admission; its source-vintage/final-use gate remains open. D1-A host configuration and liveness may be progressed in parallel, but the real D1 canonical 605016 request/provider-stage acceptance must wait for formal C1 Evidence/PIT admission. Do not substitute fixture records or another case and claim D1 acceptance.

## Diagnostic: green live-provider workflow does not necessarily mean provider PASS

The B2-D live-provider workflow is deliberately fail-closed and configured with continue-on-error for its live job. On run [#38127035406](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38127035406), the live job completed successfully but logged all required provider configuration fields as empty, emitted `BLOCKED_OR_FAILED`, and did not produce/independently verify a real live receipt. This run therefore has **zero production-acceptance credit**. Always inspect the live-job output and artifact disposition; job conclusion alone is insufficient.

That diagnostic remains separate from the operator-managed D1-A Host. A real acceptance still requires a host-origin request and verified signed receipts inside the actual configured output root.