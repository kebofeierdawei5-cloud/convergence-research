# B79 — Source trust, Evidence/PIT and formal Forecast lineage closure

Date: 2026-11-06  
Branch: feat/b76-core-integrated-20261101  
State: Draft proposal only; do not merge to main.

## Findings

### Source class is not trust admission

B57/B78 carried source data classes across EPS_MULTIPLE, but a data_class label is only a provenance classification. It does not prove an Evidence ID exists, its raw bytes were verified, its known_at is within the PIT cutoff, its source-use rights were approved, or a trusted signer admitted it.

The financial statement amount bridge had reported a source_id and publication_date but emitted PIT_TIME_COMPATIBLE_ONLY_NOT_FORMALLY_ADMITTED. That label overstated what the bridge had actually checked. B79 changes it to SOURCE_REFERENCE_PRESENT_NOT_PIT_VALIDATED_NOT_FORMALLY_ADMITTED, with explicit empty evidence_ids, raw_bytes_verified=false and pit_validation_performed=false.

### B57 provenance details

The ordinary B55/B56/B57 path now carries:
- source_data_classes
- source_evidence_statuses
- claimed_evidence_refs
- source-reference validation issues
- formal Evidence/PIT and Forecast Admission states
- decision_grade_forecast_eligible=false

The B77 financial-statement path separately identifies reported-period source reference IDs / publication dates, Q4 item assumptions and annual diluted-share assumptions. It does not relabel source IDs as Evidence IDs or claim the source files' exact bytes were verified.

B58 and B60 relay the B57 lineage assessment. B76 still performs its conditional arithmetic comparison, but explicitly reports that the result is not a decision-grade forecast and that no formal admission was created.

### Formal signature trust

The signed Evidence/PIT verifier previously returned FORMALLY_ADMITTED after checking signatures even when the signer registry was TEST_ONLY. That contradicted the preflight rule and the empty production signer registry's trust contract.

B79 requires registry_status=ACTIVE and at least one signer entry before final verification can return FORMALLY_ADMITTED. TEST_ONLY, NO_TRUSTED_SIGNERS_REGISTERED, missing or other registry statuses fail closed. The repository's actual authority registry remains NO_TRUSTED_SIGNERS_REGISTERED.

### Forecast / Valuation / Return binding

Added canonical_forecast_evidence_binding_v01.py and a content-addressed signed-admission reference. The resolver:
1. Verifies exact bytes for the signed envelope, Evidence manifest, rights record and permission instrument.
2. Re-runs Ed25519 signatures, rights validation, raw-byte verification and Core/PIT manifest validation.
3. Binds case, market, symbol and cutoff.
4. Requires every Evidence ID referenced by the canonical forecast and valuation to exist as ADMITTED, exact-byte evidence in the same signed manifest and to fall within the market-local cutoff.
5. Returns Evidence/PIT admission information but does not create a Decision or execution authority.

The formal forecast-valuation-return lineage now requires the evidence reference and resolver. A non-empty evidence_ids list or a self-consistent forecast hash is insufficient.

The market-local PIT boundary follows the signed manifest's exact cutoff instant. A date-only cutoff or date-only `known_at` uses Shanghai 00:00, matching Core Evidence/PIT; a signed timestamp such as `2026-10-04T23:59:59+08:00` is honored as the actual cutoff instant. Payload and manifest cutoff strings must still match exactly; the resolver only normalizes the parsed instant for comparison with the forecast's calendar-date identity.

## Regression coverage

- Signed B04 fixture completes when all referenced evidence IDs are in a valid signed manifest.
- Missing Forecast/Valuation evidence ID is rejected.
- Tampered signed envelope bytes are rejected.
- TEST_ONLY signer registry cannot produce FORMALLY_ADMITTED.
- Empty signer registry cannot produce FORMALLY_ADMITTED.
- Xinhecheng B77 forward-only EPS exposes reported source references as not PIT validated, while Q4 / annual share assumptions remain ANALYST_ASSUMPTION.
- B58/B60/B76 keep arithmetic output separate from formal evidence and forecast admission.

## Real-case and authority boundary

Xinhecheng still lacks Q4 Bear/Base/Bull assumptions, annual weighted-average diluted shares and operator-attested current price. The repository's canonical signer registry remains empty. No real FY2026 EPS, formal Forecast/Evidence/Valuation admission, B60 current-price inversion or BUY/NO-BUY decision is created.

PR #587 must remain Draft. Do not merge to the B73 proposal base or canonical main. Real operator macOS end-to-end acceptance remains separately NOT VERIFIED.


## B79 follow-through — signed fixture, lifecycle replay, and report CI (2026-11-07)

- Lifecycle/report/replay tests no longer use unsigned synthetic upstream bundles. `tests/decision_admission_fixture.py` creates an ephemeral, case-scoped ACTIVE Ed25519 registry, permission instrument, rights record and signed Evidence/PIT envelope under the temporary test run root; it resolves the bundle with the same production resolver. No fixture key is added to the production signer registry.
- Date-only `known_at` is interpreted at Shanghai 00:00, matching Core Evidence/PIT; timestamp cutoffs use the signed manifest instant. The real CATL 2026-10-04 end-of-day cutoff is accepted without changing signed manifest bytes.
- The lifecycle fixture requires `cryptography`; C8, C1, DR-02, TR-01/02/03, Investor Report v0.2 and MVP Pilot workflows install it explicitly. C2 Human Report also installs it because its downstream persistence fixtures use the same signed test helper.
- Investor Review Report v0.2's report tests passed (28 tests) on the prior CI run; its post-test failure was a stale historical Actions artifact ID (run 37730232684, no artifact remained). The workflow now creates a small local Publication fixture missing `canonical_run_ref` and asserts the formal writer rejects it without producing report files; this test is self-contained and no longer depends on expired cross-run artifacts.
- B79 remains a Draft PR proposal. Real authority signer registry remains empty. Local Pilot macOS acceptance is still unverified when the macOS job is cancelled.


## B79 final verification — exact PR head 849ccea (2026-11-07)

**GitHub PR #587:** open, Draft, unmerged; base `feat/b73-evidence-driven-remediation-20261031`.  
**Exact verified HEAD:** `849ccea69086c9cef28f728d12532cf58ffce3a7`.

- **PR workflow summary:** 29 success, 1 cancelled, 0 failure.
- **Investment Core CI:** 444 passed.
- **B2-E Natural Language Semantic Decision E2E:** 24 passed in the primary suite plus 8 additional checks.
- **B04-B Mandatory Forecast-Valuation-Return Lineage:** 126 passed.
- **Signed Evidence Admission Gate:** 46 passed.
- **P0 Trusted Runtime Factory:** 37 passed.
- **Investor Review Report v0.2:** 28 passed; the self-contained legacy Publication test was also accepted and the report workflow completed successfully.
- **Local Investment Pilot Linux:** 466 passed. The separate macOS acceptance job was cancelled and remains **NOT VERIFIED**, not PASS.
- Other core production-integration, trust, replay, authority-threat and fresh Xinhecheng jobs also completed successfully on this exact HEAD.

The production signer registry remains empty (`NO_TRUSTED_SIGNERS_REGISTERED`). This is intentional: the signed test registries are ephemeral and case-scoped; no real-company Evidence/PIT/Forecast/Valuation Admission was manufactured by B79. Xinhecheng still needs its Q4 line-item assumptions, annual weighted-average diluted shares and operator-attested current price before its FY2026 EPS / B60 price-implied inversion can be completed.
