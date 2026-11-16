# B54 — Decision-Chain Blocker Trace

**Status:** implemented on the feature branch; unmerged and non-canonical. **Validation:** four B54 regression cases are authored but not run. Replay, CI and real macOS full-run acceptance remain deferred / not verified.

## Why this batch

The pilot already records individual model, timing, return, risk, and portfolio states, but an operator still has to cross-read several report sections to connect a blocker to the results it makes unavailable. B54 turns those existing states into one ordered, explanatory dependency trace.

## Changes

1. **One ordered trace, within the existing decision object.** `decision.decision_chain_trace` groups source/cutoff integrity, primary-model eligibility, timing, return calculation, price hurdles, thesis-risk stress, portfolio constraints, and formal admission/authority. There is no new top-level analysis key.
2. **Blockers propagate only to the outputs they actually affect.** If the primary model is ineligible or valuation timing is unresolved, the trace explicitly connects that blocker to return calculation, target entry price and B6 price-zone sensitivity. When the return solver itself returns no metrics, the trace carries its actual reason downstream.
3. **Price failure and target-price calculation remain distinct.** If a valid return calculation says the current quote fails an entry hurdle, the trace blocks the current-price BUY/ADD screen but preserves any calculated target entry-price cap as a conditional reference. It does not treat a failed current quote as proof that a target price is uncomputable.
4. **Portfolio permission is a separate gate.** A portfolio constraint/package block prevents a conditional position package or permission to add capital, but does not erase independently calculated return/price figures. Package readiness is only shown as conditional when the integrated package status and constraint status agree.
5. **Formal authority remains a hard boundary.** The trace always shows formal admission as `NOT_ADMITTED`, formal Decision as `NOT_CREATED`, authorized new position as `0`, and execution authorization as false.

## What did not change

- No change to the production decision kernel or its precedence.
- No change to the 15% annualized-return hurdle, operator Required Return, Bear-loss cap, entry-price formula, valuation formula, or portfolio sizing arithmetic.
- The trace is an explanatory artifact built from existing results; it does not promote source claims or pilot calculations into formal Evidence/PIT, Forecast, Valuation, Decision, or execution authority.
- The trace is nested under `decision`; the existing Replay comparison already covers the full `decision` object.

## Regression cases and validation status

Four regression cases are authored in `tests/test_local_investment_pilot_v01.py`:

1. Normal analysis includes ordered trace stages and preserves the authority boundary in the report.
2. Primary-model ineligibility propagates to return and B6/target-price availability.
3. A current-price hurdle failure leaves a valid conditional target-price cap visible.
4. A portfolio constraint block prevents conditional position permission without erasing already calculated return/price values.

They have **not** been executed. No test pass, Replay match, CI pass, or macOS acceptance is claimed.
