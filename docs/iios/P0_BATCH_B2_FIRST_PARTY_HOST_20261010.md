# P0 Batch B2 — First-Party Local Host — 2026-10-10

**Record class:** deployable host adapter + fail-closed contract tests  
**Canonical implementation baseline:** `main@fcd3e1be9d7894a785c99752c0953ef1765c10ad`  
**Scope:** put an actual, versioned HTTP host entrypoint inside the canonical repository; preserve a separate production-runtime/evidence acceptance gate.

## What this implements

- `python -m iios_mvp.canonical_host_v01` starts a first-party HTTP service with `GET /healthz`, `GET /readyz` and authenticated `POST /v1/canonical-runs`.
- The POST accepts only an operator-staged `bundle_id`, never a filesystem path, runtime-factory name, provider config or provider secret.
- Bundle files are constrained to the configured bundle root; evidence-manifest and raw-evidence paths must resolve within the configured data root. Path traversal and out-of-root symlink resolutions fail closed.
- Each accepted request gets server-generated unique request/run IDs. Caller-supplied semantic facts, inferences, assumptions and uncertainties are cleared; the registered producer must generate the semantic output, and existing canonical admission remains authoritative.
- The host invokes the actual `python -m iios_mvp.cli canonical-run` subprocess without a shell. The factory selector comes only from trusted host environment.
- Bearer authentication is required for run submission; tokens must be at least 32 characters. The default bind is `127.0.0.1`. Non-loopback binding requires both explicit remote enablement and declared TLS termination by a trusted reverse proxy.
- The HTTP response never echoes subprocess stderr. It exposes only allowlisted result fields, makes human approval mandatory and keeps automatic execution disabled. `202` means only that the canonical run reached its proposal/in-progress state, not that report/publication/receipt are complete.

## Production setup contract

The operator must provision:

- `IIOS_HOST_BUNDLE_ROOT`: directory containing reviewed `<bundle_id>.json` request bundles.
- `IIOS_HOST_DATA_ROOT`: parent directory containing the exact evidence manifest and raw evidence root referenced by the bundle.
- `IIOS_HOST_OUTPUT_ROOT`: durable, write-restricted output directory.
- `IIOS_HOST_AUTH_TOKEN`: a secret of at least 32 characters; store in deployment secret storage, never in Git.
- `IIOS_CANONICAL_RUNTIME_FACTORY`: trusted `module:callable` returning all eight validated runtime bindings. This variable is not accepted from HTTP input.

Optional settings: `IIOS_HOST_BIND` (defaults to loopback), `IIOS_HOST_PORT` (8765), `IIOS_HOST_RUN_TIMEOUT_SECONDS` (600), `IIOS_HOST_ALLOW_REMOTE=true`, and `IIOS_HOST_TLS_TERMINATED=true` (the latter two are both required for non-loopback binding).

A self-hosted model is permitted by the existing provider-neutral runtime policy using `auth_mode=NONE` and a self-hosted loopback endpoint; no commercial API key is required. The host does not create fake resolvers or synthetic admissions if the runtime/data configuration is missing.

## Important acceptance boundary

This change closes the *source-code/deployable entrypoint absence* for a first-party, single-operator host. It does **not** claim that the host has already been deployed or that a valid production runtime has been registered. A genuine `module:callable`, an admitted company evidence bundle, date-correct price observation, independent forecast/valuation data, and a production-backed semantic response still need to be present before the run can pass. Missing inputs must continue returning `BLOCKED`.

The readiness response is intentionally `CONFIGURED_NOT_PRODUCTION_ACCEPTED`. Host CI proves routing, authentication, path confinement and fail-closed result handling; it is not evidence of economic decision quality or production deployment.

## Validation

`tests/test_canonical_host_v01.py` covers invalid bundle IDs, missing trusted config, remote-bind guard, path confinement, auth, request-field allowlist, server-generated identity, semantic-input clearing, trusted runtime-factory selection, stderr non-disclosure and a blocked CLI response. The dedicated workflow must run on the exact PR head.

