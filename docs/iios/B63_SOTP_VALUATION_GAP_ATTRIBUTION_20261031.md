# B63 — SOTP valuation-gap attribution across segment earnings, multiples, parent adjustments and dilution

Date: 2026-10-31

Status: branch proposal on feat/b45-normalized-earnings-variance-attribution-20261027; not merged, not tested.

## 1. Objective

B62 already compares:
- B4 forward normalized parent-attributable segment profit;
- current selected SOTP profit and P/E by segment;
- the full B4 forecast segment value pool at the unchanged selected SOTP P/Es; and
- B61's Required Return segment-pool hurdle, excluding unvalidated distributions.

B63 answers the next question: what is the mathematical source of the remaining valuation gap, and which parts are operating earnings, selected P/E assumptions, parent-level adjustments or diluted-share mechanics?

B63 is diagnostic. It does not decide whether a selected P/E is fair, whether the current market price is cheap, or whether the B4 forecast will be achieved.

## 2. Two-step segment value-pool waterfall

For scenario q and segment i:
- SOTP selected normalized parent-attributable profit: N(i,q)
- B4 forward normalized parent-attributable profit: F(i,q)
- selected SOTP terminal P/E: M(i,q)

Selected SOTP value pool:

SelectedPool(q) = Σ[N(i,q) × M(i,q)]

B4 profit change valued at unchanged selected P/Es:

EarningsEffect(q) = Σ[(F(i,q) − N(i,q)) × M(i,q)]

B4 full-vector forecast pool at selected P/Es:

B4Pool(q) = SelectedPool(q) + EarningsEffect(q) = Σ[F(i,q) × M(i,q)]

Residual segment-pool requirement after B4 earnings:

MultipleEffect(q) = RequiredPool_B61(q) − B4Pool(q)

The sign convention is positive when an effect increases the required/forecast segment value pool. The waterfall must reconcile within CNY 0.01:

SelectedPool + EarningsEffect + MultipleEffect = RequiredPool_B61

B63 separately verifies that the segment rows sum to the selected SOTP pool and B4 pool and that their earnings effects equal the aggregate B4-minus-SOTP pool change. It does not take a B61 one-at-a-time segment profit/PE threshold and add it to another segment's threshold.

## 3. Common P/E scaling sensitivity

If both B4Pool and RequiredPool_B61 are strictly positive:

CommonPEScale = RequiredPool_B61 / B4Pool

For each segment:

RequiredPE_i_under_common_scale = SelectedPE_i × CommonPEScale

This says: if B4's normalized profit forecast is achieved for every segment, what common proportional change to all selected terminal P/Es would make the total segment pool equal B61's Required Return pool?

It is not:
- an external current-market P/E;
- a fair-value P/E conclusion;
- a consensus estimate;
- an instruction to change the selected SOTP multiples; or
- an additive list of per-segment P/E targets.

If either pool is zero/negative, the common scaling ratio is not identifiable as a useful positive multiple sensitivity. Other correctly reconciled bridge components remain visible; the multiple lens must remain NOT_IDENTIFIABLE.

Each segment's selected P/E basis, data_class and evidence_refs are shown. Source references make the assumption traceable; they do not prove semantic support.

## 4. Parent adjustment contribution

B61 derives the required segment pool from required total equity using the exact parent adjustment identity:

RequiredPool = RequiredTotalEquity + CapitalizedCentralCost − NetCashDebt − OtherAdjustments

Where:

CapitalizedCentralCost = CentralCostAfterTax × CentralCostMultiple

The B63 parent bridge shows the signed contribution of each selected parent adjustment:
- capitalized central cost adds to the required segment pool;
- positive net cash offsets the required segment pool, while net debt (negative net cash) increases it;
- other adjustments are subtracted using their signed value.

B63 rechecks the same parent adjustments between the SOTP adapter and B61 and rechecks the capitalized central-cost arithmetic. It also shows the mechanical effect of a CNY 1 change in each input.

Without explicit independent forward forecasts for central cost, net cash/debt and other adjustments, B63 must not claim an amount for their future change or allocate the residual hurdle to them.

## 5. Diluted-share contribution

Required total equity follows:

RequiredTotalEquity = RequiredTerminalValuePerShare × DilutedShares

B63 checks the SOTP diluted-share count against B61 and shows:
- required terminal value per share;
- required total equity;
- B4 forecast total equity at the current parent adjustments;
- total equity gap and per-share gap;
- break-even diluted-share count at B4 forecast equity;
- share-count headroom versus that break-even count; and
- incremental required equity for one additional diluted share and for a 1% increase in shares.

The share-count bridge is an arithmetic sensitivity, not an operating-earnings or EPS-growth claim. It does not assume an issuance, buyback, option exercise or future dilution event without explicit evidence.

## 6. Cross-node reconciliation and fail-closed statuses

B63 consumes only:
- a calculated selected CNY SOTP primary model;
- B61's conditional Required Return inversion without distributions; and
- B62's comparable, calculated full-vector scenario.

It requires the same B4/B61/SOTP forecast period and rechecks:
1. selected SOTP segment universe, segment profits and P/Es;
2. selected segment pool versus B61/B62;
3. selected total equity versus segment pool less capitalized central cost plus net cash/debt and other adjustments;
4. selected terminal per-share value versus total equity divided by diluted shares;
5. SOTP versus B61 central cost, net cash/debt, other adjustments, share count and selected terminal values;
6. Required total equity versus required per-share value times diluted shares;
7. Required segment pool versus required total equity plus parent adjustment load;
8. B4 segment pool and earnings effect recalculated from the B62 segment rows; and
9. central cost capitalization versus after-tax central cost multiplied by its selected capitalization multiple.

A numerical mismatch yields RECONCILIATION_MISMATCH. Missing inputs or a period/scope/model-family blocker stays explicitly blocked or not identifiable. A non-positive value pool disables only the common P/E scale lens; it must not be repaired with an invented value.

## 7. Placement and authority

New module:
iios_mvp/sotp_valuation_gap_attribution_v01.py

Nested output:
assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation.valuation_gap_attribution

The report renders B63 after the B61/B62 sections. No new top-level JSON field is created.

B63 does not modify B4/B5/B6, SOTP main valuation, B61 inversion, external MIE, expectation_gap, target entry price, the 15% fundamental target, Required Return policy, portfolio constraints, Decision, formal admissions or execution authority.

## 8. Regression and acceptance

Eight regression cases are authored in tests/test_sotp_valuation_gap_attribution_v01.py:
- complete earnings/multiple/parent-adjustment/share-count waterfall;
- parent-cost mismatch;
- diluted-share mismatch;
- segment-universe mismatch;
- non-normalized earnings-basis blocker;
- period mismatch;
- non-SOTP non-applicability; and
- non-identifiable common P/E scaling when the B4 pool is non-positive.

They have not been executed. Replay, CI, unified tests and real macOS acceptance remain deferred. This branch-only development is not a PASS or a formal investment/valuation admission.
