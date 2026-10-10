# Route A capture attempts — RC-CN-A-605016-20261009

Date recorded: 2026-10-10  
Case cutoff: 2026-10-09  
Status: **RAW CAPTURE DIAGNOSTICS ONLY — NOT ADMITTED**

## Attempt 1 — original 12-source candidate set

- Workflow run: [38014567975](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014567975)
- Manifest SHA-256: `7a3092b47417319ff24a0f14cad070c810126bd6cb19b0fc56f87c18bc9ae5be`
- Intake: `PARTIAL_CAPTURE_NOT_ADMITTED`; 11/12 sources captured.
- Independent verification: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`; 11 raw files hash/size verified.
- Failed source: `PRICE-INVESTING-HISTORY-2026-10-09`; error code `HTTP_REQUEST_FAILED`.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; no evidence or PIT admission.
- Artifact: [11655558984](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014567975/artifacts/11655558984), 14-day Actions retention.

The failed Investing row is preserved here as acquisition history. It is not silently recoded as success or dropped from the incident record.

## Source-ref correction

The captured run showed no unregistered source references after the source registry correction: the eleven official SSE items use `SSE:COMPANY_ANNOUNCEMENT`; secondary carriers have their own explicit `SECONDARY_VALIDATION` registry entries. Registration does not establish evidence origin, factual accuracy, licensing or PIT admission.

## Attempt 2 — current retry

The inaccessible Investing historical page has been replaced with Sohu's free history page as a new acquisition candidate. The original failed source and its error remain in Attempt 1 above. A successful recapture, if obtained, will mean only raw-byte capture/integrity; it will not admit the 2026-10-09 closing price.

## Explicit gate boundary

All captured facts remain `NOT_ADMITTED` until issuer/exchange origin, known-at basis, license/reuse status, field-level locator, source-vintage and B2/PIT validation are independently reviewed. All seven required groups remain uncovered for decision purposes; no valuation, formal Decision Revision, publication or report is authorized by this capture record.
