# Route A C1 — 605016 Real Source Adjudication, Attempt 10 — 2026-10-10

**Case:** `RC-CN-A-605016-20261009`  
**Security:** 百龙创园 / 605016.SH  
**PIT cutoff:** `2026-10-09` (original date-only cutoff; no end-of-day reinterpretation)  
**Input:** actual Attempt 10 GitHub Actions artifact [#11660285551](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364/artifacts/11660285551) from run [#38026139364](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364).

## Decision

**Source byte verification: PASS. Source-by-source factual adjudication: PARTIAL PASS. Full B2 Evidence/PIT manifest: MUST REMAIN BLOCKED until the market-price record is admitted.**

The Attempt 10 receipt binds raw intake-manifest SHA-256 `563bc41ab2e6ce4925451fc02986f87409e06b879e3b92066d443ef6d796f244`. The original 12-file capture remains immutable and unchanged. The new ledger `evidence/real_cases/RC-CN-A-605016-20261009/SOURCE_ADJUDICATION_20261010.json` binds source identity decisions, publication-time precision, reuse disposition and fact locators to that capture.

This is not an attempt to relabel the original `CAPTURED_NOT_ADMITTED` receipt. The fresh workflow independently re-hashes the real raw bytes and invokes the existing `research.b2.company_evidence.build_company_evidence_manifest` and its unchanged PIT validator.

## Publication time and reuse rules

- For older official SSE filings, the published **date** is supported by the official SSE-hosted archive path and the document's matching issuer name, code, title and announcement number. Exact intraday first-public times were not exposed in the accessible archive. The ledger preserves this loss of precision rather than manufacturing a timestamp. Those source dates precede the 2026-10-09 cutoff.
- For the 2026-10-09 shareholders' meeting resolution, the official SSE-hosted PDF is dated 2026-10-09. The captured secondary article [Stockstar, timestamp 18:09:28 +08](https://wap.stockstar.com/detail/RB2026100900029140) references that same resolution. The run records 18:09:28 as a **conservative latest-known bound**, not as a claim that the SSE PDF was first published at that exact second. Under the unchanged core PIT contract, the date-only cutoff `2026-10-09` is interpreted at the start of that local date, so this event is **not eligible** for this case's cutoff. It remains in the source-adjudication ledger but is excluded from the B2 candidate manifest. A separate pre-cutoff official SSE disclosure no. 2026-042 dated 2026-09-11 covers the corporate-disclosures group with the narrower fact that convertible-bond registration was still pending at that date.
- The official SSE [legal statement](https://www.sse.com.cn/home/legal/) permits browsing/downloading for non-commercial purposes but restricts reuse/distribution without authorization. Official SSE captures are classified operationally as `RESTRICTED_NO_REDISTRIBUTION` for this internal research use; do not upload source PDFs/HTML to Git or redistribute them. Only fact-level records, locators and hashes are included in this review package.
- Secondary-source licence/reuse has not been adjudicated. The captured price article is therefore explicitly retained as an UNKNOWN candidate, not admitted market-price evidence.

## Source-by-source adjudication

| Captured source | Body/origin result | Publication/PIT result | Reuse/result |
|---|---|---|---|
| `SSE-H1-2026-FULL` — SHA-256 `a5df7754ac08d50f47c6f91d9a8af4e99cbc98894cfa3d6a94dfbeb7bdc3f35c` | Official SSE host; PDF p.1 identifies 山东百龙创园生物科技股份有限公司, 605016, 百龙创园. | Archive date 2026-08-31; exact intraday time unavailable, but safely before cutoff. | Restricted/no redistribution. Admit specific identity, H1 financial and 2026-06-30 share-base facts only. |
| `SINA-2025-ANNUAL-REPORT-PAGE` — SHA-256 `3fddcf95747f8d44f1a14d848d875c922535f74996f8abc78ca5bddabaab2e65` | Exact HTML verified, but it is a secondary mirror, not the issuer/exchange original. | Secondary listing date 2026-04-08; no need to rely on it. | Rights unknown; exclude from the admitted evidence set because primary Q1/H1 reports are available. |
| `SSE-Q1-2026-FULL` — SHA-256 `1f630ef7d8c62acef307eeb5362c9dbbacec326bad5925e1431317adc70e0d2d` | Official SSE host; PDF p.1 identifies the 2026 Q1 report and code 605016. | Archive date 2026-04-30; exact intraday time unavailable, before cutoff. | Restricted/no redistribution. Admit the specifically located Q1 financial table. |
| `SSE-H1-OPERATING-DATA-2026` — SHA-256 `d30d62a097f68d3137788d5980dabb7577e1e23d320061554686ff19e43a2196` | Official SSE host; body matches title and announcement no. 2026-038. | Archive date 2026-08-31; body says H1 figures are unaudited. | Restricted/no redistribution. Admit the located H1 product-mix table as unaudited reported data. |
| `SSE-2026-09-SUBSIDIARY-INVESTMENT` — SHA-256 `d6baad120437e6969eedef87f298c1583eaeaa4ac79ddc25eccaee7583a97caa` | Official SSE host; title/body/code and announcement no. 2026-041 match. | Archive date 2026-09-10; exact intraday time unavailable, before cutoff. | Restricted/no redistribution. Admit only the announced RMB 10m, 100%-owned Kunming subsidiary investment. |
| `SSE-2026-10-09-SHAREHOLDERS-MEETING` — SHA-256 `89136a9f3e6410c2f4c420cb516fb88c8368fa3e8767efdb12a3727fa0025936` | Official SSE host; title/body/code and announcement no. 2026-048 match. | Announcement dated 2026-10-09; exact SSE first-public minute unavailable; known publicly by 18:09:28 +08 from corroborating secondary coverage. | Restricted/no redistribution. Keep as a source-ledger fact only; exclude from this date-only-cutoff B2 manifest because known_at is after the cutoff instant. |
| `SSE-2026-09-CONVERTIBLE-BOND-UPDATE` — SHA-256 `5c18d08896a99d65a844644e7314d3c48915cd0a2ab8f58a477784c5e164dddb` | Official SSE host; title/body/code and announcement no. 2026-042 match. | Archive date 2026-09-11; exact intraday time unavailable, before cutoff. | Restricted/no redistribution. Admit procedural status only: CSRC registration was still pending; no final issuance/terms are inferred. |
| `SSE-2026-CONVERTIBLE-BOND-PROSPECTUS` — SHA-256 `23b5a43f9107df57110a57911f931e93288fe91226673c7f332a0c184803d767` | Official SSE-hosted April application draft; body identifies the company/code and calls itself “申报稿”. | Date-level source vintage 2026-04-30. A 2026-09-11 notice says application documents were subsequently updated after the H1 report. | Restricted/no redistribution; exclude from current-final-terms claims as superseded/historical. |
| `SSE-2026-H1-DIVIDEND-PLAN` — SHA-256 `2d3044e4bedc4039a22dd98cc17eab2fc73e00951c700c07bd64a77255a98a3b` | Official SSE host; body is the H1 dividend **proposal**, announcement no. 2026-036. | Proposal published 2026-08-31. SSE announcement list shows a later 2026-09-22 “2026年半年度权益分派实施公告” for 605016. | Restricted/no redistribution; exclude for the actual implemented dividend state. The later implementation PDF still needs raw capture and inspection. |
| `SSE-2026-07-PLEDGE-RELEASE` — SHA-256 `f4daed15f824900bc553e4d31fbdf2994e70682cc43cd9e8a33a4fcba5d025bf` | Official SSE host; title/body/code and announcement no. 2026-033 match. | Archive date 2026-07-24; exact intraday time unavailable, before cutoff. | Restricted/no redistribution. Admit the located pledge-release/extension facts, clearly bounded to this announcement. |
| `PRICE-STOCKSTAR-2026-10-09` — SHA-256 `0d78fe37969224552a3309e85d078a352f864b77d9c4f785db50329dd9562f98` | Exact secondary article/page and publication timestamp verified; underlying quote-data authority not independently established. | Article posted 2026-10-09 18:09:28 +08; numeric quote fields withheld from this public repository because authority/reuse were not admitted and the event postdates the original cutoff. | Reuse unresolved. Keep date/hash only; do not reproduce numeric values or use this secondary item as B2 evidence. |
| `PRICE-SOHU-HISTORY-2026-10-09` — SHA-256 `1e18871c74111367957660d6b6510b463b1955424c49330c9b43a097bf07a8be` | Exact HTML bytes verified, but captured content is a page/navigation shell and contains no usable dated close-price rows. | No defensible known-at basis. | Rights unknown; exclude. It does not support the required market-price field. |

## Fact-level results and their limits

The adjudication ledger contains eleven fact candidates: ten source-backed fact candidates from official SSE filings plus one deliberately UNKNOWN secondary price candidate. One same-day meeting fact (known at 18:09:28+08 on the cutoff date) is excluded from the B2 candidate manifest by the unchanged date-only PIT rule. Six groups pass the unchanged B2/PIT gate; market_price remains uncovered.

- **Security identity:** issuer name, short name and code from the H1 report cover.
- **Financial reality:** Q1 reported revenue/net profit/operating cash flow; H1 reported revenue/net profit/operating cash flow, with audit status preserved.
- **Business reality:** H1 product revenue mix and the announced RMB 10m Kunming subsidiary investment.
- **Corporate disclosures:** the 2026-09-11 official convertible-bond update (announcement no. 2026-042), narrowly recording that CSRC registration remained pending at that date. The 2026-10-09 meeting resolution is separately retained in the source ledger but excluded from B2 because its known_at is after the date-only cutoff.
- **Capital structure:** 420,012,320 shares **as of 2026-06-30** (not asserted to be the 2026-10-09 share count), and convertible-bond registration status as of the 2026-09-11 update.
- **Trust/governance:** the exact July pledge release/extension facts.

The market-price group remains unadmitted. It is unsafe to infer a price from the Sohu shell, nor to silently promote a secondary article to an authoritative close merely because its captured bytes hash correctly.

## Actual B2/PIT execution — SUCCESSFUL fail-closed BLOCKED result

The adjudication was executed against the **real Attempt 10 GitHub Actions artifact**, not a synthetic fixture:

- Source-adjudication workflow run [#38038481645](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38038481645), code head `a4752719595869f37863900fb3f2b28767d4dc45`, job `adjudicate-real-attempt-10`: **SUCCESS**.
- Input capture artifact [#11660285551](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38026139364/artifacts/11660285551), intake manifest SHA-256 `563bc41ab2e6ce4925451fc02986f87409e06b879e3b92066d443ef6d796f244`.
- Output JSON artifact [#11663494596](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38038481645/artifacts/11663494596), ZIP SHA-256 `10918db5f6393a2ffd81ab4fae8a07d15ebd64fc0fd0b88eb371910ef9926294`.
- Independently reverified raw source size/hash: **12/12 PASS**; expected payload contract: **12/12 PASS**.
- Adjudication ledger: 11 candidates (ten official-filing facts, including one same-day fact excluded by PIT, plus one UNKNOWN market-price candidate). B2 manifest: ten records (nine status-ADMITTED records and one UNKNOWN price record); one post-cutoff meeting fact was excluded before manifest validation.
- **B2 manifest status: BLOCKED**. Six groups pass unchanged core PIT validation: `security_identity`, `corporate_disclosures`, `business_reality`, `financial_reality`, `capital_structure`, and `trust_governance_events`.
- The only remaining required group is `market_price`.
- Exact core-validator errors:
  1. `EVIDENCE[605016-PRICE-CANDIDATE-20261009]:PIT:PIT_UNKNOWN: source availability/provenance is not established`
  2. `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`

The original date-only cutoff `2026-10-09` was preserved. The 2026-10-09 18:09:28 +08 shareholders' meeting resolution remains in the source ledger but is excluded from the B2 admission manifest; a separate pre-cutoff official announcement no. 2026-042 dated 2026-09-11 now covers the corporate-disclosures group. The validator, required groups and cutoff semantics were not relaxed or changed.

The run summary is preserved at `evidence/real_cases/RC-CN-A-605016-20261009/SOURCE_ADJUDICATION_RUN_20261010.json`. Only machine-readable JSON results were uploaded; captured source PDFs/HTML were not re-uploaded as result artifacts.

## Unchanged B2/PIT admission result

The dedicated workflow downloads the actual Attempt 10 artifact, independently re-hashes all 12 raw sources, builds the fact-level candidate manifest from the source-adjudication ledger and calls the core-owned, unchanged `research.b2.company_evidence.build_company_evidence_manifest` validator.

- Six of seven required groups are covered by source-adjudicated, PIT-eligible official Evidence Records.
- In the earlier Attempt-10-only run, `market_price` remained UNKNOWN because secondary-source authority/reuse were not admitted. The later official HTTPS run #38050190177 passed ephemerally through unchanged B2/PIT; canonical private persistence remains OPEN.
- Final manifest remains `BLOCKED`; `evidence_admission=false`, `pit_admission=false`.
- No valuation, Decision Revision, Machine Publication, Investor Review Report or complete `IIOS_RUN_RECEIPT` is authorized.

## Latest official HTTPS B2 result — 2026-10-10

The current exact-head run [#38050190177](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38050190177) completed successfully. The unchanged core B2/PIT validator returned **PASS** for an ephemeral candidate manifest: 11 admitted records, all seven required groups, zero validation errors. Sanitized report artifact [#11669076729](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38050190177/artifacts/11669076729) contains hashes, source URL/date, response shape and gate status only; it omits numerical quote values, raw price bytes and the full manifest. The current machine record is `evidence/real_cases/RC-CN-A-605016-20261009/OFFICIAL_HTTPS_B2_ADJUDICATION_20261010.json`.

This is **PASS_EPHEMERAL_B2**, not persistent canonical admission. The private local tool must still be rerun on the operator's Mac, after which its persisted candidate must pass the Investment Core-owned validator. `known_at` uses the prior market-session close event time and is not an exact endpoint first-public timestamp; independent review remains required. No decision/report/Run Receipt or production Host acceptance is authorized by this workflow.

## Next real-data gates

1. Capture and byte-verify the official 2026-09-22 H1 dividend **implementation** notice from SSE; replace the stale proposal for implementation facts.
2. Obtain a defensible official/free historical close-price record for 2026-10-09, or explicitly retain the price as UNKNOWN. Review source terms/reuse before changing its status.
3. Rerun the unchanged B2/PIT validator. Do not change its required groups, PIT semantics or status gates to force PASS.
4. Only once all seven required groups are admitted can a real 605016 canonical run continue to source-authorized Forecast/Valuation, Decision, publication/report and receipt replay.
5. Independently inspect the deployed Host configuration and execute one genuine host-origin run. TEST_ONLY semantic producers and fixture admissions are prohibited as a fallback; P0-LLM-001 / P0-LLM-004 remain OPEN pending that proof.
