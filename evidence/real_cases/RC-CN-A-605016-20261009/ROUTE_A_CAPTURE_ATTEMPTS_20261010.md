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

## Attempt 2 — registry correction, original failed locator retained

- Workflow run: [38014724607](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014724607)
- Intake: `PARTIAL_CAPTURE_NOT_ADMITTED`; 11/12 sources captured.
- Independent verification: 11 raw files hash/size verified.
- Failed source: `PRICE-INVESTING-HISTORY-2026-10-09`; `HTTP_REQUEST_FAILED`.
- Unregistered sources: **0**; all official SSE sources use `SSE:COMPANY_ANNOUNCEMENT`, and secondary sources are explicitly registered as `SECONDARY_VALIDATION`.
- Artifact: [11655484327](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014724607/artifacts/11655484327).

Source registration resolves provenance classification only. It does not establish source origin, factual accuracy, licensing or PIT admission.

## Attempt 3 — Sohu replacement for inaccessible Investing page

The manifest now uses `https://q.stock.sohu.com/cn/605016/lshq.shtml` as the free historical-price acquisition candidate under `SOHU:MARKET_HISTORY_PAGE`. The original Investing failure remains preserved above. This retry can at most establish raw-byte capture/integrity; it cannot admit the 2026-10-09 closing price.

## Explicit gate boundary

All captured facts remain `NOT_ADMITTED` until issuer/exchange origin, known-at basis, license/reuse status, field-level locator, source-vintage and B2/PIT validation are independently reviewed. All seven required groups remain uncovered for decision purposes; no valuation, formal Decision Revision, publication or report is authorized by this capture record.
