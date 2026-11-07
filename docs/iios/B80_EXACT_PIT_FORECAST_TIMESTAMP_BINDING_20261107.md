# B80 — Exact signed PIT cutoff binding for Forecast timestamps

Date: 2026-11-07  
Branch: `feat/b76-core-integrated-20261101`  
State: Draft proposal only; do not merge to `main`.

## Finding

B79 made the signed Evidence/PIT resolver compare every admitted evidence row's `known_at` against the exact cutoff instant. The canonical independent Forecast record still validated `forecast_origin` and `known_at` only by calendar date (`timestamp.date() <= cutoff_date`). The return-lineage layer therefore accepted a forecast created after an intraday cutoff, or after midnight when the signed manifest used a date-only cutoff, as long as it was on the same calendar date.

This was reproducible in the old B04 positive fixture: its forecast `known_at` occurred later than the date-only Shanghai-midnight cutoff, yet the signed Evidence/PIT lineage passed.

## B80 change

1. The signed Evidence/PIT resolver now returns the exact normalized cutoff instant it actually validated. Date-only values resolve to Shanghai 00:00; timezone-aware timestamp values are converted to Shanghai local time without changing the signed source bytes.
2. When formal Evidence/PIT binding is supplied, Forecast `forecast_origin` and `known_at` must both be timezone-aware and no later than that exact signed cutoff instant. Comparison is by absolute instant, so equivalent UTC and Shanghai timestamps are treated identically. Equality at the cutoff is allowed; any later instant is rejected.
3. The return-lineage result records the normalized PIT cutoff and whether exact Forecast temporal binding passed. A lineage without signed Evidence/PIT remains explicitly `NOT_VERIFIED_WITHOUT_SIGNED_EVIDENCE_PIT_CUTOFF`; it is not silently promoted.

## Regression coverage

- The shared B04 fixture now uses Forecast timestamps strictly before the date-only Shanghai-midnight cutoff.
- Exact intraday cutoff equality passes, including an equivalent UTC timestamp.
- `forecast_origin` after an intraday cutoff is rejected.
- `known_at` after an intraday cutoff is rejected.
- A same-date Forecast timestamp after Shanghai midnight is rejected when the signed cutoff is date-only.
- Existing B79 Evidence/PIT signature, raw-byte, rights, signer-registry and evidence-ID binding checks remain unchanged.

## Explicit non-changes

- No EPS, SOTP, MIE, expectation-gap, return, target-entry-price or position-sizing formula changes.
- The 15% annualized return hurdle remains a return hurdle, not WACC or a discount rate.
- No source class becomes admitted because of this timestamp check; source rights and trusted signer requirements remain independent gates.
- No real-company Evidence/PIT or Forecast Admission is created by synthetic fixtures.
- Production signer registry remains empty until separately authorized real signer enrollment and case-bound evidence exist.
- Real operator macOS full-run + Replay acceptance remains separate and must not be inferred from GitHub CI.

## Final validation — 2026-11-07

**Validated code commit:** `bb668cb5694bd36584988e204a5dad29fcee580e`. The current PR head `c3fbfa8251fca86d71eb7500bd77f827030aa03c` contains only subsequent B80 documentation/state-index commits; no runtime or test code changed after the validated code commit.

- **35** pull-request workflow runs: **34 success, 0 failure, 1 cancelled**.
- B04 Forecast-Valuation-Return Lineage: **16 passed**.
- B04-B Mandatory Forecast-Valuation-Return Lineage: **130 passed**.
- Canonical Host trust-boundary regressions: **22 passed**.
- Investment Core CI: **448 passed**.
- Local Investment Pilot Linux job: **466 passed**, including B76 arithmetic, real-case readiness, launcher/updater syntax and Replay acceptance.
- Signed Evidence Admission, Post-B04 red-team, B2-F red-team, B2-E E2E/red-team, B2-D live fail-closed smoke, TR-01/TR-03, P0 Runtime Factory, P0 Host, C0/C1/C2/C4/C5/C8, RP-01 and other relevant workflows completed successfully.

The single cancelled workflow is the combined Local Investment Pilot run because its separate `macos-acceptance` job was cancelled by GitHub Actions; its `local-pilot` Linux job passed. This is **not** a macOS pass. The user's real Mac two-round handoff + independent Replay remains **OPEN / NOT VERIFIED**.

PR #587 remains **Open + Draft + Unmerged**, targeting the B73 proposal branch. No changes were merged to `main`. The production signer registry remains empty; no real-company formal Evidence/PIT, Forecast, Valuation, Decision or execution authority was created.


## First exact-head CI correction — 2026-11-07

The first exact PR validation correctly rejected a legacy positive B04 core-integration fixture whose Forecast `forecast_origin` and `known_at` were later than the date-only Shanghai-midnight cutoff. The B80 guard was not relaxed. The fixture in `tests/test_b04_core_integration.py` was corrected to place both timestamps before the cutoff. Re-run exact-head B04 lineage, core integration and full pilot checks before treating B80 as validated.


## Shared lineage-fixture correction — 2026-11-07

A second downstream failure exposed that the shared `tests/b04b_return_lineage_fixture.py` helper generated `forecast_origin` at cutoff-day 12:00 UTC and `known_at` at 15:00 UTC. That was invalid under date-only Shanghai-midnight semantics and affected the Trusted Host CLI integration as well as other consumers. The helper now derives both timestamps from the case cutoff: origin at Shanghai midnight minus two hours and known_at minus one hour. This keeps all shared positive fixtures PIT-valid without weakening runtime validation. The separate B04 core-integration local fixture was also aligned. Re-run the exact-head workflow matrix after these fixture-only corrections.


**Final state:** the final validation block above supersedes the earlier pending-validation notes recorded during the B80 repair sequence.
