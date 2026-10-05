# CORE-04 × 300750 Production Decision E2E — 2026-10-05

## Status

**EXECUTED / CI PASS / CAPITAL NOT ADMITTED**

This is the first real-company execution of the post-PR#70 CORE-04 production decision boundary using the canonical main created by PR #70 merge.

Canonical main at start of E2E:
`0281a7f352dc0a7aaf6dc37756b070c31cedc2cf`

## Evidence and case

Case: `RC-CN-A-300750-20261004`

Cutoff: `2026-10-04`

Current price:
- 2026-09-30 close = **291.11 CNY/share**
- canonical price evidence = **E011**
- admitted price provenance is rebuilt through the canonical current-price registry during the E2E.

Upstream real inputs reused without new valuation-model construction:
- Core-02 reality / Trust / Quality / Value Core / Value Driver Ranking;
- Core-03 independent Bear/Base/Bull forecast;
- Core-03 human-selected DCF valuation;
- CORE-04-C historical EV/EBITDA evidence and P3/P4 semantic state.

## Horizon

The case explicitly uses a **3Y Horizon Override** because CATL is a major industry leader and is in a major investment / capacity cycle.

This is an explicit exception. IIOS default horizon remains **1Y**.

## Return / Risk result

Using the admitted CORE-03 DCF scenario values:

- Bear = 258.32 CNY/share
- Base = 418.49 CNY/share
- Bull = 638.97 CNY/share
- Probabilities = 25% / 50% / 25%
- Probability-weighted terminal wealth = **433.5675 CNY/share**

At 291.11 CNY:

- Entry Return Cushion = **48.93597%** → PASS (>=15%)
- Margin of Safety = **32.85705%**
- Expected Total Return over 3Y = **48.93597%**
- Expected Annualized Return = **14.20011257%** → **FAIL** vs 15% target
- Required Return = **10%** → PASS
- Bear Return = **-11.26378%**
- Risk Gate with max loss 25% → PASS
- Return Gate overall → **FAIL**, because all return conditions are conjunctive.

Return/risk-derived target entry price:
- **285.0776691 CNY/share**
- current price 291.11 is above that target.

No MIE is required for this path because CORE-04 v0.3 uses `OPTIONAL_EXPLANATORY` MIE semantics.

## Strict real-case decision

The real upstream Trust assessment contains conditional dimensions. The E2E therefore maps Trust to:

`REVALIDATION`

The formal Thesis state is not yet independently admitted by an upstream machine contract, so it remains:

`UNKNOWN`

The production kernel result is:

- Action: **REVIEW_REQUIRED**
- Decision Status: **REVIEW_REQUIRED**
- Primary reason: **TRUST_NOT_PASS_REQUIRES_REVIEW**
- New capital admitted: **FALSE**
- MIE policy: **OPTIONAL_EXPLANATORY**

This is the canonical real-case result. It is fail-closed and does not manufacture BUY/ADD.

## Gate-normalized kernel diagnostic

To isolate the return/price decision without pretending that the real Trust state is PASS, the same case was run under an explicitly labelled diagnostic projection:

- Trust = PASS
- Thesis = INTACT
- all other real return/risk inputs unchanged
- MIE still omitted / optional

Diagnostic result:

- Action: **WATCH**
- Decision Status: **READY**
- Primary reason: **CURRENT_PRICE_ABOVE_TARGET_ENTRY_PRICE**
- New capital admitted: **FALSE**

This isolates the key economic conclusion:

**Even after upstream qualitative gates are temporarily normalized, 300750 at 291.11 does not clear the 15% expected annualized return threshold under the explicit 3Y override.**

## Integration findings

1. Trust is not safe to coerce from conditional to PASS; the strict case correctly fails closed.
2. Formal Thesis admission is still missing as a dedicated upstream machine contract.
3. Quality and Value Driver information is available in the case, but the current Decision Kernel does not yet accept Quality as an explicit typed input.
4. MIE is now correctly optional and does not veto the return/risk decision path.
5. The current production kernel therefore works as a deterministic decision boundary, but the full upstream-to-decision contract is **not yet fully closed**.

## CI acceptance

- CORE-04 Real 300750 Decision E2E #3 — **PASS**
- Investment Core CI #459 — **PASS**
- CORE-00 Scope Reconciliation #196 — **PASS**

E2E result artifact:

`CORE04_REAL_300750_DECISION_E2E_RESULT_2026-10-05.json`

Artifact ZIP digest:

`c699b53321d9769b576abb787f6a353b5aa140a9bafd7f8ef3f678bd3cb526cc`

Extracted result JSON SHA-256:

`8b133f172411ba6c0fc7bf7edc5044cb6312b7f8fe30e602ac5c26387d376589`

## Boundary

This E2E does **not** authorize execution and does not imply a final human portfolio decision.

Current conclusion:
`REVIEW_REQUIRED / NO NEW CAPITAL`

The most important unresolved CORE-04 integration gap is now upstream gate completeness—especially Quality and formal Thesis admission—not another P3/P4 market-model expansion.
