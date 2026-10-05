# P3-A Real 300750 EV/EBITDA Consumption — 2026-10-05

## Status

**EXECUTABLE REAL SLICE / P3-A CONSUMED / P4-B FAIL-CLOSED**

This change does not modify CORE-04-C and does not acquire any new source bytes.

## Exact input boundary

The P3-A input consumes the three already admitted CORE-04-C observations:

| Observation date | Historical EV/EBITDA |
|---|---:|
| 2025-10-22 | 16.3854513730104779459499377618525879665943916394869455326834x |
| 2026-04-17 | 15.1302979548591306456425069051738011634952852968035319146755x |
| 2026-07-27 | 13.6686920853194080865159796474107277185842350664948830139214x |

The canonical historical definition remains:

`EV = close × reported total share capital + (interest-bearing debt − cash)`

`EV/EBITDA = EV / latest known completed fiscal-year EBITDA`

No vendor backfill and no synthetic TTM denominator is introduced.

## Real current PIT bridge

The existing CORE-03 admitted current bridge is reused for 2026-09-30:

- close = **291.11 CNY/share**, E011, official SZSE source-vintage evidence;
- shares = **4,380,630,342**, E008, existing CORE-03 admitted share-count bridge;
- net debt = **−276.904623bn CNY**, E005, 2026-06-30 balance-sheet basis;
- EBITDA = **119.197217bn CNY**, FY2025 completed fiscal-year EBITDA from the already admitted CORE-04-C source.

This produces:

`EV = 998,340,675,859.62 CNY`

`current EV/EBITDA = 8.375536786732361377...`

## P3-A result

The existing deterministic P3-A engine consumes all three historical observations and obtains:

- historical admissible multiple range = **13.668692085319408...x to 16.385451373010478...x**;
- current multiple = **8.375536786732361...x**;
- current multiple is **outside** the historical admissible range;
- candidate fit = **INFEASIBLE**;
- identifiability = **UNIDENTIFIABLE** for this explicitly scoped single-candidate slice.

The current multiple is approximately **38.72% below the historical lower bound**.

This is a model-boundary result, not a claim that the market “cannot” value CATL at a lower EV/EBITDA. The P3-A baseline only accepts the current point when it lies inside the historical range.

## Stability result

The current implementation requires a perturbable historical window larger than the minimum stability point count. With exactly three historical observations and the default `stability_min_historical_points=3`, P3-A returns:

**Stability = INSUFFICIENT_EVIDENCE**

A fourth pre-cutoff historical EV/EBITDA observation is therefore required to establish the current P3-A leave-one-out stability gate without changing the rule.

## P4-B / MIE result

P4-B is **not materialized** for this real slice. It fails closed because there is no feasible ratio model to convert into an MIE.

No intrinsic value, current EV/EBITDA multiple, or historical range is silently promoted to Market Implied Expectation.

## Additional audit flag

The existing CORE-03 current share-count bridge (E008) is not represented with the same semantic label as the CORE-04-C historical `reported total share capital` field. The current P3 multiple therefore remains a **technical integration result, not a decision-grade valuation observation** until share-count basis comparability is independently reconciled.

That issue is intentionally not patched inside P3-A in this batch; changing the canonical model semantics here would mix a data-definition audit with the real-observation consumption gate.

## Scope boundary

This slice proves only:

`CORE-04-C admitted observations → typed P3-A consumption → deterministic fit/identifiability/stability → P4-B fail-closed boundary`

It does not claim:

- full PE/PS/PB/EV-EBITDA candidate-set completeness;
- unique true-market-model identification;
- decision-grade MIE;
- Expectation Gap;
- Expected Return;
- decision action or position sizing.
