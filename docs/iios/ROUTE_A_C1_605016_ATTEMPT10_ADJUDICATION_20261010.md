# Route A C1 — 605016 Attempt 10 Source Adjudication Boundary — 2026-10-10

**Case:** `RC-CN-A-605016-20261009`  
**Cutoff:** `2026-10-09`  
**Capture run:** [GitHub Actions #38026139364](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364)  
**Artifact:** [11660285551](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364/artifacts/11660285551)  
**Result:** **CURRENT-MAIN RAW CAPTURE/INTEGRITY PASS; EVIDENCE/PIT ADMISSION BLOCKED**

## 1. Verified in Attempt 10

- Fresh capture ran against the refreshed intake, payload-type validator, independent raw-byte verifier and B2 preflight on the current-main refresh branch.
- Twelve of twelve declared response bodies were captured; zero transport failures and zero unregistered source refs.
- Independent verification recomputed size and SHA-256 for all 12 saved response byte objects: 12/12 passed.
- All 12 expected payload contracts passed; zero mismatches.
- The correct statuses are `CAPTURED_NOT_ADMITTED`, `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`, and `CAPTURE_COMPLETE_NOT_ADMITTED`.
- Artifact retention is temporary (14 days). Archive the ZIP and keep it bound to the intake receipt, manifest hash, exact-content hashes and attempt ledger before expiration.

## 2. Why evidence admission still fails

- `source_origin_verified=false`: byte integrity does not prove each URL returned the intended issuer/exchange original.
- One source still has unknown PIT timing.
- Sources carry `PUBLIC_ACCESS_REUSE_UNKNOWN` unless a separate review resolves the rights/reuse disposition.
- All seven required field groups remain uncovered by admitted B2 Evidence Records: `security_identity`, `market_price`, `corporate_disclosures`, `business_reality`, `financial_reality`, `capital_structure`, and `trust_governance_events`.
- B2 preflight is `BLOCKED_NOT_ADMITTED`, `evidence_admission=false`, `pit_admission=false`. Twelve captured objects are twelve candidates, not twelve admitted facts.

## 3. Required source-by-source adjudication

For each object in Artifact 11660285551:

1. Reopen exact source bytes and independently recompute SHA-256/size against the intake receipt. Stored response bytes remain the forensic original; decompressed inspection bytes must not replace them.
2. Confirm issuer/exchange identity, document title, stock code, period/date and document number from the body, not only from a URL or index heading.
3. Establish the first-public/known-at basis from a source-backed publication/event record no later than the `2026-10-09` cutoff. Retrieval time is not a substitute.
4. Resolve license/reuse separately from public access; leave unknown as unknown.
5. Extract a narrow fact only with page/table/row locator and attach source-byte digest, source vintage, temporal basis and case/cutoff identity.
6. Run the unchanged core-owned B2/PIT validator. A source group is covered only by individually valid admitted Evidence Records.

## 4. Price and report boundary

- The cutoff requires a defensible **2026-10-09 closing-price observation**, not the older 2026-09-30 close.
- Stockstar published a secondary market-close article on 2026-10-09 at 18:09:28 +08:00: https://wap.stockstar.com/detail/RB2026100900029140. Its numeric quote values are withheld from this public repository because authority/reuse were not admitted and this event is later than the original date-only cutoff. It was not admitted as a price fact.
- The SSE-hosted H1 2026 report locator is an official-source candidate. Publicly rendered content identifies code 605016 / 百龙创园 and the half-year reporting period, but rendered page text does not prove the exact captured response digest or first-public time.

## 5. Decision boundary

Until all seven groups are covered by valid, PIT-admitted records, do not run the formal 605016 valuation/decision pipeline or create an investment report, publication or complete `IIOS_RUN_RECEIPT`. Missing or conflicting data remain `UNKNOWN` / `BLOCKED`; no synthetic evidence or fixture semantic producer may be used as fallback.
