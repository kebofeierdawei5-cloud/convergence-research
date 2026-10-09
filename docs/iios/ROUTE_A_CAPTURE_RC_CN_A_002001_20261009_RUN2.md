# Route A First Real Capture — 新和成 (002001.SZ)

**Record class:** DIAGNOSTIC / raw-source capture + independent byte-integrity result  
**Case ID:** `RC-CN-A-002001-20261009`  
**Cutoff:** `2026-10-09`  
**Run:** [GitHub Actions #2 / 37918304170](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/37918304170)  
**Run branch commit:** `ef0d99ffe664340e29be7f30c577a1662593a87d`  
**Run completed:** `2026-10-09T10:33:23Z` (UTC)  
**Artifact:** `iios-company-evidence-37918304170`, ID `11610237261`  
**Artifact ZIP SHA-256:** `71600859888d65d7bcdd67591f1029791910be744fe7e17dadedfcff804006d3`  
**Artifact size:** `1,367,116` bytes  
**GitHub retention expiry:** `2026-10-23T10:33:23Z` (UTC; 14 days)  
**Manifest SHA-256:** `2e2fb0648460d646daaca3f749f8971352b8e8895d442b580609e357794ceed2`

## Run result

- Capture receipt status: `CAPTURED_NOT_ADMITTED`.
- Source count: 5; successful captures: 5; failed captures: 0.
- Independent verifier: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`.
- Recomputed raw-byte hashes: 5/5; manifest SHA-256 binding: PASS.
- Unknown PIT sources: 1; future-known sources: 0.
- `evidence_admission = false`; `source_origin_verified = false`; `live_llm_required = false`.
- The first failed run #1 (ID `37918027867`) failed in request-path resolution before source network access and produced no source artifact. The resolver was fixed in PR #241, and run #2 used the merged fix.

## Captured objects

| Source ID | Byte size | SHA-256 | Capture / PIT status |
|---|---:|---|---|
| `ISSUER-IR-PAGE-CURRENT` | 21,953 | `18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c` | HTTP 200 / `UNKNOWN_NO_KNOWN_AT` |
| `SZSE-2026-H1-FULL` | 980,820 | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-H1-SUMMARY` | 144,809 | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-Q1-FULL` | 221,878 | `facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |
| `SZSE-2026-BUYBACK-PLAN` | 142,384 | `e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9` | HTTP 200 / `PIT_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW` |

The four PDFs' opening pages were checked as a document-identity sanity check: they identify 浙江新和成股份有限公司 / 证券代码 002001 and the expected H1, Q1 or 2026-027 repurchase documents. This is not a full report review and does not authenticate the source URL's full publication timeline by itself.

## Source locators

- Issuer IR page: https://www.cnhu.com/investor/zh-cn
- 2026 H1 full report: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/83165436-1015-4d77-919c-97c8cce0c67d.PDF
- 2026 H1 summary: https://disc.static.szse.cn/disc/disk03/finalpage/2026-08-20/6d1ad0be-5e22-482b-a163-2ebb0b6d1d95.PDF
- 2026 Q1 report: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-29/094c9e5d-f2de-4411-b604-b2aece32f35b.PDF
- 2026 repurchase plan: https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-24/53248225-c2cf-45cf-a0fd-a6c9fee4f267.PDF

All records currently declare `license_status = PUBLIC_ACCESS_REUSE_UNKNOWN`. The report-date values are claims supported by path/indexing and should be checked against the existing B2 Evidence/PIT rules. They are not self-admitting provenance.

## Gaps and next action

- No market-price bytes are present.
- No separately captured operating/business-reality source beyond the reports yet.
- No separately captured capital-structure/source-master snapshot yet.
- The issuer IR landing page is current-content and has no defensible first-public date in the manifest, so it remains UNKNOWN.
- The next gate is the existing B2 Evidence/PIT admission for these objects, then add the missing company-level source groups. Neither the raw capture nor this record authorizes company-level investment conclusions.
