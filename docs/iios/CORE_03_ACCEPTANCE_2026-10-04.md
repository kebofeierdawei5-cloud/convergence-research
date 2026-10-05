# CORE-03 Real 300750 — Acceptance Record

Date: 2026-10-04
Status: PASS / MERGED — vertical slice; P4-F closure remains BLOCKED

## Scope

CORE-03 real-company vertical slice:

CORE-02 Real 300750
→ Independent Forecast
→ Company Valuation
→ P4-F Market Implied Expectation
→ Expectation Gap.

## Evidence

- PR #31: MERGED
- merge commit: `e0662bb4efa5bfc40478240a0d9ef4bbcadb658a`
- CORE-03 CI run #7 / `37210940680`: SUCCESS
- CORE-03 tests + CORE-02 / CORE-01 / Value Core regression: SUCCESS
- Investment Core CI run #230 / `37210940676`: SUCCESS
- Real case: `RC-CN-A-300750-20261004`
- Real market observation: 2026-09-30 close 291.11 CNY
- Current share-count anchor: 2026-09-29 issued shares excluding treasury 4,380,630,342
- Forecast horizon: 2027-2029 (H=3 explicit Horizon Override)
- Scenario probabilities: 25% / 50% / 25%
- Primary valuation: human-selected DCF
- P4-F snapshot: valid BLOCKED / INSUFFICIENT_EVIDENCE and replay PASS
- Expectation Gap: BLOCKED by MIE insufficiency; intrinsic-value upside is explicitly not substituted for Expectation Gap.

## Economic output

DCF scenario values per share:
- Bear: 258.3224966
- Base: 418.4908702
- Bull: 638.9731868

Probability-weighted value per share:
- 433.5693559

Expected 3-year CAGR from 291.11:
- 14.2003%

This is a research output, not a BUY/ADD/HOLD decision.

## Core research finding

The first value question remains:

Can incremental capacity investment sustain high incremental ROIC while converting earnings growth into durable FCF?

The forecast therefore makes FCF and incremental ROIC explicit scenario variables.

## P4-F closure blocker

The single-company case currently lacks sufficient PIT historical market-model observations to identify a qualified market-implied expectation for the candidate valuation set.

This is an evidence/data-closure blocker, not an excuse to substitute current price or intrinsic-value upside.

## Next task

Acquire the minimum per-company PIT market-valuation observation set needed for P3/P4 identification and P4-F replay closure.

No CSI800 / CSI Industry / A02 / universe-level Security Master dependency is required.
