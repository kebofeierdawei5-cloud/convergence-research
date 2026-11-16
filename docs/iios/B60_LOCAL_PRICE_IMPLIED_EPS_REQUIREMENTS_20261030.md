# B60 — Locally recomputed price-implied EPS requirements

Date: 2026-10-30  
Status: **BRANCH PROPOSAL ONLY / NOT MERGED / NOT TESTED**

## Problem closed

B52 introduced \`assessment.market_implied_expectation.price_implied_analysis\` as the home for conditional current-price inversion, but the local pilot checked the submitted object's method/family/reference-price/assumptions/results/limitations shape only. It did not independently recalculate the EPS_MULTIPLE inversion formula. B60 adds a locally computed EPS_MULTIPLE conditional inversion.

## Formula and semantics

For each Bear/Base/Bull scenario, use the protected structured current price, the EPS_MULTIPLE adapter's actual terminal P/E, the explicit valuation terminal date / ACT-365F year fraction, and the operator's annualized return hurdle.

Before interim distributions:

\`required_terminal_value = current_price × (1 + annualized_return_hurdle) ^ year_fraction\`

\`required_terminal_EPS = required_terminal_value / selected_terminal_PE\`

When the existing return solver has validated dated, net-of-tax eligible distributions, B60 also calculates the distribution-adjusted requirement separately:

\`PV_distributions = Σ(distribution_per_share / (1 + hurdle) ^ event_year_fraction)\`

\`required_terminal_value = max(0, (current_price − PV_distributions) × (1 + hurdle) ^ year_fraction)\`

\`required_terminal_EPS = required_terminal_value / selected_terminal_PE\`

The 15% target is used as a **holding-period annualized return hurdle** to derive required future wealth, not as WACC or a valuation discount rate. The operator's Required Return and fixed Fundamental Target are calculated separately when they differ. Unvalidated or unknown distributions are never included.

## B57–B59 connection

- B57 all-items EPS is compared with the local return-hurdle EPS only when COMPANY_WIDE scope, a matching forecast period and a reconciled B57 scenario are confirmed.
- The EPS actually used by the primary EPS_MULTIPLE adapter is shown separately, along with the current-price / forecast-EPS forward P/E.
- B59's EPS numerator, denominator and declared-EPS-input difference components are multiplied by the selected terminal P/E to show their corresponding terminal per-share value effects.
- B60 calculates the terminal P/E required at the B57 EPS assumption when that EPS is positive and comparable.

## Controls and placement

Output is nested in the existing \`assessment.market_implied_expectation.price_implied_analysis.local_eps_multiple_recalculation\` field. No new top-level analysis key is added. The external \`market_implied_expectation.status\` and \`expectation_gap.status/direction\` are not changed. No model-supplied inversion is silently overwritten.

The calculation requires selected and calculated EPS_MULTIPLE, CNY currency, a pilot PIT-compatible structured price, passing valuation timing, and positive/unit-compatible terminal P/E and adapter EPS. B57 comparisons have additional company-wide / same-period / reconciled gates.

## Limitations and authority

- The selected terminal P/E is an analyst/model assumption, not an externally observed current market multiple; this is conditional price inversion, not external MIE.
- The price remains operator-attested where that is its recorded assurance. This calculation does not establish price-source authenticity or usage rights.
- A 15% EPS requirement under one selected terminal P/E does not prove that the selected P/E is fair or achievable.
- B60 does not change primary EPS/P/E/terminal values, B5/B6, return outputs, target entry price, the 15% hurdle, formal MIE/Forecast/Valuation admission, expectation-gap decision status, Decision, or execution authority.

## Regression coverage and validation

Five regression cases are authored for (1) price-to-hurdle EPS inversion, (2) dated distributions included only when already validated, (3) B59 value-effect transmission, (4) model-family and price qualification gates, and (5) company-wide B57 comparability. They have not been executed. No Replay, CI, merge, or macOS acceptance is claimed.
