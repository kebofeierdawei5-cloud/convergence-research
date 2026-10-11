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
