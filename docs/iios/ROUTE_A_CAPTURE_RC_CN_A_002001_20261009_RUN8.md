# Route A Partial Capture Run #8 — 新和成 (002001.SZ)

**Record class:** DIAGNOSTIC / real public-source acquisition + independent raw-byte integrity; not Evidence/PIT admission  
**Case ID:** `RC-CN-A-002001-20261009`  
**Cutoff:** `2026-10-09`  
**Canonical source after code fix:** `067d28176da981245c84cdcd88b67a5f456991b8` (PR #252)  
**Run:** [GitHub Actions #8 / 37938129274](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/37938129274)  
**Capture request commit:** `b3f7486b0216d1bd88ad84332a31583ab311727b`  
**Completed:** `2026-10-09T13:37:27Z` (UTC)  
**Artifact:** `iios-company-evidence-37938129274`, ID `11620425220`  
**Artifact size:** `1,474,787` bytes  
**Artifact ZIP SHA-256:** `0c7ddb34a4b77f7298309ae89ac8de96877a059656a811beefe7eabfe99a0ba1`  
**Artifact expires:** `2026-10-23T13:37:26Z` (UTC; 14 days)  
**Exact manifest SHA-256:** `c6ec425f3c2ef5404bbdd1868e57434c64da90e255bcde5eae24586dba1227e3`

## Result

- Workflow conclusion: `SUCCESS` under the new **partial-capture** gate.
- Receipt: `PARTIAL_CAPTURE_NOT_ADMITTED`; 9 sources declared, 8 captured and 1 failed.
- Independent verifier: `INDEPENDENT_INTEGRITY_VERIFIED_NOT_ADMISSION`; 8/8 captured raw byte objects verified against receipt hashes.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; B2 manifest `BLOCKED`.
- `admitted_field_groups=[]`; all seven B2-required field groups remain uncovered for fact-level admission.
- `evidence_admission=false`; `pit_admission=false`; `source_origin_verified=false`; `llm_provider_required=false`.
- The job is green because it correctly preserved and checked the **partial** artifact, not because every candidate URL succeeded or evidence was admitted.

## Captured objects

| Source ID | Bytes | SHA-256 | Capture/PIT state |
|---|---:|---|---|
| `ISSUER-IR-PAGE-CURRENT` | 21,953 | `18453e3bb5d2f92a00fd0aae2e05bbe0b590f37b9d37b6e5ee1df87074548a1c` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `SZSE-2026-H1-FULL` | 980,820 | `ab0ff443cc4b15b20ca8f4ed5fb8d4a5dea9b7fadf4b83ab8cd0532e54dd803e` | SUCCESS / PIT candidate |
| `SZSE-2026-H1-SUMMARY` | 144,809 | `bbd0f336ee1fd4bb5ec606d20939b06a245b7c79ac4facdad602233507db25c3` | SUCCESS / PIT candidate |
| `SZSE-2026-Q1-FULL` | 221,878 | `facf0adafbc8e8e953671b2fdb1fe8aa10cab6c68e8474a4048da5dda0f98caa` | SUCCESS / PIT candidate |
| `SZSE-2026-BUYBACK-PLAN` | 142,384 | `e993200299e9b2f223817270a267614eeb5dcb180945dd4917e832810d3a47c9` | SUCCESS / PIT candidate |
| `SZSE-2026-BUYBACK-PROGRESS-SEP` | 84,057 | `af6ad44d49b10b0f23306e0812fa64200880b29883bcaa71fecaf6b54a8ac6ed` | SUCCESS / PIT candidate |
| `PRICE-SOHU-HISTORY` | 21,829 | `0f05a4c643ef19de9d313c4231ab200386b6946920c066fb104d23ebb683efd3` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `PRICE-EASTMONEY-QUOTE` | 56,928 | `97bf733ac8f7d1fd14bb3377fd85041940b4ef225349bdc07710f9c22a827cfa` | SUCCESS / `UNKNOWN_NO_KNOWN_AT` |
| `PRICE-EASTMONEY-KLINE-API` | — | — | FAILED / `SOURCE_FETCH_FAILED`; no bytes retained |

The active manifest no longer includes the previously flaky duplicate Sohu `app2/history.up` endpoint. Eastmoney's K-line API succeeded in an earlier run and failed on Run #8, showing that this runner-to-public-endpoint path is intermittent. This failure remains explicit; it is not changed to UNKNOWN success, and no hash is asserted for a source with no bytes.

## Existing B2 preflight result

The preflight generated artifact-level source records from the eight successfully captured files. Those records are explicitly `provenance_class=UNKNOWN` and `status=UNKNOWN`; therefore the existing B2 validator rejects them for PIT/field-group coverage. This is expected and correct: a file containing a report or a market page has not yet been mapped into admitted facts.

Next action: review report publication identity and source vintage, extract individually scoped facts with page/table/row locators, bind each fact to an admitted evidence record and exact raw object, and run the existing B2 validator. Add a separate official/free source for operating-model/business-reality where needed. Do not use report data merely because the captured PDF hash matches.
