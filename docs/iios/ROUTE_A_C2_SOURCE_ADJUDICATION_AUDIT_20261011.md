# Route A C2 — 新和成 002001 Source and PIT Adjudication Audit

**Audit date:** 2026-10-11  
**Case:** `RC-CN-A-002001-20261009`  
**Record class:** DIAGNOSTIC / exact-byte integrity verified; **not Evidence/PIT admission**  
**Canonical cutoff semantics:** date-only `2026-10-09` means the start of that local date under the IIOS Core/PIT contract.  
**Source artifact:** Run #8 archive `route-a-xinhecheng-run8.zip`  
**Archive SHA-256:** `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`  
**Intake manifest SHA-256:** `c6ec425f3c2ef5404bbdd1868e57434c64da90e255bcde5eae24586dba1227e3`  
**Existing B2 preflight manifest SHA-256:** `934dacbc3c9cda419018826ef91129a2a13219380469320bf22901bbabb7bce2`

## 1. Independent archive and raw-byte recheck

The original Run #8 archive was materialized from the user's existing non-Git file library, its ZIP SHA-256 was independently recomputed, and its manifest/receipt were parsed. All eight captured raw objects matched both the receipt-declared byte count and SHA-256. The ninth declared source, the Eastmoney K-line API, has no captured bytes; no hash is claimed. The archive contained 13 files including receipt, manifest and validator reports, and remains outside the public repository.

| Source ID | Byte count | SHA-256 | Current source/vintage disposition |
|---|---:|---|---|
| `ISSUER-IR-PAGE-CURRENT` | 21,953 | `18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c` | Dynamic current page; no historical publication time; not PIT-admitted |
| `SZSE-2026-H1-FULL` | 980,820 | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | Official exchange-hosted PDF candidate; filing date in URL/path is 2026-08-20; fact-level locator and internal-use/reuse adjudication remain required |
| `SZSE-2026-H1-SUMMARY` | 144,809 | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | Official exchange-hosted PDF candidate; filing date in URL/path is 2026-08-20; fact-level locator and internal-use/reuse adjudication remain required |
| `SZSE-2026-Q1-FULL` | 221,878 | `facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa` | Official exchange-hosted PDF candidate; filing date in URL/path is 2026-04-29; fact-level locator and internal-use/reuse adjudication remain required |
| `SZSE-2026-BUYBACK-PLAN` | 142,384 | `e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9` | Official exchange-hosted PDF candidate; filing date in URL/path is 2026-06-24; fact-level locator and internal-use/reuse adjudication remain required |
| `SZSE-2026-BUYBACK-PROGRESS-SEP` | 84,057 | `af6ad44d49b10b0f23306e0812fa64200880b29883bcaa71fecaf6b54a8ac6ed` | Official exchange-hosted PDF candidate dated 2026-10-09; excluded from this case's date-only cutoff unless independent pre-cutoff availability is established |
| `PRICE-SOHU-HISTORY` | 21,829 | `0f05a4c643ef19de9d313c4231ab200386b6946920c066fb104d23ebb683efd3` | Captured page bytes but no admitted dated close-price fact; source-vintage and reuse unverified; exclude from admission |
| `PRICE-EASTMONEY-QUOTE` | 56,928 | `97bf733ac8f7d1fd14bb3377fd85041940b4ef225349bdc07710f9c22a827cfa` | Captured quote-page bytes but no admitted date-bound price fact; source-vintage/reuse not admitted; exclude from admission |
| `PRICE-EASTMONEY-KLINE-API` | — | — | Capture failed; no raw bytes, no SHA-256, no evidence admission |

The raw capture is an integrity pass only. It does not establish source-origin admission for every item, does not transform extracted text into admitted facts, and does not prove license/reuse rights.

## 2. Critical cutoff-semantic defect in the historic preflight

The Run #8 B2 manifest records `cutoff_date=2026-10-09T23:59:59+08:00`, and its preflight report repeats that end-of-day interpretation. This conflicts with the canonical IIOS date-only PIT rule, which interprets the case cutoff `2026-10-09` as `2026-10-09T00:00:00+08:00`.

Consequences:

- The old Run #8 B2 validator result is a diagnostic artifact only; it is not admissible as a canonical PIT proof.
- The buyback-progress PDF whose official archive path is dated 2026-10-09 cannot be back-applied before the cutoff when only date-level publication evidence is available. Keep it excluded/UNKNOWN unless evidence establishes that it was public before the cutoff instant.
- A 2026-10-09 closing-price observation is after the case cutoff instant. A candidate for this date-only case must use the latest fully completed session before the cutoff (2026-10-08) and establish both source-vintage and permitted research use.
- Do not edit the cutoff timestamp on the old manifest and reuse its audit digest/fingerprint. Rebuild a successor from the same preserved raw objects, explicitly retain the original diagnostic, and re-run the unchanged Core/PIT validator against the canonical date-only cutoff.

Current result remains `BLOCKED / NOT_ADMITTED`. No field group is admitted by the old artifact-level source records.

## 3. Official-source and reuse boundaries

The four older filing PDFs bind to official SZSE-hosted paths:

- H1 full report: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/83165436-1015-4d77-919c-97c8cce0c67d.PDF
- H1 summary: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/6d1ad0be-5e22-482b-a163-2ebb0b6d1d95.PDF
- Q1 report: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-29/094c9e5d-f2de-4411-b604-b2aece32f35b.PDF
- Buyback plan: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-24/53248225-c2cf-45cf-a0fd-a6c9fee4f267.PDF

The captured first pages identify the issuer and report titles. Their official archive dates precede the cutoff, so they are viable candidates for fact-level source-vintage review, but no numerical or narrative fact becomes admitted until it has a field-level PDF page/table/row locator, exact raw-object binding, source-origin adjudication, cutoff-safe `known_at` and a conservative reuse disposition.

The SZSE describes SSIC as exclusively authorized to manage/distribute SZSE securities information and describes end-of-day close data as a market-data service: https://investor.szse.cn/English/services/dataServices/index.html. Publicly accessible does not itself mean unrestricted automated market-data reuse. For the historical close-price gate, do not promote the captured Sohu/Eastmoney pages or the failed Eastmoney API attempt. Independently source the 2026-10-08 official/free close or preserve `market_price=UNKNOWN`; separately record the applicable internal-use / redistribution boundary.

## 4. Next actions and pass criteria

1. Build a new C2 fact-level source ledger from the preserved raw objects. Do not mutate the Run #8 receipt, archive, manifest or preflight output.
2. For the four pre-cutoff official filing PDFs, record source identity, publication-date basis, exact byte hash, page/table/row locators per fact and a cautious no-redistribution/internal fact-level use class. If reuse remains unresolved, leave the facts UNKNOWN rather than guessing.
3. Use a date-only `2026-10-09` cutoff. Exclude the 2026-10-09 same-day buyback notice from the active manifest unless an independently supported pre-cutoff timestamp exists.
4. Resolve an official/free 2026-10-08 closing-price source, including source-vintage/known-at and whether the access route is permitted for this internal non-commercial research. No numeric quote value or raw market-data bytes may be committed to the public repository.
5. Cover all seven mandatory field groups with case-bound fact records, then run the unchanged company Evidence/PIT validator and a fresh independent review. Any uncovered group keeps the case BLOCKED.

**Non-claims:** This audit does not admit facts, pass B2, certify reuse rights, create a formal signed admission, accept a production Host, create a Decision, or authorize a trade.


## 5. Official-source page cross-check — 2026-10-11

The exact URLs for the four pre-cutoff official PDF sources were opened independently on the public SZSE static-document host. The visible PDF content confirms the issuer/security identity and document titles. Supporting official same-day board resolutions also state that the respective report/announcement was published to designated disclosure media on that date:

| Raw source in Run #8 | Official document identity | Publication-date cross-check | Conservative PIT upper bound | Current disposition |
|---|---|---|---|---|
| `SZSE-2026-H1-FULL` | 2026 H1 full report; cover identifies 浙江新和成股份有限公司 | Official archive path `2026-08-20`; board resolution announcement `2026-034` says the H1 report was disclosed in the designated media on the same day | `2026-08-20T23:59:59+08:00` | Source/date candidate verified; byte hash independently verified from Run #8; exact intraday first-public time not known |
| `SZSE-2026-H1-SUMMARY` | H1 report summary; PDF identifies code 002001 / 新和成 / announcement `2026-035` | Archive path `2026-08-20`; same-day board resolution `2026-034` names the report and summary and states same-day disclosure | `2026-08-20T23:59:59+08:00` | Source/date candidate verified; byte hash independently verified from Run #8; exact intraday first-public time not known |
| `SZSE-2026-Q1-FULL` | Q1 report; PDF identifies code 002001 / 新和成 / announcement `2026-021` | Archive path `2026-04-29`; board resolution announcement `2026-020` dated 2026-04-29 states that the Q1 report was disclosed in designated media the same day | `2026-04-29T23:59:59+08:00` | Source/date candidate verified; byte hash independently verified from Run #8; exact intraday first-public time not known |
| `SZSE-2026-BUYBACK-PLAN` | Buyback-plan announcement; PDF identifies code 002001 / 新和成 / announcement `2026-027` | Archive path `2026-06-24`; board resolution announcement `2026-026` dated 2026-06-24 states the buyback plan was disclosed in designated media/CNINFO the same day | `2026-06-24T23:59:59+08:00` | Source/date candidate verified; byte hash independently verified from Run #8; exact intraday first-public time not known |

Publicly accessible supporting document locators (the support PDFs were reviewed through the public web but their bytes were **not** added to the Run #8 archive or locally re-hashed in this task):

- H1 board resolution `2026-034`: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/a0f47443-c60c-4e88-b444-bf3e0da5372e.PDF
- Q1 board resolution `2026-020`: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-29/03e7b79f-9516-4062-854f-34f5c29dc093.PDF
- Buyback-plan board resolution `2026-026`: https://disc.static.szse.cn/disc/disk03/finalpage/2026-06-24/0f51c1d5-2f3d-4f07-9f7c-c02bfd2c63a4.PDF

The conservative date-end bounds above are all strictly before the canonical date-only cutoff instant `2026-10-09T00:00:00+08:00`. They are upper bounds, not a claim that the first-public time occurred at 23:59:59. The archived PDF bytes remain the fact source and retain their existing local SHA-256s. A final B2 successor must bind each fact to its exact archive object and page/table/row locator, record a cautious non-redistribution/internal-research disposition, and pass the unchanged Core/PIT validator.

### 5.1 Source-use distinction

SZSE's own Data Services page describes SSIC as authorized to manage/distribute SZSE securities information and describes closing-price data as end-of-day market data service: https://investor.szse.cn/English/services/dataServices/index.html. This supports keeping market-price data behind a separate source-reuse gate. It does **not** mean the four corporate-filing PDFs and market-quote pages share the same reuse status, and it does not establish an unrestricted license for bulk redistribution of filing PDFs.

For the filing documents, use the narrowest internal-research handling: original files stay in the private evidence store, public Git contains only source references/hashes/locators and adjudication status, no PDF bytes or full numeric tables are redistributed, and extracted facts are still candidates until the manifest rebuild is Core/PIT validated. This handling is a conservative workflow disposition, not a legal opinion or an assertion of a broad redistribution license.

### 5.2 Current fact-candidate coverage

From the existing 11 page-located extraction candidates, the 2026-10-09 buyback-progress fact is excluded by the date-only cutoff. The other 10 candidates bind to the earlier H1 documents; the buyback-plan PDF adds a possible earlier trust/governance fact, and the dated official H1 filing record can supply a corporate-disclosure candidate. These are **source-qualified candidates**, not yet newly emitted ADMITTED Core Evidence Records.

- Candidate-capable groups: `security_identity`, `corporate_disclosures`, `business_reality`, `financial_reality`, `capital_structure`, `trust_governance_events`.
- Still not covered by an admitted record: `market_price`. The two captured Sohu/Eastmoney pages remain `UNKNOWN_NO_KNOWN_AT`; the Eastmoney K-line source still has no bytes/hash.
- Overall case status remains `BLOCKED_NOT_ADMITTED`. The historic manifest's end-of-day cutoff is not repaired in place; a successor must be built with canonical date-only cutoff semantics.


## 6. Successor execution result — 2026-10-11 (supersedes the earlier "next actions" snapshot, not the original diagnostics)

**Result class:** `C2_SUCCESSOR_CORE_VALIDATION_REPORT_NOT_FORMAL_SIGNED_ADMISSION`. The Run #8 ZIP, receipt, intake manifest, source files and legacy B2 preflight remain unchanged.

- PR [#333](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/333) fixed date-only Route A cutoff normalization across implementation, tests and schema. The case cutoff is now represented as `2026-10-09T00:00:00+08:00` in the successor; no historic cutoff digest was reused.
- PR [#334](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/334) merged at `00be321497baf9cf0352ae14b303c560bc5846b7`. Exact-head workflow [#38121849097](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38121849097) completed SUCCESS. The GitHub Actions downloader verified the pinned Run #8 artifact SHA-256 before extraction; all eight captured raw objects were then independently re-checked against receipt sizes and hashes.
- The old Run #8 intake schema predates the optional payload-contract fields. The verifier initially failed specifically with `EXPECTED_PAYLOAD_TYPE_BINDING_MISMATCH`. A narrow compatibility view inserted only default `ANY` / `NOT_CHECKED` fields in a temporary verification copy, then reran the existing `verify_intake`; it did not modify the preserved ZIP, receipt, manifest or raw data. Any non-default value or any other verification error still blocks.
- Thirteen field-level fact candidates matched their exact locators across three official SZSE PDF source files. The candidate records are case-bound, hash-bound and field-located. Conservative publication-date end-of-day bounds are used for `known_at`; `published_at` remains a date-level value. **Exact first-public intraday timestamps remain unverified** and supporting board-resolution PDF bytes were not present in the original capture.
- The unchanged `research.b2.company_evidence.build_company_evidence_manifest` validator returned exactly one required-group error: `REQUIRED_FIELD_GROUPS_UNCOVERED:market_price`. The ephemeral candidate covers the other six groups. The overall manifest is still **BLOCKED**; this is not a signed/formal admission or final seven-group pass.
- Required market-price observation is **2026-10-08** for the original date-only cutoff. It remains `BLOCKED_UNKNOWN` because the preserved Run #8 artifact has no admitted date-specific close with an approved source-vintage and allowed-use record. The 2026-10-09 buyback-progress filing and close, dynamic issuer IR page, and Sohu/Eastmoney quote pages remain excluded.
- The sanitizer uploaded report-only artifact [#11695761835](https://api.github.com/repos/kebofeierdawei5-cloud/convergence-research/actions/artifacts/11695761835) (SHA-256 `92998897c04368da516a0987506f928bd07834cb9c4f889372b5c9e4c8f8d6ee`). The report is preserved in Git at `evidence/real_cases/RC-CN-A-002001-20261009/C2_SUCCESSOR_CORE_VALIDATION_REPORT_20261011.json`; it contains no raw PDFs or numeric market quote values. The temporary B2 manifest is not published.
- **Still open:** independent source/vintage and permitted-use review; price source admission; formal signed Evidence/PIT admission; production Host acceptance; Decision, Publication, complete Run Receipt and execution authority. No market-price value was inferred or fabricated.

**Next action:** independently review the 13 fact candidates and their source-use/vintage basis, then locate an official/free 2026-10-08 close whose source-vintage and permitted internal research use can be demonstrated. If no such source passes, leave `market_price=UNKNOWN` and B2 blocked.


## 7. Market-price source search and permission decision — 2026-10-11

**Disposition: `NO_ADMITTED_PRICE_SOURCE_FOUND; market_price remains UNKNOWN`.** This is a source-authority/permission finding, not a claim that the historical close itself is unknowable.

| Candidate | What was verified | Why it is not admitted for this C2 case |
|---|---|---|
| Official SZSE historical quote UI: https://www.szse.cn/market/trend/index.html?code=002001 | SZSE publishes a public site area with a `行情信息` / `历史行情` view. The direct page could not be reliably retrieved by this execution environment. | No original response bytes/page capture was obtained for the 2026-10-08 row in this run. Separately, SZSE's data-services description says SSIC is exclusively authorized to manage/distribute SZSE securities information and explicitly describes end-of-day closing-price data as a market-data service (https://investor.szse.cn/English/services/dataServices/index.html). This does not establish an unrestricted or permitted-for-local-retention grant for the proposed evidence use. |
| Official CNINFO / SZSE Information Data Service: https://webapi.cninfo.com.cn/ | The platform advertises a domestic stock quote center, historical quotes, API documentation and a data mall, and states that its content comes from public disclosure material. | The public landing page does not by itself establish that a historical daily-close record is free of registration/permission conditions or that its terms permit exact-byte retention in this private IIOS evidence store. No price payload/raw bytes were captured. |
| Investing.com historical page: https://cn.investing.com/equities/zhejiang-nhu-a-historical-data | Public search/web rendering exposes a date-specific historical-price table for the case's required date. | Its current terms warn that prices may not be sourced from the exchange and may be indicative; they prohibit use, storage, reproduction, display, modification, transmission or distribution of site data without prior explicit written permission from Fusion Media and/or the data provider (https://cn.investing.com/about-us/terms-and-conditions). Excluded; no value from this page is promoted into the manifest and no numeric quote value is recorded here. |
| Yahoo Finance historical view / API | Public-facing historical quote pages may show the same session. | Yahoo's Terms prohibit automated collection without express prior permission (https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html); Yahoo's own market-data help says not to redistribute information and describes it as informational, not intended for investing/trading (https://help.yahoo.com/kb/SLN2352.html). This does not supply a clean, admitted PIT + allowed-use route for this formal C2 gate. |
| Preserved Sohu/Eastmoney pages or K-line request from Run #8 | Existing capture bytes for two page candidates are hash-verified; the K-line API capture has no bytes. | The page candidates have no admitted date-specific `known_at`/permitted-use record; the K-line API failed capture and has no hash. They remain excluded as already recorded in the machine review. |

### Current gate and authorized path to continue

- Required price observation remains the latest fully completed session before case cutoff: **2026-10-08**. The case cutoff remains `2026-10-09T00:00:00+08:00`; no same-day close is admissible.
- A web search result or visible historical table can identify a candidate value but does not prove exact captured-byte integrity, source vintage, or permitted use in the local decision system. No numeric price was added to this public audit.
- The free-first next step is an **operator-supplied original quote artifact obtained through a source the operator is entitled to use for personal/internal research**—prefer an official broker statement, broker historical-price export, or an official/provider document with a clear date/source. Keep that artifact in the user's private workspace, not in GitHub. IIOS must still hash its exact bytes, bind it to 002001 and 2026-10-08, review source/known-at and use restrictions, and pass an independent Evidence/PIT check. A typed number with no source artifact is insufficient.
- If no such original artifact and adequate permitted-use basis can be supplied, preserve `market_price=UNKNOWN`; do not weaken the Core/PIT validator or label overall B2 as PASS.

**Non-claims:** No formal market-price admission, signed admission, production Host acceptance, Decision, Publication, complete Run Receipt or execution authority was created by this source search.


## 8. Operator-submitted Stockstar market-price candidate — 2026-10-11

**Disposition: `CANDIDATE_LOCATED_NOT_ADMITTED`.** `market_price` remains UNKNOWN and C2 remains BLOCKED.

- The operator supplied the page locator https://stock.stockstar.com/RB2026100900002546.shtml together with a typed transcription of daily market fields. Direct retrieval of that exact page was unavailable in this review; no original response bytes, byte count, or SHA-256 were obtained. The typed transcription is not a substitute for the original source artifact.
- A separate related Stockstar page, https://stock.stockstar.com/RB2026100800017267.shtml, is discoverable in public search with the publisher timestamp **2026-10-08 15:55:43 +08:00** and a report referring to the same security/session. That timestamp is before the case cutoff and is a useful source-vintage lead, but what was verified here is a search rendering, not a captured page response. No exact-byte integrity claim is made.
- Stockstar's legal notice (https://info.stockstar.com/aboutus/disclaimer.htm) states that site content is protected and restricts unauthorized copying/reproduction and derivative use. The Shenzhen Stock Exchange's published trading rules (https://investor.szse.cn/disclosure/notice/t20060515_499577.html) state that exchange trading information belongs to SZSE and restrict unlicensed use/propagation. Neither the linked Stockstar page nor the related search result establishes an applicable grant for exact-byte retention in the private IIOS evidence store. This audit does not make a legal conclusion; it records that permission remains unverified.
- No numeric quote value, article text, screenshot, or raw market-data bytes were added to public machine records. The existing machine report records the source locators and the blocked disposition only.

**Narrow next step:** do not ask the operator to resend the same Stockstar URL or retype the value. Obtain an original historical quote export/statement from a source whose terms permit personal/internal research and private byte retention, or obtain explicit permission from the relevant data provider. Keep it in the private workspace; hash its exact bytes; bind security and observation date; verify cutoff-safe `known_at`; then run the independent unchanged Core/PIT validator. Until every step passes, keep `market_price=UNKNOWN`.


## 9. Operator-direct market-price input policy and implementation — 2026-10-11

**Operator direction:** when market-price information is needed, ask the operator directly for the security, observation date, and price. After a direct operator-supplied price, do **not** perform a second web search or source-page audit unless the operator explicitly requests one. This supersedes the earlier instruction in sections 7–8 to keep asking for a source artifact or continue searching.

**Evidence boundary:** the system records such input as OPERATOR_ATTESTED_MARKET_DATA, not as SOURCE_VINTAGE_VERIFIED. The input carries an explicit operator assertion that the value was available by the declared known_at, plus security/date/cutoff bindings and a SHA-256 over the private attestation JSON. The hash proves the exact attestation bytes only; it does not prove the linked publisher's source bytes or independently verify the quote. The numeric value and value-bearing attestation must remain in the operator's private workspace and must never be committed to this public repository or uploaded as a public Actions artifact.

**Implementation: PASS / MERGED / CANONICAL.** PR [#338](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/338) merged as `c7fc3ff37fab75e2d72a5ba2c4a995058a85ebec`. It adds the provenance class, narrow market-price-only validation, local bundle writer, explicit cutoff confirmation and optional private bundle path. Exact-head C2 workflow run [#38123530550](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38123530550) passed its default no-private-bundle path and contract tests. The test's synthetic value is only a fixture. CI did not receive or validate the real 002001 close; the real private bundle still needs a local run against Run #8. Do not upload a value-bearing bundle or report to public GitHub.

**Next execution order:**

1. Run the private bundle writer for the already supplied 002001 close. Do not fetch or re-audit the Stockstar URL. The writer defaults known_at to 23:59:59 +08:00 on the observation date and requires explicit operator confirmation that it is cutoff-safe.
2. Run the C2 successor locally using the original pinned Run #8 archive plus the private bundle. The unchanged Core/PIT validator must report all seven required groups covered; otherwise remain BLOCKED and inspect the exact validator errors.
3. Keep the 13 official-filing source/vintage independent review as a separate gate. A Core/PIT pass on the operator-attested price alone is not formal signed admission, production Host acceptance, a canonical Decision, Publication, or Run Receipt.
4. Continue the primary 605016 production Host acceptance critical path in parallel; do not let the C2 price-source web-search loop delay it.

**Current next gate:** execute the previously generated private bundle locally. The bundle's own SHA-256 and the Run #8 archive SHA-256 have been checked in this working session; that verifies file integrity only. The official 13 fact candidates still need an independent source/vintage review. No actual-case all-seven-group Core/PIT pass, formal admission, production Host acceptance, Decision, Publication, complete Run Receipt, or execution authority is currently claimed.


## 10. Actual private C2 Core/PIT run — 2026-10-11

**Result: `PASS_EPHEMERAL_OPERATOR_ATTESTED_NOT_SOURCE_VINTAGE_VERIFIED`. The merged tool was executed locally against the pinned Run #8 archive and a private bundle generated by the merged `tools/iios_operator_market_price_attestation_v01.py`. No second web audit was performed.

- Run #8 archive SHA-256: `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`.
- Private attestation ZIP SHA-256: `78cbc2ac41b00db6509d4578f931ffe6d9bfba59751121fba51ee5d0b86d5ad5`.
- Exact private attestation payload SHA-256: `97568a2f416e922404290b66fbce820807115fcbd73931cdfed5f2ac27efb0fb`. This hash binds the operator-attestation JSON only; it does not bind/verify publisher vendor bytes.
- Private B2 manifest SHA-256: `bda2253bc98e089d87a5d2f04adb939c74be8f30e357195468e508e2f88d06ed`. The manifest/report and numeric quote remain local-only and were not uploaded to GitHub.
- The unchanged Core/PIT validator reported **all seven required field groups covered**, zero missing groups, 14 evidence records (13 official-filing fact candidates plus the operator-attested price record), 8 captured original raw objects integrity-verified, and 13 PDF fact locators passed.
- A separate local second-pass extraction checked **13/13 page-locator term sets**, **13/13 cutoff-safe source-date upper bounds**, and **13/13 official SZSE source-domain bindings**. The 2026-10-09 buyback-progress notice remains excluded. This is a second-pass local check, **not** a genuinely independent human/external review and not a legal opinion. The use boundary remains private fact-level research only; unrestricted reuse is not claimed.
- The sanitized run result contains no numeric price. It explicitly records `secondary_web_audit_performed=false`, `original_vendor_bytes_received=false`, and `source_verified_by_system=false`.

**Still open:** independent review of the 13 official-filing claims, source-date bounds, and use boundary; formal signed Evidence/PIT admission; production Host acceptance; canonical D2 forecast/valuation/decision path; Publication; complete `IIOS_RUN_RECEIPT` and independent replay. All authority-creating outputs and execution authorization remain false. The primary 605016 production Host path continues in parallel.

## 11. Manual Web semantic admission guard — canonical closure — 2026-10-11

PR [#342](https://github.com/kebofeierdawei5-cloud/convergence-research/pull/342) is **PASS / MERGED / CANONICAL** at `a496b82b8cfbc2256a9affd3337f97fce305d217`. The exact-head regression and governance checks passed, including B2 Semantic Producer Admission, Investment Core CI, State Hygiene, C0 Governance, B2-F fresh independent red-team, B00-B authority threat reproduction, B1 orchestrator, CORE-00, trusted runtime factory, Post-B04 red-team, and the associated pilot/provider checks.

The canonical `admit_semantic_artifact` boundary now blocks the manual ChatGPT Web semantic producer and renamed producer identities that retain the unapproved `IIOS-CHATGPT-WEB-OPERATOR-POLICY-` namespace. This is fail-closed enforcement under the existing frozen B0 contract, not a governance downgrade or new source-origin assurance class. Manual Web handoff remains available only as non-canonical operator assistance; local hashes still do not authenticate OpenAI/model origin.

**Remaining project gates:** P0-LLM-001 and P0-LLM-004 remain OPEN. No production Host-origin run, complete Run Receipt, independent replay, or formal canonical investment decision has been established. For C2, the next batch is a genuinely separate review of the 13 official-filing facts, conservative source-date upper bounds, and private fact-level-use boundary; no more market-price web search is required.

## 6. Prepared independent fact/use review packet (2026-10-13)

The helper `python -m iios_mvp.c2_independent_fact_review_v01` creates a private reviewer packet from the pinned, sanitized C2-P3 machine review archive. Default output is under `~/.iios-private/reviews/` with mode 0600 (parent directory mode 0700). It copies only the thirteen fact IDs/labels, official PDF URLs, physical page locators, source byte hashes/sizes and conservative `known_at` bounds. It does not copy PDF bytes or numeric market-price values.

Run from the canonical repository checkout:

```bash
python -m iios_mvp.c2_independent_fact_review_v01 \
  --source-report evidence/real_cases/RC-CN-A-002001-20261009/C2_P3_FACT_REVIEW_CI_RESULT_38126026797.json
```

The output is explicitly `TEMPLATE_PENDING_NOT_REVIEWED`. It leaves the reviewer identity, independence declaration, each fact check, private-use scope, retention/backup limits, permission instrument and final disposition as `PENDING`. The helper refuses a changed case/cutoff, a report without 13/13 machine locator/date checks, duplicated or unmapped fact rows, an upgraded reuse status, or a report containing a numeric market-price value. Its tests establish packet construction and private-file handling only; they do not independently verify the original PDF bytes or authorize any use.

A genuinely separate reviewer must inspect the exact private PDF bytes and the cited page/row for each fact, assess the conservative publication-time bound, and explicitly adjudicate fact-level private storage/computation/internal display/retention and derived-output scope. Any unknown or rejected row remains unresolved. The reviewer must not merely repeat the machine CI conclusion or use this template as evidence of their own identity. Once a real review is complete, the case-bound manifest and rights record must be reconciled and re-hashed, then the existing signed-admission contract must be executed with distinct registered admission and independent-reviewer keys. This packet is not itself cryptographically bound into that envelope and cannot replace it.

C2 is still **NOT FORMALLY ADMITTED**. Company-disclosure reuse/retention remains `PUBLIC_ACCESS_REUSE_UNKNOWN` pending the separate review and an applicable rights disposition; the operator-attested 002001 market price is a different evidence class and remains excluded from source-admission claims.
