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

The market-local PIT boundary uses Shanghai 00:00 on cutoff date, matching the existing A-share evidence contract.

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
