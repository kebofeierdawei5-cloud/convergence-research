# P0 — Canonical Runtime Callback Preflight — 2026-10-10

**Status:** operator diagnostic only; it is not a production acceptance gate.  
**Entry point:** \`python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id <staged_bundle_id>\`

## Why this exists

The first-party HTTP Host and trusted provider-backed factory are already canonical (PRs #270 and #274). This command tests the runtime boundary in the operator environment without registering a fake runtime or creating an alternate factory.

It uses \`iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime\`. It does not define another runtime factory, disable pinned Ed25519 verification, relax HTTPS, or substitute test semantic output.

## What it does

1. Loads an operator-staged bundle by ID from \`IIOS_HOST_BUNDLE_ROOT\`; a caller-supplied filesystem path is not accepted.
2. Reuses trusted Host config, data-root path confinement and the canonical runtime-factory selector from process environment.
3. Makes one actual request-intent call and one actual thesis-semantic callback through the configured provider.
4. Reuses the canonical factory's signed raw provider receipt capture, pinned runtime public-key validation and independent receipt verification. The diagnostic report stores receipt filenames and hashes/provider metadata, not prompts or raw model output.
5. Saves a content-hashed report under \`IIOS_HOST_OUTPUT_ROOT/runtime-preflight/\`.

The result is \`PREFLIGHT_ONLY_COMPLETE\` only when both provider-backed callbacks return structurally valid outputs. Missing trusted configuration, an unavailable endpoint, a bad keypair, a mismatched bundle/manifest or invalid callback output must block.

## Trusted configuration

Continue using the existing factory:

\`\`\`bash
export IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.canonical_runtime_factory_v01:build_canonical_runtime
\`\`\`

The process also needs the existing Host variables: \`IIOS_HOST_BUNDLE_ROOT\`, \`IIOS_HOST_DATA_ROOT\`, \`IIOS_HOST_OUTPUT_ROOT\`, \`IIOS_HOST_AUTH_TOKEN\`, and \`IIOS_CANONICAL_ADMISSION_ROOT\`.

Provider variables follow PR #274's existing contract:

- \`IIOS_LLM_PROVIDER_BASE_URL\`: an OpenAI Responses-compatible **HTTPS** endpoint. A local model should sit behind a verified local TLS endpoint/reverse proxy. Do not disable certificate verification or change the independent verifier's HTTPS requirement.
- \`IIOS_LLM_PROVIDER_MODEL\`, \`IIOS_LLM_PROVIDER_ID\`, \`IIOS_LLM_PROVIDER_VERSION\`, and \`IIOS_LLM_PROVIDER_PROTOCOL=OPENAI_RESPONSES\`.
- \`IIOS_LLM_PROVIDER_AUTH_MODE=NONE\` with \`IIOS_LLM_PROVIDER_DEPLOYMENT_MODE=SELF_HOSTED\` is allowed for a self-hosted model and needs no commercial provider API key.
- \`IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64\` and \`IIOS_LLM_PROVIDER_RUNTIME_PUBLIC_KEY_B64\` remain required. Generate a fresh keypair for the operator environment, keep the private key in secret storage, and pin the matching public key. Do not use a CI test key.

A staged bundle needs a case-matched manifest with at least one row containing an evidence ID and SHA-256, plus a \`THESIS_ASSESSMENT\` semantic prompt. These are callback-input checks only. The preflight does not admit any source facts or alter manifest status.

## Run

From the canonical repository checkout, in the same trusted environment intended for the Host:

\`\`\`bash
python -m iios_mvp.canonical_host_v01 --check-config
python -m iios_mvp.canonical_runtime_preflight_v01 --bundle-id 605016-case
\`\`\`

The bundle ID is illustrative; it must correspond to an operator-staged \`605016-case.json\` under \`IIOS_HOST_BUNDLE_ROOT\`.

Review the JSON result and saved report. Success confirms only that the provider-backed request interpreter and thesis-semantic callback ran and that the signed provider receipts were persisted. It does **not** prove the production HTTP Host received a real external request.

## Non-claims and next gate

The report explicitly records:
- \`evidence_pit_admission_checked=false\`;
- \`semantic_admission_checked=false\`;
- \`decision_created=false\`;
- \`publication_created=false\`;
- \`run_receipt_created=false\`;
- \`human_approval_required=true\`;
- \`auto_execution=false\`.

Do not relabel a preflight report as an Evidence/PIT admission, semantic admission, decision, Run Receipt or production PASS. The next gate after preflight is a real HTTP-host-origin canonical run with seven-group Evidence/PIT-admitted evidence and case-bound Forecast/Valuation inputs, followed by publication/report, complete \`IIOS_RUN_RECEIPT\` replay and fresh independent red-team.

The 605016 case remains blocked on its unadmitted \`market_price\` group. This diagnostic does not remove that blocker. P0-LLM-001/P0-LLM-004 remain OPEN until real-host acceptance. Human approval remains mandatory; automatic order execution is disabled.
