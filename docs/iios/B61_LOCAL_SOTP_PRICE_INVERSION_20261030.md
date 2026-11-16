# B61 — Local SOTP current-price and segment earnings requirement inversion

Date: 2026-10-30  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Purpose

B60 independently inverted the protected price through the selected EPS_MULTIPLE terminal P/E. B61 supplies the distinct SOTP path and does not route SOTP through EPS_MULTIPLE or B5's EPS adapter.

## Existing SOTP identity

The local SOTP adapter calculates:

\`SegmentEquityPool = Σ(attributableSegmentNetProfit_i × segmentPE_i)\`

\`TotalEquityValue = SegmentEquityPool − CapitalizedParentCentralCost + NetCashDebt + OtherAdjustments\`

\`TerminalValuePerShare = TotalEquityValue / DilutedShares\`

B61 consumes only the adapter's normalized CALCULATED output. It independently checks each segment profit × P/E, the segment-pool sum, the parent-level equity identity and the terminal value per diluted share before inversion.

## Price and return hurdle inversion

For a return rate \(r\) and the explicit ACT/365F year fraction \(T\):

\`RequiredTerminalEquityValue = CurrentPrice × (1+r)^T × DilutedShares\`

For dated distributions already validated by the existing return solver, B61 separately calculates each payment's present value at the same return hurdle, then:

\`RequiredTerminalEquityValue = max(0, (CurrentPrice − PVValidatedDistributions) × (1+r)^T) × DilutedShares\`

With parent adjustments held constant:

\`RequiredSegmentEquityPool = RequiredTotalEquityValue + CapitalizedParentCentralCost − NetCashDebt − OtherAdjustments\`

Required Return and the fixed 15% Fundamental Target are calculated separately. The annualized return rate is a holding-period hurdle; it is not WACC, cost of capital or a valuation discount rate.

## Segment-level requirement semantics

For one segment \(i\), with every other segment contribution frozen at the selected scenario:

\`RequiredProfit_i = (RequiredSegmentEquityPool − Σ(otherSegmentProfit_j × segmentPE_j)) / segmentPE_i\`

The output also provides the segment's selected attributable profit, P/E, value contribution, incremental profit required or profit headroom, and the alternative standalone profit threshold if that one segment alone supported the required segment pool. The signed algebraic requirement is preserved for audit; if it is negative because other segment contributions already cover the required pool, a separate non-negative operating-profit floor is shown instead of presenting negative operating profit as a real target.

**These are one-at-a-time sensitivities, not simultaneous operating forecasts.** Segment thresholds must not be summed. B61 does not allocate a total valuation gap across segments without a separately evidenced value-driver allocation rule.

## Controls and limitations

- Only selected, locally CALCULATED SOTP with CNY currency, PIT-compatible pilot price, matching forecast period and terminal date is eligible.
- Segment profits, P/E, segment value, parent adjustments, equity value and diluted-share arithmetic are rechecked; the central-cost-after-tax × central-cost-multiple capitalization is recomputed, and diluted shares must remain positive integer shares. Contradictions block the affected scenario.
- Only cash distributions already validated by the existing return solver enter the distribution-adjusted result; unvalidated distributions remain excluded.
- The adapter's segment P/Es are conditional terminal valuation assumptions, not external current segment multiples or external MIE.
- Output is nested in \`assessment.market_implied_expectation.price_implied_analysis.local_sotp_recalculation\`. External MIE and expectation-gap states are unchanged.
- No change to SOTP inputs/results, EPS_MULTIPLE, B5/B6, primary returns, target entry price, 15% hurdle, formal admission, Decision or execution authority.

## Regression cases and validation

Five cases are authored: numerical segment-pool inversion and one-at-a-time profits; validated dated distributions; mismatch of parent equity identity; model/currency gates; and external MIE/authority preservation. They have not been executed. No Replay, CI, merge or macOS acceptance is claimed.
