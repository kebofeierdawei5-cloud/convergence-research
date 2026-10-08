# B2-D3 — Real Provider Runtime + Live Evidence Gate Acceptance

Date: 2026-10-08

Status: **IMPLEMENTATION PASS / LIVE EVIDENCE BLOCKED**

## Canonical promotion

- source canonical base: `2906fb71715d51971e7dab0146bdbef8da9e45c9`;
- implementation PR: #221;
- canonical merge commit: `52f3afb6925ec34dd2982c52908416e2e2fa302d`.

## Closed implementation boundary

B2-D3 adds the first production-only runtime gate that can make an actual provider HTTP call.

The runtime sequence is:

```
production secrets / variables
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
independent verification
```

The implementation does not add semantic, Forecast, Valuation, Decision, Human Approval, publication or execution authority.

The workflow is `workflow_dispatch` only so provider quota cannot be spent by an ordinary code push or pull request.

## Technical verification

- B2-D workflow run #21: SUCCESS;
- B2-D tests: PASS;
- B2-D independent clean-room red-team: PASS;
- B2-D1 independent verifier tests: PASS;
- B2-D2 provider runtime tests: PASS;
- B2-D2 independent clean-room red-team: PASS;
- B2-D3 workflow contract tests: PASS;
- compileall: PASS;
- schema validation: PASS;
- git diff-check: PASS.

## Live evidence gate

The repository runtime currently has no admitted production provider credentials/configuration. The B2-D live smoke therefore produced the expected fail-closed `BLOCKED_OR_FAILED` status and no `LIVE_RESPONSE_CAPTURED` record.

This is **not** a failed implementation. It is an intentionally unresolved production-evidence gate.

B2-D3 may be promoted from **IMPLEMENTATION PASS / LIVE EVIDENCE BLOCKED** to live-evidence PASS only after a manual workflow run produces a real HTTP 2xx response and the same artifact is independently verified by:

`IIOS-LIVE-PROVIDER-INDEPENDENT-VERIFIER-0.1`.

## Security / scope rules

- provider credentials are never committed to Git;
- provider identity is separate from protocol, deployment mode and authentication mode;
- external/non-loopback endpoints remain HTTPS-only;
- redirects are rejected by the live transport;
- self-hosted loopback HTTP remains governed by B2-D2 policy;
- no fixture or manually authored response may satisfy the live gate;
- no live response may authorize an investment decision directly.

## Next gate

```
PRODUCTION PROVIDER CONFIGURATION
        ↓
MANUAL B2-D3 LIVE RUN
        ↓
LIVE_RESPONSE_CAPTURED
        ↓
B2-D1 INDEPENDENT_VERIFIED
        ↓
B2-E Natural-Language → Semantic → Decision E2E
```
