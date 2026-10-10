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

- Workflow run: [38014829961](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014829961)
- Intake at the time: `CAPTURED_NOT_ADMITTED`; 12/12 HTTP response bodies captured, zero failed rows, zero unregistered refs.
- Independent verification at the time: 12/12 raw byte arrays hash/size verified; `unknown_pit_sources=1`.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; all seven required field groups remained uncovered; `evidence_admission=false`, `pit_admission=false`.
- Artifact: [11655654643](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38014829961/artifacts/11655654643), 14-day Actions retention.
- **Retrospective payload inspection:** 8 of the 9 SSE URLs declared as PDF returned gzip-transported HTML/JavaScript challenge pages (HTTP 200 / HTML), not PDF report bytes. Only the convertible-bond prospectus URL returned an actual PDF. Sina, Stockstar and Sohu returned HTML pages of their declared type but remain unverified/secondary content. Thus “12/12 captured” meant HTTP response bytes retained, not 12 valid source documents. The original evidence/PIT gate remained blocked, but the raw-capture contract needed an additional expected-payload-type check.

## Payload contract hardening on this branch

- Source manifests may declare `expected_payload_type` (`PDF`, `HTML`, `JSON`, `ANY`).
- Intake checks payload magic/structure; for gzip-transported responses, decompression happens in memory **for sniffing only**. The saved bytes remain the exact response bytes and hashes are calculated over those exact bytes.
- An expected PDF that returns HTML is labelled `MISMATCH / EXPECTED_PDF_RECEIVED_HTML_OR_ACCESS_CHALLENGE`.
- The independent verifier repeats the check from raw bytes and rejects forged `PASS` labels.
- B2 preflight excludes payload-mismatched responses from Evidence Record creation; final gate status distinguishes raw capture from payload-contract success.
- Dedicated regressions cover HTTP 200 + gzip HTML challenge, independent verification, B2 candidate exclusion and red-team rejection.

## Attempt 4 — payload-contract verification

The request was incremented to attempt 4 after the payload-type gate landed. Append the exact run result below when completed. No admission is assumed in advance.

## Attempt 4 — expected-payload-type gate against real sources

- Workflow run: [38015723986](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015723986)
- Intake: 12/12 raw response bodies captured; 0 transport failures and 0 unregistered refs.
- Independent raw integrity: 12/12 raw byte arrays hash/size verified; payload checks: 12 checked, 3 passes, 9 mismatches.
- Of the nine PDF-declared SSE source URLs, 8 were correctly identified as gzip-transported HTML challenge pages. The ninth was a real PDF (`%PDF-1.5`) but was falsely classified `UNKNOWN` because the detector compared uppercase PDF magic against a lowercase literal case-sensitively.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; `b2_candidate_source_count=3` (three HTML-page candidates); `payload_contract_failure_count=9`; all seven required groups remained missing; `evidence_admission=false`, `pit_admission=false`.
- Artifact: [11656955181](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015723986/artifacts/11656955181).

## Attempt 5 — uppercase PDF fix, but slow source still failed

- Workflow run: [38015841564](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015841564)
- Runtime: approximately 4m35s, exposing why the prior sequential acquisition path felt stuck.
- Intake: 11/12 response bodies captured; source `SSE-H1-2026-FULL` failed with `SOURCE_FETCH_FAILED`; remaining 11 raw bodies independently hash/size verified.
- Payload checks: 11 checked, 4 passes, 7 mismatches. This run confirmed real `%PDF-1.5` bytes now passed and the three HTML pages passed; seven other SSE PDF URLs produced HTML access-challenge payloads.
- B2 preflight: `BLOCKED_NOT_ADMITTED`; candidate sources=4; all seven groups missing; no Evidence/PIT admission.
- Artifact: [11656331805](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015841564/artifacts/11656331805).

## Attempt 6 — bounded-read implementation exposed an import-name collision

- Workflow run: [38015985509](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015985509), conclusion `failure`; artifact [11656276832](https://github.com/kebofeierdawei5-cloud/convergence-research/actions/runs/38015985509/artifacts/11656276832).
- Root cause from exact traceback: adding `import time` shadowed the existing `datetime.time`, so `_pit_candidate_status()` failed at `time.min` with `AttributeError: module 'time' has no attribute 'min'`. No B2 admission or formal artifact was created; verifier/preflight could not run because capture did not write its receipt.
- Fix: import the monotonic clock as `_clock` and preserve `datetime.time`; regression test now patches `_clock.monotonic`.
- The per-source 18-second deadline / 8-second read timeout is retained, and response reads now prefer `read1()` with 64 KiB blocks so a slow trickle cannot hide beyond the total deadline within a 1 MiB buffered read.

## Attempt 7 — rerun after clock-collision fix

The capture request was incremented to attempt 7 after the clock import fix. The run must verify real PDF magic, detect HTML challenges, finish within the bounded capture step, preserve failed-source rows, and keep all evidence/PIT admission blocked. Results will be added only after the workflow finishes.

## Explicit gate boundary

All captured facts remain `NOT_ADMITTED` until issuer/exchange origin, known-at basis, license/reuse status, field-level locator, source-vintage and B2/PIT validation are independently reviewed. All seven required groups remain uncovered for decision purposes; no valuation, formal Decision Revision, publication or report is authorized by this capture record.
