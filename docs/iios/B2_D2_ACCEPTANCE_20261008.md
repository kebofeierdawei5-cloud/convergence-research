# B2-D2 — Provider-Neutral Runtime Boundary Acceptance

Date: 2026-10-08
Status: **PASS / CANONICAL**

## Canonical baseline

- pre-batch main: `9b0a147ba86e7f7d2645b800cc95281e8082b55f`
- implementation PR: #219
- accepted implementation head: `d5bffeff8afcde0b4b0be9114cfd9d9cab1bdfbf`
- merge commit: `7997a107ab18687d7c81f731ec7e0b3fae09ed9a`

## Runtime boundary

B2-D2 separates the `OPENAI_RESPONSES` protocol from provider deployment and authentication:

`protocol = OPENAI_RESPONSES`

`deployment_mode = EXTERNAL | SELF_HOSTED`

`auth_mode = BEARER | NONE`

Commercial credentials are therefore conditional runtime configuration, not a protocol-level or architecture-level requirement.

Security rule:
- external/non-loopback endpoints require HTTPS;
- HTTP is accepted only for explicitly `SELF_HOSTED` loopback endpoints;
- `BEARER` requires an API key;
- `NONE` rejects accidental API-key injection.

## Verification

B2-D workflow run #17:
- B2-D tests: 11 / 11 PASS;
- B2-D clean-room red-team: 15 / 15 PASS;
- B2-D1 verifier tests: PASS;
- B2-D2 runtime tests: PASS;
- B2-D2 independent red-team: PASS;
- compileall: PASS;
- schema validation: PASS;
- git diff-check: PASS.

The live smoke remained non-authoritative and correctly produced no `LIVE_RESPONSE_CAPTURED` evidence because the production provider runtime was not configured.

## Acceptance

B2-D2 closes the provider-neutral runtime boundary. It does not close the live-provider evidence gate and does not authorize B2-E.

Next boundary:

`Production Provider Runtime Configuration → Real Live Invocation → Independent Evidence Verification → B2-E`
