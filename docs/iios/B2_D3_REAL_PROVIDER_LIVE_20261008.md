# B2-D3 — Real Provider Runtime Configuration and Live Evidence Gate

Date: 2026-10-08

Status: **IMPLEMENTATION READY / LIVE CONFIGURATION PENDING**

## Purpose

B2-D3 is the first gate where IIOS may perform a real external/self-hosted provider HTTP invocation.

The sequence is strict:

```
production runtime configuration
        ↓
fail-closed preflight
        ↓
real HTTP invocation
        ↓
raw response capture
        ↓
LIVE_RESPONSE_CAPTURED
        ↓
B2-D1 independent verification
        ↓
independent verification PASS
```

No fixture provider, mocked HTTP response, or manually authored evidence record may satisfy this gate.

## Runtime configuration

The implementation reuses the canonical B2-D2 provider-neutral runtime boundary.

Required repository **Secrets**:

- `IIOS_LLM_PROVIDER_BASE_URL`
- `IIOS_LLM_PROVIDER_API_KEY` when `auth_mode=BEARER`
- `IIOS_LLM_PROVIDER_MODEL`
- `IIOS_LLM_PROVIDER_RUNTIME_PRIVATE_KEY_B64`
- `IIOS_LLM_PROVIDER_ID`
- `IIOS_LLM_PROVIDER_VERSION`
- `IIOS_LLM_PROVIDER_PROTOCOL`
- `IIOS_LLM_PROVIDER_TIMEOUT_SECONDS` (optional; defaults to 30)

Repository **Variables**:

- `IIOS_LLM_PROVIDER_AUTH_MODE` (default `BEARER`)
- `IIOS_LLM_PROVIDER_DEPLOYMENT_MODE` (default `EXTERNAL`)

For the current protocol contract, `IIOS_LLM_PROVIDER_PROTOCOL` must be `OPENAI_RESPONSES`.

For an external provider, `IIOS_LLM_PROVIDER_BASE_URL` must be HTTPS and `BEARER` normally requires the provider API key.

For a self-hosted loopback provider, B2-D2 permits HTTP only when the deployment mode is explicitly `SELF_HOSTED`; the existing runtime policy still rejects non-loopback HTTP.

The runtime private key is an IIOS-side Ed25519 signing key encoded as base64 and must decode to exactly 32 bytes. It must never be committed to the repository or printed to logs.

## Controlled execution

The dedicated workflow is:

`/.github/workflows/iios_b2d3_real_provider.yml`

It is intentionally **workflow_dispatch only**. A code push or pull request cannot silently spend provider quota or mutate live evidence.

The workflow:

1. checks runtime configuration without printing credentials;
2. invokes `iios_mvp.live_provider_evidence_v01` against the configured endpoint;
3. writes the raw provider response inside the signed evidence artifact as base64;
4. requires HTTP 2xx and `LIVE_RESPONSE_CAPTURED`;
5. runs `iios_mvp.live_provider_independent_verify_v01` in a separate process;
6. uploads the evidence plus a non-secret manifest as a short-retention CI artifact.

The live artifact is not canonical semantic state and does not authorize B2-E by itself.

## Acceptance rule

B2-D3 is **PASS** only when a real workflow run produces:

- `status = LIVE_RESPONSE_CAPTURED`;
- actual HTTP 2xx response;
- request SHA-256 match;
- response SHA-256 match;
- Replay Hash match;
- IIOS Ed25519 attestation/signature verification;
- B2-D1 independent verifier result = `INDEPENDENT_VERIFIED`.

Only after that evidence is independently verified may the project enter:

`B2-E Natural-Language → Semantic → Decision E2E`

Until then the state remains **LIVE_PROVIDER_EVIDENCE = BLOCKED**.
