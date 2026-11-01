# B75 — Event-driven future operating and earnings bridge

**Status:** implemented on an isolated branch based on B74; not merged.  
**Validation:** regression assertions added but not executed. No Replay, CI, or macOS acceptance is claimed.

## Objective

Continue from B74's primary contradiction and leading determinant. Explain the most important future events and conditions, then map those events into the existing B4 operating-driver assumptions and scenarios.

The intended causal chain is:

`current contradiction -> conditional future events -> operating variable changes -> B4 scenario bridge -> existing B5/B6 and B55-B62 per-share transmission`

## Audit findings

### Existing calculation capability

B4 already normalizes actuals and forward assumptions separately, validates units and source timing, and calculates product/company revenue, contribution, EBITDA, EBIT, pre-tax profit, simplified net profit and an FCF proxy when inputs permit. It also checks annual production against nameplate capacity when period alignment is explicit.

B42 and B55-B62 provide existing inventory/working-capital, product contribution, earnings bridge, diluted EPS, segment normalization and valuation-transmission work. These are retained.

### Missing capability

B4 receives scenario assumptions. It does not itself infer why a future event should occur, its preconditions, its sequence relative to other events, or what evidence would invalidate the event path. It also explicitly leaves project-to-company attributable earnings, dilution and per-share value unlinked unless the existing downstream transmission is supplied.

Therefore B75 does not add another numeric forecast engine. It adds the causal reasoning needed to make the existing numeric assumptions economically explainable.

## Implementation

- Extends the active price-blind Round A prompt to derive 2-4 material events/stages over the default one-year horizon from the primary contradiction.
- Reuses `assessment.thesis.drivers` as the existing ordered event narrative list; no new top-level fields or schema are added.
- Each event must explain its time window, preconditions/observable trigger, cutoff-compatible supporting evidence and counter-evidence, resulting operating-variable movement, mapping to a specific existing B4 input, profit/cash-flow direction and failure condition.
- Requires event order/dependency/parallel relationships; unrelated headlines cannot be presented as a causal chain.
- Event probabilities are numeric only when supported by a relevant base rate, historical frequency, contract milestone or observable leading indicator. Otherwise use a qualitative judgment and state its basis.
- Bear/Base/Bull paths must differ through event timing, intensity, conditions or operating outcomes. The B4 input's existing `basis`, `note` and `evidence_refs` should identify why the numeric assumption is plausible and whether it is actual, issuer forecast or analyst assumption.
- Requires reality constraints relevant to the primary contradiction: capacity, build/qualification/customer-introduction cycle, order-to-revenue conversion, supply/demand, pricing, mix, input costs, staffing/yield, funding, inventory and working capital.
- Explicitly warns that an infeasible volume path does not automatically invalidate a distinct price/mix improvement path; assess each path independently.
- Preserves the B4 arithmetic and B5/B6/B55-B62 transmission boundary. Project profit is not silently treated as attributable company net profit, EPS or shareholder value.
- Adds a report section that renders the ordered event chain before the driver ranking. Missing event chain is explicitly displayed as missing rather than inferred from scenario numbers.
- Adds deferred regression assertions. No tests were run.

## Boundaries

- No new forecast engine, event registry, event-probability engine, valuation model or decision gate.
- No change to B4 calculation formulas, B42 working-capital logic, B55-B62 earnings/per-share calculations, MIE or the 15% return hurdle.
- No change to Round A price-blind boundary or Round B frozen-artifact boundary.
- No formal evidence admission, forecast admission, Decision authority or order execution.
- Event narratives remain model research claims; citations/source references still require independent review and do not prove the event will happen.

## Later unified validation criteria

For a real company, reviewers should be able to trace:
1. one primary contradiction to 2-4 conditional events;
2. each event to cutoff-compatible evidence, counter-evidence and a time window;
3. each event to specific B4 operating assumptions;
4. each scenario to feasible, internally consistent volumes, prices, costs, capacity, capex and working capital;
5. B4 earnings/FCF outputs through existing downstream attributable earnings, diluted EPS and per-share value transmission;
6. each failure condition to the specific event, scenario and operating assumption it invalidates.

No test pass, Replay match, CI pass or macOS acceptance is claimed.
