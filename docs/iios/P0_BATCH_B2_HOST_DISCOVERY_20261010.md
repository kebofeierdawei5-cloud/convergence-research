# P0 Batch B2 — Production Host Discovery Audit — 2026-10-10

**Record class:** bounded repository/deployment-surface discovery; not an acceptance PASS  
**Canonical baseline:** `main@92ad57f837fed50ab474ebf89f4f308869e31545`  
**Result:** **DISCOVERY EXECUTED / PRODUCTION HOST ACCEPTANCE BLOCKED**

## Question investigated

Can the actual user-facing application/service that receives investment requests be located in the currently accessible source and proven to register a genuine `CanonicalRuntimeBindings` runtime before calling the canonical entry?

## Evidence inspected

- The canonical repository tree at the exact baseline above was enumerated recursively.
- The currently accessible repository inventory for the linked GitHub account exposed only `kebofeierdawei5-cloud/convergence-research`. This is a statement about the accessible inventory, **not** a claim that no other deployment exists anywhere.
- Inspected `iios_mvp/cli.py`, `iios_mvp/canonical_runtime_registry_v01.py`, `tests/test_canonical_cli_host_integration.py`, and `docs/iios/P0_BATCH_B1_CLI_HOST_INTEGRATION_20261010.md`.
- The repository tree contains the Python CLI/runtime modules, but no separately identifiable production web/server/front-end composition root or deployment entrypoint (for example, a server app package or Docker/Procfile deployment definition).

## Findings

1. The repository has an explicit `canonical-run` CLI route. It first uses a runtime pre-registered by the trusted host, or resolves a trusted `--runtime-factory module:callable` / `IIOS_CANONICAL_RUNTIME_FACTORY` setting. The factory selector is not read from request JSON.
2. The runtime registry initializes to `None`; the absence of a registered runtime deliberately returns `BLOCKED / CANONICAL_RUNTIME_NOT_REGISTERED`. No production runtime was found registered by default, and this audit made no change to that fail-closed behavior.
3. The shared validator requires all eight runtime bindings, an active typed request-interpreter registry, an active typed semantic-producer registry, identity/version/policy matches, and the required current-price, forecast, upstream-authority and valuation resolver methods. The semantic producer must declare `LLM_SEMANTIC_PRODUCER` and implement its production callback; placeholder objects are insufficient.
4. The merged CLI host integration test reaches `iios_mvp.cli.main()`, but uses a trusted **test-only** runtime factory, `TEST_ONLY` evidence and a fixture semantic producer. It proves repository control-plane routing and persistence, **not** an external/deployed product host or production semantic conformance.
5. No accessible deployment source, host launch entrypoint, production runtime-registration call, or genuine production semantic callback could be independently tied to this repository at the audit baseline.

## Gate decision

Batch B2 remains **BLOCKED — ACTUAL DEPLOYABLE HOST / PRODUCTION CALLBACK NOT IDENTIFIED IN ACCESSIBLE SOURCE**. Batch B1 is not promoted to a full Batch B PASS.

This is an evidence/ownership boundary, not a demand for a paid provider API key. Route A public-source discovery, raw-byte capture, and B2/PIT validation remain free-first and do not require LLM credentials. The production canonical decision path, however, cannot claim a genuine semantic stage unless the real host supplies an authorized model callback or an independently verifiable production-origin semantic receipt.

## Minimum evidence required to resume implementation

- The actual host repository or source location, an immutable deployed commit/release identifier, and the real service/command entrypoint that receives user requests.
- The trusted composition code/configuration that registers the eight validated bindings; configuration *names* may be recorded while secret values remain outside Git and outside audit output.
- A fresh host-originated run ID with logs/receipts showing it reached `canonical-run` (not legacy `run` / direct `run_case`) and the approved runtime identity/version/policy.
- A genuine production semantic callback or a production-origin signed semantic receipt, followed by real-company evidence/PIT and Forecast/Valuation admission, publication/report, complete `IIOS_RUN_RECEIPT` replay, and fresh independent red-team.

## Explicit non-claims

- This audit does not prove that an external deployment does not exist; it proves that no such host can be identified from the currently accessible repository scope.
- No provider was called, no production runtime was registered, and no company evidence was admitted by this discovery work.
- P0-LLM-001 and P0-LLM-004 remain **OPEN**. Human approval remains mandatory; no automatic order execution is enabled.

